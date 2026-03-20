import { useEffect, useRef } from 'react'
import { client } from '../services'
import { useAppStore } from '../stores/app-store'

const POLL_INTERVAL_MS = 30_000
const MAX_CONSECUTIVE_FAILURES = 3

export function useHealth(): void {
  const setServiceHealth = useAppStore((state) => state.setServiceHealth)
  const failureCount = useRef(0)

  useEffect(() => {
    async function fetchHealth() {
      try {
        const health = await client.health()
        failureCount.current = 0
        setServiceHealth(health)
      } catch {
        failureCount.current += 1
        if (failureCount.current >= MAX_CONSECUTIVE_FAILURES) {
          setServiceHealth({ status: 'degraded', services: [] })
        }
      }
    }

    // Fetch immediately on mount, then poll
    void fetchHealth()
    const interval = setInterval(() => void fetchHealth(), POLL_INTERVAL_MS)

    return () => clearInterval(interval)
  }, [setServiceHealth])
}
