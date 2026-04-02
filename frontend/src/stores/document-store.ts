import { create } from 'zustand'
import { client } from '../services'
import type { DocumentOut, DocumentStructureOut, UpdateContentResponse } from '../types/api'

interface DocumentMetadata {
  description: string
  document_type: string
  file_extension: string
}

interface DocumentState {
  documents: DocumentOut[]
  loading: boolean
  structureCache: Record<string, DocumentStructureOut>
  metadataCache: Record<string, DocumentMetadata>
  contentCache: Record<string, string>
  fetchDocuments: () => Promise<void>
  fetchStructure: (hash: string) => Promise<void>
  setStructureCache: (hash: string, structure: DocumentStructureOut) => void
  removeDocument: (hash: string) => Promise<void>
  removeChapter: (hash: string, chapterNumber: number) => Promise<void>
  fetchMetadata: (hash: string) => Promise<void>
  saveMetadata: (hash: string, description: string, documentType?: string) => Promise<void>
  fetchContent: (hash: string) => Promise<string | null>
  updateContent: (hash: string, content: string) => Promise<UpdateContentResponse>
  clearContent: (hash: string) => void
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  loading: false,
  structureCache: {},
  metadataCache: {},
  contentCache: {},

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

  setStructureCache: (hash: string, structure: DocumentStructureOut) => {
    set((state) => ({
      structureCache: { ...state.structureCache, [hash]: structure },
    }))
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
          [hash]: { description: resp.description, document_type: resp.document_type, file_extension: resp.file_extension },
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
        [hash]: { description, document_type: newDocType, file_extension: current?.file_extension ?? '' },
      },
    }))
    try {
      await client.saveMetadata(hash, description, newDocType)
    } catch {
      // Keep optimistic update; server sync failed silently
    }
  },

  fetchContent: async (hash: string) => {
    const { contentCache } = get()
    if (contentCache[hash]) return contentCache[hash]
    try {
      const resp = await client.getDocumentContent(hash)
      set((state) => ({
        contentCache: { ...state.contentCache, [hash]: resp.content },
      }))
      return resp.content
    } catch {
      return null
    }
  },

  updateContent: async (hash: string, content: string) => {
    const resp = await client.updateDocumentContent(hash, content)
    // Clear caches on any content update (even if same hash)
    set((state) => {
      const { [hash]: _removed, ...rest } = state.contentCache
      return { contentCache: rest }
    })
    return resp
  },

  clearContent: (hash: string) => {
    set((state) => {
      const { [hash]: _removed, ...rest } = state.contentCache
      return { contentCache: rest }
    })
  },
}))
