/**
 * Subject: src/components/reader/UnifiedDocumentReader.tsx
 * Scope:   zoom helpers (snapZoom, loadDocZoom, ZOOM_LEVELS)
 * Out of scope:
 *   - Component rendering → integration / E2E tests
 * Setup:   localStorage is available via jsdom.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { ZOOM_LEVELS, snapZoom, loadDocZoom, saveDocZoom } from './UnifiedDocumentReader'

describe('ZOOM_LEVELS', () => {
  it('has 6 levels', () => {
    expect(ZOOM_LEVELS).toHaveLength(6)
  })

  it('starts at 0.75 and ends at 2', () => {
    expect(ZOOM_LEVELS[0]).toBe(0.75)
    expect(ZOOM_LEVELS[ZOOM_LEVELS.length - 1]).toBe(2)
  })

  it('includes 1 (100 %)', () => {
    expect(ZOOM_LEVELS).toContain(1)
  })

  it('is sorted ascending', () => {
    for (let i = 1; i < ZOOM_LEVELS.length; i++) {
      expect(ZOOM_LEVELS[i]).toBeGreaterThan(ZOOM_LEVELS[i - 1])
    }
  })
})

describe('snapZoom', () => {
  describe('zoom in (dir=1)', () => {
    it('goes from 0.75 to 1', () => {
      expect(snapZoom(0.75, 1)).toBe(1)
    })

    it('goes from 1 to 1.25', () => {
      expect(snapZoom(1, 1)).toBe(1.25)
    })

    it('stays at 2 when already at max', () => {
      expect(snapZoom(2, 1)).toBe(2)
    })

    it('snaps up from non-level value 0.9 → 1', () => {
      expect(snapZoom(0.9, 1)).toBe(1)
    })

    it('snaps up from 1.1 → 1.25', () => {
      expect(snapZoom(1.1, 1)).toBe(1.25)
    })
  })

  describe('zoom out (dir=-1)', () => {
    it('goes from 1 to 0.75', () => {
      expect(snapZoom(1, -1)).toBe(0.75)
    })

    it('goes from 1.5 to 1.25', () => {
      expect(snapZoom(1.5, -1)).toBe(1.25)
    })

    it('stays at 0.75 when already at min', () => {
      expect(snapZoom(0.75, -1)).toBe(0.75)
    })

    it('snaps down from non-level value 1.3 → 1.25', () => {
      expect(snapZoom(1.3, -1)).toBe(1.25)
    })
  })

  it('handles zoom direction for every level pair', () => {
    for (let i = 0; i < ZOOM_LEVELS.length - 1; i++) {
      expect(snapZoom(ZOOM_LEVELS[i], 1)).toBe(ZOOM_LEVELS[i + 1])
    }
    for (let i = ZOOM_LEVELS.length - 1; i > 0; i--) {
      expect(snapZoom(ZOOM_LEVELS[i], -1)).toBe(ZOOM_LEVELS[i - 1])
    }
  })

  describe('extreme boundary values', () => {
    it('snaps up from below minimum (0.5 → 0.75)', () => {
      expect(snapZoom(0.5, 1)).toBe(0.75)
    })

    it('stays at max when zooming in from above (2.5 → 2)', () => {
      expect(snapZoom(2.5, 1)).toBe(2)
    })

    it('stays at min when zooming out from below (0.5 → 0.75)', () => {
      expect(snapZoom(0.5, -1)).toBe(0.75)
    })

    it('snaps down from above max (2.5 → 2)', () => {
      expect(snapZoom(2.5, -1)).toBe(2)
    })
  })
})

describe('loadDocZoom', () => {
  const treeId = 'tree-1'
  const docId = 'doc-1'

  beforeEach(() => {
    localStorage.clear()
  })

  it('returns 1 when nothing is stored', () => {
    expect(loadDocZoom(treeId, docId)).toBe(1)
  })

  it('returns stored value when available', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, '1.5')
    expect(loadDocZoom(treeId, docId)).toBe(1.5)
  })

  it('returns 1 for NaN string', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, 'not-a-number')
    expect(loadDocZoom(treeId, docId)).toBe(1)
  })

  it('returns 1 for out-of-range value (3)', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, '3')
    expect(loadDocZoom(treeId, docId)).toBe(1)
  })

  it('returns 1 for out-of-range value (0.1)', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, '0.1')
    expect(loadDocZoom(treeId, docId)).toBe(1)
  })

  it('returns 1 for empty string', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, '')
    expect(loadDocZoom(treeId, docId)).toBe(1)
  })

  it('returns 0.5 at lower boundary', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, '0.5')
    expect(loadDocZoom(treeId, docId)).toBe(0.5)
  })

  it('returns 2 at upper boundary', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:${docId}`, '2')
    expect(loadDocZoom(treeId, docId)).toBe(2)
  })

  it('treats different doc IDs independently', () => {
    localStorage.setItem(`docassist_reader_zoom:${treeId}:doc-1`, '0.75')
    localStorage.setItem(`docassist_reader_zoom:${treeId}:doc-2`, '1.5')

    expect(loadDocZoom(treeId, 'doc-1')).toBe(0.75)
    expect(loadDocZoom(treeId, 'doc-2')).toBe(1.5)
    expect(loadDocZoom(treeId, 'doc-3')).toBe(1)
  })
})

describe('saveDocZoom', () => {
  beforeEach(() => { localStorage.clear() })

  it('writes and can be read back', () => {
    saveDocZoom('t1', 'd1', 1.5)
    expect(loadDocZoom('t1', 'd1')).toBe(1.5)
  })

  it('overwrites existing value', () => {
    saveDocZoom('t1', 'd1', 1)
    saveDocZoom('t1', 'd1', 2)
    expect(loadDocZoom('t1', 'd1')).toBe(2)
  })

  it('stores values at the boundary of valid range', () => {
    saveDocZoom('t1', 'd1', 0.5)
    expect(loadDocZoom('t1', 'd1')).toBe(0.5)
    saveDocZoom('t1', 'd2', 2)
    expect(loadDocZoom('t1', 'd2')).toBe(2)
  })
})
