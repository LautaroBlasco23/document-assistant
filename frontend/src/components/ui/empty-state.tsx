import * as React from 'react'
import { Button } from './button'
import { cn } from '../../lib/cn'

export interface EmptyStateProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <Icon className="h-12 w-12 text-surface-200 dark:text-surface-200" />
      <p className="font-medium text-surface-100 dark:text-surface-100">{title}</p>
      <p className="text-sm text-surface-100 dark:text-surface-100 max-w-xs">{description}</p>
      {action && (
        <Button variant="primary" size="sm" onClick={action.onClick} className="mt-1">
          {action.label}
        </Button>
      )}
    </div>
  )
}
