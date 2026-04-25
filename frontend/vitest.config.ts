import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    // Stub CSS imports so Tailwind / third-party CSS doesn't break tests
    {
      name: 'css-mock',
      enforce: 'pre',
      resolveId(source) {
        if (/\.(css|scss|sass|less)$/.test(source)) {
          return `virtual:css-mock:${source}`
        }
      },
      load(id) {
        if (typeof id === 'string' && id.startsWith('virtual:css-mock:')) {
          return ''
        }
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    passWithNoTests: true,
    pool: 'forks',
  },
})
