/**
 * Subject: src/pages/knowledge-tree/knowledge-exam-session.tsx — KnowledgeExamSession
 * Scope:   Question rendering by type, answer selection, feedback, results screen, I don't know
 * Out of scope:
 *   - Question generation               → content-tab.test.tsx
 *   - Store interactions                → this component is pure props
 * Setup:   None — component receives questions and onFinish callback directly.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { KnowledgeExamSession } from './knowledge-exam-session'
import { renderWithProviders } from '@/test/utils'
import type { ExamQuestion } from '../../types/knowledge-tree'

const mockOnFinish = vi.fn()

describe('KnowledgeExamSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Prevent shuffleArray from reordering questions so tests are deterministic.
    // With Math.random() = 0.9999, Fisher-Yates always picks j === i → no swap.
    vi.spyOn(Math, 'random').mockReturnValue(0.9999)
  })

  // Shuffling means the order may change, but all questions should be present.
  it('renders questions from the provided array', () => {
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: '1', statement: 'The sky is blue', answer: true },
      { type: 'multiple-choice', id: '2', question: 'What is 2+2?', choices: ['3', '4', '5'], correctIndex: 1 },
    ]
    renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    expect(screen.getByText(/true or false/i)).toBeInTheDocument()
    expect(screen.getByText('The sky is blue')).toBeInTheDocument()
  })

  // True/False cards should present the statement and two options.
  it('renders True/False question card and shows feedback on answer', async () => {
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: '1', statement: 'Water boils at 100C', answer: true, explanation: 'At sea level' },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    await user.click(screen.getByRole('button', { name: 'True' }))

    await waitFor(() => {
      expect(screen.getByText('Correct!')).toBeInTheDocument()
    })
    expect(screen.getByText('At sea level')).toBeInTheDocument()
  })

  // Multiple choice should show all options and mark the correct one after answering.
  it('renders Multiple Choice question card and shows feedback', async () => {
    const questions: ExamQuestion[] = [
      { type: 'multiple-choice', id: '2', question: 'Capital of France?', choices: ['London', 'Paris', 'Berlin'], correctIndex: 1 },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    // Button accessible name is "B.Paris" (no space — JSX strips whitespace between span and text node)
    await user.click(screen.getByRole('button', { name: 'B. Paris' }))

    await waitFor(() => {
      expect(screen.getByText('Correct!')).toBeInTheDocument()
    })
  })

  // Matching questions use dropdowns; selecting all correctly should yield a pass.
  it('renders Matching question card and allows submitting matches', async () => {
    const questions: ExamQuestion[] = [
      {
        type: 'matching',
        id: '3',
        prompt: 'Match terms',
        pairs: [
          { term: 'HTTP', definition: 'Protocol' },
          { term: 'HTML', definition: 'Markup' },
        ],
      },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    const selects = screen.getAllByRole('combobox')
    expect(selects).toHaveLength(2)

    // Select correct definitions (indices 0 and 1 in order)
    await user.selectOptions(selects[0], '0')
    await user.selectOptions(selects[1], '1')

    await user.click(screen.getByRole('button', { name: /check matches/i }))

    await waitFor(() => {
      expect(screen.getByText(/2 of 2 pairs matched correctly/i)).toBeInTheDocument()
    })
  })

  // Checkbox questions allow multiple selections; only exact matches count as correct.
  it('renders Checkbox question card and shows feedback', async () => {
    const questions: ExamQuestion[] = [
      {
        type: 'checkbox',
        id: '4',
        question: 'Which are fruits?',
        choices: ['Apple', 'Carrot', 'Banana'],
        correctIndices: [0, 2],
      },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    await user.click(screen.getByText('Apple'))
    await user.click(screen.getByText('Banana'))
    await user.click(screen.getByRole('button', { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByText('Correct!')).toBeInTheDocument()
    })
  })

  // Flashcards display front text and require a flip before self-assessment.
  it('renders Flashcard question card and allows self-assessment', async () => {
    const questions: ExamQuestion[] = [
      { type: 'flashcard', id: '5', front: 'What is React?', back: 'A UI library' },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    expect(screen.getByText('What is React?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /click to reveal answer/i }))

    await waitFor(() => {
      expect(screen.getByText('A UI library')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /got it/i }))
  })

  // The "I don't know" option should count as incorrect and show the correct answer.
  it('handles I don\'t know option as incorrect', async () => {
    const questions: ExamQuestion[] = [
      { type: 'multiple-choice', id: '2', question: 'Capital of France?', choices: ['London', 'Paris', 'Berlin'], correctIndex: 1 },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    await user.click(screen.getByRole('button', { name: /i don't know/i }))

    await waitFor(() => {
      expect(screen.getByText('Incorrect')).toBeInTheDocument()
    })
  })

  // After the last question the results screen should display the score percentage.
  it('shows results screen with score percentage and missed questions', async () => {
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: '1', statement: 'Sky is blue', answer: true },
      { type: 'true-false', id: '2', statement: 'Grass is red', answer: false },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    // Answer first correctly
    await user.click(screen.getByRole('button', { name: 'True' }))
    await user.click(screen.getByRole('button', { name: /next question/i }))

    // Answer second incorrectly
    await user.click(screen.getByRole('button', { name: 'True' }))
    await user.click(screen.getByRole('button', { name: /see results/i }))

    await waitFor(() => {
      expect(screen.getByText('50%')).toBeInTheDocument()
    })
    expect(screen.getByText('1 / 2 correct')).toBeInTheDocument()
    expect(screen.getByText('Grass is red')).toBeInTheDocument()
  })

  // A perfect score should show the passed variant without a missed-questions list.
  it('shows passed state when all answers are correct', async () => {
    const questions: ExamQuestion[] = [
      { type: 'true-false', id: '1', statement: 'Sky is blue', answer: true },
    ]
    const { user } = renderWithProviders(<KnowledgeExamSession questions={questions} onFinish={mockOnFinish} />)

    await user.click(screen.getByRole('button', { name: 'True' }))
    await user.click(screen.getByRole('button', { name: /see results/i }))

    await waitFor(() => {
      expect(screen.getByText('Exam Passed!')).toBeInTheDocument()
    })
    expect(screen.queryByText(/missed questions/i)).not.toBeInTheDocument()
  })
})
