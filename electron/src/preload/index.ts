import { contextBridge } from 'electron'

// Expose minimal API to renderer
contextBridge.exposeInMainWorld('api', {
  // Placeholder for any secure IPC calls needed later
  version: '0.1.0'
})
