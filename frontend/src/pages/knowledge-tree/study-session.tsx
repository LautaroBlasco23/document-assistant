import * as React from 'react'
import { X, BookOpen } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'
import { shuffleArray, QuestionCard } from './question-cards'
import type { ExamQuestion } from '../../types/knowledge-tree'

interface StudySessionProps {
  questions: ExamQuestion[]
  onFinish: () => void
  onSave?: (results: { total_cards: number; question_ids: string[] }) => void
}

export function StudySession({ questions, onFinish, onSave }: StudySessionProps) {
  const [shuffledQuestions] = React.useState(() => shuffleArray(questions))
  const [currentIndex, setCurrentIndex] = React.useState(0)
  const [answeredSet, setAnsweredSet] = React.useState<Set<number>>(new Set())

  const total = shuffledQuestions.length
  const progressValue = total > 0 ? (currentIndex / total) * 100 : 0
  const answered = answeredSet.has(currentIndex)

  const handleAnswer = () => {
    setAnsweredSet((prev) => new Set(prev).add(currentIndex))
  }

  const handleNext = () => {
    const nextIndex = currentIndex + 1
    if (nextIndex >= total) {
      const studiedIds = shuffledQuestions.map((q) => q.id)
      onSave?.({ total_cards: total, question_ids: studiedIds })
      onFinish()
    } else {
      setCurrentIndex(nextIndex)
    }
  }

  if (total === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <BookOpen className="h-10 w-10 text-gray-200" />
        <p className="text-sm font-medium text-gray-500">No cards to study</p>
      </div>
    )
  }

  const currentQuestion = shuffledQuestions[currentIndex]
  if (!currentQuestion) return null

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <Progress value={progressValue} />
          <p className="text-xs text-text-tertiary mt-1">
            {currentIndex + 1} / {total}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onFinish} className="shrink-0">
          <X className="h-4 w-4 mr-1" /> End Study
        </Button>
      </div>

      {/* Question card */}
      <QuestionCard
        key={currentIndex}
        question={currentQuestion}
        onAnswer={handleAnswer}
        answered={answered}
        showCorrectAnswer
      />

      {/* Next button */}
      {answered && (
        <div className="flex justify-center pt-2">
          <Button variant="primary" size="sm" onClick={handleNext}>
            {currentIndex === total - 1 ? 'Finish' : 'Next'}
          </Button>
        </div>
      )}
    </div>
  )
}
