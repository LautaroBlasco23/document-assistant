/**
 * Subject: src/auth/auth-context.tsx — AuthProvider + useAuth
 * Scope:   login, register, logout, initial mount token recovery, 401 handling
 * Out of scope:
 *   - Router navigation behavior → page-level tests
 *   - Real API calls (global.fetch is mocked)
 * Setup:   localStorage is mocked in src/test/setup.ts; global.fetch is vi.fn()
 */

import { screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { useAuth } from './auth-context'
import { renderWithProviders } from '@/test/utils'

function AuthConsumer() {
  const auth = useAuth()
  return (
    <div>
      <div data-testid="user">{auth.user ? JSON.stringify(auth.user) : 'null'}</div>
      <div data-testid="token">{auth.token ?? 'null'}</div>
      <div data-testid="loading">{auth.isLoading ? 'true' : 'false'}</div>
      <button data-testid="login-btn" onClick={() => auth.login('a@b.com', 'secret')}>
        Login
      </button>
      <button
        data-testid="register-btn"
        onClick={() => auth.register('a@b.com', 'secret', 'Alice')}
      >
        Register
      </button>
      <button data-testid="logout-btn" onClick={() => auth.logout()}>
        Logout
      </button>
    </div>
  )
}

describe('AuthProvider + useAuth', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Logging in should persist the JWT and make the user object available to consumers.
  it('login stores JWT in localStorage and sets user state', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url === '/api/auth/login') {
        return { ok: true, json: async () => ({ access_token: 'jwt-login' }) } as Response
      }
      if (url === '/api/auth/me') {
        return { ok: true, json: async () => ({ id: '1', email: 'a@b.com', display_name: 'Alice' }) } as Response
      }
      return { ok: false, status: 404 } as Response
    })

    const { user } = renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))

    await user.click(screen.getByTestId('login-btn'))

    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('jwt-login'))
    expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    expect(window.localStorage.getItem('auth_token')).toBe('jwt-login')
  })

  // Registration should follow the same persistence pattern as login.
  it('register stores JWT in localStorage and sets user state', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url === '/api/auth/register') {
        return { ok: true, json: async () => ({ access_token: 'jwt-register' }) } as Response
      }
      if (url === '/api/auth/me') {
        return { ok: true, json: async () => ({ id: '2', email: 'a@b.com', display_name: 'Alice' }) } as Response
      }
      return { ok: false, status: 404 } as Response
    })

    const { user } = renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))

    await user.click(screen.getByTestId('register-btn'))

    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('jwt-register'))
    expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    expect(window.localStorage.getItem('auth_token')).toBe('jwt-register')
  })

  // Logout must completely clear session state so the UI returns to anonymous.
  it('logout clears token from localStorage and clears user state', async () => {
    // Seed an authenticated session.
    window.localStorage.setItem('auth_token', 'jwt-logout')
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ id: '3', email: 'a@b.com', display_name: 'Alice' }),
    } as Response)

    const { user } = renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('a@b.com'))
    expect(screen.getByTestId('token')).toHaveTextContent('jwt-logout')

    await user.click(screen.getByTestId('logout-btn'))

    expect(screen.getByTestId('user')).toHaveTextContent('null')
    expect(screen.getByTestId('token')).toHaveTextContent('null')
    expect(window.localStorage.getItem('auth_token')).toBeNull()
  })

  // If a token exists in localStorage the provider should validate it on mount.
  it('fetches /api/auth/me on mount when a token is present', async () => {
    window.localStorage.setItem('auth_token', 'jwt-mount')
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ id: '4', email: 'mounted@example.com', display_name: 'Mounted' }),
    } as Response)

    renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('mounted@example.com')
    expect(screen.getByTestId('token')).toHaveTextContent('jwt-mount')
  })

  // A 401 on mount means the stored token is stale; the provider should silently
  // clear it rather than crash.
  it('handles 401 on mount gracefully by clearing the stale token', async () => {
    window.localStorage.setItem('auth_token', 'jwt-bad')
    fetchMock.mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
    } as Response)

    renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('null')
    expect(screen.getByTestId('token')).toHaveTextContent('null')
    expect(window.localStorage.getItem('auth_token')).toBeNull()
  })

  // When no token is stored there is no reason to hit the API; the provider
  // should immediately finish loading.
  it('does not fetch user on mount when no token exists', async () => {
    renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.getByTestId('user')).toHaveTextContent('null')
  })
})
