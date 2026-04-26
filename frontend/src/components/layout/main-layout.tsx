import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { HealthBanner } from './health-banner'
import { useAppStore } from '../../stores/app-store'
import { useHealth } from '../../hooks/use-health'

export function MainLayout() {
  // Start health polling on mount
  useHealth()

  const serviceHealth = useAppStore((state) => state.serviceHealth)

  return (
    <div className="flex h-screen bg-surface-100 dark:bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <HealthBanner health={serviceHealth} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
