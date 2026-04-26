import * as React from 'react'
import {
  Sparkles,
  GraduationCap,
  ToggleLeft,
  ListChecks,
  Link2,
  CheckSquare,
  Check,
  RefreshCw,
  Trash2,
  BookMarked,
  ChevronDown,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Select } from '../../components/ui/select'
import { KnowledgeExamSession } from './knowledge-exam-session'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useAgents } from '../../hooks/use-agents'
import { useModels } from '../../hooks/use-models'
import { AgentCreationDialog } from '../settings/agent-creation-dialog'
import { client } from '../../services'
import type {
  KnowledgeChapter,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
  ExamQuestion,
} from '../../types/knowledge-tree'
import type { KnowledgeTreeQuestionType } from '../../types/api'

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
// Task polling hook for knowledge tree question generation
// ---------------------------------------------------------------------------

function useQuestionGenerationTask(params: {
  taskId: string | null
  onComplete: () => void
  onFail?: (error: string) => void
}) {
  const { taskId, onComplete, onFail } = params
  const [isPolling, setIsPolling] = React.useState(false)
  const [progressPct, setProgressPct] = React.useState<number | null>(null)
  const [progressMsg, setProgressMsg] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!taskId) return

    setIsPolling(true)
    setProgressPct(null)
    setProgressMsg(null)

    const interval = setInterval(async () => {
      try {
        const status = await client.getTaskStatus(taskId)
        setProgressPct(status.progress_pct ?? null)
        setProgressMsg(status.progress ?? null)

        if (status.status === 'completed') {
          clearInterval(interval)
          setIsPolling(false)
          onComplete()
        } else if (status.status === 'failed') {
          clearInterval(interval)
          setIsPolling(false)
          onFail?.(status.error ?? 'Generation failed')
        }
      } catch {
        clearInterval(interval)
        setIsPolling(false)
        onFail?.('Lost connection to server')
      }
    }, 1500)

    return () => {
      clearInterval(interval)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  return { isPolling, progressPct, progressMsg }
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
  numQuestionsControl,
  children,
}: GeneratorSectionProps) {
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
          {status !== 'loading' && (
            <Button
              variant={status === 'done' ? 'ghost' : 'secondary'}
              size="sm"
              onClick={onGenerate}
              className={status === 'done' ? 'text-gray-400 h-7 px-2' : 'h-7'}
            >
              {status === 'done' ? (
                <>
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Regenerate
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                  Generate
                </>
              )}
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
          <span className="text-gray-700 leading-relaxed flex-1">{q.statement}</span>
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
            <p className="text-xs font-medium text-gray-700">{q.question}</p>
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
                    ? 'text-green-700 bg-green-50'
                    : 'text-gray-500'
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
            <p className="text-xs font-medium text-gray-600">{q.prompt}</p>
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
                  <td className="rounded-l px-2 py-1 font-medium text-gray-700 w-36 align-top border border-surface-200 dark:border-surface-200">
                    {pair.term}
                  </td>
                  <td className="rounded-r px-2 py-1 text-gray-500 align-top border border-surface-200 dark:border-surface-200">
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
            <p className="text-xs font-medium text-gray-700">{q.question}</p>
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
                    correct ? 'text-green-700 bg-green-50' : 'text-gray-500'
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
// Exam ready screen
// ---------------------------------------------------------------------------

interface ExamTypeCount {
  label: string
  count: number
}

interface KnowledgeExamReadyProps {
  typeCounts: ExamTypeCount[]
  totalCount: number
  onStart: () => void
}

function KnowledgeExamReady({ typeCounts, totalCount, onStart }: KnowledgeExamReadyProps) {
  const hasQuestions = totalCount > 0

  if (!hasQuestions) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
        <GraduationCap className="h-9 w-9 text-gray-200" />
        <div>
          <p className="text-sm font-medium text-gray-500">No questions generated yet</p>
          <p className="text-xs text-gray-400 mt-1">
            Generate at least one question type above to take an exam.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface p-4 flex flex-col gap-3">
        <p className="text-sm text-gray-600">
          Ready to start with{' '}
          <span className="font-semibold text-gray-800">{totalCount}</span>{' '}
          {totalCount === 1 ? 'question' : 'questions'} from the following types:
        </p>

        <div className="flex flex-col gap-1">
          {typeCounts
            .filter((t) => t.count > 0)
            .map((t) => (
              <div key={t.label} className="flex items-center justify-between text-xs">
                <span className="text-gray-600">{t.label}</span>
                <span className="font-medium text-gray-700">
                  {t.count} {t.count === 1 ? 'question' : 'questions'}
                </span>
              </div>
            ))}
        </div>

        <Button variant="primary" size="sm" onClick={onStart} className="self-start mt-1">
          Start Exam
        </Button>
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

  const store = useKnowledgeTreeStore()

  // When questions exist in the store, show 'done' status
  React.useEffect(() => {
    if (questionCount > 0 && status === 'idle') {
      setStatus('done')
    }
  }, [questionCount, status])

  const { isPolling, progressMsg } = useQuestionGenerationTask({
    taskId,
    onComplete: () => {
      void store.fetchQuestions(treeId, chapter).then(() => {
        onQuestionsUpdated()
        setStatus('done')
        setTaskId(null)
      })
    },
    onFail: () => {
      setStatus('idle')
      setTaskId(null)
    },
  })

  // Keep status in sync with polling state
  React.useEffect(() => {
    if (isPolling && status !== 'loading') {
      setStatus('loading')
    }
  }, [isPolling, status])

  const handleGenerate = async () => {
    setStatus('loading')
    try {
      const id = await store.generateQuestions(treeId, chapter, questionType, numQuestions)
      setTaskId(id)
    } catch {
      setStatus('idle')
    }
  }

  const handleDelete = async (questionId: string) => {
    await store.deleteQuestion(treeId, chapter, questionId)
  }

  return (
    <GeneratorSection
      icon={icon}
      title={title}
      description={description}
      status={status}
      count={questionCount}
      spinnerColor={spinnerColor}
      progressMsg={progressMsg}
      onGenerate={() => void handleGenerate()}
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
  const [examActive, setExamActive] = React.useState(false)
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

  const currentChapter = chapters.find((c) => c.number === selectedChapter)

  const handleQuestionsUpdated = () => {
    // Store update triggers re-render automatically
  }

  const examQuestions: ExamQuestion[] = selectedChapter !== null
    ? [...tfQuestions, ...mcQuestions, ...matchingQuestions, ...cbQuestions]
    : []

  const typeCounts: ExamTypeCount[] = selectedChapter !== null
    ? [
        { label: 'True / False', count: tfQuestions.length },
        { label: 'Multiple Choice', count: mcQuestions.length },
        { label: 'Matching', count: matchingQuestions.length },
        { label: 'Checkbox', count: cbQuestions.length },
      ]
    : []

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

          <p className="text-xs text-gray-500">
            Questions are generated from the knowledge documents in{' '}
            <span className="font-medium text-gray-700">{currentChapter?.title}</span>.
            Make sure you&apos;ve added documents in the Knowledge Documents tab first.
          </p>

          {/* Question generators */}
          <div className="flex flex-col gap-4">
            <p className="text-xs text-gray-400">
              Generate each question type independently. All generated questions will be
              available in the exam below.
            </p>

            <QuestionGenerator
              treeId={treeId}
              chapter={selectedChapter}
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

          {/* Exam section */}
          <div className="mt-2">
            <div className="flex items-center gap-2 mb-3">
              <GraduationCap className="h-4 w-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Exam</span>
            </div>
            {examActive ? (
              <KnowledgeExamSession
                questions={examQuestions}
                onFinish={() => setExamActive(false)}
              />
            ) : (
              <KnowledgeExamReady
                typeCounts={typeCounts}
                totalCount={examQuestions.length}
                onStart={() => setExamActive(true)}
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}
