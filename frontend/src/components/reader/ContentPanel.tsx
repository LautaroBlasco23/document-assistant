import * as React from 'react'
import { Check, X, Loader2, AlertCircle, Pencil, ChevronDown } from 'lucide-react'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import {
  usePendingContent,
  type PendingContent,
  type PendingFlashcard,
  type PendingQuestion,
} from '../../stores/pending-content-store'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useAgents } from '../../hooks/use-agents'
import { useModels } from '../../hooks/use-models'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'
import { AgentCreationDialog } from '../../pages/settings/agent-creation-dialog'

interface ContentPanelProps {
  treeId: string
  chapter: number | null
}

export function ContentPanel({ treeId, chapter }: ContentPanelProps) {
  const items = usePendingContent((s) => s.items)
  const { settings, setAgent } = useGenerationSettings()
  const { agents, loading: agentsLoading } = useAgents()
  const { models, currentModel, loading: modelsLoading } = useModels()
  const { useCredentials } = useProviderCredentials()
  const { credentials } = useCredentials()
  const [agentDialogOpen, setAgentDialogOpen] = React.useState(false)

  const defaultAgent = agents.find((a) => a.is_default)
  const selectedAgentId = settings.agent_id ?? defaultAgent?.id ?? ''

  const handleAgentChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === '__create__') {
      setAgentDialogOpen(true)
      return
    }
    if (value) setAgent(value)
  }

  return (
    <div className="h-full flex flex-col">
      {!agentsLoading && !modelsLoading && agents.length > 0 && (
        <div className="shrink-0 border-b border-surface-200 dark:border-surface-200 px-2 py-1 flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-text-tertiary shrink-0">Agent</span>
          <div className="relative flex-1 min-w-0">
            <select
              value={selectedAgentId}
              onChange={handleAgentChange}
              className="w-full text-xs px-1.5 py-0.5 rounded border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-text-primary appearance-none cursor-pointer"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}{a.is_default ? ' (default)' : ''}
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
      )}
      <AgentCreationDialog
        open={agentDialogOpen}
        onOpenChange={setAgentDialogOpen}
        models={models}
        currentModel={currentModel}
        onCreated={(id) => setAgent(id)}
        credentials={credentials}
      />

      {items.length === 0 ? (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="text-center text-xs text-text-tertiary mt-4">
            Right-click a selection in the document
            <br />
            and choose what to generate.
            <br />
            <span className="text-text-tertiary">
              Generated items appear here for your review.
            </span>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {items.map((item) =>
            item.kind === 'flashcard' ? (
              <FlashcardCard key={item.id} item={item} treeId={treeId} chapter={chapter} />
            ) : (
              <QuestionCard key={item.id} item={item} treeId={treeId} chapter={chapter} />
            ),
          )}
        </div>
      )}
    </div>
  )
}

function CardShell({
  label,
  status,
  error,
  disposition,
  onApprove,
  onReject,
  onDismiss,
  approveDisabled,
  children,
}: {
  label: string
  status: PendingContent['status']
  error?: string
  disposition?: PendingContent['disposition']
  onApprove: () => void
  onReject: () => void
  onDismiss?: () => void
  approveDisabled?: boolean
  children: React.ReactNode
}) {
  const resolved = !!disposition
  return (
    <div className={cn(
      'rounded-lg border bg-surface dark:bg-surface-200 shadow-sm overflow-hidden transition-colors',
      disposition === 'approved'
        ? 'border-success/30'
        : disposition === 'rejected'
          ? 'border-red-300 dark:border-danger'
          : 'border-surface-200 dark:border-surface-200',
    )}>
      <div className={cn(
        'flex items-center justify-between px-3 py-1.5 border-b bg-surface-100 dark:bg-surface-200/80',
        disposition === 'approved'
          ? 'border-success/30 '
          : disposition === 'rejected'
            ? 'border-danger/30 '
            : 'border-surface-200 dark:border-surface-200',
      )}>
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
          {status === 'generating' && <Loader2 className="h-3 w-3 animate-spin" />}
          {status === 'error' && <AlertCircle className="h-3 w-3 text-danger" />}
          <span>{label}</span>
          {disposition && (
            <span className={cn(
              'ml-1 px-1.5 py-0.5 rounded text-[10px] font-bold',
              disposition === 'approved'
                ? 'bg-success-light text-success'
                : 'bg-danger-light text-danger',
            )}>
              {disposition === 'approved' ? 'Approved' : 'Rejected'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {!resolved && (
            <>
              <button
                onClick={onReject}
                disabled={status === 'saving'}
                title="Reject"
                  className="p-1 rounded text-text-tertiary hover:text-danger hover:bg-danger-light dark:hover:bg-danger/12 transition-colors disabled:opacity-50"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={onApprove}
                  disabled={approveDisabled || status === 'saving' || status === 'generating'}
                  title="Approve"
                  className="p-1 rounded text-text-tertiary hover:text-success hover:bg-success-light dark:hover:bg-success/12 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
              >
                {status === 'saving' ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Check className="h-3.5 w-3.5" />
                )}
              </button>
            </>
          )}
          {resolved && onDismiss && (
            <button
              onClick={onDismiss}
              title="Dismiss"
              className="p-1 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
      <div className="px-3 py-2">
        {error && <div className="mb-2 text-xs text-red-500">{error}</div>}
        {children}
      </div>
    </div>
  )
}

function EditableField({
  label,
  value,
  onChange,
  rows = 2,
  readOnly = false,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  rows?: number
  readOnly?: boolean
}) {
  return (
    <label className="block mb-2 last:mb-0">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary flex items-center gap-1">
        <Pencil className="h-2.5 w-2.5" /> {label}
      </span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        readOnly={readOnly}
        className={cn(
          'mt-0.5 w-full resize-none rounded border bg-surface dark:bg-surface-200 px-2 py-1 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-primary',
          readOnly
            ? 'border-surface-200 dark:border-surface-200 cursor-default pointer-events-none'
            : 'border-surface-200 dark:border-surface-200',
        )}
      />
    </label>
  )
}

function FlashcardCard({
  item,
  treeId,
  chapter,
}: {
  item: PendingFlashcard
  treeId: string
  chapter: number | null
}) {
  const update = usePendingContent((s) => s.update)
  const remove = usePendingContent((s) => s.remove)
  const resolved = !!item.disposition

  const approve = async () => {
    const ch = chapter ?? item.chapter
    if (!ch) return
    update(item.id, { status: 'saving', error: undefined })
    try {
      await client.saveFlashcard(treeId, ch, {
        front: item.front,
        back: item.back,
        source_text: item.sourceText || null,
      })
      update(item.id, { status: 'ready', disposition: 'approved' })
    } catch (e) {
      update(item.id, { status: 'ready', error: (e as Error).message || 'Failed to save' })
    }
  }

  return (
    <CardShell
      label="Flashcard"
      status={item.status}
      error={item.error}
      disposition={item.disposition}
      onApprove={approve}
      onReject={() => update(item.id, { disposition: 'rejected' })}
      onDismiss={resolved ? () => remove(item.id) : undefined}
      approveDisabled={!item.front.trim() || !item.back.trim()}
    >
      <EditableField
        label="Front"
        value={item.front}
        onChange={(v) => update(item.id, { front: v })}
        readOnly={resolved}
      />
      <EditableField
        label="Back"
        value={item.back}
        onChange={(v) => update(item.id, { back: v })}
        rows={3}
        readOnly={resolved}
      />
    </CardShell>
  )
}

function QuestionCard({
  item,
  treeId,
  chapter,
}: {
  item: PendingQuestion
  treeId: string
  chapter: number | null
}) {
  const update = usePendingContent((s) => s.update)
  const remove = usePendingContent((s) => s.remove)
  const resolved = !!item.disposition

  const setData = (patch: Record<string, unknown>) =>
    update(item.id, { questionData: { ...item.questionData, ...patch } })

  const approve = async () => {
    const ch = chapter ?? item.chapter
    if (!ch) return
    update(item.id, { status: 'saving', error: undefined })
    try {
      await client.saveQuestion(treeId, ch, item.questionType, item.questionData)
      update(item.id, { status: 'ready', disposition: 'approved' })
    } catch (e) {
      update(item.id, {
        status: 'ready',
        error: (e as Error).message || 'Validation failed',
      })
    }
  }

  let body: React.ReactNode
  if (item.questionType === 'true_false') {
    const statement = String(item.questionData.statement ?? '')
    const answer = Boolean(item.questionData.answer)
    const explanation = String(item.questionData.explanation ?? '')
    body = (
      <>
        <EditableField
          label="Statement"
          value={statement}
          onChange={(v) => setData({ statement: v })}
          rows={3}
          readOnly={resolved}
        />
        <div className="mb-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
            Answer
          </span>
          <div className="mt-1 flex gap-1">
            {[true, false].map((val) => (
              <button
                key={String(val)}
                onClick={() => !resolved && setData({ answer: val })}
                disabled={resolved}
                className={cn(
                  'flex-1 px-2 py-1 text-xs rounded border transition-colors',
                  resolved && 'cursor-default',
                  answer === val
                    ? 'bg-primary text-text-inverse border-primary'
                    : 'border-surface-200 dark:border-surface-200 text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100',
                )}
              >
                {val ? 'True' : 'False'}
              </button>
            ))}
          </div>
        </div>
        <EditableField
          label="Explanation (optional)"
          value={explanation}
          onChange={(v) => setData({ explanation: v })}
          readOnly={resolved}
        />
      </>
    )
  } else if (item.questionType === 'multiple_choice') {
    const question = String(item.questionData.question ?? '')
    const choices = (item.questionData.choices as string[] | undefined) ?? ['', '', '', '']
    const correctIndex = Number(item.questionData.correct_index ?? 0)
    const explanation = String(item.questionData.explanation ?? '')
    const setChoice = (i: number, v: string) => {
      const next = [...choices]
      next[i] = v
      setData({ choices: next })
    }
    body = (
      <>
        <EditableField
          label="Question"
          value={question}
          onChange={(v) => setData({ question: v })}
          rows={2}
          readOnly={resolved}
        />
        <span className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
          Choices (click radio to mark correct)
        </span>
        <div className="space-y-1 mt-1 mb-2">
          {choices.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="radio"
                checked={correctIndex === i}
                onChange={() => !resolved && setData({ correct_index: i })}
                disabled={resolved}
                className="shrink-0"
              />
              <input
                type="text"
                value={c}
                onChange={(e) => setChoice(i, e.target.value)}
                readOnly={resolved}
                className={cn(
                  'flex-1 rounded border bg-surface dark:bg-surface-200 px-2 py-1 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary',
                  resolved
                    ? 'border-surface-200 dark:border-surface-200 cursor-default pointer-events-none'
                    : 'border-surface-200 dark:border-surface-200',
                )}
              />
            </div>
          ))}
        </div>
        <EditableField
          label="Explanation (optional)"
          value={explanation}
          onChange={(v) => setData({ explanation: v })}
          readOnly={resolved}
        />
      </>
    )
  } else if (item.questionType === 'checkbox') {
    const question = String(item.questionData.question ?? '')
    const choices = (item.questionData.choices as string[] | undefined) ?? ['', '', '', '']
    const correctIndices = (item.questionData.correct_indices as number[] | undefined) ?? []
    const explanation = String(item.questionData.explanation ?? '')
    const toggleCorrect = (i: number) => {
      const next = correctIndices.includes(i)
        ? correctIndices.filter((x) => x !== i)
        : [...correctIndices, i]
      setData({ correct_indices: next })
    }
    const setChoice = (i: number, v: string) => {
      const next = [...choices]
      next[i] = v
      setData({ choices: next })
    }
    body = (
      <>
        <EditableField
          label="Question"
          value={question}
          onChange={(v) => setData({ question: v })}
          rows={2}
          readOnly={resolved}
        />
        <span className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
          Choices (check all correct answers)
        </span>
        <div className="space-y-1 mt-1 mb-2">
          {choices.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={correctIndices.includes(i)}
                onChange={() => !resolved && toggleCorrect(i)}
                disabled={resolved}
                className="shrink-0"
              />
              <input
                type="text"
                value={c}
                onChange={(e) => setChoice(i, e.target.value)}
                readOnly={resolved}
                className={cn(
                  'flex-1 rounded border bg-surface dark:bg-surface-200 px-2 py-1 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary',
                  resolved
                    ? 'border-surface-200 dark:border-surface-200 cursor-default pointer-events-none'
                    : 'border-surface-200 dark:border-surface-200',
                )}
              />
            </div>
          ))}
        </div>
        <EditableField
          label="Explanation (optional)"
          value={explanation}
          onChange={(v) => setData({ explanation: v })}
          readOnly={resolved}
        />
      </>
    )
  } else {
    body = (
      <pre className="text-xs whitespace-pre-wrap break-words text-text-secondary">
        {JSON.stringify(item.questionData, null, 2)}
      </pre>
    )
  }

  const labelMap: Record<string, string> = {
    true_false: 'True / False',
    multiple_choice: 'Multiple Choice',
    matching: 'Matching',
    checkbox: 'Select All That Apply',
  }

  return (
    <CardShell
      label={labelMap[item.questionType] ?? 'Question'}
      status={item.status}
      error={item.error}
      disposition={item.disposition}
      onApprove={approve}
      onReject={() => update(item.id, { disposition: 'rejected' })}
      onDismiss={resolved ? () => remove(item.id) : undefined}
    >
      {body}
    </CardShell>
  )
}
