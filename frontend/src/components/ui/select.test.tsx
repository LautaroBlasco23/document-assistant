/**
 * Subject: src/components/ui/select.tsx — Select component
 * Scope:   Rendering options, onChange firing, label display, error message display
 * Out of scope:
 *   - Multi-select behavior (not supported by this component)
 *   - Complex option grouping
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Select } from './select'

describe('Select', () => {
  // Options should be rendered as child <option> elements inside the <select>.
  it('renders options', () => {
    render(
      <Select>
        <option value="a">Option A</option>
        <option value="b">Option B</option>
      </Select>,
    )
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByText('Option A')).toBeInTheDocument()
    expect(screen.getByText('Option B')).toBeInTheDocument()
  })

  // Changing the selected option should fire the onChange handler.
  it('fires onChange when selection changes', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()
    render(
      <Select onChange={handleChange}>
        <option value="a">A</option>
        <option value="b">B</option>
      </Select>,
    )
    await user.selectOptions(screen.getByRole('combobox'), 'b')
    expect(handleChange).toHaveBeenCalledTimes(1)
  })

  // The label should be visible and associated with the select via htmlFor.
  it('displays label and associates it with the select', () => {
    render(<Select label="Category"><option>One</option></Select>)
    const label = screen.getByText('Category')
    expect(label).toBeInTheDocument()
    expect(label).toHaveAttribute('for', 'category')
    expect(screen.getByRole('combobox')).toHaveAttribute('id', 'category')
  })

  // When an error message is provided, it should be visible to the user.
  it('displays error message', () => {
    render(<Select error="Invalid choice"><option>One</option></Select>)
    expect(screen.getByText('Invalid choice')).toBeInTheDocument()
  })
})
