'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, setUser, setLoading } = useAuthStore()

  useEffect(() => {
    const checkAuth = async () => {
      if (isAuthenticated && user) {
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        const response = await apiClient.getCurrentUser()
        if (response.data) {
          setUser(response.data)
        } else {
          // Not authenticated - redirect to login
          router.push('/login')
        }
      } catch (error) {
        // Not authenticated - redirect to login
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  }, [isAuthenticated, user, setUser, setLoading, router])

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

  return <>{children}</>
}

