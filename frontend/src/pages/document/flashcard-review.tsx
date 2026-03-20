import { useState } from 'react'
import { X } from 'lucide-react'
import { useFlashcardStore } from '../../stores/flashcard-store'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'

interface FlashcardReviewProps {
  docHash: string
  chapter: number
}

export function FlashcardReview({ docHash, chapter }: FlashcardReviewProps) {
  const decks = useFlashcardStore((state) => state.decks)
  const activeReview = useFlashcardStore((state) => state.activeReview)
  const scoreCard = useFlashcardStore((state) => state.scoreCard)
  const nextCard = useFlashcardStore((state) => state.nextCard)
  const endReview = useFlashcardStore((state) => state.endReview)

  const deckKey = `${docHash}-${chapter}`
  const deck = (decks[deckKey] ?? [])[0]
  const [flipped, setFlipped] = useState(false)

  if (!deck || !activeReview) return null

  const { currentIndex, scores, isComplete } = activeReview
  const totalCards = deck.cards.length
  const progressValue = totalCards > 0 ? (currentIndex / totalCards) * 100 : 0
  const currentCard = deck.cards[currentIndex]

  const handleScore = (score: 'easy' | 'medium' | 'hard') => {
    scoreCard(score)
    setFlipped(false)
    nextCard()
  }

  // Count scores
  const scoreCounts = { easy: 0, medium: 0, hard: 0 }
  for (const s of Object.values(scores)) {
    scoreCounts[s]++
  }

  // Review complete screen
  if (isComplete) {
    return (
      <div className="flex flex-col items-center justify-center gap-6 py-12">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Review Complete!</h2>
          <p className="text-gray-500">You reviewed {totalCards} cards</p>
        </div>
        <div className="flex gap-6">
          <div className="flex flex-col items-center">
            <span className="text-2xl font-bold text-green-600">{scoreCounts.easy}</span>
            <span className="text-sm text-gray-500">Easy</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-2xl font-bold text-amber-500">{scoreCounts.medium}</span>
            <span className="text-sm text-gray-500">Medium</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-2xl font-bold text-red-500">{scoreCounts.hard}</span>
            <span className="text-sm text-gray-500">Hard</span>
          </div>
        </div>
        <Button variant="secondary" onClick={endReview}>
          Return to Browse
        </Button>
      </div>
    )
  }

  if (!currentCard) return null

  return (
    <div className="flex flex-col gap-4">
      {/* Header with progress and end button */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <Progress value={progressValue} />
          <p className="text-xs text-gray-400 mt-1">
            {currentIndex + 1} / {totalCards}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={endReview}
          aria-label="End review"
          className="shrink-0"
        >
          <X className="h-4 w-4" />
          End Review
        </Button>
      </div>

      {/* Large review card */}
      <div
        style={{ perspective: '1000px' }}
        className="cursor-pointer"
        onClick={() => !flipped && setFlipped(true)}
        role="button"
        aria-label={flipped ? 'Card answer shown' : 'Click to reveal answer'}
        tabIndex={0}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !flipped) {
            e.preventDefault()
            setFlipped(true)
          }
        }}
      >
        <div
          style={{
            transformStyle: 'preserve-3d',
            transition: 'transform 0.5s',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
            position: 'relative',
            minHeight: '240px',
          }}
        >
          {/* Front */}
          <div
            style={{ backfaceVisibility: 'hidden' }}
            className="absolute inset-0 bg-white border border-gray-200 rounded-xl p-8 flex flex-col justify-between shadow-sm"
          >
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wide">Question</div>
            <p className="text-lg text-gray-800 font-medium text-center flex-1 flex items-center justify-center py-4">
              {currentCard.question}
            </p>
            <p className="text-sm text-gray-400 text-center">Click to reveal answer</p>
          </div>

          {/* Back */}
          <div
            style={{
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
            className="absolute inset-0 bg-accent/5 border border-accent/20 rounded-xl p-8 flex flex-col justify-between shadow-sm"
          >
            <div className="text-xs font-medium text-accent uppercase tracking-wide">Answer</div>
            <p className="text-base text-gray-700 text-center flex-1 flex items-center justify-center py-4">
              {currentCard.answer}
            </p>
            <div className="flex justify-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); handleScore('hard') }}
                className="border border-red-200 text-red-600 hover:bg-red-50"
              >
                Hard
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); handleScore('medium') }}
                className="border border-amber-200 text-amber-600 hover:bg-amber-50"
              >
                Medium
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); handleScore('easy') }}
                className="border border-green-200 text-green-600 hover:bg-green-50"
              >
                Easy
              </Button>
            </div>
          </div>
        </div>
      </div>

      {flipped && (
        <p className="text-center text-sm text-gray-400">
          Rate how well you knew this card
        </p>
      )}
    </div>
  )
}
