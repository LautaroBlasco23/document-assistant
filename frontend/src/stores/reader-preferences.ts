import { create } from 'zustand'

const STORAGE_KEY = 'docassist_reader_preferences'

export type ContentWidth = 'comfortable' | 'wide' | 'full'

interface ReaderPreferences {
  defaultShowLeft: boolean
  defaultShowRight: boolean
  contentWidth: ContentWidth
}

const DEFAULTS: ReaderPreferences = {
  defaultShowLeft: true,
  defaultShowRight: true,
  contentWidth: 'comfortable',
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
