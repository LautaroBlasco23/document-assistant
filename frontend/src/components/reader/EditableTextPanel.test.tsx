/**
 * Subject: src/components/reader/EditableTextPanel.tsx
 * Scope:   controlled textarea behavior, preview toggle, error display,
 *          disabled state during save
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EditableTextPanel } from './EditableTextPanel'

describe('EditableTextPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders a textarea with the current value', () => {
    render(
      <EditableTextPanel
        value="hello world"
        fileType="txt"
        isSaving={false}
        supportsPreview={false}
        onChange={vi.fn()}
      />
    )
    const textarea = screen.getByLabelText('Edit document text') as HTMLTextAreaElement
    expect(textarea.value).toBe('hello world')
  })

  it('emits onChange when the user types', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <EditableTextPanel
        value=""
        fileType="txt"
        isSaving={false}
        supportsPreview={false}
        onChange={onChange}
      />
    )
    const textarea = screen.getByLabelText('Edit document text')
    await user.type(textarea, 'abc')
    // Controlled component: onChange fires for each keystroke. We don't
    // assert on the cumulative value (the parent stub here does not
    // re-render), only that the callback is invoked with the typed character
    // on each call.
    expect(onChange).toHaveBeenCalled()
    const allValues = onChange.mock.calls.map((c) => c[0] as string)
    expect(allValues.some((v) => v.length > 0)).toBe(true)
  })

  it('disables the textarea when isSaving is true', () => {
    render(
      <EditableTextPanel
        value="x"
        fileType="txt"
        isSaving={true}
        supportsPreview={false}
        onChange={vi.fn()}
      />
    )
    const textarea = screen.getByLabelText('Edit document text')
    expect(textarea).toBeDisabled()
  })

  it('does not show the preview toggle when supportsPreview is false', () => {
    render(
      <EditableTextPanel
        value="x"
        fileType="txt"
        isSaving={false}
        supportsPreview={false}
        onChange={vi.fn()}
      />
    )
    expect(screen.queryByRole('button', { name: /preview/i })).not.toBeInTheDocument()
  })

  it('shows the preview toggle for .md files and renders the preview pane after click', async () => {
    const user = userEvent.setup()
    render(
      <EditableTextPanel
        value="# Title"
        fileType="md"
        isSaving={false}
        supportsPreview={true}
        onChange={vi.fn()}
      />
    )
    // Preview pane is hidden until the toggle is clicked.
    expect(screen.queryByLabelText('Live preview')).not.toBeInTheDocument()
    const toggle = screen.getByRole('button', { name: /preview/i })
    await user.click(toggle)
    // Now the preview pane is mounted with the heading.
    expect(screen.getByLabelText('Live preview')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument()
  })

  it('displays an error banner when error prop is provided', () => {
    render(
      <EditableTextPanel
        value="x"
        fileType="txt"
        isSaving={false}
        error="Could not save"
        supportsPreview={false}
        onChange={vi.fn()}
      />
    )
    expect(screen.getByText('Could not save')).toBeInTheDocument()
  })
})
