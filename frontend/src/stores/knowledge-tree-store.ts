import { create } from 'zustand'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument, ExamQuestion } from '../types/knowledge-tree'
import { mapApiQuestionToExamQuestion } from '../types/knowledge-tree'
import type { KnowledgeTreeQuestionType } from '../types/api'
import { client } from '../services'

// key: `${treeId}:${chapterNumber}`
type QuestionChapterKey = string

interface KnowledgeTreeState {
  trees: KnowledgeTree[]
  treesLoading: boolean
  treesFetched: boolean

  chapters: Record<string, KnowledgeChapter[]>
  chaptersLoading: Record<string, boolean>

  documents: Record<string, KnowledgeDocument[]>  // key: `${treeId}:${chapter ?? 'main'}`
  documentsLoading: Record<string, boolean>

  // Questions keyed by `${treeId}:${chapterNumber}`
  questionsByType: Record<QuestionChapterKey, Partial<Record<KnowledgeTreeQuestionType, ExamQuestion[]>>>
  questionsLoading: Record<QuestionChapterKey, boolean>
  // Task ids for question generation, keyed by `${treeId}:${chapterNumber}:${questionType}`
  questionTaskIds: Record<string, string>

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
  createTreeFromFile: (file: File, title?: string, chapterIndices?: number[]) => Promise<string>

  generateQuestions: (treeId: string, chapter: number, questionType: KnowledgeTreeQuestionType) => Promise<string>
  fetchQuestions: (treeId: string, chapter: number) => Promise<void>
  deleteQuestion: (treeId: string, chapter: number, questionId: string) => Promise<void>
}

function docKey(treeId: string, chapter: number | null) {
  return `${treeId}:${chapter ?? 'main'}`
}

function questionKey(treeId: string, chapter: number) {
  return `${treeId}:${chapter}`
}

function questionTaskKey(treeId: string, chapter: number, questionType: KnowledgeTreeQuestionType) {
  return `${treeId}:${chapter}:${questionType}`
}

export const useKnowledgeTreeStore = create<KnowledgeTreeState>((set, get) => ({
  trees: [],
  treesLoading: false,
  treesFetched: false,
  chapters: {},
  chaptersLoading: {},
  documents: {},
  documentsLoading: {},
  questionsByType: {},
  questionsLoading: {},
  questionTaskIds: {},

  fetchTrees: async () => {
    set({ treesLoading: true })
    try {
      const trees = await client.listKnowledgeTrees()
      set({ trees, treesFetched: true })
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
    const chapterId = chapter !== null
      ? (get().chapters[treeId] ?? []).find((c) => c.number === chapter)?.id ?? null
      : null
    const doc = await client.createKnowledgeDocument(treeId, chapterId, title, content, isMain)
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

  createTreeFromFile: async (file, title, chapterIndices) => {
    const { task_id } = await client.createKnowledgeTreeFromFile(file, title, chapterIndices)
    return task_id
  },

  generateQuestions: async (treeId, chapter, questionType) => {
    const { task_id } = await client.generateKnowledgeTreeQuestions(treeId, chapter, [questionType])
    const taskKey = questionTaskKey(treeId, chapter, questionType)
    set((s) => ({ questionTaskIds: { ...s.questionTaskIds, [taskKey]: task_id } }))
    return task_id
  },

  fetchQuestions: async (treeId, chapter) => {
    const key = questionKey(treeId, chapter)
    set((s) => ({ questionsLoading: { ...s.questionsLoading, [key]: true } }))
    try {
      const raw = await client.getKnowledgeTreeQuestions(treeId, chapter)
      const byType: Partial<Record<KnowledgeTreeQuestionType, ExamQuestion[]>> = {
        true_false: [],
        multiple_choice: [],
        matching: [],
        checkbox: [],
      }
      for (const q of raw) {
        const mapped = mapApiQuestionToExamQuestion(q)
        if (mapped) {
          const bucket = byType[q.question_type]
          if (bucket) bucket.push(mapped)
        }
      }
      set((s) => ({
        questionsByType: { ...s.questionsByType, [key]: byType },
      }))
    } finally {
      set((s) => ({ questionsLoading: { ...s.questionsLoading, [key]: false } }))
    }
  },

  deleteQuestion: async (treeId, chapter, questionId) => {
    await client.deleteKnowledgeTreeQuestion(treeId, chapter, questionId)
    const key = questionKey(treeId, chapter)
    set((s) => {
      const existing = s.questionsByType[key]
      if (!existing) return s
      const updated: Partial<Record<KnowledgeTreeQuestionType, ExamQuestion[]>> = {}
      for (const [type, questions] of Object.entries(existing) as [KnowledgeTreeQuestionType, ExamQuestion[]][]) {
        updated[type] = questions.filter((q) => q.id !== questionId)
      }
      return { questionsByType: { ...s.questionsByType, [key]: updated } }
    })
    // Rehydrate from server to ensure consistency
    void get().fetchQuestions(treeId, chapter)
  },
}))

export { docKey, questionKey, questionTaskKey }
