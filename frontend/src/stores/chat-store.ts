import { create } from 'zustand'
import type { ChatMessage } from '../types/domain'

interface ChatState {
  /** Messages keyed by `${docHash}-${chapter}` */
  conversations: Record<string, ChatMessage[]>
  /** Loading state per conversation key */
  loading: Record<string, boolean>

  addUserMessage: (docHash: string, chapter: number, content: string) => string
  addAssistantMessage: (
    docHash: string,
    chapter: number,
    content: string,
    sources?: ChatMessage['sources']
  ) => void
  setLoading: (docHash: string, chapter: number, loading: boolean) => void
  clearConversation: (docHash: string, chapter: number) => void
}

function conversationKey(docHash: string, chapter: number): string {
  return `${docHash}-${chapter}`
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: {},
  loading: {},

  addUserMessage: (docHash: string, chapter: number, content: string): string => {
    const key = conversationKey(docHash, chapter)
    const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const message: ChatMessage = {
      id,
      role: 'user',
      content,
      timestamp: Date.now(),
    }
    set((state) => ({
      conversations: {
        ...state.conversations,
        [key]: [...(state.conversations[key] ?? []), message],
      },
    }))
    return id
  },

  addAssistantMessage: (
    docHash: string,
    chapter: number,
    content: string,
    sources?: ChatMessage['sources']
  ) => {
    const key = conversationKey(docHash, chapter)
    const message: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      role: 'assistant',
      content,
      sources,
      timestamp: Date.now(),
    }
    set((state) => ({
      conversations: {
        ...state.conversations,
        [key]: [...(state.conversations[key] ?? []), message],
      },
    }))
  },

  setLoading: (docHash: string, chapter: number, loading: boolean) => {
    const key = conversationKey(docHash, chapter)
    set((state) => ({
      loading: {
        ...state.loading,
        [key]: loading,
      },
    }))
  },

  clearConversation: (docHash: string, chapter: number) => {
    const key = conversationKey(docHash, chapter)
    set((state) => ({
      conversations: {
        ...state.conversations,
        [key]: [],
      },
    }))
  },
}))
