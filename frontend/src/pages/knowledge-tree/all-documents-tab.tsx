import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, FileText, FolderOpen, Layers, Plus, Check } from 'lucide-react'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useAppStore } from '../../stores/app-store'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import type { KnowledgeChapter, KnowledgeDocument } from '../../types/knowledge-tree'

interface AllDocumentsTabProps {
  treeId: string
  chapters: KnowledgeChapter[]
  resumeDocId?: string
}

function getViewerUrl(treeId: string, doc: KnowledgeDocument): string {
  const base = doc.chapter_number != null
    ? `/trees/${treeId}/chapters/${doc.chapter_number}`
    : `/trees/${treeId}`
  return `${base}/viewer/${doc.id}`
}

export function AllDocumentsTab({ treeId, chapters, resumeDocId }: AllDocumentsTabProps) {
  const navigate = useNavigate()
  const addError = useAppStore((s) => s.addError)
  const { documents: docsByKey, documentsLoading, fetchAllDocuments, createDocument, updateDocument } = useKnowledgeTreeStore()

  const [overviewExpanded, setOverviewExpanded] = React.useState(false)
  const [overviewContent, setOverviewContent] = React.useState('')
  const [overviewSaving, setOverviewSaving] = React.useState(false)

  const resumedRef = React.useRef(false)

  const key = `${treeId}:all`
  const allDocs = docsByKey[key] ?? []
  const loading = documentsLoading[key] ?? false

  // Extract tree-level main doc (overview)
  const mainDoc = React.useMemo(
    () => allDocs.find((d) => d.chapter_id === null && d.is_main) ?? null,
    [allDocs]
  )

  // Sync overview content when mainDoc changes
  React.useEffect(() => {
    setOverviewContent(mainDoc?.content ?? '')
  }, [mainDoc?.id])

  React.useEffect(() => {
    void fetchAllDocuments(treeId)
  }, [treeId, fetchAllDocuments])

  React.useEffect(() => {
    if (!resumeDocId || loading || allDocs.length === 0 || resumedRef.current) return
    const doc = allDocs.find((d) => d.id === resumeDocId)
    if (doc) {
      resumedRef.current = true
      navigate(getViewerUrl(treeId, doc), { replace: true })
    }
  }, [resumeDocId, loading, allDocs, navigate, treeId])

  const handleSaveOverview = async () => {
    setOverviewSaving(true)
    try {
      if (mainDoc) {
        await updateDocument(mainDoc.id, mainDoc.title, overviewContent, treeId, null)
      } else {
        await createDocument(treeId, null, 'Overview', overviewContent, true)
      }
    } catch {
      addError('Failed to save overview. Please try again.')
    } finally {
      setOverviewSaving(false)
    }
  }

  // A "source file" is any tree-level document that has an original file attached.
  // We check both chapter_number and chapter_id to be defensive against API quirks.
  const sourceFiles = allDocs.filter(
    (d) => d.source_file_path && (d.chapter_number == null || d.chapter_id == null)
  )
  const chapterDocs = allDocs.filter((d) => d.chapter_number != null && d.chapter_id != null)

  const docsByChapter = new Map<number, KnowledgeDocument[]>()
  for (const doc of chapterDocs) {
    const ch = doc.chapter_number!
    const existing = docsByChapter.get(ch) ?? []
    existing.push(doc)
    docsByChapter.set(ch, existing)
  }

  const sortedChapters = [...docsByChapter.keys()].sort((a, b) => a - b)

  return (
    <div className="flex flex-col gap-4 min-w-0">
      {/* Knowledge Tree Overview — collapsible */}
      <div className="flex flex-col gap-2 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 p-4">
        <button
          onClick={() => setOverviewExpanded(!overviewExpanded)}
          className="flex items-center gap-2 text-left w-full"
        >
          <Plus className={cn(
            'h-4 w-4 text-primary shrink-0 transition-transform',
            overviewExpanded && 'rotate-45'
          )} />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-text-primary">Knowledge Tree Overview</h3>
            <p className="text-xs text-text-tertiary">Add a summary of what this knowledge tree will cover</p>
          </div>
        </button>
        {overviewExpanded && (
          <div className="flex flex-col gap-2 mt-2">
            <textarea
              className="w-full rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface px-3 py-2.5 text-sm text-text-secondary placeholder-gray-400 dark:placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none font-mono leading-relaxed"
              rows={12}
              placeholder="Write an overview of this knowledge tree. Describe the main topics, goals, and structure..."
              value={overviewContent}
              onChange={(e) => setOverviewContent(e.target.value)}
            />
            <div className="flex items-center justify-between">
              <p className="text-xs text-text-tertiary">
                This document describes the overall scope. The AI will use it to provide context when generating content for each chapter.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => void handleSaveOverview()}
                disabled={overviewSaving}
              >
                <Check className="h-3.5 w-3.5 mr-1" />
                {overviewSaving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Documents section */}
      {loading ? (
        <div className="text-sm text-text-tertiary mt-4">Loading documents...</div>
      ) : allDocs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FolderOpen className="h-8 w-8 text-text-tertiary mb-3" />
          <p className="text-sm text-text-tertiary font-medium">No documents yet</p>
          <p className="text-xs text-text-tertiary mt-1">
            Import PDF, EPUB, or TXT files into chapters to see them here.
          </p>
        </div>
      ) : (
        <>
          {/* Source Document — highlighted top subsection */}
          {sourceFiles.length > 0 ? (
        <div className="flex flex-col gap-2 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 p-4">
          <div className="flex items-center gap-2 pb-2 border-b border-warning/20 dark:border-warning/25">
            <Layers className="h-4 w-4 text-warning" />
            <h3 className="text-sm font-semibold text-warning">Original Source Document</h3>
            <Badge variant="neutral" className="text-xs bg-warning-light text-warning border-warning/30 dark:border-warning/30">{sourceFiles.length}</Badge>
          </div>
          <div className="flex flex-col gap-2">
            {sourceFiles.map((doc) => (
              <SourceDocumentRow key={doc.id} doc={doc} treeId={treeId} />
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-surface-200 dark:border-surface-200 bg-surface-100/50 dark:bg-surface-200/50 p-4 text-center">
          <p className="text-xs text-text-tertiary">
            No source documents found for this tree.
          </p>
        </div>
      )}

      {/* Chapter Documents */}
      {sortedChapters.map((chNum) => {
        const docs = docsByChapter.get(chNum)!
        const chapter = chapters.find((c) => c.number === chNum)
        const chapterTitle = chapter?.title ?? `Chapter ${chNum}`

        return (
          <div key={chNum} className="flex flex-col gap-2">
            <div className="flex items-center gap-2 pb-1 border-b border-surface-200 dark:border-surface-200">
              <FileText className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold text-text-primary">{chapterTitle}</h3>
              <Badge variant="neutral" className="text-xs">{docs.length}</Badge>
            </div>
            <div className="flex flex-col gap-2 pl-1">
              {docs.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} treeId={treeId} />
              ))}
            </div>
          </div>
        )
      })}
      </>
    )}

    </div>
  )
}

interface DocumentRowProps {
  doc: KnowledgeDocument
  treeId: string
}

function getDocIsViewable(doc: KnowledgeDocument): boolean {
  if (doc.file_type) return ['pdf', 'epub', 'txt', 'md'].includes(doc.file_type)
  const fileName = (doc.source_file_name ?? doc.source_file_path ?? '').toLowerCase()
  return fileName.endsWith('.pdf') || fileName.endsWith('.epub') || fileName.endsWith('.txt')
}

function getDocIsPdf(doc: KnowledgeDocument): boolean {
  if (doc.file_type) return doc.file_type === 'pdf'
  const fileName = (doc.source_file_name ?? doc.source_file_path ?? '').toLowerCase()
  return fileName.endsWith('.pdf')
}

function SourceDocumentRow({ doc, treeId }: { doc: KnowledgeDocument; treeId: string }) {
  const navigate = useNavigate()
  const isPdf = getDocIsPdf(doc)
  const isViewable = getDocIsViewable(doc)
  const canOpen = isViewable
  const thumbnailUrl = isPdf ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''
  const [thumbError, setThumbError] = React.useState(false)

  return (
    <div
      className={cn(
        'source-doc-animated-border transition-all duration-200 ease-out',
        canOpen && 'cursor-pointer hover:shadow-xl hover:scale-[1.02]'
      )}
    >
    <div
      className="flex items-center gap-3 px-3 py-3 rounded-[9px] bg-surface dark:bg-surface-200 shadow-sm"
      onClick={() => canOpen && navigate(getViewerUrl(treeId, doc))}
    >
      {/* Thumbnail */}
      <div className="shrink-0 w-[72px] h-[96px] rounded overflow-hidden bg-surface-100 dark:bg-surface-200 flex items-center justify-center">
        {isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : (
          <BookOpen className="h-6 w-6 text-amber-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-semibold text-text-primary truncate">{doc.title}</span>
        {doc.source_file_name && (
          <p className="text-xs text-text-tertiary truncate">{doc.source_file_name}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="neutral" className="text-xs bg-warning-light text-warning border-warning/30 dark:border-warning/30 hover:bg-warning-light">
          Original
        </Badge>
      </div>
    </div>
    </div>
  )
}

function DocumentRow({ doc, treeId }: DocumentRowProps) {
  const navigate = useNavigate()
  const hasSourceFile = !!doc.source_file_path
  const isPdf = getDocIsPdf(doc)
  const isViewable = getDocIsViewable(doc)
  const hasContent = (doc.content ?? '').trim().length > 0
  const canOpen = isViewable || hasContent
  const thumbnailUrl = isPdf ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''
  const [thumbError, setThumbError] = React.useState(false)

  const handleClick = () => {
    if (canOpen) navigate(getViewerUrl(treeId, doc))
  }

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 transition-all duration-200 ease-out',
        canOpen && 'cursor-pointer hover:shadow-xl hover:scale-[1.02]'
      )}
      onClick={handleClick}
    >
      {/* Thumbnail */}
      <div className="shrink-0 w-[60px] h-[80px] rounded overflow-hidden bg-surface-100 dark:bg-surface-200 flex items-center justify-center">
        {isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : hasSourceFile ? (
          <BookOpen className="h-5 w-5 text-text-tertiary" />
        ) : (
          <FileText className="h-5 w-5 text-text-tertiary" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-text-primary truncate">{doc.title}</span>
        {doc.source_file_name && (
          <p className="text-xs text-text-tertiary truncate">{doc.source_file_name}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="neutral" className="text-xs">
          {doc.content.trim().split(/\s+/).filter(Boolean).length} words
        </Badge>
      </div>
    </div>
  )
}
