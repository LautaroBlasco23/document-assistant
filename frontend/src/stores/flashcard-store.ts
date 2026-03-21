import { create } from 'zustand'
import type { FlashcardDeck, ReviewSession } from '../types/domain'

// TODO: Upgrade to SM-2 spaced repetition scheduling.
// SM-2 requires: nextReviewAt (Date), interval (days), easeFactor (float, 2.5 default).
// scoreCard() would compute: new interval = old interval * easeFactor (adjusted by score),
// new easeFactor = easeFactor - 0.8 + 0.28*quality - 0.02*quality^2 (where quality: easy=5, medium=3, hard=1).
// This requires persisting review history per card (localStorage or backend).

interface FlashcardState {
  /** Keyed by `${docHash}-${chapter}` */
  decks: Record<string, FlashcardDeck[]>
  activeReview: ReviewSession | null
  addDeck: (docHash: string, chapter: number, deck: FlashcardDeck) => void
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

  addDeck: (docHash: string, chapter: number, deck: FlashcardDeck) => {
    const key = deckKey(docHash, chapter)
    set((state) => ({
      decks: {
        ...state.decks,
        [key]: [...(state.decks[key] ?? []), deck],
      },
    }))
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
