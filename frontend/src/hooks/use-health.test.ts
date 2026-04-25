/**
 * Subject: src/hooks/use-health.ts — useHealth
 * Scope:   health polling behavior, failure counting, degraded/recovery state transitions
 * Out of scope:
 *   - AppStore sidebar or error behavior → app-store tests (not yet implemented)
 *   - Real API calls (client is mocked)
 * Setup:   fake timers; client.health is vi.fn(); app-store state is reset before each test
 */

import { renderHook, act } from '@testing-library/react'
import { vi } from 'vitest'
import { useHealth } from './use-health'
import { useAppStore } from '../stores/app-store'
import { client } from '../services'

vi.mock('../services', () => ({
  client: {
    health: vi.fn(),
  },
}))

describe('useHealth', () => {
  let unmountHook: (() => void) | undefined

  beforeEach(() => {
    vi.useFakeTimers()
    useAppStore.setState({ serviceHealth: null })
    vi.mocked(client.health).mockReset()
  })

  afterEach(() => {
    unmountHook?.()
    unmountHook = undefined
    vi.useRealTimers()
  })

  // A successful health check should immediately surface the healthy status in the app store.
  it('sets serviceHealth to healthy on a successful response', async () => {
    vi.mocked(client.health).mockResolvedValue({ status: 'healthy', services: [] })

    const { unmount } = renderHook(() => useHealth())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })

    expect(useAppStore.getState().serviceHealth).toEqual({ status: 'healthy', services: [] })
    expect(client.health).toHaveBeenCalledTimes(1)
  })

  // The hook tolerates transient failures; only after three consecutive errors does it degrade.
  it('sets degraded after 3 consecutive failures', async () => {
    vi.mocked(client.health).mockRejectedValue(new Error('fail'))

    const { unmount } = renderHook(() => useHealth())
    unmountHook = unmount

    // First failure — still optimistic (null health).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(useAppStore.getState().serviceHealth).toBeNull()

    // Second failure — still not degraded.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().serviceHealth).toBeNull()

    // Third failure → degraded banner.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().serviceHealth).toEqual({ status: 'degraded', services: [] })
    expect(client.health).toHaveBeenCalledTimes(3)
  })

  // A single success resets the failure counter and restores healthy state.
  it('recovers to healthy after a success following failures', async () => {
    vi.mocked(client.health)
      .mockRejectedValueOnce(new Error('fail'))
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValue({ status: 'healthy', services: [] })

    const { unmount } = renderHook(() => useHealth())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(useAppStore.getState().serviceHealth).toBeNull()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().serviceHealth).toBeNull()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(useAppStore.getState().serviceHealth).toEqual({ status: 'healthy', services: [] })
  })

  // The hook should keep polling every POLL_INTERVAL_MS so the UI reflects current reality.
  it('polls at the configured interval', async () => {
    vi.mocked(client.health).mockResolvedValue({ status: 'healthy', services: [] })

    const { unmount } = renderHook(() => useHealth())
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(client.health).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(client.health).toHaveBeenCalledTimes(2)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(client.health).toHaveBeenCalledTimes(3)
  })
})
