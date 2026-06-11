import { create } from 'zustand'

const STORAGE_KEY = 'docassist_reader_preferences'

export type ContentWidth = 'comfortable' | 'wide' | 'full'

const DEFAULT_FONT_SCALE = 1
export const MIN_FONT_SCALE = 0.75
export const MAX_FONT_SCALE = 2
export const FONT_SCALE_STEP = 0.05

const DEFAULT_CONTENT_WIDTH_PX: number | null = null
export const MIN_CONTENT_WIDTH_PX = 400
export const MAX_CONTENT_WIDTH_PX = 1600
export const CONTENT_WIDTH_PX_STEP = 20

interface ReaderPreferences {
  defaultShowLeft: boolean
  defaultShowRight: boolean
  contentWidth: ContentWidth
  /** Font scale multiplier (0.75–2). Applied as font-size percentage to text content. */
  fontScale: number
  /** Custom content max-width override in px. null = use categorical contentWidth. */
  contentWidthPx: number | null
  /** When false, hides local LLM providers (Ollama, llama.cpp) from provider dropdowns. */
  showLocalProviders: boolean
}

const DEFAULTS: ReaderPreferences = {
  defaultShowLeft: true,
  defaultShowRight: true,
  contentWidth: 'comfortable',
  fontScale: DEFAULT_FONT_SCALE,
  contentWidthPx: DEFAULT_CONTENT_WIDTH_PX,
  showLocalProviders: true,
}

/** Clamp fontScale to valid range, falling back to 1 if NaN. */
export function clampFontScale(v: number): number {
  return Number.isFinite(v) ? Math.max(MIN_FONT_SCALE, Math.min(MAX_FONT_SCALE, v)) : DEFAULT_FONT_SCALE
}

/** Clamp contentWidthPx to valid range, or null if out of range / NaN. */
export function clampContentWidthPx(v: number | null | undefined): number | null {
  if (v == null || !Number.isFinite(v)) return null
  const clamped = Math.max(MIN_CONTENT_WIDTH_PX, Math.min(MAX_CONTENT_WIDTH_PX, v))
  return clamped
}

export function load(): ReaderPreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return { ...DEFAULTS, ...parsed }
    }
  } catch { /* ignore */ }
  return { ...DEFAULTS }
}

function save(value: ReaderPreferences) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch { /* ignore */ }
}

interface ReaderPreferencesState {
  preferences: ReaderPreferences
  update: (patch: Partial<ReaderPreferences>) => void
}

export const useReaderPreferences = create<ReaderPreferencesState>((set, get) => ({
  preferences: load(),
  update: (patch) => {
    const next = { ...get().preferences, ...patch }
    save(next)
    set({ preferences: next })
  },
}))
