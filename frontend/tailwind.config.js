/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Token-driven font families. `font-ui` is the chrome default (set on body);
      // `font-reading` is the serif stack applied inside the reader surface only.
      fontFamily: {
        ui: 'var(--font-ui)',
        reading: 'var(--font-reading)',
      },
      // Token-driven type scale. We extend (not override) so the default Tailwind
      // sizes (`text-base`, `text-4xl`, `text-5xl`, etc.) keep working unchanged.
      fontSize: {
        xs: 'var(--text-xs)',
        sm: 'var(--text-sm)',
        md: 'var(--text-md)',
        lg: 'var(--text-lg)',
        xl: 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
      },
      colors: {
        bg: {
          DEFAULT: 'var(--color-bg)',
          page: 'var(--color-bg-page)',
          card: 'var(--color-bg-card)',
          elevated: 'var(--color-bg-elevated)',
          inset: 'var(--color-bg-inset)',
        },
        border: {
          DEFAULT: 'var(--color-border-default)',
          strong: 'var(--color-border-strong)',
          focus: 'var(--color-border-focus)',
          input: 'var(--color-border-input)',
          subtle: 'var(--color-border-subtle)',
        },
        text: {
          DEFAULT: 'var(--color-text-primary)',
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
          disabled: 'var(--color-text-disabled)',
          inverse: 'var(--color-text-inverse)',
          link: 'var(--color-text-link)',
        },
        icon: {
          DEFAULT: 'var(--color-icon-primary)',
          primary: 'var(--color-icon-primary)',
          secondary: 'var(--color-icon-secondary)',
          accent: 'var(--color-icon-accent)',
          success: 'var(--color-icon-success)',
          warning: 'var(--color-icon-warning)',
        },
        overlay: {
          backdrop: 'var(--color-overlay-backdrop)',
          modal: 'var(--color-overlay-modal)',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          card: 'var(--color-surface-card)',
          100: 'var(--color-surface-100)',
          200: 'var(--color-surface-200)',
        },
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          active: 'var(--color-primary-active)',
          light: 'var(--color-primary-light)',
          border: 'var(--color-primary-border)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          hover: 'var(--color-secondary-hover)',
          active: 'var(--color-secondary-active)',
          light: 'var(--color-secondary-light)',
          border: 'var(--color-secondary-border)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          active: 'var(--color-accent-active)',
          light: 'var(--color-accent-light)',
          border: 'var(--color-accent-border)',
        },
        success: {
          DEFAULT: 'var(--color-success-fg)',
          light: 'var(--color-success-bg)',
          fg: 'var(--color-success-fg)',
          bg: 'var(--color-success-bg)',
          border: 'var(--color-success-border)',
        },
        warning: {
          DEFAULT: 'var(--color-warning-fg)',
          light: 'var(--color-warning-bg)',
          fg: 'var(--color-warning-fg)',
          bg: 'var(--color-warning-bg)',
          border: 'var(--color-warning-border)',
        },
        // `danger` is deprecated — use `error` instead. The CSS vars remain
        // `--color-error-*`; the Tailwind group was renamed to match.
        error: {
          DEFAULT: 'var(--color-error-fg)',
          light: 'var(--color-error-bg)',
          fg: 'var(--color-error-fg)',
          bg: 'var(--color-error-bg)',
          border: 'var(--color-error-border)',
        },
        info: {
          fg: 'var(--color-info-fg)',
          bg: 'var(--color-info-bg)',
          border: 'var(--color-info-border)',
        },
        // Education domain states (chapter read, exam score, answer correctness).
        // Distinct from `success/warning/error/info` which remain for system feedback
        // (toasts, form validation). See Phase 3 notes in `.docs/plan.md`.
        mastered: {
          DEFAULT: 'var(--color-mastered-fg)',
          fg: 'var(--color-mastered-fg)',
          bg: 'var(--color-mastered-bg)',
          border: 'var(--color-mastered-border)',
        },
        learning: {
          DEFAULT: 'var(--color-learning-fg)',
          fg: 'var(--color-learning-fg)',
          bg: 'var(--color-learning-bg)',
          border: 'var(--color-learning-border)',
        },
        review: {
          DEFAULT: 'var(--color-review-fg)',
          fg: 'var(--color-review-fg)',
          bg: 'var(--color-review-bg)',
          border: 'var(--color-review-border)',
        },
        difficult: {
          DEFAULT: 'var(--color-difficult-fg)',
          fg: 'var(--color-difficult-fg)',
          bg: 'var(--color-difficult-bg)',
          border: 'var(--color-difficult-border)',
        },
        // AI visual language — used for chat messages, model selectors,
        // Sparkles icon contexts, "AI generated" badges, and toast accents.
        ai: {
          DEFAULT: 'var(--color-ai)',
          bg: 'var(--color-ai-bg)',
          border: 'var(--color-ai-border)',
          fg: 'var(--color-ai-fg)',
        },
        highlight: 'var(--reader-highlight)',
      },
      spacing: {
        reader: 'var(--reader-width)',
        'reader-para': 'var(--reader-paragraph-spacing)',
        page: 'var(--space-page)',
        section: 'var(--space-section)',
        card: 'var(--space-card)',
        inline: 'var(--space-inline)',
      },
      borderRadius: {
        card: '0.75rem',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        focus: 'var(--shadow-focus)',
      },
      keyframes: {
        'skeleton-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
        'card-flip': {
          '0%': { transform: 'rotateY(0deg)' },
          '100%': { transform: 'rotateY(180deg)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        skeleton: 'skeleton-pulse 1.5s ease-in-out infinite',
        flip: 'card-flip 0.4s ease-in-out forwards',
        'fade-in': 'fade-in 0.2s ease-in-out',
      },
    },
  },
  plugins: [
    require('./tailwind-plugins/animations'),
    require('./tailwind-plugins/three-d'),
  ],
}
