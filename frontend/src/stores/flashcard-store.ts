import { create } from 'zustand'
import { client } from '../services'
import type { FlashcardDeck, ReviewSession } from '../types/domain'
import type { FlashcardOut } from '../types/api'

// TODO: Upgrade to SM-2 spaced repetition scheduling.
// SM-2 requires: nextReviewAt (Date), interval (days), easeFactor (float, 2.5 default).
// scoreCard() would compute: new interval = old interval * easeFactor (adjusted by score),
// new easeFactor = easeFactor - 0.8 + 0.28*quality - 0.02*quality^2 (where quality: easy=5, medium=3, hard=1).
// This requires persisting review history per card (localStorage or backend).

interface FlashcardState {
  /** Keyed by `${docHash}-${chapter}` */
  decks: Record<string, FlashcardDeck[]>
  activeReview: ReviewSession | null
  generateDeck: (docHash: string, chapter: number, bookTitle: string) => Promise<void>
  startReview: (docHash: string, chapter: number) => void
  scoreCard: (score: 'easy' | 'medium' | 'hard') => void
  nextCard: () => void
  endReview: () => void
}

function deckKey(docHash: string, chapter: number): string {
  return `${docHash}-${chapter}`
}

export const useFlashcardStore = create<FlashcardState>((set, get) => ({
  decks: {},
  activeReview: null,

  generateDeck: async (docHash: string, chapter: number, bookTitle: string) => {
    const response = await client.generateFlashcards(chapter, bookTitle)
    const taskId = response.task_id

    await new Promise<void>((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await client.getTaskStatus(taskId)

          if (status.status === 'completed') {
            clearInterval(interval)

            // Extract flashcards from task result.
            // Real backend returns { flashcards: FlashcardOut[] }; mock returns { message: 'Done' }.
            // Fall back to an empty array if the result doesn't include flashcards.
            const flashcards = (
              (status.result?.flashcards as FlashcardOut[] | undefined) ?? []
            )

            const deck: FlashcardDeck = {
              documentHash: docHash,
              chapter,
              cards: flashcards,
              generatedAt: new Date().toISOString(),
            }

            const key = deckKey(docHash, chapter)
            set((state) => ({
              decks: {
                ...state.decks,
                [key]: [...(state.decks[key] ?? []), deck],
              },
            }))

            resolve()
          } else if (status.status === 'failed') {
            clearInterval(interval)
            reject(new Error(status.error ?? 'Flashcard generation failed'))
          }
        } catch (err) {
          clearInterval(interval)
          reject(err)
        }
      }, 1500)
    })
  },

  startReview: (docHash: string, chapter: number) => {
    set({
      activeReview: {
        deckIndex: deckKey(docHash, chapter),
        currentIndex: 0,
        scores: {},
        isComplete: false,
      },
    })
  },

  scoreCard: (score: 'easy' | 'medium' | 'hard') => {
    const { activeReview } = get()
    if (!activeReview) return
    set({
      activeReview: {
        ...activeReview,
        scores: { ...activeReview.scores, [activeReview.currentIndex]: score },
      },
    })
  },

  nextCard: () => {
    const { activeReview, decks } = get()
    if (!activeReview) return

    const deck = (decks[activeReview.deckIndex] ?? [])[0]
    const totalCards = deck?.cards.length ?? 0
    const nextIndex = activeReview.currentIndex + 1
    const isComplete = nextIndex >= totalCards

    set({
      activeReview: {
        ...activeReview,
        currentIndex: nextIndex,
        isComplete,
      },
    })
  },

  endReview: () => {
    set({ activeReview: null })
  },
}))
