import * as React from 'react'
import { cn } from '../../lib/cn'

export interface BadgeProps {
  variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<BadgeProps['variant'], string> = {
  success: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
  warning: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
  danger: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
  info: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
  neutral: 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300',
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
