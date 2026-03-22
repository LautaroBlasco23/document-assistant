import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { Button } from '../ui/button'
import { Select } from '../ui/select'
import { cn } from '../../lib/cn'

const DOCUMENT_TYPES = [
  { value: 'book', label: 'Book' },
  { value: 'paper', label: 'Paper' },
  { value: 'documentation', label: 'Documentation' },
  { value: 'article', label: 'Article' },
  { value: 'notes', label: 'Notes' },
  { value: 'other', label: 'Other' },
]

const DESCRIPTION_MAX_LENGTH = 500

export interface UploadMetadataDialogProps {
  open: boolean
  fileName: string
  onSubmit: (documentType: string, description: string) => void
  onCancel: () => void
}

export function UploadMetadataDialog({
  open,
  fileName,
  onSubmit,
  onCancel,
}: UploadMetadataDialogProps) {
  const [documentType, setDocumentType] = React.useState('')
  const [description, setDescription] = React.useState('')

  // Reset form when dialog opens
  React.useEffect(() => {
    if (open) {
      setDocumentType('')
      setDescription('')
    }
  }, [open])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit(documentType, description)
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      onCancel()
    }
  }

  return (
    <RadixDialog.Root open={open} onOpenChange={handleOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-md bg-white rounded-card shadow-lg p-6',
            'animate-fade-in',
          )}
        >
          <RadixDialog.Title className="text-lg font-semibold text-gray-900 mb-1">
            Upload document
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 mb-4 truncate">
            {fileName}
          </RadixDialog.Description>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Select
              label="Document type"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
            >
              <option value="">Select a type (optional)</option>
              {DOCUMENT_TYPES.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>

            <div className="flex flex-col gap-1">
              <label
                htmlFor="upload-description"
                className="text-sm font-medium text-gray-700"
              >
                Description
                <span className="text-gray-400 font-normal ml-1">(optional)</span>
              </label>
              <textarea
                id="upload-description"
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                rows={3}
                maxLength={DESCRIPTION_MAX_LENGTH}
                placeholder="Brief description of this document..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <p className={cn(
                'text-xs text-right',
                description.length >= DESCRIPTION_MAX_LENGTH ? 'text-red-400' : 'text-gray-400',
              )}>
                {description.length}/{DESCRIPTION_MAX_LENGTH}
              </p>
            </div>

            <div className="flex justify-end gap-3 mt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={onCancel}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
              >
                Upload
              </Button>
            </div>
          </form>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
