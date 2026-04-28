import { create } from 'zustand'
import { client } from '../services'

const pollingIntervals = new Map<string, ReturnType<typeof setInterval>>()

export type GenerationTaskType = 'kt_questions' | 'kt_flashcards' | 'kt_ingest' | 'kt_create_from_file'

export interface GenerationTask {
  taskId: string
  type: GenerationTaskType
  entityId: string
  chapter: number
  entityTitle: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'rate_limited'
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

function _startPolling(taskId: string) {
  if (pollingIntervals.has(taskId)) return

  const interval = setInterval(async () => {
    try {
      const status = await client.getTaskStatus(taskId)

      useTaskStore.setState((state) => {
        const existing = state.tasks[taskId]
        if (!existing) {
          clearInterval(interval)
          pollingIntervals.delete(taskId)
          return state
        }
        const updated: GenerationTask = {
          ...existing,
          status: status.status as GenerationTask['status'],
          progress: status.progress ?? null,
          progressPct: status.progress_pct ?? null,
          result: (status.result as Record<string, unknown> | null) ?? null,
          error: status.error ?? null,
        }
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'rate_limited') {
          clearInterval(interval)
          pollingIntervals.delete(taskId)
          removeFromSession(taskId)
        }
        return { tasks: { ...state.tasks, [taskId]: updated } }
      })
    } catch (err) {
      const is404 = err instanceof Error && err.message.includes('404')
      clearInterval(interval)
      pollingIntervals.delete(taskId)
      removeFromSession(taskId)
      if (is404) {
        useTaskStore.setState((state) => {
          const updated: Record<string, GenerationTask> = {}
          for (const key of Object.keys(state.tasks)) {
            if (key !== taskId) updated[key] = state.tasks[key]
          }
          return { tasks: updated }
        })
      } else {
        useTaskStore.setState((state) => {
          const existing = state.tasks[taskId]
          if (!existing) return state
          return {
            tasks: {
              ...state.tasks,
              [taskId]: { ...existing, status: 'failed', error: 'Lost connection to server' },
            },
          }
        })
      }
    }
  }, 1500)

  pollingIntervals.set(taskId, interval)
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
  _startPolling(taskId)
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: {},

  submitTask: ({ taskId, type, entityId, chapter, entityTitle }) => {
    if (pollingIntervals.has(taskId)) return
    _addTask(taskId, type, entityId, chapter, entityTitle)
  },

  clearTask: (taskId: string) => {
    const interval = pollingIntervals.get(taskId)
    if (interval !== undefined) {
      clearInterval(interval)
      pollingIntervals.delete(taskId)
    }
    removeFromSession(taskId)
    set((state) => {
      const updated: Record<string, GenerationTask> = {}
      for (const key of Object.keys(state.tasks)) {
        if (key !== taskId) updated[key] = state.tasks[key]
      }
      return { tasks: updated }
    })
  },

  rehydrateFromBackend: async () => {
    // Clear old legacy session storage key to avoid stale entries
    try {
      sessionStorage.removeItem('docassist_active_tasks')
    } catch {
      // ignore
    }
    try {
      await client.listActiveTasks()
      // KT tasks are transient; no rehydration needed from backend
    } catch {
      // ignore network errors during rehydration
    }
  },
}))

function _rehydrateFromSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return
    const entries = JSON.parse(raw) as PersistedTask[]
    for (const entry of entries) {
      _addTask(entry.taskId, entry.type, entry.entityId, entry.chapter, entry.entityTitle)
    }
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
  }
}

// Rehydrate from backend; fallback to sessionStorage if backend is unreachable.
useTaskStore.getState().rehydrateFromBackend().catch(() => {
  _rehydrateFromSession()
})
