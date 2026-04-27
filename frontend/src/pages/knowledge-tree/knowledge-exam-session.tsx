import * as React from 'react'
import { X, Check, XCircle, HelpCircle } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'
import type {
  ExamQuestion,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
  FlashcardQuestion,
} from '../../types/knowledge-tree'

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

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

// ---------------------------------------------------------------------------
// True / False card
// ---------------------------------------------------------------------------

interface TrueFalseCardProps {
  question: TrueFalseQuestion
  onAnswer: (correct: boolean) => void
  answered: boolean
  wasCorrect: boolean | undefined
}

function TrueFalseCard({ question, onAnswer, answered, wasCorrect }: TrueFalseCardProps) {
  const [selected, setSelected] = React.useState<boolean | null>(null)

  const handleSelect = (value: boolean) => {
    if (answered) return
    setSelected(value)
    onAnswer(value === question.answer)
  }

  const optionClass = (value: boolean) => {
    const base =
      'flex-1 rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors '
    if (!answered) {
      return (
        base +
        (selected === value
          ? 'border-primary bg-primary/10 text-primary'
          : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-700 dark:text-slate-300 hover:border-gray-300 dark:hover:border-slate-500 hover:bg-surface-100 dark:hover:bg-surface-100 cursor-pointer')
      )
    }
    if (value === question.answer) {
      return base + 'border-green-400 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
    }
    if (selected === value && value !== question.answer) {
      return base + 'border-red-300 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
    }
    return base + 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-400 dark:text-slate-500'
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-indigo-500 uppercase tracking-wide mb-3">
          True or False
        </div>
        <p className="text-base text-gray-800 dark:text-slate-200 font-medium leading-relaxed">
          {question.statement}
        </p>
      </div>

      <div className="px-6 pb-5 flex gap-3">
        <button className={optionClass(true)} onClick={() => handleSelect(true)} disabled={answered}>
          True
        </button>
        <button className={optionClass(false)} onClick={() => handleSelect(false)} disabled={answered}>
          False
        </button>
      </div>

      {answered && (
        <FeedbackBanner correct={wasCorrect ?? false} explanation={question.explanation} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Multiple Choice card
// ---------------------------------------------------------------------------

interface MultipleChoiceCardProps {
  question: MultipleChoiceQuestion
  onAnswer: (correct: boolean) => void
  answered: boolean
  wasCorrect: boolean | undefined
}

function MultipleChoiceCard({ question, onAnswer, answered, wasCorrect }: MultipleChoiceCardProps) {
  const [selected, setSelected] = React.useState<number | 'unknown' | null>(null)

  const handleSelect = (index: number) => {
    if (answered) return
    setSelected(index)
    onAnswer(index === question.correctIndex)
  }

  const handleUnknown = () => {
    if (answered) return
    setSelected('unknown')
    onAnswer(false)
  }

  const optionClass = (index: number) => {
    const base =
      'w-full text-left rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors '
    if (!answered) {
      return (
        base +
        (selected === index
          ? 'border-primary bg-primary/10 text-primary'
          : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-700 dark:text-slate-300 hover:border-gray-300 dark:hover:border-slate-500 hover:bg-surface-100 dark:hover:bg-surface-100 cursor-pointer')
      )
    }
    if (index === question.correctIndex) {
      return base + 'border-green-400 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
    }
    if (selected === index && index !== question.correctIndex) {
      return base + 'border-red-300 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
    }
    return base + 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-400 dark:text-slate-500'
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-violet-500 uppercase tracking-wide mb-3">
          Multiple Choice
        </div>
        <p className="text-base text-gray-800 dark:text-slate-200 font-medium leading-relaxed">
          {question.question}
        </p>
      </div>

      <div className="px-6 pb-4 flex flex-col gap-2">
        {question.choices.map((choice, i) => (
          <button key={i} className={optionClass(i)} onClick={() => handleSelect(i)} disabled={answered}>
            <span className="text-gray-400 dark:text-slate-500 mr-2">{String.fromCharCode(65 + i)}.</span>
            {choice}
          </button>
        ))}
      </div>

      {!answered && (
        <div className="px-6 pb-5">
          <button
            onClick={handleUnknown}
            className="text-xs text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 underline underline-offset-2 transition-colors"
          >
            I don&apos;t know
          </button>
        </div>
      )}

      {answered && (
        <FeedbackBanner
          correct={wasCorrect ?? false}
          explanation={
            selected === 'unknown'
              ? `Correct answer: ${String.fromCharCode(65 + question.correctIndex)}. ${question.choices[question.correctIndex]}${question.explanation ? ` — ${question.explanation}` : ''}`
              : question.explanation
          }
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Matching card
// ---------------------------------------------------------------------------

interface MatchingCardProps {
  question: MatchingQuestion
  onAnswer: (correct: boolean) => void
  answered: boolean
  wasCorrect: boolean | undefined
}

function MatchingCard({ question, onAnswer, answered, wasCorrect }: MatchingCardProps) {
  // Shuffled definitions (indices refer to original pairs array)
  const [shuffledIndices] = React.useState(() =>
    shuffleArray(question.pairs.map((_, i) => i))
  )
  // selections[termIndex] = pairIndex of chosen definition, or null
  const [selections, setSelections] = React.useState<(number | null)[]>(
    () => question.pairs.map(() => null)
  )
  const [submitted, setSubmitted] = React.useState(false)

  const handleSelect = (termIndex: number, pairIndex: number) => {
    if (answered || submitted) return
    setSelections((prev) => {
      const next = [...prev]
      next[termIndex] = pairIndex
      return next
    })
  }

  const allSelected = selections.every((s) => s !== null)

  const handleSubmit = () => {
    if (!allSelected) return
    setSubmitted(true)
    const correct = selections.every((pairIndex, termIndex) => pairIndex === termIndex)
    onAnswer(correct)
  }

  const correctCount = submitted
    ? selections.filter((pairIndex, termIndex) => pairIndex === termIndex).length
    : 0

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-amber-500 uppercase tracking-wide mb-3">
          Matching
        </div>
        <p className="text-base text-gray-800 dark:text-slate-200 font-medium leading-relaxed mb-1">
          {question.prompt}
        </p>
        <p className="text-xs text-gray-400 dark:text-slate-500">Match each term to its correct definition.</p>
      </div>

      <div className="px-6 pb-5 flex flex-col gap-3">
        {question.pairs.map((pair, termIndex) => {
          const selected = selections[termIndex]
          const isCorrect = submitted && selected === termIndex
          const isWrong = submitted && selected !== null && selected !== termIndex

          return (
            <div key={termIndex} className="flex gap-3 items-start">
              {/* Term */}
              <div className="w-40 shrink-0 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface-200 px-3 py-2 text-sm font-medium text-gray-700 dark:text-slate-300">
                {pair.term}
              </div>

              {/* Definition select */}
              <div className="flex-1">
                <select
                  value={selected ?? ''}
                  disabled={answered || submitted}
                  onChange={(e) => handleSelect(termIndex, Number(e.target.value))}
                  className={[
                    'w-full rounded-lg border-2 px-3 py-2 text-sm bg-surface dark:bg-surface-200 focus:outline-none',
                    !submitted
                      ? 'border-surface-200 dark:border-surface-200 text-gray-700 dark:text-slate-300 focus:border-primary'
                      : isCorrect
                        ? 'border-green-400 text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/30'
                        : isWrong
                          ? 'border-red-300 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
                          : 'border-surface-200 dark:border-surface-200 text-gray-400 dark:text-slate-500',
                  ].join(' ')}
                >
                  <option value="" disabled>
                    — Select definition —
                  </option>
                  {shuffledIndices.map((pairIndex) => (
                    <option key={pairIndex} value={pairIndex}>
                      {question.pairs[pairIndex].definition}
                    </option>
                  ))}
                </select>
                {submitted && isWrong && selected !== null && (
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                    Correct: {question.pairs[termIndex].definition}
                  </p>
                )}
              </div>
            </div>
          )
        })}

        {!submitted && (
          <Button
            variant="secondary"
            size="sm"
            disabled={!allSelected}
            onClick={handleSubmit}
            className="self-start mt-1"
          >
            Check Matches
          </Button>
        )}

        {submitted && (
          <FeedbackBanner
            correct={wasCorrect ?? false}
            explanation={`${correctCount} of ${question.pairs.length} pairs matched correctly.`}
          />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Checkbox card
// ---------------------------------------------------------------------------

interface CheckboxCardProps {
  question: CheckboxQuestion
  onAnswer: (correct: boolean) => void
  answered: boolean
  wasCorrect: boolean | undefined
}

function CheckboxCard({ question, onAnswer, answered, wasCorrect }: CheckboxCardProps) {
  const [checked, setChecked] = React.useState<Set<number>>(new Set())
  const [submitted, setSubmitted] = React.useState(false)

  const toggle = (index: number) => {
    if (answered || submitted) return
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const handleSubmit = () => {
    if (checked.size === 0) return
    setSubmitted(true)
    const correctSet = new Set(question.correctIndices)
    const correct =
      checked.size === correctSet.size &&
      [...checked].every((i) => correctSet.has(i))
    onAnswer(correct)
  }

  const choiceClass = (index: number) => {
    const base = 'flex items-start gap-3 rounded-lg border-2 px-4 py-3 text-sm transition-colors '
    if (!submitted) {
      return (
        base +
        (checked.has(index)
          ? 'border-primary bg-primary/10 text-primary cursor-pointer'
          : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-700 dark:text-slate-300 hover:border-gray-300 dark:hover:border-slate-500 hover:bg-surface-100 dark:hover:bg-surface-100 cursor-pointer')
      )
    }
    const isCorrect = question.correctIndices.includes(index)
    const wasChecked = checked.has(index)
    if (isCorrect && wasChecked) return base + 'border-green-400 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
    if (isCorrect && !wasChecked) return base + 'border-green-300 bg-green-50/50 dark:bg-green-900/20 text-green-600 dark:text-green-400'
    if (!isCorrect && wasChecked) return base + 'border-red-300 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
    return base + 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-400 dark:text-slate-500'
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-teal-500 uppercase tracking-wide mb-3">
          Select All That Apply
        </div>
        <p className="text-base text-gray-800 dark:text-slate-200 font-medium leading-relaxed">
          {question.question}
        </p>
      </div>

      <div className="px-6 pb-5 flex flex-col gap-2">
        {question.choices.map((choice, i) => {
          const isCorrect = question.correctIndices.includes(i)
          const wasChecked = checked.has(i)

          return (
            <button
              key={i}
              className={choiceClass(i)}
              onClick={() => toggle(i)}
              disabled={answered || submitted}
            >
              {/* Checkbox indicator */}
              <span
                className={[
                  'mt-0.5 h-4 w-4 shrink-0 rounded border-2 flex items-center justify-center',
                  !submitted
                    ? checked.has(i)
                      ? 'border-primary bg-primary'
                      : 'border-gray-300 dark:border-surface-200 bg-surface dark:bg-surface-200'
                    : isCorrect
                      ? 'border-green-500 bg-green-500'
                      : wasChecked
                        ? 'border-red-400 bg-red-400'
                        : 'border-gray-300 dark:border-surface-200 bg-surface dark:bg-surface-200',
                ].join(' ')}
              >
                {(checked.has(i) || (submitted && isCorrect)) && (
                  <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
                )}
              </span>
              <span>{choice}</span>
              {submitted && isCorrect && !wasChecked && (
                <span className="ml-auto text-xs text-green-600 dark:text-green-400 shrink-0">(missed)</span>
              )}
            </button>
          )
        })}

        {!submitted && (
          <Button
            variant="secondary"
            size="sm"
            disabled={checked.size === 0}
            onClick={handleSubmit}
            className="self-start mt-1"
          >
            Submit
          </Button>
        )}

        {submitted && (
          <FeedbackBanner correct={wasCorrect ?? false} explanation={question.explanation} />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Flashcard
// ---------------------------------------------------------------------------

interface FlashcardCardProps {
  question: FlashcardQuestion
  onAnswer: (correct: boolean) => void
  answered: boolean
}

function FlashcardCard({ question, onAnswer, answered }: FlashcardCardProps) {
  const [flipped, setFlipped] = React.useState(false)

  return (
    <div className="flex flex-col gap-3">
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
            transition: 'transform 0.45s',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
            position: 'relative',
            minHeight: '200px',
          }}
        >
          {/* Front */}
          <div
            style={{ backfaceVisibility: 'hidden' }}
            className="absolute inset-0 bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-xl p-8 flex flex-col justify-between shadow-sm"
          >
            <div className="text-xs font-medium text-primary uppercase tracking-wide">Flashcard</div>
            <p className="text-lg text-gray-800 dark:text-slate-200 font-medium text-center flex-1 flex items-center justify-center py-4">
              {question.front}
            </p>
            <p className="text-sm text-gray-400 dark:text-slate-500 text-center">Click to reveal answer</p>
          </div>

          {/* Back */}
          <div
            style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
            className="absolute inset-0 bg-primary-light dark:bg-primary/12 border border-primary/20 dark:border-primary/30 rounded-xl p-8 flex flex-col justify-between shadow-sm"
          >
            <div className="text-xs font-medium text-primary uppercase tracking-wide">Answer</div>
            <p className="text-base text-gray-700 dark:text-slate-300 text-center flex-1 flex items-center justify-center py-4">
              {question.back}
            </p>
            {flipped && !answered && (
              <div className="flex justify-center gap-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); onAnswer(false) }}
                  className="border border-red-200 text-red-600 hover:bg-red-50 gap-1"
                >
                  <XCircle className="h-4 w-4" /> Didn't know
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); onAnswer(true) }}
                  className="border border-green-200 text-green-600 hover:bg-green-50 gap-1"
                >
                  <Check className="h-4 w-4" /> Got it
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {!flipped && (
        <p className="text-center text-sm text-gray-400 dark:text-slate-500">
          Click the card to reveal the answer
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared feedback banner
// ---------------------------------------------------------------------------

interface FeedbackBannerProps {
  correct: boolean
  explanation?: string
}

function FeedbackBanner({ correct, explanation }: FeedbackBannerProps) {
  return (
    <div
      className={[
        'px-6 py-3 border-t flex gap-3 items-start text-sm',
        correct ? 'bg-green-50 dark:bg-green-900/30 border-green-100 dark:border-green-800 text-green-700 dark:text-green-400' : 'bg-red-50 dark:bg-red-900/20 border-red-100 dark:border-red-800 text-red-700 dark:text-red-400',
      ].join(' ')}
    >
      {correct ? (
        <Check className="h-4 w-4 shrink-0 mt-0.5 text-green-500" />
      ) : (
        <XCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />
      )}
      <div className="flex flex-col gap-0.5">
        <span className="font-medium">{correct ? 'Correct!' : 'Incorrect'}</span>
        {explanation && <span className="text-xs opacity-80">{explanation}</span>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Question dispatcher
// ---------------------------------------------------------------------------

interface QuestionCardProps {
  question: ExamQuestion
  onAnswer: (correct: boolean) => void
  answered: boolean
  wasCorrect: boolean | undefined
}

function QuestionCard({ question, onAnswer, answered, wasCorrect }: QuestionCardProps) {
  switch (question.type) {
    case 'true-false':
      return <TrueFalseCard question={question} onAnswer={onAnswer} answered={answered} wasCorrect={wasCorrect} />
    case 'multiple-choice':
      return <MultipleChoiceCard question={question} onAnswer={onAnswer} answered={answered} wasCorrect={wasCorrect} />
    case 'matching':
      return <MatchingCard question={question} onAnswer={onAnswer} answered={answered} wasCorrect={wasCorrect} />
    case 'checkbox':
      return <CheckboxCard question={question} onAnswer={onAnswer} answered={answered} wasCorrect={wasCorrect} />
    case 'flashcard':
      return <FlashcardCard question={question} onAnswer={onAnswer} answered={answered} />
  }
}

// ---------------------------------------------------------------------------
// Results screen
// ---------------------------------------------------------------------------

interface ResultsScreenProps {
  questions: ExamQuestion[]
  results: Record<number, boolean>
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
        <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-200 mb-1">
          {passed ? 'Exam Passed!' : 'Exam Complete'}
        </h2>
        <p className="text-gray-500 dark:text-slate-400 text-sm">
          {passed
            ? 'All questions answered correctly.'
            : `Review the missed questions and try again.`}
        </p>
      </div>

      <div className="flex flex-col items-center gap-1">
        <span className="text-5xl font-bold text-gray-800 dark:text-slate-200">{pct}%</span>
        <span className="text-sm text-gray-500 dark:text-slate-400">
          {correctCount} / {total} correct
        </span>
      </div>

      {!passed && (
        <div className="w-full max-w-md">
          <p className="text-sm font-medium text-gray-600 dark:text-slate-400 mb-2">Missed questions:</p>
          <ul className="flex flex-col gap-2">
            {Object.entries(results)
              .filter(([, correct]) => !correct)
              .map(([idx]) => {
                const q = questions[Number(idx)]
                if (!q) return null
                const label =
                  q.type === 'true-false'
                    ? q.statement
                    : q.type === 'flashcard'
                      ? q.front
                      : q.type === 'matching'
                        ? q.prompt
                        : q.question
                return (
                  <li key={idx} className="rounded-lg border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-800 dark:text-red-300 flex gap-2">
                    <HelpCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />
                    <span>{label}</span>
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
  const [results, setResults] = React.useState<Record<number, boolean>>({})
  const [isComplete, setIsComplete] = React.useState(false)
  const [hasSaved, setHasSaved] = React.useState(false)

  const total = shuffledQuestions.length
  const progressValue = total > 0 ? (currentIndex / total) * 100 : 0
  const answered = currentIndex in results

  const handleAnswer = (correct: boolean) => {
    setResults((prev) => ({ ...prev, [currentIndex]: correct }))
  }

  const handleNext = () => {
    const nextIndex = currentIndex + 1
    if (nextIndex >= total) {
      setIsComplete(true)
    } else {
      setCurrentIndex(nextIndex)
    }
  }

  // Save session when exam completes
  React.useEffect(() => {
    if (isComplete && !hasSaved && onSave) {
      setHasSaved(true)
      const correctCount = Object.values(results).filter(Boolean).length
      const pct = total > 0 ? Math.round((correctCount / total) * 100) : 0
      const questionResults: Record<string, boolean> = {}
      for (const [idx, correct] of Object.entries(results)) {
        const q = shuffledQuestions[Number(idx)]
        if (q) {
          questionResults[q.id] = correct
        }
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
    const correctCount = Object.values(results).filter(Boolean).length
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

  // Flashcards self-advance once answered; other types need a Next button
  const needsNextButton = answered && currentQuestion.type !== 'flashcard'
  const flashcardAnswered = answered && currentQuestion.type === 'flashcard'

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <Progress value={progressValue} />
          <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
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
        wasCorrect={results[currentIndex]}
      />

      {/* Next button for non-flashcard types */}
      {(needsNextButton || flashcardAnswered) && (
        <div className="flex justify-end">
          <Button variant="primary" size="sm" onClick={handleNext}>
            {currentIndex + 1 >= total ? 'See Results' : 'Next Question →'}
          </Button>
        </div>
      )}
    </div>
  )
}
