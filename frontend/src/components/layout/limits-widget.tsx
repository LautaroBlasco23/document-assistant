import * as React from 'react'
import { NavLink } from 'react-router-dom'
import { Layers, FileText } from 'lucide-react'
import { useAppStore } from '../../stores/app-store'
import { Tooltip } from '../ui/tooltip'
import { cn } from '../../lib/cn'

interface LimitsWidgetProps {
  collapsed: boolean
}

export function LimitsWidget({ collapsed }: LimitsWidgetProps) {
  const limits = useAppStore((state) => state.limits)

  if (!limits) return null

  const treePercent = limits.max_knowledge_trees > 0
    ? Math.min((limits.current_knowledge_trees / limits.max_knowledge_trees) * 100, 100)
    : 0
  const docPercent = limits.max_documents > 0
    ? Math.min((limits.current_documents / limits.max_documents) * 100, 100)
    : 0
  const atRisk = treePercent >= 90 || docPercent >= 90

  if (collapsed) {
    return (
      <NavLink
        to="/settings/plan"
        aria-label="View plan & usage"
        className={({ isActive }) =>
          cn(
            'flex items-center justify-center px-2 py-3 border-t border-surface-200 dark:border-surface-200',
            'hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
            isActive && 'bg-primary-light dark:bg-primary/12',
          )
        }
      >
        <Tooltip content={`Trees ${limits.current_knowledge_trees}/${limits.max_knowledge_trees} · Documents ${limits.current_documents}/${limits.max_documents}`}>
          <span className="flex items-center gap-1.5" aria-hidden>
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                atRisk ? 'bg-error' : 'bg-primary',
              )}
            />
            <span className="text-[10px] font-medium text-text-secondary tabular-nums">
              {limits.current_knowledge_trees}/{limits.max_knowledge_trees}
            </span>
          </span>
        </Tooltip>
      </NavLink>
    )
  }

  return (
    <NavLink
      to="/settings/plan"
      className={({ isActive }) =>
        cn(
          'flex flex-col gap-2 px-4 py-3 border-t border-surface-200 dark:border-surface-200',
          'hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          isActive && 'bg-primary-light dark:bg-primary/12',
        )
      }
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-secondary">
          {limits.plan?.name ?? 'Plan'}
        </span>
        <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
          Usage
        </span>
      </div>

      <UsageBar
        icon={<Layers className="h-3 w-3" />}
        label="Trees"
        current={limits.current_knowledge_trees}
        max={limits.max_knowledge_trees}
        percent={treePercent}
      />
      <UsageBar
        icon={<FileText className="h-3 w-3" />}
        label="Documents"
        current={limits.current_documents}
        max={limits.max_documents}
        percent={docPercent}
      />
    </NavLink>
  )
}

interface UsageBarProps {
  icon: React.ReactNode
  label: string
  current: number
  max: number
  percent: number
}

function UsageBar({ icon, label, current, max, percent }: UsageBarProps) {
  const isAtRisk = percent >= 90
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="flex items-center gap-1 text-text-tertiary">
          {icon}
          {label}
        </span>
        <span className="text-text-secondary tabular-nums">
          {current} / {max}
        </span>
      </div>
      <div
        className="w-full bg-surface-200 dark:bg-surface-200 rounded-full h-1.5 overflow-hidden"
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} usage`}
      >
        <div
          className={cn(
            'h-1.5 rounded-full transition-all duration-300',
            isAtRisk ? 'bg-error' : 'bg-primary',
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
