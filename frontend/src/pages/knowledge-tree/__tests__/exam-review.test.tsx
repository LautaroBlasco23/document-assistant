/**
 * Subject: src/pages/knowledge-tree/exam-review.tsx — ExamReview
 * Scope:   Score header (percentage + correct count), passed/failed coloration,
 *          question review cards with correct/incorrect indicators, empty questions,
 *          and edge cases (0%, 100%).
 * Out of scope:
 *   - KnowledgeExamSession (live exam flow)     → knowledge-exam-session.test.tsx
 *   - ExamTab orchestration                     → exam-tab.test.tsx
 * Setup:   Pure component — receives session + allQuestions as props.
 *          No stores or services are mocked.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { ExamReview } from '../exam-review'
import { renderWithProviders } from '@/test/utils'
import type { ExamQuestion, ExamSession } from '../../../types/knowledge-tree'

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const baseDate = new Date('2025-06-15T14:30:00Z').toISOString()

function makeSession(overrides: Partial<ExamSession> = {}): ExamSession {
  return {
    id: 'session-1',
    tree_id: 'tree-1',
    chapter_id: 'ch-1',
    score: 80,
    total_questions: 5,
    correct_count: 4,
    question_ids: ['q1', 'q2', 'q3', 'q4', 'q5'],
    results: { q1: true, q2: true, q3: true, q4: true, q5: false },
    created_at: baseDate,
    ...overrides,
  }
}

function makeQuestions(): ExamQuestion[] {
  return [
    { type: 'true-false', id: 'q1', statement: 'Water boils at 100C', answer: true },
    { type: 'true-false', id: 'q2', statement: 'The Sun is a planet', answer: false },
    { type: 'multiple-choice', id: 'q3', question: 'Capital of Japan?', choices: ['Seoul', 'Tokyo', 'Beijing'], correctIndex: 1 },
    { type: 'checkbox', id: 'q4', question: 'Select fruits', choices: ['Apple', 'Carrot', 'Banana'], correctIndices: [0, 2] },
    { type: 'matching', id: 'q5', prompt: 'Match terms', pairs: [{ term: 'HTTP', definition: 'Protocol' }] },
  ]
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ExamReview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // The score percentage and correct/total count should be prominently displayed
  // so the user immediately knows how they performed.
  it('renders score percentage and correct count', () => {
    const session = makeSession({ score: 75, correct_count: 3, total_questions: 4 })
    renderWithProviders(<ExamReview session={session} allQuestions={makeQuestions()} />)

    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('3 of 4 correct')).toBeInTheDocument()
  })

  // Every question that was part of the session should appear in the review
  // list with a correct or incorrect indicator.
  it('renders all questions with correct/incorrect indicators', () => {
    const session = makeSession({
      question_ids: ['q1', 'q2', 'q3'],
      results: { q1: true, q2: false, q3: true },
      total_questions: 3,
      correct_count: 2,
    })
    const questions = makeQuestions().slice(0, 3)
    renderWithProviders(<ExamReview session={session} allQuestions={questions} />)

    // Each correct question shows "Correct"
    const correctLabels = screen.getAllByText('Correct')
    expect(correctLabels).toHaveLength(2)

    // The missed question shows "Missed"
    expect(screen.getByText('Missed')).toBeInTheDocument()
  })

  // For missed (incorrect) questions, the correct answer should be displayed
  // so the user can learn from their mistakes.
  it('shows correct answer info for missed questions', () => {
    const session = makeSession({
      question_ids: ['q2'],
      results: { q2: false },
      score: 0,
      total_questions: 1,
      correct_count: 0,
    })
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: 'q2', statement: 'The Sun is a planet', answer: false },
    ]
    renderWithProviders(<ExamReview session={session} allQuestions={questions} />)

    expect(screen.getByText('Missed')).toBeInTheDocument()
    // Correct answer is "False" for this true-false question
    expect(screen.getByText(/correct answer: false/i)).toBeInTheDocument()
  })

  // When the user got nothing right (0%), the score should display as 0%
  // and every question should be marked as missed.
  it('handles 0% score — all questions wrong', () => {
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: 'q1', statement: 'Earth is flat', answer: false },
      { type: 'true-false', id: 'q2', statement: 'Fish can fly', answer: false },
    ]
    const session: ExamSession = {
      id: 'session-zero',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      score: 0,
      total_questions: 2,
      correct_count: 0,
      question_ids: ['q1', 'q2'],
      results: { q1: false, q2: false },
      created_at: baseDate,
    }

    renderWithProviders(<ExamReview session={session} allQuestions={questions} />)

    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('0 of 2 correct')).toBeInTheDocument()

    // All questions should be marked missed — two "Missed" labels
    const missedLabels = screen.getAllByText('Missed')
    expect(missedLabels).toHaveLength(2)

    // No "Correct" labels
    expect(screen.queryByText('Correct')).not.toBeInTheDocument()
  })

  // A perfect score (100%) should display all questions as correct and
  // have a "passed" coloration (green).
  it('handles 100% score — all questions right', () => {
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: 'q1', statement: 'Grass is green', answer: true },
    ]
    const session: ExamSession = {
      id: 'session-perfect',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      score: 100,
      total_questions: 1,
      correct_count: 1,
      question_ids: ['q1'],
      results: { q1: true },
      created_at: baseDate,
    }

    renderWithProviders(<ExamReview session={session} allQuestions={questions} />)

    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText('1 of 1 correct')).toBeInTheDocument()
    expect(screen.getByText('Correct')).toBeInTheDocument()
    expect(screen.queryByText('Missed')).not.toBeInTheDocument()
  })

  // When no questions exist (empty allQuestions array), the component should
  // still render without crashing and show "All questions (0)".
  it('renders empty state when there are no questions', () => {
    const session = makeSession({
      question_ids: [],
      results: {},
      total_questions: 0,
      correct_count: 0,
      score: 0,
    })

    renderWithProviders(<ExamReview session={session} allQuestions={[]} />)

    expect(screen.getByText('Exam Review')).toBeInTheDocument()
    expect(screen.getByText('All questions (0)')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  // An 80+ score should use the green color class; below 50 should use red.
  // Verifies the scoreColor helper renders the right Tailwind class.
  it('applies pass/fail coloration to score text', () => {
    // Passing score (>= 80 appears green via text-green-600)
    const passingSession = makeSession({ score: 85 })
    const { unmount } = renderWithProviders(
      <ExamReview session={passingSession} allQuestions={makeQuestions()} />
    )
    const score85 = screen.getByText('85%')
    expect(score85.className).toContain('text-green-600')
    unmount()

    // Failing score (< 50 appears red via text-red-600)
    const failingSession = makeSession({ score: 30, correct_count: 1, results: { q1: true, q2: false, q3: false, q4: false, q5: false } })
    renderWithProviders(<ExamReview session={failingSession} allQuestions={makeQuestions()} />)
    const score30 = screen.getByText('30%')
    expect(score30.className).toContain('text-red-600')
  })
})
