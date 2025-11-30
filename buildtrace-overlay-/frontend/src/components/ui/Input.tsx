import React from 'react'
import { clsx } from 'clsx'
import { InputProps } from '@/types'

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({
    className,
    type = 'text',
    placeholder,
    value,
    onChange,
    error,
    disabled = false,
    required = false,
    ...props
  }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (onChange) {
        onChange(e.target.value)
      }
    }

    return (
      <div className="w-full">
        <input
          ref={ref}
          type={type}
          className={clsx(
            'w-full px-3 py-2 border rounded-lg transition-colors duration-200',
            'focus:outline-none focus:ring-2 focus:ring-buildtrace-primary focus:border-transparent',
            'placeholder-gray-400',
            {
              'border-gray-300': !error,
              'border-red-300 focus:ring-red-500': error,
              'bg-gray-50 cursor-not-allowed': disabled,
              'bg-white': !disabled
            },
            className
          )}
          placeholder={placeholder}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          required={required}
          {...props}
        />
        {error && (
          <p className="mt-1 text-sm text-red-600">{error}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input