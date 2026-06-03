import * as React from 'react'
import { Type, FileText, Sparkles, RotateCcw, ChevronDown, Loader2, Pencil, Check, X } from 'lucide-react'
import { cn } from '../../lib/cn'

export type FormatMode = 'plain' | 'markdown'

interface FormatterMenuProps {
  mode: FormatMode
  isImproved: boolean
  isImproving: boolean
  onModeChange: (mode: FormatMode) => void
  onRequestImproveText: () => void
  onRequestImproveFormatting: () => void
  onRevert: () => void
  // --- Edit mode (manual text improvement) ---
  /** True while the user is editing the document text. Hides the format menu. */
  isEditing: boolean
  /** True while a Save request is in flight. Disables Save and Cancel. */
  isSaving: boolean
  /** True when the draft differs from the saved content. Disables Save until true. */
  isDirty: boolean
  /** Enters edit mode (and snapshots the baseline if needed). */
  onEnterEdit: () => void
  /** Persists the draft content to the document. */
  onSave: () => void
  /** Discards the draft and exits edit mode without saving. */
  onCancel: () => void
  /** True when entering edit mode is allowed (e.g. no AI improve in flight). */
  canEdit: boolean
}

export function FormatterMenu({
  mode,
  isImproved,
  isImproving,
  onModeChange,
  onRequestImproveText,
  onRequestImproveFormatting,
  onRevert,
  isEditing,
  isSaving,
  isDirty,
  onEnterEdit,
  onSave,
  onCancel,
  canEdit,
}: FormatterMenuProps) {
  const [open, setOpen] = React.useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  React.useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  // Edit-mode bar: Save / Cancel replace the format dropdown.
  if (isEditing) {
    return (
      <div ref={ref} className="flex items-center gap-1.5" data-testid="formatter-edit-bar">
        <button
          type="button"
          onClick={onSave}
          disabled={!isDirty || isSaving}
          className={cn(
            'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors border shadow-sm',
            'bg-primary text-white border-primary',
            'hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg'
          )}
          title={isDirty ? 'Save changes' : 'No changes to save'}
        >
          {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
          {isSaving ? 'Saving…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSaving}
          className={cn(
            'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors border shadow-sm',
            'bg-surface dark:bg-surface-200 border-surface-200 dark:border-surface-200',
            'text-text-secondary hover:text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg'
          )}
          title="Discard changes"
        >
          <X className="h-3.5 w-3.5" />
          Cancel
        </button>
      </div>
    )
  }

  const label = mode === 'markdown' ? 'Markdown' : 'Plain'
  const Icon = mode === 'markdown' ? FileText : Type

  return (
    <div ref={ref} className="relative flex items-center gap-1.5">
      <button
        type="button"
        onClick={onEnterEdit}
        disabled={!canEdit || isImproving}
        className={cn(
          'inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors border shadow-sm',
          'bg-surface dark:bg-surface-200 border-surface-200 dark:border-surface-200',
          'text-text-secondary hover:text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg'
        )}
        title="Manually edit document text"
      >
        <Pencil className="h-3.5 w-3.5" />
        Edit
      </button>

      <button
        onClick={() => setOpen((o) => !o)}
        disabled={isImproving}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          'flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors border shadow-sm',
          'bg-surface dark:bg-surface-200 border-surface-200 dark:border-surface-200',
          'text-text-secondary hover:text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          open && 'bg-surface-100 dark:bg-surface-100'
        )}
        title="Text format"
      >
        {isImproving
          ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
          : <Icon className="h-3.5 w-3.5" />
        }
        <span>{isImproving ? 'Improving…' : label}</span>
        {isImproved && !isImproving && (
          <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" title="AI-improved" />
        )}
        <ChevronDown className={cn('h-3 w-3 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-[70] bg-surface dark:bg-surface-200 rounded-lg shadow-lg border border-surface-200 dark:border-surface-200 py-1 min-w-[180px]">
          <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
            View as
          </div>

          <button
            onClick={() => { onModeChange('plain'); setOpen(false) }}
            className={cn(
              'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset',
              mode === 'plain'
                ? 'text-primary bg-primary-light dark:bg-primary/12'
                : 'text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
            )}
          >
            <Type className="h-3.5 w-3.5 shrink-0" />
            Plain text
            {mode === 'plain' && <span className="ml-auto text-xs text-primary">✓</span>}
          </button>

          <button
            onClick={() => { onModeChange('markdown'); setOpen(false) }}
            className={cn(
              'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset',
              mode === 'markdown'
                ? 'text-primary bg-primary-light dark:bg-primary/12'
                : 'text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
            )}
          >
            <FileText className="h-3.5 w-3.5 shrink-0" />
            Markdown
            {mode === 'markdown' && <span className="ml-auto text-xs text-primary">✓</span>}
          </button>

          <div className="my-1 border-t border-surface-200 dark:border-surface-200" />
          <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
            AI formatting
          </div>

          <button
            onClick={() => { onRequestImproveFormatting(); setOpen(false) }}
            disabled={isImproving}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
          >
            <Sparkles className="h-3.5 w-3.5 text-ai shrink-0" />
            {isImproved ? 'Re-improve formatting' : 'Improve formatting'}
          </button>

          <button
            onClick={() => { onRequestImproveText(); setOpen(false) }}
            disabled={isImproving}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
          >
            <Sparkles className="h-3.5 w-3.5 text-ai shrink-0" />
            {isImproved ? 'Re-improve text' : 'Improve text'}
          </button>

          {isImproved && (
            <button
              onClick={() => { onRevert(); setOpen(false) }}
              disabled={isImproving}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
            >
              <RotateCcw className="h-3.5 w-3.5 text-text-tertiary shrink-0" />
              Revert to original
            </button>
          )}
        </div>
      )}
    </div>
  )
}
