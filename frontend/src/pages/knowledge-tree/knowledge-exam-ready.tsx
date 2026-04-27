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

      <div className="self-start border-2 border-gray-300 dark:border-slate-500 rounded-lg overflow-hidden">
        <table style={{ minWidth: '280px', borderCollapse: 'collapse' }} className="text-xs">
          <thead>
            <tr className="bg-gray-100 dark:bg-slate-700 border-b-2 border-gray-300 dark:border-slate-500">
              <th className="px-4 py-2 text-left font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wide text-[10px] whitespace-nowrap border-r-2 border-gray-300 dark:border-slate-500">
                Question Type
              </th>
              <th className="px-4 py-2 text-right font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wide text-[10px] whitespace-nowrap">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {typeCounts
              .filter((t) => t.count > 0)
              .map((t) => (
                <tr key={t.label} className="border-t border-gray-200 dark:border-slate-600">
                  <td className="px-4 py-2 text-gray-700 dark:text-slate-300 whitespace-nowrap border-r-2 border-gray-300 dark:border-slate-500">{t.label}</td>
                  <td className="px-4 py-2 text-right font-semibold tabular-nums text-gray-800 dark:text-slate-200">
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
