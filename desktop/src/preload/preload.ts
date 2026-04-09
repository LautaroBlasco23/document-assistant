import { contextBridge, ipcRenderer } from 'electron'
import type { BackendStatus, DesktopAPI } from './api'

const api: DesktopAPI = {
  startBackend: () => ipcRenderer.invoke('backend:start'),
  stopBackend: () => ipcRenderer.invoke('backend:stop'),
  getBackendStatus: () => ipcRenderer.invoke('backend:getStatus'),
  onBackendStatusChange: (callback) => {
    const handler = (_: unknown, status: BackendStatus) => callback(status)
    ipcRenderer.on('backend:status', handler)
    return () => ipcRenderer.removeListener('backend:status', handler)
  },
  getAppVersion: () => ipcRenderer.invoke('app:getVersion'),
  getPlatform: () => ipcRenderer.invoke('app:getPlatform'),
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  maximizeWindow: () => ipcRenderer.send('window:maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),
  showOpenDialog: (options) => ipcRenderer.invoke('dialog:showOpen', options),
  showSaveDialog: (options) => ipcRenderer.invoke('dialog:showSave', options),
  isDev: process.env.NODE_ENV === 'development',
}

contextBridge.exposeInMainWorld('desktopAPI', api)
