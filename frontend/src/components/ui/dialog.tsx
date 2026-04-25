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
        'w-full max-w-lg bg-white dark:bg-slate-800 rounded-card shadow-lg p-6',
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
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  className,
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-md bg-white dark:bg-slate-800 rounded-card shadow-lg p-6',
            'animate-fade-in',
            className,
          )}
        >
          <RadixDialog.Title className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">
            {title}
          </RadixDialog.Title>
          {description && (
            <RadixDialog.Description className="text-sm text-gray-600 dark:text-slate-400 mb-6">
              {description}
            </RadixDialog.Description>
          )}
          {!description && <div className="mb-6" />}
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => onOpenChange(false)}
            >
              {cancelLabel}
            </Button>
            <Button
              variant={variant === 'destructive' ? 'destructive' : 'primary'}
              onClick={() => {
                onConfirm()
                onOpenChange(false)
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
