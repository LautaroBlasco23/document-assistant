import * as React from 'react'
import { ChevronDown, Check } from 'lucide-react'
import { cn } from '../../lib/cn'
import type { ModelInfo } from '../../types/api'

const PARTICLES: Array<{ x: number; delay: number }> = [
  { x: 6,  delay: 0    },
  { x: 14, delay: 0.35 },
  { x: 24, delay: 0.65 },
  { x: 34, delay: 0.2  },
  { x: 44, delay: 0.5  },
  { x: 54, delay: 0.8  },
]

function OptionParticles({ role }: { role: string | null }) {
  if (role !== 'main' && role !== 'fast') return null
  return (
    <>
      {PARTICLES.map(({ x, delay }, i) => (
        <span
          key={i}
          className={cn(
            'model-particle',
            role === 'main' ? 'model-particle-green' : 'model-particle-orange',
          )}
          style={{ left: x, bottom: 2, animationDelay: `${delay}s` } as React.CSSProperties}
        />
      ))}
    </>
  )
}

function RoleBadge({ role }: { role: string | null }) {
  if (!role) return null
  const isMain = role === 'main'
  return (
    <span
      className={cn(
        'ml-auto shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded',
        isMain
          ? 'text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30'
          : 'text-orange-700 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/30',
      )}
    >
      {role}
    </span>
  )
}

function RoleDot({ role, className }: { role: string | null; className?: string }) {
  if (!role) return null
  return (
    <span
      className={cn(
        'inline-block w-2 h-2 rounded-full shrink-0',
        role === 'main' ? 'bg-green-500' : 'bg-orange-500',
        className,
      )}
    />
  )
}

interface ModelSelectProps {
  value: string
  onChange: (value: string) => void
  models: ModelInfo[]
  fallback?: string
  className?: string
}

export function ModelSelect({ value, onChange, models, fallback, className }: ModelSelectProps) {
  const [open, setOpen] = React.useState(false)
  const containerRef = React.useRef<HTMLDivElement>(null)

  const selectedModel = models.find((m) => m.id === value) ?? null

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

  const displayLabel = selectedModel
    ? selectedModel.label
    : (fallback ?? value)

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 border border-surface-200 dark:border-surface-200 rounded-md text-sm bg-surface dark:bg-surface-200 text-gray-800 dark:text-slate-200 cursor-pointer hover:border-gray-300 dark:hover:border-slate-500 transition-colors"
      >
        <span className="flex items-center gap-2 min-w-0">
          <RoleDot role={selectedModel?.role ?? null} />
          <span className="truncate">{displayLabel}</span>
          {selectedModel?.role && <RoleBadge role={selectedModel.role} />}
        </span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-gray-400 shrink-0 transition-transform duration-150',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-surface dark:bg-surface-200 border border-surface-200 dark:border-surface-200 rounded-md shadow-lg max-h-72 overflow-y-auto">
          {models.length > 0 ? (
            models.map((m) => {
              const isSelected = m.id === value
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => { onChange(m.id); setOpen(false) }}
                  className={cn(
                    'relative w-full flex items-center gap-2 px-3 py-2.5 text-sm text-left overflow-hidden transition-colors',
                    isSelected
                      ? 'bg-primary-light dark:bg-primary/12 text-primary'
                      : 'text-gray-800 dark:text-slate-200 hover:bg-surface-100 dark:hover:bg-surface-100',
                  )}
                >
                  <OptionParticles role={m.role} />
                  <RoleDot role={m.role} />
                  <span className="truncate">{m.label}</span>
                  <RoleBadge role={m.role} />
                    {isSelected && (
                      <Check className="h-3.5 w-3.5 shrink-0 ml-1 text-primary" />
                    )}
                </button>
              )
            })
          ) : (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
              {fallback ?? value}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
