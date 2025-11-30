import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import Button from '@/components/ui/Button'
import { LogOut, User } from 'lucide-react'

interface HeaderProps {
  showAuth?: boolean
}

const Header: React.FC<HeaderProps> = ({ showAuth = true }) => {
  const router = useRouter()
  const { isAuthenticated, user, logout } = useAuthStore()

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="container-custom">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Brand */}
          <Link href="/" className="flex items-center space-x-3">
            <div className="text-2xl font-bold text-buildtrace-primary">
              BuildTrace AI
            </div>
          </Link>

          {/* Tagline */}
          <div className="hidden md:block">
            <p className="text-sm text-gray-600">
              Intelligent Drawing Comparison & Analysis
            </p>
          </div>

          {/* Navigation and Auth */}
          <div className="flex items-center space-x-4">
            {showAuth && isAuthenticated && (
              <>
                {/* User Info */}
                <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-600">
                  <User className="w-4 h-4" />
                  <span>{user?.email}</span>
                </div>

                {/* Logout Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="flex items-center space-x-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Logout</span>
                </Button>
              </>
            )}

            {showAuth && !isAuthenticated && (
              <div className="flex items-center space-x-2">
                <Link href="/login">
                  <Button variant="ghost" size="sm">
                    Login
                  </Button>
                </Link>
                <Link href="/signup">
                  <Button variant="primary" size="sm">
                    Sign Up
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header