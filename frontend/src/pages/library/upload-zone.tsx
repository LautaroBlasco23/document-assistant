import * as React from 'react'
import { Upload } from 'lucide-react'
import { cn } from '../../lib/cn'
import { Progress } from '../../components/ui/progress'
import { client } from '../../services'
import { useDocumentStore } from '../../stores/document-store'
import { useTask } from '../../hooks/use-task'

const ACCEPTED_TYPES = '.pdf,.epub,.txt,.md'

export function UploadZone() {
  const fetchDocuments = useDocumentStore((state) => state.fetchDocuments)
  const [isDragOver, setIsDragOver] = React.useState(false)
  const [taskId, setTaskId] = React.useState<string | null>(null)
  const [statusMessage, setStatusMessage] = React.useState<string | null>(null)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const { task } = useTask(taskId, async () => {
    setStatusMessage('Done!')
    await fetchDocuments()
    setTimeout(() => {
      setTaskId(null)
      setStatusMessage(null)
    }, 2000)
  })

  React.useEffect(() => {
    if (task?.status === 'failed') {
      setErrorMessage(task.error ?? 'Upload failed')
      setTaskId(null)
    } else if (task?.progress) {
      setStatusMessage(task.progress)
    }
  }, [task])

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    const file = files[0]
    setErrorMessage(null)
    setStatusMessage('Uploading...')

    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await client.ingestDocument(formData)
      setTaskId(result.task_id)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Upload failed')
      setStatusMessage(null)
    }
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(true)
  }

  function onDragLeave() {
    setIsDragOver(false)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
    void handleFiles(e.dataTransfer.files)
  }

  function onClick() {
    inputRef.current?.click()
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    void handleFiles(e.target.files)
    // Reset input so the same file can be re-uploaded
    e.target.value = ''
  }

  const isUploading = taskId !== null && task?.status !== 'completed' && task?.status !== 'failed'
  const progressValue = task?.status === 'completed' ? 100 : isUploading ? 60 : 0

  return (
    <div className="mb-6">
      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload files"
        className={cn(
          'border-2 border-dashed rounded-card p-8 text-center cursor-pointer transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
          isDragOver
            ? 'border-primary bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50',
        )}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={onClick}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
      >
        <Upload className="h-8 w-8 text-gray-400 mx-auto mb-3" />
        <p className="text-sm font-medium text-gray-700">
          Drop files here or click to upload
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Accepted formats: PDF, EPUB, TXT, MD
        </p>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={onInputChange}
        />
      </div>

      {/* Progress feedback */}
      {(isUploading || statusMessage) && !errorMessage && (
        <div className="mt-3 space-y-1.5">
          <Progress
            value={progressValue}
            indeterminate={isUploading && progressValue === 60}
          />
          {statusMessage && (
            <p className="text-xs text-gray-500 text-center">{statusMessage}</p>
          )}
        </div>
      )}

      {/* Error message */}
      {errorMessage && (
        <p className="mt-2 text-sm text-red-600 text-center">{errorMessage}</p>
      )}
    </div>
  )
}
