import { create } from 'zustand'
import type { HealthOut } from '../types/api'

export interface AppError {
  id: string
  message: string
}

interface AppState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  serviceHealth: HealthOut | null
  setServiceHealth: (h: HealthOut | null) => void
  errors: AppError[]
  addError: (message: string) => void
  removeError: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  serviceHealth: null,
  setServiceHealth: (h) => set({ serviceHealth: h }),
  errors: [],
  addError: (message) =>
    set((state) => ({
      errors: [...state.errors, { id: crypto.randomUUID(), message }],
    })),
  removeError: (id) =>
    set((state) => ({ errors: state.errors.filter((e) => e.id !== id) })),
}))
