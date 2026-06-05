import * as React from 'react'
import type { AgentOut } from '../types/api'
import { useRefDataStore } from '../stores/reference-data-store'

interface UseAgentsResult {
  agents: AgentOut[]
  loading: boolean
  refresh: () => void
}

/**
 * Reads agents from the shared store and triggers a one-time fetch on mount.
 * `refresh()` forces a re-fetch (e.g. after creating a new agent).
 */
export function useAgents(): UseAgentsResult {
  React.useEffect(() => {
    void useRefDataStore.getState().loadAgents()
  }, [])

  const agents = useRefDataStore((s) => s.agents)
  const loading = useRefDataStore((s) => s.agentsLoading)

  const refresh = React.useCallback(() => {
    // Reset loaded flag and re-fetch
    useRefDataStore.setState({ agentsLoaded: false })
    void useRefDataStore.getState().loadAgents()
  }, [])

  return { agents, loading, refresh }
}
