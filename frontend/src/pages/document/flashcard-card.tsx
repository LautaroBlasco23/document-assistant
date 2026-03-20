import { useState } from 'react'
import type { FlashcardOut } from '../../types/api'

interface FlashcardCardProps {
  card: FlashcardOut
}

export function FlashcardCard({ card }: FlashcardCardProps) {
  const [flipped, setFlipped] = useState(false)

  return (
    <div
      style={{ perspective: '1000px' }}
      className="cursor-pointer h-40"
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
          <p className="text-sm text-gray-800 font-medium leading-snug line-clamp-4">
            {card.question}
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
            {card.answer}
          </p>
        </div>
      </div>
    </div>
  )
}
