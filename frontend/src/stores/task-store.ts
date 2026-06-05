import { create } from 'zustand'
import { client } from '../services'

export type GenerationTaskType =
  | 'kt_questions'
  | 'kt_flashcards'
  | 'kt_flashcards_bulk'
  | 'kt_ingest'
  | 'kt_create_from_file'
  | 'kt_improve'
  | 'kt_import_youtube'
  | 'kt_flashcard'

export interface GenerationTask {
  taskId: string
  type: GenerationTaskType
  entityId: string
  chapter: number
  entityTitle: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'rate_limited' | 'cancelled'
  progress: string | null
  progressPct: number | null
  result: Record<string, unknown> | null
  error: string | null
}

interface TaskState {
  tasks: Record<string, GenerationTask>
  submitTask: (params: {
    taskId: string
    type: GenerationTaskType
    entityId: string
    chapter: number
    entityTitle: string
  }) => void
  clearTask: (taskId: string) => void
  rehydrateFromBackend: () => Promise<void>
}

const SESSION_KEY = 'docassist_kt_tasks'

type PersistedTask = {
  taskId: string
  type: GenerationTaskType
  entityId: string
  chapter: number
  entityTitle: string
}

function persistToSession(entry: PersistedTask) {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    const entries: PersistedTask[] = raw ? (JSON.parse(raw) as PersistedTask[]) : []
    if (!entries.some((e) => e.taskId === entry.taskId)) {
      entries.push(entry)
    }
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(entries))
  } catch {
    // ignore storage errors
  }
}

function removeFromSession(taskId: string) {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return
    const entries = (JSON.parse(raw) as PersistedTask[]).filter((e) => e.taskId !== taskId)
    if (entries.length === 0) {
      sessionStorage.removeItem(SESSION_KEY)
    } else {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(entries))
    }
  } catch {
    // ignore storage errors
  }
}

// Shared single poller — replaces per-task intervals
let sharedPoller: ReturnType<typeof setInterval> | null = null

function _startSharedPoller() {
  if (sharedPoller) return
  sharedPoller = setInterval(async () => {
    const state = useTaskStore.getState()
    const pendingTaskIds = Object.keys(state.tasks).filter(
      (id) => state.tasks[id].status === 'pending' || state.tasks[id].status === 'running'
    )
    if (pendingTaskIds.length === 0) {
      // Nothing to poll — stop
      if (sharedPoller) {
        clearInterval(sharedPoller)
        sharedPoller = null
      }
      return
    }

    // Batch: poll each active task
    for (const taskId of pendingTaskIds) {
      try {
        const status = await client.getTaskStatus(taskId)
        useTaskStore.setState((s) => {
          const existing = s.tasks[taskId]
          if (!existing) return s
          const updated: GenerationTask = {
            ...existing,
            status: status.status as GenerationTask['status'],
            progress: status.progress ?? null,
            progressPct: status.progress_pct ?? null,
            result: (status.result as Record<string, unknown> | null) ?? null,
            error: status.error ?? null,
          }
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'rate_limited' || status.status === 'cancelled') {
            removeFromSession(taskId)
          }
          return { tasks: { ...s.tasks, [taskId]: updated } }
        })
      } catch (err) {
        const is404 = err instanceof Error && err.message.includes('404')
        if (is404) {
          useTaskStore.setState((s) => {
            const updated: Record<string, GenerationTask> = {}
            for (const key of Object.keys(s.tasks)) {
              if (key !== taskId) updated[key] = s.tasks[key]
            }
            return { tasks: updated }
          })
          removeFromSession(taskId)
        } else {
          useTaskStore.setState((s) => {
            const existing = s.tasks[taskId]
            if (!existing) return s
            return {
              tasks: {
                ...s.tasks,
                [taskId]: { ...existing, status: 'failed', error: 'Lost connection to server' },
              },
            }
          })
          removeFromSession(taskId)
        }
      }
    }
  }, 1500)
}

function _addTask(taskId: string, type: GenerationTaskType, entityId: string, chapter: number, entityTitle: string) {
  useTaskStore.setState((state) => {
    if (state.tasks[taskId]) return state
    return {
      tasks: {
        ...state.tasks,
        [taskId]: {
          taskId,
          type,
          entityId,
          chapter,
          entityTitle,
          status: 'pending',
          progress: null,
          progressPct: null,
          result: null,
          error: null,
        },
      },
    }
  })
  persistToSession({ taskId, type, entityId, chapter, entityTitle })
  _startSharedPoller()
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: {},

  submitTask: ({ taskId, type, entityId, chapter, entityTitle }) => {
    if (useTaskStore.getState().tasks[taskId]) return
    _addTask(taskId, type, entityId, chapter, entityTitle)
  },

  clearTask: (taskId: string) => {
    removeFromSession(taskId)
    set((state) => {
      const updated: Record<string, GenerationTask> = {}
      for (const key of Object.keys(state.tasks)) {
        if (key !== taskId) updated[key] = state.tasks[key]
      }
      return { tasks: updated }
    })
    // Stop shared poller if no active tasks remain
    const remaining = Object.values(useTaskStore.getState().tasks)
    if (!remaining.some((t) => t.status === 'pending' || t.status === 'running')) {
      if (sharedPoller) {
        clearInterval(sharedPoller)
        sharedPoller = null
      }
    }
  },

  rehydrateFromBackend: async () => {
    try {
      sessionStorage.removeItem('docassist_active_tasks')
    } catch {
      // ignore
    }
    try {
      const active = await client.listActiveTasks()
      // Rehydrate any active tasks from the backend
      for (const row of active.tasks) {
        const state = useTaskStore.getState()
        if (!state.tasks[row.task_id]) {
          _addTask(
            row.task_id,
            row.task_type as GenerationTaskType,
            row.doc_hash || row.filename || '',
            row.chapter,
            row.book_title || row.filename,
          )
        }
      }
    } catch {
      // ignore network errors during rehydration
    }
  },
}))

// Rehydration is handled by App.tsx useEffect — no module-level side effects here.

// Testing utility: reset shared poller state between tests
export function _resetTaskStoreForTesting() {
  if (sharedPoller) {
    clearInterval(sharedPoller)
    sharedPoller = null
  }
  useTaskStore.setState({ tasks: {} })
  sessionStorage.removeItem(SESSION_KEY)
}
