import * as React from 'react'
import { cn } from '../../lib/cn'

export interface CardProps {
  title?: string
  actions?: React.ReactNode
  className?: string
  children?: React.ReactNode
  onClick?: () => void
}

export function Card({ title, actions, className, children, onClick }: CardProps) {
  const hasHeader = title !== undefined || actions !== undefined

  return (
    <div
      className={cn(
        'bg-surface dark:bg-surface-card rounded-card shadow-sm border border-surface-200 dark:border-surface-200 p-5',
        onClick && 'cursor-pointer',
        className,
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {hasHeader && (
        <>
          <div className="flex items-center justify-between">
            {title && (
              <h3 className="font-semibold text-text-primary">{title}</h3>
            )}
            {actions && (
              <div className="ml-auto flex items-center gap-2">{actions}</div>
            )}
          </div>
          <div className="border-b border-surface-200 dark:border-surface-200 mb-4 pb-3" />
        </>
      )}
      {children}
    </div>
  )
}
