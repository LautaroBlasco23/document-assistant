import * as React from 'react'
import { Check, X, Loader2, AlertCircle, Pencil } from 'lucide-react'
import { client } from '../../services'
import { cn } from '../../lib/cn'
import {
  usePendingContent,
  type PendingContent,
  type PendingFlashcard,
  type PendingQuestion,
} from '../../stores/pending-content-store'

interface ContentPanelProps {
  treeId: string
  chapter: number | null
}

export function ContentPanel({ treeId, chapter }: ContentPanelProps) {
  const items = usePendingContent((s) => s.items)

  if (items.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        <div className="text-center text-xs text-gray-400 dark:text-slate-500 mt-4">
          Right-click a selection in the document
          <br />
          and choose what to generate.
          <br />
          <span className="text-gray-300 dark:text-slate-600">
            Generated items appear here for your review.
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {items.map((item) =>
        item.kind === 'flashcard' ? (
          <FlashcardCard key={item.id} item={item} treeId={treeId} chapter={chapter} />
        ) : (
          <QuestionCard key={item.id} item={item} treeId={treeId} chapter={chapter} />
        ),
      )}
    </div>
  )
}

function CardShell({
  label,
  status,
  error,
  onApprove,
  onReject,
  approveDisabled,
  children,
}: {
  label: string
  status: PendingContent['status']
  error?: string
  onApprove: () => void
  onReject: () => void
  approveDisabled?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-100 dark:border-slate-700/60 bg-gray-50/60 dark:bg-slate-800/80">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
          {status === 'generating' && <Loader2 className="h-3 w-3 animate-spin" />}
          {status === 'error' && <AlertCircle className="h-3 w-3 text-red-500" />}
          <span>{label}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onReject}
            disabled={status === 'saving'}
            title="Reject"
            className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
          >
            <X className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onApprove}
            disabled={approveDisabled || status === 'saving' || status === 'generating'}
            title="Approve"
            className="p-1 rounded text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
          >
            {status === 'saving' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>
      <div className="px-3 py-2">
        {error && <div className="mb-2 text-xs text-red-500">{error}</div>}
        {children}
      </div>
    </div>
  )
}

function EditableField({
  label,
  value,
  onChange,
  rows = 2,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  rows?: number
}) {
  return (
    <label className="block mb-2 last:mb-0">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-500 flex items-center gap-1">
        <Pencil className="h-2.5 w-2.5" /> {label}
      </span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="mt-0.5 w-full resize-none rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/60 px-2 py-1 text-sm text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
    </label>
  )
}

function FlashcardCard({
  item,
  treeId,
  chapter,
}: {
  item: PendingFlashcard
  treeId: string
  chapter: number | null
}) {
  const update = usePendingContent((s) => s.update)
  const remove = usePendingContent((s) => s.remove)

  const approve = async () => {
    const ch = chapter ?? item.chapter
    if (!ch) return
    update(item.id, { status: 'saving', error: undefined })
    try {
      await client.saveFlashcard(treeId, ch, {
        front: item.front,
        back: item.back,
        source_text: item.sourceText || null,
      })
      remove(item.id)
    } catch (e) {
      update(item.id, { status: 'ready', error: (e as Error).message || 'Failed to save' })
    }
  }

  return (
    <CardShell
      label="Flashcard"
      status={item.status}
      error={item.error}
      onApprove={approve}
      onReject={() => remove(item.id)}
      approveDisabled={!item.front.trim() || !item.back.trim()}
    >
      <EditableField
        label="Front"
        value={item.front}
        onChange={(v) => update(item.id, { front: v })}
      />
      <EditableField
        label="Back"
        value={item.back}
        onChange={(v) => update(item.id, { back: v })}
        rows={3}
      />
    </CardShell>
  )
}

function QuestionCard({
  item,
  treeId,
  chapter,
}: {
  item: PendingQuestion
  treeId: string
  chapter: number | null
}) {
  const update = usePendingContent((s) => s.update)
  const remove = usePendingContent((s) => s.remove)

  const setData = (patch: Record<string, unknown>) =>
    update(item.id, { questionData: { ...item.questionData, ...patch } })

  const approve = async () => {
    const ch = chapter ?? item.chapter
    if (!ch) return
    update(item.id, { status: 'saving', error: undefined })
    try {
      await client.saveQuestion(treeId, ch, item.questionType, item.questionData)
      remove(item.id)
    } catch (e) {
      update(item.id, {
        status: 'ready',
        error: (e as Error).message || 'Validation failed',
      })
    }
  }

  let body: React.ReactNode
  if (item.questionType === 'true_false') {
    const statement = String(item.questionData.statement ?? '')
    const answer = Boolean(item.questionData.answer)
    const explanation = String(item.questionData.explanation ?? '')
    body = (
      <>
        <EditableField
          label="Statement"
          value={statement}
          onChange={(v) => setData({ statement: v })}
          rows={3}
        />
        <div className="mb-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-500">
            Answer
          </span>
          <div className="mt-1 flex gap-1">
            {[true, false].map((val) => (
              <button
                key={String(val)}
                onClick={() => setData({ answer: val })}
                className={cn(
                  'flex-1 px-2 py-1 text-xs rounded border transition-colors',
                  answer === val
                    ? 'bg-blue-500 text-white border-blue-500'
                    : 'border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700',
                )}
              >
                {val ? 'True' : 'False'}
              </button>
            ))}
          </div>
        </div>
        <EditableField
          label="Explanation (optional)"
          value={explanation}
          onChange={(v) => setData({ explanation: v })}
        />
      </>
    )
  } else if (item.questionType === 'multiple_choice') {
    const question = String(item.questionData.question ?? '')
    const choices = (item.questionData.choices as string[] | undefined) ?? ['', '', '', '']
    const correctIndex = Number(item.questionData.correct_index ?? 0)
    const explanation = String(item.questionData.explanation ?? '')
    const setChoice = (i: number, v: string) => {
      const next = [...choices]
      next[i] = v
      setData({ choices: next })
    }
    body = (
      <>
        <EditableField
          label="Question"
          value={question}
          onChange={(v) => setData({ question: v })}
          rows={2}
        />
        <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-500">
          Choices (click radio to mark correct)
        </span>
        <div className="space-y-1 mt-1 mb-2">
          {choices.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="radio"
                checked={correctIndex === i}
                onChange={() => setData({ correct_index: i })}
                className="shrink-0"
              />
              <input
                type="text"
                value={c}
                onChange={(e) => setChoice(i, e.target.value)}
                className="flex-1 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/60 px-2 py-1 text-xs text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>
          ))}
        </div>
        <EditableField
          label="Explanation (optional)"
          value={explanation}
          onChange={(v) => setData({ explanation: v })}
        />
      </>
    )
  } else {
    body = (
      <pre className="text-xs whitespace-pre-wrap break-words text-gray-700 dark:text-slate-300">
        {JSON.stringify(item.questionData, null, 2)}
      </pre>
    )
  }

  const labelMap: Record<string, string> = {
    true_false: 'True / False',
    multiple_choice: 'Multiple Choice',
    matching: 'Matching',
    checkbox: 'Checkbox',
  }

  return (
    <CardShell
      label={labelMap[item.questionType] ?? 'Question'}
      status={item.status}
      error={item.error}
      onApprove={approve}
      onReject={() => remove(item.id)}
    >
      {body}
    </CardShell>
  )
}
