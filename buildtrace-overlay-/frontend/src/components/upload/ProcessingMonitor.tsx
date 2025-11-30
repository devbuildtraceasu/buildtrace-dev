'use client'

import React from 'react'
import { clsx } from 'clsx'
import { Check, AlertCircle, RotateCcw } from 'lucide-react'
import { ProcessingStep } from '@/types'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import Button from '@/components/ui/Button'

interface ProcessingMonitorProps {
  steps: ProcessingStep[]
  onReset: () => void
}

const ProcessingMonitor: React.FC<ProcessingMonitorProps> = ({
  steps,
  onReset
}) => {
  const hasFailedStep = steps.some(step => step.status === 'failed')
  const allCompleted = steps.every(step => step.status === 'completed')

  return (
    <div className="text-center">
      {/* Main Status */}
      <div className="mb-8">
        <div className="mx-auto w-16 h-16 mb-4">
          {hasFailedStep ? (
            <AlertCircle className="w-16 h-16 text-red-500" />
          ) : allCompleted ? (
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
              <Check className="w-8 h-8 text-green-600" />
            </div>
          ) : (
            <LoadingSpinner size="lg" className="w-16 h-16" />
          )}
        </div>

        <h3 className="text-2xl font-bold text-gray-900 mb-2">
          {hasFailedStep
            ? 'Processing Failed'
            : allCompleted
            ? 'Processing Complete!'
            : 'Processing Your Drawings...'
          }
        </h3>

        <p className="text-gray-600">
          {hasFailedStep
            ? 'There was an error processing your drawings'
            : allCompleted
            ? 'Your drawings have been analyzed successfully'
            : 'Please wait while we analyze your drawings'
          }
        </p>
      </div>

      {/* Processing Steps */}
      <div className="space-y-4 mb-8">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              {/* Step Icon */}
              <div className="flex-shrink-0">
                {step.status === 'completed' ? (
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <Check className="w-4 h-4 text-green-600" />
                  </div>
                ) : step.status === 'failed' ? (
                  <AlertCircle className="w-6 h-6 text-red-500" />
                ) : step.status === 'active' ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-gray-200" />
                )}
              </div>

              {/* Step Details */}
              <div className="text-left">
                <p className={clsx(
                  'font-medium',
                  {
                    'text-green-600': step.status === 'completed',
                    'text-red-600': step.status === 'failed',
                    'text-buildtrace-primary': step.status === 'active',
                    'text-gray-500': step.status === 'pending'
                  }
                )}>
                  {step.name}
                </p>
                {step.message && (
                  <p className="text-sm text-gray-500">{step.message}</p>
                )}
              </div>
            </div>

            {/* Progress */}
            {typeof step.progress === 'number' && step.status !== 'completed' && (
              <div className="text-sm text-gray-500 font-medium">
                {step.progress}%
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      {(hasFailedStep || allCompleted) && (
        <div className="flex justify-center space-x-4">
          <Button
            variant="secondary"
            onClick={onReset}
            className="flex items-center space-x-2"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Start Over</span>
          </Button>

          {allCompleted && (
            <Button variant="primary">
              View Results
            </Button>
          )}
        </div>
      )}

      {/* Progress Bar for Overall Progress */}
      {!hasFailedStep && !allCompleted && (
        <div className="mt-6">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-buildtrace-primary h-2 rounded-full transition-all duration-300"
              style={{
                width: `${(steps.filter(s => s.status === 'completed').length / steps.length) * 100}%`
              }}
            />
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Step {steps.filter(s => s.status === 'completed').length + 1} of {steps.length}
          </p>
        </div>
      )}
    </div>
  )
}

export default ProcessingMonitor