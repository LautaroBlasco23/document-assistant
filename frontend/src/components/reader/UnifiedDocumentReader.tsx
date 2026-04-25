import * as React from 'react'
import { X, Sparkles, PanelLeft, PanelRight, BookOpen } from 'lucide-react'
import ePub from 'epubjs'
import { client } from '../../services'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { cn } from '../../lib/cn'
import type { KnowledgeDocument, KnowledgeChapter } from '../../types/knowledge-tree'
import { ChatPanel } from './ChatPanel'
import { PdfPagesView, type PdfPagesViewHandle } from './PdfPagesView'
import { ResizeHandle } from './ResizeHandle'

interface UnifiedDocumentReaderProps {
  doc: KnowledgeDocument
  treeId: string
  chapters: KnowledgeChapter[]
  onClose: () => void
}

type FlashcardStatus = 'idle' | 'sending' | 'sent'

export function UnifiedDocumentReader({ doc, treeId, chapters, onClose }: UnifiedDocumentReaderProps) {
  const [currentPage, setCurrentPage] = React.useState<number>(1)
  const [showLeft, setShowLeft] = React.useState(true)
  const [showRight, setShowRight] = React.useState(true)
  const [flashcardStatus, setFlashcardStatus] = React.useState<FlashcardStatus>('idle')
  const [contextMenu, setContextMenu] = React.useState<{ x: number; y: number; text: string } | null>(null)
  const epubContainerRef = React.useRef<HTMLDivElement>(null)
  const overlayRef = React.useRef<HTMLDivElement>(null)
  const pdfScrollRef = React.useRef<PdfPagesViewHandle | null>(null)

  const [leftWidth, setLeftWidth] = React.useState(() => {
    try {
      const saved = localStorage.getItem('docassist_panel_width:left')
      if (saved) return Math.max(160, Math.min(500, parseInt(saved, 10)))
    } catch { /* ignore */ }
    return 224
  })
  const [rightWidth, setRightWidth] = React.useState(() => {
    try {
      const saved = localStorage.getItem('docassist_panel_width:right')
      if (saved) return Math.max(200, Math.min(800, parseInt(saved, 10)))
    } catch { /* ignore */ }
    return 320
  })

  const startLeftWidthRef = React.useRef(leftWidth)
  const startRightWidthRef = React.useRef(rightWidth)

  const applyLeftWidth = React.useCallback((w: number) => {
    setLeftWidth(Math.max(160, Math.min(500, w)))
  }, [])

  const saveLeftWidth = React.useCallback(() => {
    try { localStorage.setItem('docassist_panel_width:left', String(leftWidth)) } catch { /* ignore */ }
  }, [leftWidth])

  const applyRightWidth = React.useCallback((w: number) => {
    setRightWidth(Math.max(200, Math.min(800, w)))
  }, [])

  const saveRightWidth = React.useCallback(() => {
    try { localStorage.setItem('docassist_panel_width:right', String(rightWidth)) } catch { /* ignore */ }
  }, [rightWidth])

  const isPdf = doc.source_file_name?.toLowerCase().endsWith('.pdf') || doc.source_file_path?.toLowerCase().endsWith('.pdf')
  const fileUrl = client.getDocumentFileUrl(treeId, doc.id)

  // Read already-fetched documents from store (AllDocumentsTab fetched them)
  const allDocs = useKnowledgeTreeStore((s) => s.documents[`${treeId}:all`] ?? [])
  const chapterDocs = React.useMemo(() => {
    return allDocs
      .filter((d) => d.chapter_number !== null && d.page_start != null && d.page_end != null)
      .sort((a, b) => (a.chapter_number ?? 0) - (b.chapter_number ?? 0))
  }, [allDocs])

  // Visible pages: only pages that belong to any chapter's page range
  const visiblePages = React.useMemo(() => {
    if (!isPdf || chapterDocs.length === 0) return null
    const pages: number[] = []
    const sorted = [...chapterDocs].sort((a, b) => (a.page_start ?? 0) - (b.page_start ?? 0))
    for (const chDoc of sorted) {
      if (chDoc.page_start && chDoc.page_end) {
        for (let p = chDoc.page_start; p <= chDoc.page_end; p++) {
          pages.push(p)
        }
      }
    }
    return pages.length > 0 ? pages : null
  }, [chapterDocs, isPdf])

  // Compute active chapter from current page
  const activeChapter = React.useMemo(() => {
    if (!isPdf || !currentPage) return null
    const chDoc = chapterDocs.find(
      (d) => d.page_start && d.page_end && currentPage >= d.page_start && currentPage <= d.page_end
    )
    if (chDoc) return chDoc.chapter_number
    if (chapterDocs.length > 0 && currentPage < (chapterDocs[0].page_start ?? 0)) {
      return chapterDocs[0].chapter_number
    }
    if (chapterDocs.length > 0 && currentPage > (chapterDocs[chapterDocs.length - 1].page_end ?? 0)) {
      return chapterDocs[chapterDocs.length - 1].chapter_number
    }
    return null
  }, [currentPage, chapterDocs, isPdf])

  // Chat context = active chapter's content
  const activeChapterContent = React.useMemo(() => {
    if (!activeChapter) return ''
    const chDoc = chapterDocs.find((d) => d.chapter_number === activeChapter)
    return chDoc?.content ?? ''
  }, [activeChapter, chapterDocs])

  // EPUB rendering
  React.useEffect(() => {
    if (isPdf || !epubContainerRef.current) return

    const book = ePub(fileUrl)
    const rendition = book.renderTo(epubContainerRef.current, {
      width: '100%',
      height: '100%',
    })
    rendition.display()

    return () => {
      rendition.destroy()
      book.destroy()
    }
  }, [fileUrl, isPdf])

  const scrollToPage = (pageNumber: number) => {
    pdfScrollRef.current?.scrollToPage(pageNumber)
  }

  const scrollToChapter = (chapterNumber: number) => {
    const chDoc = chapterDocs.find((d) => d.chapter_number === chapterNumber)
    if (chDoc?.page_start) {
      scrollToPage(chDoc.page_start)
    }
  }

  const handleContextMenu = (e: React.MouseEvent) => {
    const selection = window.getSelection()
    const selectedText = selection?.toString()?.trim() ?? ''
    if (!selectedText) return
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, text: selectedText })
  }

  const handleMakeFlashcard = async () => {
    if (!contextMenu) return
    const chapter = activeChapter ?? 1
    setContextMenu(null)
    setFlashcardStatus('sending')
    try {
      await client.generateFlashcardFromSelection(treeId, chapter, contextMenu.text)
      setFlashcardStatus('sent')
      window.getSelection()?.removeAllRanges()
      setTimeout(() => setFlashcardStatus('idle'), 3000)
    } catch {
      setFlashcardStatus('idle')
    }
  }

  const hideContextMenu = () => setContextMenu(null)

  const renderChapterBanner = React.useCallback(
    (pageNumber: number) => {
      const chStart = chapterDocs.find((d) => d.page_start === pageNumber)
      if (!chStart) return null
      const title =
        chapters.find((c) => c.number === chStart.chapter_number)?.title ??
        `Chapter ${chStart.chapter_number}`
      return (
        <div className="w-full max-w-[800px] mb-2">
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
            <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
              {title}
            </span>
          </div>
        </div>
      )
    },
    [chapterDocs, chapters]
  )

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose()
      }}
    >
      <div
        className="w-full h-full max-h-[95vh] max-w-[1600px] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 shrink-0 bg-gray-50/80">
          <div className="flex items-center gap-3 min-w-0">
            <h2 className="text-sm font-semibold text-gray-800 truncate">{doc.title}</h2>
            {activeChapter !== null && (
              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full shrink-0">
                {chapters.find((c) => c.number === activeChapter)?.title ?? `Chapter ${activeChapter}`}
              </span>
            )}
            {flashcardStatus === 'sending' && (
              <span className="text-xs text-indigo-600 animate-pulse">Generating flashcard...</span>
            )}
            {flashcardStatus === 'sent' && (
              <span className="text-xs text-green-600">Flashcard generation started!</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {isPdf && (
              <button
                onClick={() => setShowLeft(!showLeft)}
                className={cn(
                  'p-1.5 rounded-md transition-colors',
                  showLeft
                    ? 'text-blue-600 bg-blue-50 hover:bg-blue-100'
                    : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
                )}
                aria-label="Toggle chapter sidebar"
                title="Toggle chapter sidebar"
              >
                <PanelLeft className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={() => setShowRight(!showRight)}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                showRight
                  ? 'text-blue-600 bg-blue-50 hover:bg-blue-100'
                  : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
              )}
              aria-label="Toggle chat panel"
              title="Toggle chat & notes"
            >
              <PanelRight className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors ml-2"
              aria-label="Close reader"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 min-h-0 flex">
          {/* Left panel: Chapter sidebar */}
          {isPdf && (
            <>
              <div
                className={cn(
                  'border-r border-gray-200 bg-gray-50/50 transition-all duration-300 ease-in-out overflow-hidden',
                  showLeft ? 'block' : 'hidden'
                )}
                style={{ width: showLeft ? leftWidth : 0 }}
              >
                <div className="h-full flex flex-col">
                  <div className="px-3 py-2 border-b border-gray-200">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Chapters</h3>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    {chapters.map((ch) => {
                      const isActive = activeChapter === ch.number
                      const chDoc = chapterDocs.find((d) => d.chapter_number === ch.number)
                      return (
                        <button
                          key={ch.number}
                          onClick={() => scrollToChapter(ch.number)}
                          className={cn(
                            'w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2',
                            isActive
                              ? 'bg-blue-50 text-blue-700 font-medium'
                              : 'text-gray-600 hover:bg-gray-100'
                          )}
                        >
                          <BookOpen className="h-3.5 w-3.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="truncate">{ch.title}</div>
                            {chDoc?.page_start && (
                              <div className="text-xs text-gray-400">
                                Page {chDoc.page_start}
                                {chDoc.page_end && chDoc.page_end !== chDoc.page_start
                                  ? ` - ${chDoc.page_end}`
                                  : ''}
                              </div>
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
              {showLeft && (
                <ResizeHandle
                  onResizeStart={() => { startLeftWidthRef.current = leftWidth }}
                  onResize={(delta) => applyLeftWidth(startLeftWidthRef.current + delta)}
                  onResizeEnd={saveLeftWidth}
                />
              )}
            </>
          )}

          {/* Center: Document content */}
          {isPdf ? (
            <PdfPagesView
              fileUrl={fileUrl}
              visiblePages={visiblePages}
              renderPageHeader={renderChapterBanner}
              onCurrentPageChange={setCurrentPage}
              onContextMenu={handleContextMenu}
              onClickAway={hideContextMenu}
              scrollRef={pdfScrollRef}
            />
          ) : (
            <div
              className="flex-1 min-w-0 bg-gray-100 overflow-auto flex flex-col items-center py-6 px-4 gap-8"
              onContextMenu={handleContextMenu}
              onClick={hideContextMenu}
            >
              <div
                ref={epubContainerRef}
                className="w-[800px] max-w-full h-[80vh] bg-white shadow-md rounded-sm"
              />
            </div>
          )}

          {/* Right panel: Chat & Notes */}
          {showRight && (
            <ResizeHandle
              onResizeStart={() => { startRightWidthRef.current = rightWidth }}
              onResize={(delta) => applyRightWidth(startRightWidthRef.current - delta)}
              onResizeEnd={saveRightWidth}
            />
          )}
          <div
            className={cn(
              'border-l border-gray-200 transition-all duration-300 ease-in-out overflow-hidden',
              showRight ? 'block' : 'hidden'
            )}
            style={{ width: showRight ? rightWidth : 0 }}
          >
            <div className="h-full">
              <ChatPanel
                documentContext={activeChapterContent}
                storageKey={`${treeId}:${doc.id}:unified`}
              />
            </div>
          </div>
        </div>

        {/* Context menu */}
        {contextMenu && (
          <div
            className="fixed z-[60] bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[180px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button
              onClick={handleMakeFlashcard}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-500" />
              Make a flashcard
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
