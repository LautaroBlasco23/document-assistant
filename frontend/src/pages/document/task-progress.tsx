import { Progress } from '../../components/ui/progress'

interface TaskProgressProps {
  progressPct: number | null
  message: string | null
  fallbackMessage: string
}

export function TaskProgress({ progressPct, message, fallbackMessage }: TaskProgressProps) {
  const isDeterminate = progressPct !== null && progressPct > 0
  const displayMessage = message || fallbackMessage

  return (
    <div className="flex flex-col gap-2">
      {isDeterminate ? (
        <Progress value={progressPct} />
      ) : (
        <Progress indeterminate />
      )}
      <div className="flex items-center gap-2">
        <p className="text-xs text-gray-400">{displayMessage}</p>
        {isDeterminate && (
          <span className="text-xs font-medium text-gray-500">{progressPct}%</span>
        )}
      </div>
    </div>
  )
}
