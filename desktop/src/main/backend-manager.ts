import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import { app } from 'electron'
import log from 'electron-log'

export interface BackendStatus {
  status: 'starting' | 'running' | 'error' | 'stopped'
  url?: string
  error?: string
}

type StatusCallback = (status: BackendStatus) => void

export class BackendManager {
  private process: ChildProcess | null = null
  private status: BackendStatus = { status: 'stopped' }
  private statusCallbacks: StatusCallback[] = []
  private healthCheckInterval: NodeJS.Timeout | null = null

  constructor() {
    this.updateStatus({ status: 'stopped' })
  }

  private updateStatus(newStatus: Partial<BackendStatus>) {
    this.status = { ...this.status, ...newStatus }
    this.statusCallbacks.forEach(cb => cb(this.status))
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusCallbacks.push(callback)
    callback(this.status)
    return () => {
      this.statusCallbacks = this.statusCallbacks.filter(cb => cb !== callback)
    }
  }

  async start(): Promise<BackendStatus> {
    if (this.process) {
      log.info('Backend already running')
      return this.status
    }

    this.updateStatus({ status: 'starting' })

    try {
      const isDev = process.env.NODE_ENV === 'development'
      const backendPath = isDev
        ? path.join(app.getAppPath(), '..', 'backend')
        : path.join(process.resourcesPath, 'backend')

      const configPath = isDev
        ? path.join(app.getAppPath(), '..', 'config')
        : path.join(process.resourcesPath, 'config')

      log.info('Starting backend from:', backendPath)
      log.info('Config path:', configPath)

      // Determine the uv command
      const uvCmd = process.platform === 'win32' ? 'uv.exe' : 'uv'

      // Spawn the backend process
      this.process = spawn(uvCmd, [
        'run',
        'uvicorn',
        'api.main:app',
        '--port', '8000',
        '--host', '127.0.0.1',
        '--log-level', 'info'
      ], {
        cwd: backendPath,
        env: {
          ...process.env,
          DOCASSIST_CONFIG_PATH: configPath,
        },
        stdio: 'pipe',
      })

      this.process.stdout?.on('data', (data) => {
        log.info('[Backend]', data.toString().trim())
      })

      this.process.stderr?.on('data', (data) => {
        log.error('[Backend Error]', data.toString().trim())
      })

      this.process.on('error', (error) => {
        log.error('Backend process error:', error)
        this.updateStatus({ status: 'error', error: error.message })
      })

      this.process.on('exit', (code) => {
        log.info(`Backend process exited with code ${code}`)
        this.process = null
        this.updateStatus({ status: 'stopped' })
        this.stopHealthCheck()
      })

      // Wait for backend to be ready
      await this.waitForBackend()
      this.startHealthCheck()

      return this.status
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      log.error('Failed to start backend:', errorMsg)
      this.updateStatus({ status: 'error', error: errorMsg })
      return this.status
    }
  }

  async stop(): Promise<void> {
    if (!this.process) {
      return
    }

    log.info('Stopping backend...')
    this.stopHealthCheck()

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        log.warn('Backend did not exit gracefully, forcing kill')
        this.process?.kill('SIGKILL')
      }, 5000)

      this.process?.on('exit', () => {
        clearTimeout(timeout)
        this.process = null
        resolve()
      })

      this.process?.kill('SIGTERM')
    })
  }

  getStatus(): BackendStatus {
    return this.status
  }

  private async waitForBackend(timeout = 30000): Promise<void> {
    const startTime = Date.now()
    const url = 'http://127.0.0.1:8000/api/health'

    while (Date.now() - startTime < timeout) {
      try {
        const response = await fetch(url, { method: 'GET' })
        if (response.ok) {
          log.info('Backend is ready')
          this.updateStatus({ status: 'running', url: 'http://127.0.0.1:8000' })
          return
        }
      } catch {
        // Backend not ready yet
      }
      await new Promise(r => setTimeout(r, 500))
    }

    throw new Error('Backend failed to start within timeout')
  }

  private startHealthCheck() {
    this.stopHealthCheck()
    this.healthCheckInterval = setInterval(async () => {
      if (this.status.status !== 'running') return

      try {
        const response = await fetch('http://127.0.0.1:8000/api/health', {
          method: 'GET',
          signal: AbortSignal.timeout(5000)
        })
        if (!response.ok) {
          throw new Error('Health check failed')
        }
      } catch {
        log.warn('Backend health check failed')
        this.updateStatus({ status: 'error', error: 'Health check failed' })
      }
    }, 30000)
  }

  private stopHealthCheck() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
      this.healthCheckInterval = null
    }
  }
}
