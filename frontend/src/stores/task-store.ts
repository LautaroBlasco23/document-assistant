import { create } from 'zustand'
import { client } from '../services'

const pollingIntervals = new Map<string, ReturnType<typeof setInterval>>()

export type GenerationTaskType = 'summary' | 'qa' | 'flashcards'

export interface GenerationTask {
  taskId: string
  type: GenerationTaskType
  docHash: string
  chapter: number
  bookTitle: string
  status: 'pending' | 'running' | 'completed' | 'failed'
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
    docHash: string
    chapter: number
    bookTitle: string
  }) => void
  clearTask: (taskId: string) => void
  rehydrateFromBackend: () => Promise<void>
}

const SESSION_KEY = 'docassist_active_tasks'

type PersistedTask = {
  taskId: string
  type: GenerationTaskType
  docHash: string
  chapter: number
  bookTitle: string
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
        if (status.status === 'completed' || status.status === 'failed') {
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
      useTaskStore.setState((state) => {
        const existing = state.tasks[taskId]
        if (!existing) return state
        return {
          tasks: {
            ...state.tasks,
            [taskId]: {
              ...existing,
              status: 'failed',
              error: is404 ? 'Task not found (server may have restarted)' : 'Lost connection to server',
            },
          },
        }
      })
    }
  }, 1500)

  pollingIntervals.set(taskId, interval)
}

function _addTask(taskId: string, type: GenerationTaskType, docHash: string, chapter: number, bookTitle: string) {
  useTaskStore.setState((state) => {
    if (state.tasks[taskId]) return state
    return {
      tasks: {
        ...state.tasks,
        [taskId]: {
          taskId,
          type,
          docHash,
          chapter,
          bookTitle,
          status: 'pending',
          progress: null,
          progressPct: null,
          result: null,
          error: null,
        },
      },
    }
  })
  persistToSession({ taskId, type, docHash, chapter, bookTitle })
  _startPolling(taskId)
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: {},

  submitTask: ({ taskId, type, docHash, chapter, bookTitle }) => {
    if (pollingIntervals.has(taskId)) return
    _addTask(taskId, type, docHash, chapter, bookTitle)
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
    try {
      const { tasks: activeTasks } = await client.listActiveTasks()
      for (const t of activeTasks) {
        if (t.task_type === 'summarize') {
          _addTask(t.task_id, 'summary', t.doc_hash, t.chapter, t.book_title)
        } else if (t.task_type === 'flashcards') {
          _addTask(t.task_id, 'flashcards', t.doc_hash, t.chapter, t.book_title)
        }
      }
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
      _addTask(entry.taskId, entry.type, entry.docHash, entry.chapter, entry.bookTitle)
    }
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
  }
}

_rehydrateFromSession()
