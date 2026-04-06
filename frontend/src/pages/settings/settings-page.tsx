import * as React from 'react'
import { SkeletonLine } from '../../components/ui/skeleton'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { client } from '../../services'
import { useAppStore } from '../../stores/app-store'
import type { ConfigOut } from '../../types/api'

function ServiceBadge({ serviceName }: { serviceName: string }) {
  const serviceHealth = useAppStore((state) => state.serviceHealth)

  if (!serviceHealth) {
    return <Badge variant="neutral">Unknown</Badge>
  }

  const service = serviceHealth.services.find(
    (s) => s.name.toLowerCase() === serviceName.toLowerCase(),
  )

  if (!service) {
    return <Badge variant="neutral">Unknown</Badge>
  }

  return service.healthy ? (
    <Badge variant="success">Healthy</Badge>
  ) : (
    <Badge variant="danger">Unavailable</Badge>
  )
}

function ConfigEntry({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5 py-2 border-b border-gray-50 last:border-0">
      <dt className="text-xs text-gray-400">{label}</dt>
      <dd className="font-mono text-sm text-gray-800">{String(value)}</dd>
    </div>
  )
}

export function SettingsPage() {
  const [config, setConfig] = React.useState<ConfigOut | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    void (async () => {
      try {
        const data = await client.getConfig()
        setConfig(data)
      } catch {
        // fail silently — show placeholders
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg text-sm mb-6">
        Configuration is read-only. Edit{' '}
        <code className="font-mono text-xs bg-blue-100 px-1 py-0.5 rounded">
          config/default.yml
        </code>{' '}
        to change settings.
      </div>

      <div className="flex flex-col gap-4">
        {/* Ollama */}
        <Card
          title="Ollama"
          actions={<ServiceBadge serviceName="ollama" />}
        >
          {loading ? (
            <div className="flex flex-col gap-2">
              <SkeletonLine />
              <SkeletonLine className="w-3/4" />
              <SkeletonLine className="w-1/2" />
            </div>
          ) : config ? (
            <dl>
              <ConfigEntry label="Base URL" value={config.ollama.base_url} />
              <ConfigEntry label="Model" value={config.ollama.generation_model} />
              <ConfigEntry label="Timeout (s)" value={config.ollama.timeout} />
            </dl>
          ) : (
            <p className="text-sm text-gray-400">Unable to load configuration</p>
          )}
        </Card>

        {/* Chunking */}
        <Card title="Chunking">
          {loading ? (
            <div className="flex flex-col gap-2">
              <SkeletonLine />
              <SkeletonLine className="w-1/2" />
            </div>
          ) : config ? (
            <dl>
              <ConfigEntry label="Chunk Size (tokens)" value={config.chunking.max_tokens} />
              <ConfigEntry label="Chunk Overlap (tokens)" value={config.chunking.overlap_tokens} />
            </dl>
          ) : (
            <p className="text-sm text-gray-400">Unable to load configuration</p>
          )}
        </Card>
      </div>
    </div>
  )
}
