import { create } from 'zustand'
import type { FlashcardDeck } from '../types/domain'

interface FlashcardState {
  /** Approved decks, keyed by `${docHash}-${chapter}` */
  decks: Record<string, FlashcardDeck[]>
  /** Pending decks awaiting review, keyed by `${docHash}-${chapter}` */
  pendingDecks: Record<string, FlashcardDeck | null>

  addDeck: (docHash: string, chapter: number, deck: FlashcardDeck) => void
  setPendingDeck: (docHash: string, chapter: number, deck: FlashcardDeck) => void
  clearPendingDeck: (docHash: string, chapter: number) => void
  /** Remove specific card IDs from the pending deck (after rejection) */
  removePendingCards: (docHash: string, chapter: number, cardIds: string[]) => void
}

function deckKey(docHash: string, chapter: number): string {
  return `${docHash}-${chapter}`
}

export const useFlashcardStore = create<FlashcardState>((set) => ({
  decks: {},
  pendingDecks: {},

  addDeck: (docHash: string, chapter: number, deck: FlashcardDeck) => {
    const key = deckKey(docHash, chapter)
    set((state) => ({
      decks: {
        ...state.decks,
        [key]: [deck],
      },
    }))
  },

  setPendingDeck: (docHash: string, chapter: number, deck: FlashcardDeck) => {
    const key = deckKey(docHash, chapter)
    set((state) => ({
      pendingDecks: {
        ...state.pendingDecks,
        [key]: deck,
      },
    }))
  },

  clearPendingDeck: (docHash: string, chapter: number) => {
    const key = deckKey(docHash, chapter)
    set((state) => ({
      pendingDecks: {
        ...state.pendingDecks,
        [key]: null,
      },
    }))
  },

  removePendingCards: (docHash: string, chapter: number, cardIds: string[]) => {
    const key = deckKey(docHash, chapter)
    const idSet = new Set(cardIds)
    set((state) => {
      const pending = state.pendingDecks[key]
      if (!pending) return state
      const remaining = pending.cards.filter((c) => !idSet.has(c.id ?? ''))
      return {
        pendingDecks: {
          ...state.pendingDecks,
          [key]: remaining.length > 0 ? { ...pending, cards: remaining } : null,
        },
      }
    })
  },
}))
