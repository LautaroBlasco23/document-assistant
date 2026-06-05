import * as React from 'react'
import { Bot, XCircle, ChevronDown, ChevronUp, Clock, CheckCircle2, XCircle as XCircleIcon, AlertTriangle, Ban } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { client } from '../../services'
import type { TaskHistoryItem } from '../../types/api'

const STATUS_STYLES: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
  pending: { color: 'text-text-tertiary', bg: 'bg-surface-200 dark:bg-surface-300', icon: <Clock className="h-3.5 w-3.5" /> },
  running: { color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/30', icon: <Bot className="h-3.5 w-3.5 animate-pulse" /> },
  completed: { color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-900/30', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
  failed: { color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-900/30', icon: <XCircleIcon className="h-3.5 w-3.5" /> },
  rate_limited: { color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-900/30', icon: <AlertTriangle className="h-3.5 w-3.5" /> },
  cancelled: { color: 'text-text-tertiary', bg: 'bg-surface-200 dark:bg-surface-300', icon: <Ban className="h-3.5 w-3.5" /> },
}

const TASK_TYPE_LABELS: Record<string, string> = {
  kt_questions: 'Questions',
  kt_flashcards_bulk: 'Bulk Flashcards',
  kt_flashcard: 'Flashcard',
  kt_ingest: 'Ingest',
  kt_create_from_file: 'Import',
  kt_improve: 'Improve',
  kt_import_youtube: 'YouTube',
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

function ProgressBar({ pct, className = '' }: { pct: number; className?: string }) {
  return (
    <div className={`w-full h-2 rounded-full bg-surface-200 dark:bg-surface-300 overflow-hidden ${className}`}>
      <div
        className="h-full bg-primary rounded-full transition-all duration-300"
        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
      />
    </div>
  )
}

function TaskRow({
  task,
  expanded,
  onToggle,
  onCancel,
  cancelling,
}: {
  task: TaskHistoryItem
  expanded: boolean
  onToggle: () => void
  onCancel: () => void
  cancelling: boolean
}) {
  const style = STATUS_STYLES[task.status] ?? STATUS_STYLES.pending
  const isActive = task.status === 'pending' || task.status === 'running'
  const typeLabel = TASK_TYPE_LABELS[task.task_type] ?? task.task_type

  return (
    <div className="border border-surface-200 dark:border-surface-200 rounded-lg overflow-hidden">
      {/* Header row — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-50 dark:hover:bg-surface-100 transition-colors"
      >
        <span className={style.color}>{style.icon}</span>
        <span className="text-sm font-medium text-text-primary w-28 shrink-0">{typeLabel}</span>
        <span className="text-sm text-text-secondary flex-1 truncate">
          {task.prompt || task.book_title || `Chapter ${task.chapter}`}
        </span>
        {isActive && (
          <span className="text-xs text-text-tertiary tabular-nums">{task.progress_pct}%</span>
        )}
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.bg} ${style.color}`}>
          {task.status.replace('_', ' ')}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-text-tertiary shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-text-tertiary shrink-0" />
        )}
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-surface-100 dark:border-surface-200 pt-3 space-y-3">
          {/* Progress bar for active tasks */}
          {isActive && (
            <div className="space-y-1">
              <ProgressBar pct={task.progress_pct} />
              {task.progress && (
                <p className="text-xs text-text-tertiary">{task.progress}</p>
              )}
            </div>
          )}

          {/* Prompt */}
          {task.prompt && (
            <div>
              <p className="text-xs font-medium text-text-secondary mb-1">Prompt</p>
              <p className="text-sm text-text-primary bg-surface dark:bg-surface-200 rounded p-2 whitespace-pre-wrap">
                {task.prompt}
              </p>
            </div>
          )}

          {/* Result excerpt */}
          {task.result_excerpt && (
            <div>
              <p className="text-xs font-medium text-text-secondary mb-1">Result</p>
              <p className="text-sm text-text-primary bg-surface dark:bg-surface-200 rounded p-2 whitespace-pre-wrap">
                {task.result_excerpt}
              </p>
            </div>
          )}

          {/* Error */}
          {task.error && (
            <div>
              <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">Error</p>
              <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded p-2">
                {task.error}
              </p>
            </div>
          )}

          {/* Timestamps */}
          <div className="flex items-center gap-4 text-xs text-text-tertiary">
            <span>Submitted: {formatTime(task.created_at)}</span>
            {task.started_at && <span>Started: {formatTime(task.started_at)}</span>}
            {task.finished_at && <span>Finished: {formatTime(task.finished_at)}</span>}
          </div>

          {/* Cancel button for active tasks */}
          {isActive && (
            <div className="flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={(e) => { e.stopPropagation(); onCancel() }}
                disabled={cancelling}
              >
                <XCircle className="h-4 w-4 mr-1" />
                {cancelling ? 'Cancelling...' : 'Cancel'}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function AiCallsTab() {
  const [tasks, setTasks] = React.useState<TaskHistoryItem[]>([])
  const [total, setTotal] = React.useState(0)
  const [hasMore, setHasMore] = React.useState(false)
  const [loading, setLoading] = React.useState(true)
  const [loadingMore, setLoadingMore] = React.useState(false)
  const [statusFilter, setStatusFilter] = React.useState<string | null>(null)
  const [expandedId, setExpandedId] = React.useState<string | null>(null)
  const [cancellingId, setCancellingId] = React.useState<string | null>(null)

  // Use ref for offset to avoid recreating fetchTasks on every tasks change
  const offsetRef = React.useRef(0)

  const fetchTasks = React.useCallback(async (reset = true) => {
    if (reset) setLoading(true)
    else setLoadingMore(true)
    try {
      const offset = reset ? 0 : offsetRef.current
      const result = await client.listRecentTasks(50, offset, statusFilter ?? undefined)
      if (reset) {
        setTasks(result.tasks)
        offsetRef.current = result.tasks.length
      } else {
        setTasks((prev) => [...prev, ...result.tasks])
        offsetRef.current += result.tasks.length
      }
      setTotal(result.total)
      setHasMore(result.has_more)
    } catch {
      // ignore
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [statusFilter])

  React.useEffect(() => {
    offsetRef.current = 0
    fetchTasks(true)
  }, [statusFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh active tasks every 5s — only depends on active count, not full tasks array
  const hasActive = tasks.some((t) => t.status === 'pending' || t.status === 'running')
  React.useEffect(() => {
    if (!hasActive) return
    const interval = setInterval(() => { void fetchTasks(true) }, 5000)
    return () => clearInterval(interval)
  }, [hasActive, fetchTasks])

  const handleCancel = async (taskId: string) => {
    setCancellingId(taskId)
    try {
      await client.cancelTask(taskId)
      // Refetch to update status
      fetchTasks(true)
    } catch {
      // ignore
    } finally {
      setCancellingId(null)
    }
  }

  const filters = [
    { value: null, label: 'All' },
    { value: 'pending', label: 'Pending' },
    { value: 'running', label: 'Running' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
    { value: 'rate_limited', label: 'Rate Limited' },
    { value: 'cancelled', label: 'Cancelled' },
  ]

  return (
    <Card title="AI Calls" actions={<Bot className="h-4 w-4 text-text-tertiary" />}>
      <div className="space-y-4">
        {/* Filter chips */}
        <div className="flex flex-wrap gap-2">
          {filters.map((f) => (
            <button
              key={f.value ?? 'all'}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                statusFilter === f.value
                  ? 'bg-primary text-text-inverse border-primary'
                  : 'border-surface-200 dark:border-surface-200 text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-8 text-text-tertiary text-sm">
            Loading AI calls...
          </div>
        )}

        {/* Empty state */}
        {!loading && tasks.length === 0 && (
          <div className="text-center py-8">
            <Bot className="h-12 w-12 text-text-tertiary mx-auto mb-3 opacity-40" />
            <p className="text-sm text-text-secondary">
              No AI calls yet. Try improving a document or generating flashcards.
            </p>
          </div>
        )}

        {/* Task list */}
        {!loading && tasks.length > 0 && (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskRow
                key={task.task_id}
                task={task}
                expanded={expandedId === task.task_id}
                onToggle={() => setExpandedId(expandedId === task.task_id ? null : task.task_id)}
                onCancel={() => handleCancel(task.task_id)}
                cancelling={cancellingId === task.task_id}
              />
            ))}
          </div>
        )}

        {/* Load more */}
        {hasMore && !loading && (
          <div className="flex justify-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => fetchTasks(false)}
              disabled={loadingMore}
            >
              {loadingMore ? 'Loading...' : `Load more (${total - tasks.length} remaining)`}
            </Button>
          </div>
        )}

        {/* Task count */}
        {!loading && tasks.length > 0 && (
          <p className="text-xs text-text-tertiary text-center">
            Showing {tasks.length} of {total} tasks
          </p>
        )}
      </div>
    </Card>
  )
}
