import { defineConfig } from 'vite'
import path from 'path'

export default defineConfig({
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/main/main.ts'),
      formats: ['es'],
      fileName: () => 'main.js',
    },
    outDir: 'build/main',
    emptyOutDir: true,
    rollupOptions: {
      external: ['electron', 'electron-log', 'child_process', 'path', 'fs', 'os', 'util', 'url', 'module'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
