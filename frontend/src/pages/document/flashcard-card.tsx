import { useState } from 'react'
import type { FlashcardOut } from '../../types/api'

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
}

export function FlashcardCard({ card }: FlashcardCardProps) {
  const [flipped, setFlipped] = useState(false)
  const category = card.category ?? 'key_facts'

  return (
    <div
      style={{ perspective: '1000px' }}
      className="cursor-pointer h-44"
      onClick={() => setFlipped((f) => !f)}
      role="button"
      aria-label={flipped ? 'Show question' : 'Show answer'}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          setFlipped((f) => !f)
        }
      }}
    >
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
          className="absolute inset-0 bg-accent/5 border border-accent/20 rounded-lg p-4 flex flex-col justify-center shadow-sm"
        >
          <p className="text-sm text-gray-700 leading-snug">
            {card.back}
          </p>
        </div>
      </div>
    </div>
  )
}
