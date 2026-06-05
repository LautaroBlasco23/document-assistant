import * as React from 'react'
import { Type, Minus, Plus, RotateCcw } from 'lucide-react'
import { cn } from '../../lib/cn'
import {
  useReaderPreferences,
  MIN_FONT_SCALE,
  MAX_FONT_SCALE,
  FONT_SCALE_STEP,
  MIN_CONTENT_WIDTH_PX,
  MAX_CONTENT_WIDTH_PX,
  CONTENT_WIDTH_PX_STEP,
  clampFontScale,
  clampContentWidthPx,
} from '../../stores/reader-preferences'

const DEBOUNCE_MS = 50

export function TextOptionsMenu() {
  const { preferences, update } = useReaderPreferences()
  const [open, setOpen] = React.useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  // Local state for instant visual feedback during range drag.
  const [localFontScale, setLocalFontScale] = React.useState(preferences.fontScale)
  const [localWidthPx, setLocalWidthPx] = React.useState(preferences.contentWidthPx)

  // Sync local state from store when dropdown opens.
  React.useEffect(() => {
    if (open) {
      const p = useReaderPreferences.getState().preferences
      setLocalFontScale(p.fontScale)
      setLocalWidthPx(p.contentWidthPx)
    }
  }, [open])

  // Debounced store write.
  const fontScaleTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const widthPxTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  const scheduleFontScale = React.useCallback((v: number) => {
    if (fontScaleTimerRef.current) clearTimeout(fontScaleTimerRef.current)
    fontScaleTimerRef.current = setTimeout(() => {
      update({ fontScale: clampFontScale(v) })
    }, DEBOUNCE_MS)
  }, [update])

  const scheduleWidthPx = React.useCallback((v: number | null) => {
    if (widthPxTimerRef.current) clearTimeout(widthPxTimerRef.current)
    widthPxTimerRef.current = setTimeout(() => {
      update({ contentWidthPx: clampContentWidthPx(v) })
    }, DEBOUNCE_MS)
  }, [update])

  React.useEffect(() => {
    return () => {
      if (fontScaleTimerRef.current) clearTimeout(fontScaleTimerRef.current)
      if (widthPxTimerRef.current) clearTimeout(widthPxTimerRef.current)
    }
  }, [])

  // Click-outside handler.
  React.useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        // Flush pending writes before closing.
        if (fontScaleTimerRef.current) clearTimeout(fontScaleTimerRef.current)
        if (widthPxTimerRef.current) clearTimeout(widthPxTimerRef.current)
        update({ fontScale: clampFontScale(localFontScale), contentWidthPx: clampContentWidthPx(localWidthPx) })
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open, localFontScale, localWidthPx, update])

  const handleFontChange = React.useCallback((v: number) => {
    const clamped = clampFontScale(v)
    setLocalFontScale(clamped)
    scheduleFontScale(clamped)
  }, [scheduleFontScale])

  const handleWidthChange = React.useCallback((v: number | null) => {
    const clamped = clampContentWidthPx(v)
    setLocalWidthPx(clamped)
    scheduleWidthPx(clamped)
  }, [scheduleWidthPx])

  const resetFont = React.useCallback(() => {
    setLocalFontScale(1)
    update({ fontScale: 1 })
    if (fontScaleTimerRef.current) clearTimeout(fontScaleTimerRef.current)
  }, [update])

  const resetWidth = React.useCallback(() => {
    setLocalWidthPx(null)
    update({ contentWidthPx: null })
    if (widthPxTimerRef.current) clearTimeout(widthPxTimerRef.current)
  }, [update])

  const resetAll = React.useCallback(() => {
    resetFont()
    resetWidth()
  }, [resetFont, resetWidth])

  return (
    <div ref={ref} className="relative flex items-center">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          'flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors border shadow-sm',
          'bg-surface dark:bg-surface-200 border-surface-200 dark:border-surface-200',
          'text-text-secondary hover:text-text-primary hover:bg-surface-100 dark:hover:bg-surface-100',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          open && 'bg-surface-100 dark:bg-surface-100'
        )}
        title="Text options"
      >
        <Type className="h-3.5 w-3.5" />
        <span>{Math.round(localFontScale * 100)}%</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-[70] bg-surface dark:bg-surface-200 rounded-lg shadow-lg border border-surface-200 dark:border-surface-200 py-2 px-3 min-w-[220px] space-y-3">
          {/* Font size */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                Font size
              </span>
              <span className="text-xs tabular-nums text-text-secondary">
                {Math.round(localFontScale * 100)}%
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => handleFontChange(localFontScale - FONT_SCALE_STEP)}
                disabled={localFontScale <= MIN_FONT_SCALE}
                className="p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
                aria-label="Decrease font size"
              >
                <Minus className="h-3 w-3" />
              </button>
              <input
                type="range"
                min={MIN_FONT_SCALE}
                max={MAX_FONT_SCALE}
                step={FONT_SCALE_STEP}
                value={localFontScale}
                onChange={(e) => handleFontChange(parseFloat(e.target.value))}
                aria-label="Font size"
                className="flex-1 h-1.5 accent-primary cursor-pointer"
              />
              <button
                onClick={() => handleFontChange(localFontScale + FONT_SCALE_STEP)}
                disabled={localFontScale >= MAX_FONT_SCALE}
                className="p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
                aria-label="Increase font size"
              >
                <Plus className="h-3 w-3" />
              </button>
            </div>
            <div className="flex justify-end">
              <button
                onClick={resetFont}
                disabled={localFontScale === 1}
                className="text-[10px] text-text-tertiary hover:text-text-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Width */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                Width
              </span>
              <span className="text-xs tabular-nums text-text-secondary">
                {localWidthPx != null ? `${localWidthPx}px` : 'Auto'}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => handleWidthChange((localWidthPx ?? MAX_CONTENT_WIDTH_PX) - CONTENT_WIDTH_PX_STEP)}
                disabled={localWidthPx != null && localWidthPx <= MIN_CONTENT_WIDTH_PX}
                className="p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
                aria-label="Decrease width"
              >
                <Minus className="h-3 w-3" />
              </button>
              <input
                type="range"
                min={MIN_CONTENT_WIDTH_PX}
                max={MAX_CONTENT_WIDTH_PX}
                step={CONTENT_WIDTH_PX_STEP}
                value={localWidthPx ?? MAX_CONTENT_WIDTH_PX}
                onChange={(e) => handleWidthChange(parseInt(e.target.value, 10))}
                aria-label="Content width"
                className="flex-1 h-1.5 accent-primary cursor-pointer"
              />
              <button
                onClick={() => handleWidthChange((localWidthPx ?? MIN_CONTENT_WIDTH_PX) + CONTENT_WIDTH_PX_STEP)}
                disabled={localWidthPx != null && localWidthPx >= MAX_CONTENT_WIDTH_PX}
                className="p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
                aria-label="Increase width"
              >
                <Plus className="h-3 w-3" />
              </button>
            </div>
            <div className="flex justify-end">
              <button
                onClick={resetWidth}
                disabled={localWidthPx == null}
                className="text-[10px] text-text-tertiary hover:text-text-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Reset all */}
          <div className="pt-1 border-t border-surface-200 dark:border-surface-200">
            <button
              onClick={resetAll}
              disabled={localFontScale === 1 && localWidthPx == null}
              className="w-full flex items-center justify-center gap-1 px-2 py-1 rounded text-xs text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <RotateCcw className="h-3 w-3" />
              Reset all
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
