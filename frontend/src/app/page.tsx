'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import UploadPage from '@/components/pages/UploadPage'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

export default function Home() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, setUser, setLoading } = useAuthStore()

  useEffect(() => {
    // Only check auth once on mount, or if not authenticated
    if (isAuthenticated && user) {
      return // Already authenticated, no need to check
    }

    let mounted = true

    const checkAuth = async () => {
      try {
        setLoading(true)
        // API client interceptor returns response.data directly
        // So response IS the user object: { user_id, email, name, ... }
        const userData: any = await apiClient.getCurrentUser()
        if (mounted) {
          if (userData && userData.user_id) {
            setUser(userData)
          } else {
            // Not authenticated - redirect to login
            router.push('/login')
          }
        }
      } catch (error) {
        if (mounted) {
          // Not authenticated - redirect to login
          router.push('/login')
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    checkAuth()

    return () => {
      mounted = false
    }
  }, []) // Only run once on mount

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return null // Will redirect
  }

  return <UploadPage />
}

