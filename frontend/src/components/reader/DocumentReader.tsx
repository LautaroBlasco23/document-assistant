import * as React from 'react'
import { X, Sparkles, PanelLeft, PanelRight, MessageCircleQuestion, Maximize, Minimize, ZoomIn, ZoomOut } from 'lucide-react'
import ePub from 'epubjs'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import { extractPdfText } from '../../lib/pdf-text'
import type { KnowledgeDocument } from '../../types/knowledge-tree'
import { PageSidebar } from './PageSidebar'
import { ChatPanel, type ChatPanelHandle } from './ChatPanel'
import { PdfPagesView, type PdfPagesViewHandle } from './PdfPagesView'
import { ResizeHandle } from './ResizeHandle'
import { usePendingContent, makePendingId } from '../../stores/pending-content-store'
import { useGenerationSettings } from '../../stores/generation-settings'
import type { KnowledgeTreeQuestionType } from '../../types/api'

interface DocumentReaderProps {
  doc: KnowledgeDocument
  treeId: string
  chapter: number
  onClose: () => void
}

export function DocumentReader({ doc, treeId, chapter, onClose }: DocumentReaderProps) {
  const [numPages, setNumPages] = React.useState<number>(0)
  const [currentPage, setCurrentPage] = React.useState<number>(1)
  const [showLeft, setShowLeft] = React.useState(true)
  const [showRight, setShowRight] = React.useState(true)
  const [isFullscreen, setIsFullscreen] = React.useState(false)
  const [zoom, setZoom] = React.useState(1)
  const [pdfText, setPdfText] = React.useState<string>('')
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
    return 208
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

  const persistLeftWidth = React.useCallback((w: number) => {
    const clamped = Math.max(160, Math.min(500, w))
    setLeftWidth(clamped)
    try { localStorage.setItem('docassist_panel_width:left', String(clamped)) } catch { /* ignore */ }
  }, [])

  const persistRightWidth = React.useCallback((w: number) => {
    const clamped = Math.max(200, Math.min(800, w))
    setRightWidth(clamped)
    try { localStorage.setItem('docassist_panel_width:right', String(clamped)) } catch { /* ignore */ }
  }, [])

  const isPdf = doc.source_file_name?.toLowerCase().endsWith('.pdf') || doc.source_file_path?.toLowerCase().endsWith('.pdf')
  const fileUrl = client.getDocumentFileUrl(treeId, doc.id)

  // Extract PDF text for chat context
  React.useEffect(() => {
    if (!isPdf) return
    extractPdfText(fileUrl)
      .then(setPdfText)
      .catch(() => setPdfText(''))
  }, [fileUrl, isPdf])

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
          'w-full h-full bg-white dark:bg-slate-900 flex flex-col overflow-hidden animate-fade-in',
          isFullscreen
            ? 'max-h-full max-w-full rounded-none shadow-none'
            : 'max-h-[95vh] max-w-[1600px] rounded-xl shadow-2xl'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-surface-200 dark:border-surface-200 shrink-0 bg-surface-100 dark:bg-surface-200">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 truncate">{doc.title}</h2>
          </div>
          {/* Zoom controls */}
          {isPdf && (
            <div className="flex items-center gap-0.5 bg-white dark:bg-surface rounded-md shadow-sm border border-surface-200 dark:border-surface-200 px-1.5 py-0.5">
              <button
                onClick={zoomOut}
                disabled={zoom <= 0.5}
                className="p-0.5 rounded text-surface-100 hover:text-surface-200 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Zoom out"
                title="Zoom out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <span className="text-xs tabular-nums text-surface-100 dark:text-surface-100 min-w-[3ch] text-center select-none">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={zoomIn}
                disabled={zoom >= 2}
                className="p-0.5 rounded text-surface-100 hover:text-surface-200 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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
              className="p-1.5 rounded-md transition-colors text-surface-100 hover:text-surface-200 hover:bg-surface-100 dark:text-surface-100 dark:hover:text-surface-200 dark:hover:bg-surface-100"
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
                    : 'text-surface-100 hover:text-surface-200 hover:bg-surface-100 dark:text-surface-100 dark:hover:text-surface-200 dark:hover:bg-surface-100'
                )}
                aria-label="Toggle page sidebar"
                title="Toggle page sidebar"
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
                  : 'text-surface-100 hover:text-surface-200 hover:bg-surface-100'
              )}
              aria-label="Toggle chat panel"
              title="Toggle chat & notes"
            >
              <PanelRight className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-surface-100 hover:text-surface-200 hover:bg-surface-100 dark:text-surface-100 dark:hover:text-surface-200 dark:hover:bg-surface-100 rounded-md transition-colors ml-2"
              aria-label="Close reader"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 min-h-0 flex">
          {/* Left panel: Page sidebar */}
          {isPdf && (
            <>
              <div
                className={cn(
                  'border-r border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface-100 transition-all duration-300 ease-in-out overflow-hidden',
                  showLeft ? 'block' : 'hidden'
                )}
                style={{ width: showLeft ? leftWidth : 0 }}
              >
                <div className="h-full">
                  <PageSidebar
                    numPages={numPages}
                    currentPage={currentPage}
                    onPageClick={scrollToPage}
                  />
                </div>
              </div>
              {showLeft && (
                <ResizeHandle
                  onResizeStart={() => { startLeftWidthRef.current = leftWidth }}
                  onResize={(delta) => persistLeftWidth(startLeftWidthRef.current + delta)}
                />
              )}
            </>
          )}

          {/* Center: Document content */}
          {isPdf ? (
            <PdfPagesView
              fileUrl={fileUrl}
              zoom={zoom}
              onCurrentPageChange={setCurrentPage}
              onNumPagesChange={setNumPages}
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
                className="w-[800px] max-w-full h-[80vh] bg-white dark:bg-surface shadow-md rounded-sm"
              />
            </div>
          )}

          {/* Right panel: Chat & Notes */}
          {showRight && (
            <ResizeHandle
              onResizeStart={() => { startRightWidthRef.current = rightWidth }}
              onResize={(delta) => persistRightWidth(startRightWidthRef.current - delta)}
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
                documentContext={pdfText}
                storageKey={`${treeId}:${doc.id}`}
                treeId={treeId}
                chapter={chapter}
              />
            </div>
          </div>
        </div>

        {/* Context menu */}
        {contextMenu && (
          <div
            className="fixed z-[60] bg-white dark:bg-surface rounded-lg shadow-lg border border-surface-200 dark:border-surface-200 py-1 min-w-[200px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-surface-100 dark:text-surface-100">
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
            <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-surface-100 dark:text-surface-100">
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
          </div>
        )}
      </div>
    </div>
  )
}
