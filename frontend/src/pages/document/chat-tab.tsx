import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { MessageCircle, Send } from 'lucide-react'
import { useChatStore } from '../../stores/chat-store'
import { Button } from '../../components/ui/button'
import { ChatMessageBubble } from './chat-message'

interface ChatTabProps {
  docHash: string
  chapter?: number
}

const EXAMPLE_QUESTIONS = [
  'What is the main idea of this chapter?',
  'Can you summarize the key concepts?',
  'What are the most important takeaways?',
]

export function ChatTab({ docHash, chapter }: ChatTabProps) {
  const histories = useChatStore((state) => state.histories)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const sendMessage = useChatStore((state) => state.sendMessage)

  const messages = histories[docHash] ?? []
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, messages[messages.length - 1]?.content])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    setInput('')
    void sendMessage(docHash, trimmed, chapter)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleExampleClick = (question: string) => {
    setInput(question)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-280px)] min-h-[400px]">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto py-4 px-1 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <MessageCircle className="h-12 w-12 text-gray-200" />
            <div>
              <p className="font-medium text-gray-500">Ask a question about this document</p>
              <p className="text-sm text-gray-400 mt-1">
                {chapter !== undefined
                  ? `Searching in chapter ${chapter}`
                  : 'Searching across all chapters'}
              </p>
            </div>
            <div className="flex flex-col gap-2 w-full max-w-sm">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleExampleClick(q)}
                  className="text-sm text-left px-3 py-2 rounded-lg border border-gray-200 bg-white hover:bg-surface-50 hover:border-primary text-gray-600 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <ChatMessageBubble key={index} message={message} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-100 pt-3 pb-1">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isStreaming
                ? 'Waiting for response...'
                : chapter !== undefined
                  ? `Ask about chapter ${chapter}...`
                  : 'Ask a question...'
            }
            disabled={isStreaming}
            rows={1}
            className="flex-1 resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ maxHeight: '120px', overflowY: 'auto' }}
          />
          <Button
            variant="primary"
            size="sm"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            aria-label="Send message"
            className="shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
