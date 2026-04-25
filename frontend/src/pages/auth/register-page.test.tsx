/**
 * Subject: src/pages/auth/register-page.tsx — RegisterPage
 * Scope:   Form rendering, submission behavior, error display, password validation hint, navigation link
 * Out of scope:
 *   - AuthProvider internals          → auth-context.test.tsx
 *   - useNavigate mechanics           → router integration tests
 * Setup:   useAuth is mocked; MemoryRouter provides navigation context.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { useLocation } from 'react-router-dom'
import { RegisterPage } from './register-page'
import { renderWithProviders } from '@/test/utils'

const mockRegister = vi.fn()

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

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      register: mockRegister,
      user: null,
      token: null,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  })

  // The registration form must collect the minimal fields needed to create an account.
  it('renders display name, email, and password form', () => {
    renderWithProviders(<RegisterPage />)

    expect(screen.getByText(/display name/i)).toBeInTheDocument()
    expect(screen.getByText('Email')).toBeInTheDocument()
    expect(screen.getByText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign up/i })).toBeInTheDocument()
  })

  // On successful registration the user should be authenticated and redirected to the library.
  it('submits form and calls register, then redirects on success', async () => {
    mockRegister.mockResolvedValue(undefined)
    const { user } = renderWithProviders(
      <>
        <RegisterPage />
        <LocationDisplay />
      </>,
      { routerProps: { initialEntries: ['/register'] } }
    )

    const displayNameInput = screen.getByText(/display name/i).parentElement!.querySelector('input')!
    const emailInput = screen.getByText('Email').parentElement!.querySelector('input')!
    const passwordInput = screen.getByText('Password').parentElement!.querySelector('input')!

    await user.type(displayNameInput, 'Alice')
    await user.type(emailInput, 'alice@example.com')
    await user.type(passwordInput, 'secret123')
    await user.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('alice@example.com', 'secret123', 'Alice')
    })
    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('/')
    })
  })

  // Failed registration should display the error so the user can correct their input.
  it('shows error message when registration fails', async () => {
    mockRegister.mockRejectedValue(new Error('Email already taken'))
    const { user } = renderWithProviders(<RegisterPage />)

    const emailInput = screen.getByText('Email').parentElement!.querySelector('input')!
    const passwordInput = screen.getByText('Password').parentElement!.querySelector('input')!

    await user.type(emailInput, 'dup@example.com')
    await user.type(passwordInput, 'password')
    await user.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(screen.getByText('Email already taken')).toBeInTheDocument()
    })
  })

  // The password field carries a browser-level constraint to nudge users toward stronger credentials.
  it('has password input with minLength of 6', () => {
    renderWithProviders(<RegisterPage />)

    const passwordInput = screen.getByText('Password').parentElement!.querySelector('input')!
    expect(passwordInput).toHaveAttribute('minLength', '6')
  })

  // Returning users need a quick way to get back to the login screen.
  it('has a link to the login page', () => {
    renderWithProviders(<RegisterPage />)

    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login')
  })
})
