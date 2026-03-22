import * as React from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronDown, ChevronRight } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
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
  selectedChapter: number | undefined
  onChapterChange: (chapter: number | undefined) => void
  children: React.ReactNode
  className?: string
}

const TAB_LABELS: Record<Tab, string> = {
  flashcards: 'Flashcards',
  summary: 'Summary',
}

interface ChapterTreeItemProps {
  chapter: ChapterOut
  isSelected: boolean
  onSelect: (chapterNumber: number) => void
}

function ChapterTreeItem({ chapter, isSelected, onSelect }: ChapterTreeItemProps) {
  const hasSections = chapter.sections && chapter.sections.length > 0
  const [expanded, setExpanded] = useState(false)

  function handleClick() {
    onSelect(chapter.number)
    if (hasSections) {
      setExpanded((prev) => !prev)
    }
  }

  return (
    <li>
      <button
        type="button"
        className={cn(
          'flex items-center gap-2 w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors',
          isSelected
            ? 'bg-blue-50 text-primary font-medium'
            : 'text-gray-700 hover:bg-surface-100 hover:text-gray-900',
        )}
        onClick={handleClick}
        aria-expanded={hasSections ? expanded : undefined}
      >
        {hasSections ? (
          expanded ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-gray-400" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-gray-400" />
          )
        ) : (
          <span className="h-3.5 w-3.5 shrink-0" />
        )}
        <span className="truncate">
          Chapter {chapter.number}
          {chapter.title ? `: ${chapter.title}` : ''}
        </span>
      </button>

      {hasSections && expanded && (
        <ul className="ml-5 mt-0.5 flex flex-col gap-0.5">
          {chapter.sections!.map((section, idx) => (
            <li key={idx}>
              <span className="block px-3 py-1 text-xs text-gray-500 truncate">
                {section.title}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

interface ChapterTreeProps {
  chapters: ChapterOut[]
  selectedChapter: number | undefined
  onChapterChange: (chapter: number | undefined) => void
}

function ChapterTree({ chapters, selectedChapter, onChapterChange }: ChapterTreeProps) {
  return (
    <div className="border border-gray-200 rounded-md bg-white overflow-hidden max-h-60 overflow-y-auto">
      <ul className="flex flex-col gap-0.5 p-1">
        <li>
          <button
            type="button"
            className={cn(
              'flex items-center gap-2 w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors',
              selectedChapter === undefined
                ? 'bg-blue-50 text-primary font-medium'
                : 'text-gray-700 hover:bg-surface-100 hover:text-gray-900',
            )}
            onClick={() => onChapterChange(undefined)}
          >
            <span className="h-3.5 w-3.5 shrink-0" />
            All chapters
          </button>
        </li>
        {chapters.map((ch) => (
          <ChapterTreeItem
            key={ch.number}
            chapter={ch}
            isSelected={selectedChapter === ch.number}
            onSelect={onChapterChange}
          />
        ))}
      </ul>
    </div>
  )
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
}: DocumentLayoutProps) {
  const navigate = useNavigate()

  const chapterCount = structure?.num_chapters ?? document.num_chapters

  const metadataCache = useDocumentStore((s) => s.metadataCache)
  const fetchMetadata = useDocumentStore((s) => s.fetchMetadata)
  const saveMetadataAction = useDocumentStore((s) => s.saveMetadata)

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

  // Build chapter list for the tree: use structure if available, else synthesize from count
  const chapters: ChapterOut[] = structure?.chapters ?? Array.from(
    { length: document.num_chapters },
    (_, i) => ({ number: i + 1, title: undefined, num_chunks: 0, sections: [] }),
  )

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

      {/* Chapter selector tree */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-gray-500">Chapter</span>
        <ChapterTree
          chapters={chapters}
          selectedChapter={selectedChapter}
          onChapterChange={onChapterChange}
        />
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
