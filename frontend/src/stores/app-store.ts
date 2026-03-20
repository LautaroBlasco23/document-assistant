import { create } from 'zustand'
import type { HealthOut } from '../types/api'

interface AppState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  serviceHealth: HealthOut | null
  setServiceHealth: (h: HealthOut | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  serviceHealth: null,
  setServiceHealth: (h) => set({ serviceHealth: h }),
}))
