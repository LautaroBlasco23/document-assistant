import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Select } from '../ui/select'
import { cn } from '../../lib/cn'
import { useUploadStore } from '../../stores/upload-store'

const DOCUMENT_TYPES = [
  { value: 'book', label: 'Book' },
  { value: 'paper', label: 'Paper' },
  { value: 'documentation', label: 'Documentation' },
  { value: 'article', label: 'Article' },
  { value: 'notes', label: 'Notes' },
  { value: 'other', label: 'Other' },
]

const DESCRIPTION_MAX_LENGTH = 500

export interface CreateDocumentDialogProps {
  open: boolean
  onClose: () => void
}

export function CreateDocumentDialog({ open, onClose }: CreateDocumentDialogProps) {
  const [title, setTitle] = React.useState('')
  const [content, setContent] = React.useState('')
  const [documentType, setDocumentType] = React.useState('notes')
  const [description, setDescription] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)

  React.useEffect(() => {
    if (open) {
      setTitle('')
      setContent('')
      setDocumentType('notes')
      setDescription('')
      setSubmitting(false)
    }
  }, [open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    setSubmitting(true)
    try {
      await useUploadStore.getState().createDocument(title.trim(), content, documentType, description)
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      onClose()
    }
  }

  const canSubmit = title.trim().length > 0 && content.trim().length > 0 && !submitting

  return (
    <RadixDialog.Root open={open} onOpenChange={handleOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-lg bg-white rounded-card shadow-lg p-6',
            'animate-fade-in',
          )}
        >
          <RadixDialog.Title className="text-lg font-semibold text-gray-900 mb-1">
            Create document
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 mb-4">
            Paste or type text to create a new document.
          </RadixDialog.Description>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Title"
              required
              maxLength={200}
              placeholder="My notes..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            <div className="flex flex-col gap-1">
              <label htmlFor="create-content" className="text-sm font-medium text-gray-700">
                Content <span className="text-red-500">*</span>
              </label>
              <textarea
                id="create-content"
                required
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y"
                rows={10}
                placeholder="Paste your notes or text here..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </div>

            <Select
              label="Document type"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
            >
              {DOCUMENT_TYPES.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>

            <div className="flex flex-col gap-1">
              <label htmlFor="create-description" className="text-sm font-medium text-gray-700">
                Description
                <span className="text-gray-400 font-normal ml-1">(optional)</span>
              </label>
              <textarea
                id="create-description"
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                rows={2}
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
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={!canSubmit}
              >
                {submitting ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </form>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
