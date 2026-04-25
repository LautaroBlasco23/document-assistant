/**
 * Subject: src/pages/library/library-page.tsx — LibraryPage
 * Scope:   Tree list rendering, empty state, dialog opening, loading state
 * Out of scope:
 *   - KnowledgeTreeCard internals       → knowledge-tree-card.test.tsx
 *   - Dialog submission logic           → create/import dialog tests
 * Setup:   useKnowledgeTreeStore is mocked.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { LibraryPage } from './library-page'
import { renderWithProviders } from '@/test/utils'

const mockUseKnowledgeTreeStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/knowledge-tree-store', () => ({
  useKnowledgeTreeStore: mockUseKnowledgeTreeStore,
}))

function createMockStore(overrides = {}) {
  return {
    trees: [] as any[],
    treesLoading: false,
    treesFetched: true,
    chapters: {},
    chaptersLoading: {},
    documents: {},
    documentsLoading: {},
    questionsByType: {},
    questionsLoading: {},
    questionTaskIds: {},
    fetchTrees: vi.fn().mockResolvedValue(undefined),
    createTree: vi.fn(),
    updateTree: vi.fn(),
    deleteTree: vi.fn().mockResolvedValue(undefined),
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
    fetchQuestions: vi.fn(),
    deleteQuestion: vi.fn(),
    ...overrides,
  }
}

describe('LibraryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
      const state = createMockStore()
      return selector ? selector(state) : state
    })
  })

  // When the store has trees, each one should be rendered as a card.
  it('renders grid of KnowledgeTreeCard components when trees exist', () => {
    mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
      const state = createMockStore({
        trees: [
          { id: 'tree-1', title: 'React', description: 'UI library', num_chapters: 3 },
          { id: 'tree-2', title: 'Go', description: 'Systems language', num_chapters: 5 },
        ],
      })
      return selector ? selector(state) : state
    })
    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('Go')).toBeInTheDocument()
    expect(screen.getByText('UI library')).toBeInTheDocument()
  })

  // An empty store should trigger the EmptyState so the user knows what to do next.
  it('shows empty state when no trees', () => {
    mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
      const state = createMockStore({ trees: [] })
      return selector ? selector(state) : state
    })
    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('No knowledge trees yet')).toBeInTheDocument()
  })

  // The import button should surface the file-import dialog.
  it('opens import dialog when Import from Document is clicked', async () => {
    const { user } = renderWithProviders(<LibraryPage />)

    await user.click(screen.getByRole('button', { name: /import from document/i }))

    expect(screen.getByRole('heading', { name: /import from document/i })).toBeInTheDocument()
  })

  // The create button should surface the manual tree creation dialog.
  it('opens create tree dialog when New Tree is clicked', async () => {
    const { user } = renderWithProviders(<LibraryPage />)

    await user.click(screen.getByRole('button', { name: /new tree/i }))

    expect(screen.getByRole('heading', { name: /new knowledge tree/i })).toBeInTheDocument()
  })

  // While trees are loading the grid should be replaced by skeleton cards.
  it('renders skeleton cards while loading', () => {
    mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
      const state = createMockStore({ treesLoading: true })
      return selector ? selector(state) : state
    })
    const { container } = renderWithProviders(<LibraryPage />)

    // SkeletonCard renders several animate-skeleton divs
    expect(container.querySelectorAll('.animate-skeleton').length).toBeGreaterThan(0)
  })
})
