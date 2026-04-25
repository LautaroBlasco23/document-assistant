/**
 * Subject: src/components/layout/header.tsx — Header
 * Scope:   Title, breadcrumbs, and action-slot rendering
 * Out of scope:
 *   - Page-level header usage  → individual page tests
 * Setup: Pure component; no mocks required.
 */

import { describe, it, expect } from 'vitest'
import { within } from '@testing-library/react'
import { Header } from './header'
import { renderWithProviders, screen } from '@/test/utils'

describe('Header', () => {
  it('renders the title', () => {
    // The title is the primary heading and must always be visible.
    renderWithProviders(<Header title="Dashboard" />)

    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('renders breadcrumbs with links for items that have an href', () => {
    // Breadcrumbs guide navigation; items with href should be clickable links.
    renderWithProviders(
      <Header
        title="Chapter 1"
        breadcrumbs={[
          { label: 'Library', href: '/' },
          { label: 'My Book', href: '/tree/1' },
          { label: 'Chapter 1' },
        ]}
      />
    )

    expect(screen.getByRole('link', { name: 'Library' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'My Book' })).toHaveAttribute('href', '/tree/1')
    // The last breadcrumb has no href and should render as plain text inside the breadcrumb nav.
    // The title also contains "Chapter 1", so we scope the query to the breadcrumb nav.
    const breadcrumbNav = screen.getByRole('navigation', { name: 'Breadcrumb' })
    expect(within(breadcrumbNav).getByText('Chapter 1')).toBeInTheDocument()
  })

  it('does not render the breadcrumb nav when breadcrumbs are empty', () => {
    // When no context is provided, the breadcrumb area should be omitted entirely.
    const { container } = renderWithProviders(<Header title="Simple" breadcrumbs={[]} />)

    expect(container.querySelector('nav[aria-label="Breadcrumb"]')).not.toBeInTheDocument()
  })

  it('renders the action slot when actions are provided', () => {
    // The actions area is optional and should only appear when the caller supplies content.
    renderWithProviders(
      <Header
        title="Details"
        actions={<button>Save</button>}
      />
    )

    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
  })

  it('omits the action slot when no actions are provided', () => {
    // Without actions the header should not reserve space for an empty slot.
    renderWithProviders(<Header title="Details" />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
