import ReactMarkdown from 'react-markdown'
import { cn } from '../../lib/cn'
import type { ChatMessage } from '../../types/domain'

interface ChatMessageProps {
  message: ChatMessage
}

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="bg-primary text-white rounded-2xl rounded-tr-none px-4 py-2 max-w-[80%] ml-auto text-sm">
          {message.content}
        </div>
      </div>
    )
  }

  const hasSources = (message.sources?.length ?? 0) > 0

  return (
    <div className="flex justify-start">
      <div className={cn(
        'bg-white border border-gray-100 rounded-2xl rounded-tl-none px-4 py-3 max-w-[80%] shadow-sm text-sm',
      )}>
        {message.content ? (
          <ReactMarkdown className="prose prose-sm max-w-none">
            {message.content}
          </ReactMarkdown>
        ) : (
          <ThinkingIndicator />
        )}

        {hasSources && (
          <details className="mt-3 pt-2 border-t border-gray-100">
            <summary className="text-xs text-gray-400 cursor-pointer select-none hover:text-gray-600 transition-colors">
              Sources ({message.sources!.length})
            </summary>
            <div className="mt-2 flex flex-col gap-2">
              {message.sources!.map((source) => (
                <div
                  key={source.id}
                  className="bg-surface-50 border border-gray-100 rounded-md p-2 text-xs"
                >
                  <p className="font-medium text-gray-600 mb-1">
                    Chapter {source.chapter}
                    {source.page !== undefined ? ` · Page ${source.page}` : ''}
                  </p>
                  <p className="text-gray-500 leading-relaxed">
                    {source.text.length > 150
                      ? source.text.slice(0, 150) + '...'
                      : source.text}
                  </p>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <span className="inline-flex items-center gap-0.5 text-gray-400">
      <span className="animate-bounce delay-0 h-1.5 w-1.5 rounded-full bg-gray-400" style={{ animationDelay: '0ms' }} />
      <span className="animate-bounce h-1.5 w-1.5 rounded-full bg-gray-400" style={{ animationDelay: '150ms' }} />
      <span className="animate-bounce h-1.5 w-1.5 rounded-full bg-gray-400" style={{ animationDelay: '300ms' }} />
    </span>
  )
}
