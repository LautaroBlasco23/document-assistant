/**
 * Subject: src/pages/knowledge-tree/knowledge-exam-ready.tsx — KnowledgeExamReady
 * Scope:   Empty state (no questions), question type counts table, total question
 *          count, Start Exam button visibility and click handler.
 * Out of scope:
 *   - Exam session lifecycle                    → exam-tab.test.tsx
 *   - Question generation                       → content-tab.test.tsx
 * Setup:   Pure component — receives typeCounts, totalCount, and onStart as props.
 *          No stores or services are mocked.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { KnowledgeExamReady } from '../knowledge-exam-ready'
import { renderWithProviders } from '@/test/utils'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('KnowledgeExamReady', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // When no questions have been generated (totalCount = 0) the component
  // should show a helpful message guiding the user to the Content tab.
  it('renders empty state when there are zero questions', () => {
    renderWithProviders(
      <KnowledgeExamReady
        typeCounts={[
          { label: 'True / False', count: 0 },
          { label: 'Multiple Choice', count: 0 },
        ]}
        totalCount={0}
        onStart={vi.fn()}
      />
    )

    expect(screen.getByText('No questions generated yet')).toBeInTheDocument()
    expect(screen.getByText(/generate at least one question type in the content tab/i)).toBeInTheDocument()

    // Start Exam button should not be rendered when there are no questions
    expect(screen.queryByRole('button', { name: /start exam/i })).not.toBeInTheDocument()
  })

  // When questions exist, the component shows a table with question type
  // labels and their respective counts.
  it('renders question type counts table', () => {
    renderWithProviders(
      <KnowledgeExamReady
        typeCounts={[
          { label: 'True / False', count: 5 },
          { label: 'Multiple Choice', count: 3 },
          { label: 'Matching', count: 2 },
          { label: 'Checkbox', count: 0 },
        ]}
        totalCount={10}
        onStart={vi.fn()}
      />
    )

    // Table headers
    expect(screen.getByText('Question Type')).toBeInTheDocument()
    expect(screen.getByText('Amount')).toBeInTheDocument()

    // Only types with count > 0 should appear
    expect(screen.getByText('True / False')).toBeInTheDocument()
    expect(screen.getByText('Multiple Choice')).toBeInTheDocument()
    expect(screen.getByText('Matching')).toBeInTheDocument()

    // Checkbox with count 0 is filtered out (filter((t) => t.count > 0))
    expect(screen.queryByText('Checkbox')).not.toBeInTheDocument()

    // Count values
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  // The total question count should be displayed in the descriptive text
  // with proper singular/plural form.
  it('shows total question count with correct pluralization', () => {
    // Singular: 1 question — the description paragraph uses singular "question"
    const { unmount } = renderWithProviders(
      <KnowledgeExamReady
        typeCounts={[{ label: 'True / False', count: 1 }]}
        totalCount={1}
        onStart={vi.fn()}
      />
    )
    const descriptionP = screen.getByText(/ready to start with/i)
    expect(descriptionP).toBeInTheDocument()
    expect(descriptionP.textContent).toContain('1 question')
    unmount()

    // Plural: 2 questions — the description uses plural "questions"
    renderWithProviders(
      <KnowledgeExamReady
        typeCounts={[
          { label: 'True / False', count: 1 },
          { label: 'Multiple Choice', count: 1 },
        ]}
        totalCount={2}
        onStart={vi.fn()}
      />
    )
    expect(screen.getByText(/ready to start with/i)).toBeInTheDocument()
    expect(screen.getByText(/questions from the following types/i)).toBeInTheDocument()
  })

  // The Start Exam button should be visible and call the onStart callback
  // when clicked.
  it('calls onStart when Start Exam button is clicked', async () => {
    const onStart = vi.fn()
    const { user } = renderWithProviders(
      <KnowledgeExamReady
        typeCounts={[{ label: 'True / False', count: 3 }]}
        totalCount={3}
        onStart={onStart}
      />
    )

    const startBtn = screen.getByRole('button', { name: /start exam/i })
    expect(startBtn).toBeInTheDocument()

    await user.click(startBtn)

    expect(onStart).toHaveBeenCalledTimes(1)
  })

  // The Start Exam button should be present when at least one question exists.
  // Edge case: exactly one question — the button should still render and be enabled.
  it('shows Start Exam button even with a single question', () => {
    renderWithProviders(
      <KnowledgeExamReady
        typeCounts={[{ label: 'True / False', count: 1 }]}
        totalCount={1}
        onStart={vi.fn()}
      />
    )

    const startBtn = screen.getByRole('button', { name: /start exam/i })
    expect(startBtn).toBeInTheDocument()
    expect(startBtn).not.toBeDisabled()
  })
})
