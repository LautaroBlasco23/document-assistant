import * as React from 'react'
import { BookOpen, FileText, FolderOpen, Layers } from 'lucide-react'
import { Badge } from '../../components/ui/badge'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { DocumentReader } from '../../components/reader/DocumentReader'
import { UnifiedDocumentReader } from '../../components/reader/UnifiedDocumentReader'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import type { KnowledgeChapter, KnowledgeDocument } from '../../types/knowledge-tree'

interface AllDocumentsTabProps {
  treeId: string
  chapters: KnowledgeChapter[]
}

export function AllDocumentsTab({ treeId, chapters }: AllDocumentsTabProps) {
  const { documents: docsByKey, documentsLoading, fetchAllDocuments } = useKnowledgeTreeStore()

  const [readerDoc, setReaderDoc] = React.useState<KnowledgeDocument | null>(null)
  const [unifiedReaderDoc, setUnifiedReaderDoc] = React.useState<KnowledgeDocument | null>(null)

  const key = `${treeId}:all`
  const allDocs = docsByKey[key] ?? []
  const loading = documentsLoading[key] ?? false

  React.useEffect(() => {
    void fetchAllDocuments(treeId)
  }, [treeId, fetchAllDocuments])

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

  if (loading) {
    return <div className="text-sm text-gray-400 dark:text-slate-500 mt-4">Loading documents...</div>
  }

  if (allDocs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FolderOpen className="h-8 w-8 text-gray-300 dark:text-slate-600 mb-3" />
        <p className="text-sm text-gray-500 dark:text-slate-400 font-medium">No documents yet</p>
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
          Import PDF/EPUB files into chapters to see them here.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 min-w-0">
      {/* Source Document — highlighted top subsection */}
      {sourceFiles.length > 0 ? (
        <div className="flex flex-col gap-2 rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50/40 dark:bg-amber-900/10 p-4">
          <div className="flex items-center gap-2 pb-2 border-b border-amber-200/60 dark:border-amber-800/40">
            <Layers className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300">Original Source Document</h3>
            <Badge variant="neutral" className="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800/40">{sourceFiles.length}</Badge>
          </div>
          <div className="flex flex-col gap-2">
            {sourceFiles.map((doc) => (
              <SourceDocumentRow key={doc.id} doc={doc} onReadUnified={setUnifiedReaderDoc} />
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-gray-200 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50 p-4 text-center">
          <p className="text-xs text-gray-400 dark:text-slate-500">
            No original source document found. This is only available for trees imported after the latest update.
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
            <div className="flex items-center gap-2 pb-1 border-b border-gray-200 dark:border-slate-700">
              <FileText className="h-4 w-4 text-blue-500 dark:text-blue-400" />
              <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-200">{chapterTitle}</h3>
              <Badge variant="neutral" className="text-xs">{docs.length}</Badge>
            </div>
            <div className="flex flex-col gap-2 pl-1">
              {docs.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} onRead={setReaderDoc} onReadUnified={setUnifiedReaderDoc} />
              ))}
            </div>
          </div>
        )
      })}

      {/* Document Reader Modal */}
      {readerDoc && (
        <DocumentReader
          doc={readerDoc}
          treeId={treeId}
          chapter={readerDoc.chapter_number ?? 0}
          onClose={() => setReaderDoc(null)}
        />
      )}

      {/* Unified Document Reader Modal */}
      {unifiedReaderDoc && (
        <UnifiedDocumentReader
          doc={unifiedReaderDoc}
          treeId={treeId}
          chapters={chapters}
          onClose={() => setUnifiedReaderDoc(null)}
        />
      )}
    </div>
  )
}

interface DocumentRowProps {
  doc: KnowledgeDocument
  onRead: (doc: KnowledgeDocument) => void
  onReadUnified: (doc: KnowledgeDocument) => void
}

function SourceDocumentRow({ doc, onReadUnified }: { doc: KnowledgeDocument; onReadUnified: (doc: KnowledgeDocument) => void }) {
  const hasSourceFile = !!doc.source_file_path
  const isPdf = hasSourceFile && (
    doc.source_file_name?.toLowerCase().endsWith('.pdf') ||
    doc.source_file_path?.toLowerCase().endsWith('.pdf')
  )
  const canOpen = hasSourceFile && isPdf
  const thumbnailUrl = hasSourceFile ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''
  const [thumbError, setThumbError] = React.useState(false)

  return (
    <div className="source-doc-animated-border">
    <div
      className={cn(
        'flex items-center gap-3 px-3 py-3 rounded-[9px] bg-white dark:bg-slate-800 shadow-sm transition-all duration-200 ease-out',
        canOpen && !thumbError && 'cursor-pointer hover:shadow-xl hover:scale-[1.02]'
      )}
      onClick={() => canOpen && !thumbError && onReadUnified(doc)}
    >
      {/* Thumbnail */}
      <div className="shrink-0 w-[72px] h-[96px] rounded overflow-hidden bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
        {hasSourceFile && isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : hasSourceFile && !isPdf ? (
          <BookOpen className="h-6 w-6 text-amber-500" />
        ) : (
          <FileText className="h-6 w-6 text-amber-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-semibold text-gray-900 dark:text-slate-100 truncate">{doc.title}</span>
        {doc.source_file_name && (
          <p className="text-xs text-gray-500 dark:text-slate-400 truncate">{doc.source_file_name}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="neutral" className="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800/40 hover:bg-amber-100 dark:hover:bg-amber-900/30">
          Original
        </Badge>
      </div>
    </div>
    </div>
  )
}

function DocumentRow({ doc, onRead, onReadUnified }: DocumentRowProps) {
  const hasSourceFile = !!doc.source_file_path
  const isPdf = hasSourceFile && (
    doc.source_file_name?.toLowerCase().endsWith('.pdf') ||
    doc.source_file_path?.toLowerCase().endsWith('.pdf')
  )
  const canOpen = hasSourceFile && isPdf
  const isSourceFile = doc.chapter_number == null && !doc.is_main
  const thumbnailUrl = canOpen ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''
  const [thumbError, setThumbError] = React.useState(false)

  const handleClick = () => {
    if (canOpen && !thumbError) {
      if (isSourceFile) onReadUnified(doc)
      else onRead(doc)
    }
  }

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 transition-all duration-200 ease-out',
        canOpen && !thumbError && 'cursor-pointer hover:shadow-xl hover:scale-[1.02]'
      )}
      onClick={handleClick}
    >
      {/* Thumbnail */}
      <div className="shrink-0 w-[60px] h-[80px] rounded overflow-hidden bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
        {hasSourceFile && isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : hasSourceFile && !isPdf ? (
          <BookOpen className="h-5 w-5 text-gray-400 dark:text-slate-500" />
        ) : (
          <FileText className="h-5 w-5 text-gray-400 dark:text-slate-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{doc.title}</span>
        {doc.source_file_name && (
          <p className="text-xs text-gray-400 dark:text-slate-500 truncate">{doc.source_file_name}</p>
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
