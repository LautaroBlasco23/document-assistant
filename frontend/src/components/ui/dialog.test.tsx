/**
 * Subject: src/components/ui/dialog.tsx — Dialog component
 * Scope:   Open/close lifecycle, confirm and cancel callbacks, destructive variant rendering
 * Out of scope:
 *   - Radix UI portal/overlay internals (covered by Radix's own tests)
 *   - Animation details
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Dialog } from './dialog'

describe('Dialog', () => {
  // When open is true, the dialog title and description should be visible.
  it('renders when open', () => {
    render(
      <Dialog
        open={true}
        onOpenChange={() => {}}
        title="Confirm"
        description="Are you sure?"
        onConfirm={() => {}}
      />,
    )
    expect(screen.getByRole('heading', { name: 'Confirm' })).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
  })

  // When open is false, the dialog content should not be in the document.
  it('does not render when closed', () => {
    const { container } = render(
      <Dialog
        open={false}
        onOpenChange={() => {}}
        title="Confirm"
        onConfirm={() => {}}
      />,
    )
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument()
  })

  // Clicking the confirm button should call onConfirm and close the dialog.
  it('fires onConfirm and closes when confirm is clicked', async () => {
    const onConfirm = vi.fn()
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Delete"
        onConfirm={onConfirm}
        confirmLabel="Yes"
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Yes' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  // Clicking the cancel button should close the dialog without calling onConfirm.
  it('fires onOpenChange(false) when cancel is clicked', async () => {
    const onOpenChange = vi.fn()
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Cancel?"
        onConfirm={onConfirm}
        cancelLabel="No"
      />,
    )
    await user.click(screen.getByRole('button', { name: 'No' }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  // Destructive variant should apply the destructive button styling for the confirm action.
  it('renders destructive variant on confirm button', () => {
    render(
      <Dialog
        open={true}
        onOpenChange={() => {}}
        title="Delete"
        onConfirm={() => {}}
        variant="destructive"
        confirmLabel="Delete"
      />,
    )
    expect(screen.getByRole('button', { name: 'Delete' })).toHaveClass('bg-red-500')
  })
})
