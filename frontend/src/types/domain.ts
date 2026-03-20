// Frontend-only types (not mirroring backend schemas)

import type { ChunkOut, FlashcardOut } from './api'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: ChunkOut[]
  timestamp: number
}

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

export type Tab = 'chat' | 'qa' | 'flashcards' | 'summary'

export interface SSEEvent {
  type: string
  data: Record<string, unknown>
}
