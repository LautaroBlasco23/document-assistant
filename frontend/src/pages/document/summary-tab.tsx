import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'
import { client } from '../../services'
import { useTaskStore } from '../../stores/task-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { TaskProgress } from './task-progress'
import type { DocumentStructureOut } from '../../types/api'

interface SummaryTabProps {
  docHash: string
  chapter: number
  chapterIndex: number
  structure: DocumentStructureOut | null
}

interface SummaryData {
  description: string
  bullets: string[]
}

/** Attempt to extract structured summary data, recovering from JSON-stringified fields. */
function parseSummaryData(
  description: string | undefined,
  bullets: unknown,
  content?: string
): SummaryData | null {
  const safeBullets = (val: unknown): string[] =>
    Array.isArray(val) ? val.filter((b): b is string => typeof b === 'string') : []

  // Try description field first
  if (description) {
    if (!description.startsWith('{')) {
      return { description, bullets: safeBullets(bullets) }
    }
    // Attempt recovery from JSON-stringified description
    try {
      const parsed = JSON.parse(description) as Record<string, unknown>
      if (typeof parsed.description === 'string') {
        return {
          description: parsed.description,
          bullets: safeBullets(parsed.bullets),
        }
      }
    } catch { /* not valid JSON, fall through */ }
  }

  // Fall back to content field (backward compat with markdown-only summaries)
  if (content) {
    // Strip markdown code fences that some LLMs add (e.g. ```json\n...\n```)
    const strippedContent = content.replace(/^```(?:json)?\s*\n?/, '').replace(/\n?```\s*$/, '').trim()
    if (strippedContent.startsWith('{')) {
      try {
        const parsed = JSON.parse(strippedContent) as Record<string, unknown>
        if (typeof parsed.description === 'string') {
          return {
            description: parsed.description,
            bullets: safeBullets(parsed.bullets),
          }
        }
      } catch { /* not valid JSON, fall through */ }
    } else {
      return { description: strippedContent, bullets: [] }
    }
  }

  return null
}

export function SummaryTab({ docHash, chapter, chapterIndex, structure: _structure }: SummaryTabProps) {
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null)
  const [isLoadingStored, setIsLoadingStored] = useState(false)

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  // Load stored summary when chapter changes
  useEffect(() => {
    let cancelled = false
    setIsLoadingStored(true)
    setSummaryData(null)
    void client.getStoredSummary(docHash, chapter, chapterIndex).then((stored) => {
      if (cancelled) return
      setIsLoadingStored(false)
      if (stored) {
        const parsed = parseSummaryData(stored.description, stored.bullets, stored.content)
        if (parsed) {
          setSummaryData(parsed)
        }
      }
    }).catch(() => {
      if (!cancelled) setIsLoadingStored(false)
    })
    return () => { cancelled = true }
  }, [docHash, chapter, chapterIndex])

  // Subscribe to the task for this specific (docHash, chapter, type) context
  const task = useTaskStore((state) =>
    Object.values(state.tasks).find(
      (t) => t.docHash === docHash && t.chapter === chapter && t.type === 'summary'
    )
  )

  // When the task completes, extract the result and clear it from the store
  useEffect(() => {
    if (!task || task.status !== 'completed') return
    const result = task.result

    if (result && typeof result === 'object' && !Array.isArray(result)) {
      const r = result as Record<string, unknown>
      const parsed = parseSummaryData(
        typeof r.description === 'string' ? r.description : undefined,
        r.bullets
      )
      if (parsed) {
        setSummaryData(parsed)
      }
    }
    useTaskStore.getState().clearTask(task.taskId)
  }, [task?.status, task?.taskId, docHash])

  const handleGenerate = async () => {
    setSummaryData(null)
    try {
      const response = await client.summarizeChapter(chapter, chapterIndex, bookTitle, docHash, true)
      useTaskStore.getState().submitTask({
        taskId: response.task_id,
        type: 'summary',
        docHash,
        chapter,
        bookTitle,
      })
    } catch {
      // API call failed before task was submitted -- no cleanup needed
    }
  }

  const handleClear = async () => {
    try {
      await client.deleteSummary(docHash, chapter, chapterIndex)
      setSummaryData(null)
    } catch {
      // Ignore errors (e.g. 404 if already gone)
      setSummaryData(null)
    }
  }

  const isGenerating = task !== undefined && (task.status === 'pending' || task.status === 'running')
  const hasFailed = task?.status === 'failed'
  const isLoading = isLoadingStored || isGenerating

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isGenerating}
      loading={isGenerating}
    >
      {summaryData || hasFailed ? 'Regenerate' : 'Generate'}
    </Button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        {generateButton}
        {summaryData && !isLoading && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void handleClear()}
          >
            Clear
          </Button>
        )}
      </div>

      {/* Loading state */}
      {isGenerating && (
        <TaskProgress
          progressPct={task?.progressPct ?? null}
          message={task?.progress ?? null}
          fallbackMessage="Generating summary..."
        />
      )}

      {/* Error state */}
      {hasFailed && !isGenerating && (
        <p className="text-sm text-red-500">
          {task?.error ?? 'Generation failed. Please try again.'}
        </p>
      )}

      {/* Summary content */}
      {!isLoading && summaryData && (
        <div className="prose prose-gray max-w-none">
          <p className="text-gray-700 leading-relaxed">{summaryData.description}</p>
          {summaryData.bullets.length > 0 && (
            <ul className="mt-4 space-y-1.5 list-none pl-0">
              {summaryData.bullets.map((bullet, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-700">
                  <span className="text-blue-500 font-bold mt-0.5 shrink-0">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !summaryData && (
        <EmptyState
          icon={FileText}
          title="No summary yet"
          description="Select a chapter and generate a summary"
        />
      )}
    </div>
  )
}
