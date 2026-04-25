import { test, expect } from 'vitest'
import { useAppStore } from './app-store'

test('debug app-store export', () => {
  console.log('type:', typeof useAppStore)
  console.log('getState type:', typeof useAppStore.getState)
  const state = useAppStore.getState()
  console.log('keys:', Object.keys(state))
  console.log('toggleSidebar:', typeof state.toggleSidebar)
  expect(typeof state.toggleSidebar).toBe('function')
})
