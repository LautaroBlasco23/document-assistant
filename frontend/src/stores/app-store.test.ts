/**
 * Subject: src/stores/app-store.ts — useAppStore
 * Scope:   sidebar state, service health, error toast stack
 * Out of scope:
 *   - API client interactions → knowledge-tree-store.test.ts
 *   - Task lifecycle          → task-store.test.ts
 * Setup:   Zustand store is reset to initial state before each test.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useAppStore } from './app-store'

describe('useAppStore', () => {
  beforeEach(() => {
    useAppStore.setState({ sidebarCollapsed: false, serviceHealth: null, errors: [] })
  })

  // toggleSidebar flips the boolean from false → true.
  it('toggleSidebar toggles from false to true', () => {
    useAppStore.getState().toggleSidebar()
    expect(useAppStore.getState().sidebarCollapsed).toBe(true)
  })

  // toggleSidebar flips the boolean from true → false.
  it('toggleSidebar toggles from true to false', () => {
    useAppStore.setState({ sidebarCollapsed: true }, false)
    useAppStore.getState().toggleSidebar()
    expect(useAppStore.getState().sidebarCollapsed).toBe(false)
  })

  // setServiceHealth replaces the entire health object so UI can reflect status.
  it('setServiceHealth updates health status', () => {
    const health = {
      status: 'healthy',
      services: [{ name: 'postgres', healthy: true }],
    }
    useAppStore.getState().setServiceHealth(health)
    expect(useAppStore.getState().serviceHealth).toEqual(health)
  })

  // addError appends a new error with a unique id so toasts can be tracked individually.
  it('addError assigns unique id and adds to array', () => {
    useAppStore.getState().addError('first error')
    useAppStore.getState().addError('second error')
    const errors = useAppStore.getState().errors
    expect(errors).toHaveLength(2)
    expect(errors[0].message).toBe('first error')
    expect(errors[1].message).toBe('second error')
    expect(errors[0].id).not.toBe(errors[1].id)
  })

  // removeError filters out the error matching the given id.
  it('removeError removes by id', () => {
    useAppStore.getState().addError('error one')
    useAppStore.getState().addError('error two')
    const [first] = useAppStore.getState().errors
    useAppStore.getState().removeError(first.id)
    const remaining = useAppStore.getState().errors
    expect(remaining).toHaveLength(1)
    expect(remaining[0].message).toBe('error two')
  })
})
