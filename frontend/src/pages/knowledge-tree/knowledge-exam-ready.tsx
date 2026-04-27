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
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-600 dark:text-slate-300">
        Ready to start with{' '}
        <span className="font-semibold text-gray-800 dark:text-slate-100">{totalCount}</span>{' '}
        {totalCount === 1 ? 'question' : 'questions'} from the following types:
      </p>

      <table style={{ width: 'auto', borderCollapse: 'collapse' }} className="text-xs border border-surface-200 dark:border-surface-200 rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-surface-100 dark:bg-surface-200">
            <th className="px-3 py-1.5 text-left font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wide text-[10px] whitespace-nowrap">
              Type
            </th>
            <th className="px-3 py-1.5 text-right font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wide text-[10px]">
              #
            </th>
          </tr>
        </thead>
        <tbody>
          {typeCounts
            .filter((t) => t.count > 0)
            .map((t) => (
              <tr key={t.label} className="border-t border-surface-200 dark:border-surface-200">
                <td className="px-3 py-1.5 text-gray-600 dark:text-slate-300 whitespace-nowrap">{t.label}</td>
                <td className="px-3 py-1.5 text-right font-medium tabular-nums text-gray-700 dark:text-slate-200">
                  {t.count}
                </td>
              </tr>
            ))}
        </tbody>
      </table>

      <Button variant="primary" size="sm" onClick={onStart} className="self-start mt-1">
        Start Exam
      </Button>
    </div>
  )
}
