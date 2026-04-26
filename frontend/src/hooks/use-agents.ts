import * as React from 'react'
import { client } from '../services'
import type { AgentOut } from '../types/api'

interface UseAgentsResult {
  agents: AgentOut[]
  loading: boolean
  refresh: () => void
}

export function useAgents(): UseAgentsResult {
  const [agents, setAgents] = React.useState<AgentOut[]>([])
  const [loading, setLoading] = React.useState(true)

  const refresh = React.useCallback(() => {
    setLoading(true)
    client.listAgents()
      .then(setAgents)
      .catch(() => { /* ignore */ })
      .finally(() => setLoading(false))
  }, [])

  React.useEffect(() => {
    refresh()
  }, [refresh])

  return { agents, loading, refresh }
}
