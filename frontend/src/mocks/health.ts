import type { HealthOut } from '../types/api'

export const mockHealth: HealthOut = {
  status: 'healthy',
  services: [
    { name: 'ollama', healthy: true },
    { name: 'qdrant', healthy: true },
    { name: 'neo4j', healthy: true },
  ],
}
