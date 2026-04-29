import * as React from 'react'
import { Link } from 'react-router-dom'
import { CreditCard, Bot, Plus, Info } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Tooltip } from '../../components/ui/tooltip'
import { useTheme } from '../../theme/theme-context'
import { cn } from '../../lib/cn'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useAgents } from '../../hooks/use-agents'
import { useModels } from '../../hooks/use-models'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'
import { client } from '../../services'
import { AgentCreationDialog } from './agent-creation-dialog'
import { ModelSelect } from '../../components/ui/model-select'
import { ProviderSelect } from '../../components/ui/provider-select'
import { ApiKeysCard } from './api-keys-card'

const MAX_TOKENS_OPTIONS = [256, 512, 1024, 2048, 4096, 8192]

const FIELD_INFO: Record<string, string> = {
  prompt: 'A system-level instruction that defines the agent\'s personality, tone, and behavior. This is prepended to every request.',
  model: 'The underlying LLM model that powers this agent.',
  temperature: 'Controls randomness in output (0.0 to 2.0). Lower = focused, higher = creative.',
  top_p: 'Nucleus sampling threshold (0.0 to 1.0). Lower = more focused token selection.',
  max_tokens: 'Maximum number of tokens the model can output per response.',
}

function InfoIcon({ field }: { field: string }) {
  return (
    <Tooltip content={FIELD_INFO[field] ?? ''}>
      <span>
        <Info className="h-3.5 w-3.5 text-text-tertiary hover:text-blue-500 dark:hover:text-blue-400 cursor-help transition-colors" />
      </span>
    </Tooltip>
  )
}

export function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { settings, setAgent } = useGenerationSettings()
  const { agents, loading: agentsLoading, refresh: refreshAgents } = useAgents()
  const [selectedProviderForModels, setSelectedProviderForModels] = React.useState<string | undefined>(undefined)
  const { models, currentModel } = useModels(selectedProviderForModels)
  const { useCredentials } = useProviderCredentials()
  const { credentials } = useCredentials()
  const [createDialogOpen, setCreateDialogOpen] = React.useState(false)

  const defaultAgent = agents.find((a) => a.is_default)
  const selectedId = settings.agent_id ?? defaultAgent?.id ?? ''
  const selectedAgent = agents.find((a) => a.id === selectedId)

  const [draftName, setDraftName] = React.useState('')
  const [draftPrompt, setDraftPrompt] = React.useState('')
  const [draftProvider, setDraftProvider] = React.useState('')
  const [draftModel, setDraftModel] = React.useState('')
  const [draftTemperature, setDraftTemperature] = React.useState(0.7)
  const [draftTopP, setDraftTopP] = React.useState(1.0)
  const [draftMaxTokens, setDraftMaxTokens] = React.useState(1024)
  const [saving, setSaving] = React.useState(false)
  const [saveError, setSaveError] = React.useState('')

  React.useEffect(() => {
    if (selectedAgent) {
      setDraftName(selectedAgent.name)
      setDraftPrompt(selectedAgent.prompt || '')
      setDraftProvider(selectedAgent.provider)
      setDraftModel(selectedAgent.model)
      setDraftTemperature(selectedAgent.temperature)
      setDraftTopP(selectedAgent.top_p)
      setDraftMaxTokens(selectedAgent.max_tokens)
      setSelectedProviderForModels(selectedAgent.provider)
      setSaveError('')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgent?.id])

  const isDirty = selectedAgent != null && (
    draftName !== selectedAgent.name ||
    draftPrompt !== (selectedAgent.prompt || '') ||
    draftProvider !== selectedAgent.provider ||
    draftModel !== selectedAgent.model ||
    draftTemperature !== selectedAgent.temperature ||
    draftTopP !== selectedAgent.top_p ||
    draftMaxTokens !== selectedAgent.max_tokens
  )

  const handleSave = async () => {
    if (!selectedAgent) return
    setSaving(true)
    setSaveError('')
    try {
      await client.updateAgent(selectedAgent.id, {
        name: draftName.trim(),
        provider: draftProvider,
        prompt: draftPrompt.trim(),
        model: draftModel,
        temperature: draftTemperature,
        top_p: draftTopP,
        max_tokens: draftMaxTokens,
      })
      refreshAgents()
    } catch (e) {
      setSaveError((e as Error).message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-text-primary mb-6">Settings</h1>

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
                    ? 'bg-primary text-text-inverse border-primary'
                    : 'border-border text-text-secondary hover:bg-surface-100',
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
          className="flex items-center gap-4 p-4 bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-lg hover:border-primary/40 dark:hover:border-primary/40 hover:bg-primary-light dark:hover:bg-primary/12 transition-colors group"
        >
          <div className="h-10 w-10 rounded-full bg-primary-light dark:bg-primary/12 flex items-center justify-center shrink-0 group-hover:bg-primary/20 dark:group-hover:bg-primary/20 transition-colors">
            <CreditCard className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-text-primary">Plan & Limits</h3>
            <p className="text-sm text-text-tertiary">View your usage and plan limits</p>
          </div>
          <Badge variant="neutral">Free</Badge>
        </Link>

        {/* API Keys */}
        <ApiKeysCard />

        {/* Agents */}
        <Card
          title="Agents"
          actions={<Bot className="h-4 w-4 text-text-tertiary" />}
        >
          <div className="flex flex-col gap-4">
            {/* Default agent selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-text-secondary">Default Agent</label>
              <div className="flex items-center gap-2">
                <select
                  value={selectedId}
                  onChange={(e) => setAgent(e.target.value)}
                  disabled={agentsLoading}
                  className="flex-1 px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer disabled:opacity-50"
                >
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} — {a.model}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => setCreateDialogOpen(true)}
                  title="Create new agent"
                  className="p-2 rounded-md border border-surface-200 dark:border-surface-200 text-text-tertiary hover:bg-primary-light dark:hover:bg-primary/12 hover:text-primary hover:border-primary/40 dark:hover:border-primary/30 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Editable config for selected agent */}
            {selectedAgent && (
              <div className="border-t border-surface-200 dark:border-surface-200 pt-4 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-text-secondary">
                    Agent Config
                  </span>
                  {isDirty && (
                    <span className="text-xs text-warning font-medium">
                      Unsaved changes
                    </span>
                  )}
                </div>

                {/* Name */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-1 block">
                    Name
                  </label>
                  <input
                    type="text"
                    value={draftName}
                    onChange={(e) => setDraftName(e.target.value)}
                    placeholder="e.g. Creative Writer"
                    className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>

                {/* Prompt */}
                <div>
                  <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                    Prompt
                    <InfoIcon field="prompt" />
                  </label>
                  <textarea
                    value={draftPrompt}
                    onChange={(e) => setDraftPrompt(e.target.value)}
                    placeholder="e.g. You are a concise academic tutor..."
                    rows={3}
                    className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-vertical"
                  />
                </div>

                {/* Provider */}
                <div>
                  <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                    Provider
                  </label>
                  <ProviderSelect
                    value={draftProvider}
                    onChange={(v) => {
                      setDraftProvider(v)
                      setDraftModel('')
                      setSelectedProviderForModels(v)
                    }}
                    credentials={credentials}
                  />
                </div>

                {/* Model */}
                <div>
                  <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                    Model
                    <InfoIcon field="model" />
                  </label>
                  <ModelSelect
                    value={draftModel}
                    onChange={setDraftModel}
                    models={models}
                    fallback={draftModel}
                  />
                </div>

                {/* Temperature */}
                <div>
                  <label className="flex items-center justify-between text-sm font-medium text-text-secondary mb-1">
                    <span className="flex items-center gap-1.5">
                      Temperature
                      <InfoIcon field="temperature" />
                    </span>
                    <span className="font-mono text-gray-500">{draftTemperature.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={draftTemperature}
                    onChange={(e) => setDraftTemperature(parseFloat(e.target.value))}
                    className="w-full h-2 bg-surface-200 dark:bg-surface-200 rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <div className="flex justify-between text-xs text-text-tertiary mt-1">
                    <span>Deterministic</span>
                    <span>Creative</span>
                  </div>
                </div>

                {/* Top P */}
                <div>
                  <label className="flex items-center justify-between text-sm font-medium text-text-secondary mb-1">
                    <span className="flex items-center gap-1.5">
                      Top P
                      <InfoIcon field="top_p" />
                    </span>
                    <span className="font-mono text-gray-500">{draftTopP.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={draftTopP}
                    onChange={(e) => setDraftTopP(parseFloat(e.target.value))}
                    className="w-full h-2 bg-surface-200 dark:bg-surface-200 rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <div className="flex justify-between text-xs text-text-tertiary mt-1">
                    <span>Narrow</span>
                    <span>Broad</span>
                  </div>
                </div>

                {/* Max Tokens */}
                <div>
                  <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                    Max Output Tokens
                    <InfoIcon field="max_tokens" />
                  </label>
                  <select
                    value={draftMaxTokens}
                    onChange={(e) => setDraftMaxTokens(parseInt(e.target.value, 10))}
                    className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer"
                  >
                    {MAX_TOKENS_OPTIONS.map((n) => (
                      <option key={n} value={n}>
                        {n} — {n <= 512 ? 'concise' : n <= 1024 ? 'standard' : n <= 2048 ? 'detailed' : 'long form'}
                      </option>
                    ))}
                  </select>
                </div>

                {saveError && (
                  <div className="text-sm text-danger bg-danger-light px-3 py-2 rounded">
                    {saveError}
                  </div>
                )}

                {isDirty && (
                  <div className="flex justify-end">
                    <Button variant="primary" onClick={handleSave} disabled={saving}>
                      {saving ? 'Saving...' : 'Save changes'}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>

        <AgentCreationDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
          models={models}
          currentModel={currentModel}
          onCreated={(id) => { refreshAgents(); setAgent(id) }}
          credentials={credentials}
        />
      </div>
    </div>
  )
}
