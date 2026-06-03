/**
 * Subject: src/pages/settings/plan-page.tsx — PlanPage
 * Scope:   Loading state, rendering plan name, progress bars, and counts
 * Out of scope:
 *   - Plan upgrade flow (no upgrade UI in this page)
 *   - The /users/me/limits endpoint itself → real-client.test.ts / mock-client.test.ts
 *   - useLimits polling → use-limits.test.ts
 * Setup:   useAppStore is mocked to inject limits; useAuth is mocked.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { PlanPage } from './plan-page'
import { renderWithProviders } from '@/test/utils'

const mockUseAppStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/app-store', async () => {
  const actual = await vi.importActual<typeof import('@/stores/app-store')>('@/stores/app-store')
  return {
    ...actual,
    useAppStore: mockUseAppStore,
  }
})

const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('@/auth/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/auth/auth-context')>('@/auth/auth-context')
  return {
    ...actual,
    useAuth: mockUseAuth,
  }
})

function setLimits(limits: any) {
  mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
    selector({ limits })
  )
}

function setAuth(user: { id: string; email: string } | null) {
  mockUseAuth.mockReturnValue({
    user: user as never,
    token: user ? 'tok' : null,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refetchUser: vi.fn(),
  })
}

describe('PlanPage', () => {
  beforeEach(() => {
    setAuth({ id: 'u1', email: 'a@b.com' })
  })

  // While limits are still loading (limits === null), the page shows a skeleton.
  it('renders loading skeleton when limits are not yet available', () => {
    setLimits(null)
    const { container } = renderWithProviders(<PlanPage />)

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  // Once limits are in the store, both counts and the plan name should render.
  it('renders user limits with counts and the plan name from the API', () => {
    setLimits({
      max_documents: 50,
      max_knowledge_trees: 10,
      current_documents: 25,
      current_knowledge_trees: 3,
      can_create_document: true,
      can_create_tree: true,
      plan: { slug: 'free', name: 'Free', description: 'Get started with basic document processing' },
    })

    renderWithProviders(<PlanPage />)

    expect(screen.getByText('3 / 10')).toBeInTheDocument()
    expect(screen.getByText('25 / 50')).toBeInTheDocument()
    expect(screen.getByText('Free Plan')).toBeInTheDocument()
  })

  // When a pro plan is returned, the heading reflects it.
  it('renders the pro plan name when the API returns a pro plan', () => {
    setLimits({
      max_documents: 1000,
      max_knowledge_trees: 50,
      current_documents: 42,
      current_knowledge_trees: 5,
      can_create_document: true,
      can_create_tree: true,
      plan: { slug: 'pro', name: 'Pro', description: 'For power users' },
    })

    renderWithProviders(<PlanPage />)

    expect(screen.getByText('Pro Plan')).toBeInTheDocument()
  })

  // When the user has no assigned plan, fall back to "Free" rather than crashing.
  it('falls back to Free plan name when plan is null', () => {
    setLimits({
      max_documents: 0,
      max_knowledge_trees: 0,
      current_documents: 0,
      current_knowledge_trees: 0,
      can_create_document: false,
      can_create_tree: false,
      plan: null,
    })

    renderWithProviders(<PlanPage />)

    expect(screen.getByText('Free Plan')).toBeInTheDocument()
  })
})
