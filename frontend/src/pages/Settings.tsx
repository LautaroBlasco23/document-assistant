import { useState, useEffect } from 'react'
import { api } from '@/api/client'

interface Config {
  ollama: {
    base_url: string
    generation_model: string
    embedding_model: string
    timeout: number
  }
  qdrant: {
    url: string
    collection_name: string
  }
  neo4j: {
    uri: string
    user: string
  }
  chunking: {
    max_tokens: number
    overlap_tokens: number
  }
}

export default function Settings() {
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await api.getConfig()
        setConfig(response.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    }

    loadConfig()
  }, [])

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Loading configuration...</p>
      </div>
    )
  }

  if (error || !config) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Failed to load configuration: {error}</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="space-y-6">
        {/* Ollama */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">🦙 Ollama</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Base URL</span>
              <span className="text-gray-900 font-mono">{config.ollama.base_url}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Generation Model</span>
              <span className="text-gray-900 font-mono">{config.ollama.generation_model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Embedding Model</span>
              <span className="text-gray-900 font-mono">{config.ollama.embedding_model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Timeout</span>
              <span className="text-gray-900 font-mono">{config.ollama.timeout}s</span>
            </div>
          </div>
        </div>

        {/* Qdrant */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">🔍 Qdrant</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">URL</span>
              <span className="text-gray-900 font-mono">{config.qdrant.url}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Collection</span>
              <span className="text-gray-900 font-mono">{config.qdrant.collection_name}</span>
            </div>
          </div>
        </div>

        {/* Neo4j */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📊 Neo4j</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">URI</span>
              <span className="text-gray-900 font-mono">{config.neo4j.uri}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">User</span>
              <span className="text-gray-900 font-mono">{config.neo4j.user}</span>
            </div>
          </div>
        </div>

        {/* Chunking */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">⚙️ Chunking</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Max Tokens</span>
              <span className="text-gray-900 font-mono">{config.chunking.max_tokens}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Overlap Tokens</span>
              <span className="text-gray-900 font-mono">{config.chunking.overlap_tokens}</span>
            </div>
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            ℹ️ Configuration is read-only. To modify settings, edit config/default.yml and restart the application.
          </p>
        </div>
      </div>
    </div>
  )
}
