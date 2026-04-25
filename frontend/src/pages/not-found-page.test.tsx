/**
 * Subject: src/pages/not-found-page.tsx — NotFoundPage
 * Scope:   404 messaging, navigation back to library
 * Out of scope:
 *   - Router-level 404 matching   → router tests
 * Setup:   MemoryRouter captures navigation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { useLocation } from 'react-router-dom'
import { NotFoundPage } from './not-found-page'
import { renderWithProviders } from '@/test/utils'

function LocationDisplay() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}</div>
}

describe('NotFoundPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // A friendly 404 page should clearly communicate that the route does not exist.
  it('renders 404 message', () => {
    renderWithProviders(<NotFoundPage />)

    expect(screen.getByText('Page not found')).toBeInTheDocument()
    expect(screen.getByText("The page you're looking for doesn't exist.")).toBeInTheDocument()
  })

  // The primary call-to-action should take the user back to the safe ground of the library.
  it('navigates to library when Back to Library is clicked', async () => {
    const { user } = renderWithProviders(
      <>
        <NotFoundPage />
        <LocationDisplay />
      </>,
      { routerProps: { initialEntries: ['/nonexistent'] } }
    )

    await user.click(screen.getByRole('button', { name: /back to library/i }))

    expect(screen.getByTestId('location')).toHaveTextContent('/')
  })
})
