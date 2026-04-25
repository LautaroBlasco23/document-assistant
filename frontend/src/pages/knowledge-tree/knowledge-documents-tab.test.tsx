/**
 * Subject: src/pages/knowledge-tree/knowledge-documents-tab.tsx — KnowledgeDocumentsTab
 * Scope:   Main doc editor, document cards, thumbnails, import dialog, delete confirmation
 * Out of scope:
 *   - DocumentReader modal internals      → DocumentReader tests
 *   - Full file upload workflow           → integration tests
 * Setup:   useKnowledgeTreeStore, useAppStore, and client are mocked.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { KnowledgeDocumentsTab } from './knowledge-documents-tab'
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

const mockGetTaskStatus = vi.hoisted(() => vi.fn())
const mockGetDocumentThumbnailUrl = vi.hoisted(() => vi.fn(() => 'http://example.com/thumb.png'))

vi.mock('@/services', () => ({
  client: {
    getTaskStatus: mockGetTaskStatus,
    getDocumentThumbnailUrl: mockGetDocumentThumbnailUrl,
  },
}))

function createMockStore(overrides = {}) {
  return {
    trees: [] as any[],
    treesLoading: false,
    treesFetched: true,
    chapters: {},
    chaptersLoading: {},
    documents: {} as Record<string, any[]>,
    documentsLoading: {} as Record<string, boolean>,
    questionsByType: {},
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
    fetchDocuments: vi.fn().mockResolvedValue(undefined),
    fetchAllDocuments: vi.fn(),
    createDocument: vi.fn().mockResolvedValue(undefined),
    updateDocument: vi.fn().mockResolvedValue(undefined),
    deleteDocument: vi.fn().mockResolvedValue(undefined),
    ingestFileAsDocument: vi.fn().mockResolvedValue({ task_id: 'task-1' }),
    createTreeFromFile: vi.fn(),
    generateQuestions: vi.fn(),
    fetchQuestions: vi.fn(),
    deleteQuestion: vi.fn(),
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
  mockUseAppStore.mockImplementation((selector?: (state: any) => any) => {
    const state = {
      sidebarCollapsed: false,
      toggleSidebar: vi.fn(),
      serviceHealth: null,
      setServiceHealth: vi.fn(),
      errors: [],
      addError: vi.fn(),
      removeError: vi.fn(),
    }
    return selector ? selector(state) : state
  })

  return renderWithProviders(
    <KnowledgeDocumentsTab
      treeId={props.treeId}
      selectedChapter={props.selectedChapter}
      chapters={props.chapters ?? []}
    />
  )
}

describe('KnowledgeDocumentsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  // At the tree level (no chapter selected) the main document editor should be visible.
  it('renders main doc editor when selectedChapter is null', () => {
    renderTab({ treeId: 'tree-1', selectedChapter: null })

    expect(screen.getByText('Overview Document')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/write an overview/i)).toBeInTheDocument()
  })

  // Chapter-level documents should render as cards with thumbnails when available.
  it('renders document cards with thumbnails', () => {
    const doc = {
      id: 'doc-1',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      chapter_number: 1,
      title: 'My PDF',
      content: 'Document content here',
      is_main: false,
      created_at: '',
      updated_at: '',
      source_file_path: '/files/doc.pdf',
      source_file_name: 'doc.pdf',
    }

    renderTab(
      { treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Chapter 1', tree_id: 'tree-1' }] },
      { documents: { 'tree-1:1': [doc] }, documentsLoading: { 'tree-1:1': false } }
    )

    expect(screen.getByText('My PDF')).toBeInTheDocument()
    expect(screen.getByText('Document content here')).toBeInTheDocument()
    expect(screen.getByAltText(/preview of my pdf/i)).toBeInTheDocument()
  })

  // The import button should trigger the hidden file input.
  it('opens import dialog via file input button', async () => {
    const { user } = renderTab({ treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Ch1', tree_id: 'tree-1' }] })

    const importBtn = screen.getByRole('button', { name: /import from pdf\/epub/i })
    await user.click(importBtn)

    // The hidden file input should exist in the DOM
    expect(document.querySelector('input[type="file"]')).toBeInTheDocument()
  })

  // Deleting a document should invoke the store after a browser confirmation.
  it('handles delete confirmation', async () => {
    const deleteDocument = vi.fn().mockResolvedValue(undefined)
    const doc = {
      id: 'doc-1',
      tree_id: 'tree-1',
      chapter_id: 'ch-1',
      chapter_number: 1,
      title: 'To Delete',
      content: 'content',
      is_main: false,
      created_at: '',
      updated_at: '',
    }

    const { user } = renderTab(
      { treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Ch1', tree_id: 'tree-1' }] },
      { documents: { 'tree-1:1': [doc] }, documentsLoading: { 'tree-1:1': false }, deleteDocument }
    )

    const deleteBtn = screen.getByLabelText('Delete document')
    await user.click(deleteBtn)

    await waitFor(() => {
      expect(deleteDocument).toHaveBeenCalledWith('doc-1', 'tree-1', 1)
    })
  })

  // Clicking "Add Document" should reveal the inline creation form.
  it('opens inline create form', async () => {
    const { user } = renderTab({ treeId: 'tree-1', selectedChapter: 1, chapters: [{ id: 'ch-1', number: 1, title: 'Ch1', tree_id: 'tree-1' }] })

    await user.click(screen.getByRole('button', { name: /add document/i }))

    expect(screen.getByPlaceholderText('Document title')).toBeInTheDocument()
  })
})
