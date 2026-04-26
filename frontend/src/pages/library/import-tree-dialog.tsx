import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, ChevronDown, ChevronRight, FileText, Loader2, Upload } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Progress } from '../../components/ui/progress'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import type { DocumentPreviewOut, ChapterPreviewOut } from '../../types/api'

interface ImportTreeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (treeId: string) => void
}

type DialogStep = 'upload' | 'select-chapters'
type ImportState = 'idle' | 'previewing' | 'importing' | 'polling' | 'done' | 'error'

export function ImportTreeDialog({ open, onOpenChange, onSuccess }: ImportTreeDialogProps) {
  const navigate = useNavigate()
  const fetchTrees = useKnowledgeTreeStore((s) => s.fetchTrees)
  const createTreeFromFile = useKnowledgeTreeStore((s) => s.createTreeFromFile)

  const [step, setStep] = React.useState<DialogStep>('upload')
  const [file, setFile] = React.useState<File | null>(null)
  const [title, setTitle] = React.useState('')
  const [state, setState] = React.useState<ImportState>('idle')
  const [progress, setProgress] = React.useState(0)
  const [progressMsg, setProgressMsg] = React.useState('')
  const [errorMsg, setErrorMsg] = React.useState('')

  // Chapter selection state
  const [preview, setPreview] = React.useState<DocumentPreviewOut | null>(null)
  const [selectedChapters, setSelectedChapters] = React.useState<Set<number>>(new Set())
  const [expandedChapters, setExpandedChapters] = React.useState<Set<number>>(new Set())

  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const pollIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null)

  const derivedTitle = title.trim() || (file ? file.name.replace(/\.(pdf|epub)$/i, '') : '')

  const stopPolling = () => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  const reset = () => {
    stopPolling()
    setStep('upload')
    setFile(null)
    setTitle('')
    setState('idle')
    setProgress(0)
    setProgressMsg('')
    setErrorMsg('')
    setPreview(null)
    setSelectedChapters(new Set())
    setExpandedChapters(new Set())
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleClose = () => {
    if (state === 'previewing' || state === 'importing' || state === 'polling') return
    reset()
    onOpenChange(false)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null
    setFile(f)
    if (f && !title.trim()) {
      setTitle(f.name.replace(/\.(pdf|epub)$/i, ''))
    }
  }

  const handleNext = async () => {
    if (!file) return
    setState('previewing')
    setErrorMsg('')

    try {
      const result = await client.previewKnowledgeTreeFile(file)
      setState('idle')

      if (result.chapters.length <= 1) {
        // Single chapter or no chapters: skip selection and import directly
        await startImport(null)
        return
      }

      setPreview(result)
      setSelectedChapters(new Set(result.chapters.map((c) => c.index)))
      setStep('select-chapters')
    } catch {
      setState('error')
      setErrorMsg('Failed to preview document. Check the file and try again.')
    }
  }

  const startImport = async (chapterIndices: number[] | null) => {
    if (!file) return
    setState('importing')
    setProgress(0)
    setProgressMsg('Uploading file...')
    setErrorMsg('')

    try {
      const taskId = await createTreeFromFile(
        file,
        derivedTitle || undefined,
        chapterIndices ?? undefined,
      )
      setState('polling')

      pollIntervalRef.current = setInterval(() => {
        void (async () => {
          try {
            const status = await client.getTaskStatus(taskId)
            setProgress(status.progress_pct ?? 0)
            setProgressMsg(status.progress ?? '')

            if (status.status === 'completed') {
              stopPolling()
              setState('done')
              await fetchTrees()
              const treeId = (status.result as { tree_id?: string } | null)?.tree_id
              if (treeId) {
                onSuccess(treeId)
                reset()
                onOpenChange(false)
                navigate(`/trees/${treeId}`)
              }
            } else if (status.status === 'failed') {
              stopPolling()
              setState('error')
              setErrorMsg(status.error ?? 'Import failed')
            }
          } catch {
            stopPolling()
            setState('error')
            setErrorMsg('Failed to poll task status')
          }
        })()
      }, 1500)
    } catch {
      setState('error')
      setErrorMsg('Failed to start import')
    }
  }

  const handleImport = () => {
    const indices = Array.from(selectedChapters)
    void startImport(indices)
  }

  // Cleanup on unmount
  React.useEffect(() => {
    return () => stopPolling()
  }, [])

  if (!open) return null

  const isRunning = state === 'previewing' || state === 'importing' || state === 'polling'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface dark:bg-surface-200 rounded-xl shadow-xl w-full max-w-md mx-4 flex flex-col">
        {step === 'upload' ? (
          <UploadStep
            file={file}
            title={title}
            state={state}
            isRunning={isRunning}
            errorMsg={errorMsg}
            fileInputRef={fileInputRef}
            onFileChange={handleFileChange}
            onTitleChange={setTitle}
            onNext={() => void handleNext()}
            onCancel={handleClose}
          />
        ) : (
          <SelectChaptersStep
            file={file}
            preview={preview}
            selectedChapters={selectedChapters}
            expandedChapters={expandedChapters}
            state={state}
            progress={progress}
            progressMsg={progressMsg}
            errorMsg={errorMsg}
            isRunning={isRunning}
            onToggleChapter={(index) => {
              const next = new Set(selectedChapters)
              if (next.has(index)) next.delete(index)
              else next.add(index)
              setSelectedChapters(next)
            }}
            onToggleAll={() => {
              if (!preview) return
              if (selectedChapters.size === preview.chapters.length) {
                setSelectedChapters(new Set())
              } else {
                setSelectedChapters(new Set(preview.chapters.map((c) => c.index)))
              }
            }}
            onToggleExpand={(index) => {
              const next = new Set(expandedChapters)
              if (next.has(index)) next.delete(index)
              else next.add(index)
              setExpandedChapters(next)
            }}
            onImport={handleImport}
            onBack={() => {
              setStep('upload')
              setPreview(null)
              setSelectedChapters(new Set())
              setExpandedChapters(new Set())
              setState('idle')
              setErrorMsg('')
            }}
            onCancel={handleClose}
          />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 1: Upload
// ---------------------------------------------------------------------------

interface UploadStepProps {
  file: File | null
  title: string
  state: ImportState
  isRunning: boolean
  errorMsg: string
  fileInputRef: React.RefObject<HTMLInputElement>
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onTitleChange: (v: string) => void
  onNext: () => void
  onCancel: () => void
}

function UploadStep({
  file,
  title,
  state,
  isRunning,
  errorMsg,
  fileInputRef,
  onFileChange,
  onTitleChange,
  onNext,
  onCancel,
}: UploadStepProps) {
  return (
    <div className="p-6 flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Import from Document</h2>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Upload a PDF or EPUB to automatically create a knowledge tree with chapters extracted from the document.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {/* File picker */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="import-file" className="text-sm font-medium text-gray-700 dark:text-slate-300">
            File <span className="text-red-400">*</span>
          </label>
          <div className="flex items-center gap-2">
            <input
              id="import-file"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.epub"
              className="hidden"
              onChange={onFileChange}
              disabled={isRunning}
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={isRunning}
            >
              <Upload className="w-4 h-4 mr-1" />
              Choose file
            </Button>
            {file && (
              <span className="text-sm text-gray-600 dark:text-slate-400 truncate" title={file.name}>
                {file.name}
              </span>
            )}
          </div>
        </div>

        {/* Title input */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="import-title" className="text-sm font-medium text-gray-700 dark:text-slate-300">
            Title <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <Input
            id="import-title"
            placeholder={file ? file.name.replace(/\.(pdf|epub)$/i, '') : 'e.g. Machine Learning Fundamentals'}
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            disabled={isRunning}
          />
        </div>

        {/* Previewing spinner */}
        {state === 'previewing' && (
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing document structure...
          </div>
        )}

        {/* Error message */}
        {state === 'error' && errorMsg && (
          <p className="text-sm text-red-600">{errorMsg}</p>
        )}
      </div>

      <div className="flex gap-2 justify-end pt-1">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={isRunning}>
          Cancel
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={onNext}
          disabled={!file || isRunning}
        >
          {state === 'previewing' ? (
            <>
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
              Analyzing...
            </>
          ) : (
            'Next'
          )}
        </Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 2: Select chapters
// ---------------------------------------------------------------------------

interface SelectChaptersStepProps {
  file: File | null
  preview: DocumentPreviewOut | null
  selectedChapters: Set<number>
  expandedChapters: Set<number>
  state: ImportState
  progress: number
  progressMsg: string
  errorMsg: string
  isRunning: boolean
  onToggleChapter: (index: number) => void
  onToggleAll: () => void
  onToggleExpand: (index: number) => void
  onImport: () => void
  onBack: () => void
  onCancel: () => void
}

function SelectChaptersStep({
  file,
  preview,
  selectedChapters,
  expandedChapters,
  state,
  progress,
  progressMsg,
  errorMsg,
  isRunning,
  onToggleChapter,
  onToggleAll,
  onToggleExpand,
  onImport,
  onBack,
  onCancel,
}: SelectChaptersStepProps) {
  const selectedCount = selectedChapters.size
  const totalCount = preview?.chapters.length ?? 0

  return (
    <div className="flex flex-col max-h-[85vh]">
      {/* Header */}
      <div className="p-6 border-b border-surface-200 dark:border-surface-200">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Select chapters to import</h2>
          <span className="text-sm text-gray-500 dark:text-slate-400">
            {selectedCount} of {totalCount} selected
          </span>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400 truncate">{file?.name ?? ''}</p>
      </div>

      {/* Chapter list */}
      <div className="flex-1 overflow-y-auto p-6">
        {preview && (
          <div className="space-y-2">
            <div className="flex items-center gap-3 pb-3 border-b border-surface-200 dark:border-surface-200">
              <button
                type="button"
                onClick={onToggleAll}
                disabled={isRunning}
                className={cn(
                  'flex items-center gap-2 text-sm font-medium transition-colors',
                  selectedCount === totalCount ? 'text-primary' : 'text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-slate-100',
                )}
              >
                <div
                  className={cn(
                    'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
                    selectedCount === totalCount
                      ? 'bg-primary border-primary'
                      : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200',
                  )}
                >
                  {selectedCount === totalCount && <Check className="h-3 w-3 text-white" />}
                </div>
                Select all chapters
              </button>
            </div>

            <div className="text-xs text-gray-400 dark:text-slate-500 mb-2">
              {selectedCount === 0
                ? 'No chapters selected — select at least one to import'
                : `${selectedCount} chapter${selectedCount !== 1 ? 's' : ''} will be imported`}
            </div>

            {preview.chapters.map((chapter) => (
              <ChapterItem
                key={chapter.index}
                chapter={chapter}
                isSelected={selectedChapters.has(chapter.index)}
                isExpanded={expandedChapters.has(chapter.index)}
                disabled={isRunning}
                onToggleSelect={() => onToggleChapter(chapter.index)}
                onToggleExpand={() => onToggleExpand(chapter.index)}
              />
            ))}
          </div>
        )}

        {!preview && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400 dark:text-slate-500">
            <FileText className="h-8 w-8 mb-3" />
            <p className="text-sm">No chapters found</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-6 border-t border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface">
        {/* Progress display during import */}
        {(state === 'importing' || state === 'polling') && (
          <div className="flex flex-col gap-2 mb-4">
            <Progress value={progress > 0 ? progress : undefined} indeterminate={progress === 0} />
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-500 dark:text-slate-400">{progressMsg || 'Processing...'}</p>
              {progress > 0 && (
                <span className="text-xs font-medium text-gray-500 dark:text-slate-400">{progress}%</span>
              )}
            </div>
          </div>
        )}

        {/* Error message */}
        {state === 'error' && errorMsg && (
          <p className="text-sm text-red-600 mb-4">{errorMsg}</p>
        )}

        <div className="flex justify-between items-center">
          <Button type="button" variant="ghost" onClick={onBack} disabled={isRunning}>
            Back
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onCancel} disabled={isRunning}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={onImport}
              disabled={isRunning || selectedCount === 0}
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                `Import ${selectedCount} chapter${selectedCount !== 1 ? 's' : ''}`
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Chapter item row
// ---------------------------------------------------------------------------

interface ChapterItemProps {
  chapter: ChapterPreviewOut
  isSelected: boolean
  isExpanded: boolean
  disabled: boolean
  onToggleSelect: () => void
  onToggleExpand: () => void
}

function ChapterItem({
  chapter,
  isSelected,
  isExpanded,
  disabled,
  onToggleSelect,
  onToggleExpand,
}: ChapterItemProps) {
  return (
    <div
      className={cn(
        'rounded-lg border transition-colors',
        isSelected ? 'border-primary bg-primary-light dark:bg-primary/12' : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 hover:border-surface-200 dark:hover:border-surface-200',
      )}
    >
      <div className="flex items-center gap-3 p-3">
        <button
          type="button"
          onClick={onToggleSelect}
          disabled={disabled}
          className="flex-shrink-0"
        >
          <div
            className={cn(
              'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
              isSelected ? 'bg-primary border-primary' : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200',
            )}
          >
            {isSelected && <Check className="h-3 w-3 text-white" />}
          </div>
        </button>

        <button
          type="button"
          onClick={onToggleExpand}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600"
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          onClick={onToggleSelect}
          disabled={disabled}
          className="flex-1 text-left"
        >
          <div className="font-medium text-gray-900">{chapter.title}</div>
          <div className="text-xs text-gray-500">
            Pages {chapter.page_start}
            {chapter.page_end !== chapter.page_start && ` - ${chapter.page_end}`}
          </div>
        </button>

        <div
          className={cn(
            'text-xs px-2 py-1 rounded-full',
            isSelected ? 'bg-primary/10 text-primary' : 'bg-surface-100 dark:bg-surface-200 text-gray-500 dark:text-slate-400',
          )}
        >
          {isSelected ? 'Selected' : 'Skipped'}
        </div>
      </div>
    </div>
  )
}
