import * as React from 'react'
import { client } from '../services'
import type { ModelInfo } from '../types/api'

interface UseModelsResult {
  models: ModelInfo[]
  provider: string
  currentModel: string
  loading: boolean
}

export function useModels(): UseModelsResult {
  const [models, setModels] = React.useState<ModelInfo[]>([])
  const [provider, setProvider] = React.useState('')
  const [currentModel, setCurrentModel] = React.useState('')
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let cancelled = false
    client.getModels().then((data) => {
      if (cancelled) return
      setModels(data.models)
      setProvider(data.provider)
      setCurrentModel(data.current_model)
      setLoading(false)
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  return { models, provider, currentModel, loading }
}
