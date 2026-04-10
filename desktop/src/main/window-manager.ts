import { BrowserWindow, screen, ipcMain, dialog } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import { createRequire } from 'module'
import log from 'electron-log'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)

export class WindowManager {
  private mainWindow: BrowserWindow | null = null

  createWindow(): BrowserWindow {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize

    this.mainWindow = new BrowserWindow({
      width: Math.min(1400, width - 100),
      height: Math.min(900, height - 100),
      minWidth: 1000,
      minHeight: 700,
      webPreferences: {
        preload: path.join(__dirname, '..', 'preload', 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      show: false,
    })

    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show()
    })

    this.mainWindow.on('closed', () => {
      this.mainWindow = null
    })

    // Load the app
    this.loadContent()

    return this.mainWindow
  }

  private loadContent() {
    const isDev = process.env.NODE_ENV === 'development'

    if (isDev) {
      // In dev mode, load from Vite dev server
      log.info('Loading from dev server: http://localhost:5173')
      this.mainWindow?.loadURL('http://localhost:5173')
      this.mainWindow?.webContents.openDevTools()
    } else {
      // In production, load from built files
      const indexPath = path.join(__dirname, '..', '..', '..', 'frontend', 'dist', 'index.html')
      log.info('Loading production build from:', indexPath)
      this.mainWindow?.loadFile(indexPath)
    }
  }

  getWindow(): BrowserWindow | null {
    return this.mainWindow
  }

  setupIpcHandlers(): void {
    // Window control handlers
    ipcMain.on('window:minimize', () => {
      this.mainWindow?.minimize()
    })

    ipcMain.on('window:maximize', () => {
      if (this.mainWindow?.isMaximized()) {
        this.mainWindow.unmaximize()
      } else {
        this.mainWindow?.maximize()
      }
    })

    ipcMain.on('window:close', () => {
      this.mainWindow?.close()
    })

    // Dialog handlers
    ipcMain.handle('dialog:showOpen', async (_, options) => {
      const result = await dialog.showOpenDialog(this.mainWindow!, options)
      return {
        canceled: result.canceled,
        filePaths: result.filePaths,
      }
    })

    ipcMain.handle('dialog:showSave', async (_, options) => {
      const result = await dialog.showSaveDialog(this.mainWindow!, options)
      return {
        canceled: result.canceled,
        filePath: result.filePath,
      }
    })

    // App info handlers
    ipcMain.handle('app:getVersion', () => {
      return require('../../package.json').version
    })

    ipcMain.handle('app:getPlatform', () => {
      return process.platform
    })
  }
}
