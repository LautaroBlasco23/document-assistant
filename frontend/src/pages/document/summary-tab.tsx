import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'
import { client } from '../../services'
import { useTaskStore } from '../../stores/task-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { TaskProgress } from './task-progress'
import { mockSummaries } from '../../mocks/summaries'
import type { DocumentStructureOut } from '../../types/api'

interface SummaryTabProps {
  docHash: string
  chapter: number
  structure: DocumentStructureOut | null
}

interface SummaryData {
  description: string
  bullets: string[]
}

export function SummaryTab({ docHash, chapter, structure: _structure }: SummaryTabProps) {
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
    void client.getStoredSummary(docHash, chapter).then((stored) => {
      if (cancelled) return
      setIsLoadingStored(false)
      if (stored) {
        if (stored.description) {
          setSummaryData({ description: stored.description, bullets: stored.bullets })
        } else {
          // Backward compat: old cached data only has content
          setSummaryData({ description: stored.content, bullets: [] })
        }
      }
    }).catch(() => {
      if (!cancelled) setIsLoadingStored(false)
    })
    return () => { cancelled = true }
  }, [docHash, chapter])

  // Subscribe to the task for this specific (docHash, chapter, type) context
  const task = useTaskStore((state) =>
    Object.values(state.tasks).find(
      (t) => t.docHash === docHash && t.chapter === chapter && t.type === 'summary'
    )
  )

  // When the task completes, extract the result and clear it from the store
  useEffect(() => {
    if (!task || task.status !== 'completed') return
    const resultDesc = (task.result as Record<string, unknown> | null)?.description as string | undefined
    const resultBullets = (task.result as Record<string, unknown> | null)?.bullets as string[] | undefined

    if (resultDesc) {
      setSummaryData({ description: resultDesc, bullets: resultBullets ?? [] })
    } else {
      // Fall back to mock data keyed by docHash
      const mock = mockSummaries[docHash]
      if (mock) {
        setSummaryData({ description: mock.description, bullets: mock.bullets })
      }
    }
    useTaskStore.getState().clearTask(task.taskId)
  }, [task?.status, task?.taskId, docHash])

  const handleGenerate = async () => {
    setSummaryData(null)
    try {
      const response = await client.summarizeChapter(chapter, bookTitle, docHash)
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

  const isGenerating = task !== undefined && (task.status === 'pending' || task.status === 'running')
  const isLoading = isLoadingStored || isGenerating

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isLoading}
      loading={isGenerating}
    >
      {summaryData ? 'Regenerate' : 'Generate'}
    </Button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        {generateButton}
      </div>

      {/* Loading state */}
      {isGenerating && (
        <TaskProgress
          progressPct={task?.progressPct ?? null}
          message={task?.progress ?? null}
          fallbackMessage="Generating summary..."
        />
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
