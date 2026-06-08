/**
 * Subject: src/pages/knowledge-tree/all-documents-tab.tsx — AllDocumentsTab
 * Scope:   Collapsible overview section, source files display, chapter documents display
 * Out of scope:
 *   - Document row interactions      → knowledge-documents-tab.test.tsx
 *   - Resume document logic          → integration tests
 * Setup:   useKnowledgeTreeStore, useAppStore, and client are mocked.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { AllDocumentsTab } from './all-documents-tab'
import { renderWithProviders } from '@/test/utils'

const mockUseKnowledgeTreeStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/knowledge-tree-store', () => ({
  useKnowledgeTreeStore: mockUseKnowledgeTreeStore,
}))

const mockUseAppStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/app-store', () => ({
  useAppStore: mockUseAppStore,
}))

vi.mock('@/services', () => ({
  client: {
    getDocumentThumbnailUrl: vi.fn(() => 'http://example.com/thumb.png'),
  },
}))

function createMockStore(overrides = {}) {
  return {
    documents: {} as Record<string, any[]>,
    documentsLoading: {} as Record<string, boolean>,
    fetchAllDocuments: vi.fn().mockResolvedValue(undefined),
    createDocument: vi.fn().mockResolvedValue(undefined),
    updateDocument: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

function renderTab(
  props: { treeId: string; chapters?: any[]; resumeDocId?: string },
  storeOverrides: Record<string, any> = {}
) {
  mockUseKnowledgeTreeStore.mockImplementation((selector?: (state: any) => any) => {
    const state = createMockStore(storeOverrides)
    return selector ? selector(state) : state
  })
  mockUseAppStore.mockImplementation((selector?: (state: any) => any) => {
    const state = {
      addError: vi.fn(),
    }
    return selector ? selector(state) : state
  })

  return renderWithProviders(
    <AllDocumentsTab
      treeId={props.treeId}
      chapters={props.chapters ?? []}
      resumeDocId={props.resumeDocId}
    />
  )
}

describe('AllDocumentsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // The overview section should be visible at the top of the documents tab.
  it('renders collapsible overview section', () => {
    renderTab({ treeId: 'tree-1' }, {
      documents: { 'tree-1:all': [] },
    })

    expect(screen.getByText('Knowledge Tree Overview')).toBeInTheDocument()
    expect(screen.getByText('Add a summary of what this knowledge tree will cover')).toBeInTheDocument()
  })

  // Clicking the overview toggle should expand/collapse the textarea.
  it('expands overview section on click', async () => {
    const { user } = renderTab({ treeId: 'tree-1' }, {
      documents: { 'tree-1:all': [] },
    })

    // Initially collapsed - textarea should not be visible
    expect(screen.queryByPlaceholderText(/write an overview/i)).not.toBeInTheDocument()

    // Click to expand
    await user.click(screen.getByText('Knowledge Tree Overview'))

    // Textarea should now be visible
    expect(screen.getByPlaceholderText(/write an overview/i)).toBeInTheDocument()
  })
})
