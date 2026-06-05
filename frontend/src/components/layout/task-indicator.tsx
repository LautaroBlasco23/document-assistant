import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, X } from 'lucide-react'
import { useTaskStore, type GenerationTask } from '../../stores/task-store'

const TASK_TYPE_LABELS: Record<string, string> = {
  kt_questions: 'Questions',
  kt_flashcards_bulk: 'Bulk Flashcards',
  kt_flashcard: 'Flashcard',
  kt_ingest: 'Ingest',
  kt_create_from_file: 'Import',
  kt_improve: 'Improve',
  kt_import_youtube: 'YouTube',
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="w-full h-1.5 rounded-full bg-surface-200 dark:bg-surface-300 overflow-hidden">
      <div
        className="h-full bg-primary rounded-full transition-all duration-300"
        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
      />
    </div>
  )
}

function activeTasksEqual(a: GenerationTask[], b: GenerationTask[]): boolean {
  if (a.length !== b.length) return false
  return a.every((t, i) =>
    t.taskId === b[i].taskId &&
    t.status === b[i].status &&
    t.progressPct === b[i].progressPct &&
    t.progress === b[i].progress
  )
}

export function TaskIndicator() {
  const activeTasks = useTaskStore(
    (s) =>
      Object.values(s.tasks).filter(
        (t) => t.status === 'pending' || t.status === 'running'
      ),
    activeTasksEqual
  )
  const navigate = useNavigate()
  const [expanded, setExpanded] = React.useState(false)

  if (activeTasks.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Collapsed badge */}
      {!expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-full shadow-lg hover:shadow-xl transition-all cursor-pointer group"
        >
          <Bot className="h-4 w-4 text-primary animate-pulse" />
          <span className="text-sm font-medium text-text-primary">
            {activeTasks.length} AI task{activeTasks.length !== 1 ? 's' : ''}
          </span>
          <span className="text-xs text-text-tertiary">running</span>
        </button>
      )}

      {/* Expanded panel */}
      {expanded && (
        <div className="w-80 bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-lg shadow-xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200 dark:border-surface-200">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-primary animate-pulse" />
              <span className="text-sm font-semibold text-text-primary">
                {activeTasks.length} Active Task{activeTasks.length !== 1 ? 's' : ''}
              </span>
            </div>
            <button
              onClick={() => setExpanded(false)}
              className="p-1 rounded hover:bg-surface-100 dark:hover:bg-surface-300 transition-colors"
            >
              <X className="h-4 w-4 text-text-tertiary" />
            </button>
          </div>

          {/* Task list */}
          <div className="max-h-64 overflow-y-auto">
            {activeTasks.map((task) => (
              <div
                key={task.taskId}
                className="px-4 py-3 border-b border-surface-100 dark:border-surface-200 last:border-0"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium text-text-secondary">
                    {TASK_TYPE_LABELS[task.type] ?? task.type}
                  </span>
                  <span className="text-xs text-text-tertiary tabular-nums">
                    {task.progressPct ?? 0}%
                  </span>
                </div>
                <ProgressBar pct={task.progressPct ?? 0} />
                {task.progress && (
                  <p className="text-xs text-text-tertiary mt-1 truncate">{task.progress}</p>
                )}
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-surface-200 dark:border-surface-200">
            <button
              onClick={() => { setExpanded(false); navigate('/settings') }}
              className="text-xs text-primary hover:text-primary/80 font-medium transition-colors"
            >
              View all AI calls
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
