import { useEffect } from 'react'
import { useAppStore } from '@/stores/appStore'
import { api } from '@/api/client'

export function useHealth() {
  const setServiceHealth = useAppStore((state) => state.setServiceHealth)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await api.health()
        setServiceHealth(response.data)
      } catch (error) {
        console.error('Health check failed:', error)
        setServiceHealth({
          status: 'error',
          services: [],
        })
      }
    }

    // Check immediately and then every 30 seconds
    checkHealth()
    const interval = setInterval(checkHealth, 30000)

    return () => clearInterval(interval)
  }, [setServiceHealth])
}
