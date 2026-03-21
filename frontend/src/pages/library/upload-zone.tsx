import * as React from 'react'
import { Upload } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useUploadStore } from '../../stores/upload-store'

const ACCEPTED_TYPES = '.pdf,.epub,.txt,.md'

export function UploadZone() {
  const startUpload = useUploadStore((state) => state.startUpload)
  const [isDragOver, setIsDragOver] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    void startUpload(files[0])
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
    handleFiles(e.dataTransfer.files)
  }

  function onClick() {
    inputRef.current?.click()
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files)
    // Reset input so the same file can be re-uploaded
    e.target.value = ''
  }

  return (
    <div className="mb-6">
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
    </div>
  )
}
