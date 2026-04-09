import { contextBridge, ipcRenderer } from 'electron'

// Expose minimal API for desktop integration
const api = {
  getAppVersion: () => ipcRenderer.invoke('app:getVersion'),
  getPlatform: () => ipcRenderer.invoke('app:getPlatform'),
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  maximizeWindow: () => ipcRenderer.send('window:maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),
  showOpenDialog: (options: unknown) => ipcRenderer.invoke('dialog:showOpen', options),
  showSaveDialog: (options: unknown) => ipcRenderer.invoke('dialog:showSave', options),
  isDev: process.env.NODE_ENV === 'development',
  isElectron: true,
}

contextBridge.exposeInMainWorld('desktopAPI', api)
