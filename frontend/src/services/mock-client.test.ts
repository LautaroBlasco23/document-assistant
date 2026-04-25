/**
 * Subject: src/services/mock-client.ts — MockClient
 * Scope:   CRUD consistency for knowledge trees, simulated network delays,
 *          and reasonable defaults for all ServiceClient methods.
 * Out of scope:
 *   - Real HTTP calls            → real-client.ts (not tested here)
 *   - React component behavior   → component tests
 * Setup:   Fake timers freeze setTimeout delays; Math.random is stubbed for deterministic IDs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MockClient } from './mock-client'
import { mockHealth } from '../mocks/health'
import { mockKnowledgeTrees } from '../mocks/knowledge-trees'

describe('MockClient', () => {
  let client: MockClient

  beforeEach(() => {
    vi.useFakeTimers()
    client = new MockClient()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // Returns the mock health payload after the simulated network delay.
  it('returns mock health data after a simulated delay', async () => {
    const promise = client.health()
    await vi.advanceTimersByTimeAsync(100)
    const result = await promise
    expect(result).toEqual(mockHealth)
  })

  // Lists the seeded knowledge trees after the standard delay.
  it('returns the initial mock knowledge trees', async () => {
    const promise = client.listKnowledgeTrees()
    await vi.advanceTimersByTimeAsync(150)
    const result = await promise
    expect(result).toEqual(mockKnowledgeTrees)
  })

  // Creating a tree assigns a generated id, stores the tree, and returns it.
  it('creates a knowledge tree with a generated id and returns it', async () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.5)

    const promise = client.createKnowledgeTree('New Tree', 'A description')
    await vi.advanceTimersByTimeAsync(200)
    const result = await promise

    expect(result).toMatchObject({
      id: expect.stringMatching(/^tree-[a-z0-9]+$/),
      title: 'New Tree',
      description: 'A description',
      num_chapters: 0,
    })
    expect(result.created_at).toBeDefined()
  })

  // CRUD consistency: after create, the tree appears in the list.
  it('creates a tree so that listing includes the new tree', async () => {
    const createPromise = client.createKnowledgeTree('Test Tree')
    await vi.advanceTimersByTimeAsync(200)
    const created = await createPromise

    const listPromise = client.listKnowledgeTrees()
    await vi.advanceTimersByTimeAsync(150)
    const trees = await listPromise

    expect(trees.some((t) => t.id === created.id)).toBe(true)
  })

  // Updating a tree mutates the title and description fields.
  it('updates an existing knowledge tree title and description', async () => {
    const updatePromise = client.updateKnowledgeTree('tree-ml', 'Updated Title', 'Updated Desc')
    await vi.advanceTimersByTimeAsync(150)
    const updated = await updatePromise
    expect(updated.title).toBe('Updated Title')
    expect(updated.description).toBe('Updated Desc')
  })

  // Deleting a tree removes it from the list but leaves other trees intact.
  it('deletes a knowledge tree so it no longer appears in listings', async () => {
    const deletePromise = client.deleteKnowledgeTree('tree-ml')
    await vi.advanceTimersByTimeAsync(150)
    await deletePromise

    const listPromise = client.listKnowledgeTrees()
    await vi.advanceTimersByTimeAsync(150)
    const trees = await listPromise

    expect(trees.find((t) => t.id === 'tree-ml')).toBeUndefined()
    expect(trees.length).toBe(mockKnowledgeTrees.length - 1)
  })

  // Deleting one tree leaves other trees intact.
  it('deleting one tree leaves other trees intact', async () => {
    const deletePromise = client.deleteKnowledgeTree('tree-ml')
    await vi.advanceTimersByTimeAsync(150)
    await deletePromise

    const listPromise = client.listKnowledgeTrees()
    await vi.advanceTimersByTimeAsync(150)
    const trees = await listPromise

    expect(trees.find((t) => t.id === 'tree-clean-arch')).toBeDefined()
  })

  // Auxiliary ServiceClient methods return sensible defaults without throwing.
  it('returns reasonable defaults for auxiliary methods without throwing', async () => {
    // getConfig
    const configPromise = client.getConfig()
    await vi.advanceTimersByTimeAsync(150)
    const config = await configPromise
    expect(config).toBeDefined()
    expect(config.ollama).toBeDefined()

    // listActiveTasks
    const tasksPromise = client.listActiveTasks()
    await vi.advanceTimersByTimeAsync(100)
    const tasks = await tasksPromise
    expect(tasks.tasks).toEqual([])

    // getDocumentFileUrl
    expect(client.getDocumentFileUrl('tree-1', 'doc-1')).toBe('#mock-file-doc-1')

    // getDocumentThumbnailUrl
    expect(client.getDocumentThumbnailUrl('tree-1', 'doc-1')).toBe('')

    // chat
    const chatPromise = client.chat({ messages: [] })
    await vi.advanceTimersByTimeAsync(500)
    const chat = await chatPromise
    expect(chat.reply).toContain('mock')
  })
})
