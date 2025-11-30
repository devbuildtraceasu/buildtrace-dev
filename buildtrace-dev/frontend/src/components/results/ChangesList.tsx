'use client'

import React from 'react'
import Card from '@/components/ui/Card'
import { FileText, ChevronRight } from 'lucide-react'
import { clsx } from 'clsx'
import { ChangeItem } from './types'

interface ChangesListProps {
  changes: ChangeItem[]
  selectedChangeId?: string | null
  onSelectChange: (changeId: string) => void
  className?: string
}

export default function ChangesList({ 
  changes, 
  selectedChangeId, 
  onSelectChange,
  className 
}: ChangesListProps) {
  if (changes.length === 0) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">Changes List</h3>
        <div className="text-center py-8 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>No changes detected</p>
        </div>
      </Card>
    )
  }

  const getChangeTypeColor = (type: ChangeItem['change_type']) => {
    switch (type) {
      case 'added':
        return 'bg-green-100 text-green-700 border-green-200'
      case 'removed':
        return 'bg-red-100 text-red-700 border-red-200'
      case 'modified':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getChangeTypeLabel = (type: ChangeItem['change_type']) => {
    switch (type) {
      case 'added':
        return 'Added'
      case 'removed':
        return 'Removed'
      case 'modified':
        return 'Modified'
      default:
        return 'Change'
    }
  }

  return (
    <Card className={className}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Changes List</h3>
        <span className="text-sm text-gray-500">{changes.length} change{changes.length !== 1 ? 's' : ''}</span>
      </div>
      
      <div className="space-y-2 max-h-[600px] overflow-y-auto">
        {changes.map((change) => {
          const isSelected = selectedChangeId === change.id
          
          return (
            <button
              key={change.id}
              onClick={() => onSelectChange(change.id)}
              className={clsx(
                'w-full text-left p-4 rounded-lg border-2 transition-all',
                'hover:shadow-md',
                isSelected
                  ? 'border-blue-500 bg-blue-50 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-2">
                    {change.drawing_code && (
                      <span className="font-mono text-sm font-semibold text-gray-900">
                        {change.drawing_code}
                      </span>
                    )}
                    {change.page_number && (
                      <span className="text-xs text-gray-500">
                        Page {change.page_number}
                      </span>
                    )}
                    <span className={clsx(
                      'px-2 py-0.5 rounded-full text-xs font-medium border',
                      getChangeTypeColor(change.change_type)
                    )}>
                      {getChangeTypeLabel(change.change_type)}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-700 line-clamp-2">
                    {change.summary}
                  </p>
                  
                  {(() => {
                    const detailCount = change.detail_count ?? change.details?.length ?? 0
                    if (detailCount > 0) {
                      return (
                        <p className="text-xs text-gray-500 mt-2">
                          {detailCount} detail{detailCount !== 1 ? 's' : ''}
                        </p>
                      )
                    }
                    return null
                  })()}
                </div>
                
                <ChevronRight 
                  className={clsx(
                    'w-5 h-5 flex-shrink-0 ml-2 transition-colors',
                    isSelected ? 'text-blue-600' : 'text-gray-400'
                  )} 
                />
              </div>
            </button>
          )
        })}
      </div>
    </Card>
  )
}
