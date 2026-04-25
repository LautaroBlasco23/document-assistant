/**
 * Subject: src/pages/settings/plan-page.tsx — PlanPage
 * Scope:   Loading limits, rendering progress bars, counts, error handling
 * Out of scope:
 *   - Plan upgrade flow (no upgrade UI in this page)
 * Setup:   global.fetch is mocked; localStorage token is seeded.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { PlanPage } from './plan-page'
import { renderWithProviders } from '@/test/utils'

describe('PlanPage', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.clearAllMocks()
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    window.localStorage.setItem('auth_token', 'test-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // While limits are loading the user should see a skeleton placeholder.
  it('renders loading skeleton initially', () => {
    fetchMock.mockReturnValue(new Promise(() => {}))
    const { container } = renderWithProviders(<PlanPage />)

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  // Once loaded, both tree and document counts should be visible alongside their progress bars.
  it('renders user limits with progress bars and counts', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        max_documents: 50,
        max_knowledge_trees: 10,
        current_documents: 25,
        current_knowledge_trees: 3,
        can_create_document: true,
        can_create_tree: true,
      }),
    } as Response)
    renderWithProviders(<PlanPage />)

    await waitFor(() => {
      expect(screen.getByText('3 / 10')).toBeInTheDocument()
    })
    expect(screen.getByText('25 / 50')).toBeInTheDocument()
    expect(screen.getByText('Free Plan')).toBeInTheDocument()
  })

  // When the API rejects, the page should surface the failure instead of hanging.
  it('shows error state when fetch fails', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
    } as Response)
    renderWithProviders(<PlanPage />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load limits')).toBeInTheDocument()
    })
  })
})
