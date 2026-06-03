import * as React from 'react'
import { X, HelpCircle } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'
import { shuffleArray, QuestionCard } from './question-cards'
import type { ExamQuestion } from '../../types/knowledge-tree'

interface KnowledgeExamSessionProps {
  questions: ExamQuestion[]
  onFinish: () => void
  onSave?: (results: {
    score: number
    total_questions: number
    correct_count: number
    question_ids: string[]
    results: Record<string, boolean>
  }) => void
}

interface QuestionResult {
  correct: boolean
  userAnswer: string
  correctAnswer: string
}

// ---------------------------------------------------------------------------
// Results screen
// ---------------------------------------------------------------------------

interface ResultsScreenProps {
  questions: ExamQuestion[]
  results: Record<number, QuestionResult>
  correctCount: number
  total: number
  onFinish: () => void
}

function ResultsScreen({ questions, results, correctCount, total, onFinish }: ResultsScreenProps) {
  const passed = correctCount === total
  const pct = total > 0 ? Math.round((correctCount / total) * 100) : 0

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-text-primary mb-1">
          {passed ? 'Exam Passed!' : 'Exam Complete'}
        </h2>
        <p className="text-text-tertiary text-sm">
          {passed ? 'All questions answered correctly.' : 'Review the missed questions and try again.'}
        </p>
      </div>

      <div className="flex flex-col items-center gap-1">
        <span className="text-5xl font-bold text-text-primary">{pct}%</span>
        <span className="text-sm text-text-tertiary">
          {correctCount} / {total} correct
        </span>
      </div>

      {!passed && (
        <div className="w-full max-w-lg">
          <p className="text-sm font-medium text-text-secondary mb-2">Missed questions:</p>
          <ul className="flex flex-col gap-2">
            {Object.entries(results)
              .filter(([, r]) => !r.correct)
              .map(([idx, r]) => {
                const q = questions[Number(idx)]
                if (!q) return null
                const label =
                  q.type === 'true-false' ? q.statement
                  : q.type === 'flashcard' ? q.front
                  : q.type === 'matching' ? q.prompt
                  : q.question
                return (
                  <li key={idx} className="rounded-lg border border-difficult/30 bg-difficult-bg/50 px-3 py-3 flex gap-2.5">
                    <HelpCircle className="h-4 w-4 shrink-0 mt-0.5 text-difficult" />
                    <div className="flex flex-col gap-1.5 min-w-0">
                      <p className="text-sm text-difficult font-medium leading-snug">{label}</p>
                      <div className="flex flex-col gap-0.5 text-xs">
                        <span className="text-difficult">
                          <span className="font-semibold">Your answer:</span> {r.userAnswer}
                        </span>
                        <span className="text-mastered">
                          <span className="font-semibold">Correct:</span> {r.correctAnswer}
                        </span>
                      </div>
                    </div>
                  </li>
                )
              })}
          </ul>
        </div>
      )}

      <Button variant="primary" onClick={onFinish}>
        Finish
      </Button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main exam session
// ---------------------------------------------------------------------------

export function KnowledgeExamSession({ questions, onFinish, onSave }: KnowledgeExamSessionProps) {
  const [shuffledQuestions] = React.useState(() => shuffleArray(questions))
  const [currentIndex, setCurrentIndex] = React.useState(0)
  const [results, setResults] = React.useState<Record<number, QuestionResult>>({})
  const [isComplete, setIsComplete] = React.useState(false)
  const [hasSaved, setHasSaved] = React.useState(false)

  const total = shuffledQuestions.length
  const progressValue = total > 0 ? (currentIndex / total) * 100 : 0
  const answered = currentIndex in results

  const handleAnswer = (correct: boolean, userAnswer: string, correctAnswer: string) => {
    setResults((prev) => ({ ...prev, [currentIndex]: { correct, userAnswer, correctAnswer } }))
    setTimeout(() => {
      const nextIndex = currentIndex + 1
      if (nextIndex >= total) {
        setIsComplete(true)
      } else {
        setCurrentIndex(nextIndex)
      }
    }, 350)
  }

  // Save session when exam completes
  React.useEffect(() => {
    if (isComplete && !hasSaved && onSave) {
      setHasSaved(true)
      const correctCount = Object.values(results).filter((r) => r.correct).length
      const pct = total > 0 ? Math.round((correctCount / total) * 100) : 0
      const questionResults: Record<string, boolean> = {}
      for (const [idx, r] of Object.entries(results)) {
        const q = shuffledQuestions[Number(idx)]
        if (q) questionResults[q.id] = r.correct
      }
      onSave({
        score: pct,
        total_questions: total,
        correct_count: correctCount,
        question_ids: shuffledQuestions.map((q) => q.id),
        results: questionResults,
      })
    }
  }, [isComplete, hasSaved, onSave, results, shuffledQuestions, total])

  if (isComplete) {
    const correctCount = Object.values(results).filter((r) => r.correct).length
    return (
      <ResultsScreen
        questions={shuffledQuestions}
        results={results}
        correctCount={correctCount}
        total={total}
        onFinish={onFinish}
      />
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
          <X className="h-4 w-4 mr-1" /> End Exam
        </Button>
      </div>

      {/* Question */}
      <QuestionCard
        key={currentIndex}
        question={currentQuestion}
        onAnswer={handleAnswer}
        answered={answered}
      />
    </div>
  )
}
