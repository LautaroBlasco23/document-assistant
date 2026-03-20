import { useState } from 'react'
import { HelpCircle } from 'lucide-react'
import { client } from '../../services'
import { useTask } from '../../hooks/use-task'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Progress } from '../../components/ui/progress'
import { EmptyState } from '../../components/ui/empty-state'
import { Tooltip } from '../../components/ui/tooltip'
import { mockQAPairs } from '../../mocks/qa-pairs'
import type { DocumentStructureOut, QAPairOut } from '../../types/api'

interface QATabProps {
  docHash: string
  chapter?: number
  structure: DocumentStructureOut | null
}

export function QATab({ docHash, chapter, structure: _structure }: QATabProps) {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [pairs, setPairs] = useState<QAPairOut[] | null>(null)
  const [generating, setGenerating] = useState(false)

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  const { task } = useTask(taskId, (result) => {
    // After task completes, extract pairs from result or fall back to mock data
    const resultPairs = (result as Record<string, unknown> | null)?.qa_pairs as QAPairOut[] | undefined
    if (resultPairs && resultPairs.length > 0) {
      setPairs(resultPairs)
    } else {
      // Fall back to mock data keyed by docHash
      const mockData = mockQAPairs[docHash]
      setPairs(mockData ?? [])
    }
    setTaskId(null)
    setGenerating(false)
  })

  const handleGenerate = async () => {
    if (chapter === undefined) return
    setGenerating(true)
    setPairs(null)
    try {
      const response = await client.generateQA(chapter, bookTitle)
      setTaskId(response.task_id)
    } catch {
      setGenerating(false)
    }
  }

  const isLoading = generating || (taskId !== null && task?.status !== 'completed')
  const isDisabled = chapter === undefined

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isDisabled || isLoading}
      loading={isLoading}
    >
      Generate Q&amp;A
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
      {isLoading && (
        <div className="flex flex-col gap-2">
          <Progress indeterminate />
          {task?.progress && (
            <p className="text-xs text-gray-400">{task.progress}</p>
          )}
        </div>
      )}

      {/* Q&A pairs list */}
      {!isLoading && pairs && pairs.length > 0 && (
        <div className="flex flex-col gap-3">
          {pairs.map((pair, index) => (
            <Card key={index}>
              <p className="font-semibold text-gray-800">{pair.question}</p>
              <p className="text-gray-600 text-sm mt-1">{pair.answer}</p>
            </Card>
          ))}
        </div>
      )}

      {/* Empty pairs result */}
      {!isLoading && pairs !== null && pairs.length === 0 && (
        <EmptyState
          icon={HelpCircle}
          title="No Q&A pairs generated"
          description="Try selecting a different chapter or regenerating"
        />
      )}

      {/* Initial empty state */}
      {!isLoading && pairs === null && (
        <EmptyState
          icon={HelpCircle}
          title="No Q&A pairs yet"
          description="Generate Q&A pairs to test your understanding"
        />
      )}
    </div>
  )
}
