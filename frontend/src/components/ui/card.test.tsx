/**
 * Subject: src/components/ui/card.tsx — Card component
 * Scope:   Rendering title/children/actions, onClick interaction, cursor styling
 * Out of scope:
 *   - Keyboard navigation (handled by page-level a11y tests)
 *   - Complex nested layouts
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Card } from './card'

describe('Card', () => {
  // A card should display its title, body content, and action slot elements.
  it('renders title, children, and actions', () => {
    render(
      <Card title="My Card" actions={<button>Action</button>}>
        <p>Content</p>
      </Card>,
    )
    expect(screen.getByText('My Card')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
  })

  // When onClick is provided, the card behaves like a clickable surface.
  it('fires onClick when clicked', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    render(<Card onClick={handleClick}>Clickable</Card>)
    await user.click(screen.getByText('Clickable'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  // Without onClick, the card should not advertise itself as clickable via cursor-pointer.
  it('does not have cursor-pointer when onClick is absent', () => {
    render(<Card>Static</Card>)
    expect(screen.getByText('Static').parentElement).not.toHaveClass('cursor-pointer')
  })
})
