import * as React from 'react'
import { Trophy, Check, XCircle } from 'lucide-react'
import type { ExamQuestion, ExamSession } from '../../types/knowledge-tree'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExamReviewProps {
  session: ExamSession
  allQuestions: ExamQuestion[]
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function rebuildQuestionOrder(
  allQuestions: ExamQuestion[],
  session: ExamSession,
): ExamQuestion[] {
  const questionMap = new Map<string, ExamQuestion>()
  for (const q of allQuestions) {
    questionMap.set(q.id, q)
  }

  const ordered: ExamQuestion[] = []
  for (const id of session.question_ids) {
    const q = questionMap.get(id)
    if (q) ordered.push(q)
  }
  for (const q of allQuestions) {
    if (!session.question_ids.includes(q.id)) {
      ordered.push(q)
    }
  }
  return ordered
}

function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 50) return 'text-amber-600'
  return 'text-red-600'
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ---------------------------------------------------------------------------
// Question display (read-only review)
// ---------------------------------------------------------------------------

function ReviewQuestionCard({
  question,
  wasCorrect,
}: {
  question: ExamQuestion
  wasCorrect: boolean
}) {
  const icon = wasCorrect ? (
    <Check className="h-4 w-4 text-green-500" />
  ) : (
    <XCircle className="h-4 w-4 text-red-400" />
  )

  const questionLabel = (q: ExamQuestion): string => {
    switch (q.type) {
      case 'true-false':
        return q.statement
      case 'multiple-choice':
        return q.question
      case 'matching':
        return q.prompt
      case 'checkbox':
        return q.question
      case 'flashcard':
        return q.front
    }
  }

  const questionType = (q: ExamQuestion): string => {
    switch (q.type) {
      case 'true-false':
        return 'True / False'
      case 'multiple-choice':
        return 'Multiple Choice'
      case 'matching':
        return 'Matching'
      case 'checkbox':
        return 'Select All'
      case 'flashcard':
        return 'Flashcard'
    }
  }

  const answerInfo = (q: ExamQuestion): string => {
    switch (q.type) {
      case 'true-false': {
        const correctAnswer = q.answer ? 'True' : 'False'
        return `Correct answer: ${correctAnswer}`
      }
      case 'multiple-choice': {
        const letter = String.fromCharCode(65 + q.correctIndex)
        return `Correct answer: ${letter}. ${q.choices[q.correctIndex]}`
      }
      case 'matching': {
        const pairs = q.pairs.map((p) => `${p.term} → ${p.definition}`).join('; ')
        return `Correct matches: ${pairs}`
      }
      case 'checkbox': {
        const correct = q.correctIndices.map((i) => q.choices[i]).join(', ')
        return `Correct selections: ${correct}`
      }
      case 'flashcard':
        return `Answer: ${q.back}`
    }
  }

  return (
    <div
      className={`rounded-lg border px-4 py-3 flex items-start gap-3 text-sm ${
        wasCorrect
          ? 'border-green-200 bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'
          : 'border-red-200 bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300'
      }`}
    >
      <div className="shrink-0 mt-0.5">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] uppercase tracking-wide opacity-60 font-medium">
            {questionType(question)}
          </span>
          <span className={`text-xs font-semibold ${wasCorrect ? 'text-green-600' : 'text-red-600'}`}>
            {wasCorrect ? 'Correct' : 'Missed'}
          </span>
        </div>
        <p className="font-medium">{questionLabel(question)}</p>
        {!wasCorrect && (
          <p className="text-xs mt-1 opacity-70">{answerInfo(question)}</p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main review component
// ---------------------------------------------------------------------------

export function ExamReview({ session, allQuestions }: ExamReviewProps) {
  const orderedQuestions = React.useMemo(
    () => rebuildQuestionOrder(allQuestions, session),
    [allQuestions, session],
  )

  const correctIds = new Set(
    Object.entries(session.results)
      .filter(([, correct]) => correct)
      .map(([id]) => id)
  )

  return (
    <div className="flex flex-col gap-6 py-4">
      {/* Summary header */}
      <div className="text-center">
        <Trophy className="h-8 w-8 text-amber-400 mx-auto mb-2" />
        <h2 className="text-xl font-bold text-gray-800 dark:text-slate-200">
          Exam Review
        </h2>
        <p className="text-sm text-gray-400 mt-0.5">
          {formatDate(session.created_at)}
        </p>
      </div>

      {/* Score */}
      <div className="flex flex-col items-center gap-1">
        <span className={`text-4xl font-bold ${scoreColor(session.score)}`}>
          {Math.round(session.score)}%
        </span>
        <span className="text-sm text-gray-500">
          {session.correct_count} of {session.total_questions} correct
        </span>
      </div>

      {/* All questions review */}
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-gray-600 mb-1">
          All questions ({orderedQuestions.length})
        </p>
        {orderedQuestions.map((q) => {
          const wasCorrect = correctIds.has(q.id)
          return (
            <ReviewQuestionCard
              key={q.id}
              question={q}
              wasCorrect={wasCorrect}
            />
          )
        })}
      </div>
    </div>
  )
}
