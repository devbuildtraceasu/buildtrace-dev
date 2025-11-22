'use client'

import React from 'react'
import clsx from 'clsx'

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export default function TextArea({ label, error, className, ...props }: TextAreaProps) {
  return (
    <div className="flex flex-col space-y-2">
      {label && <label className="text-sm font-medium text-gray-700">{label}</label>}
      <textarea
        className={clsx(
          'border border-gray-300 rounded-md px-3 py-2 text-sm font-mono',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          className
        )}
        {...props}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
