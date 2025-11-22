'use client'

import React from 'react'
import { Check } from 'lucide-react'
import { clsx } from 'clsx'

interface ProgressStepsProps {
  currentStep: number
}

export default function ProgressSteps({ currentStep }: ProgressStepsProps) {
  const steps = [
    { number: 1, label: 'Upload Old' },
    { number: 2, label: 'Upload New' },
    { number: 3, label: 'Process' },
    { number: 4, label: 'Results' }
  ]

  return (
    <div className="flex items-center justify-center">
      <div className="flex items-center space-x-8">
        {steps.map((step, index) => (
          <div key={step.number} className="flex items-center">
            {/* Step Circle */}
            <div className="flex items-center">
              <div
                className={clsx(
                  'w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-colors',
                  {
                    'bg-blue-600 text-white': currentStep >= step.number,
                    'bg-gray-200 text-gray-500': currentStep < step.number
                  }
                )}
              >
                {currentStep > step.number ? (
                  <Check className="w-5 h-5" />
                ) : (
                  step.number
                )}
              </div>

              {/* Step Label */}
              <span
                className={clsx(
                  'ml-3 text-sm font-medium',
                  {
                    'text-blue-600': currentStep >= step.number,
                    'text-gray-500': currentStep < step.number
                  }
                )}
              >
                {step.label}
              </span>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div
                className={clsx(
                  'w-16 h-0.5 ml-6 transition-colors',
                  {
                    'bg-blue-600': currentStep > step.number,
                    'bg-gray-200': currentStep <= step.number
                  }
                )}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

