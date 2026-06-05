import * as React from 'react'
import { create } from 'zustand'
import type { ModelInfo, AgentOut, CredentialStatus, ProviderInfo } from '../types/api'
import { client } from '../services'

// ─── In-flight deduplication ────────────────────────────────────────────────
const inflight = new Map<string, Promise<unknown>>()

function dedup<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  const existing = inflight.get(key)
  if (existing) return existing as Promise<T>

  const promise = fetcher().finally(() => inflight.delete(key))
  inflight.set(key, promise)
  return promise
}

// ─── Store ──────────────────────────────────────────────────────────────────

interface ModelsSlice {
  models: ModelInfo[]
  modelsProvider: string
  modelsCurrentModel: string
  modelsLoadedFilter: string | undefined  // the filter used for the last load
  modelsLoading: boolean
}

interface AgentsSlice {
  agents: AgentOut[]
  agentsLoaded: boolean
  agentsLoading: boolean
}

interface CredentialsSlice {
  providers: ProviderInfo[]
  credentials: CredentialStatus[]
  credentialsLoaded: boolean
  credentialsLoading: boolean
}

interface ReferenceDataState extends ModelsSlice, AgentsSlice, CredentialsSlice {
  loadModels: (providerFilter?: string) => Promise<void>
  loadAgents: () => Promise<void>
  loadCredentials: () => Promise<void>
  /** Reset all cached data (call on logout). */
  reset: () => void
}

function sortModels(models: ModelInfo[]): ModelInfo[] {
  const order: Record<string, number> = { high: 0, medium: 1, low: 2 }
  return [...models].sort((a, b) => {
    const tierDiff = (order[a.quality_tier] ?? 1) - (order[b.quality_tier] ?? 1)
    if (tierDiff !== 0) return tierDiff
    return a.label.localeCompare(b.label)
  })
}

export const useRefDataStore = create<ReferenceDataState>((set, get) => ({
  // Models
  models: [],
  modelsProvider: '',
  modelsCurrentModel: '',
  modelsLoadedFilter: undefined,
  modelsLoading: false,

  // Agents
  agents: [],
  agentsLoaded: false,
  agentsLoading: false,

  // Credentials
  providers: [],
  credentials: [],
  credentialsLoaded: false,
  credentialsLoading: false,

  loadModels: async (providerFilter) => {
    // Re-fetch if filter changed or not yet loaded
    if (get().modelsLoadedFilter === providerFilter && get().models.length > 0) return
    if (get().modelsLoading) return
    set({ modelsLoading: true })
    try {
      const data = await dedup(`models:${providerFilter ?? ''}`, () => client.getModels(providerFilter))
      set({
        models: sortModels(data.models),
        modelsProvider: data.provider,
        modelsCurrentModel: data.current_model,
        modelsLoadedFilter: providerFilter,
      })
    } finally {
      set({ modelsLoading: false })
    }
  },

  loadAgents: async () => {
    if (get().agentsLoaded) return
    if (get().agentsLoading) return
    set({ agentsLoading: true })
    try {
      const agents = await dedup('agents', () => client.listAgents())
      set({ agents, agentsLoaded: true })
    } finally {
      set({ agentsLoading: false })
    }
  },

  loadCredentials: async () => {
    if (get().credentialsLoaded) return
    if (get().credentialsLoading) return
    set({ credentialsLoading: true })
    try {
      const [providers, credentials] = await Promise.all([
        dedup('providers', () => client.listProviders()),
        dedup('credentials', () => client.listCredentials()),
      ])
      set({ providers, credentials, credentialsLoaded: true })
    } finally {
      set({ credentialsLoading: false })
    }
  },

  reset: () => {
    inflight.clear()
    set({
      models: [],
      modelsProvider: '',
      modelsCurrentModel: '',
      modelsLoadedFilter: undefined,
      modelsLoading: false,
      agents: [],
      agentsLoaded: false,
      agentsLoading: false,
      providers: [],
      credentials: [],
      credentialsLoaded: false,
      credentialsLoading: false,
    })
  },
}))

/**
 * Convenience hook that triggers all three loads on mount.
 * Returns the combined cached state.
 */
export function useRefData() {
  const models = useRefDataStore((s) => s.models)
  const modelsProvider = useRefDataStore((s) => s.modelsProvider)
  const modelsCurrentModel = useRefDataStore((s) => s.modelsCurrentModel)
  const modelsLoading = useRefDataStore((s) => s.modelsLoading)

  const agents = useRefDataStore((s) => s.agents)
  const agentsLoading = useRefDataStore((s) => s.agentsLoading)

  const providers = useRefDataStore((s) => s.providers)
  const credentials = useRefDataStore((s) => s.credentials)
  const credentialsLoading = useRefDataStore((s) => s.credentialsLoading)

  React.useEffect(() => {
    void useRefDataStore.getState().loadModels()
    void useRefDataStore.getState().loadAgents()
    void useRefDataStore.getState().loadCredentials()
  }, [])

  return {
    models,
    modelsProvider,
    modelsCurrentModel,
    modelsLoading,
    agents,
    agentsLoading,
    providers,
    credentials,
    credentialsLoading,
  }
}
