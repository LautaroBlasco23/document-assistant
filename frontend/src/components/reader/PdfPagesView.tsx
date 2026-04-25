import * as React from 'react'
import { Document, Page } from 'react-pdf'

import 'react-pdf/dist/Page/TextLayer.css'

export interface PdfPagesViewHandle {
  scrollToPage: (pageNumber: number) => void
}

interface PdfPagesViewProps {
  fileUrl: string
  visiblePages?: number[] | null
  renderPageHeader?: (pageNumber: number) => React.ReactNode
  onCurrentPageChange?: (pageNumber: number) => void
  onNumPagesChange?: (numPages: number) => void
  onContextMenu?: (e: React.MouseEvent) => void
  onClickAway?: () => void
  scrollRef?: React.MutableRefObject<PdfPagesViewHandle | null>
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
  renderPageHeader,
  onCurrentPageChange,
  onNumPagesChange,
  onContextMenu,
  onClickAway,
  scrollRef,
}: PdfPagesViewProps) {
  const [numPages, setNumPages] = React.useState(0)
  const [containerWidth, setContainerWidth] = React.useState(() =>
    typeof window !== 'undefined' ? Math.min(800, window.innerWidth - SIDE_PADDING) : 800
  )
  const [activePages, setActivePages] = React.useState<Set<number>>(() => new Set())
  const [estimatedPageHeight, setEstimatedPageHeight] = React.useState(FALLBACK_PAGE_HEIGHT)

  const scrollContainerRef = React.useRef<HTMLDivElement>(null)
  const pageSlotRefs = React.useRef<Map<number, HTMLDivElement>>(new Map())
  const observerRef = React.useRef<IntersectionObserver | null>(null)
  const onCurrentPageChangeRef = React.useRef(onCurrentPageChange)
  const onNumPagesChangeRef = React.useRef(onNumPagesChange)

  React.useEffect(() => {
    onCurrentPageChangeRef.current = onCurrentPageChange
  }, [onCurrentPageChange])
  React.useEffect(() => {
    onNumPagesChangeRef.current = onNumPagesChange
  }, [onNumPagesChange])

  const pageList = React.useMemo(() => {
    if (visiblePages && visiblePages.length > 0) return visiblePages
    if (numPages > 0) return Array.from({ length: numPages }, (_, i) => i + 1)
    return []
  }, [visiblePages, numPages])

  // ResizeObserver tracks the scroll container width so pages re-fit on layout changes.
  React.useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (!w) return
      const next = Math.min(800, Math.max(320, w - 32))
      setContainerWidth((prev) => (Math.abs(prev - next) > 1 ? next : prev))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Single IntersectionObserver shared across all page slots. Tracks which pages
  // are within ~3 viewports of the visible area; only those are rendered fully.
  React.useEffect(() => {
    const root = scrollContainerRef.current
    if (!root) return
    const margin = `${PAGE_BUFFER_VIEWPORTS * 100}% 0px`
    const observer = new IntersectionObserver(
      (entries) => {
        let nextActive: Set<number> | null = null
        let topMost: { page: number; ratio: number } | null = null
        for (const entry of entries) {
          const pageNum = Number((entry.target as HTMLElement).dataset.page)
          if (!pageNum) continue
          if (entry.isIntersecting) {
            if (!nextActive) nextActive = new Set(activePagesRef.current)
            nextActive.add(pageNum)
            // Track the most-visible page for current-page reporting.
            if (entry.intersectionRatio > 0 && (!topMost || entry.intersectionRatio > topMost.ratio)) {
              topMost = { page: pageNum, ratio: entry.intersectionRatio }
            }
          } else {
            if (!nextActive) nextActive = new Set(activePagesRef.current)
            nextActive.delete(pageNum)
          }
        }
        if (nextActive) {
          activePagesRef.current = nextActive
          setActivePages(nextActive)
        }
        if (topMost) onCurrentPageChangeRef.current?.(topMost.page)
      },
      { root, rootMargin: margin, threshold: [0, 0.25, 0.5, 0.75, 1] }
    )
    observerRef.current = observer
    // Observe any slots already mounted.
    pageSlotRefs.current.forEach((el) => observer.observe(el))
    return () => {
      observer.disconnect()
      observerRef.current = null
    }
  }, [])

  // Mirror activePages into a ref so the observer callback can merge without re-subscribing.
  const activePagesRef = React.useRef<Set<number>>(activePages)
  React.useEffect(() => {
    activePagesRef.current = activePages
  }, [activePages])

  // Stable per-page ref factory: same identity per pageNumber across renders.
  const refFactoryCache = React.useRef<Map<number, (el: HTMLDivElement | null) => void>>(new Map())
  const getSlotRef = React.useCallback((pageNumber: number) => {
    let cached = refFactoryCache.current.get(pageNumber)
    if (cached) return cached
    cached = (el: HTMLDivElement | null) => {
      const observer = observerRef.current
      const prev = pageSlotRefs.current.get(pageNumber)
      if (prev && prev !== el) observer?.unobserve(prev)
      if (el) {
        pageSlotRefs.current.set(pageNumber, el)
        observer?.observe(el)
      } else {
        pageSlotRefs.current.delete(pageNumber)
      }
    }
    refFactoryCache.current.set(pageNumber, cached)
    return cached
  }, [])

  // Imperative handle for parent-driven scroll.
  React.useImperativeHandle(
    scrollRef as React.MutableRefObject<PdfPagesViewHandle | null> | undefined,
    () => ({
      scrollToPage: (pageNumber: number) => {
        const el = pageSlotRefs.current.get(pageNumber)
        el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      },
    }),
    []
  )

  const handleDocLoad = React.useCallback(({ numPages: n }: { numPages: number }) => {
    setNumPages(n)
    onNumPagesChangeRef.current?.(n)
  }, [])

  const handleFirstPageRender = React.useCallback(() => {
    // After the first page paints, capture its height as the placeholder estimate.
    const first = pageSlotRefs.current.values().next().value as HTMLDivElement | undefined
    if (!first) return
    const h = first.getBoundingClientRect().height
    if (h > 100) setEstimatedPageHeight(h)
  }, [])

  return (
    <div
      ref={scrollContainerRef}
      className="flex-1 min-w-0 bg-gray-100 overflow-auto flex flex-col items-center py-6 px-4 gap-8 cursor-text"
      onContextMenu={onContextMenu}
      onClick={onClickAway}
    >
      <Document
        file={fileUrl}
        options={DOCUMENT_OPTIONS}
        onLoadSuccess={handleDocLoad}
        loading={
          <div className="w-[600px] h-[800px] flex items-center justify-center text-sm text-gray-400">
            Loading PDF...
          </div>
        }
        error={
          <div className="w-[600px] h-[200px] flex items-center justify-center text-sm text-red-400 px-6">
            Failed to load PDF. The file may not be available.
          </div>
        }
      >
        {pageList.map((pageNumber, idx) => {
          const isActive = activePages.has(pageNumber)
          return (
            <React.Fragment key={pageNumber}>
              {renderPageHeader?.(pageNumber)}
              <div
                ref={getSlotRef(pageNumber)}
                data-page={pageNumber}
                className="flex flex-col items-center"
                style={{ minHeight: isActive ? undefined : estimatedPageHeight }}
              >
                {isActive ? (
                  <div className="bg-white shadow-md">
                    <MemoPage
                      pageNumber={pageNumber}
                      width={containerWidth}
                      onRenderSuccess={idx === 0 ? handleFirstPageRender : undefined}
                    />
                  </div>
                ) : (
                  <div
                    className="bg-white shadow-md"
                    style={{ width: containerWidth, height: estimatedPageHeight }}
                  />
                )}
                <span className="mt-2 text-xs text-gray-400 select-none">
                  {pageNumber} / {pageList.length}
                </span>
              </div>
            </React.Fragment>
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
