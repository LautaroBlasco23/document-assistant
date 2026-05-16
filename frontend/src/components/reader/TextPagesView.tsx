import * as React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { cn } from '../../lib/cn'
import type { KnowledgeChapter } from '../../types/knowledge-tree'
import type { FormatMode } from './FormatterMenu'
import type { ContentWidth } from '../../stores/reader-preferences'
import { readerMarkdownComponents } from './markdownComponents'
import type { Highlight } from '../../stores/highlights-store'

function markTextByPosition(text: string, highlights: Highlight[], chapterNumber: number): React.ReactNode {
  const spans = highlights
    .filter((h) => h.chapterNumber === chapterNumber && h.startOffset !== undefined && h.endOffset !== undefined)
    .map((h) => ({ start: h.startOffset!, end: h.endOffset! }))
    .sort((a, b) => a.start - b.start)

  if (spans.length === 0) return text

  const parts: React.ReactNode[] = []
  let lastEnd = 0

  for (const { start, end } of spans) {
    if (start > lastEnd) {
      parts.push(text.slice(lastEnd, start))
    }
    if (end > lastEnd) {
      parts.push(
        <mark key={start} className="bg-yellow-200 dark:bg-yellow-700/50 text-inherit rounded-sm px-0.5">
          {text.slice(Math.max(start, lastEnd), Math.min(end, text.length))}
        </mark>,
      )
      lastEnd = end
    }
  }

  if (lastEnd < text.length) {
    parts.push(text.slice(lastEnd))
  }

  return <>{parts}</>
}

export interface TextPagesViewHandle {
  scrollToChapter: (chapterNumber: number) => void
}

interface ChapterDoc {
  chapter_number: number | null
  content: string
}

interface TextPagesViewProps {
  chapters: KnowledgeChapter[]
  chapterDocs: ChapterDoc[]
  zoom?: number
  mode?: 'scroll' | 'paged'
  formatMode?: FormatMode
  contentWidth?: ContentWidth
  initialChapter?: number
  onCurrentChapterChange?: (chapterNumber: number) => void
  onContextMenu?: (e: React.MouseEvent) => void
  onClickAway?: () => void
  scrollRef?: React.MutableRefObject<TextPagesViewHandle | null>
  isTxt?: boolean
  highlights?: Highlight[]
}

export function TextPagesView({
  chapters,
  chapterDocs,
  zoom = 1,
  mode = 'scroll',
  formatMode = 'plain',
  contentWidth = 'comfortable',
  initialChapter,
  onCurrentChapterChange,
  onContextMenu,
  onClickAway,
  scrollRef,
  isTxt = false,
  highlights = [],
}: TextPagesViewProps) {
  const scrollContainerRef = React.useRef<HTMLDivElement>(null)
  const sectionRefs = React.useRef<Map<number, HTMLElement>>(new Map())
  const onCurrentChapterChangeRef = React.useRef(onCurrentChapterChange)
  React.useEffect(() => { onCurrentChapterChangeRef.current = onCurrentChapterChange }, [onCurrentChapterChange])

  const [pagedChapter, setPagedChapter] = React.useState<number>(() => {
    if (initialChapter !== undefined) return initialChapter
    return chapters[0]?.number ?? 1
  })

  const pagedInitDoneRef = React.useRef(false)
  React.useEffect(() => {
    if (mode !== 'paged' || pagedInitDoneRef.current || chapters.length === 0) return
    pagedInitDoneRef.current = true
    const target = initialChapter !== undefined ? initialChapter : chapters[0].number
    setPagedChapter(target)
  }, [chapters.length, mode, initialChapter])

  React.useEffect(() => {
    if (mode === 'paged') onCurrentChapterChangeRef.current?.(pagedChapter)
  }, [pagedChapter, mode])

  const initialScrollDoneRef = React.useRef(false)
  React.useEffect(() => {
    if (mode === 'paged' || initialScrollDoneRef.current || chapters.length === 0) return
    if (initialChapter === undefined) return
    initialScrollDoneRef.current = true
    requestAnimationFrame(() => {
      sectionRefs.current.get(initialChapter)?.scrollIntoView({ behavior: 'instant', block: 'start' })
    })
  }, [chapters.length, initialChapter, mode])

  // Viewport IntersectionObserver to track current chapter in scroll mode
  const viewportObserverRef = React.useRef<IntersectionObserver | null>(null)
  const viewportVisibleRef = React.useRef<Set<number>>(new Set())

  React.useEffect(() => {
    if (mode === 'paged') return
    const root = scrollContainerRef.current
    if (!root) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const num = Number((entry.target as HTMLElement).dataset.chapter)
          if (!num) continue
          if (entry.isIntersecting) {
            viewportVisibleRef.current.add(num)
          } else {
            viewportVisibleRef.current.delete(num)
          }
        }
        if (viewportVisibleRef.current.size > 0) {
          const top = Math.min(...viewportVisibleRef.current)
          onCurrentChapterChangeRef.current?.(top)
        }
      },
      { root, rootMargin: '0px', threshold: 0.01 }
    )
    viewportObserverRef.current = observer
    sectionRefs.current.forEach((el) => observer.observe(el))
    return () => {
      observer.disconnect()
      viewportObserverRef.current = null
    }
  }, [mode])

  const getSectionRef = React.useCallback((chapterNumber: number) => (el: HTMLElement | null) => {
    const observer = viewportObserverRef.current
    const prev = sectionRefs.current.get(chapterNumber)
    if (prev && prev !== el) observer?.unobserve(prev)
    if (el) {
      sectionRefs.current.set(chapterNumber, el)
      observer?.observe(el)
    } else {
      sectionRefs.current.delete(chapterNumber)
      viewportVisibleRef.current.delete(chapterNumber)
    }
  }, [])

  React.useImperativeHandle(
    scrollRef as React.MutableRefObject<TextPagesViewHandle | null> | undefined,
    () => ({
      scrollToChapter: (chapterNumber: number) => {
        if (mode === 'paged') {
          setPagedChapter(chapterNumber)
          return
        }
        sectionRefs.current.get(chapterNumber)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      },
    }),
    [mode]
  )

  const pagedIdx = chapters.findIndex((c) => c.number === pagedChapter)
  const canPrev = pagedIdx > 0
  const canNext = pagedIdx < chapters.length - 1

  const gotoPrev = React.useCallback(() => {
    setPagedChapter((cur) => {
      const idx = chapters.findIndex((c) => c.number === cur)
      return idx > 0 ? chapters[idx - 1].number : cur
    })
  }, [chapters])

  const gotoNext = React.useCallback(() => {
    setPagedChapter((cur) => {
      const idx = chapters.findIndex((c) => c.number === cur)
      return idx < chapters.length - 1 ? chapters[idx + 1].number : cur
    })
  }, [chapters])

  React.useEffect(() => {
    if (mode !== 'paged') return
    const handleKey = (e: KeyboardEvent) => {
      const active = document.activeElement
      if (
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active as HTMLElement)?.isContentEditable
      ) return
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); gotoPrev() }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); gotoNext() }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [mode, gotoPrev, gotoNext])

  React.useEffect(() => {
    if (mode === 'paged') scrollContainerRef.current?.scrollTo({ top: 0 })
  }, [pagedChapter, mode])

  const fontSize = `${Math.round(zoom * 100)}%`
  const contentWidthClass = contentWidth === 'full' ? '' : contentWidth === 'wide' ? 'max-w-5xl' : 'max-w-3xl'

  const renderContent = (chapterNumber: number) => {
    const doc = chapterDocs.find((d) => d.chapter_number === chapterNumber)
    const text = doc?.content ?? ''

    if (formatMode === 'markdown') {
      return (
        <div className="text-text-secondary leading-relaxed">
          <ReactMarkdown components={readerMarkdownComponents}>{text}</ReactMarkdown>
        </div>
      )
    }

    const marked = markTextByPosition(text, highlights, chapterNumber)

    if (isTxt) {
      return (
        <pre className="whitespace-pre-wrap font-mono text-text-secondary leading-relaxed break-words">
          {marked}
        </pre>
      )
    }
    return (
      <p className="text-text-secondary leading-relaxed whitespace-pre-wrap break-words">
        {marked}
      </p>
    )
  }

  if (mode === 'paged') {
    const chapter = chapters.find((c) => c.number === pagedChapter)
    return (
      <div
        className="flex-1 min-w-0 flex bg-surface-100 dark:bg-bg-inset"
        onContextMenu={onContextMenu}
        onClick={onClickAway}
      >
        <button
          onClick={(e) => { e.stopPropagation(); gotoPrev() }}
          disabled={!canPrev}
          className="flex items-center justify-center w-10 shrink-0 text-text-tertiary hover:text-text-primary hover:bg-surface-200 dark:hover:bg-surface-100 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
          aria-label="Previous chapter"
          title="Previous chapter (←)"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>

        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
          <div className={cn('mx-auto py-8 px-6', contentWidthClass)} style={{ fontSize }}>
            {chapter && (
              <>
                <h2 className="text-xl font-semibold text-text-primary mb-6">{chapter.title}</h2>
                {renderContent(chapter.number)}
              </>
            )}
            <div className="mt-8 text-center text-xs tabular-nums text-text-tertiary select-none">
              {pagedIdx + 1} / {chapters.length}
            </div>
          </div>
        </div>

        <button
          onClick={(e) => { e.stopPropagation(); gotoNext() }}
          disabled={!canNext}
          className="flex items-center justify-center w-10 shrink-0 text-text-tertiary hover:text-text-primary hover:bg-surface-200 dark:hover:bg-surface-100 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
          aria-label="Next chapter"
          title="Next chapter (→)"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      </div>
    )
  }

  return (
    <div
      ref={scrollContainerRef}
      className={cn(
        'flex-1 min-w-0 overflow-y-auto bg-surface-100 dark:bg-bg-inset'
      )}
      onContextMenu={onContextMenu}
      onClick={onClickAway}
    >
      <div className={cn('mx-auto py-8 px-6 flex flex-col gap-12', contentWidthClass)} style={{ fontSize }}>
        {chapters.map((ch) => (
          <section
            key={ch.number}
            ref={getSectionRef(ch.number)}
            data-chapter={ch.number}
          >
            <h2 className="text-xl font-semibold text-text-primary mb-6 pb-2 border-b border-surface-200 dark:border-surface-200">
              {ch.title}
            </h2>
            {renderContent(ch.number)}
          </section>
        ))}
      </div>
    </div>
  )
}
