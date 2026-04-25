/**
 * Subject: src/components/ui/error-toasts.tsx — ErrorToasts + ErrorToast
 * Scope:   Rendering errors from the app store, auto-dismiss timer, manual removal
 * Out of scope:
 *   - addError / store logic  → app-store.test.tsx
 * Setup: Fake timers so the 5-second auto-dismiss can be tested deterministically.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ErrorToasts } from './error-toasts'
import { renderWithProviders, screen, fireEvent } from '@/test/utils'

const mockRemoveError = vi.hoisted(() => vi.fn())
const mockUseAppStore = vi.hoisted(() => vi.fn())

vi.mock('@/stores/app-store', () => ({
  useAppStore: mockUseAppStore,
}))

function createMockStore(errors: any[]) {
  return {
    sidebarCollapsed: false,
    toggleSidebar: vi.fn(),
    serviceHealth: null,
    setServiceHealth: vi.fn(),
    errors,
    addError: vi.fn(),
    removeError: mockRemoveError,
  }
}

describe('ErrorToasts', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockRemoveError.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders nothing when there are no errors', () => {
    // The toast container should not be present in the DOM when the app is error-free.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore([]))
    )

    const { container } = renderWithProviders(<ErrorToasts />)

    expect(container.firstChild).toBeNull()
  })

  it('renders each error message from the store', () => {
    // Every active error should surface as a visible toast with its message.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(
        createMockStore([
          { id: 'err-1', message: 'Network failure' },
          { id: 'err-2', message: 'Save failed' },
        ])
      )
    )

    renderWithProviders(<ErrorToasts />)

    expect(screen.getByText('Network failure')).toBeInTheDocument()
    expect(screen.getByText('Save failed')).toBeInTheDocument()
  })

  it('auto-dismisses an error after the timeout expires', () => {
    // Errors should disappear automatically so the UI doesn't stay cluttered.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore([{ id: 'err-1', message: 'Timeout' }]))
    )

    renderWithProviders(<ErrorToasts />)
    expect(screen.getByText('Timeout')).toBeInTheDocument()

    vi.advanceTimersByTime(5000)

    expect(mockRemoveError).toHaveBeenCalledWith('err-1')
    expect(mockRemoveError).toHaveBeenCalledTimes(1)
  })

  it('cleans up the timer on unmount to avoid leaking setTimeout callbacks', () => {
    // Unmounting should cancel any pending auto-dismiss to prevent state updates on unmounted components.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore([{ id: 'err-1', message: 'Leak test' }]))
    )

    const { unmount } = renderWithProviders(<ErrorToasts />)
    unmount()

    vi.advanceTimersByTime(5000)

    // removeError should not be called after unmount because the effect cleanup clears the timer.
    expect(mockRemoveError).not.toHaveBeenCalled()
  })

  it('removes an error immediately when the dismiss button is clicked', () => {
    // Users should be able to dismiss toasts manually without waiting for the timeout.
    // We use fireEvent because user-event hangs when fake timers are active.
    mockUseAppStore.mockImplementation((selector: (state: any) => any) =>
      selector(createMockStore([{ id: 'err-1', message: 'Click to dismiss' }]))
    )

    renderWithProviders(<ErrorToasts />)

    const dismissBtn = screen.getByLabelText('Dismiss')
    fireEvent.click(dismissBtn)

    expect(mockRemoveError).toHaveBeenCalledWith('err-1')
    expect(mockRemoveError).toHaveBeenCalledTimes(1)
  })
})
