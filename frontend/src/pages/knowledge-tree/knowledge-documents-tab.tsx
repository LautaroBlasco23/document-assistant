import * as React from 'react'
import { Plus, Pencil, Trash2, Check, X, FileText, Upload, BookOpen, Files } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { useKnowledgeTreeStore, docKey } from '../../stores/knowledge-tree-store'
import { useAppStore } from '../../stores/app-store'
import { client } from '../../services'
import { DocumentReader } from '../../components/reader/DocumentReader'
import { cn } from '../../lib/cn'
import type { KnowledgeChapter, KnowledgeDocument } from '../../types/knowledge-tree'

interface KnowledgeDocumentsTabProps {
  treeId: string
  selectedChapter: number | null  // null = tree-level (main doc)
  chapters: KnowledgeChapter[]
}

interface DocumentEditorState {
  id: string | null  // null = creating new
  title: string
  content: string
}

export function KnowledgeDocumentsTab({
  treeId,
  selectedChapter,
  chapters,
}: KnowledgeDocumentsTabProps) {
  const {
    documents: docsByKey,
    documentsLoading,
    fetchDocuments,
    createDocument,
    updateDocument,
    deleteDocument,
    ingestFileAsDocument,
  } = useKnowledgeTreeStore()
  const addError = useAppStore((s) => s.addError)

  const [editor, setEditor] = React.useState<DocumentEditorState | null>(null)
  const [saving, setSaving] = React.useState(false)
  const [ingesting, setIngesting] = React.useState(false)
  const [multiIngestProgress, setMultiIngestProgress] = React.useState<{ current: number; total: number } | null>(null)
  const [readerDoc, setReaderDoc] = React.useState<KnowledgeDocument | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const multiFileInputRef = React.useRef<HTMLInputElement>(null)

  const key = docKey(treeId, selectedChapter)
  const docs = docsByKey[key] ?? []
  const loading = documentsLoading[key] ?? false

  const selectedChapterId = selectedChapter !== null
    ? chapters.find((c) => c.number === selectedChapter)?.id ?? null
    : null

  React.useEffect(() => {
    void fetchDocuments(treeId, selectedChapter, selectedChapterId)
  }, [treeId, selectedChapter, selectedChapterId, fetchDocuments])

  const handleOpenCreate = () => {
    setEditor({ id: null, title: '', content: '' })
  }

  const handleOpenEdit = (doc: KnowledgeDocument) => {
    setEditor({ id: doc.id, title: doc.title, content: doc.content })
  }

  const handleCancelEditor = () => {
    setEditor(null)
  }

  const handleSave = async () => {
    if (!editor || !editor.title.trim()) return
    setSaving(true)
    try {
      if (editor.id === null) {
        await createDocument(treeId, selectedChapter, editor.title.trim(), editor.content, false)
      } else {
        await updateDocument(editor.id, editor.title.trim(), editor.content, treeId, selectedChapter)
      }
      setEditor(null)
    } finally {
      setSaving(false)
    }
  }

  const handleIngestFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || selectedChapter === null) return
    e.target.value = ''
    setIngesting(true)
    try {
      const { task_id } = await ingestFileAsDocument(treeId, selectedChapter, file)
      await pollIngestTask(task_id, treeId, selectedChapter, selectedChapterId)
    } catch {
      addError('Failed to start file import. Please try again.')
      setIngesting(false)
    }
  }

  const handleIngestMultipleFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (files.length === 0 || selectedChapter === null) return
    e.target.value = ''
    setMultiIngestProgress({ current: 0, total: files.length })
    try {
      for (let i = 0; i < files.length; i++) {
        setMultiIngestProgress({ current: i + 1, total: files.length })
        try {
          const { task_id } = await ingestFileAsDocument(treeId, selectedChapter, files[i])
          await pollIngestTask(task_id, treeId, selectedChapter, selectedChapterId)
        } catch {
          addError(`Failed to import "${files[i].name}". Skipping.`)
        }
      }
    } finally {
      setMultiIngestProgress(null)
    }
  }

  const pollIngestTask = (
    taskId: string,
    tid: string,
    chapter: number,
    chapterId: string | null,
  ) =>
    new Promise<void>((resolve) => {
      const interval = setInterval(() => {
        void (async () => {
          try {
            const status = await client.getTaskStatus(taskId)
            if (status.status === 'completed') {
              clearInterval(interval)
              await fetchDocuments(tid, chapter, chapterId)
              setIngesting(false)
              resolve()
            } else if (status.status === 'failed') {
              clearInterval(interval)
              addError(status.error ?? 'File import failed. The document was not added.')
              setIngesting(false)
              resolve()
            } else if (status.status === 'rate_limited') {
              clearInterval(interval)
              const retryAfter = (status.result as { retry_after?: number } | undefined)?.retry_after
              addError(
                retryAfter
                  ? `AI provider is rate-limiting requests. Please retry in ${Math.ceil(retryAfter)}s.`
                  : (status.error ?? 'Rate limited by AI provider. Please try again shortly.')
              )
              setIngesting(false)
              resolve()
            }
          } catch {
            clearInterval(interval)
            addError('Lost connection while importing file.')
            setIngesting(false)
            resolve()
          }
        })()
      }, 1500)
    })

  const handleDelete = async (doc: KnowledgeDocument) => {
    if (!window.confirm(`Delete "${doc.title}"? This cannot be undone.`)) return
    await deleteDocument(doc.id, treeId, selectedChapter)
  }

  const isMain = selectedChapter === null
  const mainDoc = isMain ? docs.find((d) => d.is_main) : undefined

  const handleSaveMainDoc = async (newContent: string) => {
    setSaving(true)
    try {
      if (mainDoc) {
        await updateDocument(mainDoc.id, mainDoc.title, newContent, treeId, null)
      } else {
        await createDocument(treeId, null, 'Overview', newContent, true)
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 min-w-0">
        {loading ? (
          <div className="text-sm text-text-tertiary mt-4">Loading documents...</div>
        ) : isMain ? (
          /* Tree-level: single main document (editable inline) */
          <MainDocEditor
            doc={mainDoc ?? null}
            saving={saving}
            onSave={handleSaveMainDoc}
          />
        ) : (
          /* Chapter level: list of docs */
          <>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-text-primary">
                  {chapters.find((c) => c.number === selectedChapter)?.title ?? `Chapter ${selectedChapter}`}
                </h3>
                <p className="text-xs text-text-tertiary">{docs.length} {docs.length === 1 ? 'document' : 'documents'}</p>
              </div>
              {editor === null && (
                <div className="flex items-center gap-2">
                  <input
                    ref={multiFileInputRef}
                    type="file"
                    accept=".pdf,.epub,.txt"
                    multiple
                    className="hidden"
                    onChange={(e) => void handleIngestMultipleFiles(e)}
                  />
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.epub,.txt"
                    className="hidden"
                    onChange={(e) => void handleIngestFile(e)}
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => multiFileInputRef.current?.click()}
                    disabled={ingesting || multiIngestProgress !== null}
                    title="Import multiple PDF, EPUB, or TXT files at once"
                  >
                    {multiIngestProgress !== null ? (
                      <>
                        <div className="h-3.5 w-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin mr-1" />
                        {`Importing ${multiIngestProgress.current}/${multiIngestProgress.total}...`}
                      </>
                    ) : (
                      <>
                        <Files className="h-3.5 w-3.5 mr-1" />
                        Import Multiple
                      </>
                    )}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={ingesting || multiIngestProgress !== null}
                    title="Import from PDF, EPUB, or TXT"
                  >
                    {ingesting ? (
                      <div className="h-3.5 w-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin mr-1" />
                    ) : (
                      <Upload className="h-3.5 w-3.5 mr-1" />
                    )}
                    {ingesting ? 'Importing...' : 'Import from PDF/EPUB'}
                  </Button>
                  <Button variant="primary" size="sm" onClick={handleOpenCreate}>
                    <Plus className="h-3.5 w-3.5 mr-1" />
                    Add Document
                  </Button>
                </div>
              )}
            </div>

            {/* Inline create form */}
            {editor !== null && editor.id === null && (
              <DocumentEditorCard
                editor={editor}
                saving={saving}
                onChange={setEditor}
                onSave={() => void handleSave()}
                onCancel={handleCancelEditor}
                isNew
              />
            )}

            {/* Documents list */}
            {docs.length === 0 && editor === null ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="h-8 w-8 text-text-tertiary mb-3" />
                <p className="text-sm text-text-tertiary font-medium">No documents yet</p>
                <p className="text-xs text-text-tertiary mt-1">
                  Add knowledge documents for this chapter. They will be used to generate summaries and flashcards.
                </p>
              </div>
            ) : (
               docs.map((doc) => (
                 editor !== null && editor.id === doc.id ? (
                   <DocumentEditorCard
                     key={doc.id}
                     editor={editor}
                     saving={saving}
                     onChange={setEditor}
                     onSave={() => void handleSave()}
                     onCancel={handleCancelEditor}
                     isNew={false}
                   />
                 ) : (
                   <DocumentCard
                     key={doc.id}
                     doc={doc}
                     chapter={selectedChapter}
                     onEdit={() => handleOpenEdit(doc)}
                     onDelete={() => void handleDelete(doc)}
                     onRead={setReaderDoc}
                   />
                 )
               ))
             )}

             {/* Document Reader Modal */}
             {readerDoc && selectedChapter !== null && (
               <DocumentReader
                 doc={readerDoc}
                 treeId={treeId}
                 chapter={selectedChapter}
                 onClose={() => setReaderDoc(null)}
               />
             )}
           </>
         )}
     </div>
   )
 }

// ─── Sub-components ───────────────────────────────────────────────────────────

interface MainDocEditorProps {
  doc: KnowledgeDocument | null
  saving: boolean
  onSave: (content: string) => Promise<void>
}

function MainDocEditor({ doc, saving, onSave }: MainDocEditorProps) {
  const [content, setContent] = React.useState(doc?.content ?? '')
  const [dirty, setDirty] = React.useState(false)

  // Sync when doc changes
  React.useEffect(() => {
    setContent(doc?.content ?? '')
    setDirty(false)
  }, [doc?.id])

  const handleChange = (val: string) => {
    setContent(val)
    setDirty(val !== (doc?.content ?? ''))
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Overview Document</h3>
          <p className="text-xs text-text-tertiary">Describes the overall scope of this knowledge tree.</p>
        </div>
        {dirty && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => void onSave(content)}
            disabled={saving}
          >
            <Check className="h-3.5 w-3.5 mr-1" />
            {saving ? 'Saving...' : 'Save'}
          </Button>
        )}
      </div>
      <textarea
        className="w-full rounded-lg border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2.5 text-sm text-text-secondary placeholder-gray-400 dark:placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none font-mono leading-relaxed"
        rows={18}
        placeholder="Write an overview of this knowledge tree. Describe the main topics, goals, and structure..."
        value={content}
        onChange={(e) => handleChange(e.target.value)}
      />
      <p className="text-xs text-text-tertiary">
        This document describes the overall scope. The AI will use it to provide context when generating content for each chapter.
      </p>
    </div>
  )
}

interface DocumentCardProps {
  doc: KnowledgeDocument
  chapter: number | null
  onEdit: () => void
  onDelete: () => void
  onRead: (doc: KnowledgeDocument) => void
}

function DocumentCard({ doc, chapter, onEdit, onDelete, onRead }: DocumentCardProps) {
  const preview = doc.content.trim().slice(0, 200)
  const hasSourceFile = !!doc.source_file_path
  const isPdf = hasSourceFile && (
    doc.source_file_name?.toLowerCase().endsWith('.pdf') ||
    doc.source_file_path?.toLowerCase().endsWith('.pdf')
  )
  const canRead = hasSourceFile && chapter !== null
  const thumbnailUrl = canRead ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''
  const [thumbError, setThumbError] = React.useState(false)

  const handleCardClick = () => {
    if (canRead && isPdf) {
      onRead(doc)
    }
  }

  return (
    <div
      className={cn(
        'border border-surface-200 dark:border-surface-200 rounded-lg p-3 flex flex-row gap-4 bg-surface dark:bg-surface-200',
        canRead && isPdf && 'cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 ease-out'
      )}
      onClick={handleCardClick}
    >
      {/* Edit/Delete buttons */}
      <div className="shrink-0 flex flex-col gap-1.5 justify-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => { e.stopPropagation(); onEdit(); }}
          className="h-8 w-8 p-0 text-text-tertiary hover:text-gray-700 dark:hover:text-slate-200 hover:bg-surface-100 dark:hover:bg-surface-100"
          title="Edit document"
        >
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          aria-label="Delete document"
          className="h-8 w-8 p-0 text-danger hover:text-danger dark:hover:text-danger hover:bg-danger-light dark:hover:bg-danger/12"
          title="Delete document"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Thumbnail */}
      <div className="shrink-0 w-[100px] h-[130px] rounded-md overflow-hidden bg-surface-100 dark:bg-surface-200 flex items-center justify-center">
        {hasSourceFile && isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : hasSourceFile && !isPdf ? (
          <div className="flex flex-col items-center gap-1 text-text-tertiary">
            <BookOpen className="h-8 w-8" />
            <span className="text-[10px] font-medium">EPUB</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 text-text-tertiary">
            <FileText className="h-8 w-8" />
            <span className="text-[10px] font-medium">TXT</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <span className="text-sm font-medium text-text-primary truncate">{doc.title}</span>
        {preview && (
          <p className="text-xs text-text-tertiary line-clamp-3 leading-relaxed font-mono">
            {preview}{doc.content.length > 200 ? '...' : ''}
          </p>
        )}
        <div className="flex items-center gap-2 pt-1">
          <Badge variant="neutral" className="text-xs">
            {doc.content.trim().split(/\s+/).filter(Boolean).length} words
          </Badge>
        </div>
      </div>
    </div>
  )
}

interface DocumentEditorCardProps {
  editor: DocumentEditorState
  saving: boolean
  isNew: boolean
  onChange: (state: DocumentEditorState) => void
  onSave: () => void
  onCancel: () => void
}

interface DocumentEditorState {
  id: string | null
  title: string
  content: string
}

function DocumentEditorCard({ editor, saving, isNew, onChange, onSave, onCancel }: DocumentEditorCardProps) {
  return (
    <div className="border border-primary/40 rounded-lg p-4 flex flex-col gap-3 bg-primary-light dark:bg-primary/12">
      <div className="flex items-center gap-2">
        <Input
          placeholder="Document title"
          value={editor.title}
          onChange={(e) => onChange({ ...editor, title: e.target.value })}
          className="flex-1"
          autoFocus={isNew}
        />
      </div>
      <textarea
        className="w-full rounded-md border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 px-3 py-2.5 text-sm text-text-secondary placeholder-gray-400 dark:placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none font-mono leading-relaxed"
        rows={10}
        placeholder="Write the knowledge document content here..."
        value={editor.content}
        onChange={(e) => onChange({ ...editor, content: e.target.value })}
      />
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={saving}>
          <X className="h-3.5 w-3.5 mr-1" />
          Cancel
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={onSave}
          disabled={saving || !editor.title.trim()}
        >
          <Check className="h-3.5 w-3.5 mr-1" />
          {saving ? 'Saving...' : isNew ? 'Create' : 'Save'}
        </Button>
      </div>
    </div>
  )
}
