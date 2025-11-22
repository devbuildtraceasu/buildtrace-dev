'use client'

import React, { useEffect } from 'react'
import Link from 'next/link'
import LoginButton from '@/components/auth/LoginButton'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'

export default function Header() {
  const { user, isAuthenticated, setUser, setLoading } = useAuthStore()

  useEffect(() => {
    // Only check auth if not already authenticated
    if (user && isAuthenticated) {
      return // Already have user, no need to check
    }

    let mounted = true

    const checkAuth = async () => {
      try {
        setLoading(true)
        const userData: any = await apiClient.getCurrentUser()
        if (mounted && userData && userData.user_id) {
          setUser(userData)
        } else if (mounted) {
          setUser(null)
        }
      } catch (error) {
        // Not authenticated or error
        if (mounted) {
          setUser(null)
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

  // Check for OAuth callback - only run once
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const authStatus = urlParams.get('auth')
    const userId = urlParams.get('user_id')
    const error = urlParams.get('error')

    if (authStatus === 'success' && userId) {
      // Fetch user info after successful login
      apiClient.getCurrentUser()
        .then((userData: any) => {
          // API client interceptor returns response.data directly
          // So userData IS the user object: { user_id, email, name, ... }
          if (userData && userData.user_id) {
            setUser(userData)
            // Clean up URL first
            window.history.replaceState({}, '', window.location.pathname)
            // Then refresh to show upload page
            window.location.reload()
          } else {
            console.error('Invalid user data received:', userData)
            window.history.replaceState({}, '', window.location.pathname)
          }
        })
        .catch(err => {
          console.error('Failed to fetch user:', err)
          // Clean up URL even on error
          window.history.replaceState({}, '', window.location.pathname)
        })
    } else if (error) {
      console.error('Authentication error:', error)
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, []) // Only run once on mount

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Brand */}
          <Link href="/" className="flex items-center space-x-3">
            <div className="text-2xl font-bold text-blue-600">
              BuildTrace AI
            </div>
          </Link>

          {/* Tagline */}
          <div className="hidden md:block">
            <p className="text-sm text-gray-600">
              Intelligent Drawing Comparison & Analysis
            </p>
          </div>

          {/* Navigation */}
          <div className="flex items-center space-x-4">
            <Link href="/">
              <span className="text-sm text-gray-600 hover:text-gray-900">Home</span>
            </Link>
            <Link href="/results">
              <span className="text-sm text-gray-600 hover:text-gray-900">Results</span>
            </Link>
            <LoginButton />
          </div>
        </div>
      </div>
    </header>
  )
}
