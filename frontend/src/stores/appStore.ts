import { create } from 'zustand'

interface AppState {
  currentBook: string | null
  setCurrentBook: (book: string) => void

  serviceHealth: {
    status: string
    services: Array<{ name: string; healthy: boolean; error?: string }>
  } | null
  setServiceHealth: (health: AppState['serviceHealth']) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentBook: null,
  setCurrentBook: (book: string) => set({ currentBook: book }),

  serviceHealth: null,
  setServiceHealth: (health) => set({ serviceHealth: health }),
}))
