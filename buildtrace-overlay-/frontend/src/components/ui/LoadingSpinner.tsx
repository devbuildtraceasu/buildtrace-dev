import React from 'react'
import { clsx } from 'clsx'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  color?: 'primary' | 'white' | 'gray'
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className,
  color = 'primary'
}) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }

  const colors = {
    primary: 'border-buildtrace-primary',
    white: 'border-white',
    gray: 'border-gray-600'
  }

  return (
    <div
      className={clsx(
        'animate-spin rounded-full border-2 border-transparent border-t-current',
        sizes[size],
        colors[color],
        className
      )}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export default LoadingSpinner