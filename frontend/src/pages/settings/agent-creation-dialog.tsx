import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { Info } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Tooltip } from '../../components/ui/tooltip'
import { client } from '../../services'
import type { ModelInfo, AgentOut, CredentialStatus } from '../../types/api'
import { ModelSelect } from '../../components/ui/model-select'
import { ProviderSelect } from '../../components/ui/provider-select'
import { useModels } from '../../hooks/use-models'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'

interface AgentCreationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  models: ModelInfo[]
  currentModel: string
  onCreated: (agentId: string) => void
  onUpdated?: () => void
  editAgent?: AgentOut | null
  onClose?: () => void
  credentials?: CredentialStatus[]
}

const MAX_TOKENS_OPTIONS = [256, 512, 1024, 2048, 4096, 8192]

const FIELD_INFO: Record<string, string> = {
  name: 'Give your agent a memorable name that describes its role or personality (e.g. "Factual Summarizer", "Creative Storyteller").',
  prompt: 'A system-level instruction that defines the agent\'s personality, tone, and behavior. This is prepended to every request. For example: "You are a concise academic tutor. Use formal language and cite sources when possible."',
  model: 'The underlying LLM model that powers this agent. Different models have different capabilities, speeds, and costs. The "main" model is the default for quality; "fast" models prioritize speed.',
  temperature: 'Controls randomness in output (0.0 to 2.0). Lower values (e.g. 0.2) produce focused, deterministic replies. Higher values (e.g. 1.5) give more creative and varied responses. 0.7 is a balanced default.',
  top_p: 'Nucleus sampling threshold (0.0 to 1.0). Only tokens with cumulative probability above this value are considered. Lower values (e.g. 0.5) restrict to the most likely tokens. 1.0 considers all tokens.',
  max_tokens: 'Maximum number of tokens (words + punctuation) the model can output per response. Lower = faster/cheaper but may truncate. Higher = more complete answers but slower.',
}

function InfoIcon({ field, className = '' }: { field: string; className?: string }) {
  return (
    <Tooltip content={FIELD_INFO[field] ?? ''}>
      <span className={className}>
        <Info className="h-3.5 w-3.5 text-text-tertiary hover:text-primary cursor-help transition-colors" />
      </span>
    </Tooltip>
  )
}

export function AgentCreationDialog({
  open,
  onOpenChange,
  models: externalModels,
  currentModel: externalCurrentModel,
  onCreated,
  onUpdated,
  editAgent,
  onClose,
  credentials,
}: AgentCreationDialogProps) {
  const isEdit = !!editAgent
  const [provider, setProvider] = React.useState('')
  const { models: providerModels } = useModels(provider || undefined)
  const { useCredentials } = useProviderCredentials()
  const { credentials: internalCredentials } = useCredentials()
  const resolvedCredentials = credentials ?? internalCredentials

  const models = provider ? providerModels : externalModels
  const currentModel = provider ? '' : externalCurrentModel

  const [name, setName] = React.useState('')
  const [prompt, setPrompt] = React.useState('')
  const [model, setModel] = React.useState(externalCurrentModel)
  const [temperature, setTemperature] = React.useState(0.7)
  const [topP, setTopP] = React.useState(1.0)
  const [maxTokens, setMaxTokens] = React.useState(1024)
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState('')

  React.useEffect(() => {
    if (open) {
      if (editAgent) {
        setName(editAgent.name)
        setPrompt(editAgent.prompt || '')
        setProvider(editAgent.provider || '')
        setModel(editAgent.model)
        setTemperature(editAgent.temperature)
        setTopP(editAgent.top_p)
        setMaxTokens(editAgent.max_tokens)
      } else {
        setName('')
        setPrompt('')
        const firstConfigured = resolvedCredentials.find((c) => c.last_test_ok)?.provider ?? ''
        setProvider(firstConfigured)
        setModel('')
        setTemperature(0.7)
        setTopP(1.0)
        setMaxTokens(1024)
      }
      setError('')
    }
  }, [open, editAgent, resolvedCredentials])

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    if (!provider) {
      setError('Provider is required')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      if (isEdit && editAgent) {
        await client.updateAgent(editAgent.id, {
          name: name.trim(),
          provider,
          prompt: prompt.trim(),
          model,
          temperature,
          top_p: topP,
          max_tokens: maxTokens,
        })
        onUpdated?.()
      } else {
        const agent = await client.createAgent({
          name: name.trim(),
          provider,
          prompt: prompt.trim(),
          model,
          temperature,
          top_p: topP,
          max_tokens: maxTokens,
        })
        onCreated(agent.id)
      }
      onOpenChange(false)
      onClose?.()
    } catch (e) {
      setError((e as Error).message || 'Failed to save agent')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="bg-black/50 fixed inset-0 z-40 animate-fade-in" />
        <RadixDialog.Content
          className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-surface dark:bg-surface-200 rounded-lg shadow-lg p-6 animate-fade-in max-h-[90vh] overflow-y-auto"
        >
          <RadixDialog.Title className="text-lg font-semibold text-text-primary mb-2">
            {isEdit ? 'Edit Agent' : 'Create New Agent'}
          </RadixDialog.Title>
          <RadixDialog.Description className="text-sm text-text-secondary mb-6">
            {isEdit
              ? 'Update this agent\'s model and generation settings.'
              : 'Define a new agent with its own model and generation settings.'}
          </RadixDialog.Description>

          <div className="flex flex-col gap-4">
            {error && (
              <div className="text-sm text-danger bg-danger-light px-3 py-2 rounded">
                {error}
              </div>
            )}

            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                Provider
              </label>
              <ProviderSelect
                value={provider}
                onChange={(v) => {
                  setProvider(v)
                  setModel('')
                }}
                credentials={resolvedCredentials}
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                Agent Name
                <InfoIcon field="name" />
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Creative Writer"
                className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                autoFocus
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                Main Prompt
                <InfoIcon field="prompt" />
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. You are a concise academic tutor..."
                rows={3}
                className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-vertical"
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                Model
                <InfoIcon field="model" />
              </label>
              <ModelSelect
                value={model}
                onChange={setModel}
                models={models}
                fallback={currentModel}
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 justify-between text-sm font-medium text-text-secondary mb-1">
                <span className="flex items-center gap-1.5">
                  Temperature
                  <InfoIcon field="temperature" />
                </span>
                <span className="font-mono text-gray-500">{temperature.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full h-2 bg-surface-200 dark:bg-surface-200 rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-xs text-text-tertiary mt-1">
                <span>Deterministic</span>
                <span>Creative</span>
              </div>
            </div>

            <div>
              <label className="flex items-center gap-1.5 justify-between text-sm font-medium text-text-secondary mb-1">
                <span className="flex items-center gap-1.5">
                  Top P
                  <InfoIcon field="top_p" />
                </span>
                <span className="font-mono text-gray-500">{topP.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={topP}
                onChange={(e) => setTopP(parseFloat(e.target.value))}
                className="w-full h-2 bg-surface-200 dark:bg-surface-200 rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-xs text-text-tertiary mt-1">
                <span>Narrow</span>
                <span>Broad</span>
              </div>
            </div>

            <div>
              <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
                Max Output Tokens
                <InfoIcon field="max_tokens" />
              </label>
              <select
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer"
              >
                {MAX_TOKENS_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n} — {n <= 512 ? 'concise' : n <= 1024 ? 'standard' : n <= 2048 ? 'detailed' : 'long form'}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting || !name.trim() || !provider}>
              {submitting ? 'Saving...' : isEdit ? 'Save' : 'Create'}
            </Button>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
