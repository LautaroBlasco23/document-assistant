/**
 * Subject: src/stores/task-store.ts — useTaskStore
 * Scope:   task submission, polling lifecycle, sessionStorage persistence,
 *          rehydration from backend
 * Out of scope:
 *   - Knowledge tree CRUD    → knowledge-tree-store.test.ts
 *   - App-level errors       → app-store.test.ts
 * Setup:   Fake timers; sessionStorage is cleared; Zustand store reset;
 *          @/services/index client is fully mocked.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import type { GenerationTaskType } from './task-store'

// Mock the service client before the store module is imported.
vi.mock('@/services/index', () => ({
  client: {
    listActiveTasks: vi.fn().mockResolvedValue({ tasks: [] }),
    getTaskStatus: vi.fn(),
  },
}))

import { client } from '@/services/index'
import { useTaskStore } from './task-store'

const mockClient = vi.mocked(client, true)

describe('useTaskStore', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    useTaskStore.setState({ tasks: {} })
    sessionStorage.clear()
    vi.clearAllMocks()
    mockClient.listActiveTasks.mockResolvedValue({ tasks: [] })
    mockClient.getTaskStatus.mockReset()
  })

  afterEach(async () => {
    // Clean up any lingering polling intervals.
    const state = useTaskStore.getState()
    for (const id of Object.keys(state.tasks)) {
      state.clearTask(id)
    }
    vi.useRealTimers()
  })

  // submitTask creates a pending task entry with all expected fields.
  it('submitTask creates entry with correct fields', () => {
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions' as GenerationTaskType,
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Test Entity',
    })
    const task = useTaskStore.getState().tasks['t1']
    expect(task).toBeDefined()
    expect(task.taskId).toBe('t1')
    expect(task.type).toBe('kt_questions')
    expect(task.entityId).toBe('e1')
    expect(task.chapter).toBe(1)
    expect(task.entityTitle).toBe('Test Entity')
    expect(task.status).toBe('pending')
    expect(task.progress).toBeNull()
    expect(task.progressPct).toBeNull()
    expect(task.result).toBeNull()
    expect(task.error).toBeNull()
  })

  // Calling submitTask twice with the same id is idempotent so duplicate
  // intervals are never created.
  it('submitTask is idempotent for duplicate task ids', () => {
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions' as GenerationTaskType,
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Test',
    })
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_ingest' as GenerationTaskType,
      entityId: 'e2',
      chapter: 2,
      entityTitle: 'Different',
    })
    const task = useTaskStore.getState().tasks['t1']
    expect(task.type).toBe('kt_questions')
  })

  // clearTask removes the task from state and cancels its polling interval.
  it('clearTask deletes by id and cleans up interval', () => {
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions' as GenerationTaskType,
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Test',
    })
    expect(useTaskStore.getState().tasks['t1']).toBeDefined()
    useTaskStore.getState().clearTask('t1')
    expect(useTaskStore.getState().tasks['t1']).toBeUndefined()
  })

  // clearTask also wipes the matching entry from sessionStorage.
  it('clearTask removes from sessionStorage', () => {
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_ingest' as GenerationTaskType,
      entityId: 'e1',
      chapter: 2,
      entityTitle: 'Test',
    })
    expect(sessionStorage.getItem('docassist_kt_tasks')).toBeTruthy()
    useTaskStore.getState().clearTask('t1')
    expect(sessionStorage.getItem('docassist_kt_tasks')).toBeNull()
  })

  // submitTask serialises the task metadata into sessionStorage so it survives reloads.
  it('persistToSession stores in sessionStorage', () => {
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_ingest' as GenerationTaskType,
      entityId: 'e1',
      chapter: 2,
      entityTitle: 'Test',
    })
    const raw = sessionStorage.getItem('docassist_kt_tasks')
    expect(raw).toBeTruthy()
    const entries = JSON.parse(raw!)
    expect(entries).toHaveLength(1)
    expect(entries[0].taskId).toBe('t1')
  })

  // rehydrateFromBackend wipes the legacy sessionStorage key used by older versions.
  it('rehydrateFromBackend clears legacy sessionStorage key', async () => {
    sessionStorage.setItem('docassist_active_tasks', 'legacy')
    await useTaskStore.getState().rehydrateFromBackend()
    expect(sessionStorage.getItem('docassist_active_tasks')).toBeNull()
  })

  // rehydrateFromBackend should swallow network errors rather than surface them.
  it('rehydrateFromBackend handles network errors gracefully', async () => {
    mockClient.listActiveTasks.mockRejectedValue(new Error('Network error'))
    await expect(
      useTaskStore.getState().rehydrateFromBackend(),
    ).resolves.toBeUndefined()
  })

  // When the backend reports a task as completed, the polling loop updates status,
  // progress, result and then tears down the interval.
  it('polling updates task status when completed', async () => {
    mockClient.getTaskStatus.mockResolvedValue({
      task_id: 't1',
      status: 'completed',
      progress: 'done',
      progress_pct: 100,
      result: { ok: true },
    })

    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions' as GenerationTaskType,
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Test',
    })

    await vi.advanceTimersByTimeAsync(1500)

    const task = useTaskStore.getState().tasks['t1']
    expect(task.status).toBe('completed')
    expect(task.progress).toBe('done')
    expect(task.progressPct).toBe(100)
    expect(task.result).toEqual({ ok: true })
  })

  // A 404 from getTaskStatus means the task no longer exists server-side;
  // the client should drop it from local state.
  it('polling removes task on 404', async () => {
    const err = new Error('404 Not Found')
    mockClient.getTaskStatus.mockRejectedValue(err)

    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions' as GenerationTaskType,
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Test',
    })

    await vi.advanceTimersByTimeAsync(1500)

    expect(useTaskStore.getState().tasks['t1']).toBeUndefined()
  })

  // Non-404 errors (e.g. network failure) mark the task as failed rather than deleting it.
  it('polling marks task failed on other errors', async () => {
    const err = new Error('Network error')
    mockClient.getTaskStatus.mockRejectedValue(err)

    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions' as GenerationTaskType,
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Test',
    })

    await vi.advanceTimersByTimeAsync(1500)

    const task = useTaskStore.getState().tasks['t1']
    expect(task.status).toBe('failed')
    expect(task.error).toBe('Lost connection to server')
  })

  // Consumers can filter the tasks Record by type using normal collection operations.
  it('filters tasks by type from state', () => {
    useTaskStore.getState().submitTask({
      taskId: 't1',
      type: 'kt_questions',
      entityId: 'e1',
      chapter: 1,
      entityTitle: 'Q',
    })
    useTaskStore.getState().submitTask({
      taskId: 't2',
      type: 'kt_ingest',
      entityId: 'e2',
      chapter: 2,
      entityTitle: 'I',
    })
    useTaskStore.getState().submitTask({
      taskId: 't3',
      type: 'kt_questions',
      entityId: 'e3',
      chapter: 3,
      entityTitle: 'Q2',
    })

    const questions = Object.values(useTaskStore.getState().tasks).filter(
      (t) => t.type === 'kt_questions',
    )
    expect(questions).toHaveLength(2)
    expect(questions.map((t) => t.taskId)).toEqual(['t1', 't3'])
  })
})
