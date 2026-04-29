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
          <p className="text-xs text-text-tertiary mt-1">
            Generate at least one question type in the Content tab to take an exam.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-text-secondary">
        Ready to start with{' '}
        <span className="font-semibold text-text-primary">{totalCount}</span>{' '}
        {totalCount === 1 ? 'question' : 'questions'} from the following types:
      </p>

      <div className="self-start border-2 border-border-subtle rounded-lg overflow-hidden">
        <table style={{ minWidth: '280px', borderCollapse: 'collapse' }} className="text-xs">
          <thead>
            <tr className="bg-surface-100 border-b-2 border-border-subtle">
              <th className="px-4 py-2 text-left font-semibold text-text-secondary uppercase tracking-wide text-[10px] whitespace-nowrap border-r-2 border-border-subtle">
                Question Type
              </th>
              <th className="px-4 py-2 text-right font-semibold text-text-secondary uppercase tracking-wide text-[10px] whitespace-nowrap">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {typeCounts
              .filter((t) => t.count > 0)
              .map((t) => (
                <tr key={t.label} className="border-t border-border">
                  <td className="px-4 py-2 text-text-secondary whitespace-nowrap border-r-2 border-border-subtle">{t.label}</td>
                  <td className="px-4 py-2 text-right font-semibold tabular-nums text-text-primary">
                    {t.count}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <Button variant="primary" size="sm" onClick={onStart} className="self-start mt-1">
        Start Exam
      </Button>
    </div>
  )
}
