import { app, BrowserWindow } from 'electron'
import path from 'path'
import log from 'electron-log'
import { BackendManager } from './backend-manager'
import { WindowManager } from './window-manager'
import { setupBackendIpc } from './ipc-handlers'

// Configure logging
log.transports.file.level = 'info'
log.transports.console.level = 'debug'

// Initialize managers
let backendManager: BackendManager | null = null
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

  // Create backend manager
  backendManager = new BackendManager()

  // Create window manager and setup IPC
  windowManager = new WindowManager()
  windowManager.setupIpcHandlers()
  setupBackendIpc(backendManager)

  // Create main window
  createWindow()

  // Start backend automatically
  try {
    log.info('Auto-starting backend...')
    await backendManager.start()
  } catch (error) {
    log.error('Failed to auto-start backend:', error)
    // Don't quit - let the user see the error in the UI
  }
}

// App event handlers
app.whenReady().then(initializeApp)

app.on('window-all-closed', async () => {
  log.info('All windows closed')

  // Stop backend when app is quitting
  if (backendManager) {
    try {
      await backendManager.stop()
    } catch (error) {
      log.error('Error stopping backend:', error)
    }
  }

  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

app.on('before-quit', async (event) => {
  log.info('App before-quit event')

  if (backendManager) {
    event.preventDefault()
    try {
      await backendManager.stop()
    } catch (error) {
      log.error('Error stopping backend during quit:', error)
    }
    app.quit()
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
