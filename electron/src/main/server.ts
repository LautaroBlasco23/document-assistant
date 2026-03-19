import { spawn, spawnSync, ChildProcess } from 'child_process'
import { existsSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import { is } from '@electron-toolkit/utils'
import axios from 'axios'

let serverProcess: ChildProcess | null = null

function resolveUvPath(): string {
  if (process.platform !== 'win32') return 'uv'

  // Try `where uv` to find the binary in the user's PATH
  const result = spawnSync('where', ['uv'], { encoding: 'utf8', shell: true })
  if (result.status === 0 && result.stdout) {
    const first = result.stdout.trim().split('\n')[0].trim()
    if (first) return first
  }

  // Common Windows install locations for uv
  const candidates = [
    join(process.env.USERPROFILE ?? '', '.local', 'bin', 'uv.exe'),
    join(process.env.APPDATA ?? '', 'uv', 'bin', 'uv.exe'),
    join(process.env.LOCALAPPDATA ?? '', 'uv', 'bin', 'uv.exe'),
    join(process.env.USERPROFILE ?? '', '.cargo', 'bin', 'uv.exe'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate
  }

  return 'uv.exe' // last resort: hope it's on PATH
}

export async function startServer(): Promise<void> {
  const uvPath = resolveUvPath()

  try {
    // Resolve project root: in dev electron/ parent, in prod next to the .exe
    const cwd = is.dev
      ? join(app.getAppPath(), '..')
      : join(process.resourcesPath, 'app')

    // Spawn uvicorn as a child process (attached so Electron can terminate it)
    // On Windows, use shell: true so cmd.exe resolves uv from the user's PATH
    serverProcess = spawn(uvPath, [
      'run',
      'uvicorn',
      'api.main:app',
      '--port',
      '8000',
      '--host',
      '127.0.0.1'
    ], {
      stdio: ['ignore', 'pipe', 'pipe'],
      cwd,
      shell: process.platform === 'win32'
    })

    let stderrOutput = ''
    serverProcess.stderr?.on('data', (data: Buffer) => {
      const text = data.toString()
      stderrOutput += text
      console.error('[uvicorn stderr]', text)
    })
    serverProcess.stdout?.on('data', (data: Buffer) => {
      console.log('[uvicorn stdout]', data.toString())
    })

    // Detect immediate process exit (e.g. uv not found, import error)
    let exitCode: number | null = null
    serverProcess.on('exit', (code) => {
      exitCode = code ?? -1
      console.error(`[uvicorn] process exited with code ${exitCode}`)
    })

    // Poll for server readiness
    for (let i = 0; i < 40; i++) {
      if (exitCode !== null) {
        throw new Error(
          `uvicorn exited with code ${exitCode}.\nstderr: ${stderrOutput.slice(-2000)}`
        )
      }
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

    throw new Error(`Server failed to start within 20 seconds.\nstderr: ${stderrOutput.slice(-2000)}`)
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
        spawn('taskkill', ['/PID', String(serverProcess.pid), '/F', '/T'], {
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
