'use client'

import React from 'react'
import Card from '@/components/ui/Card'
import { CostImpactData } from '@/mocks/data'
import { AlertTriangle, Target, DollarSign } from 'lucide-react'

interface CostImpactReportProps {
  data: CostImpactData
  onClose?: () => void
}

export default function CostImpactReport({ data, onClose }: CostImpactReportProps) {
  return (
    <Card className="bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Cost Impact Analysis</h2>
            <p className="text-sm text-gray-500">Estimated costs based on detected changes</p>
          </div>
        </div>
        {onClose && (
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
          >
            ×
          </button>
        )}
      </div>

      {/* Cost Categories */}
      <div className="space-y-6">
        {data.categories.map((category, catIndex) => (
          <div key={catIndex}>
            <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center">
              <span className="mr-2">{category.icon}</span>
              {category.name}
            </h3>
            <div className="overflow-hidden rounded-lg border border-gray-200">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="text-left px-4 py-3 text-sm font-semibold text-gray-700">Item</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold text-gray-700">Description</th>
                    <th className="text-right px-4 py-3 text-sm font-semibold text-gray-700">Cost Range</th>
                  </tr>
                </thead>
                <tbody>
                  {category.items.map((item, itemIndex) => (
                    <tr 
                      key={itemIndex} 
                      className={itemIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                    >
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.item}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{item.description}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-green-600 text-right">{item.costRange}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {/* Project Totals */}
      <div className="mt-8">
        <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center">
          <span className="mr-2">💰</span>
          Project Totals
        </h3>
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full">
            <tbody>
              <tr className="bg-white border-b border-gray-200">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">Subtotal</td>
                <td className="px-4 py-3 text-sm font-semibold text-gray-900 text-right">{data.subtotal}</td>
              </tr>
              <tr className="bg-gray-50 border-b border-gray-200">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">Contingency ({data.contingencyPercent}%)</td>
                <td className="px-4 py-3 text-sm font-semibold text-gray-900 text-right">{data.contingency}</td>
              </tr>
              <tr className="bg-white border-b-2 border-blue-200">
                <td className="px-4 py-3 text-sm font-bold text-blue-700">Total Estimate</td>
                <td className="px-4 py-3 text-sm font-bold text-blue-700 text-right">{data.totalEstimate}</td>
              </tr>
              <tr className="bg-red-50">
                <td className="px-4 py-3 text-sm font-bold text-red-600">Ballpark Total</td>
                <td className="px-4 py-3 text-sm font-bold text-red-600 text-right">{data.ballparkTotal}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Important Notes */}
      <div className="mt-6 bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg p-4">
        <div className="flex items-start">
          <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-yellow-800 mb-1">Important Notes</h4>
            <p className="text-sm text-yellow-700">{data.importantNotes}</p>
          </div>
        </div>
      </div>

      {/* Next Steps */}
      <div className="mt-4 bg-orange-50 border-l-4 border-orange-400 rounded-r-lg p-4">
        <div className="flex items-start">
          <Target className="w-5 h-5 text-orange-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-orange-800 mb-1">🎯 Next Steps</h4>
            <p className="text-sm text-orange-700">{data.nextSteps}</p>
          </div>
        </div>
      </div>
    </Card>
  )
}

