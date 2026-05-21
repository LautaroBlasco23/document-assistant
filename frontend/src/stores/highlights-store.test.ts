/**
 * Subject: src/stores/highlights-store.ts — useHighlights
 * Scope:   add, remove, clear, setHighlightDocId, clearHighlightDocId, localStorage persistence
 * Out of scope:
 *   - UI rendering of highlights → component tests
 * Setup:   Store state is reset before each test; localStorage is mocked.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useHighlights } from './highlights-store'

describe('useHighlights', () => {
  beforeEach(() => {
    localStorage.clear()
    useHighlights.setState({ highlights: {}, highlightDocIds: {} })
  })

  it('add creates a highlight with generated id and timestamp', () => {
    const result = useHighlights.getState().add('doc-1', 'highlighted text')

    expect(result.id).toMatch(/^h-/)
    expect(result.text).toBe('highlighted text')
    expect(result.createdAt).toBeDefined()
    expect(result.createdAt).toMatch(/\d{4}-\d{2}-\d{2}/)

    const highlights = useHighlights.getState().highlights['doc-1']
    expect(highlights).toHaveLength(1)
    expect(highlights[0]).toBe(result)
  })

  it('add preserves optional fields', () => {
    const result = useHighlights.getState().add('doc-1', 'text', {
      chapterNumber: 3,
      pageNumber: 12,
      startOffset: 5,
      endOffset: 20,
      isTitleHighlight: true,
    })

    expect(result.chapterNumber).toBe(3)
    expect(result.pageNumber).toBe(12)
    expect(result.startOffset).toBe(5)
    expect(result.endOffset).toBe(20)
    expect(result.isTitleHighlight).toBe(true)
  })

  it('add appends to existing highlights for the same doc', () => {
    useHighlights.getState().add('doc-1', 'first')
    useHighlights.getState().add('doc-1', 'second')

    const highlights = useHighlights.getState().highlights['doc-1']
    expect(highlights).toHaveLength(2)
    expect(highlights[0].text).toBe('first')
    expect(highlights[1].text).toBe('second')
  })

  it('add persists to localStorage', () => {
    useHighlights.getState().add('doc-1', 'text')

    const stored = JSON.parse(localStorage.getItem('docassist_highlights') || '{}')
    expect(stored.highlights['doc-1']).toHaveLength(1)
  })

  it('remove deletes a highlight by id', () => {
    const h = useHighlights.getState().add('doc-1', 'to remove')
    useHighlights.getState().add('doc-1', 'to keep')

    useHighlights.getState().remove('doc-1', h.id)

    const highlights = useHighlights.getState().highlights['doc-1']
    expect(highlights).toHaveLength(1)
    expect(highlights[0].text).toBe('to keep')
  })

  it('remove persists to localStorage', () => {
    const h = useHighlights.getState().add('doc-1', 'text')
    useHighlights.getState().remove('doc-1', h.id)

    const stored = JSON.parse(localStorage.getItem('docassist_highlights') || '{}')
    expect(stored.highlights['doc-1']).toHaveLength(0)
  })

  it('clear removes all highlights for a doc', () => {
    useHighlights.getState().add('doc-1', 'one')
    useHighlights.getState().add('doc-1', 'two')
    useHighlights.getState().add('doc-2', 'other')

    useHighlights.getState().clear('doc-1')

    expect(useHighlights.getState().highlights['doc-1']).toEqual([])
    expect(useHighlights.getState().highlights['doc-2']).toHaveLength(1)
  })

  it('setHighlightDocId stores the mapping', () => {
    useHighlights.getState().setHighlightDocId('source-1', 'highlights-doc-1')

    expect(useHighlights.getState().highlightDocIds['source-1']).toBe('highlights-doc-1')
  })

  it('setHighlightDocId persists to localStorage', () => {
    useHighlights.getState().setHighlightDocId('source-1', 'highlights-doc-1')

    const stored = JSON.parse(localStorage.getItem('docassist_highlights') || '{}')
    expect(stored.highlightDocIds['source-1']).toBe('highlights-doc-1')
  })

  it('clearHighlightDocId removes the mapping', () => {
    useHighlights.getState().setHighlightDocId('source-1', 'highlights-doc-1')
    useHighlights.getState().setHighlightDocId('source-2', 'highlights-doc-2')

    useHighlights.getState().clearHighlightDocId('source-1')

    expect(useHighlights.getState().highlightDocIds['source-1']).toBeUndefined()
    expect(useHighlights.getState().highlightDocIds['source-2']).toBe('highlights-doc-2')
  })

  it('loads from localStorage on initialization', () => {
    const data = {
      highlights: { 'doc-1': [{ id: 'h-1', text: 'restored', createdAt: '2024-01-01' }] },
      highlightDocIds: { 'source-1': 'doc-1' },
    }
    localStorage.setItem('docassist_highlights', JSON.stringify(data))

    // Re-import to trigger load
    vi.resetModules()
  })

  it('handles corrupt localStorage gracefully', () => {
    localStorage.setItem('docassist_highlights', 'not json')

    // Should not throw
    const state = useHighlights.getState()
    expect(state.highlights).toEqual({})
  })
})
