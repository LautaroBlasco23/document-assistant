import * as React from 'react'
import { BookOpen, FileText, FolderOpen, Layers } from 'lucide-react'
import { Button } from '../../components/ui/button'
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

  const sourceFiles = allDocs.filter((d) => d.source_file_path && d.chapter_number === null)
  const chapterDocs = allDocs.filter((d) => d.chapter_number !== null)

  const docsByChapter = new Map<number, KnowledgeDocument[]>()
  for (const doc of chapterDocs) {
    const ch = doc.chapter_number!
    const existing = docsByChapter.get(ch) ?? []
    existing.push(doc)
    docsByChapter.set(ch, existing)
  }

  const sortedChapters = [...docsByChapter.keys()].sort((a, b) => a - b)

  if (loading) {
    return <div className="text-sm text-gray-400 mt-4">Loading documents...</div>
  }

  if (allDocs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FolderOpen className="h-8 w-8 text-gray-300 mb-3" />
        <p className="text-sm text-gray-500 font-medium">No documents yet</p>
        <p className="text-xs text-gray-400 mt-1">
          Import PDF/EPUB files into chapters to see them here.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 min-w-0">
      {/* Source Files */}
      {sourceFiles.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 pb-1 border-b border-gray-200">
            <Layers className="h-4 w-4 text-green-600" />
            <h3 className="text-sm font-semibold text-gray-800">Source Files</h3>
            <Badge variant="neutral" className="text-xs">{sourceFiles.length}</Badge>
          </div>
          <div className="flex flex-col gap-2 pl-1">
            {sourceFiles.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} onRead={setReaderDoc} onReadUnified={setUnifiedReaderDoc} />
            ))}
          </div>
        </div>
      )}

      {/* Chapter Documents */}
      {sortedChapters.map((chNum) => {
        const docs = docsByChapter.get(chNum)!
        const chapter = chapters.find((c) => c.number === chNum)
        const chapterTitle = chapter?.title ?? `Chapter ${chNum}`

        return (
          <div key={chNum} className="flex flex-col gap-2">
            <div className="flex items-center gap-2 pb-1 border-b border-gray-200">
              <FileText className="h-4 w-4 text-blue-500" />
              <h3 className="text-sm font-semibold text-gray-800">{chapterTitle}</h3>
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

function DocumentRow({ doc, onRead, onReadUnified }: DocumentRowProps) {
  const hasSourceFile = !!doc.source_file_path
  const isPdf = hasSourceFile && (
    doc.source_file_name?.toLowerCase().endsWith('.pdf') ||
    doc.source_file_path?.toLowerCase().endsWith('.pdf')
  )
  const canRead = hasSourceFile
  const isSourceFile = doc.chapter_number === null && !doc.is_main
  const thumbnailUrl = canRead ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''
  const [thumbError, setThumbError] = React.useState(false)

  const handleThumbClick = () => {
    if (canRead && isPdf) {
      if (isSourceFile) onReadUnified(doc)
      else onRead(doc)
    }
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50 transition-colors">
      {/* Thumbnail */}
      <div
        className={cn(
          'shrink-0 w-[60px] h-[80px] rounded overflow-hidden bg-gray-100 flex items-center justify-center',
          canRead && isPdf && !thumbError && 'cursor-pointer hover:ring-2 hover:ring-indigo-400 hover:ring-offset-1 transition-all'
        )}
        onClick={handleThumbClick}
        title={canRead && isPdf ? 'Click to open document viewer' : undefined}
      >
        {hasSourceFile && isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : hasSourceFile && !isPdf ? (
          <BookOpen className="h-5 w-5 text-gray-400" />
        ) : (
          <FileText className="h-5 w-5 text-gray-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 truncate">{doc.title}</span>
        {doc.source_file_name && (
          <p className="text-xs text-gray-400 truncate">{doc.source_file_name}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="neutral" className="text-xs">
          {doc.content.trim().split(/\s+/).filter(Boolean).length} words
        </Badge>
        {canRead && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => (isSourceFile ? onReadUnified(doc) : onRead(doc))}
            className="h-7 px-2 text-indigo-500 hover:text-indigo-700 hover:bg-indigo-50"
            title="Read document"
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span className="ml-1 text-xs">Read</span>
          </Button>
        )}
      </div>
    </div>
  )
}
