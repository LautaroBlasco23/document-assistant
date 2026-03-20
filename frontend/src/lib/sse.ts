import type { SSEEvent } from '../types/domain'

/**
 * Stream SSE events from a server endpoint using fetch + ReadableStream.
 * Handles partial line buffering for robust event parsing.
 */
export async function streamSSE(
  url: string,
  method: string,
  body: unknown,
  onEvent: (event: SSEEvent) => void
): Promise<void> {
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

    // Parse SSE events line by line, keeping incomplete lines in the buffer
    const lines = buffer.split('\n')
    buffer = lines[lines.length - 1] // Last element may be an incomplete line

    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i]

      if (line.startsWith('event: ')) {
        const eventType = line.slice(7)
        const nextLine = lines[i + 1]

        if (nextLine?.startsWith('data: ')) {
          try {
            const data = JSON.parse(nextLine.slice(6))
            onEvent({ type: eventType, data })
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  }
}
