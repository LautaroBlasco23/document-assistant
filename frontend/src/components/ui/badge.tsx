import * as React from 'react'
import { cn } from '../../lib/cn'

export interface BadgeProps {
  variant:
    | 'mastered'
    | 'learning'
    | 'review'
    | 'difficult'
    | 'success'
    | 'warning'
    | 'error'
    | 'info'
    | 'neutral'
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<BadgeProps['variant'], string> = {
  // Education domain states (Phase 3) — use for chapter read, exam score,
  // answer correctness, "needs review" affordances, etc.
  mastered:  'bg-mastered-bg  text-mastered  dark:text-mastered',
  learning:  'bg-learning-bg  text-learning  dark:text-learning',
  review:    'bg-review-bg    text-review    dark:text-review',
  difficult: 'bg-difficult-bg text-difficult dark:text-difficult',
  // System feedback (toasts, form validation) — keep distinct from the
  // domain states above even when colors look similar.
  success: 'bg-success-light text-success dark:text-success',
  warning: 'bg-warning-light text-warning dark:text-warning',
  error:  'bg-error-light  text-error  dark:text-error',
  info:    'bg-primary-light text-primary dark:text-primary',
  neutral: 'bg-surface-100 dark:bg-surface-200 text-text-secondary',
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
