import { useState, useEffect } from 'react'
import { HelpCircle } from 'lucide-react'
import { client } from '../../services'
import { useTaskStore } from '../../stores/task-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { EmptyState } from '../../components/ui/empty-state'
import { Tooltip } from '../../components/ui/tooltip'
import { TaskProgress } from './task-progress'
import type { DocumentStructureOut, QAPairOut } from '../../types/api'

interface QATabProps {
  docHash: string
  chapter?: number
  structure: DocumentStructureOut | null
}

export function QATab({ docHash, chapter, structure: _structure }: QATabProps) {
  const [pairs, setPairs] = useState<QAPairOut[] | null>(null)
  const [isLoadingStored, setIsLoadingStored] = useState(false)

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  // Load stored Q&A when chapter changes
  useEffect(() => {
    if (chapter === undefined) return
    let cancelled = false
    setIsLoadingStored(true)
    setPairs(null)
    void client.getStoredQAPairs(docHash, chapter).then((stored) => {
      if (cancelled) return
      setIsLoadingStored(false)
      if (stored.length > 0) setPairs(stored)
    }).catch(() => {
      if (!cancelled) setIsLoadingStored(false)
    })
    return () => { cancelled = true }
  }, [docHash, chapter])

  // Subscribe to the task for this specific (docHash, chapter, type) context
  const task = useTaskStore((state) =>
    Object.values(state.tasks).find(
      (t) => t.docHash === docHash && t.chapter === chapter && t.type === 'qa'
    )
  )

  // When the task completes, extract the result and clear it from the store
  useEffect(() => {
    if (!task || task.status !== 'completed') return
    const resultPairs = (task.result as Record<string, unknown> | null)?.qa_pairs as QAPairOut[] | undefined
    setPairs(resultPairs ?? [])
    useTaskStore.getState().clearTask(task.taskId)
  }, [task?.status, task?.taskId, docHash])

  const handleGenerate = async () => {
    if (chapter === undefined) return
    setPairs(null)
    try {
      const response = await client.generateQA(chapter, bookTitle, docHash)
      useTaskStore.getState().submitTask({
        taskId: response.task_id,
        type: 'qa',
        docHash,
        chapter,
        bookTitle,
      })
    } catch {
      // API call failed before task was submitted -- no cleanup needed
    }
  }

  const isGenerating = task !== undefined && (task.status === 'pending' || task.status === 'running')
  const generateError = task?.status === 'failed' ? (task.error ?? 'Generation failed') : null
  const isDisabled = chapter === undefined

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isDisabled || isGenerating || isLoadingStored}
      loading={isGenerating}
    >
      {pairs && pairs.length > 0 ? 'Regenerate Q&A' : 'Generate Q&A'}
    </Button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        {isDisabled ? (
          <Tooltip content="Select a specific chapter first">
            <span>{generateButton}</span>
          </Tooltip>
        ) : (
          generateButton
        )}
      </div>

      {/* Loading state */}
      {isGenerating && (
        <TaskProgress
          progressPct={task?.progressPct ?? null}
          message={task?.progress ?? null}
          fallbackMessage="Generating Q&A pairs..."
        />
      )}

      {/* Error state */}
      {generateError && (
        <p className="text-sm text-red-500">{generateError}</p>
      )}

      {/* Q&A pairs list */}
      {!isGenerating && pairs && pairs.length > 0 && (
        <div className="flex flex-col gap-3">
          {pairs.map((pair, index) => {
            const levelLabel =
              pair.level === 'remember' ? 'Remember' :
              pair.level === 'understand' ? 'Understand' :
              pair.level === 'apply_analyze' ? 'Apply / Analyze' :
              null
            const levelColor =
              pair.level === 'remember' ? 'bg-blue-100 text-blue-700' :
              pair.level === 'understand' ? 'bg-amber-100 text-amber-700' :
              pair.level === 'apply_analyze' ? 'bg-purple-100 text-purple-700' :
              ''
            return (
              <Card key={index}>
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">{pair.question}</p>
                    <p className="text-gray-600 text-sm mt-1">{pair.answer}</p>
                  </div>
                  {levelLabel && (
                    <span className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full ${levelColor}`}>
                      {levelLabel}
                    </span>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Empty pairs result */}
      {!isGenerating && pairs !== null && pairs.length === 0 && (
        <EmptyState
          icon={HelpCircle}
          title="No Q&A pairs generated"
          description="Try selecting a different chapter or regenerating"
        />
      )}

      {/* Initial empty state */}
      {!isGenerating && !isLoadingStored && pairs === null && (
        <EmptyState
          icon={HelpCircle}
          title="No Q&A pairs yet"
          description="Generate Q&A pairs to test your understanding"
        />
      )}
    </div>
  )
}
