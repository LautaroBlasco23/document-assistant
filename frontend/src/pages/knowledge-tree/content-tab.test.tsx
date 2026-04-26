/**
 * Subject: src/pages/knowledge-tree/content-tab.tsx — ContentTab
 * Scope:   Question generator buttons, generate→poll→display workflow, question deletion, exam launch
 * Out of scope:
 *   - KnowledgeExamSession internals      → knowledge-exam-session.test.tsx
 *   - Full LLM generation logic           → backend tests
 * Setup:   useKnowledgeTreeStore and client are mocked; fake timers control polling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { ContentTab } from './content-tab'
import { renderWithProviders } from '@/test/utils'

const mockUseKnowledgeTreeStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/knowledge-tree-store', () => ({
  useKnowledgeTreeStore: mockUseKnowledgeTreeStore,
  docKey: (treeId: string, chapter: number | null) => `${treeId}:${chapter ?? 'main'}`,
  questionKey: (treeId: string, chapter: number) => `${treeId}:${chapter}`,
  questionTaskKey: (treeId: string, chapter: number, type: string) => `${treeId}:${chapter}:${type}`,
}))

const mockGetTaskStatus = vi.hoisted(() => vi.fn())

vi.mock('@/services', () => ({
  client: {
    getTaskStatus: mockGetTaskStatus,
    getModels: vi.fn().mockResolvedValue({
      provider: 'groq',
      current_model: 'llama-3.3-70b-versatile',
      models: [
        { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B', role: 'smart' },
      ],
    }),
  },
}))

function createMockStore(overrides = {}) {
  return {
    trees: [] as any[],
    treesLoading: false,
    treesFetched: true,
    chapters: {} as Record<string, any[]>,
    chaptersLoading: {},
    documents: {},
    documentsLoading: {},
    questionsByType: {} as Record<string, any>,
    questionsLoading: {},
    questionTaskIds: {},
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
    generateQuestions: vi.fn().mockResolvedValue('task-123'),
    fetchQuestions: vi.fn().mockResolvedValue(undefined),
    deleteQuestion: vi.fn().mockResolvedValue(undefined),
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
    <ContentTab
      treeId={props.treeId}
      selectedChapter={props.selectedChapter}
      chapters={props.chapters ?? []}
    />
  )
}

describe('ContentTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // When no chapter is selected, a helpful empty state should guide the user.
  it('prompts to select a chapter when none is selected', () => {
    renderTab({ treeId: 'tree-1', selectedChapter: null, chapters: [{ id: 'ch-1', number: 1, title: 'Intro', tree_id: 'tree-1' }] })

    expect(screen.getByText('Select a chapter')).toBeInTheDocument()
  })

  // When a chapter is selected but has no questions, all four generator buttons should be visible.
  it('renders question generator buttons for each type', () => {
    renderTab({
      treeId: 'tree-1',
      selectedChapter: 1,
      chapters: [{ id: 'ch-1', number: 1, title: 'Intro', tree_id: 'tree-1' }],
    })

    // Each section renders a plain "Generate" button — the type is shown in the section title
    const generateBtns = screen.getAllByRole('button', { name: 'Generate' })
    expect(generateBtns).toHaveLength(4)

    expect(screen.getByText('True / False')).toBeInTheDocument()
    expect(screen.getByText('Multiple Choice')).toBeInTheDocument()
    expect(screen.getByText('Matching')).toBeInTheDocument()
    expect(screen.getByText('Checkbox (Select All That Apply)')).toBeInTheDocument()
  })

  // Clicking Generate should call generateQuestions then poll until complete and invoke fetchQuestions.
  it('handles generate → poll → display workflow', async () => {
    const generateQuestions = vi.fn().mockResolvedValue('task-123')
    const fetchQuestions = vi.fn().mockResolvedValue(undefined)

    mockGetTaskStatus.mockResolvedValue({ status: 'completed', progress_pct: 100, progress: 'Done' })

    const { user } = renderTab(
      { treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Intro', tree_id: 'tree-1' }] },
      { generateQuestions, fetchQuestions }
    )

    const [firstGenerateBtn] = screen.getAllByRole('button', { name: 'Generate' })
    await user.click(firstGenerateBtn)

    await waitFor(() => {
      expect(generateQuestions).toHaveBeenCalledWith('tree-1', 1, 'true_false', null)
    })

    await vi.advanceTimersByTimeAsync(2000)

    await waitFor(() => {
      expect(fetchQuestions).toHaveBeenCalledWith('tree-1', 1)
    })
  })

  // Existing questions should have a delete button that invokes the store.
  it('deletes a question when trash icon is clicked', async () => {
    const deleteQuestion = vi.fn().mockResolvedValue(undefined)

    const { user } = renderTab(
      { treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Intro', tree_id: 'tree-1' }] },
      {
        questionsByType: {
          'tree-1:1': {
            true_false: [{ type: 'true-false', id: 'q1', statement: 'Sky is blue', answer: true }],
          },
        },
        deleteQuestion,
      }
    )

    // Wait for the effect that sets status='done' to fire and show questions
    const deleteBtn = await screen.findByLabelText('Delete question')
    await user.click(deleteBtn)

    await waitFor(() => {
      expect(deleteQuestion).toHaveBeenCalledWith('tree-1', 1, 'q1')
    })
  })

  // With at least one question generated, the Start Exam button should appear.
  it('launches exam session when Start Exam is clicked', async () => {
    const { user } = renderTab(
      { treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Intro', tree_id: 'tree-1' }] },
      {
        questionsByType: {
          'tree-1:1': {
            true_false: [{ type: 'true-false', id: 'q1', statement: 'Sky is blue', answer: true }],
          },
        },
      }
    )

    const startBtn = await screen.findByRole('button', { name: /start exam/i })
    await user.click(startBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /end exam/i })).toBeInTheDocument()
    })
  })
})
