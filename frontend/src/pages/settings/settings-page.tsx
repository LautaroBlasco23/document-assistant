import * as React from 'react'
import { Link } from 'react-router-dom'
import { CreditCard } from 'lucide-react'
import { SkeletonLine } from '../../components/ui/skeleton'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { client } from '../../services'
import { useAppStore } from '../../stores/app-store'
import { useTheme } from '../../theme/theme-context'
import { cn } from '../../lib/cn'
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
    <div className="flex flex-col gap-0.5 py-2 border-b border-gray-50 dark:border-slate-700 last:border-0">
      <dt className="text-xs text-gray-400 dark:text-slate-500">{label}</dt>
      <dd className="font-mono text-sm text-gray-800 dark:text-slate-200">{String(value)}</dd>
    </div>
  )
}

export function SettingsPage() {
  const { theme, setTheme } = useTheme()
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
      <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100 mb-6">Settings</h1>

      {/* Info banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300 px-4 py-3 rounded-lg text-sm mb-6">
        Configuration is read-only. Edit{' '}
        <code className="font-mono text-xs bg-blue-100 dark:bg-blue-900/40 px-1 py-0.5 rounded">
          config/default.yml
        </code>{' '}
        to change settings.
      </div>

      <div className="flex flex-col gap-4">
        {/* Appearance */}
        <Card title="Appearance">
          <div className="flex gap-2">
            {(['light', 'dark', 'system'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTheme(t)}
                className={cn(
                  'flex-1 py-2 px-3 rounded-md text-sm font-medium capitalize border transition-colors',
                  theme === t
                    ? 'bg-primary text-white border-primary'
                    : 'border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 hover:bg-surface-100',
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </Card>

        {/* Plan & Limits */}
        <Link
          to="/settings/plan"
          className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-lg hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50/30 dark:hover:bg-blue-900/20 transition-colors group"
        >
          <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center shrink-0 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/60 transition-colors">
            <CreditCard className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-slate-100">Plan & Limits</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400">View your usage and plan limits</p>
          </div>
          <Badge variant="neutral">Free</Badge>
        </Link>

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
            <p className="text-sm text-gray-400 dark:text-slate-500">Unable to load configuration</p>
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
            <p className="text-sm text-gray-400 dark:text-slate-500">Unable to load configuration</p>
          )}
        </Card>
      </div>
    </div>
  )
}
