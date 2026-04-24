import * as React from 'react'
import { X, Sparkles, PanelLeft, PanelRight } from 'lucide-react'
import { Document, Page } from 'react-pdf'
import ePub from 'epubjs'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import { extractPdfText } from '../../lib/pdf-text'
import type { KnowledgeDocument } from '../../types/knowledge-tree'
import { PageSidebar } from './PageSidebar'
import { ChatPanel } from './ChatPanel'

import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

interface DocumentReaderProps {
  doc: KnowledgeDocument
  treeId: string
  chapter: number
  onClose: () => void
}

type FlashcardStatus = 'idle' | 'sending' | 'sent'

export function DocumentReader({ doc, treeId, chapter, onClose }: DocumentReaderProps) {
  const [numPages, setNumPages] = React.useState<number>(0)
  const [currentPage, setCurrentPage] = React.useState<number>(1)
  const [showLeft, setShowLeft] = React.useState(true)
  const [showRight, setShowRight] = React.useState(true)
  const [pdfText, setPdfText] = React.useState<string>('')
  const [flashcardStatus, setFlashcardStatus] = React.useState<FlashcardStatus>('idle')
  const [contextMenu, setContextMenu] = React.useState<{ x: number; y: number; text: string } | null>(null)
  const epubContainerRef = React.useRef<HTMLDivElement>(null)
  const overlayRef = React.useRef<HTMLDivElement>(null)
  const pageRefs = React.useRef<Map<number, HTMLDivElement>>(new Map())

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

  // IntersectionObserver to track current page
  React.useEffect(() => {
    if (!isPdf || numPages === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.intersectionRatio - b.intersectionRatio)
        if (visible.length > 0) {
          const pageEl = visible[visible.length - 1].target
          const pageNum = Number(pageEl.getAttribute('data-page'))
          if (pageNum) setCurrentPage(pageNum)
        }
      },
      { root: null, threshold: [0, 0.25, 0.5, 0.75, 1] }
    )

    pageRefs.current.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [isPdf, numPages])

  const scrollToPage = (pageNumber: number) => {
    const el = pageRefs.current.get(pageNumber)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
          {/* Left panel: Page sidebar */}
          {isPdf && (
            <div
              className={cn(
                'border-r border-gray-200 bg-gray-50/50 transition-all duration-300 ease-in-out overflow-hidden',
                showLeft ? 'w-52' : 'w-0 border-r-0'
              )}
            >
              <div className="w-52 h-full">
                <PageSidebar
                  numPages={numPages}
                  currentPage={currentPage}
                  onPageClick={scrollToPage}
                />
              </div>
            </div>
          )}

          {/* Center: Document content */}
          <div
            className="flex-1 min-w-0 bg-gray-100 overflow-auto flex flex-col items-center py-6 px-4 gap-8"
            onContextMenu={handleContextMenu}
            onClick={hideContextMenu}
          >
            {isPdf ? (
              <Document
                file={fileUrl}
                onLoadSuccess={({ numPages }) => setNumPages(numPages)}
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
                {Array.from({ length: numPages }, (_, i) => {
                  const pageNumber = i + 1
                  return (
                    <div
                      key={pageNumber}
                      ref={(el) => {
                        if (el) pageRefs.current.set(pageNumber, el)
                        else pageRefs.current.delete(pageNumber)
                      }}
                      data-page={pageNumber}
                      className="flex flex-col items-center"
                    >
                      <div className="bg-white shadow-md overflow-hidden">
                        <Page
                          pageNumber={pageNumber}
                          width={Math.min(800, window.innerWidth - 400)}
                          renderAnnotationLayer
                          renderTextLayer
                        />
                      </div>
                      <span className="mt-2 text-xs text-gray-400 select-none">
                        {pageNumber} / {numPages}
                      </span>
                    </div>
                  )
                })}
              </Document>
            ) : (
              <div
                ref={epubContainerRef}
                className="w-[800px] max-w-full h-[80vh] bg-white shadow-md rounded-sm"
              />
            )}
          </div>

          {/* Right panel: Chat & Notes */}
          <div
            className={cn(
              'border-l border-gray-200 transition-all duration-300 ease-in-out overflow-hidden',
              showRight ? 'w-80' : 'w-0 border-l-0'
            )}
          >
            <div className="w-80 h-full">
              <ChatPanel documentContext={pdfText} storageKey={`${treeId}:${doc.id}`} />
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
