'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Header from '@/components/layout/Header'

export default function LoginPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()

  useEffect(() => {
    // If already authenticated, redirect to home (upload/comparison page)
    if (isAuthenticated && user) {
      router.push('/')
    }
    
    // Also check for OAuth callback in URL (in case user lands here after OAuth)
    const urlParams = new URLSearchParams(window.location.search)
    const authStatus = urlParams.get('auth')
    if (authStatus === 'success') {
      // OAuth callback detected - Header component will handle it, then redirect
      // Just ensure we're on home page
      router.push('/')
    }
  }, [isAuthenticated, user, router])

  const handleLogin = async () => {
    try {
      console.log('Initiating Google login...')
      const response: any = await apiClient.googleLogin()
      console.log('Login response:', response)
      
      // API client interceptor returns response.data directly
      // So response is already the JSON body: { auth_url: ..., state: ... }
      const authUrl = response?.auth_url || response?.data?.auth_url
      
      if (authUrl) {
        console.log('Redirecting to:', authUrl)
        // Redirect to Google OAuth
        window.location.href = authUrl
      } else {
        console.error('No auth_url in response:', response)
        alert('Failed to get authentication URL. Please check console for details.')
      }
    } catch (error: any) {
      console.error('Login failed:', error)
      alert(error.message || 'Failed to initiate login')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <Card className="max-w-md w-full p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome to BuildTrace AI
            </h1>
            <p className="text-gray-600">
              Sign in to compare and analyze your architectural drawings
            </p>
          </div>

          <div className="space-y-4">
            <Button
              onClick={handleLogin}
              className="w-full"
              size="lg"
            >
              Sign in with Google
            </Button>

            <p className="text-sm text-gray-500 text-center mt-6">
              By signing in, you agree to use BuildTrace AI for drawing comparison and analysis.
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}

