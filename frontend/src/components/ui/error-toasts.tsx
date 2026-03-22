import { useEffect } from 'react'
import { useAppStore } from '../../stores/app-store'
import type { AppError } from '../../stores/app-store'

const AUTO_DISMISS_MS = 5000

function ErrorToast({ error }: { error: AppError }) {
  const removeError = useAppStore((s) => s.removeError)

  useEffect(() => {
    const timer = setTimeout(() => removeError(error.id), AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [error.id, removeError])

  return (
    <div className="flex items-start gap-3 bg-red-900/90 border border-red-700 text-red-100 rounded-lg px-4 py-3 shadow-lg max-w-sm w-full">
      <span className="text-red-400 mt-0.5">✕</span>
      <p className="text-sm flex-1 break-words">{error.message}</p>
      <button
        onClick={() => removeError(error.id)}
        className="text-red-400 hover:text-red-200 ml-1 shrink-0"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  )
}

export function ErrorToasts() {
  const errors = useAppStore((s) => s.errors)

  if (errors.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {errors.map((e) => (
        <ErrorToast key={e.id} error={e} />
      ))}
    </div>
  )
}
