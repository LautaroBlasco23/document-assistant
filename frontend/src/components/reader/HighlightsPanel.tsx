import { Trash2, Highlighter, FileText } from 'lucide-react'
import { useHighlights } from '../../stores/highlights-store'

interface HighlightsPanelProps {
  docId: string
  docTitle: string
}

export function HighlightsPanel({ docId, docTitle }: HighlightsPanelProps) {
  const highlightsMap = useHighlights((s) => s.highlights)
  const hasHighlightDoc = useHighlights((s) => !!s.highlightDocIds[docId])
  const remove = useHighlights((s) => s.remove)
  const clear = useHighlights((s) => s.clear)
  const highlights = highlightsMap[docId] ?? []

  if (highlights.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        <div className="text-center text-xs text-text-tertiary mt-4">
          Select text and choose <strong>Highlight</strong> from the right-click menu
          <br />
          or press <kbd className="px-1 py-0.5 rounded bg-surface-200 dark:bg-surface-200 text-[10px] font-mono">Ctrl+A</kbd> on a selection.
          <br />
          <span className="block mt-2">Highlights are saved as a document in this chapter.</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] uppercase tracking-wide font-semibold text-text-tertiary">
          {highlights.length} highlight{highlights.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={() => clear(docId)}
          className="text-[10px] text-text-tertiary hover:text-error transition-colors"
        >
          Clear all
        </button>
      </div>

      {hasHighlightDoc && (
        <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-surface-100 dark:bg-surface-100 border border-surface-200 dark:border-surface-200 text-[11px] text-text-tertiary">
          <FileText className="h-3 w-3 shrink-0 text-primary" />
          Saved to <em className="not-italic font-medium text-text-secondary">{docTitle} — Highlights</em>
        </div>
      )}

      {highlights.map((h) => (
        <div
          key={h.id}
          className="group relative rounded-lg border border-highlight bg-highlight/30 dark:bg-highlight/20 px-3 py-2 shadow-sm"
        >
          <div className="flex items-start gap-2">
            <Highlighter className="h-3 w-3 mt-0.5 shrink-0 text-text-tertiary" />
            <p className="flex-1 text-sm text-text-primary leading-relaxed break-words whitespace-pre-wrap">
              {h.text}
            </p>
            <button
              onClick={() => remove(docId, h.id)}
              title="Remove from panel"
              className="shrink-0 p-0.5 rounded text-text-tertiary hover:text-error hover:bg-error-light dark:hover:bg-error/12 transition-colors opacity-0 group-hover:opacity-100"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-1 text-[10px] text-text-tertiary pl-5">
            {new Date(h.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      ))}
    </div>
  )
}
