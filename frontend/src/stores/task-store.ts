import { create } from 'zustand'
import { client } from '../services'
import type { TaskStatusOut } from '../types/api'

// Module-level map of active polling intervals (outside Zustand state)
const pollingIntervals = new Map<string, ReturnType<typeof setInterval>>()

interface TaskState {
  tasks: Record<string, TaskStatusOut>
  startPolling: (taskId: string, onComplete?: (result: unknown) => void) => void
  stopPolling: (taskId: string) => void
  clearTask: (taskId: string) => void
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: {},

  startPolling: (taskId: string, onComplete?: (result: unknown) => void) => {
    // Avoid duplicate polling for the same task
    if (pollingIntervals.has(taskId)) return

    const interval = setInterval(async () => {
      try {
        const status = await client.getTaskStatus(taskId)
        set((state) => ({
          tasks: { ...state.tasks, [taskId]: status },
        }))

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval)
          pollingIntervals.delete(taskId)

          if (status.status === 'completed' && onComplete) {
            onComplete(status.result ?? null)
          }
        }
      } catch {
        // On error, stop polling to avoid infinite retries
        clearInterval(interval)
        pollingIntervals.delete(taskId)
      }
    }, 1500)

    pollingIntervals.set(taskId, interval)
  },

  stopPolling: (taskId: string) => {
    const interval = pollingIntervals.get(taskId)
    if (interval !== undefined) {
      clearInterval(interval)
      pollingIntervals.delete(taskId)
    }
  },

  clearTask: (taskId: string) => {
    const interval = pollingIntervals.get(taskId)
    if (interval !== undefined) {
      clearInterval(interval)
      pollingIntervals.delete(taskId)
    }
    set((state) => {
      const updated: Record<string, TaskStatusOut> = {}
      for (const key of Object.keys(state.tasks)) {
        if (key !== taskId) {
          updated[key] = state.tasks[key]
        }
      }
      return { tasks: updated }
    })
  },
}))
