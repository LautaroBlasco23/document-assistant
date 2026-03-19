import { spawn, ChildProcess } from 'child_process'
import { existsSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import { is } from '@electron-toolkit/utils'
import axios from 'axios'

let serverProcess: ChildProcess | null = null

export async function startServer(): Promise<void> {
  // Try to find uv executable
  const uvPath = process.platform === 'win32' ? 'uv.exe' : 'uv'

  try {
    // Resolve project root: in dev electron/ parent, in prod next to the .exe
    const cwd = is.dev
      ? join(app.getAppPath(), '..')
      : join(process.resourcesPath, 'app')

    // Spawn uvicorn as a child process (attached so Electron can terminate it)
    serverProcess = spawn(uvPath, [
      'run',
      'uvicorn',
      'api.main:app',
      '--port',
      '8000',
      '--host',
      '127.0.0.1'
    ], {
      stdio: 'ignore',
      cwd
    })

    // Poll for server readiness
    for (let i = 0; i < 40; i++) {
      try {
        const response = await axios.get('http://localhost:8000/api/health', {
          timeout: 1000
        })
        if (response.status === 200) {
          console.log('FastAPI server started successfully')
          return
        }
      } catch (e) {
        // Server not ready yet, wait and retry
        await new Promise(resolve => setTimeout(resolve, 500))
      }
    }

    throw new Error('Server failed to start within 20 seconds')
  } catch (error) {
    console.error('Failed to start server:', error)
    throw error
  }
}

export async function stopServer(): Promise<void> {
  if (serverProcess) {
    try {
      // Send SIGTERM to process group
      if (process.platform === 'win32') {
        // On Windows, use taskkill
        spawn('taskkill', ['/PID', String(serverProcess.pid), '/F'], {
          stdio: 'ignore'
        })
      } else {
        // On Unix, send SIGTERM to process group
        process.kill(-serverProcess.pid, 'SIGTERM')
      }

      // Wait a bit for graceful shutdown
      await new Promise(resolve => setTimeout(resolve, 1000))
    } catch (error) {
      console.error('Error stopping server:', error)
    }
    serverProcess = null
  }
}
