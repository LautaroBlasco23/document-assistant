import { create } from 'zustand'
import { client } from '../services'
import type { ChapterExamStatusOut, FlashcardOut } from '../types/api'
import type { ExamSession } from '../types/domain'

interface ExamState {
  /** Active exam session (null when not in exam) */
  activeExam: ExamSession | null

  /** Keyed by `${docHash}-${chapter}` */
  chapterStatus: Record<string, ChapterExamStatusOut>

  startExam: (docHash: string, chapter: number, cards: FlashcardOut[]) => void
  answerCard: (correct: boolean) => void
  completeExam: () => Promise<void>
  cancelExam: () => void
  fetchChapterStatus: (docHash: string) => Promise<void>
  fetchSingleChapterStatus: (docHash: string, chapter: number) => Promise<void>
  clearChapterStatus: (docHash: string, chapter: number) => void
}

function statusKey(docHash: string, chapter: number): string {
  return `${docHash}-${chapter}`
}

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

export const useExamStore = create<ExamState>((set, get) => ({
  activeExam: null,
  chapterStatus: {},

  startExam: (docHash: string, chapter: number, cards: FlashcardOut[]) => {
    const shuffledCards = shuffleArray(cards)
    set({
      activeExam: {
        docHash,
        chapter,
        cards: shuffledCards,
        currentIndex: 0,
        results: {},
        isComplete: false,
      },
    })
  },

  answerCard: (correct: boolean) => {
    const { activeExam } = get()
    if (!activeExam || activeExam.isComplete) return

    const newResults = { ...activeExam.results, [activeExam.currentIndex]: correct }
    const nextIndex = activeExam.currentIndex + 1
    const isComplete = nextIndex >= activeExam.cards.length

    set({
      activeExam: {
        ...activeExam,
        results: newResults,
        currentIndex: nextIndex,
        isComplete,
      },
    })
  },

  completeExam: async () => {
    const { activeExam } = get()
    if (!activeExam || !activeExam.isComplete) return

    const correctCount = Object.values(activeExam.results).filter(Boolean).length
    const totalCards = activeExam.cards.length

    try {
      await client.submitExamResult(
        activeExam.docHash,
        activeExam.chapter,
        totalCards,
        correctCount,
      )
      // Refresh status to get updated level and cooldown
      await get().fetchSingleChapterStatus(activeExam.docHash, activeExam.chapter)
    } finally {
      set({ activeExam: null })
    }
  },

  cancelExam: () => {
    set({ activeExam: null })
  },

  fetchChapterStatus: async (docHash: string) => {
    const statuses = await client.getExamStatus(docHash)
    set((state) => {
      const updated = { ...state.chapterStatus }
      for (const s of statuses) {
        updated[statusKey(docHash, s.chapter)] = s
      }
      return { chapterStatus: updated }
    })
  },

  fetchSingleChapterStatus: async (docHash: string, chapter: number) => {
    const status = await client.getExamStatusForChapter(docHash, chapter)
    set((state) => ({
      chapterStatus: {
        ...state.chapterStatus,
        [statusKey(docHash, chapter)]: status,
      },
    }))
  },

  clearChapterStatus: (docHash: string, chapter: number) => {
    const key = statusKey(docHash, chapter)
    set((state) => {
      const updated = { ...state.chapterStatus }
      delete updated[key]
      return { chapterStatus: updated }
    })
  },
}))
