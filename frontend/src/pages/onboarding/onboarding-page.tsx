import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, ChevronRight, Loader2, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/auth/auth-context'
import { client } from '@/services'
import { useModels } from '@/hooks/use-models'
import { ModelSelect } from '@/components/ui/model-select'
import { ProviderSelect } from '@/components/ui/provider-select'
import type { CredentialStatus } from '@/types/api'

const PROVIDERS = ['groq', 'openrouter', 'nvidia', 'gemini', 'huggingface'] as const
type Provider = (typeof PROVIDERS)[number]

const PROVIDER_LABELS: Record<Provider, string> = {
  groq: 'Groq',
  openrouter: 'OpenRouter',
  nvidia: 'NVIDIA',
  gemini: 'Google Gemini',
  huggingface: 'HuggingFace',
}

const PROVIDER_KEY_HELP: Record<Provider, string> = {
  groq: 'Get your free API key at console.groq.com',
  openrouter: 'Get your API key at openrouter.ai/keys',
  nvidia: 'Get your API key at build.nvidia.com',
  gemini: 'Get your API key at aistudio.google.com',
  huggingface: 'Get your API key at huggingface.co/settings/tokens',
}

type Step = 'credential' | 'agent'

function StepIndicator({ current }: { current: Step }) {
  const steps: { id: Step; label: string }[] = [
    { id: 'credential', label: 'Add API Key' },
    { id: 'agent', label: 'Create Agent' },
  ]
  const currentIdx = steps.findIndex((s) => s.id === current)

  return (
    <div className="flex items-center gap-3 mb-8">
      {steps.map((step, idx) => {
        const done = idx < currentIdx
        const active = idx === currentIdx
        return (
          <React.Fragment key={step.id}>
            <div className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                  done
                    ? 'bg-success text-white'
                    : active
                    ? 'bg-primary text-white'
                    : 'bg-surface-200 text-text-tertiary'
                }`}
              >
                {done ? <CheckCircle className="w-4 h-4" /> : idx + 1}
              </div>
              <span
                className={`text-sm font-medium ${
                  active ? 'text-text-primary' : done ? 'text-success' : 'text-text-tertiary'
                }`}
              >
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <ChevronRight className="w-4 h-4 text-text-tertiary flex-shrink-0" />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

function CredentialStep({
  onComplete,
}: {
  onComplete: (provider: string, credential: CredentialStatus) => void
}) {
  const [provider, setProvider] = React.useState<Provider>('groq')
  const [apiKey, setApiKey] = React.useState('')
  const [showKey, setShowKey] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState('')

  const handleSave = async () => {
    if (!apiKey.trim()) {
      setError('API key is required')
      return
    }
    setSaving(true)
    setError('')
    try {
      const result = await client.saveCredential(provider, apiKey.trim())
      if (!result.last_test_ok) {
        setError(result.last_test_error || 'Connection test failed — check your key and try again')
        return
      }
      onComplete(provider, result)
    } catch (e) {
      setError((e as Error).message || 'Failed to save credential')
    } finally {
      setSaving(false)
    }
  }

  // Fake credentials list for ProviderSelect — all unconfigured at this stage
  const fakeCredentials: CredentialStatus[] = PROVIDERS.map((p) => ({
    provider: p,
    configured: false,
    last4: null,
    last_tested_at: null,
    last_test_ok: null,
    last_test_error: null,
  }))

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-xl font-semibold text-text-primary mb-1">Connect an AI Provider</h2>
        <p className="text-sm text-text-secondary">
          Choose an LLM provider and enter your API key. It will be encrypted and stored securely.
          The connection is tested automatically.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">Provider</label>
        <ProviderSelect
          value={provider}
          onChange={(v) => {
            setProvider(v as Provider)
            setApiKey('')
            setError('')
          }}
          credentials={fakeCredentials}
        />
        {PROVIDER_KEY_HELP[provider] && (
          <p className="mt-1.5 text-xs text-text-tertiary">{PROVIDER_KEY_HELP[provider]}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          API Key for {PROVIDER_LABELS[provider]}
        </label>
        <div className="relative">
          <input
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            placeholder="Paste your API key here"
            className="w-full px-3 py-2 pr-10 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono"
            autoFocus
          />
          <button
            type="button"
            onClick={() => setShowKey((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary transition-colors"
          >
            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-error bg-error-light px-3 py-2 rounded">{error}</div>
      )}

      <button
        onClick={handleSave}
        disabled={saving || !apiKey.trim()}
        className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-md text-sm font-medium text-text-inverse bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {saving ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Testing connection…
          </>
        ) : (
          'Save & Test Connection'
        )}
      </button>
    </div>
  )
}

function AgentStep({
  provider,
  onComplete,
}: {
  provider: string
  onComplete: () => void
}) {
  const { models, currentModel, loading: modelsLoading } = useModels(provider)
  const [name, setName] = React.useState('My First Agent')
  const [model, setModel] = React.useState('')
  const [prompt, setPrompt] = React.useState('')
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState('')

  React.useEffect(() => {
    if (models.length > 0 && !model) {
      setModel(models[0].id)
    }
  }, [models, model])

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    if (!model) {
      setError('Select a model')
      return
    }
    setSaving(true)
    setError('')
    try {
      await client.createAgent({
        name: name.trim(),
        provider,
        prompt: prompt.trim(),
        model,
        temperature: 0.7,
        top_p: 1.0,
        max_tokens: 1024,
      })
      onComplete()
    } catch (e) {
      setError((e as Error).message || 'Failed to create agent')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-xl font-semibold text-text-primary mb-1">Create Your First Agent</h2>
        <p className="text-sm text-text-secondary">
          An agent is an AI assistant that powers content generation — flashcards, questions, and
          more. You can fine-tune it later in Settings.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">Agent Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. My Study Assistant"
          className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">Model</label>
        {modelsLoading ? (
          <div className="flex items-center gap-2 text-sm text-text-tertiary py-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading models…
          </div>
        ) : (
          <ModelSelect value={model} onChange={setModel} models={models} fallback={currentModel} />
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          System Prompt{' '}
          <span className="font-normal text-text-tertiary">(optional)</span>
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. You are a concise academic tutor. Use formal language."
          rows={3}
          className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-vertical"
        />
      </div>

      {error && (
        <div className="text-sm text-error bg-error-light px-3 py-2 rounded">{error}</div>
      )}

      <button
        onClick={handleCreate}
        disabled={saving || !name.trim() || !model}
        className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-md text-sm font-medium text-text-inverse bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {saving ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Creating…
          </>
        ) : (
          'Create Agent & Continue'
        )}
      </button>
    </div>
  )
}

export function OnboardingPage() {
  const { refetchUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = React.useState<Step>('credential')
  const [selectedProvider, setSelectedProvider] = React.useState('')

  const handleCredentialDone = (provider: string) => {
    setSelectedProvider(provider)
    setStep('agent')
  }

  const handleAgentDone = async () => {
    await refetchUser()
    navigate('/', { replace: true })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-100 dark:bg-surface px-4">
      <div className="w-full max-w-md bg-surface dark:bg-surface-200 rounded-xl shadow-lg p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary">Welcome aboard</h1>
          <p className="text-sm text-text-secondary mt-1">
            Quick setup to start generating knowledge content with AI.
          </p>
        </div>

        <StepIndicator current={step} />

        {step === 'credential' && <CredentialStep onComplete={handleCredentialDone} />}
        {step === 'agent' && selectedProvider && (
          <AgentStep provider={selectedProvider} onComplete={handleAgentDone} />
        )}
      </div>
    </div>
  )
}
