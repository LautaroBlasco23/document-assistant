import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { HealthBanner } from './health-banner'
import { useAppStore } from '../../stores/app-store'
import { useHealth } from '../../hooks/use-health'
import { useLimits } from '../../hooks/use-limits'

export function MainLayout() {
  // Start background polling on mount
  useHealth()
  useLimits()

  const serviceHealth = useAppStore((state) => state.serviceHealth)

  return (
    <div className="flex h-screen bg-surface-100 dark:bg-bg font-ui">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <HealthBanner health={serviceHealth} />
        <main className="flex-1 overflow-y-auto p-page">
          <div className="space-y-section">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
