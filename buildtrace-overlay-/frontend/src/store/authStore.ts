import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, AuthState } from '@/types'
import { apiClient } from '@/lib/api'

interface AuthStore extends AuthState {
  login: (email: string, password: string) => Promise<void>
  loginWithGoogle: () => Promise<void>
  logout: () => Promise<void>
  signup: (email: string, password: string, name?: string) => Promise<void>
  checkAuth: () => Promise<void>
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      user: null,
      isLoading: true,

      login: async (email: string, password: string) => {
        try {
          set({ isLoading: true })
          const response = await apiClient.post('/auth/login', { email, password })

          if (response.success && response.data?.user) {
            set({
              isAuthenticated: true,
              user: response.data.user,
              isLoading: false
            })
          } else {
            throw new Error(response.error || 'Login failed')
          }
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      loginWithGoogle: async () => {
        try {
          set({ isLoading: true })
          // Redirect to Google OAuth endpoint
          window.location.href = '/auth/google'
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: async () => {
        try {
          await apiClient.post('/auth/logout')
        } catch (error) {
          console.warn('Logout request failed:', error)
        } finally {
          set({
            isAuthenticated: false,
            user: null,
            isLoading: false
          })
          // Clear persisted storage
          localStorage.removeItem('auth-storage')
        }
      },

      signup: async (email: string, password: string, name?: string) => {
        try {
          set({ isLoading: true })
          const response = await apiClient.post('/auth/signup', {
            email,
            password,
            name
          })

          if (response.success && response.data?.user) {
            set({
              isAuthenticated: true,
              user: response.data.user,
              isLoading: false
            })
          } else {
            throw new Error(response.error || 'Signup failed')
          }
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      checkAuth: async () => {
        try {
          set({ isLoading: true })
          const response = await apiClient.get('/auth/me')

          if (response.success && response.data?.user) {
            set({
              isAuthenticated: true,
              user: response.data.user,
              isLoading: false
            })
          } else {
            set({
              isAuthenticated: false,
              user: null,
              isLoading: false
            })
          }
        } catch (error) {
          console.warn('Auth check failed:', error)
          set({
            isAuthenticated: false,
            user: null,
            isLoading: false
          })
        }
      },

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: !!user })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user
      })
    }
  )
)