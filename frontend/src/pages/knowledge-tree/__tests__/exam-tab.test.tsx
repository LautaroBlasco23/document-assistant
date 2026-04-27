/**
 * Subject: src/pages/knowledge-tree/exam-tab.tsx — ExamTab
 * Scope:   Empty states (no chapters, no chapter selected), exam-ready view, exam session
 *          launch, exam history display, and review mode.
 * Out of scope:
 *   - KnowledgeExamSession question rendering    → knowledge-exam-session.test.tsx
 *   - ExamReview question display                → exam-review.test.tsx
 *   - KnowledgeExamReady count/button rendering  → knowledge-exam-ready.test.tsx
 * Setup:   useKnowledgeTreeStore is mocked via vi.hoisted.
 *          ExamSession and ExamReview components render naturally (they receive props).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { ExamTab } from '../exam-tab'
import { renderWithProviders } from '@/test/utils'

const mockUseKnowledgeTreeStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/knowledge-tree-store', () => ({
  useKnowledgeTreeStore: mockUseKnowledgeTreeStore,
  questionKey: (treeId: string, chapter: number) => `${treeId}:${chapter}`,
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createMockStore(overrides: Record<string, any> = {}) {
  return {
    trees: [] as any[],
    treesLoading: false,
    treesFetched: true,
    chapters: {} as Record<string, any[]>,
    chaptersLoading: {} as Record<string, boolean>,
    documents: {} as Record<string, any[]>,
    documentsLoading: {} as Record<string, boolean>,
    questionsByType: {} as Record<string, any>,
    questionsLoading: {} as Record<string, boolean>,
    questionTaskIds: {} as Record<string, string>,
    examSessionsByChapter: {} as Record<string, any[]>,
    examSessionsLoading: {} as Record<string, boolean>,
    fetchTrees: vi.fn(),
    createTree: vi.fn(),
    updateTree: vi.fn(),
    deleteTree: vi.fn(),
    fetchChapters: vi.fn(),
    createChapter: vi.fn(),
    updateChapter: vi.fn(),
    deleteChapter: vi.fn(),
    fetchDocuments: vi.fn(),
    fetchAllDocuments: vi.fn(),
    createDocument: vi.fn(),
    updateDocument: vi.fn(),
    deleteDocument: vi.fn(),
    ingestFileAsDocument: vi.fn(),
    createTreeFromFile: vi.fn(),
    generateQuestions: vi.fn(),
    fetchQuestions: vi.fn().mockResolvedValue(undefined),
    deleteQuestion: vi.fn(),
    saveExamSession: vi.fn().mockResolvedValue({}),
    fetchExamSessions: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

function renderTab(
  props: { treeId: string; selectedChapter: number | null; chapters?: any[] },
  storeOverrides: Record<string, any> = {}
) {
  mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
    const state = createMockStore(storeOverrides)
    return selector ? selector(state) : state
  })

  return renderWithProviders(
    <ExamTab
      treeId={props.treeId}
      selectedChapter={props.selectedChapter}
      chapters={props.chapters ?? []}
    />
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ExamTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // When no chapters exist in the tree, the user should see a helpful guidance
  // message explaining they need to add chapters first.
  it('renders empty state when chapters list is empty', () => {
    renderTab({ treeId: 'tree-1', selectedChapter: null, chapters: [] })

    expect(screen.getByText('No chapters yet')).toBeInTheDocument()
    expect(screen.getByText(/add chapters in the knowledge documents tab/i)).toBeInTheDocument()
  })

  // When chapters exist but none is selected, guide the user to pick one from
  // the sidebar before they can take an exam.
  it('renders prompt to select a chapter when none is selected', () => {
    renderTab({
      treeId: 'tree-1',
      selectedChapter: null,
      chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }],
    })

    expect(screen.getByText('Select a chapter')).toBeInTheDocument()
    expect(screen.getByText(/choose a chapter from the sidebar/i)).toBeInTheDocument()
  })

  // With a chapter selected and no sessions in history, the ready screen
  // (type counts + start button) should be visible. Covers the default
  // state before any exam has been taken.
  it('renders exam ready screen when chapter is selected and no sessions exist', () => {
    renderTab({
      treeId: 'tree-1',
      selectedChapter: 1,
      chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }],
    })

    // KnowledgeExamReady renders a graduation cap and "No questions generated yet" when total=0
    expect(screen.getByText('No questions generated yet')).toBeInTheDocument()
  })

  // After clicking Start Exam, the component transitions to the active exam
  // session view. This tests the local examActive state toggle.
  it('renders exam session when start button is clicked and questions exist', async () => {
    const { user } = renderTab(
      {
        treeId: 'tree-1',
        selectedChapter: 1,
        chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }],
      },
      {
        questionsByType: {
          'tree-1:1': {
            true_false: [{ type: 'true-false', id: 'q1', statement: 'Sky is blue', answer: true }],
          },
        },
      }
    )

    // KnowledgeExamReady shows Start Exam button when questions exist
    const startBtn = await screen.findByRole('button', { name: /start exam/i })
    await user.click(startBtn)

    // KnowledgeExamSession should be visible — it renders "True or False" heading
    await waitFor(() => {
      expect(screen.getByText(/true or false/i)).toBeInTheDocument()
    })
  })

  // When exam history entries exist, they should show up as clickable items
  // with score percentage, correct count badge, and formatted date.
  it('renders exam history when past sessions exist', () => {
    const mockSession = {
      id: 'session-1',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      score: 85,
      total_questions: 10,
      correct_count: 8,
      question_ids: ['q1', 'q2'],
      results: { q1: true, q2: false },
      created_at: new Date('2025-06-15T14:30:00Z').toISOString(),
    }

    renderTab(
      {
        treeId: 'tree-1',
        selectedChapter: 1,
        chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }],
      },
      {
        examSessionsByChapter: {
          'tree-1:1': [mockSession],
        },
      }
    )

    expect(screen.getByText('Exam History')).toBeInTheDocument()
    expect(screen.getByText('85%')).toBeInTheDocument()
    expect(screen.getByText('8/10 correct')).toBeInTheDocument()
  })

  // Clicking on a past exam session history item should switch to review mode,
  // rendering the ExamReview component with the session data.
  it('renders exam review when a past session is clicked', async () => {
    const mockSession = {
      id: 'session-1',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      score: 100,
      total_questions: 2,
      correct_count: 2,
      question_ids: ['q1'],
      results: { q1: true },
      created_at: new Date('2025-06-15T14:30:00Z').toISOString(),
    }

    const { user } = renderTab(
      {
        treeId: 'tree-1',
        selectedChapter: 1,
        chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }],
      },
      {
        examSessionsByChapter: {
          'tree-1:1': [mockSession],
        },
      }
    )

    // Click on the exam history entry (button containing the score)
    const historyBtn = screen.getByText('100%').closest('button')
    await user.click(historyBtn!)

    // ExamReview should appear, showing "Exam Review" heading
    await waitFor(() => {
      expect(screen.getByText('Exam Review')).toBeInTheDocument()
    })
  })

  // The "back to exams" button in review mode should return to the default
  // (ready) view.
  it('returns to exam list from review mode via back button', async () => {
    const mockSession = {
      id: 'session-1',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      score: 100,
      total_questions: 1,
      correct_count: 1,
      question_ids: ['q1'],
      results: { q1: true },
      created_at: new Date('2025-06-15T14:30:00Z').toISOString(),
    }

    const { user } = renderTab(
      {
        treeId: 'tree-1',
        selectedChapter: 1,
        chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }],
      },
      {
        examSessionsByChapter: {
          'tree-1:1': [mockSession],
        },
      }
    )

    // Enter review mode
    const historyBtn = screen.getByText('100%').closest('button')
    await user.click(historyBtn!)
    await waitFor(() => {
      expect(screen.getByText('Exam Review')).toBeInTheDocument()
    })

    // Click back button
    await user.click(screen.getByText('← Back to exams'))

    await waitFor(() => {
      expect(screen.queryByText('Exam Review')).not.toBeInTheDocument()
      expect(screen.getByText('Exam History')).toBeInTheDocument()
    })
  })
})
