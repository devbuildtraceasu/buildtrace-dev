'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import ResultsPage from '@/components/pages/ResultsPage'

export default function ResultsRoute() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, setUser, setLoading } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated && user) {
      return
    }

    let mounted = true
    const checkAuth = async () => {
      try {
        setLoading(true)
        const userData: any = await apiClient.getCurrentUser()
        if (mounted) {
          if (userData && userData.user_id) {
            setUser(userData)
          } else {
            router.push('/login')
          }
        }
      } catch (error) {
        if (mounted) {
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
  }, [isAuthenticated, user, router, setLoading, setUser])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return null
  }

  return <ResultsPage />
}
