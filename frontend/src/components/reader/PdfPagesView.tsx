import * as React from 'react'
import { Document, Page } from 'react-pdf'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import 'react-pdf/dist/Page/TextLayer.css'

import type { ContentWidth } from '../../stores/reader-preferences'

function maxPdfWidth(cw: ContentWidth): number {
  if (cw === 'full') return Infinity
  if (cw === 'wide') return 1100
  return 800
}

export interface PdfPagesViewHandle {
  scrollToPage: (pageNumber: number) => void
}

interface PdfPagesViewProps {
  fileUrl: string
  visiblePages?: number[] | null
  zoom?: number
  contentWidth?: ContentWidth
  onCurrentPageChange?: (pageNumber: number) => void
  onNumPagesChange?: (numPages: number) => void
  onContextMenu?: (e: React.MouseEvent) => void
  onClickAway?: () => void
  scrollRef?: React.MutableRefObject<PdfPagesViewHandle | null>
  mode?: 'scroll' | 'paged'
  initialPage?: number
}

const PAGE_BUFFER_VIEWPORTS = 3
const FALLBACK_PAGE_HEIGHT = 1000
const SIDE_PADDING = 400

const DOCUMENT_OPTIONS = {
  // Keep stable identity across renders to avoid pdfjs reloading the file.
} as const

export function PdfPagesView({
  fileUrl,
  visiblePages,
  zoom = 1,
  contentWidth = 'comfortable',
  onCurrentPageChange,
  onNumPagesChange,
  onContextMenu,
  onClickAway,
  scrollRef,
  mode = 'scroll',
  initialPage,
}: PdfPagesViewProps) {
  const [numPages, setNumPages] = React.useState(0)
  const capRef = React.useRef(maxPdfWidth(contentWidth))
  capRef.current = maxPdfWidth(contentWidth)
  const [baseWidth, setBaseWidth] = React.useState(() =>
    typeof window !== 'undefined' ? Math.min(maxPdfWidth(contentWidth), window.innerWidth - SIDE_PADDING) : maxPdfWidth(contentWidth)
  )
  const displayWidth = Math.round(baseWidth * zoom)
  const [activePages, setActivePages] = React.useState<Set<number>>(() => new Set())
  const [estimatedPageHeight, setEstimatedPageHeight] = React.useState(FALLBACK_PAGE_HEIGHT)

  // Paged mode: current page (0 = not yet initialized)
  const [pagedPage, setPagedPage] = React.useState<number>(0)
  const pagedInitDoneRef = React.useRef(false)

  const scrollContainerRef = React.useRef<HTMLDivElement>(null)
  const pageSlotRefs = React.useRef<Map<number, HTMLDivElement>>(new Map())
  const observerRef = React.useRef<IntersectionObserver | null>(null)
  const onCurrentPageChangeRef = React.useRef(onCurrentPageChange)
  const onNumPagesChangeRef = React.useRef(onNumPagesChange)

  React.useEffect(() => { onCurrentPageChangeRef.current = onCurrentPageChange }, [onCurrentPageChange])
  React.useEffect(() => { onNumPagesChangeRef.current = onNumPagesChange }, [onNumPagesChange])

  const pageList = React.useMemo(() => {
    if (visiblePages && visiblePages.length > 0) return visiblePages
    if (numPages > 0) return Array.from({ length: numPages }, (_, i) => i + 1)
    return []
  }, [visiblePages, numPages])

  // Paged mode: initialize current page when pageList first populates
  React.useEffect(() => {
    if (mode !== 'paged' || pageList.length === 0 || pagedInitDoneRef.current) return
    pagedInitDoneRef.current = true
    const target = (initialPage && pageList.includes(initialPage)) ? initialPage : pageList[0]
    setPagedPage(target)
  }, [pageList.length, mode, initialPage])

  // Paged mode: report current page to parent
  React.useEffect(() => {
    if (mode === 'paged' && pagedPage > 0) {
      onCurrentPageChangeRef.current?.(pagedPage)
    }
  }, [pagedPage, mode])

  // Scroll mode: scroll to initialPage after PDF loads.
  // We pre-activate the target page and its neighbors before scrolling so that their real
  // heights are in the DOM, then do a smooth correction pass to counteract any drift caused
  // by placeholder pages above the target expanding to their actual heights.
  const initialScrollDoneRef = React.useRef(false)
  React.useEffect(() => {
    if (mode === 'paged' || initialScrollDoneRef.current || !numPages || !initialPage) return
    if (!pageList.includes(initialPage)) return
    initialScrollDoneRef.current = true

    // Pre-activate a window around the target so real heights are rendered.
    const idx = pageList.indexOf(initialPage)
    if (idx !== -1) {
      const toActivate = new Set(activePagesRef.current)
      for (let i = Math.max(0, idx - 2); i <= Math.min(pageList.length - 1, idx + 3); i++) {
        toActivate.add(pageList[i])
      }
      activePagesRef.current = toActivate
      setActivePages(toActivate)
    }

    // First pass: instant jump to approximate position.
    pageSlotRefs.current.get(initialPage)?.scrollIntoView({ behavior: 'instant', block: 'start' })
    // Smooth correction after real page heights have settled.
    setTimeout(() => {
      pageSlotRefs.current.get(initialPage)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 250)
  }, [numPages, initialPage, mode, pageList])

  // ResizeObserver: tracks scroll container width for page re-fit on layout changes.
  React.useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (!w) return
      const cap = capRef.current
      const next = Number.isFinite(cap) ? Math.min(cap, Math.max(320, w - 32)) : Math.max(320, w - 32)
      setBaseWidth((prev) => (Math.abs(prev - next) > 1 ? next : prev))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // IntersectionObserver for virtualization — scroll mode only.
  React.useEffect(() => {
    if (mode === 'paged') return
    const root = scrollContainerRef.current
    if (!root) return
    const margin = `${PAGE_BUFFER_VIEWPORTS * 100}% 0px`
    const observer = new IntersectionObserver(
      (entries) => {
        let nextActive: Set<number> | null = null
        for (const entry of entries) {
          const pageNum = Number((entry.target as HTMLElement).dataset.page)
          if (!pageNum) continue
          if (entry.isIntersecting) {
            if (!nextActive) nextActive = new Set(activePagesRef.current)
            nextActive.add(pageNum)
          } else {
            if (!nextActive) nextActive = new Set(activePagesRef.current)
            nextActive.delete(pageNum)
          }
        }
        if (nextActive) {
          activePagesRef.current = nextActive
          setActivePages(nextActive)
        }
      },
      { root, rootMargin: margin, threshold: 0 }
    )
    observerRef.current = observer
    pageSlotRefs.current.forEach((el) => observer.observe(el))
    return () => {
      observer.disconnect()
      observerRef.current = null
    }
  }, [mode])

  const activePagesRef = React.useRef<Set<number>>(activePages)
  React.useEffect(() => { activePagesRef.current = activePages }, [activePages])

  // Viewport observer: tracks topmost visible page to report as current — scroll mode only.
  const viewportObserverRef = React.useRef<IntersectionObserver | null>(null)
  const viewportVisibleRef = React.useRef<Set<number>>(new Set())
  React.useEffect(() => {
    if (mode === 'paged') return
    const root = scrollContainerRef.current
    if (!root) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const pageNum = Number((entry.target as HTMLElement).dataset.page)
          if (!pageNum) continue
          if (entry.isIntersecting) {
            viewportVisibleRef.current.add(pageNum)
          } else {
            viewportVisibleRef.current.delete(pageNum)
          }
        }
        if (viewportVisibleRef.current.size > 0) {
          const topPage = Math.min(...viewportVisibleRef.current)
          onCurrentPageChangeRef.current?.(topPage)
        }
      },
      { root, rootMargin: '0px', threshold: 0.01 }
    )
    viewportObserverRef.current = observer
    pageSlotRefs.current.forEach((el) => observer.observe(el))
    return () => {
      observer.disconnect()
      viewportObserverRef.current = null
    }
  }, [mode])

  // Stable per-page ref factory: same identity per pageNumber across renders.
  const refFactoryCache = React.useRef<Map<number, (el: HTMLDivElement | null) => void>>(new Map())
  const getSlotRef = React.useCallback((pageNumber: number) => {
    let cached = refFactoryCache.current.get(pageNumber)
    if (cached) return cached
    cached = (el: HTMLDivElement | null) => {
      const observer = observerRef.current
      const vpObserver = viewportObserverRef.current
      const prev = pageSlotRefs.current.get(pageNumber)
      if (prev && prev !== el) {
        observer?.unobserve(prev)
        vpObserver?.unobserve(prev)
      }
      if (el) {
        pageSlotRefs.current.set(pageNumber, el)
        observer?.observe(el)
        vpObserver?.observe(el)
      } else {
        pageSlotRefs.current.delete(pageNumber)
        viewportVisibleRef.current.delete(pageNumber)
      }
    }
    refFactoryCache.current.set(pageNumber, cached)
    return cached
  }, [])

  // Paged mode navigation helpers
  const pagedPageIdx = pageList.indexOf(pagedPage)
  const canPrev = pagedPageIdx > 0
  const canNext = pagedPageIdx < pageList.length - 1

  const gotoPrev = React.useCallback(() => {
    setPagedPage((p) => {
      const idx = pageList.indexOf(p)
      return idx > 0 ? pageList[idx - 1] : p
    })
  }, [pageList])

  const gotoNext = React.useCallback(() => {
    setPagedPage((p) => {
      const idx = pageList.indexOf(p)
      return idx < pageList.length - 1 ? pageList[idx + 1] : p
    })
  }, [pageList])

  // Keyboard navigation in paged mode (skip when focus is inside an input/textarea).
  React.useEffect(() => {
    if (mode !== 'paged') return
    const handleKey = (e: KeyboardEvent) => {
      const active = document.activeElement
      if (
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active as HTMLElement)?.isContentEditable
      ) return
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault()
        gotoPrev()
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault()
        gotoNext()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [mode, gotoPrev, gotoNext])

  // Imperative scroll handle
  React.useImperativeHandle(
    scrollRef as React.MutableRefObject<PdfPagesViewHandle | null> | undefined,
    () => ({
      scrollToPage: (pageNumber: number) => {
        if (mode === 'paged') {
          if (pageList.includes(pageNumber)) setPagedPage(pageNumber)
          return
        }

        // Force the target and its immediate neighbors into activePages so their real heights
        // are in the DOM before we correct the scroll position. Without this, placeholder divs
        // with estimated heights cause layout shifts that push the target out from under us.
        const idx = pageList.indexOf(pageNumber)
        if (idx !== -1) {
          const toActivate = new Set(activePagesRef.current)
          for (let i = Math.max(0, idx - 1); i <= Math.min(pageList.length - 1, idx + 2); i++) {
            toActivate.add(pageList[i])
          }
          activePagesRef.current = toActivate
          setActivePages(toActivate)
        }

        // First pass: instant jump to approximate position (page may still be a placeholder).
        pageSlotRefs.current.get(pageNumber)?.scrollIntoView({ behavior: 'instant', block: 'start' })
        // Smooth correction once the pre-activated pages have actually rendered.
        setTimeout(() => {
          pageSlotRefs.current.get(pageNumber)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 250)
      },
    }),
    [mode, pageList]
  )

  const handleDocLoad = React.useCallback(({ numPages: n }: { numPages: number }) => {
    setNumPages(n)
    onNumPagesChangeRef.current?.(n)
  }, [])

  const handleFirstPageRender = React.useCallback(() => {
    const first = pageSlotRefs.current.values().next().value as HTMLDivElement | undefined
    if (!first) return
    const h = first.getBoundingClientRect().height
    if (h > 100) setEstimatedPageHeight(h)
  }, [])

  // ── PAGED MODE ───────────────────────────────────────────────────────────────
  // Scroll back to top whenever the user moves to a new page.
  React.useEffect(() => {
    if (mode === 'paged') scrollContainerRef.current?.scrollTo({ top: 0 })
  }, [pagedPage, mode])

  if (mode === 'paged') {
    return (
      <div
        className="flex-1 min-w-0 flex bg-surface-100 dark:bg-bg-inset"
        onContextMenu={onContextMenu}
        onClick={onClickAway}
      >
        {/* Left arrow — full height strip */}
        <button
          onClick={(e) => { e.stopPropagation(); gotoPrev() }}
          disabled={!canPrev}
          className="flex items-center justify-center w-10 shrink-0 text-text-tertiary hover:text-text-primary hover:bg-surface-200 dark:hover:bg-surface-100 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
          aria-label="Previous page"
          title="Previous page (←)"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>

        {/* Page content */}
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
          <Document
            file={fileUrl}
            options={DOCUMENT_OPTIONS}
            onLoadSuccess={handleDocLoad}
            loading={
              <div className="h-full flex items-center justify-center text-sm text-text-tertiary">
                Loading PDF...
              </div>
            }
            error={
              <div className="h-full flex items-center justify-center text-sm text-danger px-6">
                Failed to load PDF. The file may not be available.
              </div>
            }
          >
            {pagedPage > 0 && (
              <div className="w-full flex flex-col items-center py-6">
                <div className="bg-surface dark:bg-surface-100 shadow-md">
                  <MemoPage pageNumber={pagedPage} width={displayWidth} />
                </div>
                <div className="mt-3 text-xs tabular-nums text-text-tertiary select-none">
                  {pagedPageIdx + 1} / {pageList.length}
                </div>
              </div>
            )}
          </Document>
        </div>

        {/* Right arrow — full height strip */}
        <button
          onClick={(e) => { e.stopPropagation(); gotoNext() }}
          disabled={!canNext}
          className="flex items-center justify-center w-10 shrink-0 text-text-tertiary hover:text-text-primary hover:bg-surface-200 dark:hover:bg-surface-100 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
          aria-label="Next page"
          title="Next page (→)"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      </div>
    )
  }

  // ── SCROLL MODE ──────────────────────────────────────────────────────────────
  return (
    <div
      ref={scrollContainerRef}
      className="flex-1 min-w-0 bg-surface-100 dark:bg-bg-inset overflow-auto flex flex-col items-center py-6 px-4 gap-8"
      onContextMenu={onContextMenu}
      onClick={onClickAway}
    >
      <Document
        file={fileUrl}
        options={DOCUMENT_OPTIONS}
        onLoadSuccess={handleDocLoad}
        loading={
          <div className="w-[600px] h-[800px] flex items-center justify-center text-sm text-text-tertiary">
            Loading PDF...
          </div>
        }
        error={
          <div className="w-[600px] h-[200px] flex items-center justify-center text-sm text-danger px-6">
            Failed to load PDF. The file may not be available.
          </div>
        }
      >
        {pageList.map((pageNumber, idx) => {
          const isActive = activePages.has(pageNumber)
          return (
            <div
              key={pageNumber}
              ref={getSlotRef(pageNumber)}
              data-page={pageNumber}
              className="flex flex-col items-center"
              style={{ minHeight: isActive ? undefined : estimatedPageHeight }}
            >
              {isActive ? (
                <div className="bg-surface dark:bg-surface-100 shadow-md">
                  <MemoPage
                    pageNumber={pageNumber}
                    width={displayWidth}
                    onRenderSuccess={idx === 0 ? handleFirstPageRender : undefined}
                  />
                </div>
              ) : (
                <div
                  className="bg-white shadow-md"
                  style={{ width: displayWidth, height: estimatedPageHeight }}
                />
              )}
            </div>
          )
        })}
      </Document>
    </div>
  )
}

interface MemoPageProps {
  pageNumber: number
  width: number
  onRenderSuccess?: () => void
}

const MemoPage = React.memo(function MemoPage({ pageNumber, width, onRenderSuccess }: MemoPageProps) {
  return (
    <Page
      pageNumber={pageNumber}
      width={width}
      renderAnnotationLayer={false}
      renderTextLayer
      onRenderSuccess={onRenderSuccess}
    />
  )
})
