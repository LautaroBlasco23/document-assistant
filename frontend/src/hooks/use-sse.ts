import { useChatStore } from '../stores/chat-store'

/**
 * Exposes streaming state from the chat store for components that only need to
 * read stream status without subscribing to the full chat history.
 * Actual streaming is handled internally by chatStore.sendMessage().
 */
export function useSSE(): { isStreaming: boolean; error: string | null } {
  const isStreaming = useChatStore((state) => state.isStreaming)
  const error = useChatStore((state) => state.error)
  return { isStreaming, error }
}
