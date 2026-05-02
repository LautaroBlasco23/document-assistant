import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { Button } from './button'
import { cn } from '../../lib/cn'

export interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  /** Optional body content rendered between description and action buttons */
  children?: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'destructive'
  loading?: boolean
  onConfirm: () => void | Promise<void>
  className?: string
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  loading = false,
  onConfirm,
  className,
}: ConfirmDialogProps) {
  const handleConfirm = async () => {
    await onConfirm()
  }

  return (
    <RadixDialog.Root open={open} onOpenChange={(o) => { if (!loading) onOpenChange(o) }}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-lg bg-surface dark:bg-surface rounded-card shadow-lg p-6',
            'animate-fade-in flex flex-col gap-4',
            className,
          )}
          onClick={(e) => e.stopPropagation()}
        >
          <div>
            <RadixDialog.Title className="text-base font-semibold text-text-primary">
              {title}
            </RadixDialog.Title>
            {description && (
              <RadixDialog.Description className="text-sm text-text-tertiary mt-1">
                {description}
              </RadixDialog.Description>
            )}
          </div>

          {children && <div>{children}</div>}

          <div className="flex justify-end gap-3 pt-1">
            <Button
              variant="secondary"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              {cancelLabel}
            </Button>
            <Button
              variant={variant === 'destructive' ? 'destructive' : 'primary'}
              onClick={() => void handleConfirm()}
              disabled={loading}
            >
              {loading
                ? <span className="flex items-center gap-2">
                    <span className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    {confirmLabel}
                  </span>
                : confirmLabel
              }
            </Button>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
