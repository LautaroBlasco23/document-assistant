import * as React from 'react'
import { Send, Loader2, MessageSquare, PenLine, Plus, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import type { ChatMessage } from '../../types/api'

type PanelMode = 'chat' | 'notes'

interface ChatSession {
  id: string
  name: string
  messages: ChatMessage[]
}

interface ChatPanelProps {
  documentContext: string
  storageKey: string
}

function makeId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
}

function loadSessions(key: string): ChatSession[] {
  try {
    const raw = localStorage.getItem(`docassist_chat:${key}`)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed
    }
  } catch {
    // ignore parse errors
  }
  return [{ id: makeId(), name: 'Chat 1', messages: [] }]
}

function saveSessions(key: string, sessions: ChatSession[]) {
  try {
    localStorage.setItem(`docassist_chat:${key}`, JSON.stringify(sessions))
  } catch {
    // ignore storage errors
  }
}

function MessageContent({ content, role }: { content: string; role: string }) {
  const isUser = role === 'user'

  return (
    <ReactMarkdown
      components={{
        pre({ children, ...props }) {
          return (
            <pre
              className={cn(
                'block text-xs font-mono whitespace-pre-wrap break-words p-2 rounded my-1 overflow-x-auto',
                isUser ? 'bg-blue-600/50' : 'bg-gray-200 text-gray-800'
              )}
              {...props}
            >
              {children}
            </pre>
          )
        },
        code({ children, className, ...props }) {
          if (className) {
            // Inside a code block - render without extra background
            return (
              <code className={cn('text-xs font-mono', className)} {...props}>
                {children}
              </code>
            )
          }
          return (
            <code
              className={cn(
                'px-1 py-0.5 rounded text-xs font-mono',
                isUser ? 'bg-blue-600/50' : 'bg-gray-200'
              )}
              {...props}
            >
              {children}
            </code>
          )
        },
        a({ children, href, ...props }) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'underline font-medium',
                isUser ? 'text-blue-200' : 'text-blue-600 hover:text-blue-700'
              )}
              {...props}
            >
              {children}
            </a>
          )
        },
        p({ children }) {
          return <p className="mb-1 last:mb-0">{children}</p>
        },
        ul({ children }) {
          return <ul className="list-disc pl-4 mb-1 last:mb-0 space-y-0.5">{children}</ul>
        },
        ol({ children }) {
          return <ol className="list-decimal pl-4 mb-1 last:mb-0 space-y-0.5">{children}</ol>
        },
        li({ children }) {
          return <li>{children}</li>
        },
        blockquote({ children }) {
          return (
            <blockquote
              className={cn(
                'border-l-2 pl-2 my-1 italic',
                isUser ? 'border-blue-300 text-blue-100' : 'border-gray-300 text-gray-600'
              )}
            >
              {children}
            </blockquote>
          )
        },
        hr() {
          return (
            <hr className={cn('my-2 border-t', isUser ? 'border-blue-400' : 'border-gray-300')} />
          )
        },
        h1({ children }) {
          return <h1 className="text-base font-bold mb-1 mt-2 first:mt-0">{children}</h1>
        },
        h2({ children }) {
          return <h2 className="text-sm font-bold mb-1 mt-2 first:mt-0">{children}</h2>
        },
        h3({ children }) {
          return <h3 className="text-sm font-semibold mb-1 mt-2 first:mt-0">{children}</h3>
        },
        h4({ children }) {
          return <h4 className="text-xs font-semibold mb-1 mt-2 first:mt-0">{children}</h4>
        },
        strong({ children }) {
          return <strong className="font-bold">{children}</strong>
        },
        em({ children }) {
          return <em className="italic">{children}</em>
        },
        table({ children }) {
          return (
            <div className="overflow-x-auto my-1">
              <table className={cn('w-full text-xs border-collapse', isUser ? '' : '')}>
                {children}
              </table>
            </div>
          )
        },
        thead({ children }) {
          return <thead className={cn('border-b', isUser ? 'border-blue-400' : 'border-gray-300')}>{children}</thead>
        },
        th({ children }) {
          return <th className="px-2 py-1 text-left font-semibold">{children}</th>
        },
        td({ children }) {
          return <td className="px-2 py-1">{children}</td>
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

export function ChatPanel({ documentContext, storageKey }: ChatPanelProps) {
  const [mode, setMode] = React.useState<PanelMode>('chat')
  const [sessions, setSessions] = React.useState<ChatSession[]>(() => loadSessions(storageKey))
  const [activeSessionId, setActiveSessionId] = React.useState<string>(sessions[0]?.id ?? '')
  const [input, setInput] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [notes, setNotes] = React.useState('')
  const scrollRef = React.useRef<HTMLDivElement>(null)

  const activeSession = sessions.find((s) => s.id === activeSessionId)

  React.useEffect(() => {
    saveSessions(storageKey, sessions)
  }, [sessions, storageKey])

  React.useEffect(() => {
    if (!activeSession) {
      setActiveSessionId(sessions[0]?.id ?? '')
    }
  }, [sessions, activeSession])

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [activeSession?.messages])

  const handleNewSession = () => {
    const newSession: ChatSession = {
      id: makeId(),
      name: `Chat ${sessions.length + 1}`,
      messages: [],
    }
    setSessions((prev) => [...prev, newSession])
    setActiveSessionId(newSession.id)
  }

  const handleDeleteSession = (sessionId: string) => {
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId)
      if (filtered.length === 0) {
        return [{ id: makeId(), name: 'Chat 1', messages: [] }]
      }
      return filtered
    })
  }

  const updateSessionMessages = (sessionId: string, messages: ChatMessage[]) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, messages } : s))
    )
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading || !activeSession) return

    if (text === '/clear') {
      updateSessionMessages(activeSession.id, [])
      setInput('')
      return
    }

    const userMsg: ChatMessage = { role: 'user', content: text }
    const updatedMessages = [...activeSession.messages, userMsg]
    updateSessionMessages(activeSession.id, updatedMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await client.chat({
        messages: updatedMessages,
        context: documentContext || null,
      })
      updateSessionMessages(activeSession.id, [
        ...updatedMessages,
        { role: 'assistant', content: res.reply },
      ])
    } catch {
      updateSessionMessages(activeSession.id, [
        ...updatedMessages,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="flex border-b border-gray-200 shrink-0">
        <button
          onClick={() => setMode('chat')}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors',
            mode === 'chat'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
              : 'text-gray-500 hover:text-gray-700'
          )}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Chat
        </button>
        <button
          onClick={() => setMode('notes')}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors',
            mode === 'notes'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
              : 'text-gray-500 hover:text-gray-700'
          )}
        >
          <PenLine className="h-3.5 w-3.5" />
          Notes
        </button>
      </div>

      {mode === 'chat' ? (
        <>
          {/* Session selector */}
          <div className="shrink-0 border-b border-gray-200 px-2 py-1.5 flex items-center gap-1.5">
            <select
              value={activeSessionId}
              onChange={(e) => setActiveSessionId(e.target.value)}
              className="flex-1 min-w-0 text-xs bg-transparent border-none focus:ring-0 text-gray-700 truncate cursor-pointer"
            >
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.messages.length} msgs)
                </option>
              ))}
            </select>
            <button
              onClick={handleNewSession}
              title="New chat"
              className="p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
            {sessions.length > 1 && (
              <button
                onClick={() => activeSession && handleDeleteSession(activeSession.id)}
                title="Delete chat"
                className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
            {(!activeSession || activeSession.messages.length === 0) && (
              <div className="text-center text-xs text-gray-400 mt-4">
                Ask questions about this document
                <br />
                <span className="text-gray-300">Type /clear to reset context</span>
              </div>
            )}
            {activeSession?.messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  'text-sm leading-relaxed rounded-lg px-3 py-2 max-w-[90%]',
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white ml-auto'
                    : 'bg-gray-100 text-gray-800'
                )}
              >
                <MessageContent content={msg.content} role={msg.role} />
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                Thinking...
              </div>
            )}
          </div>
          <div className="border-t border-gray-200 p-2 shrink-0">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                rows={2}
                className="flex-1 resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className={cn(
                  'p-2 rounded-lg transition-colors shrink-0',
                  input.trim() && !loading
                    ? 'bg-blue-500 text-white hover:bg-blue-600'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                )}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      ) : (
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Write your notes here..."
          className="flex-1 resize-none p-3 text-sm focus:outline-none"
        />
      )}
    </div>
  )
}
