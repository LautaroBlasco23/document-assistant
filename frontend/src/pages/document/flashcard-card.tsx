import { useState } from 'react'
import { Check, X } from 'lucide-react'
import type { FlashcardOut } from '../../types/api'
import { SourceContextPanel } from './source-context-panel'

const categoryLabels: Record<string, string> = {
  terminology: 'Terminology',
  key_facts: 'Key Fact',
  concepts: 'Concept',
}

const categoryColors: Record<string, string> = {
  terminology: 'text-blue-500',
  key_facts: 'text-amber-500',
  concepts: 'text-purple-500',
}

interface FlashcardCardProps {
  card: FlashcardOut
  /** When true, show approve/reject controls for review mode */
  reviewMode?: boolean
  selected?: boolean
  onToggleSelect?: (id: string) => void
}

export function FlashcardCard({ card, reviewMode, selected, onToggleSelect }: FlashcardCardProps) {
  const [flipped, setFlipped] = useState(false)
  const category = card.category ?? 'key_facts'
  const hasSource = (card.source_page != null) || (card.source_text && card.source_text.length > 0)

  const handleClick = () => {
    if (reviewMode && card.id && onToggleSelect) {
      onToggleSelect(card.id)
    } else {
      setFlipped((f) => !f)
    }
  }

  return (
    <div
      style={{ perspective: '1000px' }}
      className={`cursor-pointer ${reviewMode ? 'min-h-44' : 'h-44'} ${selected ? 'ring-2 ring-primary ring-offset-1 rounded-lg' : ''}`}
      onClick={handleClick}
      role="button"
      aria-label={reviewMode ? (selected ? 'Deselect card' : 'Select card') : (flipped ? 'Show question' : 'Show answer')}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleClick()
        }
      }}
    >
      {reviewMode ? (
        // Review mode: show both sides stacked, no flip animation
        <div className={`relative rounded-lg border ${selected ? 'border-primary bg-primary/5' : 'border-gray-200 bg-white'} p-4 shadow-sm flex flex-col gap-2`}>
          {/* Selection indicator */}
          <div className="absolute top-2 right-2">
            {selected ? (
              <Check className="h-4 w-4 text-primary" />
            ) : (
              <div className="h-4 w-4 rounded border border-gray-300" />
            )}
          </div>

          <span className={`text-[10px] font-semibold uppercase tracking-wider ${categoryColors[category]}`}>
            {categoryLabels[category] ?? category}
          </span>
          <p className="text-sm text-gray-800 font-medium leading-snug pr-6">{card.front}</p>
          <p className="text-sm text-gray-600 leading-snug border-t border-gray-100 pt-2">{card.back}</p>
          {hasSource && (
            <SourceContextPanel sourcePage={card.source_page} sourceText={card.source_text} />
          )}
        </div>
      ) : (
        // Normal flip-card mode
        <div
          style={{
            transformStyle: 'preserve-3d',
            transition: 'transform 0.5s',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
            position: 'relative',
            width: '100%',
            height: '100%',
          }}
        >
          {/* Front face */}
          <div
            style={{ backfaceVisibility: 'hidden' }}
            className="absolute inset-0 bg-white border border-gray-200 rounded-lg p-4 flex flex-col justify-between shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-semibold uppercase tracking-wider ${categoryColors[category]}`}>
                {categoryLabels[category] ?? category}
              </span>
            </div>
            <p className="text-sm text-gray-800 font-medium leading-snug line-clamp-4">
              {card.front}
            </p>
            <p className="text-xs text-gray-400">Click to reveal</p>
          </div>

          {/* Back face */}
          <div
            style={{
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
            className="absolute inset-0 bg-accent/5 border border-accent/20 rounded-lg p-4 flex flex-col shadow-sm overflow-y-auto"
          >
            <p className="text-sm text-gray-700 leading-snug flex-1">
              {card.back}
            </p>
            {hasSource && (
              <SourceContextPanel sourcePage={card.source_page} sourceText={card.source_text} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Standalone approve/reject button row for use in review toolbar
interface ReviewActionsProps {
  cardId: string
  onApprove: (id: string) => void
  onReject: (id: string) => void
}

export function ReviewCardActions({ cardId, onApprove, onReject }: ReviewActionsProps) {
  return (
    <div className="flex gap-1 mt-1">
      <button
        className="flex-1 flex items-center justify-center gap-1 rounded border border-green-200 bg-green-50 text-green-700 text-xs py-1 hover:bg-green-100 transition-colors"
        onClick={(e) => { e.stopPropagation(); onApprove(cardId) }}
      >
        <Check className="h-3 w-3" /> Approve
      </button>
      <button
        className="flex-1 flex items-center justify-center gap-1 rounded border border-red-200 bg-red-50 text-red-700 text-xs py-1 hover:bg-red-100 transition-colors"
        onClick={(e) => { e.stopPropagation(); onReject(cardId) }}
      >
        <X className="h-3 w-3" /> Reject
      </button>
    </div>
  )
}
