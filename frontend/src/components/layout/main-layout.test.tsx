/**
 * Subject: src/components/layout/main-layout.tsx — MainLayout
 * Scope:   Layout shell rendering (sidebar + outlet) and health-polling lifecycle
 * Out of scope:
 *   - Sidebar behavior          → sidebar.test.tsx
 *   - HealthBanner visibility   → health-banner.test.tsx
 *   - useHealth internals       → use-health.test.tsx
 * Setup: Outlet is mocked to avoid react-router route-configuration boilerplate.
 *        useHealth, useAuth, and useAppStore are mocked to keep the test focused on MainLayout.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MainLayout } from './main-layout'
import { renderWithProviders, screen } from '@/test/utils'

const mockUseAppStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/app-store', () => ({
  useAppStore: mockUseAppStore,
}))

const mockUseHealth = vi.hoisted(() => vi.fn())
vi.mock('@/hooks/use-health', () => ({
  useHealth: mockUseHealth,
}))

const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('@/auth/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/auth/auth-context')>('@/auth/auth-context')
  return {
    ...actual,
    useAuth: mockUseAuth,
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    Outlet: () => <div data-testid="outlet">Outlet Content</div>,
  }
})

function createMockStore(overrides = {}) {
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

describe('MainLayout', () => {
  beforeEach(() => {
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore())
    )
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      token: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    })
    mockUseHealth.mockClear()
  })

  it('starts health polling on mount by calling useHealth', () => {
    // MainLayout is responsible for initiating the background health checks.
    // We verify the hook is invoked as a side-effect of rendering.
    renderWithProviders(<MainLayout />)

    expect(mockUseHealth).toHaveBeenCalledTimes(1)
  })

  it('renders the sidebar and the outlet content area', () => {
    // The layout must always provide the sidebar chrome and a slot for nested routes.
    renderWithProviders(<MainLayout />)

    // Sidebar presence is indicated by the collapse-toggle button
    expect(screen.getByLabelText(/collapse sidebar/i)).toBeInTheDocument()
    // Outlet is rendered inside the main content area
    expect(screen.getByTestId('outlet')).toBeInTheDocument()
  })

  it('passes current service health to the banner', () => {
    // The layout reads serviceHealth from the app store and forwards it to HealthBanner.
    // We verify the banner is present by looking for its dismiss button when health is degraded.
    const degradedHealth = {
      status: 'degraded',
      services: [{ name: 'LLM', healthy: false, error: 'timeout' }],
    }
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore({ serviceHealth: degradedHealth }))
    )

    renderWithProviders(<MainLayout />)

    expect(screen.getByText(/some services are unavailable/i)).toBeInTheDocument()
  })
})
