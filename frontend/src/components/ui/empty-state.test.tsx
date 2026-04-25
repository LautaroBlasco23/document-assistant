/**
 * Subject: src/components/ui/empty-state.tsx — EmptyState component
 * Scope:   Rendering icon, title, description; conditional action button
 * Out of scope:
 *   - Icon component internals (tested by icon library)
 *   - Styling details beyond presence/absence of elements
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EmptyState } from './empty-state'

// Simple stub icon for testing
function TestIcon({ className }: { className?: string }) {
  return <svg data-testid="test-icon" className={className} />
}

describe('EmptyState', () => {
  // The empty state should display its three primary visual elements: icon, title, and description.
  it('renders icon, title, and description', () => {
    render(
      <EmptyState
        icon={TestIcon}
        title="No items"
        description="Get started by creating your first item."
      />,
    )
    expect(screen.getByTestId('test-icon')).toBeInTheDocument()
    expect(screen.getByText('No items')).toBeInTheDocument()
    expect(screen.getByText('Get started by creating your first item.')).toBeInTheDocument()
  })

  // When an action is provided, a button should be rendered and be clickable.
  it('renders action button when action is provided', async () => {
    const handleAction = vi.fn()
    const user = userEvent.setup()
    render(
      <EmptyState
        icon={TestIcon}
        title="No items"
        description="Create one now."
        action={{ label: 'Create', onClick: handleAction }}
      />,
    )
    const button = screen.getByRole('button', { name: 'Create' })
    expect(button).toBeInTheDocument()
    await user.click(button)
    expect(handleAction).toHaveBeenCalledTimes(1)
  })

  // Omitting the action prop should not render any button element.
  it('does not render a button when action is omitted', () => {
    render(
      <EmptyState
        icon={TestIcon}
        title="No items"
        description="Nothing to do here."
      />,
    )
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
