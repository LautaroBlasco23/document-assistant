import { create } from 'zustand'
import type { GenerationParams } from '../types/api'

const STORAGE_KEY = 'docassist_generation_settings'

function load(): GenerationParams {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as GenerationParams
  } catch { /* ignore */ }
  return { temperature: 0.7, top_p: 1.0, max_tokens: 1024 }
}

function save(value: GenerationParams) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch { /* ignore */ }
}

interface GenerationSettingsState {
  settings: GenerationParams
  update: (patch: Partial<GenerationParams>) => void
  /**
   * Reset the model override so the app uses the backend default.
   * Call this after the models list has been fetched and the
   * previously stored model is no longer supported.
   */
  clearModel: () => void
}

export const useGenerationSettings = create<GenerationSettingsState>((set, get) => ({
  settings: load(),
  update: (patch) => {
    const next = { ...get().settings, ...patch }
    save(next)
    set({ settings: next })
  },
  clearModel: () => {
    const next = { ...get().settings }
    delete next.model
    save(next)
    set({ settings: next })
  },
}))
