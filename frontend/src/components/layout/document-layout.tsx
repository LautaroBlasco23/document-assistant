import * as React from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2, Eye, BookOpen, Pencil } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Select } from '../ui/select'
import { cn } from '../../lib/cn'
import type { ChapterOut, DocumentOut, DocumentStructureOut } from '../../types/api'
import type { Tab } from '../../types/domain'
import { useDocumentStore } from '../../stores/document-store'
import { useExamStore } from '../../stores/exam-store'
import { PdfViewer, EpubViewer } from '../document-viewer'
import { client } from '../../services'
import { ChapterEditorDialog } from '../dialogs/chapter-editor-dialog'
import { DocumentEditorDialog } from '../dialogs/document-editor-dialog'

const DESCRIPTION_MAX_LENGTH = 500

export interface DocumentLayoutProps {
  document: DocumentOut
  structure: DocumentStructureOut | null
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  selectedChapter: number
  onChapterChange: (chapter: number) => void
  children: React.ReactNode
  className?: string
  onChapterRemoved?: (removedChapterNumber: number) => void
  onEditSave?: () => void
  canEdit?: boolean
}

const TAB_LABELS: Record<Tab, string> = {
  flashcards: 'Flashcards',
  summary: 'Summary',
  exam: 'Exam',
}

const LEVEL_SUFFIXES: Record<number, string> = {
  1: ' [Completed]',
  2: ' [Gold]',
  3: ' [Platinum]',
}


export function DocumentLayout({
  document,
  structure,
  activeTab,
  onTabChange,
  selectedChapter,
  onChapterChange,
  children,
  className,
  onChapterRemoved,
  onEditSave,
  canEdit = true,
}: DocumentLayoutProps) {
  const navigate = useNavigate()

  const chapterCount = structure?.num_chapters ?? document.num_chapters

  const metadataCache = useDocumentStore((s) => s.metadataCache)
  const fetchMetadata = useDocumentStore((s) => s.fetchMetadata)
  const saveMetadataAction = useDocumentStore((s) => s.saveMetadata)
  const removeChapter = useDocumentStore((s) => s.removeChapter)
  const [removingChapter, setRemovingChapter] = useState(false)

  const docHash = document.file_hash
  const [localDescription, setLocalDescription] = useState('')
  const [metadataLoaded, setMetadataLoaded] = useState(false)

  const chapterStatus = useExamStore((s) => s.chapterStatus)
  const fetchChapterStatus = useExamStore((s) => s.fetchChapterStatus)

  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerMode, setViewerMode] = useState<'full' | 'chapter'>('full')

  const [chapterEditorOpen, setChapterEditorOpen] = useState(false)
  const [documentEditorOpen, setDocumentEditorOpen] = useState(false)

  // Fetch metadata on mount or when document changes
  useEffect(() => {
    setMetadataLoaded(false)
    void fetchMetadata(docHash).then(() => setMetadataLoaded(true))
  }, [docHash, fetchMetadata])

  // Fetch exam status for all chapters when document changes
  useEffect(() => {
    void fetchChapterStatus(docHash)
  }, [docHash, fetchChapterStatus])

  // Sync local state from cache after fetch completes
  useEffect(() => {
    if (metadataLoaded && metadataCache[docHash] !== undefined) {
      setLocalDescription(metadataCache[docHash].description)
    }
  }, [metadataLoaded, docHash, metadataCache])

  const handleBlur = () => {
    const cached = metadataCache[docHash]?.description ?? ''
    if (localDescription !== cached) {
      void saveMetadataAction(docHash, localDescription)
    }
  }

  // Build chapter list: use structure if available, else synthesize from count
  const chapters: ChapterOut[] = structure?.chapters ?? Array.from(
    { length: document.num_chapters },
    (_, i) => ({ number: i + 1, chapter_index: i, title: undefined, num_chunks: 0, sections: [] }),
  )

  const selectedChapterObj = chapters.find((ch) => ch.number === selectedChapter)

  const handleRemoveChapter = async () => {
    if (!selectedChapterObj) return
    const prefix = `Chapter ${selectedChapterObj.number}`
    const title = selectedChapterObj.title?.startsWith(prefix)
      ? selectedChapterObj.title.slice(prefix.length).trim()
      : selectedChapterObj.title
    const displayName = title || prefix
    const confirmed = window.confirm(
      `Remove "${displayName}"? This will delete its summary, flashcards, and all indexed content. This cannot be undone.`
    )
    if (!confirmed) return
    setRemovingChapter(true)
    try {
      await removeChapter(docHash, selectedChapter)
      // Navigate to first remaining chapter
      if (onChapterRemoved) {
        onChapterRemoved(selectedChapter)
      }
    } finally {
      setRemovingChapter(false)
    }
  }

  const metadata = metadataCache[docHash]
  const fileExtension = metadata?.file_extension || ''
  const canViewFile = fileExtension === 'pdf' || fileExtension === 'epub'
  const canEditDocument = canEdit && (fileExtension === 'txt' || fileExtension === 'text')

  const handleViewFile = () => {
    setViewerMode('full')
    setViewerOpen(true)
  }

  const handleViewChapter = () => {
    setViewerMode('chapter')
    setViewerOpen(true)
  }

  const selectedChapterSections = selectedChapterObj?.sections || []
  const chapterPageStart = selectedChapterSections.length > 0 ? selectedChapterSections[0].page_start : 1
  const chapterPageEnd = selectedChapterSections.length > 0 ? selectedChapterSections[selectedChapterSections.length - 1].page_end : 1

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Document header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/')}
          className="shrink-0"
          aria-label="Back to library"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-900 truncate">
            {document.filename}
          </h1>
        </div>
        {canEditDocument && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDocumentEditorOpen(true)}
            aria-label="Edit document"
            className="shrink-0 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <Pencil className="h-4 w-4" />
          </Button>
        )}
        <Badge variant="neutral" className="shrink-0">
          {chapterCount} {chapterCount === 1 ? 'chapter' : 'chapters'}
        </Badge>
      </div>

      {/* Document context input */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <label
            htmlFor="doc-context"
            className="text-xs font-medium text-gray-500"
          >
            Document context
          </label>
          {canViewFile && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleViewFile}
              className="h-6 px-2 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50"
            >
              <Eye className="h-3 w-3 mr-1" />
              View file
            </Button>
          )}
        </div>
        <textarea
          id="doc-context"
          className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
          rows={2}
          maxLength={DESCRIPTION_MAX_LENGTH}
          placeholder="Describe this document (e.g., 'Machine learning textbook for beginners')..."
          value={localDescription}
          onChange={(e) => setLocalDescription(e.target.value)}
          onBlur={handleBlur}
        />
        <p className="text-xs text-gray-400 flex justify-between">
          <span>This description is sent to the AI to improve generated summaries and flashcards.</span>
          <span className={localDescription.length >= DESCRIPTION_MAX_LENGTH ? 'text-red-400' : ''}>
            {localDescription.length}/{DESCRIPTION_MAX_LENGTH}
          </span>
        </p>
      </div>

      {/* Chapter selector dropdown with remove button */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Select
            label="Chapter"
            value={selectedChapter}
            onChange={(e) => onChapterChange(Number(e.target.value))}
          >
            {chapters.map((ch) => {
              const prefix = `Chapter ${ch.number}`
              const title = ch.title?.startsWith(prefix) ? ch.title.slice(prefix.length).trim() : ch.title
              const statusKey = `${docHash}-${ch.number}`
              const level = chapterStatus[statusKey]?.level ?? 0
              const levelSuffix = LEVEL_SUFFIXES[level] ?? ''
              return (
                <option key={ch.number} value={ch.number}>
                  {(title || prefix) + levelSuffix}
                </option>
              )
            })}
          </Select>
        </div>
        {canEditDocument && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setChapterEditorOpen(true)}
            aria-label="Edit chapter"
            className="shrink-0 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <Pencil className="h-4 w-4" />
          </Button>
        )}
        {chapters.length > 1 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { void handleRemoveChapter() }}
            disabled={removingChapter}
            aria-label="Remove chapter"
            className="shrink-0 text-gray-400 hover:text-red-500 hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
      {fileExtension === 'pdf' && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleViewChapter}
          className="text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 -mt-2"
        >
          <BookOpen className="h-3 w-3 mr-1" />
          {`View chapter pages (p. ${chapterPageStart}${chapterPageEnd !== chapterPageStart ? `-${chapterPageEnd}` : ''})`}
        </Button>
      )}

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => onTabChange(v as Tab)}
      >
        <TabsList>
          {(Object.keys(TAB_LABELS) as Tab[]).map((tab) => (
            <TabsTrigger key={tab} value={tab}>
              {TAB_LABELS[tab]}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* Render all tab content slots; the active one is shown by Radix */}
        {(Object.keys(TAB_LABELS) as Tab[]).map((tab) => (
          <TabsContent key={tab} value={tab}>
            {activeTab === tab ? children : null}
          </TabsContent>
        ))}
      </Tabs>

      {/* Document viewer modal */}
      {viewerOpen && canViewFile && (
        fileExtension === 'pdf' ? (
          <PdfViewer
            fileUrl={viewerMode === 'chapter' && selectedChapterObj?.sections?.length
              ? client.getChapterPdfUrl(docHash, selectedChapter)
              : client.getDocumentFileUrl(docHash)}
            filename={viewerMode === 'chapter' && selectedChapterObj?.sections?.length
              ? `${selectedChapterObj.title || `Chapter ${selectedChapter}`}.pdf`
              : document.filename}
            onClose={() => setViewerOpen(false)}
          />
        ) : (
          <EpubViewer
            fileUrl={client.getDocumentFileUrl(docHash)}
            filename={document.filename}
            onClose={() => setViewerOpen(false)}
            initialChapterHref={viewerMode === 'chapter' ? (selectedChapterObj?.toc_href || undefined) : undefined}
            initialChapterIndex={viewerMode === 'chapter' ? (selectedChapter - 1) : undefined}
          />
        )
      )}

      {/* Chapter editor dialog */}
      <ChapterEditorDialog
        open={chapterEditorOpen}
        onClose={() => setChapterEditorOpen(false)}
        docHash={docHash}
        chapterNumber={selectedChapter}
        totalChapters={chapterCount}
        onSave={onEditSave}
      />

      {/* Document editor dialog */}
      <DocumentEditorDialog
        open={documentEditorOpen}
        onClose={() => setDocumentEditorOpen(false)}
        docHash={docHash}
        initialTitle={document.filename}
        onSave={onEditSave}
      />
    </div>
  )
}
