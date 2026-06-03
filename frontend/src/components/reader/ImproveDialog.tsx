import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { ChevronDown, Loader2, Sparkles, Plus } from 'lucide-react'
import { Button } from '../ui/button'
import { cn } from '../../lib/cn'
import { useAgents } from '../../hooks/use-agents'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useModels } from '../../hooks/use-models'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'
import { AgentCreationDialog } from '../../pages/settings/agent-creation-dialog'

export interface ImproveDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: 'text' | 'formatting'
  /** When true, the user can toggle between "text" and "formatting" inside the dialog. */
  modeSelectable?: boolean
  onConfirm: (mode: 'text' | 'formatting', agentId: string) => void
  isImproving: boolean
}

export function ImproveDialog({
  open,
  onOpenChange,
  mode,
  modeSelectable = false,
  onConfirm,
  isImproving,
}: ImproveDialogProps) {
  const { agents, loading: agentsLoading, refresh: refreshAgents } = useAgents()
  const { settings, setAgent: persistAgent } = useGenerationSettings()
  const { models } = useModels()
  const { useCredentials } = useProviderCredentials()
  const { credentials } = useCredentials()

  const [selectedAgentId, setSelectedAgentId] = React.useState('')
  const [selectedMode, setSelectedMode] = React.useState(mode)
  const [agentDialogOpen, setAgentDialogOpen] = React.useState(false)

  // Sync selectedMode with prop when dialog opens
  React.useEffect(() => {
    if (!open) return
    setSelectedMode(mode)
    const defaultAgent = agents.find((a) => a.is_default)
    const initial =
      (settings.agent_id && agents.find((a) => a.id === settings.agent_id)?.id) ??
      defaultAgent?.id ??
      agents[0]?.id ??
      ''
    setSelectedAgentId(initial)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const selectedAgent = React.useMemo(
    () => agents.find((a) => a.id === selectedAgentId),
    [agents, selectedAgentId],
  )

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === '__create__') {
      setAgentDialogOpen(true)
      return
    }
    setSelectedAgentId(value)
  }

  const effectiveMode = modeSelectable ? selectedMode : mode

  const handleRun = () => {
    if (!selectedAgentId) return
    persistAgent(selectedAgentId)
    onConfirm(effectiveMode, selectedAgentId)
  }

  return (
    <>
      <RadixDialog.Root
        open={open}
        onOpenChange={(o) => {
          if (!isImproving) onOpenChange(o)
        }}
      >
        <RadixDialog.Portal>
          <RadixDialog.Overlay
            className="bg-black/50 fixed inset-0 z-40 animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          />
          <RadixDialog.Content
            onOpenAutoFocus={(e) => e.preventDefault()}
            onClick={(e) => e.stopPropagation()}
            className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-surface dark:bg-surface-200 rounded-lg shadow-lg p-6 animate-fade-in"
          >
            <RadixDialog.Title className="text-lg font-semibold text-text-primary mb-1">
              Improve document
            </RadixDialog.Title>
            <RadixDialog.Description className="text-sm text-text-secondary mb-5">
              Choose the agent that will{' '}
              {effectiveMode === 'formatting' ? 'reformat' : 'improve'} this text.
            </RadixDialog.Description>

            {/* Mode selector / badge */}
            <div className="mb-4">
              <span className="text-xs font-semibold uppercase tracking-wide text-text-tertiary block mb-1.5">
                Mode
              </span>
              {modeSelectable ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedMode('formatting')}
                    disabled={isImproving}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium border transition-colors flex-1',
                      effectiveMode === 'formatting'
                        ? 'bg-ai/10 text-ai border-ai/30'
                        : 'bg-surface dark:bg-surface-200 border-surface-200 dark:border-surface-200 text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100',
                    )}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Improve formatting
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedMode('text')}
                    disabled={isImproving}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium border transition-colors flex-1',
                      effectiveMode === 'text'
                        ? 'bg-primary-light dark:bg-primary/12 text-primary border-primary/30'
                        : 'bg-surface dark:bg-surface-200 border-surface-200 dark:border-surface-200 text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100',
                    )}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Improve text
                  </button>
                </div>
              ) : (
                <span
                  className={cn(
                    'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium',
                    mode === 'formatting'
                      ? 'bg-ai/10 text-ai'
                      : 'bg-primary-light dark:bg-primary/12 text-primary',
                  )}
                >
                  <Sparkles className="h-3 w-3" />
                  {mode === 'formatting' ? 'Improve formatting' : 'Improve text'}
                </span>
              )}
            </div>

            {/* Agent selector */}
            <div className="mb-5">
              <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1.5">
                Agent
              </label>
              {agentsLoading ? (
                <div className="flex items-center gap-2 text-sm text-text-tertiary py-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Loading agents…
                </div>
              ) : agents.length === 0 ? (
                <div className="rounded-md bg-surface-100 dark:bg-surface-100 px-3 py-3 text-sm text-text-secondary">
                  <p className="mb-2">No agents configured. Create one to continue.</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setAgentDialogOpen(true)}
                  >
                    <Plus className="h-3.5 w-3.5 mr-1" />
                    Create new agent
                  </Button>
                </div>
              ) : (
                <div className="relative">
                  <select
                    value={selectedAgentId}
                    onChange={handleSelectChange}
                    className="w-full px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                        {a.is_default ? ' (default)' : ''}
                        {' — '}
                        {a.provider} · {a.model}
                      </option>
                    ))}
                    <option disabled className="text-text-tertiary">
                      ──────────────
                    </option>
                    <option value="__create__">+ Create new agent</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
                </div>
              )}
            </div>

            {/* Info block */}
            <div className="mb-5 px-3 py-2 rounded-md bg-surface-100 dark:bg-surface-100 text-xs text-text-tertiary leading-relaxed">
              The selected agent's model, parameters, and system prompt will be used
              for this improvement.
              {selectedAgent && selectedAgent.prompt && (
                <div className="mt-1.5">
                  <span className="font-semibold">Agent prompt:</span>{' '}
                  <span className="italic">{selectedAgent.prompt}</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => onOpenChange(false)}
                disabled={isImproving}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleRun}
                disabled={!selectedAgentId || agents.length === 0 || isImproving}
                loading={isImproving}
              >
                Run
              </Button>
            </div>
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>

      {/* Sub-dialog for creating a new agent */}
      <AgentCreationDialog
        open={agentDialogOpen}
        onOpenChange={setAgentDialogOpen}
        models={models}
        currentModel={''}
        credentials={credentials}
        onCreated={(id) => {
          setSelectedAgentId(id)
          setAgentDialogOpen(false)
          refreshAgents()
        }}
      />
    </>
  )
}
