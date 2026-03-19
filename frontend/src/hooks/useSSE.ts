import { useState, useCallback } from 'react'

export interface SSEEvent {
  type: string
  data: Record<string, unknown>
}

export function useSSE() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stream = useCallback(
    async (
      url: string,
      method: string = 'POST',
      body?: Record<string, unknown>,
      onEvent?: (event: SSEEvent) => void
    ) => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: body ? JSON.stringify(body) : undefined,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE events
          const lines = buffer.split('\n')
          buffer = lines[lines.length - 1] // Keep incomplete line in buffer

          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i]

            if (line.startsWith('event: ')) {
              const eventType = line.slice(7)
              const nextLine = lines[i + 1]

              if (nextLine?.startsWith('data: ')) {
                try {
                  const data = JSON.parse(nextLine.slice(6))
                  onEvent?.({ type: eventType, data })
                } catch (e) {
                  console.error('Failed to parse SSE data:', e)
                }
              }
            }
          }
        }

        setIsLoading(false)
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        setError(errorMsg)
        setIsLoading(false)
        throw err
      }
    },
    []
  )

  return { stream, isLoading, error }
}
