// Frontend-only types (not mirroring backend schemas)

import type { FlashcardOut } from './api'

export interface FlashcardDeck {
  documentHash: string
  chapter: number
  cards: FlashcardOut[]
  generatedAt: string
  status?: 'pending' | 'approved'
}

export type ChapterLevel = 'none' | 'completed' | 'gold' | 'platinum'

export interface ExamSession {
  docHash: string
  chapter: number
  cards: FlashcardOut[]
  currentIndex: number
  results: Record<number, boolean>  // cardIndex -> correct/incorrect
  isComplete: boolean
}

export type Tab = 'flashcards' | 'summary' | 'exam'
