/**
 * Subject: src/pages/knowledge-tree/all-documents-tab.tsx — AllDocumentsTab
 * Scope:   Loading state, empty state, document list rendering (source files +
 *          chapter documents), document click to open reader, reader modal display.
 * Out of scope:
 *   - DocumentReader / UnifiedDocumentReader internals → reader tests
 *   - Chapter-level document editing               → knowledge-documents-tab.test.tsx
 * Setup:   useKnowledgeTreeStore and client are mocked via vi.hoisted.
 *          DocumentReader and UnifiedDocumentReader are shallowly mocked
 *          to avoid complex reader dependencies.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { AllDocumentsTab } from '../all-documents-tab'
import { renderWithProviders } from '@/test/utils'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockUseKnowledgeTreeStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/knowledge-tree-store', () => ({
  useKnowledgeTreeStore: mockUseKnowledgeTreeStore,
}))

const mockGetDocumentThumbnailUrl = vi.hoisted(() => vi.fn())
vi.mock('@/services', () => ({
  client: {
    getDocumentThumbnailUrl: mockGetDocumentThumbnailUrl,
  },
}))

// Shallow mock the reader components so they don't pull in their own
// complex dependencies (store, PDF, ePub, chat panel, etc.).
// Use @/ alias so vitest resolves consistently with the source imports.
vi.mock('@/components/reader/DocumentReader', () => ({
  DocumentReader: ({ doc, onClose }: { doc: any; onClose: () => void }) => (
    <div data-testid="document-reader">
      Reading: {doc.title}
      <button onClick={onClose}>Close reader</button>
    </div>
  ),
}))

vi.mock('@/components/reader/UnifiedDocumentReader', () => ({
  UnifiedDocumentReader: ({ doc, onClose }: { doc: any; onClose: () => void }) => (
    <div data-testid="unified-document-reader">
      Reading (unified): {doc.title}
      <button onClick={onClose}>Close unified</button>
    </div>
  ),
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
    fetchTrees: vi.fn(),
    createTree: vi.fn(),
    updateTree: vi.fn(),
    deleteTree: vi.fn(),
    fetchChapters: vi.fn(),
    createChapter: vi.fn(),
    updateChapter: vi.fn(),
    deleteChapter: vi.fn(),
    fetchDocuments: vi.fn(),
    fetchAllDocuments: vi.fn().mockResolvedValue(undefined),
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

function renderTab(
  props: { treeId: string; chapters?: any[] },
  storeOverrides: Record<string, any> = {}
) {
  mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
    const state = createMockStore(storeOverrides)
    return selector ? selector(state) : state
  })
  mockGetDocumentThumbnailUrl.mockReturnValue('http://example.com/thumb.png')

  return renderWithProviders(
    <AllDocumentsTab
      treeId={props.treeId}
      chapters={props.chapters ?? []}
    />
  )
}

// ---------------------------------------------------------------------------
// Test data factories
// ---------------------------------------------------------------------------

function makeSourceDoc(overrides: Record<string, any> = {}) {
  return {
    id: 'src-doc-1',
    tree_id: 'tree-1',
    chapter_id: null,
    chapter_number: null,
    title: 'Original Source',
    content: 'Source content',
    is_main: false,
    created_at: '',
    updated_at: '',
    source_file_path: '/files/doc.pdf',
    source_file_name: 'doc.pdf',
    ...overrides,
  }
}

function makeChapterDoc(chapterNum: number, overrides: Record<string, any> = {}) {
  return {
    id: `doc-ch${chapterNum}`,
    tree_id: 'tree-1',
    chapter_id: `ch-${chapterNum}`,
    chapter_number: chapterNum,
    title: `Chapter ${chapterNum} Doc`,
    content: `Content for chapter ${chapterNum}`,
    is_main: false,
    created_at: '',
    updated_at: '',
    source_file_path: `/files/ch${chapterNum}.pdf`,
    source_file_name: `ch${chapterNum}.pdf`,
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AllDocumentsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // When documents are still loading, a loading indicator should be shown
  // so the user knows data is being fetched.
  it('renders loading state when documents are being fetched', () => {
    renderTab(
      { treeId: 'tree-1' },
      {
        documents: { 'tree-1:all': [] },
        documentsLoading: { 'tree-1:all': true },
      }
    )

    expect(screen.getByText('Loading documents...')).toBeInTheDocument()
  })

  // When no documents exist for the tree, the user should see a friendly
  // empty state with guidance on how to add documents.
  it('renders empty state when no documents exist', () => {
    renderTab(
      { treeId: 'tree-1' },
      {
        documents: { 'tree-1:all': [] },
        documentsLoading: { 'tree-1:all': false },
      }
    )

    expect(screen.getByText('No documents yet')).toBeInTheDocument()
    expect(screen.getByText(/import pdf\/epub files into chapters/i)).toBeInTheDocument()
  })

  // Source files (tree-level, with source_file_path and null chapter_number)
  // should appear in the highlighted "Original Source Document" section.
  it('renders source files in a dedicated section', () => {
    const sourceDoc = makeSourceDoc()

    renderTab(
      { treeId: 'tree-1' },
      {
        documents: { 'tree-1:all': [sourceDoc] },
        documentsLoading: { 'tree-1:all': false },
      }
    )

    expect(screen.getByText('Original Source Document')).toBeInTheDocument()
    expect(screen.getByText('Original Source')).toBeInTheDocument()
    expect(screen.getByText('Original')).toBeInTheDocument()
  })

  // Chapter documents should be grouped by chapter number and display
  // the chapter title as a section heading.
  it('renders chapter documents grouped by chapter', () => {
    const ch1Doc = makeChapterDoc(1)
    const ch2Doc = makeChapterDoc(2)

    renderTab(
      {
        treeId: 'tree-1',
        chapters: [
          { id: 'ch-1', number: 1, title: 'Introduction', tree_id: 'tree-1' },
          { id: 'ch-2', number: 2, title: 'Main Content', tree_id: 'tree-1' },
        ],
      },
      {
        documents: { 'tree-1:all': [ch1Doc, ch2Doc] },
        documentsLoading: { 'tree-1:all': false },
      }
    )

    expect(screen.getByText('Introduction')).toBeInTheDocument()
    expect(screen.getByText('Main Content')).toBeInTheDocument()
    expect(screen.getByText('Chapter 1 Doc')).toBeInTheDocument()
    expect(screen.getByText('Chapter 2 Doc')).toBeInTheDocument()
  })

  // Clicking on a chapter document that has a PDF source file should open
  // the DocumentReader modal for viewing.
  it('opens DocumentReader when a chapter document with PDF is clicked', async () => {
    const chDoc = makeChapterDoc(1)
    const { user } = renderTab(
      {
        treeId: 'tree-1',
        chapters: [
          { id: 'ch-1', number: 1, title: 'Introduction', tree_id: 'tree-1' },
        ],
      },
      {
        documents: { 'tree-1:all': [chDoc] },
        documentsLoading: { 'tree-1:all': false },
      }
    )

    // Click the document card (the div containing the document title)
    await user.click(screen.getByText('Chapter 1 Doc'))

    await waitFor(() => {
      expect(screen.getByTestId('document-reader')).toBeInTheDocument()
      expect(screen.getByText('Reading: Chapter 1 Doc')).toBeInTheDocument()
    })
  })

  // Clicking on a source document with a PDF file should open the
  // UnifiedDocumentReader (the enhanced reader with chapter navigation).
  it('opens UnifiedDocumentReader when a source document with PDF is clicked', async () => {
    const sourceDoc = makeSourceDoc()
    const { user } = renderTab(
      {
        treeId: 'tree-1',
        chapters: [],
      },
      {
        documents: { 'tree-1:all': [sourceDoc] },
        documentsLoading: { 'tree-1:all': false },
      }
    )

    // Click the source document row (the div wrapping the document info)
    await user.click(screen.getByText('Original Source'))

    await waitFor(() => {
      expect(screen.getByTestId('unified-document-reader')).toBeInTheDocument()
      expect(screen.getByText('Reading (unified): Original Source')).toBeInTheDocument()
    })
  })

  // The component should not crash when a chapter referenced by a document
  // does not exist in the chapters array — it falls back to "Chapter N".
  it('falls back to chapter number when chapter title is unavailable', () => {
    const chDoc = makeChapterDoc(3)

    renderTab(
      {
        treeId: 'tree-1',
        chapters: [], // no chapter metadata available
      },
      {
        documents: { 'tree-1:all': [chDoc] },
        documentsLoading: { 'tree-1:all': false },
      }
    )

    // Falls back to "Chapter 3" when no matching chapter is found
    expect(screen.getByText('Chapter 3')).toBeInTheDocument()
  })
})
