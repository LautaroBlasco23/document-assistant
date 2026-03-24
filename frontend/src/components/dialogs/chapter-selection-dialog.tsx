import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { Check, ChevronDown, ChevronRight, Loader2, FileText } from 'lucide-react'
import { Button } from '../ui/button'
import { cn } from '../../lib/cn'
import type { DocumentPreviewOut, ChapterPreviewOut } from '../../types/api'

export interface ChapterSelectionDialogProps {
  open: boolean
  file: File | null
  preview: DocumentPreviewOut | null
  isLoading: boolean
  isSubmitting: boolean
  onSubmit: (chapterIndices: number[], documentType: string, description: string) => void
  onCancel: () => void
  onBack: () => void
}

export function ChapterSelectionDialog({
  open,
  file,
  preview,
  isLoading,
  isSubmitting,
  onSubmit,
  onCancel,
  onBack,
}: ChapterSelectionDialogProps) {
  const [selectedChapters, setSelectedChapters] = React.useState<Set<number>>(new Set())
  const [selectAll, setSelectAll] = React.useState(true)
  const [expandedChapters, setExpandedChapters] = React.useState<Set<number>>(new Set())
  const [documentType, setDocumentType] = React.useState('')
  const [description, setDescription] = React.useState('')

  React.useEffect(() => {
    if (open) {
      setSelectedChapters(new Set())
      setSelectAll(true)
      setExpandedChapters(new Set())
      setDocumentType('')
      setDescription('')
    }
  }, [open])

  React.useEffect(() => {
    if (preview && selectAll) {
      setSelectedChapters(new Set(preview.chapters.map((c) => c.index)))
    }
  }, [preview, selectAll])

  function toggleChapter(index: number) {
    const next = new Set(selectedChapters)
    if (next.has(index)) {
      next.delete(index)
    } else {
      next.add(index)
    }
    setSelectedChapters(next)
    setSelectAll(next.size === preview?.chapters.length)
  }

  function toggleAll() {
    if (selectAll && preview) {
      setSelectedChapters(new Set())
      setSelectAll(false)
    } else if (preview) {
      setSelectedChapters(new Set(preview.chapters.map((c) => c.index)))
      setSelectAll(true)
    }
  }

  function toggleExpand(index: number) {
    const next = new Set(expandedChapters)
    if (next.has(index)) {
      next.delete(index)
    } else {
      next.add(index)
    }
    setExpandedChapters(next)
  }

  function handleSubmit() {
    onSubmit(Array.from(selectedChapters), documentType, description)
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      onCancel()
    }
  }

  const selectedCount = selectedChapters.size
  const totalCount = preview?.chapters.length ?? 0

  return (
    <RadixDialog.Root open={open} onOpenChange={handleOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-2xl max-h-[85vh] bg-white rounded-card shadow-lg flex flex-col',
            'animate-fade-in',
          )}
        >
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between mb-1">
              <RadixDialog.Title className="text-lg font-semibold text-gray-900">
                Select chapters to process
              </RadixDialog.Title>
              <RadixDialog.Title className="text-sm text-gray-500">
                {preview ? `${selectedCount} of ${totalCount} selected` : 'Preview loading...'}
              </RadixDialog.Title>
            </div>
            <RadixDialog.Description className="text-sm text-gray-500 truncate">
              {file?.name ?? 'Select a file to preview'}
            </RadixDialog.Description>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {isLoading && (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <Loader2 className="h-8 w-8 animate-spin mb-3" />
                <p className="text-sm">Analyzing document structure...</p>
              </div>
            )}

            {!isLoading && preview && (
              <div className="space-y-2">
                <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
                  <button
                    type="button"
                    onClick={toggleAll}
                    className={cn(
                      'flex items-center gap-2 text-sm font-medium transition-colors',
                      selectedCount === totalCount ? 'text-primary' : 'text-gray-600 hover:text-gray-900',
                    )}
                  >
                    <div
                      className={cn(
                        'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
                        selectedCount === totalCount
                          ? 'bg-primary border-primary'
                          : 'border-gray-300 bg-white',
                      )}
                    >
                      {selectedCount === totalCount && <Check className="h-3 w-3 text-white" />}
                    </div>
                    Select all chapters
                  </button>
                </div>

                <div className="text-xs text-gray-400 mb-2">
                  {selectedCount === 0
                    ? 'No chapters selected — choose which chapters to process with AI'
                    : `${selectedCount} chapter${selectedCount !== 1 ? 's' : ''} will be processed`}
                </div>

                {preview.chapters.map((chapter) => (
                  <ChapterItem
                    key={chapter.index}
                    chapter={chapter}
                    isSelected={selectedChapters.has(chapter.index)}
                    isExpanded={expandedChapters.has(chapter.index)}
                    onToggleSelect={() => toggleChapter(chapter.index)}
                    onToggleExpand={() => toggleExpand(chapter.index)}
                  />
                ))}
              </div>
            )}

            {!isLoading && !preview && (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <FileText className="h-8 w-8 mb-3" />
                <p className="text-sm">No chapters found</p>
              </div>
            )}
          </div>

          <div className="p-6 border-t border-gray-200 bg-gray-50">
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Document type</label>
                <select
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                >
                  <option value="">Select type (optional)</option>
                  <option value="book">Book</option>
                  <option value="paper">Paper</option>
                  <option value="documentation">Documentation</option>
                  <option value="article">Article</option>
                  <option value="notes">Notes</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Description</label>
                <input
                  type="text"
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Brief description (optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-between items-center">
              <Button
                type="button"
                variant="ghost"
                onClick={onBack}
                disabled={isSubmitting}
              >
                Back
              </Button>
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={onCancel}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  onClick={handleSubmit}
                  disabled={isSubmitting || selectedCount === 0}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    `Process ${selectedCount} chapter${selectedCount !== 1 ? 's' : ''}`
                  )}
                </Button>
              </div>
            </div>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}

interface ChapterItemProps {
  chapter: ChapterPreviewOut
  isSelected: boolean
  isExpanded: boolean
  onToggleSelect: () => void
  onToggleExpand: () => void
}

function ChapterItem({ chapter, isSelected, isExpanded, onToggleSelect, onToggleExpand }: ChapterItemProps) {
  return (
    <div
      className={cn(
        'rounded-lg border transition-colors',
        isSelected ? 'border-primary bg-blue-50/50' : 'border-gray-200 bg-white hover:border-gray-300',
      )}
    >
      <div className="flex items-center gap-3 p-3">
        <button
          type="button"
          onClick={onToggleSelect}
          className="flex-shrink-0"
        >
          <div
            className={cn(
              'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
              isSelected ? 'bg-primary border-primary' : 'border-gray-300 bg-white',
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
            isSelected ? 'bg-primary/10 text-primary' : 'bg-gray-100 text-gray-500',
          )}
        >
          {isSelected ? 'Selected' : 'Skipped'}
        </div>
      </div>
    </div>
  )
}
