import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'node:fs'

function copyPdfjsResources(): Plugin {
  return {
    name: 'copy-pdfjs-resources',
    buildStart() {
      const srcRoot = path.resolve('node_modules', 'pdfjs-dist')
      const destRoot = path.resolve('public', 'pdfjs')
      const dirs = ['cmaps', 'standard_fonts', 'wasm']
      for (const dir of dirs) {
        const srcDir = path.join(srcRoot, dir)
        const destDir = path.join(destRoot, dir)
        if (!fs.existsSync(srcDir)) continue
        fs.mkdirSync(destDir, { recursive: true })
        for (const file of fs.readdirSync(srcDir)) {
          const srcFile = path.join(srcDir, file)
          const destFile = path.join(destDir, file)
          if (fs.statSync(srcFile).isFile() && !fs.existsSync(destFile)) {
            fs.copyFileSync(srcFile, destFile)
          }
        }
      }
    },
  }
}

function patchReactPdfWorker(): Plugin {
  return {
    name: 'patch-react-pdf-worker',
    transform(code, id) {
      if (id.includes('react-pdf') && id.endsWith('.js')) {
        return code.replace(/pdfjs\.GlobalWorkerOptions\.workerSrc\s*=\s*['"]pdf\.worker\.mjs['"]\s*;?/g, '')
      }
      return null
    },
  }
}

export default defineConfig({
  plugins: [react(), copyPdfjsResources(), patchReactPdfWorker()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    exclude: ['pdfjs-dist'],
  },
  build: {
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: parseInt(process.env.FRONTEND_PORT || '3500', 10),
    strictPort: true,
  },
})
