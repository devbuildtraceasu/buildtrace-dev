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

interface PageProgress {
  page_number: number
  drawing_name?: string
  ocr_status: string
  diff_status: string
  summary_status: string
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
  const [pageProgress, setPageProgress] = useState<PageProgress[]>([])
  const [totalPages, setTotalPages] = useState(0)
  
  // Check if OCR step is active or completed
  const ocrStep = steps.find(step => step.id === 'ocr')
  const isOcrActive = ocrStep?.status === 'active' || ocrStep?.status === 'completed'
  
  // Fetch progress data for per-page updates
  useEffect(() => {
    if (jobId) {
      const fetchProgress = async () => {
        try {
          const progress = await apiClient.getJobProgress(jobId)
          if (progress.pages) {
            setPageProgress(progress.pages as PageProgress[])
            setTotalPages(progress.total_pages || 0)
          }
        } catch (error) {
          console.debug('Progress not available yet:', error)
        }
      }
      
      fetchProgress()
      // Poll every 2 seconds for real-time updates
      const interval = setInterval(fetchProgress, 2000)
      return () => clearInterval(interval)
    }
  }, [jobId])
  
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
        {steps.map((step) => {
          // Get per-page progress for this step
          let completedPages = 0
          let inProgressPages = 0
          let totalPagesForStep = totalPages
          
          if (step.id === 'ocr' && pageProgress.length > 0) {
            completedPages = pageProgress.filter(p => p.ocr_status === 'completed').length
            inProgressPages = pageProgress.filter(p => p.ocr_status === 'in_progress').length
          } else if (step.id === 'diff' && pageProgress.length > 0) {
            completedPages = pageProgress.filter(p => p.diff_status === 'completed').length
            inProgressPages = pageProgress.filter(p => p.diff_status === 'in_progress').length
          } else if (step.id === 'summary' && pageProgress.length > 0) {
            completedPages = pageProgress.filter(p => p.summary_status === 'completed').length
            inProgressPages = pageProgress.filter(p => p.summary_status === 'in_progress').length
          }
          
          return (
            <div key={step.id} className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
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

                {/* Progress Count */}
                {totalPagesForStep > 0 && step.status !== 'completed' && (
                  <div className="text-sm text-gray-500 font-medium">
                    {completedPages}/{totalPagesForStep} pages
                  </div>
                )}
              </div>
              
              {/* Per-page progress bar */}
              {totalPagesForStep > 0 && step.status !== 'completed' && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(completedPages / totalPagesForStep) * 100}%`
                      }}
                    />
                  </div>
                  {inProgressPages > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      {inProgressPages} page{inProgressPages !== 1 ? 's' : ''} in progress...
                    </p>
                  )}
                  
                  {/* Page-by-page status (show first few pages) */}
                  {pageProgress.length > 0 && pageProgress.length <= 5 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {pageProgress.map((page) => {
                        let pageStatus = 'pending'
                        if (step.id === 'ocr') pageStatus = page.ocr_status
                        else if (step.id === 'diff') pageStatus = page.diff_status
                        else if (step.id === 'summary') pageStatus = page.summary_status
                        
                        return (
                          <div
                            key={page.page_number}
                            className={clsx(
                              'px-2 py-1 rounded text-xs font-medium',
                              {
                                'bg-green-100 text-green-700': pageStatus === 'completed',
                                'bg-blue-100 text-blue-700': pageStatus === 'in_progress',
                                'bg-gray-100 text-gray-500': pageStatus === 'pending',
                                'bg-red-100 text-red-700': pageStatus === 'failed'
                              }
                            )}
                            title={page.drawing_name || `Page ${page.page_number}`}
                          >
                            P{page.page_number}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Actions */}
      <div className="flex justify-center space-x-4">
        {/* Always show Cancel/Reset button */}
        <Button
          variant="secondary"
          onClick={onReset}
          className="flex items-center space-x-2"
        >
          <RotateCcw className="w-4 h-4" />
          <span>{hasFailedStep || allCompleted ? 'Start Over' : 'Cancel'}</span>
        </Button>

        {allCompleted && onViewResults && (
          <Button onClick={onViewResults}>
            View Results
          </Button>
        )}
      </div>

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
