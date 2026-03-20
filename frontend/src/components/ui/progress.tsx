import { cn } from '../../lib/cn'

export interface ProgressProps {
  value?: number
  indeterminate?: boolean
  className?: string
}

export function Progress({ value = 0, indeterminate = false, className }: ProgressProps) {
  const clampedValue = Math.min(100, Math.max(0, value))

  return (
    <div
      className={cn('w-full bg-surface-200 rounded-full h-2 overflow-hidden', className)}
      role="progressbar"
      aria-valuenow={indeterminate ? undefined : clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      {indeterminate ? (
        <div className="h-2 w-1/3 bg-primary rounded-full animate-pulse" />
      ) : (
        <div
          className="bg-primary h-2 rounded-full transition-all duration-300"
          style={{ width: `${clampedValue}%` }}
        />
      )}
    </div>
  )
}
