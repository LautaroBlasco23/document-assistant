import { create } from 'zustand'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument, ExamQuestion, ExamSession, CreateExamSessionPayload, StudySession, CreateStudySessionPayload } from '../types/knowledge-tree'
import { mapApiQuestionToExamQuestion } from '../types/knowledge-tree'
import type { KnowledgeTreeQuestionType, FlashcardOut } from '../types/api'
import { client } from '../services'
import { useGenerationSettings } from './generation-settings'
import { LIMITS_INVALIDATE_EVENT } from './app-store'

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

  // Flashcards keyed by `${treeId}:${chapterNumber}`
  flashcardsByChapter: Record<QuestionChapterKey, FlashcardOut[]>
  flashcardsLoading: Record<QuestionChapterKey, boolean>

  // Exam sessions keyed by `${treeId}:${chapterNumber}`
  examSessionsByChapter: Record<QuestionChapterKey, ExamSession[]>
  examSessionsLoading: Record<QuestionChapterKey, boolean>

  // Study sessions keyed by `${treeId}:${chapterNumber}`
  studySessionsByChapter: Record<QuestionChapterKey, StudySession[]>
  studySessionsLoading: Record<QuestionChapterKey, boolean>

  fetchTrees: () => Promise<void>
  createTree: (title: string, description?: string) => Promise<KnowledgeTree>
  updateTree: (id: string, title: string, description?: string) => Promise<KnowledgeTree>
  deleteTree: (id: string) => Promise<void>

  fetchChapters: (treeId: string) => Promise<void>
  createChapter: (treeId: string, title: string) => Promise<KnowledgeChapter>
  updateChapter: (treeId: string, chapterNumber: number, title: string) => Promise<KnowledgeChapter>
  deleteChapter: (treeId: string, chapterNumber: number) => Promise<void>
  deleteChapters: (treeId: string, chapterNumbers: number[]) => Promise<void>

  fetchDocuments: (treeId: string, chapter: number | null, chapterId: string | null) => Promise<void>
  fetchAllDocuments: (treeId: string) => Promise<void>
  createDocument: (treeId: string, chapter: number | null, title: string, content: string, isMain?: boolean) => Promise<KnowledgeDocument>
  updateDocument: (id: string, title: string, content: string, treeId: string, chapter: number | null, fileType?: string | null, originalContent?: string | null) => Promise<KnowledgeDocument>
  deleteDocument: (id: string, treeId: string, chapter: number | null) => Promise<void>
  improveDocument: (treeId: string, docId: string, chapter: number | null, mode?: 'text' | 'formatting') => Promise<string>
  revertDocument: (treeId: string, docId: string, chapter: number | null) => Promise<KnowledgeDocument>
  applyImproveResult: (treeId: string, chapter: number | null, docId: string, result: Record<string, unknown>) => void
  splitChapter: (treeId: string, chapterNumber: number, chapters: { page_start: number; page_end: number; title?: string | null }[]) => Promise<{ chapters: KnowledgeChapter[] }>
  ingestFileAsDocument: (treeId: string, chapter: number, file: File) => Promise<{ task_id: string }>
  importYouTubeDocument: (treeId: string, url: string, chapterId?: string | null) => Promise<{ task_id: string }>
  createTreeFromFile: (file: File, title?: string, chapterIndices?: number[]) => Promise<string>

  generateQuestions: (treeId: string, chapter: number, questionType: KnowledgeTreeQuestionType, numQuestions?: number | null) => Promise<string>
  fetchQuestions: (treeId: string, chapter: number) => Promise<void>
  deleteQuestion: (treeId: string, chapter: number, questionId: string) => Promise<void>
  deleteAllQuestions: (treeId: string, chapter: number, questionType?: KnowledgeTreeQuestionType) => Promise<void>

  generateFlashcards: (treeId: string, chapter: number, numFlashcards?: number | null) => Promise<string>
  fetchFlashcards: (treeId: string, chapter: number) => Promise<void>
  deleteFlashcard: (treeId: string, chapter: number, flashcardId: string) => Promise<void>
  deleteAllFlashcards: (treeId: string, chapter: number) => Promise<void>

  saveExamSession: (treeId: string, chapter: number, payload: CreateExamSessionPayload) => Promise<ExamSession>
  fetchExamSessions: (treeId: string, chapter: number) => Promise<void>

  markChapterRead: (treeId: string, chapterNumber: number) => Promise<void>

  saveStudySession: (treeId: string, chapter: number, payload: CreateStudySessionPayload) => Promise<StudySession>
  fetchStudySessions: (treeId: string, chapter: number) => Promise<void>
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

function invalidateLimits() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(LIMITS_INVALIDATE_EVENT))
  }
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
  flashcardsByChapter: {},
  flashcardsLoading: {},
  examSessionsByChapter: {},
  examSessionsLoading: {},
  studySessionsByChapter: {},
  studySessionsLoading: {},

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
    invalidateLimits()
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
    invalidateLimits()
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

  deleteChapters: async (treeId, chapterNumbers) => {
    const deleted = new Set(chapterNumbers)
    await client.deleteKnowledgeChapters(treeId, chapterNumbers)
    set((s) => ({
      chapters: {
        ...s.chapters,
        [treeId]: (s.chapters[treeId] ?? []).filter((c) => !deleted.has(c.number)),
      },
      trees: s.trees.map((t) => t.id === treeId ? { ...t, num_chapters: Math.max(0, t.num_chapters - chapterNumbers.length) } : t),
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

  fetchAllDocuments: async (treeId) => {
    const key = `${treeId}:all`
    set((s) => ({ documentsLoading: { ...s.documentsLoading, [key]: true } }))
    try {
      const docs = await client.listKnowledgeDocuments(treeId)
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
    invalidateLimits()
    return doc
  },

  updateDocument: async (id, title, content, treeId, chapter, fileType, originalContent) => {
    const doc = await client.updateKnowledgeDocument(treeId, id, title, content, fileType, originalContent)
    const key = docKey(treeId, chapter)
    const allKey = `${treeId}:all`
    set((s) => ({
      documents: {
        ...s.documents,
        [key]: (s.documents[key] ?? []).map((d) => d.id === id ? doc : d),
        [allKey]: (s.documents[allKey] ?? []).map((d) => d.id === id ? doc : d),
      },
    }))
    return doc
  },

  deleteDocument: async (id, treeId, chapter) => {
    await client.deleteKnowledgeDocument(treeId, id)
    const key = docKey(treeId, chapter)
    set((s) => ({
      documents: {
        ...s.documents,
        [key]: (s.documents[key] ?? []).filter((d) => d.id !== id),
      },
    }))
    invalidateLimits()
  },

  improveDocument: async (treeId, docId, _chapter, mode = 'text') => {
    const { agent_id } = useGenerationSettings.getState().settings
    const { task_id } = await client.improveKnowledgeDocument(treeId, docId, agent_id, mode)
    return task_id
  },

  applyImproveResult: (treeId, chapter, docId, result) => {
    const doc = result as unknown as KnowledgeDocument
    const key = docKey(treeId, chapter)
    const allKey = `${treeId}:all`
    set((s) => ({
      documents: {
        ...s.documents,
        [key]: (s.documents[key] ?? []).map((d) => d.id === docId ? doc : d),
        [allKey]: (s.documents[allKey] ?? []).map((d) => d.id === docId ? doc : d),
      },
    }))
  },

  revertDocument: async (treeId, docId, chapter) => {
    const doc = await client.revertKnowledgeDocument(treeId, docId)
    const key = docKey(treeId, chapter)
    const allKey = `${treeId}:all`
    set((s) => ({
      documents: {
        ...s.documents,
        [key]: (s.documents[key] ?? []).map((d) => d.id === docId ? doc : d),
        [allKey]: (s.documents[allKey] ?? []).map((d) => d.id === docId ? doc : d),
      },
    }))
    return doc
  },

  splitChapter: async (treeId, chapterNumber, chapters) => {
    const result = await client.splitKnowledgeChapter(treeId, chapterNumber, chapters)
    await get().fetchChapters(treeId)
    await get().fetchDocuments(treeId, chapterNumber, null)
    return result
  },

  ingestFileAsDocument: async (treeId, chapter, file) => {
    return client.ingestFileAsKnowledgeDocument(treeId, chapter, file)
  },

  importYouTubeDocument: async (treeId, url, chapterId) => {
    return client.importYouTubeDocument(treeId, url, chapterId)
  },

  createTreeFromFile: async (file, title, chapterIndices) => {
    const { task_id } = await client.createKnowledgeTreeFromFile(file, title, chapterIndices)
    return task_id
  },

  generateQuestions: async (treeId, chapter, questionType, numQuestions = undefined) => {
    const { model, agent_id } = useGenerationSettings.getState().settings
    const { task_id } = await client.generateKnowledgeTreeQuestions(treeId, chapter, [questionType], model, agent_id, numQuestions)
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
    get().fetchQuestions(treeId, chapter).catch(
      (err) => console.error('Failed to refetch questions:', err),
    )
  },

  deleteAllQuestions: async (treeId, chapter, questionType) => {
    await client.deleteAllKnowledgeTreeQuestions(treeId, chapter, questionType)
    await get().fetchQuestions(treeId, chapter)
  },

  generateFlashcards: async (treeId, chapter, numFlashcards = undefined) => {
    const { model, agent_id } = useGenerationSettings.getState().settings
    const { task_id } = await client.generateChapterFlashcards(treeId, chapter, numFlashcards, model, agent_id)
    return task_id
  },

  fetchFlashcards: async (treeId, chapter) => {
    const key = questionKey(treeId, chapter)
    set((s) => ({ flashcardsLoading: { ...s.flashcardsLoading, [key]: true } }))
    try {
      const cards = await client.listChapterFlashcards(treeId, chapter)
      set((s) => ({ flashcardsByChapter: { ...s.flashcardsByChapter, [key]: cards } }))
    } finally {
      set((s) => ({ flashcardsLoading: { ...s.flashcardsLoading, [key]: false } }))
    }
  },

  deleteFlashcard: async (treeId, chapter, flashcardId) => {
    await client.deleteKnowledgeTreeFlashcard(treeId, chapter, flashcardId)
    const key = questionKey(treeId, chapter)
    set((s) => ({
      flashcardsByChapter: {
        ...s.flashcardsByChapter,
        [key]: (s.flashcardsByChapter[key] ?? []).filter((f) => f.id !== flashcardId),
      },
    }))
  },

  deleteAllFlashcards: async (treeId, chapter) => {
    await client.deleteAllKnowledgeTreeFlashcards(treeId, chapter)
    const key = questionKey(treeId, chapter)
    set((s) => ({ flashcardsByChapter: { ...s.flashcardsByChapter, [key]: [] } }))
  },

  saveExamSession: async (treeId, chapter, payload) => {
    const session = await client.saveExamSession(treeId, chapter, payload)
    const key = questionKey(treeId, chapter)
    set((s) => ({
      examSessionsByChapter: {
        ...s.examSessionsByChapter,
        [key]: [session, ...(s.examSessionsByChapter[key] ?? [])],
      },
    }))
    return session
  },

  fetchExamSessions: async (treeId, chapter) => {
    const key = questionKey(treeId, chapter)
    set((s) => ({ examSessionsLoading: { ...s.examSessionsLoading, [key]: true } }))
    try {
      const sessions = await client.listExamSessions(treeId, chapter)
      set((s) => ({ examSessionsByChapter: { ...s.examSessionsByChapter, [key]: sessions } }))
    } finally {
      set((s) => ({ examSessionsLoading: { ...s.examSessionsLoading, [key]: false } }))
    }
  },

  markChapterRead: async (treeId, chapterNumber) => {
    await client.markKnowledgeChapterRead(treeId, chapterNumber)
    set((s) => ({
      chapters: {
        ...s.chapters,
        [treeId]: (s.chapters[treeId] ?? []).map((c) =>
          c.number === chapterNumber ? { ...c, status: 'read' } : c
        ),
      },
    }))
  },

  saveStudySession: async (treeId, chapter, payload) => {
    const session = await client.saveStudySession(treeId, chapter, payload)
    const key = questionKey(treeId, chapter)
    set((s) => ({
      studySessionsByChapter: {
        ...s.studySessionsByChapter,
        [key]: [session, ...(s.studySessionsByChapter[key] ?? [])],
      },
    }))
    return session
  },

  fetchStudySessions: async (treeId, chapter) => {
    const key = questionKey(treeId, chapter)
    set((s) => ({ studySessionsLoading: { ...s.studySessionsLoading, [key]: true } }))
    try {
      const sessions = await client.listStudySessions(treeId, chapter)
      set((s) => ({ studySessionsByChapter: { ...s.studySessionsByChapter, [key]: sessions } }))
    } finally {
      set((s) => ({ studySessionsLoading: { ...s.studySessionsLoading, [key]: false } }))
    }
  },
}))

export { docKey, questionKey, questionTaskKey }
