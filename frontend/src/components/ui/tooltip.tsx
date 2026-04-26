import * as React from 'react'
import * as RadixTooltip from '@radix-ui/react-tooltip'
import { cn } from '../../lib/cn'

export interface TooltipProps {
  content: string
  children: React.ReactNode
  className?: string
}

export function Tooltip({ content, children, className }: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={300}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>
          <span>{children}</span>
        </RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            className={cn(
              'bg-surface-200 dark:bg-surface-200 text-gray-800 dark:text-slate-200 text-xs px-2 py-1 rounded z-50',
              'animate-fade-in',
              className,
            )}
            sideOffset={4}
          >
            {content}
            <RadixTooltip.Arrow className="fill-surface-200 dark:fill-surface-200" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  )
}
