import { create } from 'zustand'
import { client } from '../services'

// Module-level map of active polling intervals (outside Zustand state)
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
  result: Record<string, unknown> | null
  error: string | null
}

interface TaskState {
  tasks: Record<string, GenerationTask>  // keyed by taskId
  submitTask: (params: {
    taskId: string
    type: GenerationTaskType
    docHash: string
    chapter: number
    bookTitle: string
  }) => void
  clearTask: (taskId: string) => void
}

// --- sessionStorage helpers ---

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

// --- Store ---

export const useTaskStore = create<TaskState>((set) => ({
  tasks: {},

  submitTask: ({ taskId, type, docHash, chapter, bookTitle }) => {
    // Guard against duplicate polling
    if (pollingIntervals.has(taskId)) return

    // Add task entry to state
    set((state) => ({
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
          result: null,
          error: null,
        },
      },
    }))

    // Persist to sessionStorage so we can recover after page refresh
    persistToSession({ taskId, type, docHash, chapter, bookTitle })

    const interval = setInterval(async () => {
      try {
        const status = await client.getTaskStatus(taskId)

        set((state) => {
          const existing = state.tasks[taskId]
          if (!existing) return state
          return {
            tasks: {
              ...state.tasks,
              [taskId]: {
                ...existing,
                status: status.status as GenerationTask['status'],
                progress: status.progress ?? null,
                result: (status.result as Record<string, unknown> | null) ?? null,
                error: status.error ?? null,
              },
            },
          }
        })

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval)
          pollingIntervals.delete(taskId)
          removeFromSession(taskId)
        }
      } catch (err) {
        // Detect 404 (stale task ID after server restart) vs generic network error
        const is404 =
          err instanceof Error && err.message.includes('404')
        clearInterval(interval)
        pollingIntervals.delete(taskId)
        removeFromSession(taskId)

        set((state) => {
          const existing = state.tasks[taskId]
          if (!existing) return state
          return {
            tasks: {
              ...state.tasks,
              [taskId]: {
                ...existing,
                status: 'failed',
                error: is404
                  ? 'Task not found (server may have restarted)'
                  : 'Lost connection to server',
              },
            },
          }
        })
      }
    }, 1500)

    pollingIntervals.set(taskId, interval)
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
        if (key !== taskId) {
          updated[key] = state.tasks[key]
        }
      }
      return { tasks: updated }
    })
  },
}))

// --- Rehydration on module load ---
// Resume polling for any tasks that were in progress when the page was refreshed.

function rehydrate() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return
    const entries = JSON.parse(raw) as PersistedTask[]
    for (const entry of entries) {
      useTaskStore.getState().submitTask(entry)
    }
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
  }
}

rehydrate()
