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

// Load initial state from localStorage
const getInitialState = () => {
  if (typeof window === 'undefined') {
    return { user: null, token: null }
  }
  
  let user = null
  let token = null
  
  try {
    const storedUser = localStorage.getItem('buildtrace-user')
    if (storedUser) {
      user = JSON.parse(storedUser)
    }
  } catch (e) {
    console.warn('Failed to parse stored user:', e)
    localStorage.removeItem('buildtrace-user')
  }
  
  token = localStorage.getItem('buildtrace-token')
  
  return { user, token }
}

const initialState = getInitialState()

export const useAuthStore = create<AuthState>((set) => ({
  user: initialState.user,
  token: initialState.token,
  isAuthenticated: !!initialState.user,
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

