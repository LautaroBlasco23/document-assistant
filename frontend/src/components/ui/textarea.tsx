import * as React from 'react'
import { cn } from '../../lib/cn'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={textareaId}
            className="text-sm font-medium text-gray-700 dark:text-slate-300"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={cn(
            'w-full rounded-md border border-surface-200 dark:border-surface-200 bg-white dark:bg-surface px-3 py-2 text-sm text-gray-900 dark:text-slate-100',
            'placeholder:text-surface-100 dark:placeholder:text-surface-100 resize-y min-h-[80px]',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-surface-100',
            error && 'border-danger focus:ring-danger',
            className,
          )}
          {...props}
        />
        {error && (
          <p className="text-xs text-danger dark:text-danger">{error}</p>
        )}
      </div>
    )
  },
)

Textarea.displayName = 'Textarea'
