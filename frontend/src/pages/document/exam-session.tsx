import { useState } from 'react'
import { X, Check, XCircle } from 'lucide-react'
import { useExamStore } from '../../stores/exam-store'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'

export function ExamSession() {
  const activeExam = useExamStore((state) => state.activeExam)
  const answerCard = useExamStore((state) => state.answerCard)
  const completeExam = useExamStore((state) => state.completeExam)
  const cancelExam = useExamStore((state) => state.cancelExam)

  const [flipped, setFlipped] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (!activeExam) return null

  const { cards, currentIndex, results, isComplete } = activeExam
  const totalCards = cards.length
  const progressValue = totalCards > 0 ? (currentIndex / totalCards) * 100 : 0

  const handleAnswer = (correct: boolean) => {
    answerCard(correct)
    setFlipped(false)
  }

  const handleFinish = async () => {
    setSubmitting(true)
    try {
      await completeExam()
    } finally {
      setSubmitting(false)
    }
  }

  // Completed screen
  if (isComplete) {
    const correctCount = Object.values(results).filter(Boolean).length
    const passed = correctCount === totalCards
    const passMessage = passed
      ? 'All correct! You passed this exam.'
      : `${correctCount} of ${totalCards} correct. Try again after the cooldown.`

    return (
      <div className="flex flex-col items-center justify-center gap-6 py-12">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            {passed ? 'Exam Passed!' : 'Exam Complete'}
          </h2>
          <p className="text-gray-500">{passMessage}</p>
        </div>

        <div className="flex flex-col items-center gap-1">
          <span className="text-4xl font-bold text-gray-800">
            {correctCount} / {totalCards}
          </span>
          <span className="text-sm text-gray-500">correct</span>
        </div>

        {!passed && (
          <div className="w-full max-w-sm">
            <p className="text-sm font-medium text-gray-600 mb-2">Missed cards:</p>
            <ul className="flex flex-col gap-2">
              {Object.entries(results)
                .filter(([, correct]) => !correct)
                .map(([idx]) => {
                  const card = cards[Number(idx)]
                  return card ? (
                    <li key={idx} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                      {card.front}
                    </li>
                  ) : null
                })}
            </ul>
          </div>
        )}

        <Button
          variant="primary"
          onClick={() => void handleFinish()}
          disabled={submitting}
          loading={submitting}
        >
          Finish
        </Button>
      </div>
    )
  }

  const currentCard = cards[currentIndex]
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
          onClick={cancelExam}
          aria-label="End exam"
          className="shrink-0"
        >
          <X className="h-4 w-4" />
          End Exam
        </Button>
      </div>

      {/* Card */}
      <div
        style={{ perspective: '1000px' }}
        className={flipped ? '' : 'cursor-pointer'}
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
              {currentCard.front}
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
              {currentCard.back}
            </p>
            {flipped && (
              <div className="flex justify-center gap-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); handleAnswer(false) }}
                  className="border border-red-200 text-red-600 hover:bg-red-50 gap-1"
                >
                  <XCircle className="h-4 w-4" />
                  Incorrect
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); handleAnswer(true) }}
                  className="border border-green-200 text-green-600 hover:bg-green-50 gap-1"
                >
                  <Check className="h-4 w-4" />
                  Correct
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {!flipped && (
        <p className="text-center text-sm text-gray-400">
          Click the card to reveal the answer, then mark if you knew it
        </p>
      )}
    </div>
  )
}
