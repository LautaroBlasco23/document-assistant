import { useState, useEffect } from 'react'
import { api } from '@/api/client'

export interface TaskStatus {
  task_id: string
  status: string
  progress: string
  result?: Record<string, unknown>
  error?: string
}

export function useTask(taskId: string | null, onComplete?: (result: Record<string, unknown>) => void) {
  const [task, setTask] = useState<TaskStatus | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!taskId) return

    setLoading(true)
    const interval = setInterval(async () => {
      try {
        const response = await api.getTaskStatus(taskId)
        setTask(response.data)

        if (response.data.status === 'completed') {
          clearInterval(interval)
          setLoading(false)
          if (onComplete && response.data.result) {
            onComplete(response.data.result)
          }
        } else if (response.data.status === 'failed') {
          clearInterval(interval)
          setLoading(false)
        }
      } catch (error) {
        console.error('Failed to get task status:', error)
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [taskId, onComplete])

  return { task, loading }
}
