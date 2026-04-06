import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Progress } from '../../components/ui/progress'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { client } from '../../services'

interface ImportTreeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (treeId: string) => void
}

type ImportState = 'idle' | 'importing' | 'polling' | 'done' | 'error'

export function ImportTreeDialog({ open, onOpenChange, onSuccess }: ImportTreeDialogProps) {
  const navigate = useNavigate()
  const fetchTrees = useKnowledgeTreeStore((s) => s.fetchTrees)
  const createTreeFromFile = useKnowledgeTreeStore((s) => s.createTreeFromFile)

  const [file, setFile] = React.useState<File | null>(null)
  const [title, setTitle] = React.useState('')
  const [state, setState] = React.useState<ImportState>('idle')
  const [progress, setProgress] = React.useState(0)
  const [progressMsg, setProgressMsg] = React.useState('')
  const [errorMsg, setErrorMsg] = React.useState('')

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
    setFile(null)
    setTitle('')
    setState('idle')
    setProgress(0)
    setProgressMsg('')
    setErrorMsg('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleClose = () => {
    if (state === 'importing' || state === 'polling') return
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

  const handleImport = async () => {
    if (!file) return
    setState('importing')
    setProgress(0)
    setProgressMsg('Uploading file...')
    setErrorMsg('')

    try {
      const taskId = await createTreeFromFile(file, derivedTitle || undefined)
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

  // Cleanup on unmount
  React.useEffect(() => {
    return () => stopPolling()
  }, [])

  if (!open) return null

  const isRunning = state === 'importing' || state === 'polling'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 flex flex-col gap-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Import from Document</h2>
          <p className="text-sm text-gray-500 mt-1">
            Upload a PDF or EPUB to automatically create a knowledge tree with chapters extracted from the document.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          {/* File picker */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="import-file" className="text-sm font-medium text-gray-700">
              File <span className="text-red-400">*</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="import-file"
                ref={fileInputRef}
                type="file"
                accept=".pdf,.epub"
                className="hidden"
                onChange={handleFileChange}
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
                <span className="text-sm text-gray-600 truncate" title={file.name}>
                  {file.name}
                </span>
              )}
            </div>
          </div>

          {/* Title input */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="import-title" className="text-sm font-medium text-gray-700">
              Title <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <Input
              id="import-title"
              placeholder={file ? file.name.replace(/\.(pdf|epub)$/i, '') : 'e.g. Machine Learning Fundamentals'}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isRunning}
            />
          </div>

          {/* Progress display */}
          {isRunning && (
            <div className="flex flex-col gap-2">
              <Progress value={progress > 0 ? progress : undefined} indeterminate={progress === 0} />
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">{progressMsg || 'Processing...'}</p>
                {progress > 0 && (
                  <span className="text-xs font-medium text-gray-500">{progress}%</span>
                )}
              </div>
            </div>
          )}

          {/* Error message */}
          {state === 'error' && errorMsg && (
            <p className="text-sm text-red-600">{errorMsg}</p>
          )}
        </div>

        <div className="flex gap-2 justify-end pt-1">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isRunning}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={() => void handleImport()}
            disabled={!file || isRunning}
          >
            {isRunning ? 'Importing...' : 'Import'}
          </Button>
        </div>
      </div>
    </div>
  )
}
