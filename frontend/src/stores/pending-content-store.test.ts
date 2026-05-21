/**
 * Subject: src/stores/pending-content-store.ts — usePendingContent, makePendingId
 * Scope:   add, update, remove, clearForDoc, makePendingId
 * Out of scope:
 *   - UI rendering of pending items → component tests
 * Setup:   Store state is reset before each test.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { usePendingContent, makePendingId } from './pending-content-store'

describe('usePendingContent', () => {
  beforeEach(() => {
    usePendingContent.setState({ items: [] })
  })

  it('add appends a pending item', () => {
    const item = {
      id: 'pc-1',
      kind: 'flashcard' as const,
      status: 'generating' as const,
      chapter: 1,
      front: 'What is X?',
      back: 'X is Y',
      sourceText: 'source',
    }

    usePendingContent.getState().add(item)

    const items = usePendingContent.getState().items
    expect(items).toHaveLength(1)
    expect(items[0]).toBe(item)
  })

  it('add supports question type items', () => {
    const item = {
      id: 'pc-2',
      kind: 'question' as const,
      status: 'generating' as const,
      chapter: 2,
      questionType: 'multiple_choice' as const,
      questionData: { question: 'Q?', options: ['A', 'B'], answer: 'A' },
      sourceText: 'source',
    }

    usePendingContent.getState().add(item)

    const items = usePendingContent.getState().items
    expect(items[0].kind).toBe('question')
    expect(items[0].questionType).toBe('multiple_choice')
  })

  it('update modifies an existing item by id', () => {
    const item = {
      id: 'pc-1',
      kind: 'flashcard' as const,
      status: 'generating' as const,
      chapter: 1,
      front: 'Q?',
      back: 'A',
      sourceText: 'source',
    }
    usePendingContent.getState().add(item)

    usePendingContent.getState().update('pc-1', { status: 'ready' })

    const items = usePendingContent.getState().items
    expect(items[0].status).toBe('ready')
  })

  it('update does not affect other items', () => {
    usePendingContent.getState().add({
      id: 'pc-1', kind: 'flashcard' as const, status: 'generating' as const,
      chapter: 1, front: 'Q1', back: 'A1', sourceText: 's1',
    })
    usePendingContent.getState().add({
      id: 'pc-2', kind: 'flashcard' as const, status: 'generating' as const,
      chapter: 1, front: 'Q2', back: 'A2', sourceText: 's2',
    })

    usePendingContent.getState().update('pc-1', { status: 'ready' })

    const items = usePendingContent.getState().items
    expect(items[0].status).toBe('ready')
    expect(items[1].status).toBe('generating')
  })

  it('update with error status stores error message', () => {
    usePendingContent.getState().add({
      id: 'pc-1', kind: 'flashcard' as const, status: 'generating' as const,
      chapter: 1, front: 'Q', back: 'A', sourceText: 's',
    })

    usePendingContent.getState().update('pc-1', { status: 'error', error: 'LLM failed' })

    const items = usePendingContent.getState().items
    expect(items[0].status).toBe('error')
    expect(items[0].error).toBe('LLM failed')
  })

  it('remove deletes an item by id', () => {
    usePendingContent.getState().add({
      id: 'pc-1', kind: 'flashcard' as const, status: 'ready' as const,
      chapter: 1, front: 'Q1', back: 'A1', sourceText: 's1',
    })
    usePendingContent.getState().add({
      id: 'pc-2', kind: 'flashcard' as const, status: 'ready' as const,
      chapter: 1, front: 'Q2', back: 'A2', sourceText: 's2',
    })

    usePendingContent.getState().remove('pc-1')

    const items = usePendingContent.getState().items
    expect(items).toHaveLength(1)
    expect(items[0].id).toBe('pc-2')
  })

  it('clearForDoc removes all items', () => {
    usePendingContent.getState().add({
      id: 'pc-1', kind: 'flashcard' as const, status: 'ready' as const,
      chapter: 1, front: 'Q1', back: 'A1', sourceText: 's1',
    })
    usePendingContent.getState().add({
      id: 'pc-2', kind: 'question' as const, status: 'ready' as const,
      chapter: 1, questionType: 'true_false' as const, questionData: {}, sourceText: 's2',
    })

    usePendingContent.getState().clearForDoc()

    expect(usePendingContent.getState().items).toHaveLength(0)
  })

  it('starts with empty items array', () => {
    expect(usePendingContent.getState().items).toEqual([])
  })
})

describe('makePendingId', () => {
  it('generates a string starting with pc-', () => {
    const id = makePendingId()
    expect(id.startsWith('pc-')).toBe(true)
  })

  it('generates unique ids', () => {
    const ids = new Set<string>()
    for (let i = 0; i < 100; i++) {
      ids.add(makePendingId())
    }
    expect(ids.size).toBe(100)
  })
})
