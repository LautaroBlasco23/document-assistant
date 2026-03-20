import { create } from 'zustand'
import { client } from '../services'
import type { ChatMessage } from '../types/domain'
import type { ChunkOut } from '../types/api'

interface ChatState {
  histories: Record<string, ChatMessage[]>
  isStreaming: boolean
  error: string | null
  sendMessage: (docHash: string, query: string, chapter?: number) => Promise<void>
  clearHistory: (docHash: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  histories: {},
  isStreaming: false,
  error: null,

  sendMessage: async (docHash: string, query: string, chapter?: number) => {
    // 1. Append user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    set((state) => ({
      histories: {
        ...state.histories,
        [docHash]: [...(state.histories[docHash] ?? []), userMessage],
      },
    }))

    // 2. Set streaming state
    set({ isStreaming: true, error: null })

    // 3. Append empty assistant placeholder
    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: Date.now(),
    }
    set((state) => ({
      histories: {
        ...state.histories,
        [docHash]: [...(state.histories[docHash] ?? []), assistantMessage],
      },
    }))

    try {
      // 4. Stream tokens and accumulate into the last (assistant) message
      await client.streamAsk(query, chapter, (event) => {
        if (event.type === 'token') {
          const token = event.data.token as string
          set((state) => {
            const history = state.histories[docHash] ?? []
            const updated = [...history]
            const lastIndex = updated.length - 1
            if (lastIndex >= 0 && updated[lastIndex].role === 'assistant') {
              updated[lastIndex] = {
                ...updated[lastIndex],
                content: updated[lastIndex].content + token,
              }
            }
            return { histories: { ...state.histories, [docHash]: updated } }
          })
        } else if (event.type === 'done') {
          const sources = (event.data.sources ?? []) as ChunkOut[]
          set((state) => {
            const history = state.histories[docHash] ?? []
            const updated = [...history]
            const lastIndex = updated.length - 1
            if (lastIndex >= 0 && updated[lastIndex].role === 'assistant') {
              updated[lastIndex] = {
                ...updated[lastIndex],
                sources,
              }
            }
            return { histories: { ...state.histories, [docHash]: updated } }
          })
        }
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred'
      set({ error: message })
    } finally {
      set({ isStreaming: false })
    }
  },

  clearHistory: (docHash: string) => {
    // Read current histories via get() and rebuild without the given docHash
    const current = get().histories
    const updated: Record<string, ChatMessage[]> = {}
    for (const key of Object.keys(current)) {
      if (key !== docHash) {
        updated[key] = current[key]
      }
    }
    set({ histories: updated })
  },
}))
