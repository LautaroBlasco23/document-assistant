/**
 * Subject: src/components/ui/button.tsx — Button component
 * Scope:   Rendering text, click handling, disabled state, loading spinner, variants, sizes, ref forwarding
 * Out of scope:
 *   - Form submission behavior (covered by page-level tests)
 *   - asChild prop (not implemented in this Button)
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './button'
import { createRef } from 'react'

describe('Button', () => {
  // Basic smoke test: the button text is visible to the user.
  it('renders text children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  // Clicking a button should invoke the provided callback.
  it('fires onClick when clicked', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    render(<Button onClick={handleClick}>Click</Button>)
    await user.click(screen.getByRole('button', { name: 'Click' }))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  // A disabled button must not trigger onClick; this covers both visual and behavioral accessibility.
  it('does not fire onClick when disabled', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    render(<Button onClick={handleClick} disabled>Disabled</Button>)
    await user.click(screen.getByRole('button', { name: 'Disabled' }))
    expect(handleClick).not.toHaveBeenCalled()
  })

  // When loading is true, the button should be disabled and show a visual spinner indicator.
  it('shows spinner and disables button while loading', () => {
    render(<Button loading>Loading</Button>)
    const button = screen.getByRole('button', { name: 'Loading' })
    expect(button).toBeDisabled()
    expect(button.querySelector('[aria-hidden="true"]')).toBeInTheDocument()
  })

  // Each variant produces a distinct visual treatment; we assert on the presence of the variant-specific class.
  it.each([
    ['primary', 'bg-primary'],
    ['secondary', 'bg-surface-100'],
    ['ghost', 'bg-transparent'],
    ['destructive', 'bg-red-500'],
  ] as const)('renders %s variant', (variant, expectedClass) => {
    render(<Button variant={variant}>{variant}</Button>)
    expect(screen.getByRole('button')).toHaveClass(expectedClass)
  })

  // Each size produces different padding and text size; we assert on the presence of the size-specific class.
  it.each([
    ['sm', 'text-sm'],
    ['md', 'text-sm'],
    ['lg', 'text-base'],
  ] as const)('renders %s size', (size, expectedClass) => {
    render(<Button size={size}>{size}</Button>)
    expect(screen.getByRole('button')).toHaveClass(expectedClass)
  })

  // Forwarding refs allows parent components to imperatively access the underlying <button> element.
  it('forwards ref to the underlying button element', () => {
    const ref = createRef<HTMLButtonElement>()
    render(<Button ref={ref}>Ref</Button>)
    expect(ref.current).toBeInstanceOf(HTMLButtonElement)
    expect(ref.current?.tagName).toBe('BUTTON')
  })
})
