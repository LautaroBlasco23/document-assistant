import { useState } from 'react'
import { useSSE } from '@/hooks/useSSE'

interface SSEEvent {
  type: string
  data: Record<string, unknown>
}

export default function AskQuestion() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { stream } = useSSE()

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setAnswer('')
    setError(null)
    setIsStreaming(true)

    try {
      let fullAnswer = ''

      await stream(
        '/api/ask',
        'POST',
        { query },
        (event: SSEEvent) => {
          if (event.type === 'token') {
            const token = String(event.data.token || '')
            fullAnswer += token
            setAnswer(fullAnswer)
          } else if (event.type === 'done') {
            setIsStreaming(false)
          } else if (event.type === 'error') {
            setError(String(event.data.message))
            setIsStreaming(false)
          }
        }
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
      setIsStreaming(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Ask a Question</h1>

      {/* Question Form */}
      <form onSubmit={handleAsk} className="mb-6">
        <div className="flex flex-col gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your documents..."
            disabled={isStreaming}
            className="px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={isStreaming || !query.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
          >
            {isStreaming ? 'Thinking...' : 'Ask'}
          </button>
        </div>
      </form>

      {/* Answer */}
      {(answer || isStreaming || error) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Answer</h2>
          {error ? (
            <div className="bg-red-50 border border-red-200 rounded p-4">
              <p className="text-red-700">{error}</p>
            </div>
          ) : (
            <div className="bg-gray-50 rounded p-4 min-h-24">
              <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                {answer}
                {isStreaming && <span className="animate-pulse">▌</span>}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
