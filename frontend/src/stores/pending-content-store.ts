import { create } from 'zustand'
import type { KnowledgeTreeQuestionType } from '../types/api'

export type PendingContentStatus = 'generating' | 'ready' | 'saving' | 'error'
export type PendingContentDisposition = 'approved' | 'rejected'

export interface PendingFlashcard {
  id: string
  kind: 'flashcard'
  status: PendingContentStatus
  disposition?: PendingContentDisposition
  chapter: number
  front: string
  back: string
  sourceText: string
  error?: string
}

export interface PendingQuestion {
  id: string
  kind: 'question'
  status: PendingContentStatus
  disposition?: PendingContentDisposition
  chapter: number
  questionType: KnowledgeTreeQuestionType
  questionData: Record<string, unknown>
  sourceText: string
  error?: string
}

export type PendingContent = PendingFlashcard | PendingQuestion

interface PendingContentState {
  items: PendingContent[]
  add: (item: PendingContent) => void
  update: (id: string, patch: Partial<PendingContent>) => void
  remove: (id: string) => void
  clearForDoc: () => void
}

export const usePendingContent = create<PendingContentState>((set) => ({
  items: [],
  add: (item) => set((s) => ({ items: [...s.items, item] })),
  update: (id, patch) =>
    set((s) => ({
      items: s.items.map((it) => (it.id === id ? ({ ...it, ...patch } as PendingContent) : it)),
    })),
  remove: (id) => set((s) => ({ items: s.items.filter((it) => it.id !== id) })),
  clearForDoc: () => set({ items: [] }),
}))

export function makePendingId() {
  return `pc-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}
