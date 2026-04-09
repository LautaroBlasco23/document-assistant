import { ipcMain, IpcMainInvokeEvent } from 'electron'
import log from 'electron-log'
import { BackendManager, BackendStatus } from './backend-manager'

export function setupBackendIpc(backendManager: BackendManager): void {
  // Start backend
  ipcMain.handle('backend:start', async (): Promise<BackendStatus> => {
    try {
      log.info('IPC: Starting backend')
      return await backendManager.start()
    } catch (error) {
      log.error('Failed to start backend:', error)
      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  })

  // Stop backend
  ipcMain.handle('backend:stop', async (): Promise<void> => {
    try {
      log.info('IPC: Stopping backend')
      await backendManager.stop()
    } catch (error) {
      log.error('Failed to stop backend:', error)
      throw error
    }
  })

  // Get backend status
  ipcMain.handle('backend:getStatus', (): BackendStatus => {
    return backendManager.getStatus()
  })

  // Subscribe to status changes (one-way communication to renderer)
  backendManager.onStatusChange((status) => {
    const { BrowserWindow } = require('electron')
    const windows = BrowserWindow.getAllWindows()
    windows.forEach((win: Electron.BrowserWindow) => {
      win.webContents.send('backend:status', status)
    })
  })
}
