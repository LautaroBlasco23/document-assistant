import { useEffect, useRef, useState } from 'react'
import { client } from '../services'
import type { TaskStatusOut } from '../types/api'

const POLL_INTERVAL_MS = 1500

export function useTask(
  taskId: string | null,
  onComplete?: (result: unknown) => void
): { task: TaskStatusOut | null; loading: boolean } {
  const [task, setTask] = useState<TaskStatusOut | null>(null)
  const [loading, setLoading] = useState(false)
  // Keep a stable ref to onComplete to avoid restarting the effect on every render
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  useEffect(() => {
    if (!taskId) {
      setTask(null)
      setLoading(false)
      return
    }

    setLoading(true)

    const interval = setInterval(async () => {
      try {
        const status = await client.getTaskStatus(taskId)
        setTask(status)

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'rate_limited') {
          clearInterval(interval)
          setLoading(false)

          if (status.status === 'completed' && onCompleteRef.current) {
            onCompleteRef.current(status.result ?? null)
          }
        }
      } catch {
        clearInterval(interval)
        setLoading(false)
      }
    }, POLL_INTERVAL_MS)

    return () => {
      clearInterval(interval)
      setLoading(false)
    }
  }, [taskId])

  return { task, loading }
}
