/**
 * Subject: src/components/ui/textarea.tsx — Textarea component
 * Scope:   Value binding, onChange firing, label rendering, error display, rows attribute
 * Out of scope:
 *   - Form submission behavior
 *   - Auto-resize logic
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Textarea } from './textarea'

describe('Textarea', () => {
  // Typing into the textarea should update its value and fire onChange.
  it('binds value and fires onChange', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()
    render(<Textarea value="" onChange={handleChange} />)
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'hello')
    expect(handleChange).toHaveBeenCalledTimes(5)
  })

  // The label should be visible and associated with the textarea via htmlFor.
  it('renders label and associates it with the textarea', () => {
    render(<Textarea label="Notes" />)
    const label = screen.getByText('Notes')
    expect(label).toBeInTheDocument()
    expect(label).toHaveAttribute('for', 'notes')
    expect(screen.getByRole('textbox')).toHaveAttribute('id', 'notes')
  })

  // When an error message is provided, it should be visible to the user.
  it('displays error message', () => {
    render(<Textarea error="Too long" />)
    expect(screen.getByText('Too long')).toBeInTheDocument()
  })

  // The rows attribute should be passed through to the underlying textarea element.
  it('passes rows attribute', () => {
    render(<Textarea rows={10} />)
    expect(screen.getByRole('textbox')).toHaveAttribute('rows', '10')
  })
})
