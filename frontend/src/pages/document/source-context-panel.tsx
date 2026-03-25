import { useState } from 'react'

interface SourceContextPanelProps {
  sourcePage?: number | null
  sourceText?: string
}

export function SourceContextPanel({ sourcePage, sourceText }: SourceContextPanelProps) {
  const [expanded, setExpanded] = useState(false)

  const hasPage = sourcePage != null
  const hasText = sourceText && sourceText.length > 0

  if (!hasPage && !hasText) return null

  const truncated = hasText && sourceText!.length > 400
  const displayText = expanded || !truncated ? sourceText : sourceText!.slice(0, 400) + '...'

  return (
    <div className="mt-2 border-t border-gray-200 pt-2 text-xs text-gray-500">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-semibold text-gray-400 uppercase tracking-wide">Source</span>
        {hasPage && (
          <span className="inline-flex items-center rounded bg-gray-100 px-1.5 py-0.5 text-gray-600 font-mono text-[10px]">
            p.&nbsp;{sourcePage}
          </span>
        )}
      </div>
      {hasText && (
        <div>
          <p className="leading-relaxed text-gray-500 italic">{displayText}</p>
          {truncated && (
            <button
              className="mt-0.5 text-primary hover:underline text-[11px]"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded((v) => !v)
              }}
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
