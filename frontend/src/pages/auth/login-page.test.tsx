/**
 * Subject: src/pages/auth/login-page.tsx — LoginPage
 * Scope:   Form rendering, submission behavior, error display, navigation link
 * Out of scope:
 *   - AuthProvider internals          → auth-context.test.tsx
 *   - useNavigate mechanics           → router integration tests
 * Setup:   useAuth is mocked; MemoryRouter provides navigation context.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { useLocation } from 'react-router-dom'
import { LoginPage } from './login-page'
import { renderWithProviders } from '@/test/utils'

const mockLogin = vi.fn()

const mockUseAuth = vi.hoisted(() => vi.fn())
vi.mock('@/auth/auth-context', async () => {
  const actual = await vi.importActual<typeof import('@/auth/auth-context')>('@/auth/auth-context')
  return {
    ...actual,
    useAuth: mockUseAuth,
  }
})

function LocationDisplay() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}</div>
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      user: null,
      token: null,
      isLoading: false,
      register: vi.fn(),
      logout: vi.fn(),
    })
  })

  // The login page is the entry point for returning users; it must expose the two
  // credential fields and a primary action.
  it('renders email and password form', () => {
    renderWithProviders(<LoginPage />)

    expect(screen.getByText('Email')).toBeInTheDocument()
    expect(screen.getByText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  // Submitting the form should invoke the auth layer and, on success, redirect
  // the user to the library. We observe the redirect via MemoryRouter location.
  it('submits form and calls login, then redirects on success', async () => {
    mockLogin.mockResolvedValue(undefined)
    const { user } = renderWithProviders(
      <>
        <LoginPage />
        <LocationDisplay />
      </>,
      { routerProps: { initialEntries: ['/login'] } }
    )

    const emailInput = screen.getByText('Email').parentElement!.querySelector('input')!
    const passwordInput = screen.getByText('Password').parentElement!.querySelector('input')!

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123')
    })
    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('/')
    })
  })

  // A failed login should surface the error message so the user knows what went wrong
  // rather than being left on an unresponsive form.
  it('shows error message when login fails', async () => {
    mockLogin.mockRejectedValue(new Error('Invalid credentials'))
    const { user } = renderWithProviders(<LoginPage />)

    const emailInput = screen.getByText('Email').parentElement!.querySelector('input')!
    const passwordInput = screen.getByText('Password').parentElement!.querySelector('input')!

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  // New users need a discoverable path to registration.
  it('has a link to the register page', () => {
    renderWithProviders(<LoginPage />)

    expect(screen.getByRole('link', { name: /sign up/i })).toHaveAttribute('href', '/register')
  })
})
