import * as React from 'react'
import { cn } from '../../lib/cn'

export interface BadgeProps {
  variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<BadgeProps['variant'], string> = {
  success: 'bg-success-light text-success dark:text-success',
  warning: 'bg-warning-light text-warning dark:text-warning',
  danger: 'bg-danger-light text-danger dark:text-danger',
  info: 'bg-primary-light text-primary dark:text-primary',
  neutral: 'bg-surface-100 dark:bg-surface-200 text-surface-200 dark:text-surface-100',
}

export function Badge({ variant, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full',
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}
