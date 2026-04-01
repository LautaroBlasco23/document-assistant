import { create } from 'zustand'
import { client } from '../services'
import { useDocumentStore } from './document-store'

const pollingIntervals = new Map<string, ReturnType<typeof setInterval>>()

export type UploadStatus = 'uploading' | 'processing' | 'completed' | 'failed'

export interface UploadEntry {
  id: string
  filename: string
  taskId: string | null
  status: UploadStatus
  progress: string | null
  error: string | null
}

interface UploadState {
  uploads: UploadEntry[]
  startUpload: (file: File, documentType?: string, description?: string) => Promise<void>
  createDocument: (title: string, content: string, documentType?: string, description?: string) => Promise<void>
  handleIngestTask: (taskId: string, filename: string) => void
  dismissUpload: (id: string) => void
  rehydrate: () => Promise<void>
}

const LOCAL_KEY = 'docassist_uploads'

type PersistedUpload = Omit<UploadEntry, 'progress' | 'error'>

function _load(): PersistedUpload[] {
  try {
    const raw = localStorage.getItem(LOCAL_KEY)
    return raw ? (JSON.parse(raw) as PersistedUpload[]) : []
  } catch {
    return []
  }
}

function _save(uploads: UploadEntry[]) {
  try {
    const persisted: PersistedUpload[] = uploads.map(({ id, filename, taskId, status }) => ({
      id,
      filename,
      taskId,
      status,
    }))
    localStorage.setItem(LOCAL_KEY, JSON.stringify(persisted))
  } catch {
    // ignore storage errors
  }
}

function _remove(id: string) {
  try {
    const raw = localStorage.getItem(LOCAL_KEY)
    if (!raw) return
    const uploads = (JSON.parse(raw) as PersistedUpload[]).filter((u) => u.id !== id)
    if (uploads.length === 0) {
      localStorage.removeItem(LOCAL_KEY)
    } else {
      localStorage.setItem(LOCAL_KEY, JSON.stringify(uploads))
    }
  } catch {
    // ignore
  }
}

function _startPolling(id: string, taskId: string) {
  if (pollingIntervals.has(id)) return

  const interval = setInterval(async () => {
    try {
      const status = await client.getTaskStatus(taskId)

      useUploadStore.setState((state) => {
        const entry = state.uploads.find((u) => u.id === id)
        if (!entry) {
          clearInterval(interval)
          pollingIntervals.delete(id)
          return state
        }

        const updated: UploadEntry = { ...entry, progress: status.progress }
        if (status.status === 'completed') {
          updated.status = 'completed'
          clearInterval(interval)
          pollingIntervals.delete(id)
          _remove(id)
          setTimeout(() => useUploadStore.getState().dismissUpload(id), 2000)
          useDocumentStore.getState().fetchDocuments()
        } else if (status.status === 'failed') {
          updated.status = 'failed'
          updated.error = status.error ?? 'Processing failed'
          clearInterval(interval)
          pollingIntervals.delete(id)
          _remove(id)
        }

        return { uploads: state.uploads.map((u) => (u.id === id ? updated : u)) }
      })
    } catch {
      useUploadStore.setState((state) => ({
        uploads: state.uploads.map((u) =>
          u.id === id ? { ...u, status: 'failed', error: 'Lost connection to server' } : u
        ),
      }))
      clearInterval(interval)
      pollingIntervals.delete(id)
      _remove(id)
    }
  }, 1500)

  pollingIntervals.set(id, interval)
}

function _addUpload(upload: UploadEntry) {
  useUploadStore.setState((state) => ({
    uploads: [...state.uploads.filter((u) => u.id !== upload.id), upload],
  }))
}

export const useUploadStore = create<UploadState>((set) => ({
  uploads: [],

  startUpload: async (file: File, documentType = '', description = '') => {
    const id = crypto.randomUUID()
    const entry: UploadEntry = {
      id,
      filename: file.name,
      taskId: null,
      status: 'uploading',
      progress: null,
      error: null,
    }

    _addUpload(entry)

    let taskId: string
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      formData.append('description', description)
      const result = await client.ingestDocument(formData)
      taskId = result.task_id
    } catch (err) {
      _addUpload({
        ...entry,
        status: 'failed',
        error: err instanceof Error ? err.message : 'Upload failed',
      })
      return
    }

    const processingEntry: UploadEntry = { ...entry, taskId, status: 'processing' }
    _addUpload(processingEntry)
    _save([...useUploadStore.getState().uploads, processingEntry])
    _startPolling(id, taskId)
  },

  createDocument: async (title: string, content: string, documentType = '', description = '') => {
    const id = crypto.randomUUID()
    const entry: UploadEntry = {
      id,
      filename: title,
      taskId: null,
      status: 'uploading',
      progress: null,
      error: null,
    }

    _addUpload(entry)

    let taskId: string
    try {
      const result = await client.createDocument({ title, content, description, document_type: documentType })
      taskId = result.task_id
    } catch (err) {
      _addUpload({
        ...entry,
        status: 'failed',
        error: err instanceof Error ? err.message : 'Create failed',
      })
      return
    }

    const processingEntry: UploadEntry = { ...entry, taskId, status: 'processing' }
    _addUpload(processingEntry)
    _save([...useUploadStore.getState().uploads, processingEntry])
    _startPolling(id, taskId)
  },

  handleIngestTask: (taskId: string, filename: string) => {
    const id = crypto.randomUUID()
    const entry: UploadEntry = {
      id,
      filename,
      taskId,
      status: 'processing',
      progress: null,
      error: null,
    }
    _addUpload(entry)
    _save([...useUploadStore.getState().uploads, entry])
    _startPolling(id, taskId)
  },

  dismissUpload: (id: string) => {
    const interval = pollingIntervals.get(id)
    if (interval !== undefined) {
      clearInterval(interval)
      pollingIntervals.delete(id)
    }
    _remove(id)
    set((state) => ({ uploads: state.uploads.filter((u) => u.id !== id) }))
  },

  rehydrate: async () => {
    const persisted = _load()
    if (persisted.length === 0) return

    for (const p of persisted) {
      _addUpload({ ...p, progress: null, error: null })

      if (p.status === 'processing' && p.taskId) {
        _startPolling(p.id, p.taskId)
      } else if (p.status !== 'processing') {
        _remove(p.id)
      }
    }
  },
}))
