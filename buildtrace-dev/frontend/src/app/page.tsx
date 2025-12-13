'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import UploadPage from '@/components/pages/UploadPage'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

export default function Home() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, setUser, setLoading, setToken } = useAuthStore()
  const isMockMode = process.env.NEXT_PUBLIC_USE_MOCKS === 'true'

  // Initialize from localStorage on mount (client-side only) - run only once
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    // Check if we've already initialized to avoid re-running
    const currentState = useAuthStore.getState()
    if (currentState.user || currentState.token) {
      return // Already initialized
    }
    
    try {
      const storedUser = localStorage.getItem('buildtrace-user')
      const storedToken = localStorage.getItem('buildtrace-token')
      
      if (storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser)
          setUser(parsedUser)
        } catch (parseError) {
          console.warn('[Home] Failed to parse stored user:', parseError)
          localStorage.removeItem('buildtrace-user')
        }
      }
      if (storedToken) {
        setToken(storedToken)
      }
    } catch (e) {
      console.warn('[Home] Failed to load from localStorage:', e)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

  useEffect(() => {
    if (!isMockMode || typeof window === 'undefined') {
      return
    }
    ;(window as any).__USE_MOCKS__ = true
    let cancelled = false
    ;(async () => {
      try {
        const { mockUser } = await import('@/mocks/data')
        if (!cancelled) {
          setUser(mockUser)
          setToken('mock-token')
          setLoading(false)
        }
      } catch (error) {
        console.warn('[Home] Failed to load mock user', error)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isMockMode, setUser, setToken, setLoading])

  useEffect(() => {
    if (isMockMode) {
      return
    }
    let mounted = true

    const checkAuth = async () => {
      console.log('[Home] Checking authentication...')
      try {
        setLoading(true)
        const userData: any = await apiClient.getCurrentUser()
        if (mounted) {
          if (userData && userData.user_id) {
            console.log('[Home] Authentication successful:', { user_id: userData.user_id })
            setUser(userData)
          } else {
            console.log('[Home] No valid user data - redirecting to login')
            router.push('/login')
          }
        }
      } catch (error) {
        console.log('[Home] Authentication failed - redirecting to login')
        if (mounted) {
          router.push('/login')
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    const processOAuthCallback = () => {
      if (typeof window === 'undefined') {
        return false
      }

      const urlParams = new URLSearchParams(window.location.search)
      const authStatus = urlParams.get('auth')
      if (authStatus !== 'success') {
        return false
      }

      const token = urlParams.get('token')
      const userId = urlParams.get('user_id')
      const userEmail = urlParams.get('email') || ''
      const userName = urlParams.get('name') || ''

      if (!token || !userId) {
        console.error('[Home] OAuth callback detected but token or user ID missing', {
          hasToken: !!token,
          userId,
        })
        router.push('/login')
        return true
      }

      console.log('[Home] OAuth callback detected - storing token and user info')
      setLoading(true)
      setToken(token)

      const userData = {
        user_id: userId,
        email: userEmail,
        name: userName,
        email_verified: true,
        is_active: true,
      }

      setUser(userData)
      window.history.replaceState({}, '', window.location.pathname)
      setLoading(false)

      setTimeout(() => {
        apiClient
          .getCurrentUser()
          .then((backendUser: any) => {
            if (backendUser && backendUser.user_id) {
              console.log('[Home] Backend verification after OAuth succeeded')
              setUser(backendUser)
            }
          })
          .catch((err) => {
            console.warn('[Home] Backend verification after OAuth failed (non-critical):', err.message)
          })
      }, 150)

      return true
    }

    const handledOAuth = processOAuthCallback()
    if (handledOAuth) {
      console.log('[Home] OAuth callback handled within Home component')
      return () => {
        mounted = false
      }
    }

    if (isAuthenticated && user) {
      console.log('[Home] Already authenticated:', { user_id: user.user_id })
      // Ensure loading is false when already authenticated
      setLoading(false)
      return () => {
        mounted = false
      }
    }

    console.log('[Home] No active session - checking with backend...')
    checkAuth()

    return () => {
      mounted = false
    }
  }, [isAuthenticated, user, router, setUser, setLoading, setToken])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
        <div className="ml-4 text-gray-600">
          {typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('auth') === 'success'
            ? 'Completing authentication...'
            : 'Loading...'}
        </div>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    console.log('[Home] Not authenticated - rendering null (redirect in progress)')
    return null
  }

  console.log('[Home] Rendering UploadPage for authenticated user')
  return <UploadPage />
}
