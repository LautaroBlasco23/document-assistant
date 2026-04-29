import * as React from 'react'
import { Plus, ChevronDown } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useAgents } from '../../hooks/use-agents'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useModels } from '../../hooks/use-models'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'
import { AgentCreationDialog } from './agent-creation-dialog'

interface AgentSelectorProps {
  compact?: boolean
}

export function AgentSelector({ compact = false }: AgentSelectorProps) {
  const { agents, loading, refresh } = useAgents()
  const { settings, setAgent } = useGenerationSettings()
  const { models, currentModel, loading: modelsLoading } = useModels()
  const { useCredentials } = useProviderCredentials()
  const { credentials } = useCredentials()
  const [dialogOpen, setDialogOpen] = React.useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === '__create__') {
      setDialogOpen(true)
      return
    }
    if (value) {
      setAgent(value)
    }
  }

  const handleCreated = (agentId: string) => {
    refresh()
    setAgent(agentId)
  }

  const defaultAgent = agents.find((a) => a.is_default)
  const selectedId = settings.agent_id ?? defaultAgent?.id ?? ''

  if (loading || modelsLoading) {
    return (
      <div className={cn(
        'flex items-center gap-1.5',
        compact ? 'px-2 py-1 border-b border-surface-200 dark:border-surface-200' : 'px-3 py-2'
      )}>
        <span className="text-[10px] uppercase tracking-wide text-text-tertiary shrink-0">
          Agent
        </span>
        <span className="text-xs text-text-tertiary">Loading...</span>
      </div>
    )
  }

  if (compact) {
    return (
      <>
        <div className="shrink-0 border-b border-surface-200 dark:border-surface-200 px-2 py-1 flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-text-tertiary shrink-0">Agent</span>
          <div className="relative flex-1 min-w-0">
            <select
              value={selectedId}
              onChange={handleChange}
              className="w-full text-xs px-1.5 py-0.5 rounded border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
              <option value="__create__" disabled className="text-text-tertiary">
                ──────────────
              </option>
              <option value="__create__">+ Create new agent</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-text-tertiary" />
          </div>
        </div>
        <AgentCreationDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          models={models}
          currentModel={currentModel}
          onCreated={handleCreated}
          credentials={credentials}
        />
      </>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <label className="block text-sm text-text-secondary">
            Default Agent
          </label>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedId}
            onChange={handleChange}
            className="flex-1 px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer"
          >
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} — {a.model}
              </option>
            ))}
          </select>
          <button
            onClick={() => setDialogOpen(true)}
            title="Create new agent"
            className="p-2 rounded-md border border-surface-200 dark:border-surface-200 text-text-tertiary hover:bg-primary-light dark:hover:bg-primary/12 hover:text-primary hover:border-primary/40 dark:hover:border-primary/30 transition-colors"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        {selectedId && (
          <p className="text-xs text-text-tertiary leading-relaxed">
            Agents bundle model selection with generation parameters (temperature, top-p, max tokens).
            Switch agents to change how content is generated.
          </p>
        )}
      </div>
      <AgentCreationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        models={models}
        currentModel={currentModel}
        onCreated={handleCreated}
        credentials={credentials}
      />
    </>
  )
}
