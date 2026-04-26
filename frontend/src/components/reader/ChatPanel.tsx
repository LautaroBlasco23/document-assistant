import * as React from 'react'
import { Send, Loader2, MessageSquare, FileText, Plus, Trash2, ChevronDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import { useGenerationSettings } from '../../stores/generation-settings'
import { usePendingContent } from '../../stores/pending-content-store'
import { useAgents } from '../../hooks/use-agents'
import { useModels } from '../../hooks/use-models'
import { AgentCreationDialog } from '../../pages/settings/agent-creation-dialog'
import { ContentPanel } from './ContentPanel'
import type { ChatMessage } from '../../types/api'

type PanelMode = 'chat' | 'content'

interface ChatSession {
  id: string
  name: string
  messages: ChatMessage[]
}

interface ChatPanelProps {
  documentContext: string
  storageKey: string
  treeId: string
  chapter: number | null
}

export interface ChatPanelHandle {
  showContent: () => void
  askInChat: (text: string) => void
}

function makeId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
}

function loadSessions(key: string): ChatSession[] {
  try {
    const raw = localStorage.getItem(`docassist_chat:${key}`)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
  } catch {
    // ignore parse errors
  }
  return []
}

function saveSessions(key: string, sessions: ChatSession[]) {
  try {
    const withMessages = sessions.filter((s) => s.messages.length > 0)
    localStorage.setItem(`docassist_chat:${key}`, JSON.stringify(withMessages))
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
                isUser ? 'bg-primary/20' : 'bg-surface-100 dark:bg-surface-100 text-gray-800 dark:text-slate-200'
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
                isUser ? 'bg-primary/20' : 'bg-surface-100 dark:bg-surface-100'
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
                isUser ? 'text-primary-light' : 'text-primary dark:text-primary hover:text-primary-hover dark:hover:text-primary-hover'
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
                isUser ? 'border-primary text-primary-light' : 'border-surface-200 dark:border-surface-200 text-gray-600 dark:text-slate-400'
              )}
            >
              {children}
            </blockquote>
          )
        },
        hr() {
          return (
            <hr className={cn('my-2 border-t', isUser ? 'border-primary' : 'border-surface-200 dark:border-surface-200')} />
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
          return <thead className={cn('border-b', isUser ? 'border-primary' : 'border-surface-200 dark:border-surface-200')}>{children}</thead>
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

export const ChatPanel = React.forwardRef<ChatPanelHandle, ChatPanelProps>(function ChatPanel(
  { documentContext, storageKey, treeId, chapter },
  ref,
) {
  const { settings, setAgent } = useGenerationSettings()
  const { agents, loading: agentsLoading } = useAgents()
  const { models, currentModel, loading: modelsLoading } = useModels()
  const [mode, setMode] = React.useState<PanelMode>('chat')
  const pendingCount = usePendingContent((s) => s.items.filter((it) => !it.disposition).length)
  const [dropdownOpen, setDropdownOpen] = React.useState(false)
  const [agentDialogOpen, setAgentDialogOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  const defaultAgent = agents.find((a) => a.is_default)
  const selectedAgentId = settings.agent_id ?? defaultAgent?.id ?? ''

  const handleAgentChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === '__create__') {
      setAgentDialogOpen(true)
      return
    }
    if (value) setAgent(value)
  }

  const handleAgentCreated = (agentId: string) => {
    setAgent(agentId)
  }

  const [{ initialSessions, initialActiveId }] = React.useState(() => {
    const stored = loadSessions(storageKey)
    const newSession: ChatSession = {
      id: makeId(),
      name: `Chat ${stored.length + 1}`,
      messages: [],
    }
    return { initialSessions: [...stored, newSession], initialActiveId: newSession.id }
  })

  const [sessions, setSessions] = React.useState<ChatSession[]>(initialSessions)
  const [activeSessionId, setActiveSessionId] = React.useState<string>(initialActiveId)
  const [input, setInput] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const scrollRef = React.useRef<HTMLDivElement>(null)

  const activeSession = sessions.find((s) => s.id === activeSessionId)

  React.useEffect(() => {
    saveSessions(storageKey, sessions)
  }, [sessions, storageKey])

  React.useEffect(() => {
    if (!dropdownOpen) return
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [dropdownOpen])

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
        const fallback: ChatSession = { id: makeId(), name: 'Chat 1', messages: [] }
        setActiveSessionId(fallback.id)
        return [fallback]
      }
      return filtered
    })
  }

  const updateSessionMessages = (sessionId: string, messages: ChatMessage[]) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, messages } : s))
    )
  }

  const sendText = async (rawText: string) => {
    const text = rawText.trim()
    if (!text || loading || !activeSession) return

    if (text === '/clear') {
      updateSessionMessages(activeSession.id, [])
      return
    }

    const userMsg: ChatMessage = { role: 'user', content: text }
    const updatedMessages = [...activeSession.messages, userMsg]
    updateSessionMessages(activeSession.id, updatedMessages)
    setLoading(true)

    try {
      const res = await client.chat({
        messages: updatedMessages,
        context: documentContext || null,
        model: settings.model,
        agent_id: settings.agent_id,
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

  const handleSend = async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    await sendText(text)
  }

  const sendTextRef = React.useRef(sendText)
  sendTextRef.current = sendText

  React.useImperativeHandle(
    ref,
    () => ({
      showContent: () => setMode('content'),
      askInChat: (selected: string) => {
        const trimmed = selected.trim()
        if (!trimmed) return
        setMode('chat')
        const prompt = `Define and explain the following excerpt in the context of this document:\n\n"${trimmed}"`
        sendTextRef.current(prompt)
      },
    }),
    [],
  )

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full flex flex-col bg-surface dark:bg-surface-200">
      <div className="flex border-b border-surface-200 dark:border-surface-200 shrink-0">
        <button
          onClick={() => setMode('chat')}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors',
            mode === 'chat'
              ? 'text-primary border-b-2 border-primary bg-primary-light dark:bg-primary/12'
              : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
          )}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Chat
        </button>
        <button
          onClick={() => setMode('content')}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors',
            mode === 'content'
              ? 'text-primary border-b-2 border-primary bg-primary-light dark:bg-primary/12'
              : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
          )}
        >
          <FileText className="h-3.5 w-3.5" />
          Content
          {pendingCount > 0 && (
            <span className="ml-0.5 inline-flex items-center justify-center min-w-[1rem] h-4 px-1 text-[10px] font-semibold rounded-full bg-amber-500 text-white">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {mode === 'chat' ? (
        <>
          {/* Session selector */}
           <div className="shrink-0 border-b border-surface-200 dark:border-surface-200 px-2 py-1.5 flex items-center gap-1.5">
            <div ref={dropdownRef} className="relative flex-1 min-w-0">
              <button
                onClick={() => setDropdownOpen((o) => !o)}
                className="w-full flex items-center justify-between gap-1 text-xs px-2 py-1 rounded border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-700 dark:text-slate-200 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors truncate"
              >
                <span className="truncate">
                  {activeSession?.name} ({activeSession?.messages.length} msgs)
                </span>
                <ChevronDown className={cn('h-3 w-3 shrink-0 text-gray-400 dark:text-slate-500 transition-transform', dropdownOpen && 'rotate-180')} />
              </button>
              {dropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 z-50 rounded-md border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 shadow-lg max-h-48 overflow-y-auto">
                  {sessions.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => { setActiveSessionId(s.id); setDropdownOpen(false) }}
                      className={cn(
                        'w-full text-left text-xs px-3 py-1.5 truncate transition-colors',
                        s.id === activeSessionId
                          ? 'bg-primary-light dark:bg-primary/12 text-primary font-medium'
                          : 'text-gray-700 dark:text-slate-300 hover:bg-surface-100 dark:hover:bg-surface-100'
                      )}
                    >
                      {s.name} ({s.messages.length} msgs)
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={handleNewSession}
              title="New chat"
              className="p-1 rounded text-gray-400 dark:text-slate-500 hover:text-primary dark:hover:text-primary hover:bg-primary-light dark:hover:bg-primary/12 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
            {sessions.length > 1 && (
              <button
                onClick={() => activeSession && handleDeleteSession(activeSession.id)}
                title="Delete chat"
                className="p-1 rounded text-gray-400 dark:text-slate-500 hover:text-danger dark:hover:text-danger hover:bg-danger-light dark:hover:bg-danger/12 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Agent selector */}
          {!agentsLoading && !modelsLoading && agents.length > 0 && (
            <div className="shrink-0 border-b border-surface-200 dark:border-surface-200 px-2 py-1 flex items-center gap-1.5">
              <span className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-slate-500 shrink-0">Agent</span>
              <div className="relative flex-1 min-w-0">
                <select
                  value={selectedAgentId}
                  onChange={handleAgentChange}
                  className="w-full text-xs px-1.5 py-0.5 rounded border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 text-gray-700 dark:text-slate-200 appearance-none cursor-pointer"
                >
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}{a.is_default ? ' (default)' : ''}
                    </option>
                  ))}
                  <option value="__create__" disabled className="text-gray-400 dark:text-slate-500">
                    ──────────────
                  </option>
                  <option value="__create__">+ Create new agent</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400 dark:text-slate-500" />
              </div>
            </div>
          )}
          <AgentCreationDialog
            open={agentDialogOpen}
            onOpenChange={setAgentDialogOpen}
            models={models}
            currentModel={currentModel}
            onCreated={handleAgentCreated}
          />

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
            {(!activeSession || activeSession.messages.length === 0) && (
              <div className="text-center text-xs text-gray-400 dark:text-slate-500 mt-4">
                Ask questions about this document
                <br />
                <span className="text-gray-300 dark:text-slate-600">Type /clear to reset context</span>
              </div>
            )}
            {activeSession?.messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  'text-sm leading-relaxed rounded-lg px-3 py-2 max-w-[90%]',
                  msg.role === 'user'
                    ? 'bg-primary text-white ml-auto'
                    : 'bg-surface-100 dark:bg-surface-200 text-gray-800 dark:text-slate-200'
                )}
              >
                <MessageContent content={msg.content} role={msg.role} />
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-slate-500">
                <Loader2 className="h-3 w-3 animate-spin" />
                Thinking...
              </div>
            )}
          </div>
          <div className="border-t border-surface-200 dark:border-surface-200 p-2 shrink-0">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                rows={2}
                className="flex-1 resize-none rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 px-3 py-2 text-sm text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary placeholder:text-gray-400 dark:placeholder:text-slate-500"
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className={cn(
                  'p-2 rounded-lg transition-colors shrink-0',
                  input.trim() && !loading
                    ? 'bg-primary text-white hover:bg-primary-hover'
                    : 'bg-surface-100 dark:bg-surface-200 text-gray-400 dark:text-slate-500 cursor-not-allowed'
                )}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      ) : (
        <ContentPanel treeId={treeId} chapter={chapter} />
      )}
    </div>
  )
})
