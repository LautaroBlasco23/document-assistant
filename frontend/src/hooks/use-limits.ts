import { useEffect, useRef, useCallback } from 'react'
import { client } from '../services'
import { useAppStore, LIMITS_INVALIDATE_EVENT } from '../stores/app-store'
import { useAuth } from '../auth/auth-context'

const POLL_INTERVAL_MS = 30_000
const MAX_CONSECUTIVE_FAILURES = 3

/**
 * Polls the /users/me/limits endpoint and writes the result to useAppStore.
 * Refetches on the LIMITS_INVALIDATE_EVENT so mutation sites can opt in.
 * Resets to null on logout.
 */
export function useLimits(): void {
  const setLimits = useAppStore((state) => state.setLimits)
  const { user } = useAuth()
  const failureCount = useRef(0)

  const fetchLimits = useCallback(async () => {
    try {
      const limits = await client.getMyLimits()
      failureCount.current = 0
      setLimits(limits)
    } catch {
      failureCount.current += 1
      if (failureCount.current >= MAX_CONSECUTIVE_FAILURES) {
        setLimits(null)
      }
    }
  }, [setLimits])

  useEffect(() => {
    if (!user) {
      setLimits(null)
      return
    }

    void fetchLimits()
    const interval = setInterval(() => void fetchLimits(), POLL_INTERVAL_MS)

    const handleInvalidate = () => {
      failureCount.current = 0
      void fetchLimits()
    }
    window.addEventListener(LIMITS_INVALIDATE_EVENT, handleInvalidate)

    return () => {
      clearInterval(interval)
      window.removeEventListener(LIMITS_INVALIDATE_EVENT, handleInvalidate)
    }
  }, [user, fetchLimits, setLimits])
}
