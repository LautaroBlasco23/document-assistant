/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
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
        danger: {
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
      },
      borderRadius: {
        card: '0.75rem',
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
  plugins: [],
}
