import * as React from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'

/**
 * Tracks the user's `prefers-reduced-motion` OS setting.
 *
 * Returns `true` when the user has requested reduced motion (system-level
 * accessibility setting). Use this to gate animation-heavy React effects
 * (e.g. particle effects) that the CSS guard cannot reach. Long-running
 * animations defined purely in CSS are already covered by the
 * `prefers-reduced-motion` media query in `index.css`.
 *
 * Returns `false` during SSR or when `window.matchMedia` is unavailable.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia(QUERY).matches
  })

  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mql = window.matchMedia(QUERY)
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches)
    // `addEventListener` is the modern API; Safari < 14 needs `addListener`.
    if (mql.addEventListener) {
      mql.addEventListener('change', handler)
      return () => mql.removeEventListener('change', handler)
    }
    mql.addListener(handler)
    return () => mql.removeListener(handler)
  }, [])

  return reduced
}
