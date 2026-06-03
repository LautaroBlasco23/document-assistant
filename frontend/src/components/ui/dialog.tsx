import * as RadixDialog from '@radix-ui/react-dialog'
import { Button } from './button'
import { cn } from '../../lib/cn'

export interface DialogContentProps {
  children: React.ReactNode
  className?: string
}

export function DialogContent({ children, className }: DialogContentProps) {
  return (
    <RadixDialog.Content
      className={cn(
        'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
        'w-full max-w-lg bg-surface dark:bg-surface rounded-card shadow-lg p-6',
        'animate-fade-in',
        className,
      )}
    >
      {children}
    </RadixDialog.Content>
  )
}

export interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  onConfirm: () => void
  /** Async confirm — show loading spinner on the confirm button */
  confirmLoading?: boolean
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'destructive'
  className?: string
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  confirmLoading = false,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  className,
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={(o) => { if (!confirmLoading) onOpenChange(o) }}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-md bg-surface dark:bg-surface rounded-card shadow-lg p-6',
            'animate-fade-in',
            className,
          )}
        >
          <RadixDialog.Title className="text-lg font-semibold text-text-primary mb-2">
            {title}
          </RadixDialog.Title>
          {description && (
              <RadixDialog.Description className="text-sm text-text-tertiary mb-6">
              {description}
            </RadixDialog.Description>
          )}
          {!description && <div className="mb-6" />}
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => onOpenChange(false)}
              disabled={confirmLoading}
            >
              {cancelLabel}
            </Button>
            <Button
              variant={variant === 'destructive' ? 'destructive' : 'primary'}
              loading={confirmLoading}
              onClick={() => {
                onConfirm()
                if (!confirmLoading) onOpenChange(false)
              }}
            >
              {confirmLabel}
            </Button>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
