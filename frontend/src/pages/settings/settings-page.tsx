import * as React from 'react'
import { Link } from 'react-router-dom'
import { CreditCard, SlidersHorizontal, Cpu } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { useTheme } from '../../theme/theme-context'
import { cn } from '../../lib/cn'
import { useGenerationSettings } from '../../stores/generation-settings'
import { client } from '../../services'
import type { ModelsOut } from '../../types/api'

export function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { settings, update, clearModel } = useGenerationSettings()
  const [modelsData, setModelsData] = React.useState<ModelsOut | null>(null)

  React.useEffect(() => {
    client.getModels()
      .then(setModelsData)
      .catch(() => { /* ignore if backend unavailable */ })
  }, [])

  // Detect stored model that is no longer in the available list
  const storedModel = settings.model
  const availableIds = new Set(modelsData?.models.map((m) => m.id) ?? [])
  const modelStale = storedModel != null && !availableIds.has(storedModel)

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

        {/* Model Selection */}
        <Card
          title="Model Selection"
          actions={<Cpu className="h-4 w-4 text-gray-400 dark:text-slate-500" />}
        >
          {modelsData ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-slate-400">Provider:</span>
                <Badge variant="neutral">{modelsData.provider}</Badge>
              </div>
              <div>
                <label className="block text-sm text-gray-600 dark:text-slate-400 mb-1">
                  Active Model
                </label>
                <select
                  value={modelStale ? '' : (settings.model ?? modelsData.current_model)}
                  onChange={(e) => update({ model: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-md text-sm bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 appearance-none cursor-pointer"
                >
                  {modelsData.models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}{m.role ? ` (${m.role})` : ''}
                    </option>
                  ))}
                </select>
                {modelStale && (
                  <div className="mt-2 flex items-center gap-2">
                    <p className="text-xs text-amber-600 dark:text-amber-400">
                      Your saved model &quot;{storedModel}&quot; is no longer supported by {modelsData.provider}.
                    </p>
                    <button
                      onClick={clearModel}
                      className="text-xs text-primary underline hover:no-underline"
                    >
                      Reset to default
                    </button>
                  </div>
                )}
                {!modelStale && (
                  <p className="text-xs text-gray-400 dark:text-slate-500 mt-1.5 leading-relaxed">
                    Overrides the default model for chat, question generation, and flashcard drafting. Applies to all requests in this browser session.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-slate-500">
              Connect to the backend to see available models.
            </p>
          )}
        </Card>

        {/* Generation Settings */}
        <Card
          title="Generation Settings"
          actions={<SlidersHorizontal className="h-4 w-4 text-gray-400 dark:text-slate-500" />}
        >
          <div className="flex flex-col gap-5">
            <div>
              <label className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-slate-400">Temperature</span>
                <span className="font-mono text-gray-800 dark:text-slate-200">{settings.temperature.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={settings.temperature}
                onChange={(e) => update({ temperature: parseFloat(e.target.value) })}
                className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-xs text-gray-400 dark:text-slate-500 mt-1">
                <span>Deterministic</span>
                <span>Creative</span>
              </div>
              <p className="text-xs text-gray-400 dark:text-slate-500 mt-1.5 leading-relaxed">
                Controls randomness in the output. Lower values (e.g. 0.2) give focused, factual replies. Higher values (e.g. 1.5) produce more varied and creative responses.
              </p>
            </div>

            <div>
              <label className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-slate-400">Top P</span>
                <span className="font-mono text-gray-800 dark:text-slate-200">{settings.top_p.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.top_p}
                onChange={(e) => update({ top_p: parseFloat(e.target.value) })}
                className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-xs text-gray-400 dark:text-slate-500 mt-1">
                <span>Narrow</span>
                <span>Broad</span>
              </div>
              <p className="text-xs text-gray-400 dark:text-slate-500 mt-1.5 leading-relaxed">
                Nucleus sampling. Only tokens with cumulative probability above this threshold are considered. Lower values (e.g. 0.5) restrict choices to the most likely tokens; 1.0 considers all tokens.
              </p>
            </div>

            <div>
              <label className="block text-sm text-gray-600 dark:text-slate-400 mb-1">
                Max Output Tokens
              </label>
              <select
                value={settings.max_tokens}
                onChange={(e) => update({ max_tokens: parseInt(e.target.value, 10) })}
                className="w-full px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-md text-sm bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 appearance-none cursor-pointer"
              >
                <option value={256}>256 — short answer</option>
                <option value={512}>512 — concise</option>
                <option value={1024}>1024 — standard</option>
                <option value={2048}>2048 — detailed</option>
                <option value={4096}>4096 — long form</option>
                <option value={8192}>8192 — very long</option>
              </select>
              <p className="text-xs text-gray-400 dark:text-slate-500 mt-1.5 leading-relaxed">
                Caps the total tokens (words + punctuation) the model can generate per response. Longer outputs take more time and cost.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
