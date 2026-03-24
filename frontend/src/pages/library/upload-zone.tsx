import * as React from 'react'
import { Upload } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useUploadStore } from '../../stores/upload-store'
import { client } from '../../services'
import { UploadMetadataDialog } from '../../components/dialogs/upload-metadata-dialog'
import { ChapterSelectionDialog } from '../../components/dialogs/chapter-selection-dialog'
import type { DocumentPreviewOut } from '../../types/api'

const ACCEPTED_TYPES = '.pdf,.epub,.txt,.md'

type UploadPhase = 'idle' | 'metadata' | 'chapter-select' | 'submitting'

export function UploadZone() {
  const startUpload = useUploadStore((state) => state.startUpload)
  const [isDragOver, setIsDragOver] = React.useState(false)
  const [pendingFile, setPendingFile] = React.useState<File | null>(null)
  const [phase, setPhase] = React.useState<UploadPhase>('idle')
  const [preview, setPreview] = React.useState<DocumentPreviewOut | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = React.useState(false)
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    const file = files[0]
    setPendingFile(file)
    loadPreview(file)
  }

  async function loadPreview(file: File) {
    setIsLoadingPreview(true)
    setPhase('chapter-select')
    try {
      const result = await client.previewDocument(file)
      setPreview(result)
    } catch (err) {
      console.error('Failed to preview document:', err)
      setPhase('metadata')
    } finally {
      setIsLoadingPreview(false)
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
    handleFiles(e.dataTransfer.files)
  }

  function onClick() {
    inputRef.current?.click()
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files)
    e.target.value = ''
  }

  function handleMetadataSubmit(documentType: string, description: string) {
    if (pendingFile) {
      void startUpload(pendingFile, documentType, description)
    }
    setPendingFile(null)
    setPhase('idle')
  }

  function handleChapterSelectSubmit(chapterIndices: number[], documentType: string, description: string) {
    if (!pendingFile || !preview) return

    setIsSubmitting(true)
    setPhase('submitting')

    client
      .ingestDocumentChapters(preview.file_hash, pendingFile, chapterIndices, documentType, description)
      .then((result) => {
        useUploadStore.getState().handleIngestTask(result.task_id, pendingFile!.name)
        resetUpload()
      })
      .catch((err) => {
        console.error('Failed to ingest document:', err)
        resetUpload()
      })
  }

  function handleDialogCancel() {
    resetUpload()
  }

  function handleBack() {
    setPreview(null)
    setPhase('metadata')
  }

  function resetUpload() {
    setPendingFile(null)
    setPreview(null)
    setPhase('idle')
    setIsSubmitting(false)
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

      <UploadMetadataDialog
        open={phase === 'metadata' && pendingFile !== null}
        fileName={pendingFile?.name ?? ''}
        onSubmit={handleMetadataSubmit}
        onCancel={handleDialogCancel}
      />

      <ChapterSelectionDialog
        open={phase === 'chapter-select' && pendingFile !== null}
        file={pendingFile}
        preview={preview}
        isLoading={isLoadingPreview}
        isSubmitting={isSubmitting}
        onSubmit={handleChapterSelectSubmit}
        onCancel={handleDialogCancel}
        onBack={handleBack}
      />
    </div>
  )
}
