import React from 'react'
import { clsx } from 'clsx'
import { BaseComponentProps } from '@/types'

interface CardProps extends BaseComponentProps {
  variant?: 'default' | 'elevated' | 'outlined'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const Card: React.FC<CardProps> = ({
  children,
  className,
  variant = 'default',
  padding = 'md'
}) => {
  const variants = {
    default: 'bg-white border border-gray-200 shadow-sm',
    elevated: 'bg-white shadow-lg border-0',
    outlined: 'bg-white border-2 border-gray-200 shadow-none'
  }

  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  }

  return (
    <div
      className={clsx(
        'rounded-lg',
        variants[variant],
        paddings[padding],
        className
      )}
    >
      {children}
    </div>
  )
}

export default Card