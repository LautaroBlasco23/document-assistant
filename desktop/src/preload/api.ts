export interface BackendStatus {
  status: 'starting' | 'running' | 'error' | 'stopped'
  url?: string
  error?: string
}

export interface DesktopAPI {
  startBackend: () => Promise<BackendStatus>
  stopBackend: () => Promise<void>
  getBackendStatus: () => Promise<BackendStatus>
  onBackendStatusChange: (callback: (status: BackendStatus) => void) => () => void
  getAppVersion: () => Promise<string>
  getPlatform: () => Promise<string>
  minimizeWindow: () => void
  maximizeWindow: () => void
  closeWindow: () => void
  showOpenDialog: (options: {
    properties: ('openFile' | 'multiSelections')[]
    filters?: { name: string; extensions: string[] }[]
  }) => Promise<{ canceled: boolean; filePaths: string[] }>
  showSaveDialog: (options: {
    defaultPath?: string
    filters?: { name: string; extensions: string[] }[]
  }) => Promise<{ canceled: boolean; filePath?: string }>
  isDev: boolean
}

declare global {
  interface Window {
    desktopAPI: DesktopAPI
  }
}
