import * as React from 'react'
import { cn } from '../../lib/cn'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-gray-700 dark:text-slate-300"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'w-full rounded-md border border-surface-200 dark:border-slate-600 bg-surface dark:bg-surface-100 px-3 py-2 text-sm text-gray-900 dark:text-slate-100',
            'placeholder:text-gray-400 dark:placeholder:text-slate-500',
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

Input.displayName = 'Input'
