import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../../stores/app-store'
import type { AppError } from '../../stores/app-store'

const AUTO_DISMISS_MS = 5000

function ErrorToast({ error }: { error: AppError }) {
  const removeError = useAppStore((s) => s.removeError)
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => removeError(error.id), AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [error.id, removeError])

  const handleLinkClick = () => {
    removeError(error.id)
    if (error.link) navigate(error.link)
  }

  return (
    <div className="flex items-start gap-3 bg-danger border border-danger text-text-inverse rounded-lg px-4 py-3 shadow-lg max-w-sm w-full">
      <span className="text-danger mt-0.5">✕</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm break-words">{error.message}</p>
        {error.link && (
          <button
            onClick={handleLinkClick}
            className="text-sm text-accent hover:text-accent underline mt-1"
          >
            {error.linkText ?? error.link}
          </button>
        )}
      </div>
      <button
        onClick={() => removeError(error.id)}
        className="text-danger hover:text-danger ml-1 shrink-0"
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
