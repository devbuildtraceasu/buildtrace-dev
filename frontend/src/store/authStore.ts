import { create } from 'zustand'

export interface User {
  user_id: string
  email: string
  name: string
  company?: string
  role?: string
  organization_id?: string
  email_verified: boolean
  is_active: boolean
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: User | null) => void
  clearUser: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  setUser: (user) => {
    set({ user, isAuthenticated: !!user })
    // Persist to localStorage
    if (user) {
      localStorage.setItem('buildtrace-user', JSON.stringify(user))
    } else {
      localStorage.removeItem('buildtrace-user')
    }
  },
  clearUser: () => {
    set({ user: null, isAuthenticated: false })
    localStorage.removeItem('buildtrace-user')
  },
  setLoading: (isLoading) => set({ isLoading }),
}))

// Load user from localStorage on init
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('buildtrace-user')
  if (stored) {
    try {
      const user = JSON.parse(stored)
      useAuthStore.getState().setUser(user)
    } catch (e) {
      localStorage.removeItem('buildtrace-user')
    }
  }
}

