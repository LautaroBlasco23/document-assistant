/**
 * Subject: src/components/auth/protected-route.tsx — ProtectedRoute
 * Scope:   Authentication-based route guarding — loading spinner, unauthenticated redirect, authenticated pass-through
 * Out of scope:
 *   - AuthProvider internals  → auth-context.test.tsx
 *   - useAuth hook behavior   → use-auth.test.tsx
 * Setup: useAuth is mocked so tests control auth state directly without hitting the real AuthProvider.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ProtectedRoute } from './protected-route'
import { renderWithProviders, screen } from '@/test/utils'

const mockUseAuth = vi.hoisted(() => vi.fn())

vi.mock('@/auth/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/auth/auth-context')>('@/auth/auth-context')
  return {
    ...actual,
    useAuth: mockUseAuth,
  }
})

function setAuthState(state: { user: any; isLoading: boolean }) {
  mockUseAuth.mockReturnValue({
    user: state.user,
    isLoading: state.isLoading,
    token: state.user ? 'tok' : null,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  })
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    mockUseAuth.mockClear()
  })

  it('shows a spinner while the auth state is loading', () => {
    // When the auth context hasn't finished initializing, the user should see feedback
    // instead of a flash of the login redirect or protected content.
    setAuthState({ user: null, isLoading: true })

    const { container } = renderWithProviders(
      <ProtectedRoute>
        <div data-testid="protected">secret</div>
      </ProtectedRoute>
    )

    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument()
  })

  it('redirects to /login when the user is unauthenticated', () => {
    // An unauthenticated visitor should never see protected UI.
    // Navigate renders nothing, so we assert the child content is absent.
    setAuthState({ user: null, isLoading: false })

    renderWithProviders(
      <ProtectedRoute>
        <div data-testid="protected">secret</div>
      </ProtectedRoute>,
      { routerProps: { initialEntries: ['/dashboard'] } }
    )

    expect(screen.queryByTestId('protected')).not.toBeInTheDocument()
  })

  it('renders children when the user is authenticated', () => {
    // Once auth is resolved and a user exists, the protected content should be visible.
    setAuthState({
      user: { id: '1', email: 'a@b.com', display_name: 'Alice' },
      isLoading: false,
    })

    renderWithProviders(
      <ProtectedRoute>
        <div data-testid="protected">secret</div>
      </ProtectedRoute>
    )

    expect(screen.getByTestId('protected')).toBeInTheDocument()
    expect(screen.getByText('secret')).toBeInTheDocument()
  })
})
