import * as React from 'react'
import { Eye, EyeOff } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { cn } from '../../lib/cn'
import { readerMarkdownComponents } from './markdownComponents'

interface EditableTextPanelProps {
  /** The text being edited (controlled). */
  value: string
  /** File type of the source document — controls preview behaviour. */
  fileType: string | null | undefined
  /** When true, Save / Cancel in the parent are in flight. Disables local preview toggle. */
  isSaving: boolean
  /** Optional error from the save attempt, displayed above the textarea. */
  error?: string | null
  /** True when this panel is for a `.md` doc and the live markdown preview is supported. */
  supportsPreview: boolean
  onChange: (next: string) => void
  className?: string
}

/**
 * Plain-text editor with an optional live markdown preview pane.
 *
 * Used by the viewer's "Edit" mode. The parent owns draft state and persistence;
 * this component only handles local UI (textarea + preview toggle).
 */
export function EditableTextPanel({
  value,
  fileType,
  isSaving,
  error,
  supportsPreview,
  onChange,
  className,
}: EditableTextPanelProps) {
  const [showPreview, setShowPreview] = React.useState(false)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  // Auto-grow the textarea up to a reasonable cap to reduce visual scroll-jump.
  React.useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 1200)}px`
  }, [value])

  return (
    <div className={cn('flex flex-col gap-2 h-full', className)}>
      {supportsPreview && (
        <div className="flex items-center justify-end">
          <button
            type="button"
            onClick={() => setShowPreview((p) => !p)}
            disabled={isSaving}
            className={cn(
              'inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-md border transition-colors',
              'border-surface-200 dark:border-surface-200',
              'text-text-secondary hover:text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            title={showPreview ? 'Hide preview' : 'Show preview'}
          >
            {showPreview ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            {showPreview ? 'Hide preview' : 'Preview'}
          </button>
        </div>
      )}

      {error && (
        <div className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      <div
        className={cn(
          'flex-1 min-h-0 grid gap-4',
          showPreview ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={isSaving}
          spellCheck={true}
          aria-label="Edit document text"
          className={cn(
            'w-full h-full min-h-[60vh] resize-none rounded-md border p-4 text-sm leading-relaxed',
            'font-mono whitespace-pre-wrap break-words',
            'bg-surface dark:bg-surface-200',
            'border-surface-200 dark:border-surface-200',
            'text-text-primary placeholder:text-text-tertiary',
            'focus:outline-none focus:ring-2 focus:ring-primary/40',
            'disabled:opacity-60 disabled:cursor-not-allowed'
          )}
        />

        {showPreview && (
          <div
            className={cn(
              'min-h-[60vh] max-h-[80vh] overflow-auto rounded-md border p-4 text-sm leading-relaxed',
              'bg-surface-100 dark:bg-bg-inset',
              'border-surface-200 dark:border-surface-200',
              'text-text-secondary'
            )}
            aria-label="Live preview"
          >
            {fileType === 'md' ? (
              <ReactMarkdown components={readerMarkdownComponents}>{value || ''}</ReactMarkdown>
            ) : (
              <p className="whitespace-pre-wrap break-words">{value}</p>
            )}
          </div>
        )}
      </div>

      <div className="text-[11px] text-text-tertiary">
        {fileType === 'md'
          ? 'Editing markdown source. Use the Preview pane to see how it renders.'
          : 'Editing raw text. Changes are saved to the document when you click Save.'}
      </div>
    </div>
  )
}
