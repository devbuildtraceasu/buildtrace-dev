'use client'

import React from 'react'
import Button from '@/components/ui/Button'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'

export default function LoginButton() {
  const { isAuthenticated, user } = useAuthStore()
  const isMockMode = process.env.NEXT_PUBLIC_USE_MOCKS === 'true'

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

  if (isAuthenticated && user) {
    return (
      <div className="flex items-center space-x-4">
        <span className="text-sm text-gray-700">
          {user.name || user.email}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={async () => {
            try {
              await apiClient.logout()
              useAuthStore.getState().clearUser()
              window.location.href = '/'
            } catch (error) {
              console.error('Logout failed:', error)
            }
          }}
        >
          Logout
        </Button>
        {isMockMode && (
          <span className="text-xs font-semibold text-green-600 uppercase tracking-wide">
            Mock Mode
          </span>
        )}
      </div>
    )
  }

  if (isMockMode) {
    return (
      <Button
        size="sm"
        onClick={async () => {
          const { mockUser } = await import('@/mocks/data')
          useAuthStore.getState().setUser(mockUser)
          useAuthStore.getState().setToken('mock-token')
        }}
      >
        Use Mock User
      </Button>
    )
  }

  return (
    <Button onClick={handleLogin} size="sm">
      Sign in with Google
    </Button>
  )
}

