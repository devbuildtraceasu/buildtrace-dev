'use client'

import React from 'react'
import Button from '@/components/ui/Button'
import { LayoutGrid, Layers, FileText, FileCheck } from 'lucide-react'
import { ViewMode } from './types'

interface ViewModeToggleProps {
  currentMode: ViewMode
  onModeChange: (mode: ViewMode) => void
  className?: string
}

export default function ViewModeToggle({ 
  currentMode, 
  onModeChange,
  className 
}: ViewModeToggleProps) {
  const modes: Array<{ mode: ViewMode; label: string; icon: React.ElementType }> = [
    { mode: 'overlay', label: 'Overlay', icon: Layers },
    { mode: 'side-by-side', label: 'Side by Side', icon: LayoutGrid },
    { mode: 'baseline', label: 'Baseline Only', icon: FileText },
    { mode: 'revised', label: 'Revised Only', icon: FileCheck },
  ]

  return (
    <div className={`flex items-center space-x-2 ${className || ''}`}>
      <span className="text-sm font-medium text-gray-700 mr-2">View Mode:</span>
      <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
        {modes.map(({ mode, label, icon: Icon }) => (
          <button
            key={mode}
            onClick={() => onModeChange(mode)}
            className={`
              flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-all
              ${currentMode === mode
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }
            `}
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

