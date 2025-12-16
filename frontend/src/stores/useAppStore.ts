import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  // UI State
  theme: 'light' | 'dark' | 'system'
  sidebarOpen: boolean

  // User Preferences
  preferredLLMModel: string

  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  toggleTheme: () => void
  toggleSidebar: () => void
  setPreferredLLMModel: (model: string) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Initial state
      theme: 'system',
      sidebarOpen: true,
      preferredLLMModel: 'llama3.1:8b',

      // Actions
      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set((state) => {
          const cycle = { light: 'dark', dark: 'system', system: 'light' } as const
          return { theme: cycle[state.theme] }
        }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setPreferredLLMModel: (model) => set({ preferredLLMModel: model }),
    }),
    {
      name: 'skillforge-app-storage',
    }
  )
)
