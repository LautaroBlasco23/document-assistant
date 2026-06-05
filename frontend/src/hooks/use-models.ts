import * as React from 'react'
import type { ModelInfo } from '../types/api'
import { useRefDataStore } from '../stores/reference-data-store'

interface UseModelsOptions {
  provider?: string
  recommendedFor?: string
}

interface UseModelsResult {
  models: ModelInfo[]
  provider: string
  currentModel: string
  loading: boolean
}

export function useModels(providerOrOptions?: string | UseModelsOptions): UseModelsResult {
  const providerFilter = typeof providerOrOptions === 'string'
    ? providerOrOptions
    : providerOrOptions?.provider
  const recommendedFor = typeof providerOrOptions === 'object'
    ? providerOrOptions.recommendedFor
    : undefined

  // Load from shared store (idempotent — only fetches once per filter)
  React.useEffect(() => {
    void useRefDataStore.getState().loadModels(providerFilter)
  }, [providerFilter])

  // Subscribe to store
  const models = useRefDataStore((s) => s.models)
  const provider = useRefDataStore((s) => s.modelsProvider)
  const currentModel = useRefDataStore((s) => s.modelsCurrentModel)
  const loading = useRefDataStore((s) => s.modelsLoading)

  // Client-side filter (no re-fetch)
  const filtered = React.useMemo(() => {
    if (!recommendedFor) return models
    return models.filter((m) => m.recommended_for.includes(recommendedFor))
  }, [models, recommendedFor])

  return { models: filtered, provider, currentModel, loading }
}
