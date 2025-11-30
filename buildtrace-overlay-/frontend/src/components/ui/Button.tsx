import React from 'react'
import { clsx } from 'clsx'
import { ButtonProps } from '@/types'
import LoadingSpinner from './LoadingSpinner'

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    children,
    className,
    variant = 'primary',
    size = 'md',
    disabled = false,
    loading = false,
    onClick,
    type = 'button',
    ...props
  }, ref) => {
    const baseClasses = 'font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2'

    const variants = {
      primary: 'bg-buildtrace-primary hover:bg-blue-700 text-white focus:ring-buildtrace-primary',
      secondary: 'bg-gray-100 hover:bg-gray-200 text-gray-800 focus:ring-gray-500',
      danger: 'bg-red-500 hover:bg-red-600 text-white focus:ring-red-500',
      ghost: 'bg-transparent hover:bg-gray-100 text-gray-700 focus:ring-gray-500'
    }

    const sizes = {
      sm: 'px-3 py-2 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg'
    }

    const isDisabled = disabled || loading

    return (
      <button
        ref={ref}
        type={type}
        className={clsx(
          baseClasses,
          variants[variant],
          sizes[size],
          className
        )}
        disabled={isDisabled}
        onClick={onClick}
        {...props}
      >
        {loading && <LoadingSpinner size="sm" />}
        <span className={loading ? 'opacity-70' : ''}>{children}</span>
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button