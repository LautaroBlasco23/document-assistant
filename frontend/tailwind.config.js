/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563eb', // blue-600
          hover: '#1d4ed8',   // blue-700
          light: '#eff6ff',   // blue-50
        },
        surface: {
          DEFAULT: '#f8fafc', // slate-50
          100: '#f1f5f9',     // slate-100
          200: '#e2e8f0',     // slate-200
        },
        accent: {
          DEFAULT: '#8b5cf6', // violet-500
          hover: '#7c3aed',   // violet-600
          light: '#f5f3ff',   // violet-50
        },
        success: {
          DEFAULT: '#22c55e', // green-500
          light: '#f0fdf4',   // green-50
        },
        warning: {
          DEFAULT: '#f59e0b', // amber-500
          light: '#fffbeb',   // amber-50
        },
        danger: {
          DEFAULT: '#ef4444', // red-500
          light: '#fef2f2',   // red-50
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
