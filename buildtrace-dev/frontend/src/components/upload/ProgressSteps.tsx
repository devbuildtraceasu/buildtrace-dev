'use client'

import React from 'react'
import { Check } from 'lucide-react'
import { clsx } from 'clsx'

interface ProgressStepsProps {
  currentStep: number
  className?: string
}

export default function ProgressSteps({ currentStep, className }: ProgressStepsProps) {
  const steps = ['Upload Old', 'Upload New', 'Process', 'Results']

  return (
    <div className={clsx("flex items-center justify-center", className)} data-testid="stepper">
      <div className="flex items-center space-x-4">
        {steps.map((step, index) => {
          const stepNumber = index + 1
          const isActive = stepNumber === currentStep
          const isCompleted = stepNumber < currentStep
          const isLast = index === steps.length - 1

          return (
            <div key={step} className="flex items-center">
              <div className="flex items-center">
                <div
                  className={clsx(
                    "w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-colors",
                    {
                      "bg-primary-500 text-white": isActive || isCompleted,
                      "bg-gray-300 text-gray-600": !isActive && !isCompleted,
                    }
                  )}
                  data-testid={`step-${stepNumber}`}
                >
                  {isCompleted ? (
                    <span>✓</span>
                  ) : (
                    stepNumber
                  )}
                </div>
                <span
                  className={clsx(
                    "ml-3 text-sm font-medium transition-colors",
                    {
                      "text-gray-900": isActive || isCompleted,
                      "text-gray-500": !isActive && !isCompleted,
                    }
                  )}
                  data-testid={`step-label-${stepNumber}`}
                >
                  {step}
                </span>
              </div>
              {!isLast && (
                <div
                  className={clsx(
                    "w-16 h-0.5 ml-4 transition-colors",
                    {
                      "bg-primary-500": isCompleted,
                      "bg-gray-300": !isCompleted,
                    }
                  )}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

