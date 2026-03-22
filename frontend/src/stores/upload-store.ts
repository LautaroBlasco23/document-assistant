import { create } from 'zustand'
import { client } from '../services'
import { useDocumentStore } from './document-store'

// Module-level map of active polling intervals (outside Zustand state)
const pollingIntervals = new Map<string, ReturnType<typeof setInterval>>()

export interface UploadEntry {
  id: string
  filename: string
  taskId: string | null
  status: 'uploading' | 'processing' | 'completed' | 'failed'
  progress: string | null
  error: string | null
}

interface UploadState {
  uploads: UploadEntry[]
  startUpload: (file: File, documentType?: string, description?: string) => Promise<void>
  dismissUpload: (id: string) => void
}

function updateEntry(
  set: (fn: (state: UploadState) => Partial<UploadState>) => void,
  id: string,
  partial: Partial<UploadEntry>,
) {
  set((state) => ({
    uploads: state.uploads.map((entry) =>
      entry.id === id ? { ...entry, ...partial } : entry
    ),
  }))
}

export const useUploadStore = create<UploadState>((set, get) => ({
  uploads: [],

  startUpload: async (file: File, documentType = '', description = '') => {
    const id = crypto.randomUUID()

    // Push new entry immediately so the card appears right away
    set((state) => ({
      uploads: [
        ...state.uploads,
        {
          id,
          filename: file.name,
          taskId: null,
          status: 'uploading',
          progress: null,
          error: null,
        },
      ],
    }))

    let taskId: string
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      formData.append('description', description)
      const result = await client.ingestDocument(formData)
      taskId = result.task_id
    } catch (err) {
      updateEntry(set, id, {
        status: 'failed',
        error: err instanceof Error ? err.message : 'Upload failed',
      })
      return
    }

    updateEntry(set, id, { taskId, status: 'processing' })

    const interval = setInterval(async () => {
      try {
        const status = await client.getTaskStatus(taskId)

        if (status.status === 'completed') {
          updateEntry(set, id, { status: 'completed', progress: status.progress })
          clearInterval(interval)
          pollingIntervals.delete(id)

          await useDocumentStore.getState().fetchDocuments()
          setTimeout(() => {
            get().dismissUpload(id)
          }, 2000)
        } else if (status.status === 'failed') {
          updateEntry(set, id, {
            status: 'failed',
            error: status.error ?? 'Processing failed',
            progress: status.progress,
          })
          clearInterval(interval)
          pollingIntervals.delete(id)
        } else {
          // Still running — update progress message
          updateEntry(set, id, { progress: status.progress })
        }
      } catch {
        // Network error during polling — stop and mark failed
        updateEntry(set, id, { status: 'failed', error: 'Lost connection to server' })
        clearInterval(interval)
        pollingIntervals.delete(id)
      }
    }, 1500)

    pollingIntervals.set(id, interval)
  },

  dismissUpload: (id: string) => {
    const interval = pollingIntervals.get(id)
    if (interval !== undefined) {
      clearInterval(interval)
      pollingIntervals.delete(id)
    }
    set((state) => ({
      uploads: state.uploads.filter((entry) => entry.id !== id),
    }))
  },
}))
