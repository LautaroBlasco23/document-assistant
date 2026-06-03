/**
 * Subject: src/components/layout/sidebar.tsx — Sidebar
 * Scope:   Collapse toggle, navigation links, user info display, health dot rendering, limits widget
 * Out of scope:
 *   - useHealth behavior      → use-health.test.tsx
 *   - useLimits behavior      → use-limits.test.ts
 *   - AuthProvider logic      → auth-context.test.tsx
 *   - Tooltip hover behavior  → tooltip.test.tsx
 * Setup: useAppStore, useAuth, and Tooltip are mocked. MemoryRouter provides router context.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Sidebar } from './sidebar'
import { renderWithProviders, screen } from '@/test/utils'

const mockUseAppStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/app-store', () => ({
  useAppStore: mockUseAppStore,
}))

const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('@/auth/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/auth/auth-context')>('@/auth/auth-context')
  return {
    ...actual,
    useAuth: mockUseAuth,
  }
})

// Mock Tooltip to avoid Radix portal complexity; tooltip content is exposed via data attribute only
// so it doesn't interfere with text-visibility assertions in collapsed mode.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children, content }: any) => (
    <div data-tooltip={content}>{children}</div>
  ),
}))

function createMockStore(overrides = {}) {
  return {
    sidebarCollapsed: false,
    toggleSidebar: vi.fn(),
    serviceHealth: null,
    setServiceHealth: vi.fn(),
    errors: [],
    addError: vi.fn(),
    removeError: vi.fn(),
    limits: null,
    setLimits: vi.fn(),
    ...overrides,
  }
}

function setUser(user: any) {
  mockUseAuth.mockReturnValue({
    user,
    isLoading: false,
    token: user ? 'tok' : null,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  })
}

describe('Sidebar', () => {
  beforeEach(() => {
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore())
    )
    setUser(null)
  })

  it('renders navigation links for Library and Settings', () => {
    // The sidebar is the primary navigation chrome; these two links must always be present.
    renderWithProviders(<Sidebar />)

    expect(screen.getByText('Library')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('displays the user avatar and email when a user is logged in', () => {
    // The user section should surface identity information so the viewer knows who is authenticated.
    setUser({
      id: '1',
      email: 'alice@example.com',
      display_name: 'Alice Smith',
    })

    renderWithProviders(<Sidebar />)

    expect(screen.getByText('Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.getByText('AS')).toBeInTheDocument() // initials
  })

  it('falls back to email for avatar initials when display_name is absent', () => {
    // Edge case: users without a display name still need an avatar badge.
    setUser({
      id: '2',
      email: 'bob@example.com',
      display_name: null,
    })

    renderWithProviders(<Sidebar />)

    // When display_name is absent, the email is shown in both the name paragraph
    // and the email paragraph, so we expect two occurrences.
    expect(screen.getAllByText('bob@example.com')).toHaveLength(2)
    // Initials derived from email first letter
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('toggles collapse state when the toggle button is clicked', async () => {
    // The sidebar should be collapsible to free up horizontal space.
    const toggleSidebar = vi.fn()
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore({ sidebarCollapsed: false, toggleSidebar }))
    )

    const { user } = renderWithProviders(<Sidebar />)
    const btn = screen.getByLabelText('Collapse sidebar')

    await user.click(btn)

    expect(toggleSidebar).toHaveBeenCalledTimes(1)
  })

  it('shows expand aria-label when collapsed', () => {
    // Accessibility: the toggle button must describe the action it will perform.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore({ sidebarCollapsed: true }))
    )

    renderWithProviders(<Sidebar />)

    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument()
  })

  it('hides the app name and link labels when collapsed', () => {
    // Collapsed mode is space-constrained, so text labels should be hidden.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore({ sidebarCollapsed: true }))
    )

    renderWithProviders(<Sidebar />)

    expect(screen.queryByText('Doc Assistant')).not.toBeInTheDocument()
    expect(screen.queryByText('Library')).not.toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
  })

  it('renders green health dots when all services are healthy', () => {
    // Even without explicit health data, the sidebar should default to showing healthy indicators.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(
        createMockStore({
          serviceHealth: {
            status: 'healthy',
            services: [
              { name: 'LLM', healthy: true },
              { name: 'PostgreSQL', healthy: true },
            ],
          },
        })
      )
    )

    const { container } = renderWithProviders(<Sidebar />)

    // Both tooltips indicate healthy status via data attribute
    expect(container.querySelector('[data-tooltip="LLM: healthy"]')).toBeInTheDocument()
    expect(container.querySelector('[data-tooltip="PostgreSQL: healthy"]')).toBeInTheDocument()
  })

  it('renders red health dots for unhealthy services', () => {
    // When a service is degraded, the corresponding dot tooltip should indicate unavailability.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(
        createMockStore({
          serviceHealth: {
            status: 'degraded',
            services: [
              { name: 'LLM', healthy: false, error: 'timeout' },
              { name: 'PostgreSQL', healthy: true },
            ],
          },
        })
      )
    )

    const { container } = renderWithProviders(<Sidebar />)

    expect(container.querySelector('[data-tooltip="LLM: unavailable"]')).toBeInTheDocument()
    expect(container.querySelector('[data-tooltip="PostgreSQL: healthy"]')).toBeInTheDocument()
  })

  // The limits widget should render when the app store has limits and link to /settings/plan.
  it('renders the limits widget with plan name and usage counts when limits are available', () => {
    setUser({ id: '1', email: 'a@b.com', display_name: 'Alice' })
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(
        createMockStore({
          limits: {
            max_documents: 200,
            max_knowledge_trees: 3,
            current_documents: 47,
            current_knowledge_trees: 2,
            can_create_document: true,
            can_create_tree: true,
            plan: { slug: 'free', name: 'Free', description: 'Get started' },
          },
        })
      )
    )

    renderWithProviders(<Sidebar />)

    // Plan name appears in the widget header.
    expect(screen.getByText('Free')).toBeInTheDocument()
    // Usage counts (x / y) appear for both trees and documents.
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(screen.getByText('47 / 200')).toBeInTheDocument()
    // The widget is a NavLink to /settings/plan.
    const widgetLink = screen.getByRole('link', { name: /free/i }).closest('a[href="/settings/plan"]')
    expect(widgetLink).toBeInTheDocument()
  })

  // The limits widget should not render anything when limits are not yet available.
  it('does not render the limits widget when limits are null', () => {
    setUser({ id: '1', email: 'a@b.com', display_name: 'Alice' })
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore({ limits: null }))
    )

    renderWithProviders(<Sidebar />)

    expect(screen.queryByText('2 / 3')).not.toBeInTheDocument()
    expect(screen.queryByText('47 / 200')).not.toBeInTheDocument()
  })

  // The collapsed sidebar should expose the limits widget with a tooltip summarizing usage.
  it('shows the limits widget tooltip when the sidebar is collapsed', () => {
    setUser({ id: '1', email: 'a@b.com', display_name: 'Alice' })
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(
        createMockStore({
          sidebarCollapsed: true,
          limits: {
            max_documents: 200,
            max_knowledge_trees: 3,
            current_documents: 47,
            current_knowledge_trees: 2,
            can_create_document: true,
            can_create_tree: true,
            plan: { slug: 'free', name: 'Free', description: 'Get started' },
          },
        })
      )
    )

    const { container } = renderWithProviders(<Sidebar />)

    expect(
      container.querySelector('[data-tooltip="Trees 2/3 · Documents 47/200"]')
    ).toBeInTheDocument()
  })
})
