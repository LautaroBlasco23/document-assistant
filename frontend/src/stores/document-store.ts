import { create } from 'zustand'
import { client } from '../services'
import type { DocumentOut, DocumentStructureOut } from '../types/api'

interface DocumentState {
  documents: DocumentOut[]
  loading: boolean
  structureCache: Record<string, DocumentStructureOut>
  fetchDocuments: () => Promise<void>
  fetchStructure: (hash: string) => Promise<void>
  removeDocument: (hash: string) => Promise<void>
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  loading: false,
  structureCache: {},

  fetchDocuments: async () => {
    set({ loading: true })
    try {
      const documents = await client.listDocuments()
      set({ documents })
    } catch {
      // fail silently — loading stops regardless
    } finally {
      set({ loading: false })
    }
  },

  fetchStructure: async (hash: string) => {
    const { structureCache } = get()
    if (structureCache[hash]) return
    try {
      const structure = await client.documentStructure(hash)
      set((state) => ({
        structureCache: { ...state.structureCache, [hash]: structure },
      }))
    } catch {
      // fail silently
    }
  },

  removeDocument: async (hash: string) => {
    await client.deleteDocument(hash)
    set((state) => ({
      documents: state.documents.filter((doc) => doc.file_hash !== hash),
    }))
  },
}))
