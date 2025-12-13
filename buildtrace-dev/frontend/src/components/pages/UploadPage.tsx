'use client'

import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Header from '@/components/layout/Header'
import FileUploader from '@/components/upload/FileUploader'
import ProcessingMonitor from '@/components/upload/ProcessingMonitor'
import RecentSessions from '@/components/upload/RecentSessions'
import ProgressSteps from '@/components/upload/ProgressSteps'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { apiClient } from '@/lib/api'
import { ProcessingStep, Project } from '@/types'
import { useAuthStore } from '@/store/authStore'

export default function UploadPage() {
  const router = useRouter()
  const { user, isAuthenticated } = useAuthStore()
  const [oldFile, setOldFile] = useState<File | null>(null)
  const [newFile, setNewFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([])
  const [uploadProgress, setUploadProgress] = useState(0)
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [storedJobId, setStoredJobId] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!user) return
    let mounted = true

    const fetchProjects = async () => {
      try {
        const result: any = await apiClient.listProjects(user.user_id)
        if (!mounted) return
        const list = result?.projects || []
        setProjects(list)
        if (list.length > 0) {
          setSelectedProjectId(list[0].project_id)
        } else {
          setSelectedProjectId('default-project')
        }
      } catch (error) {
        console.error('Failed to load projects', error)
        setProjects([])
        setSelectedProjectId('default-project')
      }
    }

    fetchProjects()

    return () => {
      mounted = false
    }
  }, [user])

  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  // Prevent hydration mismatch by waiting for client-side mount
  useEffect(() => {
    setMounted(true)
  }, [])

  // ALL HOOKS MUST BE CALLED BEFORE ANY CONDITIONAL RETURNS
  const handleFileSelect = useCallback((type: 'old' | 'new', file: File | null) => {
    if (type === 'old') {
      setOldFile(file)
      if (file && !newFile) {
        setCurrentStep(2)
      }
    } else {
      setNewFile(file)
      if (file && oldFile) {
        setCurrentStep(3)
      }
    }
  }, [oldFile, newFile])

  const handleRemoveFile = useCallback((type: 'old' | 'new') => {
    if (type === 'old') {
      setOldFile(null)
      if (newFile) {
        setCurrentStep(2)
      } else {
        setCurrentStep(1)
      }
    } else {
      setNewFile(null)
      setCurrentStep(oldFile ? 2 : 1)
    }
  }, [oldFile, newFile])

  const handleStartProcessing = async () => {
    if (!oldFile || !newFile || !selectedProjectId) {
      return
    }

    setIsProcessing(true)
    setCurrentStep(3)
    setUploadProgress(0)
    setActiveJobId(null)

    try {
      const steps: ProcessingStep[] = [
        { id: 'upload', name: 'Uploading files', status: 'active', progress: 0 },
        { id: 'ocr', name: 'OCR Processing', status: 'pending' },
        { id: 'diff', name: 'Comparing drawings', status: 'pending' },
        { id: 'summary', name: 'Generating summary', status: 'pending' }
      ]
      setProcessingSteps(steps)

      const oldResponse: any = await apiClient.uploadDrawing(
        oldFile,
        selectedProjectId,
        undefined,
        userId,
        (progress) => {
          setUploadProgress(progress / 2)
          setProcessingSteps(prev => prev.map(step =>
            step.id === 'upload'
              ? { ...step, progress: progress / 2 }
              : step
          ))
        }
      )

      if (oldResponse.error || !oldResponse.drawing_version_id) {
        throw new Error(oldResponse.error || 'Failed to upload old file')
      }

      const oldVersionId = oldResponse.drawing_version_id

      const newResponse: any = await apiClient.uploadDrawing(
        newFile,
        selectedProjectId,
        oldVersionId,
        userId,
        (progress) => {
          setUploadProgress(50 + progress / 2)
          setProcessingSteps(prev => prev.map(step =>
            step.id === 'upload'
              ? { ...step, progress: 50 + progress / 2 }
              : step
          ))
        }
      )

      if (newResponse.error || !newResponse.drawing_version_id) {
        throw new Error(newResponse.error || 'Failed to upload new file')
      }

      const jobId = newResponse.job_id
      if (jobId) {
        setActiveJobId(jobId)
        // Navigate to results page immediately after upload completes
        // Results page will show live progress as OCR/diff/summary complete
        router.push(`/results?jobId=${jobId}`)
      } else {
        // No job ID - just mark as complete
        setProcessingSteps(prev => prev.map(step => ({
          ...step,
          status: 'completed',
          progress: step.id === 'upload' ? 100 : undefined
        })))
        setIsProcessing(false)
        setCurrentStep(4)
      }
    } catch (error: any) {
      console.error('Processing failed:', error)
      setProcessingSteps(prev => prev.map(step =>
        step.status === 'active'
          ? { ...step, status: 'failed', message: error.message }
          : step
      ))
      setIsProcessing(false)
    }
  }

  const pollJobStatus = useCallback((jobId: string) => {
    setStoredJobId(jobId)
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('buildtrace-active-job', jobId)
    }

    stopPolling()

    const poll = async () => {
      try {
        // Use progress endpoint for real-time per-page updates
        const progress = await apiClient.getJobProgress(jobId)
        const job = await apiClient.getJob(jobId)

        // Update steps based on progress data
        setProcessingSteps(prev => prev.map(step => {
          if (step.id === 'ocr') {
            const ocrProgress = progress.progress?.ocr || { completed: 0, total: progress.total_pages || 0 }
            const ocrPages = progress.pages?.filter((p: any) => p.ocr_status === 'completed').length || 0
            const ocrInProgress = progress.pages?.some((p: any) => p.ocr_status === 'in_progress') || false
            
            let status: ProcessingStep['status'] = 'pending'
            let message: string | undefined
            
            if (ocrProgress.total > 0) {
              if (ocrPages === ocrProgress.total) {
                status = 'completed'
                message = `All ${ocrProgress.total} page${ocrProgress.total !== 1 ? 's' : ''} processed`
              } else if (ocrInProgress || ocrPages > 0) {
                status = 'active'
                message = `Processing ${ocrPages}/${ocrProgress.total} page${ocrProgress.total !== 1 ? 's' : ''}`
              }
            }
            
            return { ...step, status, message }
          }
          
          if (step.id === 'diff') {
            const diffProgress = progress.progress?.diff || { completed: 0, total: progress.total_pages || 0 }
            const diffPages = progress.pages?.filter((p: any) => p.diff_status === 'completed').length || 0
            const diffInProgress = progress.pages?.some((p: any) => p.diff_status === 'in_progress') || false
            
            let status: ProcessingStep['status'] = 'pending'
            let message: string | undefined
            
            if (diffProgress.total > 0) {
              if (diffPages === diffProgress.total) {
                status = 'completed'
                message = `All ${diffProgress.total} page${diffProgress.total !== 1 ? 's' : ''} compared`
              } else if (diffInProgress || diffPages > 0) {
                status = 'active'
                message = `Comparing ${diffPages}/${diffProgress.total} page${diffProgress.total !== 1 ? 's' : ''}`
              }
            }
            
            return { ...step, status, message }
          }
          
          if (step.id === 'summary') {
            const summaryProgress = progress.progress?.summary || { completed: 0, total: progress.total_pages || 0 }
            const summaryPages = progress.pages?.filter((p: any) => p.summary_status === 'completed').length || 0
            const summaryInProgress = progress.pages?.some((p: any) => p.summary_status === 'in_progress') || false
            
            let status: ProcessingStep['status'] = 'pending'
            let message: string | undefined
            
            if (summaryProgress.total > 0) {
              if (summaryPages === summaryProgress.total) {
                status = 'completed'
                message = `All ${summaryProgress.total} page${summaryProgress.total !== 1 ? 's' : ''} summarized`
              } else if (summaryInProgress || summaryPages > 0) {
                status = 'active'
                message = `Summarizing ${summaryPages}/${summaryProgress.total} page${summaryProgress.total !== 1 ? 's' : ''}`
              }
            }
            
            return { ...step, status, message }
          }
          
          return step
        }))

        if (job.status === 'completed') {
          stopPolling()
          if (typeof window !== 'undefined') {
            sessionStorage.removeItem('buildtrace-active-job')
          }
          setStoredJobId(null)
          setIsProcessing(false)
          setCurrentStep(4)
          router.push(`/results?jobId=${jobId}`)
        } else if (job.status === 'failed') {
          stopPolling()
          if (typeof window !== 'undefined') {
            sessionStorage.removeItem('buildtrace-active-job')
          }
          setStoredJobId(null)
          setProcessingSteps(prev => prev.map(step =>
            step.status === 'active'
              ? { ...step, status: 'failed', message: job.error_message }
              : step
          ))
          setIsProcessing(false)
        } else {
          // Poll more frequently for real-time updates (every 2 seconds)
          pollTimerRef.current = setTimeout(poll, 2000)
        }
      } catch (err: any) {
        console.error('Error polling job status:', err)
        pollTimerRef.current = setTimeout(poll, 5000)
      }
    }

    poll()
  }, [router, stopPolling])

  const resumeExistingJob = useCallback((jobId: string) => {
    setActiveJobId(jobId)
    setIsProcessing(true)
    setCurrentStep(3)
    setProcessingSteps([
      { id: 'upload', name: 'Uploading files', status: 'completed', progress: 100 },
      { id: 'ocr', name: 'OCR Processing', status: 'active' },
      { id: 'diff', name: 'Comparing drawings', status: 'pending' },
      { id: 'summary', name: 'Generating summary', status: 'pending' }
    ])
    pollJobStatus(jobId)
  }, [pollJobStatus])

  useEffect(() => {
    if (!user || activeJobId) return
    if (typeof window === 'undefined') return
    const jobId = sessionStorage.getItem('buildtrace-active-job')
    if (jobId) {
      resumeExistingJob(jobId)
    }
  }, [user, activeJobId, resumeExistingJob])

  // Return null during SSR and initial client render to prevent hydration mismatch
  // MUST BE AFTER ALL HOOKS
  if (!mounted || !isAuthenticated || !user) {
    return null
  }

  const canCompare = oldFile && newFile && !isProcessing && Boolean(selectedProjectId)
  const userId = user.user_id

  const handleReset = () => {
    stopPolling()
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('buildtrace-active-job')
    }
    setStoredJobId(null)
    setOldFile(null)
    setNewFile(null)
    setIsProcessing(false)
    setCurrentStep(1)
    setProcessingSteps([])
    setUploadProgress(0)
    setActiveJobId(null)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="container mx-auto px-4 py-8 space-y-8 max-w-7xl">
        {/* Hero Section */}
        <div className="text-center py-12" data-testid="hero-section">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">BuildTrace AI</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Intelligently detect and analyze changes between construction drawing versions
          </p>
        </div>

        {/* Drawing Comparison Card */}
        <div className="bg-white rounded-2xl shadow-card p-8" data-testid="drawing-comparison-card">
          <h2 className="text-2xl font-semibold text-gray-900 mb-8">Drawing Comparison</h2>
          
          {/* Project Selector - Bigger Cards */}
          <div className="mb-8">
            <label className="block text-sm font-medium text-gray-700 mb-3">Select Project</label>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...projects, { project_id: 'default-project', name: 'Default Project', description: 'Default workspace for comparisons', location: '' }]
                .filter((project, index, arr) => arr.findIndex(p => p.project_id === project.project_id) === index)
                .map(project => (
                  <button
                    key={project.project_id}
                    onClick={() => setSelectedProjectId(project.project_id)}
                    className={`
                      p-5 rounded-xl border-2 text-left transition-all hover:shadow-md
                      ${selectedProjectId === project.project_id 
                        ? 'border-blue-500 bg-blue-50 shadow-md' 
                        : 'border-gray-200 bg-white hover:border-gray-300'
                      }
                    `}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className={`font-semibold text-lg ${selectedProjectId === project.project_id ? 'text-blue-700' : 'text-gray-900'}`}>
                          {project.name}
                        </h3>
                        {project.description && (
                          <p className="text-sm text-gray-500 mt-1 line-clamp-2">{project.description}</p>
                        )}
                        {project.location && (
                          <p className="text-xs text-gray-400 mt-2 flex items-center">
                            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            {project.location}
                          </p>
                        )}
                      </div>
                      {selectedProjectId === project.project_id && (
                        <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0 ml-2">
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </div>
                  </button>
                ))}
            </div>
          </div>

          {/* Stepper */}
          <ProgressSteps currentStep={currentStep} className="mb-8" />

          {!isProcessing ? (
            <>
              {/* Upload Dropzones */}
              <div className="grid md:grid-cols-2 gap-8 mb-8">
                <FileUploader
                  title="Baseline Drawing (Old)"
                  description="Drag & drop your baseline drawing here"
                  file={oldFile}
                  onFileSelect={(file) => handleFileSelect('old', file)}
                  onRemoveFile={() => handleRemoveFile('old')}
                  accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg"
                  maxSize={70 * 1024 * 1024}
                />

                <FileUploader
                  title="Revised Drawing (New)"
                  description="Drag & drop your revised drawing here"
                  file={newFile}
                  onFileSelect={(file) => handleFileSelect('new', file)}
                  onRemoveFile={() => handleRemoveFile('new')}
                  accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg"
                  maxSize={70 * 1024 * 1024}
                />
              </div>

              {/* Compare Button */}
              <div className="text-center">
                <Button
                  onClick={handleStartProcessing}
                  disabled={!canCompare}
                  size="lg"
                  className="px-8 py-3 text-lg font-semibold"
                  data-testid="button-compare-drawings"
                >
                  {isProcessing ? "Processing..." : "Compare Drawings"}
                </Button>
              </div>
            </>
          ) : (
            <ProcessingMonitor
              steps={processingSteps}
              jobId={activeJobId ?? undefined}
              onReset={handleReset}
              onViewResults={activeJobId ? () => router.push(`/results?jobId=${activeJobId}`) : undefined}
            />
          )}
        </div>

        {/* Recent Comparisons Table */}
        {!isProcessing && (
          <RecentSessions />
        )}
      </div>
    </div>
  )
}
