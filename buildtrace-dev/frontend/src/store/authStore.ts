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

// Initialize with null values to avoid SSR hydration issues
// State will be loaded from localStorage after component mount
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  setUser: (user) => {
    set({ user, isAuthenticated: !!user })
    // Persist to localStorage (client-side only)
    if (typeof window !== 'undefined') {
      if (user) {
        localStorage.setItem('buildtrace-user', JSON.stringify(user))
      } else {
        localStorage.removeItem('buildtrace-user')
      }
    }
  },
  setToken: (token) => {
    set({ token })
    // Persist token to localStorage (client-side only)
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('buildtrace-token', token)
      } else {
        localStorage.removeItem('buildtrace-token')
      }
    }
  },
  clearUser: () => {
    set({ user: null, token: null, isAuthenticated: false })
    if (typeof window !== 'undefined') {
      localStorage.removeItem('buildtrace-user')
      localStorage.removeItem('buildtrace-token')
    }
  },
  setLoading: (isLoading) => set({ isLoading }),
}))

