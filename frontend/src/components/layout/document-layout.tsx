import * as React from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Select } from '../ui/select'
import { cn } from '../../lib/cn'
import type { ChapterOut, DocumentOut, DocumentStructureOut } from '../../types/api'
import type { Tab } from '../../types/domain'
import { useDocumentStore } from '../../stores/document-store'

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
}

const TAB_LABELS: Record<Tab, string> = {
  flashcards: 'Flashcards',
  summary: 'Summary',
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

  // Fetch metadata on mount or when document changes
  useEffect(() => {
    setMetadataLoaded(false)
    void fetchMetadata(docHash).then(() => setMetadataLoaded(true))
  }, [docHash, fetchMetadata])

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
    (_, i) => ({ number: i + 1, title: undefined, num_chunks: 0, sections: [] }),
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
        <Badge variant="neutral" className="shrink-0">
          {chapterCount} {chapterCount === 1 ? 'chapter' : 'chapters'}
        </Badge>
      </div>

      {/* Document context input */}
      <div className="flex flex-col gap-1">
        <label
          htmlFor="doc-context"
          className="text-xs font-medium text-gray-500"
        >
          Document context
        </label>
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
              return (
                <option key={ch.number} value={ch.number}>
                  {title || prefix}
                </option>
              )
            })}
          </Select>
        </div>
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
    </div>
  )
}
