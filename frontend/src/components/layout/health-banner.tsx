import * as React from 'react'
import { X } from 'lucide-react'
import type { HealthOut } from '../../types/api'

export interface HealthBannerProps {
  health: HealthOut | null
}

export function HealthBanner({ health }: HealthBannerProps) {
  const [dismissed, setDismissed] = React.useState(false)

  if (dismissed || health === null) {
    return null
  }

  const unhealthyServices = health.services.filter((s) => !s.healthy)

  if (unhealthyServices.length === 0) {
    return null
  }

  const names = unhealthyServices.map((s) => s.name).join(', ')

  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-amber-800 dark:text-amber-300 px-4 py-2 text-sm flex items-center justify-between">
      <span>
        Some services are unavailable: <strong>{names}</strong>
      </span>
      <button
        onClick={() => setDismissed(true)}
        className="ml-4 text-amber-600 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-200 transition-colors"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
