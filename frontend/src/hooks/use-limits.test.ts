/**
 * Subject: src/hooks/use-limits.ts — useLimits
 * Scope:   limits polling behavior, failure counting, event-driven refetch, logout reset
 * Out of scope:
 *   - AppStore sidebar or error behavior → app-store tests
 *   - Real API calls (client is mocked)
 * Setup:   fake timers; client.getMyLimits is vi.fn(); app-store state is reset before each test
 */

import { renderHook, act } from '@testing-library/react'
import { vi } from 'vitest'
import { useLimits } from './use-limits'
import { useAppStore, LIMITS_INVALIDATE_EVENT } from '../stores/app-store'
import { useAuth } from '../auth/auth-context'
import { client } from '../services'

vi.mock('../services', () => ({
  client: {
    getMyLimits: vi.fn(),
  },
}))

vi.mock('../auth/auth-context', async () => {
  const actual = await vi.importActual<typeof import('../auth/auth-context')>('../auth/auth-context')
  return {
    ...actual,
    useAuth: vi.fn(),
  }
})

const FREE_LIMITS = {
  max_documents: 200,
  max_knowledge_trees: 3,
  current_documents: 5,
  current_knowledge_trees: 1,
  can_create_document: true,
  can_create_tree: true,
  plan: { slug: 'free', name: 'Free', description: 'Get started' },
}

function setAuth(user: { id: string; email: string } | null) {
  vi.mocked(useAuth).mockReturnValue({
    user: user as never,
    token: user ? 'tok' : null,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refetchUser: vi.fn(),
  })
}

describe('useLimits', () => {
  let unmountHook: (() => void) | undefined

  beforeEach(() => {
    vi.useFakeTimers()
    useAppStore.setState({ limits: null })
    vi.mocked(client.getMyLimits).mockReset()
    setAuth({ id: 'u1', email: 'a@b.com' })
  })

  afterEach(() => {
    unmountHook?.()
    unmountHook = undefined
    vi.useRealTimers()
  })

  // On mount with a logged-in user, the hook should immediately fetch and write limits.
  it('fetches limits immediately on mount for a logged-in user', async () => {
    vi.mocked(client.getMyLimits).mockResolvedValue(FREE_LIMITS)

    const { unmount } = renderHook(() => useLimits())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })

    expect(useAppStore.getState().limits).toEqual(FREE_LIMITS)
    expect(client.getMyLimits).toHaveBeenCalledTimes(1)
  })

  // For an unauthenticated user, the hook should clear limits and not fetch.
  it('does not fetch and clears limits for an unauthenticated user', async () => {
    setAuth(null)

    const { unmount } = renderHook(() => useLimits())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })

    expect(useAppStore.getState().limits).toBeNull()
    expect(client.getMyLimits).toHaveBeenCalledTimes(0)
  })

  // The hook should keep polling every POLL_INTERVAL_MS so the quota stays fresh.
  it('polls at the configured interval', async () => {
    vi.mocked(client.getMyLimits).mockResolvedValue(FREE_LIMITS)

    const { unmount } = renderHook(() => useLimits())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(client.getMyLimits).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(client.getMyLimits).toHaveBeenCalledTimes(2)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(client.getMyLimits).toHaveBeenCalledTimes(3)
  })

  // The LIMITS_INVALIDATE_EVENT should trigger an immediate refetch (used by mutation sites).
  it('refetches when the limits:invalidate event fires', async () => {
    vi.mocked(client.getMyLimits).mockResolvedValue(FREE_LIMITS)

    const { unmount } = renderHook(() => useLimits())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(client.getMyLimits).toHaveBeenCalledTimes(1)

    await act(async () => {
      window.dispatchEvent(new Event(LIMITS_INVALIDATE_EVENT))
      await vi.advanceTimersByTimeAsync(0)
    })

    expect(client.getMyLimits).toHaveBeenCalledTimes(2)
  })

  // After 3 consecutive failures, the hook should clear the cached limits.
  it('clears limits after 3 consecutive failures', async () => {
    useAppStore.setState({ limits: FREE_LIMITS })
    vi.mocked(client.getMyLimits).mockRejectedValue(new Error('fail'))

    const { unmount } = renderHook(() => useLimits())
    unmountHook = unmount

    // First failure (mount fetch) — limits still cached.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(useAppStore.getState().limits).toEqual(FREE_LIMITS)
    expect(client.getMyLimits).toHaveBeenCalledTimes(1)

    // Second failure — still cached (threshold is 3).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().limits).toEqual(FREE_LIMITS)
    expect(client.getMyLimits).toHaveBeenCalledTimes(2)

    // Third failure → clear.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().limits).toBeNull()
    expect(client.getMyLimits).toHaveBeenCalledTimes(3)
  })

  // A single success after failures should restore the limits.
  it('restores limits after a success following failures', async () => {
    useAppStore.setState({ limits: FREE_LIMITS })
    vi.mocked(client.getMyLimits)
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValue(FREE_LIMITS)

    const { unmount } = renderHook(() => useLimits())
    unmountHook = unmount

    // First poll (mount) fails — limits are still cached.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(useAppStore.getState().limits).toEqual(FREE_LIMITS)
    expect(client.getMyLimits).toHaveBeenCalledTimes(1)

    // Second poll (after interval) succeeds — limits are restored.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().limits).toEqual(FREE_LIMITS)
    expect(client.getMyLimits).toHaveBeenCalledTimes(2)
  })
})
