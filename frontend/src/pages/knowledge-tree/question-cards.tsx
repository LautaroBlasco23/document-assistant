import * as React from 'react'
import { Check, XCircle } from 'lucide-react'
import { Button } from '../../components/ui/button'
import type {
  ExamQuestion,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
  FlashcardQuestion,
} from '../../types/knowledge-tree'

export function shuffleArray<T>(arr: T[]): T[] {
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
  onAnswer: (correct: boolean, userAnswer: string, correctAnswer: string) => void
  answered: boolean
  showCorrectAnswer?: boolean
}

export function TrueFalseCard({ question, onAnswer, answered, showCorrectAnswer }: TrueFalseCardProps) {
  const [selected, setSelected] = React.useState<boolean | null>(null)

  const handleSelect = (value: boolean) => {
    if (answered) return
    setSelected(value)
    onAnswer(
      value === question.answer,
      value ? 'True' : 'False',
      question.answer ? 'True' : 'False',
    )
  }

  const optionClass = (value: boolean) => {
    const base = 'flex-1 rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors '
    if (showCorrectAnswer && answered && value === question.answer) {
      return base + 'border-success bg-success-light text-success'
    }
    if (selected === value && !(showCorrectAnswer && answered && value !== question.answer)) {
      return base + 'border-primary bg-primary/10 text-primary'
    }
    return (
      base +
      'border-border bg-surface dark:bg-surface-200 text-text-secondary' +
      (!answered ? ' hover:border-border-strong hover:bg-surface-100 dark:hover:bg-surface-100 cursor-pointer' : '')
    )
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-accent uppercase tracking-wide mb-3">
          True or False
        </div>
        <p className="text-base text-text-primary font-medium leading-relaxed">
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

      {answered && selected !== null && !showCorrectAnswer && (
        <div className="px-6 pb-5">
          {selected === question.answer ? (
            <p className="text-sm font-medium text-success">Correct!</p>
          ) : (
            <p className="text-sm font-medium text-danger">Incorrect</p>
          )}
          {question.explanation && (
            <p className="text-xs text-text-tertiary mt-1">{question.explanation}</p>
          )}
        </div>
      )}

      {answered && showCorrectAnswer && selected !== null && question.explanation && (
        <div className="px-6 pb-5">
          <p className="text-xs text-text-tertiary">{question.explanation}</p>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Multiple Choice card
// ---------------------------------------------------------------------------

interface MultipleChoiceCardProps {
  question: MultipleChoiceQuestion
  onAnswer: (correct: boolean, userAnswer: string, correctAnswer: string) => void
  answered: boolean
  showCorrectAnswer?: boolean
}

export function MultipleChoiceCard({ question, onAnswer, answered, showCorrectAnswer }: MultipleChoiceCardProps) {
  const [selected, setSelected] = React.useState<number | 'unknown' | null>(null)

  const correctLabel = `${String.fromCharCode(65 + question.correctIndex)}. ${question.choices[question.correctIndex]}`

  const handleSelect = (index: number) => {
    if (answered) return
    setSelected(index)
    onAnswer(
      index === question.correctIndex,
      `${String.fromCharCode(65 + index)}. ${question.choices[index]}`,
      correctLabel,
    )
  }

  const handleUnknown = () => {
    if (answered) return
    setSelected('unknown')
    onAnswer(false, "I don't know", correctLabel)
  }

  const optionClass = (index: number) => {
    const base = 'w-full text-left rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors '
    if (showCorrectAnswer && answered && index === question.correctIndex) {
      return base + 'border-success bg-success-light text-success'
    }
    if (selected === index && !(showCorrectAnswer && answered)) {
      return base + 'border-primary bg-primary/10 text-primary'
    }
    return (
      base +
      'border-border bg-surface dark:bg-surface-200 text-text-secondary' +
      (!answered ? ' hover:border-border-strong hover:bg-surface-100 dark:hover:bg-surface-100 cursor-pointer' : '')
    )
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-secondary uppercase tracking-wide mb-3">
          Multiple Choice
        </div>
        <p className="text-base text-text-primary font-medium leading-relaxed">
          {question.question}
        </p>
      </div>

      <div className="px-6 pb-4 flex flex-col gap-2">
        {question.choices.map((choice, i) => (
          <button key={i} className={optionClass(i)} onClick={() => handleSelect(i)} disabled={answered}>
            <span className="text-text-tertiary mr-2">{String.fromCharCode(65 + i)}.</span>
            {choice}
          </button>
        ))}
      </div>

      {!answered && (
        <div className="px-6 pb-5">
          <button
            onClick={handleUnknown}
            className="text-xs text-text-tertiary hover:text-text-secondary underline underline-offset-2 transition-colors"
          >
            I don&apos;t know
          </button>
        </div>
      )}

      {answered && !showCorrectAnswer && selected !== null && (
        <div className="px-6 pb-5">
          {selected === question.correctIndex ? (
            <p className="text-sm font-medium text-success">Correct!</p>
          ) : (
            <p className="text-sm font-medium text-danger">Incorrect</p>
          )}
          {question.explanation && (
            <p className="text-xs text-text-tertiary mt-1">{question.explanation}</p>
          )}
        </div>
      )}

      {answered && showCorrectAnswer && selected !== null && question.explanation && (
        <div className="px-6 pb-5">
          <p className="text-xs text-text-tertiary">{question.explanation}</p>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Matching card
// ---------------------------------------------------------------------------

interface MatchingCardProps {
  question: MatchingQuestion
  onAnswer: (correct: boolean, userAnswer: string, correctAnswer: string) => void
  answered: boolean
  showCorrectAnswer?: boolean
}

export function MatchingCard({ question, onAnswer, answered, showCorrectAnswer }: MatchingCardProps) {
  const [shuffledIndices] = React.useState(() =>
    shuffleArray(question.pairs.map((_, i) => i))
  )
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
    const correctCountLocal = selections.filter((pairIndex, termIndex) => pairIndex === termIndex).length
    const correct = correctCountLocal === question.pairs.length
    const userAnswer = `${correctCountLocal} / ${question.pairs.length} pairs matched`
    const correctAnswer = question.pairs.map((p) => `${p.term} → ${p.definition}`).join('; ')
    onAnswer(correct, userAnswer, correctAnswer)
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-amber-500 uppercase tracking-wide mb-3">
          Matching
        </div>
        <p className="text-base text-text-primary font-medium leading-relaxed mb-1">
          {question.prompt}
        </p>
        <p className="text-xs text-text-tertiary">Match each term to its correct definition.</p>
      </div>

      <div className="px-6 pb-5 flex flex-col gap-3">
        {question.pairs.map((pair, termIndex) => {
          const selected = selections[termIndex]
          const isCorrectMatch = submitted && selected === termIndex

          return (
            <div key={termIndex} className="flex gap-3 items-start">
              <div className="w-40 shrink-0 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface-200 px-3 py-2 text-sm font-medium text-text-secondary">
                {pair.term}
              </div>
              <div className="flex-1 flex items-center gap-2">
                {showCorrectAnswer && submitted ? (
                  <div className={`w-full rounded-lg border-2 px-3 py-2 text-sm ${
                    isCorrectMatch
                      ? 'border-success bg-success-light text-success'
                      : 'border-danger/30 bg-danger-light/50 text-danger'
                  }`}>
                    {isCorrectMatch ? pair.definition : `${pair.definition} (correct)`}
                  </div>
                ) : (
                  <select
                    value={selected ?? ''}
                    disabled={answered || submitted}
                    onChange={(e) => handleSelect(termIndex, Number(e.target.value))}
                    className={`w-full rounded-lg border-2 px-3 py-2 text-sm bg-surface dark:bg-surface-200 border-border text-text-secondary focus:outline-none focus:border-primary ${
                      showCorrectAnswer && submitted && !isCorrectMatch ? 'border-danger/30' : ''
                    }`}
                  >
                    <option value="" disabled>— Select definition —</option>
                    {shuffledIndices.map((pairIndex) => (
                      <option key={pairIndex} value={pairIndex}>
                        {question.pairs[pairIndex].definition}
                      </option>
                    ))}
                  </select>
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

        {!showCorrectAnswer && submitted && (
          <div className="mt-2">
            {(() => {
              const correctCountLocal = selections.filter((pairIndex, termIndex) => pairIndex === termIndex).length
              const correct = correctCountLocal === question.pairs.length
              return correct ? (
                <p className="text-sm font-medium text-success">
                  Correct! {correctCountLocal} of {question.pairs.length} pairs matched correctly.
                </p>
              ) : (
                <p className="text-sm font-medium text-danger">
                  Incorrect. {correctCountLocal} of {question.pairs.length} pairs matched correctly.
                </p>
              )
            })()}
          </div>
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
  onAnswer: (correct: boolean, userAnswer: string, correctAnswer: string) => void
  answered: boolean
  showCorrectAnswer?: boolean
}

export function CheckboxCard({ question, onAnswer, answered, showCorrectAnswer }: CheckboxCardProps) {
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
    const correct = checked.size === correctSet.size && [...checked].every((i) => correctSet.has(i))
    const userAnswer = [...checked].map((i) => question.choices[i]).join(', ') || 'None'
    const correctAnswer = question.correctIndices.map((i) => question.choices[i]).join(', ')
    onAnswer(correct, userAnswer, correctAnswer)
  }

  const choiceClass = (index: number) => {
    const base = 'flex items-start gap-3 rounded-lg border-2 px-4 py-3 text-sm transition-colors '
    if (showCorrectAnswer && submitted && question.correctIndices.includes(index)) {
      return base + 'border-success bg-success-light text-success'
    }
    if (checked.has(index) && !(showCorrectAnswer && submitted)) {
      return base + 'border-primary bg-primary/10 text-primary' + (!submitted ? ' cursor-pointer' : '')
    }
    return (
      base +
      'border-border bg-surface dark:bg-surface-200 text-text-secondary' +
      (!submitted ? ' hover:border-border-strong hover:bg-surface-100 dark:hover:bg-surface-100 cursor-pointer' : '')
    )
  }

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-xl bg-surface dark:bg-surface-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4">
        <div className="text-xs font-medium text-accent uppercase tracking-wide mb-3">
          Select All That Apply
        </div>
        <p className="text-base text-text-primary font-medium leading-relaxed">
          {question.question}
        </p>
      </div>

      <div className="px-6 pb-5 flex flex-col gap-2">
        {question.choices.map((choice, i) => (
          <button
            key={i}
            className={choiceClass(i)}
            onClick={() => toggle(i)}
            disabled={answered || submitted}
          >
            <span
              className={[
                'mt-0.5 h-4 w-4 shrink-0 rounded border-2 flex items-center justify-center',
                checked.has(i)
                  ? 'border-primary bg-primary'
                  : 'border-border-subtle bg-surface dark:bg-surface-200',
              ].join(' ')}
            >
              {checked.has(i) && <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
            </span>
            <span>{choice}</span>
          </button>
        ))}

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

        {!showCorrectAnswer && submitted && (
          <div className="mt-2">
            {(() => {
              const correctSet = new Set(question.correctIndices)
              const correct = checked.size === correctSet.size && [...checked].every((i) => correctSet.has(i))
              return correct ? (
                <p className="text-sm font-medium text-success">Correct!</p>
              ) : (
                <p className="text-sm font-medium text-danger">Incorrect</p>
              )
            })()}
            {question.explanation && (
              <p className="text-xs text-text-tertiary mt-1">{question.explanation}</p>
            )}
          </div>
        )}

        {showCorrectAnswer && submitted && question.explanation && (
          <div className="mt-2">
            <p className="text-xs text-text-tertiary">{question.explanation}</p>
          </div>
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
  onAnswer: (correct: boolean, userAnswer: string, correctAnswer: string) => void
  answered: boolean
  showCorrectAnswer?: boolean
}

export function FlashcardCard({ question, onAnswer, answered, showCorrectAnswer }: FlashcardCardProps) {
  const [flipped, setFlipped] = React.useState(false)

  const handleFlip = () => {
    if (flipped || answered) return
    setFlipped(true)
    if (showCorrectAnswer) {
      onAnswer(true, 'Flipped', question.back)
    }
  }

  const handleDidntKnow = (e: React.MouseEvent) => {
    e.stopPropagation()
    onAnswer(false, "Didn't know", question.back)
  }

  const handleGotIt = (e: React.MouseEvent) => {
    e.stopPropagation()
    onAnswer(true, 'Got it', question.back)
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        style={{ perspective: '1000px' }}
        className={!flipped ? 'cursor-pointer' : ''}
        onClick={handleFlip}
        role="button"
        aria-label={flipped ? 'Card answer shown' : 'Click to reveal answer'}
        tabIndex={0}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !flipped && !answered) {
            e.preventDefault()
            handleFlip()
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
            <p className="text-lg text-text-primary font-medium text-center flex-1 flex items-center justify-center py-4">
              {question.front}
            </p>
            <p className="text-sm text-text-tertiary text-center">Click to reveal answer</p>
          </div>

          {/* Back */}
          <div
            style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
            className="absolute inset-0 bg-primary-light dark:bg-primary/12 border border-primary/20 dark:border-primary/30 rounded-xl p-8 flex flex-col justify-between shadow-sm"
          >
            <div className="text-xs font-medium text-primary uppercase tracking-wide">Answer</div>
            <p className="text-base text-text-secondary text-center flex-1 flex items-center justify-center py-4">
              {question.back}
            </p>
            {flipped && !showCorrectAnswer && !answered && (
              <div className="flex justify-center gap-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDidntKnow}
                  className="border border-danger/30 text-danger hover:bg-danger-light gap-1"
                >
                  <XCircle className="h-4 w-4" /> Didn't know
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleGotIt}
                  className="border border-success/30 text-success hover:bg-success-light gap-1"
                >
                  <Check className="h-4 w-4" /> Got it
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {!flipped && (
        <p className="text-center text-sm text-text-tertiary">
          Click the card to reveal the answer
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Question dispatcher
// ---------------------------------------------------------------------------

interface QuestionCardProps {
  question: ExamQuestion
  onAnswer: (correct: boolean, userAnswer: string, correctAnswer: string) => void
  answered: boolean
  showCorrectAnswer?: boolean
}

export function QuestionCard({ question, onAnswer, answered, showCorrectAnswer }: QuestionCardProps) {
  switch (question.type) {
    case 'true-false':
      return <TrueFalseCard question={question} onAnswer={onAnswer} answered={answered} showCorrectAnswer={showCorrectAnswer} />
    case 'multiple-choice':
      return <MultipleChoiceCard question={question} onAnswer={onAnswer} answered={answered} showCorrectAnswer={showCorrectAnswer} />
    case 'matching':
      return <MatchingCard question={question} onAnswer={onAnswer} answered={answered} showCorrectAnswer={showCorrectAnswer} />
    case 'checkbox':
      return <CheckboxCard question={question} onAnswer={onAnswer} answered={answered} showCorrectAnswer={showCorrectAnswer} />
    case 'flashcard':
      return <FlashcardCard question={question} onAnswer={onAnswer} answered={answered} showCorrectAnswer={showCorrectAnswer} />
  }
}
