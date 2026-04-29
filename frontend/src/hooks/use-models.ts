import * as React from 'react'
import { client } from '../services'
import type { ModelInfo } from '../types/api'

const TIER_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 }

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

function sortModels(models: ModelInfo[]): ModelInfo[] {
  return [...models].sort((a, b) => {
    const tierDiff = (TIER_ORDER[a.quality_tier] ?? 1) - (TIER_ORDER[b.quality_tier] ?? 1)
    if (tierDiff !== 0) return tierDiff
    return a.label.localeCompare(b.label)
  })
}

function filterModels(models: ModelInfo[], recommendedFor?: string): ModelInfo[] {
  if (!recommendedFor) return models
  return models.filter((m) => m.recommended_for.includes(recommendedFor))
}

export function useModels(providerOrOptions?: string | UseModelsOptions): UseModelsResult {
  const providerFilter = typeof providerOrOptions === 'string'
    ? providerOrOptions
    : providerOrOptions?.provider
  const recommendedFor = typeof providerOrOptions === 'object'
    ? providerOrOptions.recommendedFor
    : undefined

  const [models, setModels] = React.useState<ModelInfo[]>([])
  const [provider, setProvider] = React.useState('')
  const [currentModel, setCurrentModel] = React.useState('')
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let cancelled = false
    client.getModels(providerFilter).then((data) => {
      if (cancelled) return
      const filtered = filterModels(data.models, recommendedFor)
      setModels(sortModels(filtered))
      setProvider(data.provider)
      setCurrentModel(data.current_model)
      setLoading(false)
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [providerFilter, recommendedFor])

  return { models, provider, currentModel, loading }
}
