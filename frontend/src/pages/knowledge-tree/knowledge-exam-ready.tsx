import { GraduationCap } from 'lucide-react'
import { Button } from '../../components/ui/button'

// ---------------------------------------------------------------------------
// Types
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

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function KnowledgeExamReady({ typeCounts, totalCount, onStart }: KnowledgeExamReadyProps) {
  const hasQuestions = totalCount > 0

  if (!hasQuestions) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
        <GraduationCap className="h-9 w-9 text-gray-200" />
        <div>
          <p className="text-sm font-medium text-gray-500">No questions generated yet</p>
          <p className="text-xs text-gray-400 mt-1">
            Generate at least one question type in the Content tab to take an exam.
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
