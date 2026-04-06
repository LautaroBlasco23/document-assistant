import { useEffect, useRef, useState } from 'react'
import { MessageCircle, Trash2 } from 'lucide-react'
import { client } from '../../services'
import { useChatStore } from '../../stores/chat-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { cn } from '../../lib/cn'
import type { DocumentStructureOut } from '../../types/api'

interface ChatTabProps {
  docHash: string
  chapter: number
  chapterIndex: number
  structure: DocumentStructureOut | null
}

export function ChatTab({ docHash, chapter, chapterIndex }: ChatTabProps) {
  const conversationKey = `${docHash}-${chapter}`

  const conversations = useChatStore((s) => s.conversations)
  const loading = useChatStore((s) => s.loading)
  const addUserMessage = useChatStore((s) => s.addUserMessage)
  const addAssistantMessage = useChatStore((s) => s.addAssistantMessage)
  const setLoading = useChatStore((s) => s.setLoading)
  const clearConversation = useChatStore((s) => s.clearConversation)

  const messages = conversations[conversationKey] ?? []
  const isLoading = loading[conversationKey] ?? false

  const [query, setQuery] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to the bottom whenever messages change or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isLoading])

  const handleSend = async () => {
    const trimmed = query.trim()
    if (!trimmed || isLoading) return

    setQuery('')
    addUserMessage(docHash, chapter, trimmed)
    setLoading(docHash, chapter, true)

    // Build history from the last 6 messages (before the new user message)
    const history = messages
      .slice(-6)
      .map((msg) => ({ role: msg.role, content: msg.content }))

    try {
      const response = await client.chat(docHash, trimmed, chapter, chapterIndex, history)
      addAssistantMessage(docHash, chapter, response.answer, response.sources)
    } catch {
      addAssistantMessage(
        docHash,
        chapter,
        'Sorry, something went wrong. Please try again.',
        undefined
      )
    } finally {
      setLoading(docHash, chapter, false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      {messages.length > 0 && (
        <div className="flex justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => clearConversation(docHash, chapter)}
            className="text-gray-400 hover:text-red-500 hover:bg-red-50 text-xs gap-1"
          >
            <Trash2 className="h-3 w-3" />
            Clear chat
          </Button>
        </div>
      )}

      {/* Message list */}
      {messages.length === 0 && !isLoading ? (
        <EmptyState
          icon={MessageCircle}
          title="Ask a question"
          description="Ask anything about this chapter and the AI will answer based on the document content."
        />
      ) : (
        <div className="flex flex-col gap-3 max-h-[500px] overflow-y-auto pr-1">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'flex flex-col gap-1',
                msg.role === 'user' ? 'items-end' : 'items-start'
              )}
            >
              <div
                className={cn(
                  'rounded-lg px-3 py-2 text-sm max-w-[85%] whitespace-pre-wrap',
                  msg.role === 'user'
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-800'
                )}
              >
                {msg.content}
              </div>

              {/* Sources for assistant messages */}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <SourceList sources={msg.sources} />
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-start">
              <div className="bg-gray-100 rounded-lg px-3 py-2">
                <LoadingDots />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input area */}
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
          rows={2}
          placeholder="Ask a question about this chapter... (Enter to send, Shift+Enter for newline)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <Button
          variant="primary"
          size="sm"
          onClick={() => void handleSend()}
          disabled={isLoading || !query.trim()}
          loading={isLoading}
          className="shrink-0"
        >
          Send
        </Button>
      </div>
    </div>
  )
}

interface Source {
  page_number: number | null
  text_preview: string
}

function SourceList({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="max-w-[85%] w-full">
      <button
        className="text-xs text-gray-400 hover:text-gray-600 underline underline-offset-2"
        onClick={() => setExpanded((prev) => !prev)}
      >
        {expanded ? 'Hide sources' : `Show ${sources.length} source${sources.length !== 1 ? 's' : ''}`}
      </button>
      {expanded && (
        <div className="mt-1 flex flex-col gap-1">
          {sources.map((src, i) => (
            <div
              key={i}
              className="text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded px-2 py-1"
            >
              {src.page_number != null && (
                <span className="font-medium text-gray-600 mr-1">[p.{src.page_number}]</span>
              )}
              {src.text_preview}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function LoadingDots() {
  return (
    <span className="flex gap-1 items-center h-4">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  )
}
