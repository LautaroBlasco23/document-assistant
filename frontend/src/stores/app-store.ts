import { create } from 'zustand'
import type { HealthOut } from '../types/api'

export interface AppError {
  id: string
  message: string
  link?: string
  linkText?: string
}

export interface AddErrorOpts {
  link?: string
  linkText?: string
}

interface AppState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  serviceHealth: HealthOut | null
  setServiceHealth: (h: HealthOut | null) => void
  errors: AppError[]
  addError: (message: string, opts?: AddErrorOpts) => void
  removeError: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  serviceHealth: null,
  setServiceHealth: (h) => set({ serviceHealth: h }),
  errors: [],
  addError: (message, opts) =>
    set((state) => ({
      errors: [...state.errors, { id: crypto.randomUUID(), message, ...opts }],
    })),
  removeError: (id) =>
    set((state) => ({ errors: state.errors.filter((e) => e.id !== id) })),
}))
