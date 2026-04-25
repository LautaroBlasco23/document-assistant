/**
 * Subject: src/components/ui/input.tsx — Input component
 * Scope:   Label rendering, value binding, onChange firing, error display, ref forwarding
 * Out of scope:
 *   - Form integration (covered by page tests)
 *   - Complex validation logic
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from './input'
import { createRef } from 'react'

describe('Input', () => {
  // The label should be visible and associated with the input via htmlFor.
  it('renders label and associates it with the input', () => {
    render(<Input label="Email" />)
    const label = screen.getByText('Email')
    expect(label).toBeInTheDocument()
    expect(label).toHaveAttribute('for', 'email')
    expect(screen.getByRole('textbox')).toHaveAttribute('id', 'email')
  })

  // Typing into the input should update its value and fire onChange.
  it('binds value and fires onChange', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()
    render(<Input value="" onChange={handleChange} />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'hello')
    expect(handleChange).toHaveBeenCalledTimes(5)
  })

  // When an error message is provided, it should be visible to the user.
  it('displays error message', () => {
    render(<Input error="Required field" />)
    expect(screen.getByText('Required field')).toBeInTheDocument()
  })

  // Forwarding refs allows parent components to access the underlying DOM node for focus, selection, etc.
  it('forwards ref to the underlying input element', () => {
    const ref = createRef<HTMLInputElement>()
    render(<Input ref={ref} />)
    expect(ref.current).toBeInstanceOf(HTMLInputElement)
  })
})
