import * as React from 'react'

/**
 * Wires a `beforeunload` browser guard while `isDirty` is true.
 *
 * When the user closes the tab, refreshes, or navigates away externally, the
 * browser will show its native "leave site?" prompt. In-app navigation (e.g.
 * clicking another chapter) is not covered here — callers should disable
 * navigation affordances or prompt manually when dirty.
 */
export function useEditGuard(isDirty: boolean): void {
  React.useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      // Modern browsers ignore the returned string but require returnValue to be set.
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])
}
