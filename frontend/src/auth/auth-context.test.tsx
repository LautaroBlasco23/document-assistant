import { screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { useAuth } from './auth-context'
import { renderWithProviders } from '@/test/utils'
import type { AuthTokenResponse, UserProfile } from '@/types/api'

vi.mock('@/services/index', () => ({
  client: {
    login: vi.fn(),
    register: vi.fn(),
    getMe: vi.fn(),
  },
}))

const clientModule = await import('@/services/index')
const mockClient = vi.mocked(clientModule.client, true)

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
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
  })

  it('login stores JWT in localStorage and sets user state', async () => {
    const loginResponse: AuthTokenResponse = { access_token: 'jwt-login', token_type: 'bearer', expires_in_days: 7 }
    const userProfile: UserProfile = { id: '1', email: 'a@b.com', display_name: 'Alice', has_first_agent: false, created_at: new Date().toISOString() }
    mockClient.login.mockResolvedValue(loginResponse)
    mockClient.getMe.mockResolvedValue(userProfile)

    const { user } = renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))

    await user.click(screen.getByTestId('login-btn'))

    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('jwt-login'))
    expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    expect(window.localStorage.getItem('auth_token')).toBe('jwt-login')
  })

  it('register stores JWT in localStorage and sets user state', async () => {
    const registerResponse: AuthTokenResponse = { access_token: 'jwt-register', token_type: 'bearer', expires_in_days: 7 }
    const userProfile: UserProfile = { id: '2', email: 'a@b.com', display_name: 'Alice', has_first_agent: false, created_at: new Date().toISOString() }
    mockClient.register.mockResolvedValue(registerResponse)
    mockClient.getMe.mockResolvedValue(userProfile)

    const { user } = renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))

    await user.click(screen.getByTestId('register-btn'))

    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('jwt-register'))
    expect(screen.getByTestId('user')).toHaveTextContent('a@b.com')
    expect(window.localStorage.getItem('auth_token')).toBe('jwt-register')
  })

  it('logout clears token from localStorage and clears user state', async () => {
    window.localStorage.setItem('auth_token', 'jwt-logout')
    const userProfile: UserProfile = { id: '3', email: 'a@b.com', display_name: 'Alice', has_first_agent: false, created_at: new Date().toISOString() }
    mockClient.getMe.mockResolvedValue(userProfile)

    const { user } = renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('a@b.com'))
    expect(screen.getByTestId('token')).toHaveTextContent('jwt-logout')

    await user.click(screen.getByTestId('logout-btn'))

    expect(screen.getByTestId('user')).toHaveTextContent('null')
    expect(screen.getByTestId('token')).toHaveTextContent('null')
    expect(window.localStorage.getItem('auth_token')).toBeNull()
  })

  it('fetches /api/auth/me on mount when a token is present', async () => {
    window.localStorage.setItem('auth_token', 'jwt-mount')
    const userProfile: UserProfile = { id: '4', email: 'mounted@example.com', display_name: 'Mounted', has_first_agent: false, created_at: new Date().toISOString() }
    mockClient.getMe.mockResolvedValue(userProfile)

    renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('mounted@example.com')
    expect(screen.getByTestId('token')).toHaveTextContent('jwt-mount')
  })

  it('handles 401 on mount gracefully by clearing the stale token', async () => {
    window.localStorage.setItem('auth_token', 'jwt-bad')
    mockClient.getMe.mockRejectedValue(new Error('Unauthorized'))

    renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('null')
    expect(screen.getByTestId('token')).toHaveTextContent('null')
    expect(window.localStorage.getItem('auth_token')).toBeNull()
  })

  it('does not fetch user on mount when no token exists', async () => {
    renderWithProviders(<AuthConsumer />)

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(mockClient.getMe).not.toHaveBeenCalled()
    expect(screen.getByTestId('user')).toHaveTextContent('null')
  })
})
