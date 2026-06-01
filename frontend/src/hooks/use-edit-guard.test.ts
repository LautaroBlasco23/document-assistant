/**
 * Subject: src/hooks/use-edit-guard.ts — useEditGuard
 * Scope:   beforeunload handler is attached only while isDirty is true;
 *          removed when isDirty goes false or the component unmounts.
 * Out of scope:
 *   - Browser confirm dialog UI (jsdom does not implement beforeunload prompts)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useEditGuard } from './use-edit-guard'

describe('useEditGuard', () => {
  let addSpy: ReturnType<typeof vi.spyOn>
  let removeSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    addSpy = vi.spyOn(window, 'addEventListener')
    removeSpy = vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    addSpy.mockRestore()
    removeSpy.mockRestore()
  })

  it('attaches a beforeunload listener when isDirty is true', () => {
    renderHook(() => useEditGuard(true))
    const events = addSpy.mock.calls.map((c) => c[0])
    expect(events).toContain('beforeunload')
  })

  it('does NOT attach a beforeunload listener when isDirty is false', () => {
    renderHook(() => useEditGuard(false))
    const events = addSpy.mock.calls.map((c) => c[0])
    expect(events).not.toContain('beforeunload')
  })

  it('removes the beforeunload listener on unmount', () => {
    const { unmount } = renderHook(() => useEditGuard(true))
    unmount()
    const removed = removeSpy.mock.calls.map((c) => c[0])
    expect(removed).toContain('beforeunload')
  })
})
