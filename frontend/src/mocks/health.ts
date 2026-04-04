import type { HealthOut } from '../types/api'

export const mockHealth: HealthOut = {
  status: 'healthy',
  services: [
    { name: 'llm', healthy: true },
    { name: 'postgres', healthy: true },
  ],
}
