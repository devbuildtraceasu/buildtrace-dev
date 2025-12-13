'use client'

import React from 'react'
import Card from '@/components/ui/Card'
import { ScheduleImpactData } from '@/mocks/data'
import { Clock, Target, AlertCircle } from 'lucide-react'

interface ScheduleImpactReportProps {
  data: ScheduleImpactData
  onClose?: () => void
}

export default function ScheduleImpactReport({ data, onClose }: ScheduleImpactReportProps) {
  const getProbabilityColor = (color: 'green' | 'yellow' | 'red') => {
    switch (color) {
      case 'green':
        return 'bg-green-500'
      case 'yellow':
        return 'bg-yellow-500'
      case 'red':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getScenarioNameColor = (color: 'green' | 'yellow' | 'red') => {
    switch (color) {
      case 'green':
        return 'text-green-600'
      case 'yellow':
        return 'text-yellow-600'
      case 'red':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <Card className="bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <Clock className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Ask About Changes</h2>
            <p className="text-sm text-gray-500">Schedule impact analysis based on detected changes</p>
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

      {/* Critical Path & Overlap Opportunities */}
      <div className="mb-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center">
          <span className="mr-2">🎯</span>
          Critical Path & Overlap Opportunities
        </h3>
        <div className="bg-gray-50 rounded-lg p-4 border-l-4 border-blue-500">
          <ul className="space-y-3">
            {data.criticalPathItems.map((item, index) => (
              <li key={index} className="text-sm text-gray-700">
                <span className="font-semibold text-gray-900">{item.item}</span>
                {' '}
                <span className="text-gray-500">({item.duration})</span>
                {' '}
                {item.note}
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-4 text-sm text-gray-600 italic">
          {data.overlapSummary}
        </p>
      </div>

      {/* Likely Impact Scenarios */}
      <div className="mb-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center border-l-4 border-blue-500 pl-3">
          Likely Impact Scenarios
        </h3>
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-700">Scenario</th>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-700">Description</th>
                <th className="text-center px-4 py-3 text-sm font-semibold text-gray-700">Schedule Impact</th>
                <th className="text-center px-4 py-3 text-sm font-semibold text-gray-700">Probability</th>
              </tr>
            </thead>
            <tbody>
              {data.scenarios.map((scenario, index) => (
                <tr 
                  key={index} 
                  className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                >
                  <td className={`px-4 py-3 text-sm font-semibold ${getScenarioNameColor(scenario.color)}`}>
                    {scenario.name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{scenario.description}</td>
                  <td className={`px-4 py-3 text-sm font-semibold text-center ${getScenarioNameColor(scenario.color)}`}>
                    {scenario.impact}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-semibold text-white ${getProbabilityColor(scenario.color)}`}>
                      {scenario.probability}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Line */}
      <div className="bg-red-50 border-l-4 border-red-400 rounded-r-lg p-4">
        <div className="flex items-start">
          <Target className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-red-800 mb-1">🎯 Bottom Line</h4>
            <p className="text-sm text-red-700">{data.bottomLine}</p>
          </div>
        </div>
      </div>
    </Card>
  )
}

