'use client'

import React, { useState, useMemo } from 'react'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { FileText, ChevronRight, ChevronDown, RefreshCw, Plus, Minus, Edit3 } from 'lucide-react'
import { clsx } from 'clsx'
import { ChangeItem } from './types'

interface ChangesListProps {
  changes: ChangeItem[]
  selectedChangeId?: string | null
  onSelectChange: (changeId: string) => void
  onRegenerate?: () => void
  isRegenerating?: boolean
  className?: string
}

// Group changes by type for drawing-level summary
interface ChangeGroup {
  type: 'added' | 'modified' | 'removed'
  label: string
  icon: React.ReactNode
  color: string
  bgColor: string
  borderColor: string
  changes: ChangeItem[]
}

export default function ChangesList({ 
  changes, 
  selectedChangeId, 
  onSelectChange,
  onRegenerate,
  isRegenerating,
  className 
}: ChangesListProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['added', 'modified', 'removed']))

  // Helper: build type groups within a single drawing
  const buildTypeGroups = (items: ChangeItem[]): ChangeGroup[] => {
    const added = items.filter(c => c.change_type === 'added')
    const modified = items.filter(c => c.change_type === 'modified')
    const removed = items.filter(c => c.change_type === 'removed')

    const groups: ChangeGroup[] = [
      {
        type: 'added' as const,
        label: 'Added',
        icon: <Plus className="w-4 h-4" />,
        color: 'text-green-700',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        changes: added
      },
      {
        type: 'modified' as const,
        label: 'Modified',
        icon: <Edit3 className="w-4 h-4" />,
        color: 'text-amber-700',
        bgColor: 'bg-amber-50',
        borderColor: 'border-amber-200',
        changes: modified
      },
      {
        type: 'removed' as const,
        label: 'Removed',
        icon: <Minus className="w-4 h-4" />,
        color: 'text-red-700',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        changes: removed
      }
    ]
    return groups.filter(g => g.changes.length > 0)
  }

  // Group changes by drawing first (A-101, A-111, etc.)
  const drawingGroups = useMemo(() => {
    const byDrawing: Record<string, ChangeItem[]> = {}

    for (const change of changes) {
      const key = change.drawing_code || 'Unknown Drawing'
      if (!byDrawing[key]) {
        byDrawing[key] = []
      }
      byDrawing[key].push(change)
    }

    return Object.entries(byDrawing).map(([drawingCode, items]) => ({
      drawingCode,
      items,
    }))
  }, [changes])

  const toggleGroup = (type: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }

  if (changes.length === 0) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Changes List</h3>
          {onRegenerate && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRegenerate}
              disabled={isRegenerating}
              className="flex items-center space-x-1"
            >
              <RefreshCw className={clsx("w-4 h-4", isRegenerating && "animate-spin")} />
              <span>{isRegenerating ? 'Regenerating...' : 'Regenerate'}</span>
            </Button>
          )}
        </div>
        <div className="text-center py-8 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>No changes detected</p>
        </div>
      </Card>
    )
  }

  return (
    <Card className={className}>
      {/* Header with regenerate button */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-semibold">Changes Summary</h3>
        </div>
        {onRegenerate && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="flex items-center space-x-1"
          >
            <RefreshCw className={clsx("w-4 h-4", isRegenerating && "animate-spin")} />
            <span>{isRegenerating ? 'Regenerating...' : 'Regenerate'}</span>
          </Button>
        )}
      </div>

      {/* Global Summary Stats (across all drawings in this view) */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { type: 'added', label: 'Added', count: changes.filter(c => c.change_type === 'added').length, color: 'text-green-600', bg: 'bg-green-100' },
          { type: 'modified', label: 'Modified', count: changes.filter(c => c.change_type === 'modified').length, color: 'text-amber-600', bg: 'bg-amber-100' },
          { type: 'removed', label: 'Removed', count: changes.filter(c => c.change_type === 'removed').length, color: 'text-red-600', bg: 'bg-red-100' },
        ].map(stat => (
          <div key={stat.type} className={`${stat.bg} rounded-lg p-3 text-center`}>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.count}</p>
            <p className="text-xs text-gray-600">{stat.label}</p>
          </div>
        ))}
      </div>
      
      {/* Grouped Changes - First by Drawing, then by Type */}
      <div className="space-y-4 max-h-[500px] overflow-y-auto">
        {drawingGroups.map(({ drawingCode, items }) => {
          const groupsForDrawing = buildTypeGroups(items)
          return (
            <div key={drawingCode} className="space-y-2">
              <div className="px-1 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                {drawingCode}
              </div>
              {groupsForDrawing.map((group) => {
                const isExpanded = expandedGroups.has(group.type)
                return (
                  <div key={`${drawingCode}-${group.type}`} className={`rounded-lg border ${group.borderColor} overflow-hidden`}>
                    {/* Group Header - per drawing and type */}
                    <button
                      onClick={() => toggleGroup(group.type)}
                      className={`w-full flex items-center justify-between p-3 ${group.bgColor} hover:opacity-90 transition-opacity`}
                    >
                      <div className="flex items-center space-x-2">
                        <span className={group.color}>{group.icon}</span>
                        <span className={`font-semibold ${group.color}`}>{group.label}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${group.bgColor} ${group.color} border ${group.borderColor}`}>
                          {group.changes.length} item{group.changes.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      {isExpanded ? (
                        <ChevronDown className={`w-5 h-5 ${group.color}`} />
                      ) : (
                        <ChevronRight className={`w-5 h-5 ${group.color}`} />
                      )}
                    </button>
                    
                    {/* Change-Level Details - Expandable */}
                    {isExpanded && (
                      <div className="bg-white divide-y divide-gray-100">
                        {group.changes.map((change) => {
                          const isSelected = selectedChangeId === change.id
                          
                          return (
                            <button
                              key={change.id}
                              onClick={() => onSelectChange(change.id)}
                              className={clsx(
                                'w-full text-left p-3 transition-all',
                                'hover:bg-gray-50',
                                isSelected && 'bg-blue-50 border-l-4 border-l-blue-500'
                              )}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm text-gray-800 line-clamp-2">
                                    {change.summary}
                                  </p>
                                  {(() => {
                                    const detailCount = change.detail_count ?? change.details?.length ?? 0
                                    if (detailCount > 0) {
                                      return (
                                        <p className="text-xs text-gray-400 mt-1">
                                          {detailCount} detail{detailCount !== 1 ? 's' : ''} →
                                        </p>
                                      )
                                    }
                                    return null
                                  })()}
                                </div>
                                <ChevronRight 
                                  className={clsx(
                                    'w-4 h-4 flex-shrink-0 ml-2',
                                    isSelected ? 'text-blue-600' : 'text-gray-300'
                                  )} 
                                />
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
