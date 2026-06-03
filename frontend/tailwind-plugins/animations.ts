import plugin from 'tailwindcss/plugin'

/**
 * Animation keyframes and utility classes migrated from hand-rolled CSS in
 * `src/index.css`. These provide IntelliSense discoverability and inline
 * documentation while preserving the original visual behavior.
 *
 * NOTE: `.source-doc-animated-border`, `.sidebar-border-green`, and
 * `.sidebar-border-blue` remain defined in `index.css` because they use
 * pseudo-elements (`::before`) or reference CSS custom properties via
 * `color-mix()` in ways that are impractical to express through
 * `addUtilities`. Their keyframes are registered here so they can be
 * discovered and reused.
 */
export default plugin(({ addBase, addUtilities }) => {
  addBase({
    /* ── Sidebar left-border breathing ── */
    '@keyframes breathe-green': {
      '0%, 100%': {
        boxShadow:
          'inset 2px 0 0 0 color-mix(in srgb, var(--color-success-fg) 30%, transparent)',
      },
      '50%': {
        boxShadow:
          'inset 2px 0 0 0 color-mix(in srgb, var(--color-success-fg) 90%, transparent)',
      },
    },
    '@keyframes breathe-blue': {
      '0%, 100%': {
        boxShadow:
          'inset 2px 0 0 0 color-mix(in srgb, var(--color-primary) 30%, transparent)',
      },
      '50%': {
        boxShadow:
          'inset 2px 0 0 0 color-mix(in srgb, var(--color-primary) 90%, transparent)',
      },
    },
    /* ── Spinning conic-gradient border (Original Source Document card) ── */
    '@keyframes source-border-spin': {
      to: { '--source-border-angle': '360deg' },
    },
    /* ── Model-select role particles ── */
    '@keyframes model-particle-rise': {
      '0%': { transform: 'translateY(0) scale(1)', opacity: '0.85' },
      '70%': { opacity: '0.5' },
      '100%': { transform: 'translateY(-16px) scale(0.2)', opacity: '0' },
    },
  })

  addUtilities({
    '.animate-breathe-green': {
      animation: 'breathe-green 2.5s ease-in-out infinite',
    },
    '.animate-breathe-blue': {
      animation: 'breathe-blue 2.5s ease-in-out infinite',
    },
    '.animate-source-border': {
      animation: 'source-border-spin 4s linear infinite',
    },
  })
})
