import { cn } from '../../lib/cn'

export interface SkeletonLineProps {
  className?: string
}

export function SkeletonLine({ className }: SkeletonLineProps) {
  return (
    <div
      className={cn('h-4 bg-surface-200 rounded animate-skeleton', className)}
    />
  )
}

export interface SkeletonBlockProps {
  height?: string
  className?: string
}

export function SkeletonBlock({ height = 'h-20', className }: SkeletonBlockProps) {
  return (
    <div
      className={cn('bg-surface-200 rounded animate-skeleton', height, className)}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-card border border-surface-200 dark:border-surface-200 p-4 flex flex-col gap-3">
      <SkeletonBlock height="h-40" />
      <SkeletonLine className="w-3/4" />
      <SkeletonLine className="w-1/2" />
    </div>
  )
}
