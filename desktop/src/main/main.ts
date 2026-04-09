import { app, BrowserWindow } from 'electron'
import path from 'path'
import log from 'electron-log'
import { WindowManager } from './window-manager'

// Configure logging
log.transports.file.level = 'info'
log.transports.console.level = 'debug'

// Initialize window manager
let windowManager: WindowManager | null = null

// Environment detection
const isDev = process.env.NODE_ENV === 'development'

function createWindow(): BrowserWindow {
  if (!windowManager) {
    windowManager = new WindowManager()
  }
  return windowManager.createWindow()
}

async function initializeApp() {
  log.info('App starting...', { version: app.getVersion(), platform: process.platform })
  log.info('Mode: Client-only (connects to external backend at localhost:8000)')

  // Create window manager
  windowManager = new WindowManager()
  windowManager.setupIpcHandlers()

  // Create main window
  createWindow()
}

// App event handlers
app.whenReady().then(initializeApp)

app.on('window-all-closed', () => {
  log.info('All windows closed')
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

// Security: Prevent new window creation
app.on('web-contents-created', (_, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault()
    log.warn('Blocked new window:', navigationUrl)
  })

  contents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl)

    // Only allow navigation to localhost in dev, or file:// in production
    if (isDev) {
      if (parsedUrl.origin !== 'http://localhost:5173') {
        event.preventDefault()
        log.warn('Blocked navigation to:', navigationUrl)
      }
    } else {
      if (parsedUrl.protocol !== 'file:') {
        event.preventDefault()
        log.warn('Blocked navigation to:', navigationUrl)
      }
    }
  })
})
