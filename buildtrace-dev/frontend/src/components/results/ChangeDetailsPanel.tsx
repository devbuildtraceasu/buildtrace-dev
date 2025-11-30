'use client'

import React from 'react'
import Card from '@/components/ui/Card'
import { FileText, Info, Image as ImageIcon } from 'lucide-react'
import { ChangeDetails } from './types'

interface ChangeDetailsPanelProps {
  change: ChangeDetails | null
  className?: string
}

export default function ChangeDetailsPanel({ change, className }: ChangeDetailsPanelProps) {
  if (!change) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">Change Details</h3>
        <div className="text-center py-12 text-gray-500">
          <Info className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>Select a change to view details</p>
        </div>
      </Card>
    )
  }

  const getChangeTypeColor = (type: ChangeDetails['change_type']) => {
    switch (type) {
      case 'added':
        return 'bg-green-50 text-green-800 border-green-200'
      case 'removed':
        return 'bg-red-50 text-red-800 border-red-200'
      case 'modified':
        return 'bg-yellow-50 text-yellow-800 border-yellow-200'
      default:
        return 'bg-gray-50 text-gray-800 border-gray-200'
    }
  }

  const getChangeTypeLabel = (type: ChangeDetails['change_type']) => {
    switch (type) {
      case 'added':
        return 'Addition'
      case 'removed':
        return 'Removal'
      case 'modified':
        return 'Modification'
      default:
        return 'Change'
    }
  }

  const descriptionItems = Array.isArray(change.description) 
    ? change.description 
    : change.description 
      ? [change.description] 
      : []

  return (
    <Card className={className}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Change Details</h3>
        <span className={`
          px-3 py-1 rounded-full text-xs font-medium border
          ${getChangeTypeColor(change.change_type)}
        `}>
          {getChangeTypeLabel(change.change_type)}
        </span>
      </div>

      {/* Drawing Info */}
      {(change.drawing_code || change.page_number) && (
        <div className="mb-4 pb-4 border-b border-gray-200">
          <div className="flex items-center space-x-2 text-sm">
            <FileText className="w-4 h-4 text-gray-400" />
            {change.drawing_code && (
              <span className="font-mono font-semibold text-gray-900">
                {change.drawing_code}
              </span>
            )}
            {change.page_number && (
              <span className="text-gray-500">
                • Page {change.page_number}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
        <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">
          {change.summary}
        </p>
      </div>

      {/* Description */}
      {descriptionItems.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Description</h4>
          <ul className="space-y-2">
            {descriptionItems.map((item, index) => (
              <li key={index} className="text-sm text-gray-700 flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Related Images */}
      {(change.baseline_image_url || change.revised_image_url || change.overlay_image_url) && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
            <ImageIcon className="w-4 h-4 mr-2" />
            Related Drawings
          </h4>
          <div className="grid grid-cols-3 gap-3">
            {change.baseline_image_url && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Baseline</p>
                <img
                  src={change.baseline_image_url}
                  alt="Baseline drawing"
                  className="w-full h-24 object-cover rounded border border-gray-200"
                />
              </div>
            )}
            {change.revised_image_url && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Revised</p>
                <img
                  src={change.revised_image_url}
                  alt="Revised drawing"
                  className="w-full h-24 object-cover rounded border border-gray-200"
                />
              </div>
            )}
            {change.overlay_image_url && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Overlay</p>
                <img
                  src={change.overlay_image_url}
                  alt="Overlay comparison"
                  className="w-full h-24 object-cover rounded border border-gray-200"
                />
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}

