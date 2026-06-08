import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Pencil, Trash2, Check, X, FileText, Upload, BookOpen, Files, Wand2, RotateCcw, Youtube, Scissors, Loader2 } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { ConfirmDialog } from '../../components/ui/confirm-dialog'
import { useKnowledgeTreeStore, docKey } from '../../stores/knowledge-tree-store'
import { useAppStore, LIMITS_INVALIDATE_EVENT } from '../../stores/app-store'
import { useTaskStore, selectActiveImproveTask, selectUnprocessedImproveTask } from '../../stores/task-store'
import { client } from '../../services'

const invalidateLimits = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(LIMITS_INVALIDATE_EVENT))
  }
}
import { cn } from '../../lib/cn'
import { ImproveDialog } from '../../components/reader/ImproveDialog'
import type { KnowledgeChapter, KnowledgeDocument } from '../../types/knowledge-tree'

function useTaskEntry(taskId: string | null) {
  return useTaskStore((s) => (taskId ? (s.tasks[taskId] ?? null) : null))
}

interface SplitChapterEntry {
  pageStart: string
  pageEnd: string
  title: string
}

function validateSplitEntries(entries: SplitChapterEntry[], maxOffset: number): string | null {
  if (entries.length < 2) return 'Must split into at least 2 chapters'
  for (let i = 0; i < entries.length; i++) {
    const start = parseInt(entries[i].pageStart, 10)
    const end = parseInt(entries[i].pageEnd, 10)
    if (isNaN(start) || isNaN(end)) return `Row ${i + 1}: invalid page numbers`
    if (start < 1) return `Row ${i + 1}: page ${start} is before the start (1)`
    if (end > maxOffset + 1) return `Row ${i + 1}: page ${end} is beyond the document (${maxOffset + 1})`
    if (start > end) return `Row ${i + 1}: start page (${start}) must be ≤ end page (${end})`
    if (i > 0) {
      const prevEnd = parseInt(entries[i - 1].pageEnd, 10)
      if (start !== prevEnd + 1) return `Row ${i + 1}: chapters must be contiguous (expected page ${prevEnd + 1})`
    }
  }
  const lastEnd = parseInt(entries[entries.length - 1].pageEnd, 10)
  if (lastEnd !== maxOffset + 1) return 'Last chapter must end at the last page'
  return null
}

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
  const navigate = useNavigate()
  const addError = useAppStore((s) => s.addError)

  // Actions — stable refs from the store
  const fetchDocuments = useKnowledgeTreeStore((s) => s.fetchDocuments)
  const createDocument = useKnowledgeTreeStore((s) => s.createDocument)
  const updateDocument = useKnowledgeTreeStore((s) => s.updateDocument)
  const deleteDocument = useKnowledgeTreeStore((s) => s.deleteDocument)
  const improveDocument = useKnowledgeTreeStore((s) => s.improveDocument)
  const revertDocument = useKnowledgeTreeStore((s) => s.revertDocument)
  const ingestFileAsDocument = useKnowledgeTreeStore((s) => s.ingestFileAsDocument)
  const importYouTubeDocument = useKnowledgeTreeStore((s) => s.importYouTubeDocument)
  const splitChapter = useKnowledgeTreeStore((s) => s.splitChapter)

  const [editor, setEditor] = React.useState<DocumentEditorState | null>(null)
  const [saving, setSaving] = React.useState(false)
  const [ingesting, setIngesting] = React.useState(false)
  const [multiIngestProgress, setMultiIngestProgress] = React.useState<{ current: number; total: number } | null>(null)
  const [youtubeModalOpen, setYoutubeModalOpen] = React.useState(false)
  const [youtubeUrl, setYoutubeUrl] = React.useState('')
  const [youtubeImporting, setYoutubeImporting] = React.useState(false)
  const [splitFormOpen, setSplitFormOpen] = React.useState(false)
  const [splitting, setSplitting] = React.useState(false)
  const [splitEntries, setSplitEntries] = React.useState<SplitChapterEntry[]>([])
  const [splitError, setSplitError] = React.useState<string | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const multiFileInputRef = React.useRef<HTMLInputElement>(null)

  const key = docKey(treeId, selectedChapter)
  const docs = useKnowledgeTreeStore((s) => s.documents[key] ?? [])
  const loading = useKnowledgeTreeStore((s) => s.documentsLoading[key] ?? false)

  const selectedChapterId = selectedChapter !== null
    ? chapters.find((c) => c.number === selectedChapter)?.id ?? null
    : null

  const pdfDoc = docs.find(
    (d) => d.source_file_path && d.page_start != null && d.page_end != null && d.page_end > d.page_start
  )

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

  const handleYoutubeImport = async () => {
    if (!youtubeUrl.trim()) return
    setYoutubeImporting(true)
    try {
      const chapterId = selectedChapterId
      const { task_id } = await importYouTubeDocument(treeId, youtubeUrl.trim(), chapterId)
      setYoutubeModalOpen(false)
      setYoutubeUrl('')
      await pollIngestTask(task_id, treeId, selectedChapter ?? 0, chapterId)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      addError(detail ?? 'Failed to import YouTube video. Please try again.')
    } finally {
      setYoutubeImporting(false)
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
              invalidateLimits()
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
    await deleteDocument(doc.id, treeId, selectedChapter)
  }

  const handleImprove = (doc: KnowledgeDocument) => (mode: 'text' | 'formatting', agentId?: string) =>
    improveDocument(treeId, doc.id, selectedChapter, mode, agentId)

  const handleRevert = (doc: KnowledgeDocument) => () =>
    revertDocument(treeId, doc.id, selectedChapter)

  const handleUpdateFileType = async (docId: string, fileType: string) => {
    const doc = docs.find((d) => d.id === docId)
    if (!doc) return
    try {
      await updateDocument(docId, doc.title, doc.content, treeId, selectedChapter, fileType)
    } catch {
      addError('Failed to update file type.')
    }
  }

  const handleSplit = async () => {
    if (!pdfDoc || selectedChapter === null) return
    const maxOffset = pdfDoc.page_end! - pdfDoc.page_start!
    const validationError = validateSplitEntries(splitEntries, maxOffset)
    if (validationError) {
      setSplitError(validationError)
      return
    }
    setSplitError(null)
    setSplitting(true)
    try {
      const chapters = splitEntries.map(e => ({
        page_start: parseInt(e.pageStart, 10) - 1,
        page_end: parseInt(e.pageEnd, 10) - 1,
        title: e.title.trim() || null,
      }))
      await splitChapter(treeId, selectedChapter, chapters)
      await fetchDocuments(treeId, selectedChapter, selectedChapterId)
      setSplitFormOpen(false)
      setSplitEntries([])
      setSplitError(null)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      addError(detail ?? 'Failed to split chapter.')
    } finally {
      setSplitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 min-w-0">
        {loading ? (
          <div className="text-sm text-text-tertiary mt-4">Loading documents...</div>
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
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setYoutubeModalOpen(true)}
                    disabled={ingesting || multiIngestProgress !== null || youtubeImporting}
                    title="Import transcript from a YouTube video"
                  >
                    <Youtube className="h-3.5 w-3.5 mr-1" />
                    YouTube
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

            {/* Split Chapter — collapsible card */}
            {!splitFormOpen && pdfDoc && (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  await fetchDocuments(treeId, selectedChapter, selectedChapterId)
                  const chapter = chapters.find(c => c.number === selectedChapter)
                  const maxOffset = pdfDoc.page_end! - pdfDoc.page_start!
                  setSplitEntries([{
                    pageStart: '1',
                    pageEnd: String(maxOffset + 1),
                    title: chapter?.title ?? '',
                  }])
                  setSplitFormOpen(true)
                  setSplitError(null)
                }}
                className="self-start"
              >
                <Scissors className="h-3.5 w-3.5 mr-1" />
                Split Chapter
              </Button>
            )}
            {splitFormOpen && pdfDoc && (
              <SplitChapterCard
                pdfDoc={pdfDoc}
                splitEntries={splitEntries}
                splitting={splitting}
                splitError={splitError}
                onEntriesChange={setSplitEntries}
                onSplit={() => void handleSplit()}
                onCancel={() => { setSplitFormOpen(false); setSplitEntries([]); setSplitError(null) }}
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
                      onEdit={() => handleOpenEdit(doc)}
                      onDelete={() => void handleDelete(doc)}
                      onRead={(d) => {
                        const viewerBase = selectedChapter !== null
                          ? `/trees/${treeId}/chapters/${selectedChapter}`
                          : `/trees/${treeId}`
                        navigate(`${viewerBase}/viewer/${d.id}`)
                      }}
                      onImprove={handleImprove(doc)}
                      onRevert={handleRevert(doc)}
                      onUpdateFileType={(ft) => void handleUpdateFileType(doc.id, ft)}
                    />
                 )
               ))
             )}

           </>
         )}

      {/* YouTube Import Modal */}
      {youtubeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-surface-elevated rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
                <Youtube className="h-4 w-4 text-red-500" />
                Import from YouTube
              </h2>
              <button
                onClick={() => { setYoutubeModalOpen(false); setYoutubeUrl('') }}
                className="text-text-tertiary hover:text-text-primary"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-text-tertiary mb-3">
              Paste a YouTube URL. The video's transcript (captions) will be imported as a document.
              The video must have captions available.
            </p>
            <Input
              type="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') void handleYoutubeImport() }}
              disabled={youtubeImporting}
              className="mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => { setYoutubeModalOpen(false); setYoutubeUrl('') }}
                disabled={youtubeImporting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => void handleYoutubeImport()}
                disabled={!youtubeUrl.trim() || youtubeImporting}
              >
                {youtubeImporting ? (
                  <>
                    <div className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin mr-1" />
                    Importing...
                  </>
                ) : 'Import'}
              </Button>
            </div>
          </div>
        </div>
      )}
     </div>
   )
 }

interface DocumentCardProps {
  doc: KnowledgeDocument
  onEdit: () => void
  onDelete: () => void
  onRead: (doc: KnowledgeDocument) => void
  onImprove: (mode: 'text' | 'formatting', agentId?: string) => Promise<string>
  onRevert: () => Promise<KnowledgeDocument>
  onUpdateFileType: (fileType: string) => void
}

const FILE_TYPE_OPTIONS = ['pdf', 'epub', 'txt', 'md'] as const

function getFileTypeLabel(doc: KnowledgeDocument): string {
  if (doc.file_type) return doc.file_type.toUpperCase()
  const fileName = (doc.source_file_name ?? doc.source_file_path ?? '').toLowerCase()
  if (fileName.endsWith('.pdf')) return 'PDF'
  if (fileName.endsWith('.epub')) return 'EPUB'
  if (fileName.endsWith('.txt')) return 'TXT'
  if (fileName.endsWith('.md')) return 'MD'
  return 'TXT'
}

function DocumentCard({ doc, onEdit, onDelete, onRead, onImprove, onRevert, onUpdateFileType }: DocumentCardProps) {
  const [improveOpen, setImproveOpen] = React.useState(false)
  const [revertOpen, setRevertOpen] = React.useState(false)
  const [deleteOpen, setDeleteOpen] = React.useState(false)
  const [acting, setActing] = React.useState(false)
  const [improveTaskId, setImproveTaskId] = React.useState<string | null>(null)
  const [thumbError, setThumbError] = React.useState(false)
  const [ftDropdownOpen, setFtDropdownOpen] = React.useState(false)
  const ftButtonRef = React.useRef<HTMLButtonElement>(null)
  const ftDropdownRef = React.useRef<HTMLDivElement>(null)
  const addError = useAppStore((s) => s.addError)
  const submitTask = useTaskStore((s) => s.submitTask)
  const clearTask = useTaskStore((s) => s.clearTask)
  const applyImproveResult = useKnowledgeTreeStore((s) => s.applyImproveResult)

  React.useEffect(() => {
    if (!ftDropdownOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (
        ftDropdownRef.current &&
        !ftDropdownRef.current.contains(e.target as Node) &&
        ftButtonRef.current &&
        !ftButtonRef.current.contains(e.target as Node)
      ) {
        setFtDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [ftDropdownOpen])

  const isImproved = doc.original_content !== null

  const handleConfirmImprove = async (mode: 'text' | 'formatting', agentId: string) => {
    setActing(true)
    try {
      const taskId = await onImprove(mode, agentId)
      submitTask({
        taskId,
        type: 'kt_improve',
        entityId: doc.tree_id,
        chapter: doc.chapter_number ?? 0,
        entityTitle: `Improve: ${doc.title}`,
        docId: doc.id,
      })
      setImproveTaskId(taskId)
      setImproveOpen(false)
    } catch {
      addError('Failed to improve document. Please try again.')
    } finally {
      setActing(false)
    }
  }

  const improveTaskEntry = useTaskEntry(improveTaskId)

  React.useEffect(() => {
    if (!improveTaskId || !improveTaskEntry) return
    if (improveTaskEntry.status === 'completed') {
      if (improveTaskEntry.result) {
        applyImproveResult(doc.tree_id, doc.chapter_number, doc.id, improveTaskEntry.result)
      }
      clearTask(improveTaskId)
      setImproveTaskId(null)
    } else if (improveTaskEntry.status === 'failed') {
      addError(improveTaskEntry.error ?? 'Improvement failed')
      clearTask(improveTaskId)
      setImproveTaskId(null)
    } else if (improveTaskEntry.status === 'rate_limited') {
      const retryAfter = (improveTaskEntry.result as { retry_after?: number } | null)?.retry_after
      addError(
        retryAfter
          ? `AI provider is rate-limiting. Please retry in ${Math.ceil(retryAfter)}s.`
          : (improveTaskEntry.error ?? 'Rate limited by AI provider.')
      )
      clearTask(improveTaskId)
      setImproveTaskId(null)
    }
  }, [improveTaskId, improveTaskEntry?.status, applyImproveResult, clearTask, addError, doc])

  // ── Re-link improve task state after navigation ──────────────────────────────────
  const activeImproveTask = useTaskStore(selectActiveImproveTask(doc.id))
  const unprocessedImproveTask = useTaskStore(selectUnprocessedImproveTask(doc.id))

  // Restore task ID for in-flight improves that started before navigation.
  React.useEffect(() => {
    if (activeImproveTask && !improveTaskId) {
      setImproveTaskId(activeImproveTask.taskId)
    }
  }, [activeImproveTask?.taskId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle tasks that completed/failed while the component was unmounted.
  React.useEffect(() => {
    if (!unprocessedImproveTask) return
    const task = unprocessedImproveTask
    if (task.status === 'completed') {
      if (task.result) {
        applyImproveResult(doc.tree_id, doc.chapter_number, doc.id, task.result)
      }
      clearTask(task.taskId)
      setImproveTaskId(null)
    } else {
      addError(task.error ?? 'Improvement failed')
      clearTask(task.taskId)
      setImproveTaskId(null)
    }
  }, [unprocessedImproveTask?.taskId]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleConfirmRevert = async () => {
    setActing(true)
    try {
      await onRevert()
      setRevertOpen(false)
    } catch {
      addError('Failed to revert document. Please try again.')
    } finally {
      setActing(false)
    }
  }

  const handleConfirmDelete = async () => {
    setActing(true)
    try {
      await onDelete()
      setDeleteOpen(false)
    } catch {
      addError('Failed to delete document. Please try again.')
    } finally {
      setActing(false)
    }
  }

  const preview = doc.content.trim().slice(0, 200)
  const hasSourceFile = !!doc.source_file_path
  const ftOptions = hasSourceFile ? FILE_TYPE_OPTIONS : FILE_TYPE_OPTIONS.filter((o) => o !== 'pdf')
  const fileName = (doc.source_file_name ?? doc.source_file_path ?? '').toLowerCase()
  const ft = doc.file_type
  const resolvedExt = ft ?? (
    fileName.endsWith('.pdf') ? 'pdf' :
    fileName.endsWith('.epub') ? 'epub' :
    fileName.endsWith('.txt') ? 'txt' :
    fileName.endsWith('.md') ? 'md' :
    ''
  )
  const isPdf = hasSourceFile && resolvedExt === 'pdf'
  const isViewable = hasSourceFile && ['pdf', 'epub', 'txt', 'md'].includes(resolvedExt)
  const hasContent = (doc.content ?? '').trim().length > 0
  const canRead = isViewable || hasContent
  const thumbnailUrl = isPdf ? client.getDocumentThumbnailUrl(doc.tree_id, doc.id) : ''

  const handleCardClick = () => {
    if (canRead) onRead(doc)
  }

  return (
    <div
      className={cn(
        'border border-surface-200 dark:border-surface-200 rounded-lg p-3 flex flex-row gap-4 bg-surface dark:bg-surface-200',
        canRead && 'cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 ease-out'
      )}
      onClick={handleCardClick}
    >
      {/* Action buttons */}
      <div className="shrink-0 flex flex-col gap-1.5 justify-center">
        {/* File type button */}
        <div className="relative">
          <Button
            ref={ftButtonRef}
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); setFtDropdownOpen(!ftDropdownOpen); }}
            className="h-8 w-10 p-0 text-[10px] font-bold text-text-tertiary hover:text-primary dark:hover:text-primary hover:bg-surface-100 dark:hover:bg-surface-100"
            title={`File type: ${getFileTypeLabel(doc)}`}
          >
            {getFileTypeLabel(doc)}
          </Button>
          {ftDropdownOpen && (
            <div
              ref={ftDropdownRef}
              className="absolute left-full top-0 ml-1 z-50 bg-surface dark:bg-surface-200 rounded-lg shadow-lg border border-surface-200 dark:border-surface-200 py-1 min-w-[72px]"
              onClick={(e) => e.stopPropagation()}
            >
              {ftOptions.map((ft) => (
                <button
                  key={ft}
                  onClick={() => {
                    onUpdateFileType(ft)
                    setFtDropdownOpen(false)
                  }}
                  className="w-full px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 hover:text-text-primary text-left transition-colors"
                >
                  {ft.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => { e.stopPropagation(); onEdit(); }}
          className="h-8 w-8 p-0 text-text-tertiary hover:text-gray-700 dark:hover:text-slate-200 hover:bg-surface-100 dark:hover:bg-surface-100"
          title="Edit document"
        >
          <Pencil className="h-4 w-4" />
        </Button>

        {isImproved ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); setRevertOpen(true); }}
            disabled={!!improveTaskId || !!activeImproveTask}
            className="h-8 w-8 p-0 text-amber-500 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Revert improvement"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); setImproveOpen(true); }}
            disabled={!!improveTaskId || !!activeImproveTask}
            className="h-8 w-8 p-0 text-text-tertiary hover:text-primary dark:hover:text-primary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Improve with AI"
          >
            {improveTaskId
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Wand2 className="h-4 w-4" />
            }
          </Button>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => { e.stopPropagation(); setDeleteOpen(true); }}
          aria-label="Delete document"
          className="h-8 w-8 p-0 text-error hover:text-error dark:hover:text-error hover:bg-error-light dark:hover:bg-error/12"
          title="Delete document"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={(o) => { if (!acting) setDeleteOpen(o) }}
        title="Delete document?"
        description={`This will permanently delete "${doc.title}" and remove it from this knowledge tree. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        loading={acting}
        onConfirm={() => void handleConfirmDelete()}
      />

      {/* Improve modal — agent selection + mode toggle */}
      <ImproveDialog
        open={improveOpen}
        onOpenChange={(o) => { if (!acting) setImproveOpen(o) }}
        mode="formatting"
        modeSelectable
        onConfirm={handleConfirmImprove}
        isImproving={acting}
      />

      {/* Revert confirmation dialog */}
      <ConfirmDialog
        open={revertOpen}
        onOpenChange={(o) => { if (!acting) setRevertOpen(o) }}
        title="Revert to original?"
        description="This will replace the current (improved) content with the original version shown below."
        confirmLabel="Revert"
        cancelLabel="Keep improved"
        loading={acting}
        onConfirm={() => void handleConfirmRevert()}
        className="max-w-2xl"
      >
        <textarea
          readOnly
          value={doc.original_content ?? ''}
          className="w-full h-48 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2.5 text-xs text-text-secondary font-mono leading-relaxed resize-none focus:outline-none"
        />
      </ConfirmDialog>

      {/* Thumbnail */}
      <div className="shrink-0 w-[100px] h-[130px] rounded-md overflow-hidden bg-surface-100 dark:bg-surface-200 flex items-center justify-center">
        {isPdf && !thumbError ? (
          <img
            src={thumbnailUrl}
            alt={`Preview of ${doc.title}`}
            className="w-full h-full object-cover"
            onError={() => setThumbError(true)}
          />
        ) : resolvedExt === 'epub' ? (
          <div className="flex flex-col items-center gap-1 text-text-tertiary">
            <BookOpen className="h-8 w-8" />
            <span className="text-[10px] font-medium">EPUB</span>
          </div>
        ) : resolvedExt === 'txt' || resolvedExt === 'md' ? (
          <div className="flex flex-col items-center gap-1 text-text-tertiary">
            <FileText className="h-8 w-8" />
            <span className="text-[10px] font-medium">{resolvedExt.toUpperCase()}</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 text-text-tertiary">
            <FileText className="h-8 w-8" />
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

interface SplitChapterCardProps {
  pdfDoc: KnowledgeDocument
  splitEntries: SplitChapterEntry[]
  splitting: boolean
  splitError: string | null
  onEntriesChange: (entries: SplitChapterEntry[]) => void
  onSplit: () => void
  onCancel: () => void
}

function SplitChapterCard({
  pdfDoc,
  splitEntries,
  splitting,
  splitError,
  onEntriesChange,
  onSplit,
  onCancel,
}: SplitChapterCardProps) {
  const maxOffset = pdfDoc.page_end! - pdfDoc.page_start!
  const totalPages = maxOffset + 1
  const isValid = splitEntries.length >= 2 && splitEntries.every(
    (e) => !isNaN(parseInt(e.pageStart, 10)) && !isNaN(parseInt(e.pageEnd, 10))
  ) && splitError === null

  const handleEntryChange = (index: number, field: 'pageStart' | 'pageEnd' | 'title', value: string) => {
    const updated = splitEntries.map((entry, i) => i === index ? { ...entry, [field]: value } : entry)
    onEntriesChange(updated)
  }

  const handleAddEntry = () => {
    const last = splitEntries[splitEntries.length - 1]
    const lastEnd = parseInt(last.pageEnd, 10)
    onEntriesChange([...splitEntries, { pageStart: String(lastEnd + 1), pageEnd: String(maxOffset + 1), title: '' }])
  }

  const handleRemoveEntry = (index: number) => {
    const removed = splitEntries[index]
    const updated = splitEntries.filter((_, i) => i !== index)
    if (index > 0) {
      updated[index - 1] = { ...updated[index - 1], pageEnd: removed.pageEnd }
    }
    onEntriesChange(updated)
  }

  return (
    <div className="border border-primary/40 rounded-lg p-4 flex flex-col gap-3 bg-primary-light dark:bg-primary/12">
      <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
        <Scissors className="h-4 w-4" />
        Split Chapter
      </div>
      <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-md px-3 py-2">
        This will re-extract text, re-chunk, and update the vector store. It may take a moment.
      </div>
      <div className="text-xs text-text-tertiary">
        Current range: Pages 1 – {maxOffset + 1} ({totalPages} pages total)
      </div>
      <div className="text-xs font-medium text-text-primary">Resulting chapters:</div>
      <div className="flex flex-col gap-2">
        {splitEntries.map((entry, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-xs text-text-secondary w-5 shrink-0">{i + 1}.</span>
            <span className="text-xs text-text-secondary shrink-0">Pages</span>
            <Input
              type="number"
              className="w-[72px]"
              value={entry.pageStart}
              onChange={(e) => handleEntryChange(i, 'pageStart', e.target.value)}
              disabled={splitting}
            />
            <span className="text-xs text-text-secondary">–</span>
            <Input
              type="number"
              className="w-[72px]"
              value={entry.pageEnd}
              onChange={(e) => handleEntryChange(i, 'pageEnd', e.target.value)}
              disabled={splitting}
            />
            <span className="text-xs text-text-secondary shrink-0">Title:</span>
            <Input
              type="text"
              className="flex-1 min-w-0"
              placeholder={`Chapter title (optional)`}
              value={entry.title}
              onChange={(e) => handleEntryChange(i, 'title', e.target.value)}
              disabled={splitting}
            />
            {i > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleRemoveEntry(i)}
                disabled={splitting}
                className="h-8 w-8 p-0 shrink-0"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        ))}
      </div>
      {splitError && (
        <div className="text-xs text-red-500">{splitError}</div>
      )}
      <div className="flex gap-2">
        <Button variant="ghost" size="sm" onClick={handleAddEntry} disabled={splitting}>
          <Plus className="h-3.5 w-3.5 mr-1" />
          Add Chapter
        </Button>
      </div>
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={splitting}>
          <X className="h-3.5 w-3.5 mr-1" />
          Cancel
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={onSplit}
          disabled={!isValid || splitting}
        >
          {splitting ? (
            <>
              <div className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin mr-1" />
              Splitting...
            </>
          ) : (
            <>
              <Scissors className="h-3.5 w-3.5 mr-1" />
              Split Chapter
            </>
          )}
        </Button>
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
