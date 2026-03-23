import { create } from 'zustand'
import { client } from '../services'
import type { DocumentOut, DocumentStructureOut } from '../types/api'

interface DocumentMetadata {
  description: string
  document_type: string
}

interface DocumentState {
  documents: DocumentOut[]
  loading: boolean
  structureCache: Record<string, DocumentStructureOut>
  metadataCache: Record<string, DocumentMetadata>
  fetchDocuments: () => Promise<void>
  fetchStructure: (hash: string) => Promise<void>
  removeDocument: (hash: string) => Promise<void>
  removeChapter: (hash: string, chapterNumber: number) => Promise<void>
  fetchMetadata: (hash: string) => Promise<void>
  saveMetadata: (hash: string, description: string, documentType?: string) => Promise<void>
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  loading: false,
  structureCache: {},
  metadataCache: {},

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

  removeChapter: async (hash: string, chapterNumber: number) => {
    await client.deleteChapter(hash, chapterNumber)
    // Invalidate structure cache so the chapter list is re-fetched on next access
    set((state) => {
      const { [hash]: _removed, ...rest } = state.structureCache
      return { structureCache: rest }
    })
    // Re-fetch structure to reflect the deletion immediately
    try {
      const structure = await client.documentStructure(hash)
      set((state) => ({
        structureCache: { ...state.structureCache, [hash]: structure },
      }))
    } catch {
      // fail silently — cache is already invalidated
    }
  },

  fetchMetadata: async (hash: string) => {
    try {
      const resp = await client.getMetadata(hash)
      set((state) => ({
        metadataCache: {
          ...state.metadataCache,
          [hash]: { description: resp.description, document_type: resp.document_type },
        },
      }))
    } catch {
      // fail silently
    }
  },

  saveMetadata: async (hash: string, description: string, documentType?: string) => {
    const current = get().metadataCache[hash]
    const newDocType = documentType ?? current?.document_type ?? ''
    // Optimistically update cache
    set((state) => ({
      metadataCache: {
        ...state.metadataCache,
        [hash]: { description, document_type: newDocType },
      },
    }))
    try {
      await client.saveMetadata(hash, description, newDocType)
    } catch {
      // Keep optimistic update; server sync failed silently
    }
  },
}))
