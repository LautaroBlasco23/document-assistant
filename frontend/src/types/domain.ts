// Frontend-only types (not mirroring backend schemas)

import type { FlashcardOut } from './api'

export interface FlashcardDeck {
  documentHash: string
  chapter: number
  cards: FlashcardOut[]
  generatedAt: string
}

export interface ReviewSession {
  deckIndex: string
  currentIndex: number
  scores: Record<number, 'easy' | 'medium' | 'hard'>
  isComplete: boolean
}

export type Tab = 'flashcards' | 'summary'
