import React from 'react'
import ReactDOM from 'react-dom/client'
import { pdfjs } from 'react-pdf'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?worker&url'
import App from './App'
import './index.css'
import { ThemeProvider } from './theme/theme-context'

pdfjs.GlobalWorkerOptions.workerSrc = PdfWorker

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
