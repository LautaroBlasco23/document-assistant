import * as React from 'react'
import { X, Sparkles, PanelLeft, PanelRight, BookOpen, MessageCircleQuestion, Maximize, Minimize, ZoomIn, ZoomOut } from 'lucide-react'
import ePub from 'epubjs'
import { client } from '../../services'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { cn } from '../../lib/cn'
import type { KnowledgeDocument, KnowledgeChapter } from '../../types/knowledge-tree'
import { ChatPanel, type ChatPanelHandle } from './ChatPanel'
import { usePendingContent, makePendingId } from '../../stores/pending-content-store'
import type { KnowledgeTreeQuestionType } from '../../types/api'
import { PdfPagesView, type PdfPagesViewHandle } from './PdfPagesView'
import { ResizeHandle } from './ResizeHandle'
import { useGenerationSettings } from '../../stores/generation-settings'

interface UnifiedDocumentReaderProps {
  doc: KnowledgeDocument
  treeId: string
  chapters: KnowledgeChapter[]
  onClose: () => void
}

export function UnifiedDocumentReader({ doc, treeId, chapters, onClose }: UnifiedDocumentReaderProps) {
  const [currentPage, setCurrentPage] = React.useState<number>(1)
  const [showLeft, setShowLeft] = React.useState(true)
  const [showRight, setShowRight] = React.useState(true)
  const [isFullscreen, setIsFullscreen] = React.useState(false)
  const [zoom, setZoom] = React.useState(1)
  const [contextMenu, setContextMenu] = React.useState<{ x: number; y: number; text: string } | null>(null)
  const epubContainerRef = React.useRef<HTMLDivElement>(null)
  const overlayRef = React.useRef<HTMLDivElement>(null)
  const pdfScrollRef = React.useRef<PdfPagesViewHandle | null>(null)
  const chatPanelRef = React.useRef<ChatPanelHandle | null>(null)
  const pendingAdd = usePendingContent((s) => s.add)
  const pendingUpdate = usePendingContent((s) => s.update)
  const pendingRemove = usePendingContent((s) => s.remove)
  const { settings: genSettings } = useGenerationSettings()

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

  const getContext = React.useCallback((): Promise<string> => {
    if (!activeChapter) return Promise.resolve('')
    const chDoc = chapterDocs.find((d) => d.chapter_number === activeChapter)
    return Promise.resolve(chDoc?.content ?? '')
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

  const openContentTab = () => {
    setShowRight(true)
    chatPanelRef.current?.showContent()
  }

  const handleMakeFlashcard = async () => {
    if (!contextMenu) return
    const chapter = activeChapter ?? 1
    const text = contextMenu.text
    const id = makePendingId()
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    pendingAdd({
      id,
      kind: 'flashcard',
      status: 'generating',
      chapter,
      front: '',
      back: '',
      sourceText: text,
    })
    openContentTab()
    try {
      const draft = await client.draftFlashcard(treeId, chapter, text, undefined, genSettings.agent_id)
      pendingUpdate(id, {
        status: 'ready',
        front: draft.front,
        back: draft.back,
        sourceText: draft.source_text,
      })
    } catch (e) {
      pendingUpdate(id, { status: 'error', error: (e as Error).message || 'Generation failed' })
      setTimeout(() => pendingRemove(id), 4000)
    }
  }

  const handleMakeQuestion = async (questionType: KnowledgeTreeQuestionType) => {
    if (!contextMenu) return
    const chapter = activeChapter ?? 1
    const text = contextMenu.text
    const id = makePendingId()
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    pendingAdd({
      id,
      kind: 'question',
      status: 'generating',
      chapter,
      questionType,
      questionData: {},
      sourceText: text,
    })
    openContentTab()
    try {
      const draft = await client.draftQuestion(treeId, chapter, questionType, text, undefined, genSettings.agent_id)
      pendingUpdate(id, { status: 'ready', questionData: draft.question_data })
    } catch (e) {
      pendingUpdate(id, { status: 'error', error: (e as Error).message || 'Generation failed' })
      setTimeout(() => pendingRemove(id), 4000)
    }
  }

  const handleAskDefinition = () => {
    if (!contextMenu) return
    const text = contextMenu.text
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    setShowRight(true)
    chatPanelRef.current?.askInChat(text)
  }

  const hideContextMenu = () => setContextMenu(null)

  const zoomIn = React.useCallback(() => setZoom((z) => Math.min(2, +(z + 0.1).toFixed(1))), [])
  const zoomOut = React.useCallback(() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(1))), [])

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isFullscreen])

  const renderChapterBanner = React.useCallback(
    (pageNumber: number) => {
      const chStart = chapterDocs.find((d) => d.page_start === pageNumber)
      if (!chStart) return null
      const title =
        chapters.find((c) => c.number === chStart.chapter_number)?.title ??
        `Chapter ${chStart.chapter_number}`
      return (
        <div className="w-full max-w-[800px] mb-2">
          <div className="bg-primary-light dark:bg-primary/12 border border-primary/20 dark:border-primary/30 rounded-lg px-4 py-2">
            <span className="text-xs font-semibold text-primary uppercase tracking-wide">
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
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm',
        isFullscreen ? 'p-0' : 'p-4'
      )}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose()
      }}
    >
      <div
        className={cn(
          'w-full h-full bg-surface dark:bg-surface flex flex-col overflow-hidden animate-fade-in',
          isFullscreen
            ? 'max-h-full max-w-full rounded-none shadow-none'
            : 'max-h-[95vh] max-w-[1600px] rounded-xl shadow-2xl'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-surface-200 dark:border-surface-200 shrink-0 bg-surface-100 dark:bg-surface-100">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-gray-800 dark:text-slate-200 truncate">{doc.title}</h2>
            {activeChapter !== null && (
              <span className="text-xs px-2 py-0.5 bg-primary-light dark:bg-primary/12 text-primary rounded-full shrink-0">
                {chapters.find((c) => c.number === activeChapter)?.title ?? `Chapter ${activeChapter}`}
              </span>
            )}
          </div>
          {/* Zoom controls */}
          {isPdf && (
            <div className="flex items-center gap-0.5 bg-surface dark:bg-surface-200 rounded-md shadow-sm border border-surface-200 dark:border-surface-200 px-1.5 py-0.5">
              <button
                onClick={zoomOut}
                disabled={zoom <= 0.5}
                className="p-0.5 rounded text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Zoom out"
                title="Zoom out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <span className="text-xs tabular-nums text-gray-500 dark:text-slate-400 min-w-[3ch] text-center select-none">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={zoomIn}
                disabled={zoom >= 2}
                className="p-0.5 rounded text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Zoom in"
                title="Zoom in"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          <div className="flex items-center gap-1 flex-1 justify-end">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 rounded-md transition-colors text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100"
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </button>
            {isPdf && (
              <button
                onClick={() => setShowLeft(!showLeft)}
                className={cn(
                  'p-1.5 rounded-md transition-colors',
                  showLeft
                    ? 'text-primary bg-primary-light hover:bg-primary-light dark:bg-primary/12 dark:hover:bg-primary/12'
                    : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100'
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
                    ? 'text-primary bg-primary-light hover:bg-primary-light dark:bg-primary/12 dark:hover:bg-primary/12'
                    : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100'
                )}
                aria-label="Toggle chat panel"
                title="Toggle chat & notes"
              >
                <PanelRight className="h-4 w-4" />
              </button>
              <button
                onClick={onClose}
                className="p-1.5 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 rounded-md transition-colors ml-2"
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
                  'border-r border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface-100 transition-all duration-300 ease-in-out overflow-hidden',
                  showLeft ? 'block' : 'hidden'
                )}
                style={{ width: showLeft ? leftWidth : 0 }}
              >
                <div className="h-full flex flex-col">
                  <div className="px-3 py-2 border-b border-surface-200 dark:border-surface-200">
                    <h3 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Chapters</h3>
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
                              ? 'bg-primary-light dark:bg-primary/12 text-primary font-medium'
                              : 'text-gray-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-surface-100'
                          )}
                        >
                          <BookOpen className="h-3.5 w-3.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="truncate">{ch.title}</div>
                            {chDoc?.page_start && (
                              <div className="text-xs text-gray-400 dark:text-slate-500">
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
              zoom={zoom}
              renderPageHeader={renderChapterBanner}
              onCurrentPageChange={setCurrentPage}
              onContextMenu={handleContextMenu}
              onClickAway={hideContextMenu}
              scrollRef={pdfScrollRef}
            />
          ) : (
            <div
              className="flex-1 min-w-0 bg-surface-100 dark:bg-surface overflow-auto flex flex-col items-center py-6 px-4 gap-8"
              onContextMenu={handleContextMenu}
              onClick={hideContextMenu}
            >
              <div
                ref={epubContainerRef}
                className="w-[800px] max-w-full h-[80vh] bg-surface dark:bg-surface-200 shadow-md rounded-sm"
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
              'border-l border-surface-200 dark:border-surface-200 transition-all duration-300 ease-in-out overflow-hidden',
              showRight ? 'block' : 'hidden'
            )}
            style={{ width: showRight ? rightWidth : 0 }}
          >
            <div className="h-full">
              <ChatPanel
                ref={chatPanelRef}
                getContext={getContext}
                storageKey={`${treeId}:${doc.id}:unified`}
                treeId={treeId}
                chapter={activeChapter}
              />
            </div>
          </div>
        </div>

        {/* Context menu */}
        {contextMenu && (
          <div
            className="fixed z-[60] bg-surface dark:bg-surface-200 rounded-lg shadow-lg border border-surface-200 dark:border-surface-200 py-1 min-w-[200px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-slate-500">
              Ask
            </div>
            <button
              onClick={handleAskDefinition}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <MessageCircleQuestion className="h-3.5 w-3.5 text-accent" />
              Ask definition in chat
            </button>
            <div className="my-1 border-t border-surface-200 dark:border-surface-200" />
            <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-slate-500">
              Generate
            </div>
            <button
              onClick={handleMakeFlashcard}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5 text-warning" />
              Flashcard
            </button>
            <button
              onClick={() => handleMakeQuestion('true_false')}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5 text-success" />
              True / False question
            </button>
            <button
              onClick={() => handleMakeQuestion('multiple_choice')}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Multiple choice question
            </button>
            <button
              onClick={() => handleMakeQuestion('checkbox')}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              Select all that apply
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
