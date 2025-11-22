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
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  clearUser: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
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
  setToken: (token) => {
    set({ token })
    // Persist token to localStorage
    if (token) {
      localStorage.setItem('buildtrace-token', token)
    } else {
      localStorage.removeItem('buildtrace-token')
    }
  },
  clearUser: () => {
    set({ user: null, token: null, isAuthenticated: false })
    localStorage.removeItem('buildtrace-user')
    localStorage.removeItem('buildtrace-token')
  },
  setLoading: (isLoading) => set({ isLoading }),
}))

// Load user and token from localStorage on init
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('buildtrace-user')
  const storedToken = localStorage.getItem('buildtrace-token')
  if (stored) {
    try {
      const user = JSON.parse(stored)
      useAuthStore.getState().setUser(user)
    } catch (e) {
      localStorage.removeItem('buildtrace-user')
    }
  }
  if (storedToken) {
    useAuthStore.getState().setToken(storedToken)
  }
}

