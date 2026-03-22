import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { client } from '../../services'
import { useTaskStore } from '../../stores/task-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { TaskProgress } from './task-progress'
import { Tooltip } from '../../components/ui/tooltip'
import { mockSummaries } from '../../mocks/summaries'
import type { DocumentStructureOut } from '../../types/api'

interface SummaryTabProps {
  docHash: string
  chapter?: number
  structure: DocumentStructureOut | null
}

export function SummaryTab({ docHash, chapter, structure: _structure }: SummaryTabProps) {
  const [summaryText, setSummaryText] = useState<string | null>(null)

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  // Subscribe to the task for this specific (docHash, chapter, type) context
  const task = useTaskStore((state) =>
    Object.values(state.tasks).find(
      (t) => t.docHash === docHash && t.chapter === chapter && t.type === 'summary'
    )
  )

  // When the task completes, extract the result and clear it from the store
  useEffect(() => {
    if (!task || task.status !== 'completed') return
    const resultSummary = (task.result as Record<string, unknown> | null)?.summary as string | undefined
    if (resultSummary) {
      setSummaryText(resultSummary)
    } else {
      // Fall back to mock data keyed by docHash
      setSummaryText(mockSummaries[docHash]?.summary ?? 'Summary not available.')
    }
    useTaskStore.getState().clearTask(task.taskId)
  }, [task?.status, task?.taskId, docHash])

  const handleGenerate = async () => {
    if (chapter === undefined) return
    setSummaryText(null)
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

  const isLoading = task !== undefined && (task.status === 'pending' || task.status === 'running')
  const isDisabled = chapter === undefined

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isDisabled || isLoading}
      loading={isLoading}
    >
      Generate
    </Button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        {isDisabled ? (
          <Tooltip content="Select a chapter first">
            <span>{generateButton}</span>
          </Tooltip>
        ) : (
          generateButton
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <TaskProgress
          progressPct={task?.progressPct ?? null}
          message={task?.progress ?? null}
          fallbackMessage="Generating summary..."
        />
      )}

      {/* Summary content */}
      {!isLoading && summaryText && (
        <div className="bg-white border border-gray-100 rounded-lg p-5 shadow-sm">
          <ReactMarkdown className="prose prose-sm max-w-none text-gray-700">
            {summaryText}
          </ReactMarkdown>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !summaryText && (
        <EmptyState
          icon={FileText}
          title="No summary yet"
          description="Select a chapter and generate a summary"
        />
      )}
    </div>
  )
}
