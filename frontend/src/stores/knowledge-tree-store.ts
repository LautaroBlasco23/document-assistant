import { create } from 'zustand'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument } from '../types/knowledge-tree'
import { client } from '../services'

interface KnowledgeTreeState {
  trees: KnowledgeTree[]
  treesLoading: boolean

  chapters: Record<string, KnowledgeChapter[]>
  chaptersLoading: Record<string, boolean>

  documents: Record<string, KnowledgeDocument[]>  // key: `${treeId}:${chapter ?? 'main'}`
  documentsLoading: Record<string, boolean>

  fetchTrees: () => Promise<void>
  createTree: (title: string, description?: string) => Promise<KnowledgeTree>
  updateTree: (id: string, title: string, description?: string) => Promise<KnowledgeTree>
  deleteTree: (id: string) => Promise<void>

  fetchChapters: (treeId: string) => Promise<void>
  createChapter: (treeId: string, title: string) => Promise<KnowledgeChapter>
  updateChapter: (treeId: string, chapterNumber: number, title: string) => Promise<KnowledgeChapter>
  deleteChapter: (treeId: string, chapterNumber: number) => Promise<void>

  fetchDocuments: (treeId: string, chapter: number | null, chapterId: string | null) => Promise<void>
  createDocument: (treeId: string, chapter: number | null, title: string, content: string, isMain?: boolean) => Promise<KnowledgeDocument>
  updateDocument: (id: string, title: string, content: string, treeId: string, chapter: number | null) => Promise<KnowledgeDocument>
  deleteDocument: (id: string, treeId: string, chapter: number | null) => Promise<void>
  ingestFileAsDocument: (treeId: string, chapter: number, file: File) => Promise<KnowledgeDocument>
  createTreeFromFile: (file: File, title?: string) => Promise<string>
}

function docKey(treeId: string, chapter: number | null) {
  return `${treeId}:${chapter ?? 'main'}`
}

export const useKnowledgeTreeStore = create<KnowledgeTreeState>((set, _get) => ({
  trees: [],
  treesLoading: false,
  chapters: {},
  chaptersLoading: {},
  documents: {},
  documentsLoading: {},

  fetchTrees: async () => {
    set({ treesLoading: true })
    try {
      const trees = await client.listKnowledgeTrees()
      set({ trees })
    } finally {
      set({ treesLoading: false })
    }
  },

  createTree: async (title, description) => {
    const tree = await client.createKnowledgeTree(title, description)
    set((s) => ({ trees: [...s.trees, tree] }))
    return tree
  },

  updateTree: async (id, title, description) => {
    const tree = await client.updateKnowledgeTree(id, title, description)
    set((s) => ({ trees: s.trees.map((t) => t.id === id ? tree : t) }))
    return tree
  },

  deleteTree: async (id) => {
    await client.deleteKnowledgeTree(id)
    set((s) => ({ trees: s.trees.filter((t) => t.id !== id) }))
  },

  fetchChapters: async (treeId) => {
    set((s) => ({ chaptersLoading: { ...s.chaptersLoading, [treeId]: true } }))
    try {
      const chapters = await client.getKnowledgeTreeChapters(treeId)
      set((s) => ({ chapters: { ...s.chapters, [treeId]: chapters } }))
    } finally {
      set((s) => ({ chaptersLoading: { ...s.chaptersLoading, [treeId]: false } }))
    }
  },

  createChapter: async (treeId, title) => {
    const chapter = await client.createKnowledgeChapter(treeId, title)
    set((s) => ({
      chapters: { ...s.chapters, [treeId]: [...(s.chapters[treeId] ?? []), chapter] },
      trees: s.trees.map((t) => t.id === treeId ? { ...t, num_chapters: t.num_chapters + 1 } : t),
    }))
    return chapter
  },

  updateChapter: async (treeId, chapterNumber, title) => {
    const chapter = await client.updateKnowledgeChapter(treeId, chapterNumber, title)
    set((s) => ({
      chapters: {
        ...s.chapters,
        [treeId]: (s.chapters[treeId] ?? []).map((c) => c.number === chapterNumber ? chapter : c),
      },
    }))
    return chapter
  },

  deleteChapter: async (treeId, chapterNumber) => {
    await client.deleteKnowledgeChapter(treeId, chapterNumber)
    set((s) => ({
      chapters: {
        ...s.chapters,
        [treeId]: (s.chapters[treeId] ?? []).filter((c) => c.number !== chapterNumber),
      },
      trees: s.trees.map((t) => t.id === treeId ? { ...t, num_chapters: Math.max(0, t.num_chapters - 1) } : t),
    }))
  },

  fetchDocuments: async (treeId, chapter, chapterId) => {
    const key = docKey(treeId, chapter)
    set((s) => ({ documentsLoading: { ...s.documentsLoading, [key]: true } }))
    try {
      const docs = await client.listKnowledgeDocuments(treeId, chapterId)
      set((s) => ({ documents: { ...s.documents, [key]: docs } }))
    } finally {
      set((s) => ({ documentsLoading: { ...s.documentsLoading, [key]: false } }))
    }
  },

  createDocument: async (treeId, chapter, title, content, isMain) => {
    const doc = await client.createKnowledgeDocument(treeId, chapter, title, content, isMain)
    const key = docKey(treeId, chapter)
    set((s) => ({ documents: { ...s.documents, [key]: [...(s.documents[key] ?? []), doc] } }))
    return doc
  },

  updateDocument: async (id, title, content, treeId, chapter) => {
    const doc = await client.updateKnowledgeDocument(id, title, content)
    const key = docKey(treeId, chapter)
    set((s) => ({
      documents: {
        ...s.documents,
        [key]: (s.documents[key] ?? []).map((d) => d.id === id ? doc : d),
      },
    }))
    return doc
  },

  deleteDocument: async (id, treeId, chapter) => {
    await client.deleteKnowledgeDocument(id)
    const key = docKey(treeId, chapter)
    set((s) => ({
      documents: {
        ...s.documents,
        [key]: (s.documents[key] ?? []).filter((d) => d.id !== id),
      },
    }))
  },

  ingestFileAsDocument: async (treeId, chapter, file) => {
    const doc = await client.ingestFileAsKnowledgeDocument(treeId, chapter, file)
    const key = docKey(treeId, chapter)
    set((s) => ({ documents: { ...s.documents, [key]: [...(s.documents[key] ?? []), doc] } }))
    return doc
  },

  createTreeFromFile: async (file, title) => {
    const { task_id } = await client.createKnowledgeTreeFromFile(file, title)
    return task_id
  },
}))

export { docKey }
