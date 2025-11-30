'use client'

import React, { useEffect } from 'react'
import Link from 'next/link'
import LoginButton from '@/components/auth/LoginButton'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'

export default function Header() {
  const { user, isAuthenticated, setUser, setToken, setLoading } = useAuthStore()

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
    const userEmail = urlParams.get('email')
    const userName = urlParams.get('name')
    const token = urlParams.get('token')
    const error = urlParams.get('error')

    if (authStatus === 'success' && userId && token) {
      console.log('[OAuth] Callback received:', { userId, email: userEmail, token: token.substring(0, 20) + '...' })
      
      // Store JWT token first - this must happen before any API calls
      setToken(token)
      console.log('[OAuth] Token stored in Zustand store')
      
      // Verify token is stored in localStorage
      const storedToken = localStorage.getItem('buildtrace-token')
      console.log('[OAuth] Token in localStorage:', storedToken ? 'YES (' + storedToken.substring(0, 20) + '...)' : 'NOT FOUND')
      
      // Use user info from URL params (session cookies don't work cross-domain in Cloud Run)
      const userData = {
        user_id: userId,
        email: userEmail || '',
        name: userName || '',
        email_verified: true,
        is_active: true
      }
      
      if (userData.user_id) {
        console.log('[OAuth] Setting user in store:', { user_id: userData.user_id, email: userData.email })
        setUser(userData)
        
        console.log('[OAuth] User authentication complete - state updated')
        console.log('[OAuth] Cleaning up URL parameters...')
        // Clean up URL - remove query params but stay on current page
        window.history.replaceState({}, '', window.location.pathname)
        console.log('[OAuth] URL cleaned. Zustand will trigger re-render.')
        
        // NO PAGE RELOAD - let React/Zustand handle the state change
        // The page component will re-render when user state updates
        
        // Verify with backend in background (non-blocking) to get full user profile
        setTimeout(() => {
          const checkToken = useAuthStore.getState().token || localStorage.getItem('buildtrace-token')
          console.log('[OAuth] Background verification - token available:', checkToken ? 'YES' : 'NO')
          
          if (checkToken) {
            apiClient.getCurrentUser()
              .then((backendUser: any) => {
                console.log('[OAuth] Backend verification successful - updating with full profile')
                if (backendUser && backendUser.user_id) {
                  setUser(backendUser)
                }
              })
              .catch(err => {
                console.warn('[OAuth] Background verification failed (non-critical):', err.message)
                // User is already authenticated from OAuth, so we continue
              })
          }
        }, 100)
      } else {
        console.error('[OAuth] Invalid user data in URL params')
        window.history.replaceState({}, '', window.location.pathname)
      }
    } else if (error) {
      console.error('[OAuth] Authentication error:', error)
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [setUser, setToken]) // Include dependencies

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
