/**
 * Subject: src/pages/knowledge-tree/knowledge-tree-page.tsx — KnowledgeTreePage
 * Scope:   Tree title display, chapter sidebar, tab switching, not-found handling, chapter CRUD
 * Out of scope:
 *   - KnowledgeDocumentsTab internals   → knowledge-documents-tab.test.tsx
 *   - ContentTab internals              → content-tab.test.tsx
 *   - AllDocumentsTab internals         → all-documents-tab.test.tsx
 * Setup:   useKnowledgeTreeStore and useAppStore are mocked; component is rendered inside a Route.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { KnowledgeTreePage } from './knowledge-tree-page'
import { renderWithProviders } from '@/test/utils'

const mockUseKnowledgeTreeStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/knowledge-tree-store', () => ({
  useKnowledgeTreeStore: mockUseKnowledgeTreeStore,
  docKey: (treeId: string, chapter: number | null) => `${treeId}:${chapter ?? 'main'}`,
}))

const mockUseAppStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/app-store', () => ({
  useAppStore: mockUseAppStore,
}))

function createMockTreeStore(overrides = {}) {
  return {
    trees: [] as any[],
    treesLoading: false,
    treesFetched: true,
    chapters: {} as Record<string, any[]>,
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
    fetchChapters: vi.fn().mockResolvedValue(undefined),
    createChapter: vi.fn().mockResolvedValue(undefined),
    updateChapter: vi.fn().mockResolvedValue(undefined),
    deleteChapter: vi.fn().mockResolvedValue(undefined),
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

function createMockAppStore(overrides = {}) {
  return {
    sidebarCollapsed: false,
    toggleSidebar: vi.fn(),
    serviceHealth: null,
    setServiceHealth: vi.fn(),
    errors: [],
    addError: vi.fn(),
    removeError: vi.fn(),
    ...overrides,
  }
}

function renderTreePage(treeId: string, storeOverrides = {}, appOverrides = {}) {
  mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
    const state = createMockTreeStore(storeOverrides)
    return selector ? selector(state) : state
  })
  mockUseAppStore.mockImplementation((selector?: (state: any) => any) => {
    const state = createMockAppStore(appOverrides)
    return selector ? selector(state) : state
  })

  return renderWithProviders(
    <Routes>
      <Route path="/trees/:treeId" element={<KnowledgeTreePage />} />
      <Route path="/" element={<div data-testid="library">Library</div>} />
    </Routes>,
    { routerProps: { initialEntries: [`/trees/${treeId}`] } }
  )
}

describe('KnowledgeTreePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  // When a valid tree is loaded, the header should show its title and the sidebar its chapters.
  it('renders tree title and chapters sidebar', () => {
    renderTreePage('tree-1', {
      trees: [{ id: 'tree-1', title: 'Machine Learning', description: 'ML basics', num_chapters: 2 }],
      chapters: {
        'tree-1': [
          { id: 'ch-1', number: 1, title: 'Introduction', tree_id: 'tree-1' },
          { id: 'ch-2', number: 2, title: 'Linear Regression', tree_id: 'tree-1' },
        ],
      },
    })

    expect(screen.getByText('Machine Learning')).toBeInTheDocument()
    expect(screen.getByText('Introduction')).toBeInTheDocument()
    expect(screen.getByText('Linear Regression')).toBeInTheDocument()
  })

  // Tabs should allow switching between the Documents view and the Content view.
  it('switches tabs between Knowledge Documents and Content', async () => {
    const { user } = renderTreePage('tree-1', {
      trees: [{ id: 'tree-1', title: 'ML', num_chapters: 1 }],
      chapters: {
        'tree-1': [{ id: 'ch-1', number: 1, title: 'Intro', tree_id: 'tree-1' }],
      },
    })

    // Wait for tree to load and select a chapter so tabs appear
    await user.click(screen.getByText('Intro'))

    const documentsTab = screen.getByRole('tab', { name: /knowledge documents/i })
    const contentTab = screen.getByRole('tab', { name: /content/i })

    expect(documentsTab).toBeInTheDocument()
    expect(contentTab).toBeInTheDocument()

    await user.click(contentTab)
    expect(contentTab).toHaveAttribute('data-state', 'active')
  })

  // If the tree id does not exist, the page should redirect back to the library.
  it('redirects to library when tree is not found', async () => {
    renderTreePage('missing-tree', {
      trees: [],
    })

    await waitFor(() => {
      expect(screen.getByTestId('library')).toBeInTheDocument()
    })
  })

  // Creating a new chapter should invoke the store and refresh the sidebar.
  it('adds a new chapter via sidebar', async () => {
    const createChapter = vi.fn().mockResolvedValue(undefined)
    const fetchChapters = vi.fn().mockResolvedValue(undefined)
    const { user } = renderTreePage('tree-1', {
      trees: [{ id: 'tree-1', title: 'ML', num_chapters: 0 }],
      chapters: { 'tree-1': [] },
      createChapter,
      fetchChapters,
    })

    await user.click(screen.getByText('New Chapter'))
    const input = screen.getByPlaceholderText('Chapter title')
    await user.type(input, 'New Chapter')
    await user.click(screen.getByRole('button', { name: 'Add' }))

    await waitFor(() => {
      expect(createChapter).toHaveBeenCalledWith('tree-1', 'New Chapter')
    })
  })

  // Renaming a chapter should invoke the store update method.
  it('renames a chapter via sidebar', async () => {
    const updateChapter = vi.fn().mockResolvedValue(undefined)
    const fetchChapters = vi.fn().mockResolvedValue(undefined)
    const { user } = renderTreePage('tree-1', {
      trees: [{ id: 'tree-1', title: 'ML', num_chapters: 1 }],
      chapters: {
        'tree-1': [{ id: 'ch-1', number: 1, title: 'Old Title', tree_id: 'tree-1' }],
      },
      updateChapter,
      fetchChapters,
    })

    const renameBtn = screen.getByLabelText('Rename chapter Old Title')
    await user.click(renameBtn)

    const input = screen.getByDisplayValue('Old Title')
    await user.clear(input)
    await user.type(input, 'New Title')
    await user.click(screen.getByLabelText('Save'))

    await waitFor(() => {
      expect(updateChapter).toHaveBeenCalledWith('tree-1', 1, 'New Title')
    })
  })

  // Deleting a chapter should invoke the store delete method after confirmation.
  it('deletes a chapter via sidebar', async () => {
    const deleteChapter = vi.fn().mockResolvedValue(undefined)
    const fetchChapters = vi.fn().mockResolvedValue(undefined)
    const { user } = renderTreePage('tree-1', {
      trees: [{ id: 'tree-1', title: 'ML', num_chapters: 1 }],
      chapters: {
        'tree-1': [{ id: 'ch-1', number: 1, title: 'To Delete', tree_id: 'tree-1' }],
      },
      deleteChapter,
      fetchChapters,
    })

    const deleteBtn = screen.getByLabelText('Delete chapter To Delete')
    await user.click(deleteBtn)

    await waitFor(() => {
      expect(deleteChapter).toHaveBeenCalledWith('tree-1', 1)
    })
  })
})
