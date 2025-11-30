'use client'

import React, { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { Check, AlertCircle, RotateCcw, FileText } from 'lucide-react'
import { ProcessingStep } from '@/types'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import Button from '@/components/ui/Button'
import { apiClient } from '@/lib/api'

interface ProcessingMonitorProps {
  steps: ProcessingStep[]
  jobId?: string
  onReset: () => void
  onViewResults?: () => void
}

interface OcrLogData {
  drawing_name: string
  log: {
    summary?: {
      total_pages?: number
      drawings_found?: string[]
      project_info?: any
      architect_info?: any
      revision_summary?: any
    }
    pages?: Array<{
      page_number: number
      drawing_name: string
      extracted_info?: {
        sections?: any
      }
      processed_at: string
    }>
  }
}

export default function ProcessingMonitor({
  steps,
  jobId,
  onReset,
  onViewResults
}: ProcessingMonitorProps) {
  const hasFailedStep = steps.some(step => step.status === 'failed')
  const allCompleted = steps.every(step => step.status === 'completed')
  const [ocrLogs, setOcrLogs] = useState<OcrLogData[]>([])
  const [showOcrInfo, setShowOcrInfo] = useState(false)
  
  // Check if OCR step is active or completed
  const ocrStep = steps.find(step => step.id === 'ocr')
  const isOcrActive = ocrStep?.status === 'active' || ocrStep?.status === 'completed'
  
  // Fetch OCR logs when OCR step is active or completed
  useEffect(() => {
    if (jobId && isOcrActive) {
      const fetchOcrLog = async () => {
        try {
          const response = await apiClient.getOcrLog(jobId)
          if (response.data?.ocr_logs) {
            setOcrLogs(response.data.ocr_logs)
            setShowOcrInfo(true)
          }
        } catch (error) {
          // Silently fail - OCR log might not be available yet
          console.debug('OCR log not available yet:', error)
        }
      }
      
      fetchOcrLog()
      // Poll every 3 seconds while OCR is active
      if (ocrStep?.status === 'active') {
        const interval = setInterval(fetchOcrLog, 3000)
        return () => clearInterval(interval)
      }
    }
  }, [jobId, isOcrActive, ocrStep?.status])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Processing Area */}
      <div className="lg:col-span-2 text-center">
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
                    'text-blue-600': step.status === 'active',
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

          {allCompleted && onViewResults && (
            <Button onClick={onViewResults}>
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
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
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

      {/* OCR Information Sidebar */}
      {showOcrInfo && ocrLogs.length > 0 && (
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-md p-6 sticky top-4">
            <div className="flex items-center space-x-2 mb-4">
              <FileText className="w-5 h-5 text-blue-600" />
              <h4 className="text-lg font-semibold text-gray-900">Drawing Information</h4>
            </div>
            
            {ocrLogs.map((ocrLog, idx) => {
              const summary = ocrLog.log.summary
              const pages = ocrLog.log.pages || []
              
              return (
                <div key={idx} className="mb-6 last:mb-0">
                  <h5 className="font-medium text-gray-800 mb-3">{ocrLog.drawing_name}</h5>
                  
                  {summary && (
                    <div className="space-y-3 text-sm">
                      {summary.project_info?.projects && summary.project_info.projects.length > 0 && (
                        <div>
                          <p className="text-gray-600 font-medium mb-1">Project:</p>
                          <p className="text-gray-800">{summary.project_info.projects[0]}</p>
                        </div>
                      )}
                      
                      {summary.architect_info?.architects && summary.architect_info.architects.length > 0 && (
                        <div>
                          <p className="text-gray-600 font-medium mb-1">Architect:</p>
                          <p className="text-gray-800 text-xs">{summary.architect_info.architects[0].substring(0, 100)}...</p>
                        </div>
                      )}
                      
                      {summary.drawings_found && summary.drawings_found.length > 0 && (
                        <div>
                          <p className="text-gray-600 font-medium mb-1">Drawings:</p>
                          <p className="text-gray-800">{summary.drawings_found.join(', ')}</p>
                        </div>
                      )}
                      
                      {summary.revision_summary && summary.revision_summary.total_revisions > 0 && (
                        <div>
                          <p className="text-gray-600 font-medium mb-1">Revisions:</p>
                          <p className="text-gray-800">{summary.revision_summary.total_revisions} revision(s) found</p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {pages.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs text-gray-500 mb-2">
                        Processing {pages.length} page{pages.length !== 1 ? 's' : ''}...
                      </p>
                      <div className="space-y-1">
                        {pages.map((page, pageIdx) => (
                          <div key={pageIdx} className="flex items-center space-x-2 text-xs">
                            <Check className="w-3 h-3 text-green-500" />
                            <span className="text-gray-600">
                              Page {page.page_number}: {page.drawing_name}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
            
            {ocrStep?.status === 'active' && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 italic">
                  Extracting information from drawings...
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
