import * as React from 'react'
import { ChevronDown, Check, Star, Zap, Sparkles, Search } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useReducedMotion } from '../../hooks/use-reduced-motion'
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
  const reducedMotion = useReducedMotion()
  if (reducedMotion) return null
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
          ? 'text-success bg-success-light'
          : 'text-warning bg-warning-light',
      )}
    >
      {role}
    </span>
  )
}

const TIER_CONFIG: Record<string, { label: string; icon: typeof Star; color: string; dotColor: string }> = {
  high: {
    label: 'high',
    icon: Star,
    color: 'text-warning bg-warning-light',
    dotColor: 'bg-warning',
  },
  medium: {
    label: 'medium',
    icon: Zap,
    color: 'text-info bg-info-light',
    dotColor: 'bg-info',
  },
  low: {
    label: 'low',
    icon: Sparkles,
    color: 'text-text-secondary bg-surface-100',
    dotColor: 'bg-surface-200',
  },
}

function QualityBadge({ tier }: { tier: string }) {
  const config = TIER_CONFIG[tier]
  if (!config) return null
  const Icon = config.icon
  return (
    <span className={cn('text-xs font-semibold px-1.5 py-0.5 rounded', config.color)}>
      <Icon className="inline-block w-3 h-3 mr-0.5 -mt-0.5" />
      {config.label}
    </span>
  )
}

function QualityDot({ tier, className }: { tier: string; className?: string }) {
  const config = TIER_CONFIG[tier]
  if (!config) return null
  return (
    <span
      className={cn('inline-block w-2 h-2 rounded-full shrink-0', config.dotColor, className)}
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
  const [searchQuery, setSearchQuery] = React.useState('')
  const containerRef = React.useRef<HTMLDivElement>(null)
  const searchInputRef = React.useRef<HTMLInputElement>(null)

  const selectedModel = models.find((m) => m.id === value) ?? null

  const filteredModels = React.useMemo(() => {
    if (!searchQuery.trim()) return models
    const q = searchQuery.toLowerCase()
    return models.filter(
      (m) =>
        m.label.toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q) ||
        m.role?.toLowerCase().includes(q),
    )
  }, [models, searchQuery])

  const handleOpen = React.useCallback(() => {
    setOpen((v) => {
      const next = !v
      if (next) {
        setSearchQuery('')
        requestAnimationFrame(() => searchInputRef.current?.focus())
      }
      return next
    })
  }, [])

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
        onClick={handleOpen}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 border border-ai-border rounded-md text-sm bg-surface dark:bg-surface-200 text-text-primary cursor-pointer hover:border-ai transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      >
        <span className="flex items-center gap-2 min-w-0">
          <QualityDot tier={selectedModel?.quality_tier ?? 'medium'} />
          <span className="truncate">{displayLabel}</span>
          {selectedModel?.role && <RoleBadge role={selectedModel.role} />}
          {selectedModel?.quality_tier && <QualityBadge tier={selectedModel.quality_tier} />}
        </span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-text-tertiary shrink-0 transition-transform duration-150',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-surface dark:bg-surface-200 border border-ai-border rounded-md shadow-lg max-h-80 overflow-hidden flex flex-col">
          {models.length > 0 && (
            <div className="sticky top-0 px-3 py-2 border-b border-ai-border bg-surface dark:bg-surface-200 z-10">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-tertiary pointer-events-none" />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search models..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') {
                      setOpen(false)
                      setSearchQuery('')
                    }
                  }}
                  className="w-full pl-7 pr-3 py-1.5 text-sm bg-surface-100 dark:bg-surface-100 border border-ai-border rounded-md text-text-primary placeholder:text-text-tertiary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />
              </div>
            </div>
          )}
          <div className="overflow-y-auto max-h-64">
          {filteredModels.length > 0 ? (
            filteredModels.map((m) => {
              const isSelected = m.id === value
              return (
                <button
                  key={m.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => { onChange(m.id); setOpen(false); setSearchQuery('') }}
                  className={cn(
                    'relative w-full flex items-center gap-2 px-3 py-2.5 text-sm text-left overflow-hidden transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset',
                    isSelected
                      ? 'bg-primary-light dark:bg-primary/12 text-primary'
                      : 'text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
                  )}
                >
                  <OptionParticles role={m.role} />
                  <QualityDot tier={m.quality_tier ?? 'medium'} />
                  <span className="truncate">{m.label}</span>
                  <RoleBadge role={m.role} />
                  <QualityBadge tier={m.quality_tier ?? 'medium'} />
                  {isSelected && (
                    <Check className="h-3.5 w-3.5 shrink-0 ml-1 text-primary" />
                  )}
                </button>
              )
            })
          ) : (
            <div className="px-3 py-4 text-sm text-text-tertiary text-center">
              {models.length > 0 ? 'No models match your search.' : (fallback ?? value)}
            </div>
          )}
          </div>
        </div>
      )}
    </div>
  )
}
