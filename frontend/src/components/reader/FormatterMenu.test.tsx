/**
 * Subject: src/components/reader/FormatterMenu.tsx — edit-mode rendering
 * Scope:   when isEditing is true, render Save/Cancel and call onSave / onCancel.
 *          When isEditing is false, render the Edit button that calls onEnterEdit.
 * Out of scope:
 *   - The full format dropdown menu (covered by behaviour; here we focus on
 *     the manual-edit affordances added in this change).
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FormatterMenu } from './FormatterMenu'

const baseProps = {
  mode: 'plain' as const,
  isImproved: false,
  isImproving: false,
  onModeChange: vi.fn(),
  onImprove: vi.fn(),
  onImproveFormatting: vi.fn(),
  onRevert: vi.fn(),
  isEditing: false,
  isSaving: false,
  isDirty: false,
  onEnterEdit: vi.fn(),
  onSave: vi.fn(),
  onCancel: vi.fn(),
  canEdit: true,
}

describe('FormatterMenu — manual edit', () => {
  it('renders an Edit button when not editing', () => {
    render(<FormatterMenu {...baseProps} />)
    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument()
  })

  it('calls onEnterEdit when the Edit button is clicked', async () => {
    const onEnterEdit = vi.fn()
    const user = userEvent.setup()
    render(<FormatterMenu {...baseProps} onEnterEdit={onEnterEdit} />)
    await user.click(screen.getByRole('button', { name: /^edit$/i }))
    expect(onEnterEdit).toHaveBeenCalledTimes(1)
  })

  it('disables the Edit button when canEdit is false', () => {
    render(<FormatterMenu {...baseProps} canEdit={false} />)
    expect(screen.getByRole('button', { name: /^edit$/i })).toBeDisabled()
  })

  it('disables the Edit button when an AI improve is in flight', () => {
    render(<FormatterMenu {...baseProps} isImproving={true} />)
    expect(screen.getByRole('button', { name: /^edit$/i })).toBeDisabled()
  })

  it('renders Save and Cancel buttons in edit mode', () => {
    render(<FormatterMenu {...baseProps} isEditing={true} />)
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument()
  })

  it('disables Save when isDirty is false', () => {
    render(<FormatterMenu {...baseProps} isEditing={true} isDirty={false} />)
    expect(screen.getByRole('button', { name: /^save$/i })).toBeDisabled()
  })

  it('enables Save when isDirty is true', () => {
    render(<FormatterMenu {...baseProps} isEditing={true} isDirty={true} />)
    expect(screen.getByRole('button', { name: /^save$/i })).not.toBeDisabled()
  })

  it('disables Save and Cancel while isSaving is true', () => {
    render(
      <FormatterMenu
        {...baseProps}
        isEditing={true}
        isDirty={true}
        isSaving={true}
      />
    )
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeDisabled()
  })

  it('calls onSave when Save is clicked', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(
      <FormatterMenu
        {...baseProps}
        isEditing={true}
        isDirty={true}
        onSave={onSave}
      />
    )
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when Cancel is clicked', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()
    render(
      <FormatterMenu
        {...baseProps}
        isEditing={true}
        onCancel={onCancel}
      />
    )
    await user.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})
