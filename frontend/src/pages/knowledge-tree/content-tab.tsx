import * as React from 'react'
import {
  Sparkles,
  ToggleLeft,
  ListChecks,
  Link2,
  CheckSquare,
  Check,
  Trash2,
  BookMarked,
  ChevronDown,
  BookOpen,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Select } from '../../components/ui/select'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useTaskStore } from '../../stores/task-store'
import { useAppStore } from '../../stores/app-store'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useAgents } from '../../hooks/use-agents'
import { useModels } from '../../hooks/use-models'
import { AgentCreationDialog } from '../settings/agent-creation-dialog'
import type {
  KnowledgeChapter,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
} from '../../types/knowledge-tree'
import type { KnowledgeTreeQuestionType, FlashcardOut } from '../../types/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type GenerateStatus = 'idle' | 'loading' | 'done'

interface ContentTabProps {
  treeId: string
  selectedChapter: number | null
  chapters: KnowledgeChapter[]
}

// ---------------------------------------------------------------------------
// Selector: read a single task's live state from the global store
// ---------------------------------------------------------------------------

function useTaskEntry(taskId: string | null) {
  return useTaskStore((s) => (taskId ? (s.tasks[taskId] ?? null) : null))
}

// ---------------------------------------------------------------------------
// Shared generator section shell
// ---------------------------------------------------------------------------

interface GeneratorSectionProps {
  icon: React.ReactNode
  title: string
  description: string
  status: GenerateStatus
  count: number
  spinnerColor?: string
  progressMsg?: string | null
  onGenerate: () => void
  onDeleteAll?: () => void
  numQuestionsControl?: React.ReactNode
  children: React.ReactNode
}

function GeneratorSection({
  icon,
  title,
  description,
  status,
  count,
  spinnerColor = 'border-primary',
  progressMsg,
  onGenerate,
  onDeleteAll,
  numQuestionsControl,
  children,
}: GeneratorSectionProps) {
  const [confirmDelete, setConfirmDelete] = React.useState(false)

  const handleDeleteAll = () => {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setConfirmDelete(false)
    onDeleteAll?.()
  }

  return (
    <div className="rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">{title}</span>
          {status === 'done' && (
            <Badge variant="success" className="text-xs py-0">
              {count} {count === 1 ? 'question' : 'questions'}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {numQuestionsControl}
          {status === 'done' && onDeleteAll && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeleteAll}
              onBlur={() => setConfirmDelete(false)}
              className={confirmDelete ? 'text-red-500 h-7 px-2' : 'text-gray-300 h-7 px-2'}
              title={confirmDelete ? 'Click again to confirm' : 'Delete all questions of this type'}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              {confirmDelete ? 'Confirm?' : 'Delete all'}
            </Button>
          )}
          {status !== 'loading' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onGenerate}
              className="h-7"
            >
              <Sparkles className="h-3.5 w-3.5 mr-1" />
              {status === 'done' ? 'Generate more' : 'Generate'}
            </Button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3">
        {status === 'idle' && (
          <p className="text-xs text-gray-400 dark:text-slate-500">{description}</p>
        )}
        {status === 'loading' && (
          <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-slate-500 py-1">
            <div
              className={`h-3.5 w-3.5 rounded-full border-2 ${spinnerColor} border-t-transparent animate-spin`}
            />
            {progressMsg ?? 'Generating from knowledge documents...'}
          </div>
        )}
        {status === 'done' && children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Question preview lists (with delete button)
// ---------------------------------------------------------------------------

function TrueFalseList({
  questions,
  onDelete,
}: {
  questions: TrueFalseQuestion[]
  onDelete?: (id: string) => void
}) {
  return (
    <ul className="flex flex-col gap-1.5">
      {questions.map((q) => (
        <li
          key={q.id}
          className="flex items-start gap-2 rounded-md border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2 text-xs"
        >
          <span
            className={`mt-0.5 shrink-0 rounded px-1 py-0.5 font-semibold uppercase text-[10px] ${
              q.answer
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-600'
            }`}
          >
            {q.answer ? 'True' : 'False'}
          </span>
          <span className="text-gray-700 dark:text-slate-200 leading-relaxed flex-1">{q.statement}</span>
          {onDelete && (
            <button
              onClick={() => onDelete(q.id)}
              className="ml-1 shrink-0 text-gray-300 hover:text-red-400 transition-colors"
              aria-label="Delete question"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}

function MultipleChoiceList({
  questions,
  onDelete,
}: {
  questions: MultipleChoiceQuestion[]
  onDelete?: (id: string) => void
}) {
  return (
    <ul className="flex flex-col gap-2">
      {questions.map((q) => (
        <li
          key={q.id}
          className="rounded-md border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2"
        >
          <div className="flex items-start justify-between mb-1.5">
            <p className="text-xs font-medium text-gray-700 dark:text-slate-200">{q.question}</p>
            {onDelete && (
              <button
                onClick={() => onDelete(q.id)}
                className="ml-2 shrink-0 text-gray-300 hover:text-red-400 transition-colors"
                aria-label="Delete question"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <ul className="flex flex-col gap-0.5">
            {q.choices.map((choice, i) => (
              <li
                key={i}
                className={`flex items-center gap-1.5 text-xs rounded px-1.5 py-0.5 ${
                  i === q.correctIndex
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-600 dark:text-slate-300'
                }`}
              >
                {i === q.correctIndex ? (
                  <Check className="h-3 w-3 shrink-0 text-green-500" strokeWidth={3} />
                ) : (
                  <span className="h-3 w-3 shrink-0" />
                )}
                <span>{String.fromCharCode(65 + i)}. {choice}</span>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}

function MatchingList({
  questions,
  onDelete,
}: {
  questions: MatchingQuestion[]
  onDelete?: (id: string) => void
}) {
  return (
    <ul className="flex flex-col gap-2">
      {questions.map((q) => (
        <li key={q.id} className="rounded-md border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2">
          <div className="flex items-start justify-between mb-1.5">
            <p className="text-xs font-medium text-gray-700 dark:text-slate-200">{q.prompt}</p>
            {onDelete && (
              <button
                onClick={() => onDelete(q.id)}
                className="ml-2 shrink-0 text-gray-300 hover:text-red-400 transition-colors"
                aria-label="Delete question"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {q.pairs.map((pair, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-surface dark:bg-surface-200' : 'bg-surface-100 dark:bg-surface'}>
                  <td className="rounded-l px-2 py-1 font-medium text-gray-700 dark:text-slate-200 w-36 align-top border border-surface-200 dark:border-surface-200">
                    {pair.term}
                  </td>
                  <td className="rounded-r px-2 py-1 text-gray-600 dark:text-slate-300 align-top border border-surface-200 dark:border-surface-200">
                    {pair.definition}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </li>
      ))}
    </ul>
  )
}

function CheckboxList({
  questions,
  onDelete,
}: {
  questions: CheckboxQuestion[]
  onDelete?: (id: string) => void
}) {
  return (
    <ul className="flex flex-col gap-2">
      {questions.map((q) => (
        <li key={q.id} className="rounded-md border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2">
          <div className="flex items-start justify-between mb-1.5">
            <p className="text-xs font-medium text-gray-700 dark:text-slate-200">{q.question}</p>
            {onDelete && (
              <button
                onClick={() => onDelete(q.id)}
                className="ml-2 shrink-0 text-gray-300 hover:text-red-400 transition-colors"
                aria-label="Delete question"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <ul className="flex flex-col gap-0.5">
            {q.choices.map((choice, i) => {
              const correct = q.correctIndices.includes(i)
              return (
                <li
                  key={i}
                  className={`flex items-center gap-1.5 text-xs rounded px-1.5 py-0.5 ${
                    correct
                      ? 'text-green-600 dark:text-green-400 border border-green-500 dark:border-green-500'
                      : 'text-gray-600 dark:text-slate-300'
                  }`}
                >
                  <span
                    className={`h-3 w-3 shrink-0 rounded border flex items-center justify-center ${
                      correct ? 'border-green-500 bg-green-500' : 'border-gray-300'
                    }`}
                  >
                    {correct && <Check className="h-2 w-2 text-white" strokeWidth={3} />}
                  </span>
                  {choice}
                </li>
              )
            })}
          </ul>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Saved flashcard list
// ---------------------------------------------------------------------------

function FlashcardList({
  flashcards,
  onDelete,
}: {
  flashcards: FlashcardOut[]
  onDelete?: (id: string) => void
}) {
  return (
    <ul className="flex flex-col gap-2">
      {flashcards.map((card) => (
        <li
          key={card.id}
          className="rounded-md border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface px-3 py-2"
        >
          <div className="flex items-start justify-between mb-1">
            <p className="text-xs font-semibold text-gray-700 dark:text-slate-300 flex-1">{card.front}</p>
            {onDelete && (
              <button
                onClick={() => onDelete(card.id)}
                className="ml-2 shrink-0 text-gray-300 hover:text-red-400 transition-colors"
                aria-label="Delete flashcard"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <p className="text-xs text-gray-600 dark:text-slate-300 leading-relaxed">{card.back}</p>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Flashcard generator (bulk generation from chapter chunks)
// ---------------------------------------------------------------------------

interface FlashcardGeneratorProps {
  treeId: string
  chapter: number
  chapterTitle: string
  flashcardCount: number
  onFlashcardsUpdated: () => void
}

function FlashcardGenerator({ treeId, chapter, chapterTitle, flashcardCount, onFlashcardsUpdated }: FlashcardGeneratorProps) {
  const [taskId, setTaskId] = React.useState<string | null>(null)
  const [status, setStatus] = React.useState<GenerateStatus>('idle')
  const [numFlashcards, setNumFlashcards] = React.useState<number | null>(null)
  const [confirmDeleteAll, setConfirmDeleteAll] = React.useState(false)
  const handledRef = React.useRef<string | null>(null)

  const store = useKnowledgeTreeStore()
  const submitTask = useTaskStore((s) => s.submitTask)
  const clearTask = useTaskStore((s) => s.clearTask)
  const addError = useAppStore((s) => s.addError)
  const taskEntry = useTaskEntry(taskId)

  // On mount: resume any in-flight flashcard task for this chapter
  React.useEffect(() => {
    const existing = Object.values(useTaskStore.getState().tasks).find(
      (t) => t.type === 'kt_flashcards' && t.entityId === treeId && t.chapter === chapter
    )
    if (existing) setTaskId(existing.taskId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  React.useEffect(() => {
    if (flashcardCount > 0 && status === 'idle') setStatus('done')
    else if (flashcardCount === 0 && status === 'done') setStatus('idle')
  }, [flashcardCount, status])

  React.useEffect(() => {
    if (taskId && taskEntry && (taskEntry.status === 'pending' || taskEntry.status === 'running')) {
      if (status !== 'loading') setStatus('loading')
    }
  }, [taskId, taskEntry, status])

  React.useEffect(() => {
    if (!taskId || !taskEntry) return
    if (handledRef.current === taskId) return

    if (taskEntry.status === 'completed') {
      handledRef.current = taskId
      void store.fetchFlashcards(treeId, chapter).then(() => {
        onFlashcardsUpdated()
        setStatus('done')
        clearTask(taskId)
        setTaskId(null)
      })
    } else if (taskEntry.status === 'failed') {
      handledRef.current = taskId
      addError(taskEntry.error ?? 'Flashcard generation failed')
      setStatus(flashcardCount > 0 ? 'done' : 'idle')
      clearTask(taskId)
      setTaskId(null)
    } else if (taskEntry.status === 'rate_limited') {
      handledRef.current = taskId
      const retryAfter = (taskEntry.result as { retry_after?: number } | null)?.retry_after
      addError(
        retryAfter
          ? `AI provider is rate-limiting requests. Please retry in ${Math.ceil(retryAfter)}s.`
          : (taskEntry.error ?? 'Rate limited by AI provider. Please try again shortly.')
      )
      setStatus(flashcardCount > 0 ? 'done' : 'idle')
      clearTask(taskId)
      setTaskId(null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, taskEntry?.status])

  const handleGenerate = async () => {
    setStatus('loading')
    try {
      const id = await store.generateFlashcards(treeId, chapter, numFlashcards)
      submitTask({
        taskId: id,
        type: 'kt_flashcards',
        entityId: treeId,
        chapter,
        entityTitle: `${chapterTitle} — Flashcards`,
      })
      setTaskId(id)
    } catch {
      setStatus(flashcardCount > 0 ? 'done' : 'idle')
    }
  }

  const handleDeleteAll = async () => {
    if (!confirmDeleteAll) { setConfirmDeleteAll(true); return }
    setConfirmDeleteAll(false)
    await store.deleteAllFlashcards(treeId, chapter)
  }

  const handleDeleteSingle = async (id: string) => {
    await store.deleteFlashcard(treeId, chapter, id)
  }

  const chapterKey = `${treeId}:${chapter}`
  const flashcards = store.flashcardsByChapter[chapterKey] ?? []

  return (
    <div className="rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-emerald-400" />
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">Flashcards</span>
          {status === 'done' && (
            <Badge variant="success" className="text-xs py-0">
              {flashcardCount} {flashcardCount === 1 ? 'card' : 'cards'}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {status === 'done' && flashcardCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void handleDeleteAll()}
              onBlur={() => setConfirmDeleteAll(false)}
              className={confirmDeleteAll ? 'text-red-500 h-7 px-2' : 'text-gray-300 h-7 px-2'}
              title={confirmDeleteAll ? 'Click again to confirm' : 'Delete all flashcards'}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              {confirmDeleteAll ? 'Confirm?' : 'Delete all'}
            </Button>
          )}
          {status !== 'loading' && (
            <Select
              value={numFlashcards ?? ''}
              onChange={(e) => {
                const v = e.target.value
                setNumFlashcards(v === '' ? null : Number(v))
              }}
              className="w-[168px] h-8 text-xs py-1"
            >
              <option value="" className="text-gray-900 dark:text-slate-100">Let the model choose</option>
              <option value="5" className="text-gray-900 dark:text-slate-100">5 flashcards</option>
              <option value="10" className="text-gray-900 dark:text-slate-100">10 flashcards</option>
              <option value="20" className="text-gray-900 dark:text-slate-100">20 flashcards</option>
              <option value="30" className="text-gray-900 dark:text-slate-100">30 flashcards</option>
            </Select>
          )}
          {status !== 'loading' && (
            <Button variant="secondary" size="sm" onClick={() => void handleGenerate()} className="h-7">
              <Sparkles className="h-3.5 w-3.5 mr-1" />
              {status === 'done' ? 'Generate more' : 'Generate'}
            </Button>
          )}
        </div>
      </div>
      <div className="px-4 py-3">
        {status === 'idle' && (
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Generate flashcards from the knowledge documents, or approve individual ones from the PDF viewer.
          </p>
        )}
        {status === 'loading' && (
          <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-slate-500 py-1">
            <div className="h-3.5 w-3.5 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
            {taskEntry?.progress ?? 'Generating flashcards from knowledge documents...'}
          </div>
        )}
        {status === 'done' && (
          <FlashcardList flashcards={flashcards} onDelete={(id) => void handleDeleteSingle(id)} />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Per-question-type generator with task polling
// ---------------------------------------------------------------------------

interface QuestionGeneratorProps {
  treeId: string
  chapter: number
  chapterTitle: string
  questionType: KnowledgeTreeQuestionType
  icon: React.ReactNode
  title: string
  description: string
  spinnerColor?: string
  onQuestionsUpdated: () => void
  children: (onDelete: (id: string) => void) => React.ReactNode
  questionCount: number
}

function QuestionGenerator({
  treeId,
  chapter,
  chapterTitle,
  questionType,
  icon,
  title,
  description,
  spinnerColor,
  onQuestionsUpdated,
  children,
  questionCount,
}: QuestionGeneratorProps) {
  const [taskId, setTaskId] = React.useState<string | null>(null)
  const [status, setStatus] = React.useState<GenerateStatus>('idle')
  const [numQuestions, setNumQuestions] = React.useState<number | null>(null)
  const handledRef = React.useRef<string | null>(null)

  const store = useKnowledgeTreeStore()
  const submitTask = useTaskStore((s) => s.submitTask)
  const clearTask = useTaskStore((s) => s.clearTask)
  const addError = useAppStore((s) => s.addError)
  const taskEntry = useTaskEntry(taskId)

  // On mount: resume any in-flight task for this chapter+type from the global store.
  // This covers the "navigated away while generating" case.
  React.useEffect(() => {
    const entityId = `${treeId}:${questionType}`
    const existing = Object.values(useTaskStore.getState().tasks).find(
      (t) =>
        t.type === 'kt_questions' &&
        t.entityId === entityId &&
        t.chapter === chapter
    )
    if (existing) setTaskId(existing.taskId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sync questionCount → UI status (only idle↔done, never overrides loading)
  React.useEffect(() => {
    if (questionCount > 0 && status === 'idle') setStatus('done')
    else if (questionCount === 0 && status === 'done') setStatus('idle')
  }, [questionCount, status])

  // Keep UI in sync while the task is pending/running
  React.useEffect(() => {
    if (taskId && taskEntry && (taskEntry.status === 'pending' || taskEntry.status === 'running')) {
      if (status !== 'loading') setStatus('loading')
    }
  }, [taskId, taskEntry, status])

  // React to terminal task states (completed / failed / rate_limited)
  React.useEffect(() => {
    if (!taskId || !taskEntry) return
    if (handledRef.current === taskId) return

    if (taskEntry.status === 'completed') {
      handledRef.current = taskId
      void store.fetchQuestions(treeId, chapter).then(() => {
        onQuestionsUpdated()
        setStatus('done')
        clearTask(taskId)
        setTaskId(null)
      })
    } else if (taskEntry.status === 'failed') {
      handledRef.current = taskId
      addError(taskEntry.error ?? 'Question generation failed')
      setStatus(questionCount > 0 ? 'done' : 'idle')
      clearTask(taskId)
      setTaskId(null)
    } else if (taskEntry.status === 'rate_limited') {
      handledRef.current = taskId
      const retryAfter = (taskEntry.result as { retry_after?: number } | null)?.retry_after
      addError(
        retryAfter
          ? `AI provider is rate-limiting requests. Please retry in ${Math.ceil(retryAfter)}s.`
          : (taskEntry.error ?? 'Rate limited by AI provider. Please try again shortly.')
      )
      setStatus(questionCount > 0 ? 'done' : 'idle')
      clearTask(taskId)
      setTaskId(null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, taskEntry?.status])

  const handleGenerate = async () => {
    setStatus('loading')
    try {
      const id = await store.generateQuestions(treeId, chapter, questionType, numQuestions)
      submitTask({
        taskId: id,
        type: 'kt_questions',
        entityId: `${treeId}:${questionType}`,
        chapter,
        entityTitle: `${chapterTitle} — ${title}`,
      })
      setTaskId(id)
    } catch {
      setStatus(questionCount > 0 ? 'done' : 'idle')
    }
  }

  const handleDelete = async (questionId: string) => {
    await store.deleteQuestion(treeId, chapter, questionId)
  }

  const handleDeleteAll = async () => {
    await store.deleteAllQuestions(treeId, chapter, questionType)
  }

  return (
    <GeneratorSection
      icon={icon}
      title={title}
      description={description}
      status={status}
      count={questionCount}
      spinnerColor={spinnerColor}
      progressMsg={taskEntry?.progress ?? null}
      onGenerate={() => void handleGenerate()}
      onDeleteAll={questionCount > 0 ? () => void handleDeleteAll() : undefined}
      numQuestionsControl={
        status !== 'loading' && (
          <Select
            value={numQuestions ?? ''}
            onChange={(e) => {
              const v = e.target.value
              setNumQuestions(v === '' ? null : Number(v))
            }}
            className="w-[168px] h-8 text-xs py-1"
          >
            <option value="" className="text-gray-900 dark:text-slate-100">
              Let the model choose
            </option>
            <option value="5" className="text-gray-900 dark:text-slate-100">
              5 questions
            </option>
            <option value="10" className="text-gray-900 dark:text-slate-100">
              10 questions
            </option>
            <option value="15" className="text-gray-900 dark:text-slate-100">
              15 questions
            </option>
            <option value="20" className="text-gray-900 dark:text-slate-100">
              20 questions
            </option>
          </Select>
        )
      }
    >
      {children(handleDelete)}
    </GeneratorSection>
  )
}

// ---------------------------------------------------------------------------
// Main content tab
// ---------------------------------------------------------------------------

export function ContentTab({ treeId, selectedChapter, chapters }: ContentTabProps) {
  const [agentDialogOpen, setAgentDialogOpen] = React.useState(false)

  const store = useKnowledgeTreeStore()
  const { settings, setAgent } = useGenerationSettings()
  const { agents, loading: agentsLoading } = useAgents()
  const { models, currentModel, loading: modelsLoading } = useModels()

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

  const chapterKey = selectedChapter !== null ? `${treeId}:${selectedChapter}` : null
  const questionsByType = chapterKey ? (store.questionsByType[chapterKey] ?? {}) : {}

  const tfQuestions = (questionsByType['true_false'] ?? []) as TrueFalseQuestion[]
  const mcQuestions = (questionsByType['multiple_choice'] ?? []) as MultipleChoiceQuestion[]
  const matchingQuestions = (questionsByType['matching'] ?? []) as MatchingQuestion[]
  const cbQuestions = (questionsByType['checkbox'] ?? []) as CheckboxQuestion[]

  const flashcards: FlashcardOut[] = chapterKey ? (store.flashcardsByChapter[chapterKey] ?? []) : []

  const currentChapter = chapters.find((c) => c.number === selectedChapter)

  // Load questions and flashcards when chapter is selected
  React.useEffect(() => {
    if (treeId && selectedChapter !== null) {
      void store.fetchQuestions(treeId, selectedChapter)
      void store.fetchFlashcards(treeId, selectedChapter)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [treeId, selectedChapter])

  const handleQuestionsUpdated = () => {
    // Store update triggers re-render automatically
  }


  return (
    <div className="flex flex-col gap-5">
      {chapters.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Sparkles className="h-10 w-10 text-gray-200 mb-4" />
          <p className="text-sm font-medium text-gray-500">No chapters yet</p>
          <p className="text-xs text-gray-400 mt-1">
            Add chapters in the Knowledge Documents tab, then come back here to generate questions.
          </p>
        </div>
      ) : selectedChapter === null ? (
        <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
          <BookMarked className="h-10 w-10 text-gray-200" />
          <p className="text-sm font-medium text-gray-500">Select a chapter</p>
          <p className="text-xs text-gray-400">Choose a chapter from the sidebar to generate questions.</p>
        </div>
      ) : (
        <>
          {/* Agent selector */}
          {!agentsLoading && !modelsLoading && agents.length > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface">
              <span className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-slate-500 shrink-0">
                Agent
              </span>
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
            onCreated={(id) => setAgent(id)}
          />

          <p className="text-xs text-gray-500 dark:text-slate-400">
            Questions are generated from the knowledge documents in{' '}
            <span className="font-medium text-gray-700 dark:text-slate-200">{currentChapter?.title}</span>.
            Make sure you&apos;ve added documents in the Knowledge Documents tab first.
          </p>

          {/* Flashcards section — top */}
          <FlashcardGenerator
            treeId={treeId}
            chapter={selectedChapter}
            chapterTitle={currentChapter?.title ?? ''}
            flashcardCount={flashcards.length}
            onFlashcardsUpdated={handleQuestionsUpdated}
          />

          {/* Question generators */}
          <div className="flex flex-col gap-4">
            <p className="text-xs text-gray-400 dark:text-slate-400">
              Generate each question type independently. All generated questions will be
              available in the Exam tab.
            </p>

            <QuestionGenerator
              treeId={treeId}
              chapter={selectedChapter}
              chapterTitle={currentChapter?.title ?? ''}
              questionType="true_false"
              icon={<ToggleLeft className="h-4 w-4 text-indigo-400" />}
              title="True / False"
              description="Statements the student must evaluate as true or false, with explanations."
              spinnerColor="border-indigo-400"
              onQuestionsUpdated={handleQuestionsUpdated}
              questionCount={tfQuestions.length}
            >
              {(onDelete) => <TrueFalseList questions={tfQuestions} onDelete={onDelete} />}
            </QuestionGenerator>

            <QuestionGenerator
              treeId={treeId}
              chapter={selectedChapter}
              chapterTitle={currentChapter?.title ?? ''}
              questionType="multiple_choice"
              icon={<ListChecks className="h-4 w-4 text-violet-400" />}
              title="Multiple Choice"
              description="Questions with four options where only one is correct."
              spinnerColor="border-violet-400"
              onQuestionsUpdated={handleQuestionsUpdated}
              questionCount={mcQuestions.length}
            >
              {(onDelete) => <MultipleChoiceList questions={mcQuestions} onDelete={onDelete} />}
            </QuestionGenerator>

            <QuestionGenerator
              treeId={treeId}
              chapter={selectedChapter}
              chapterTitle={currentChapter?.title ?? ''}
              questionType="matching"
              icon={<Link2 className="h-4 w-4 text-amber-400" />}
              title="Matching"
              description="Term-to-definition pairs the student must connect correctly."
              spinnerColor="border-amber-400"
              onQuestionsUpdated={handleQuestionsUpdated}
              questionCount={matchingQuestions.length}
            >
              {(onDelete) => <MatchingList questions={matchingQuestions} onDelete={onDelete} />}
            </QuestionGenerator>

            <QuestionGenerator
              treeId={treeId}
              chapter={selectedChapter}
              chapterTitle={currentChapter?.title ?? ''}
              questionType="checkbox"
              icon={<CheckSquare className="h-4 w-4 text-teal-400" />}
              title="Checkbox (Select All That Apply)"
              description="Questions where multiple answers may be correct."
              spinnerColor="border-teal-400"
              onQuestionsUpdated={handleQuestionsUpdated}
              questionCount={cbQuestions.length}
            >
              {(onDelete) => <CheckboxList questions={cbQuestions} onDelete={onDelete} />}
            </QuestionGenerator>
          </div>
        </>
      )}
    </div>
  )
}
