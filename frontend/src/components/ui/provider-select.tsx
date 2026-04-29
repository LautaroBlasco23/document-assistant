import * as React from 'react'
import { ChevronDown, Check, Key } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'
import type { CredentialStatus } from '../../types/api'

interface ProviderSelectProps {
  value: string
  onChange: (value: string) => void
  credentials?: CredentialStatus[]
  className?: string
}

export function ProviderSelect({ value, onChange, credentials, className }: ProviderSelectProps) {
  const [open, setOpen] = React.useState(false)
  const containerRef = React.useRef<HTMLDivElement>(null)
  const { useProviders } = useProviderCredentials()
  const { providers, loading } = useProviders()

  React.useEffect(() => {
    if (!open) return
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [open])

  const credMap = React.useMemo(() => {
    const map = new Map<string, CredentialStatus>()
    if (credentials) {
      for (const c of credentials) {
        map.set(c.provider, c)
      }
    }
    return map
  }, [credentials])

  const selectedProvider = providers.find((p) => p.slug === value)

  const displayed = providers.filter((p) => {
    if (p.key_required) return true
    return true
  })

  const selectedLabel = selectedProvider ? selectedProvider.label : (value || 'Select provider')

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary cursor-pointer hover:border-border-strong transition-colors"
      >
        <span className="truncate">{selectedLabel}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-text-tertiary shrink-0 transition-transform duration-150',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-md shadow-lg max-h-72 overflow-y-auto">
          {loading ? (
            <div className="px-3 py-2 text-sm text-text-tertiary">Loading...</div>
          ) : displayed.length > 0 ? (
            displayed.map((p) => {
              const isSelected = p.slug === value
              const cred = credMap.get(p.slug)
              const configured = cred?.configured ?? false
              const needsKey = p.key_required && !configured

              return (
                <button
                  key={p.slug}
                  type="button"
                  onClick={() => { onChange(p.slug); setOpen(false) }}
                  className={cn(
                    'relative w-full flex items-center gap-2 px-3 py-2.5 text-sm text-left transition-colors',
                    needsKey && 'opacity-50',
                    isSelected
                      ? 'bg-primary-light dark:bg-primary/12 text-primary'
                      : 'text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
                  )}
                >
                  <span className="truncate flex-1">{p.label}</span>
                  {needsKey && (
                    <span className="shrink-0 flex items-center gap-1 text-xs text-warning">
                      <Key className="h-3 w-3" />
                      needs key
                    </span>
                  )}
                  {configured && (
                    <span className="shrink-0 w-2 h-2 rounded-full bg-success" />
                  )}
                  {isSelected && (
                    <Check className="h-3.5 w-3.5 shrink-0 text-primary" />
                  )}
                </button>
              )
            })
          ) : (
            <div className="px-3 py-2 text-sm text-text-tertiary">
              {value || 'No providers available'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
