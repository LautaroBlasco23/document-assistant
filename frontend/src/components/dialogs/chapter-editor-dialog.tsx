import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { cn } from '../../lib/cn'
import { useDocumentStore } from '../../stores/document-store'

const WORD_COUNT_WARNING = 30000
const WORD_COUNT_CRITICAL = 50000

function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length
}

function extractChapterContent(fullContent: string, chapterNumber: number, totalChapters: number): { content: string; title: string } {
  const lines = fullContent.split('\n')
  
  let chapterStart = -1
  let chapterTitle = ''
  let currentChapter = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const isSeparator = /^#{3,}\s*$/.test(line)
    const isMarkdownHeader = /^#\s+/.test(line)
    
    if (isSeparator || isMarkdownHeader) {
      currentChapter++
      if (currentChapter === chapterNumber) {
        chapterStart = i + 1
        if (isMarkdownHeader) {
          chapterTitle = line.replace(/^#\s+/, '').trim()
        }
      } else if (currentChapter > chapterNumber) {
        break
      }
    }
  }

  if (chapterStart === -1) {
    const contentPerChapter = Math.floor(lines.length / totalChapters)
    chapterStart = (chapterNumber - 1) * contentPerChapter
  }

  let chapterEnd = lines.length
  for (let i = chapterStart; i < lines.length; i++) {
    const line = lines[i]
    const isSeparator = /^#{3,}\s*$/.test(line)
    const isMarkdownHeader = /^#\s+/.test(line)
    
    if ((isSeparator || isMarkdownHeader) && i > chapterStart) {
      chapterEnd = i
      break
    }
  }

  const content = lines.slice(chapterStart, chapterEnd).join('\n').trim()

  if (!chapterTitle) {
    chapterTitle = `Chapter ${chapterNumber}`
  }

  return { content, title: chapterTitle }
}

export interface ChapterEditorDialogProps {
  open: boolean
  onClose: () => void
  docHash: string
  chapterNumber: number
  totalChapters: number
  initialContent?: string
  onSave?: (newHash?: string) => void
}

export function ChapterEditorDialog({
  open,
  onClose,
  docHash,
  chapterNumber,
  totalChapters,
  initialContent,
  onSave,
}: ChapterEditorDialogProps) {
  const [content, setContent] = React.useState('')
  const [title, setTitle] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const fetchContent = useDocumentStore((s) => s.fetchContent)
  const updateContent = useDocumentStore((s) => s.updateContent)

  React.useEffect(() => {
    if (open) {
      setLoading(true)
      setSaving(false)
      
      if (initialContent) {
        const extracted = extractChapterContent(initialContent, chapterNumber, totalChapters)
        setContent(extracted.content)
        setTitle(extracted.title)
        setLoading(false)
      } else {
        fetchContent(docHash)
          .then((fullContent) => {
            if (fullContent) {
              const extracted = extractChapterContent(fullContent, chapterNumber, totalChapters)
              setContent(extracted.content)
              setTitle(extracted.title)
            }
          })
          .finally(() => setLoading(false))
      }
    }
  }, [open, docHash, chapterNumber, totalChapters, initialContent, fetchContent])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim() || saving) return
    
    setSaving(true)
    try {
      const fullContent = await fetchContent(docHash)
      if (!fullContent) {
        throw new Error('Could not fetch document content')
      }

      const lines = fullContent.split('\n')
      let chapterStart = -1
      let currentChapter = 0

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const isSeparator = /^#{3,}\s*$/.test(line)
        const isMarkdownHeader = /^#\s+/.test(line)
        
        if (isSeparator || isMarkdownHeader) {
          currentChapter++
          if (currentChapter === chapterNumber) {
            chapterStart = i
            break
          }
        }
      }

      if (chapterStart === -1) {
        const contentPerChapter = Math.floor(lines.length / totalChapters)
        chapterStart = (chapterNumber - 1) * contentPerChapter
      }

      let chapterEnd = lines.length
      for (let i = chapterStart + 1; i < lines.length; i++) {
        const line = lines[i]
        const isSeparator = /^#{3,}\s*$/.test(line)
        const isMarkdownHeader = /^#\s+/.test(line)
        
        if ((isSeparator || isMarkdownHeader) && i > chapterStart) {
          chapterEnd = i
          break
        }
      }

      const newChapterLine = `###\n# ${title.trim() || `Chapter ${chapterNumber}`}\n###\n`
      const newContent = [
        ...lines.slice(0, chapterStart),
        newChapterLine,
        content.trim(),
        ...lines.slice(chapterEnd),
      ].join('\n')

      const resp = await updateContent(docHash, newContent)
      onSave?.(resp.new_hash)
      onClose()
    } catch {
      // error handled by interceptor
    } finally {
      setSaving(false)
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      onClose()
    }
  }

  const wordCount = countWords(content)
  const canSubmit = content.trim().length > 0 && !saving && !loading

  return (
    <RadixDialog.Root open={open} onOpenChange={handleOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-2xl bg-white rounded-card shadow-lg p-6',
            'animate-fade-in max-h-[90vh] overflow-y-auto',
          )}
        >
          <RadixDialog.Title className="text-lg font-semibold text-gray-900 mb-1">
            Edit Chapter {chapterNumber}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-gray-500 mb-4">
            Use <code className="text-xs bg-gray-100 px-1 rounded">###</code> separators with <code className="text-xs bg-gray-100 px-1 rounded"># Chapter Name</code> to create chapter breaks.
          </RadixDialog.Description>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <span className="text-gray-400">Loading chapter...</span>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input
                label="Chapter Title"
                placeholder={`Chapter ${chapterNumber}`}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />

              <div className="flex flex-col gap-1">
                <label htmlFor="chapter-content" className="text-sm font-medium text-gray-700">
                  Content
                </label>
                <textarea
                  id="chapter-content"
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y font-mono"
                  rows={15}
                  placeholder="Chapter content..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  disabled={saving}
                />
                <p className={cn(
                  'text-xs text-right',
                  wordCount > WORD_COUNT_CRITICAL ? 'text-red-500 font-medium' :
                  wordCount > WORD_COUNT_WARNING ? 'text-orange-500' :
                  'text-gray-400',
                )}>
                  {wordCount.toLocaleString()} words
                </p>
              </div>

              <p className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
                Saving will re-process this document. Existing summaries/flashcards for unchanged chapters will be preserved.
              </p>

              <div className="flex justify-end gap-3 mt-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={onClose}
                  disabled={saving}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={!canSubmit}
                >
                  {saving ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </form>
          )}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
