/**
 * Subject: src/hooks/use-task.ts — useTask
 * Scope:   task status polling, onComplete callback, terminal state handling, error handling
 * Out of scope:
 *   - TaskStore persistence → task-store tests (not yet implemented)
 *   - Real API calls (client is mocked)
 * Setup:   fake timers; client.getTaskStatus is vi.fn()
 */

import { renderHook, act } from '@testing-library/react'
import { vi } from 'vitest'
import { useTask } from './use-task'
import { client } from '../services'

vi.mock('../services', () => ({
  client: {
    getTaskStatus: vi.fn(),
  },
}))

describe('useTask', () => {
  let unmountHook: (() => void) | undefined

  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(client.getTaskStatus).mockReset()
  })

  afterEach(() => {
    unmountHook?.()
    unmountHook = undefined
    vi.useRealTimers()
  })

  // When a taskId is present the hook must signal loading immediately,
  // before the first poll response arrives.
  it('returns loading initially when a taskId is provided', async () => {
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 't1',
      status: 'pending',
      progress: '0%',
    })

    const { result, unmount } = renderHook(() => useTask('t1'))
    unmountHook = unmount

    expect(result.current.loading).toBe(true)
    expect(result.current.task).toBeNull()
  })

  // The hook should surface each status transition as the backend progresses.
  it('updates task when status changes from pending to running to completed', async () => {
    vi.mocked(client.getTaskStatus)
      .mockResolvedValueOnce({
        task_id: 't1',
        status: 'pending',
        progress: '0%',
      })
      .mockResolvedValueOnce({
        task_id: 't1',
        status: 'running',
        progress: '50%',
      })
      .mockResolvedValueOnce({
        task_id: 't1',
        status: 'completed',
        progress: '100%',
        result: { data: 'ok' },
      })

    const { result, unmount } = renderHook(() => useTask('t1'))
    unmountHook = unmount

    // Initial render — still loading, no task yet.
    expect(result.current.loading).toBe(true)
    expect(result.current.task).toBeNull()

    // First poll → pending.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })
    expect(result.current.task?.status).toBe('pending')
    expect(result.current.loading).toBe(true)

    // Second poll → running.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })
    expect(result.current.task?.status).toBe('running')
    expect(result.current.loading).toBe(true)

    // Third poll → completed.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })
    expect(result.current.task?.status).toBe('completed')
    expect(result.current.loading).toBe(false)
  })

  // Callers rely on onComplete to react when a background task finishes successfully.
  it('fires onComplete callback when task completes', async () => {
    const onComplete = vi.fn()
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 't1',
      status: 'completed',
      progress: '100%',
      result: { foo: 'bar' },
    })

    const { unmount } = renderHook(() => useTask('t1', onComplete))
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete).toHaveBeenCalledWith({ foo: 'bar' })
  })

  // Terminal failure should be surfaced so the UI can show an error message.
  it('handles error status (task failed)', async () => {
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 't1',
      status: 'failed',
      progress: '100%',
      error: 'something broke',
    })

    const { result, unmount } = renderHook(() => useTask('t1'))
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })

    expect(result.current.task?.status).toBe('failed')
    expect(result.current.loading).toBe(false)
  })

  // Once a task is done (success or failure) there is no reason to keep hitting the API.
  it('stops polling when task reaches terminal state (completed)', async () => {
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 't1',
      status: 'completed',
      progress: '100%',
    })

    const { unmount } = renderHook(() => useTask('t1'))
    unmountHook = unmount

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })
    expect(client.getTaskStatus).toHaveBeenCalledTimes(1)

    // Advance well past the next interval tick — no additional calls.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(client.getTaskStatus).toHaveBeenCalledTimes(1)
  })

  // Providing a null taskId is the canonical way to pause/clear tracking.
  it('does not poll when taskId is null', async () => {
    const { result, unmount } = renderHook(() => useTask(null))
    unmountHook = unmount

    expect(result.current.loading).toBe(false)
    expect(result.current.task).toBeNull()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })

    expect(client.getTaskStatus).not.toHaveBeenCalled()
  })
})
