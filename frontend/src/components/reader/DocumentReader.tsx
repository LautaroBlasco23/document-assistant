import * as React from 'react'
import { X, Sparkles } from 'lucide-react'
import { Document, Page } from 'react-pdf'
import ePub from 'epubjs'
import { client } from '../../services'
import type { KnowledgeDocument } from '../../types/knowledge-tree'

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
  const [flashcardStatus, setFlashcardStatus] = React.useState<FlashcardStatus>('idle')
  const [contextMenu, setContextMenu] = React.useState<{ x: number; y: number; text: string } | null>(null)
  const epubContainerRef = React.useRef<HTMLDivElement>(null)
  const readerRef = React.useRef<HTMLDivElement>(null)

  const isPdf = doc.source_file_name?.toLowerCase().endsWith('.pdf') || doc.source_file_path?.toLowerCase().endsWith('.pdf')

  const fileUrl = client.getDocumentFileUrl(treeId, doc.id)

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

  const handleContextMenu = (e: React.MouseEvent) => {
    const selection = window.getSelection()
    const selectedText = selection?.toString()?.trim() ?? ''
    if (!selectedText) {
      // Allow default browser context menu if no text selected
      return
    }
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
      // Reset status after a few seconds
      setTimeout(() => setFlashcardStatus('idle'), 3000)
    } catch {
      setFlashcardStatus('idle')
    }
  }

  const hideContextMenu = () => setContextMenu(null)

  return (
    <div
      ref={readerRef}
      className="fixed inset-0 z-50 flex flex-col bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === readerRef.current) onClose()
      }}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200 shrink-0">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-gray-800 truncate">{doc.title}</h2>
          {flashcardStatus === 'sending' && (
            <span className="text-xs text-indigo-600">Generating flashcard...</span>
          )}
          {flashcardStatus === 'sent' && (
            <span className="text-xs text-green-600">Flashcard generation started!</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
          aria-label="Close reader"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Content */}
      <div
        className="flex-1 min-h-0 bg-gray-100 overflow-auto flex flex-col items-center py-6 px-4 gap-8"
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
            {Array.from({ length: numPages }, (_, i) => (
              <div key={i + 1} className="flex flex-col items-center">
                <div className="bg-white shadow-md overflow-hidden">
                  <Page
                    pageNumber={i + 1}
                    width={Math.min(800, window.innerWidth - 48)}
                    renderAnnotationLayer
                    renderTextLayer
                  />
                </div>
                <span className="mt-2 text-xs text-gray-400 select-none">
                  {i + 1} / {numPages}
                </span>
              </div>
            ))}
          </Document>
        ) : (
          <div
            ref={epubContainerRef}
            className="w-[800px] max-w-full h-[80vh] bg-white shadow-md rounded-sm"
          />
        )}
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
  )
}
