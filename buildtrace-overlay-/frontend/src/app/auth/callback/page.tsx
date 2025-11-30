'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { toast } from 'react-hot-toast'

export default function OAuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { checkAuth, setLoading } = useAuthStore()

  useEffect(() => {
    const handleCallback = async () => {
      try {
        setLoading(true)

        // Check if there's an error from OAuth provider
        const error = searchParams.get('error')
        if (error) {
          toast.error(`Authentication failed: ${error}`)
          router.push('/login')
          return
        }

        // Wait a moment for the backend to set the session cookie
        await new Promise(resolve => setTimeout(resolve, 500))

        // Check authentication status with backend
        await checkAuth()

        // If successful, redirect to home
        toast.success('Successfully logged in!')
        router.push('/')
      } catch (error: any) {
        console.error('OAuth callback error:', error)
        toast.error(error.message || 'Authentication failed')
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }

    handleCallback()
  }, [searchParams, router, checkAuth, setLoading])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <LoadingSpinner size="lg" />
      <p className="mt-4 text-gray-600">Completing authentication...</p>
    </div>
  )
}

