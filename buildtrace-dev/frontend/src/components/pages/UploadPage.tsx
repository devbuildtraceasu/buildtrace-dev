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
      }

      setProcessingSteps(prev => prev.map(step =>
        step.id === 'upload'
          ? { ...step, status: 'completed', progress: 100 }
          : step.id === 'ocr'
          ? { ...step, status: 'active' }
          : step
      ))

      if (jobId) {
        pollJobStatus(jobId)
      } else {
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
        const job = await apiClient.getJob(jobId)
        const stages = await apiClient.getJobStages(jobId)

        const computeStageState = (stepId: string) => {
          const relevant = stages.stages?.filter((s: any) => {
            if (stepId === 'ocr') return s.stage === 'ocr'
            if (stepId === 'diff') return s.stage === 'diff'
            if (stepId === 'summary') return s.stage === 'summary'
            return false
          }) ?? []

          if (!relevant.length) return null

          const total = relevant.length
          const completedCount = relevant.filter((s: any) => s.status === 'completed' || s.status === 'skipped').length

          if (relevant.some((s: any) => s.status === 'failed')) {
            return { status: 'failed', message: 'Stage failed' }
          }
          if (relevant.some((s: any) => s.status === 'in_progress')) {
            const msg = total > 1 ? `${completedCount}/${total} pages processed` : undefined
            return { status: 'active', message: msg }
          }
          if (completedCount === total) {
            const msg = total > 1 ? `All ${total} pages processed` : undefined
            return { status: 'completed', message: msg }
          }
          if (relevant.some((s: any) => s.status === 'pending')) {
            const msg = total > 1 ? `${completedCount}/${total} pages processed` : undefined
            return { status: 'pending', message: msg }
          }
          return { status: relevant[0].status, message: undefined }
        }

        setProcessingSteps(prev => prev.map(step => {
          const aggregate = computeStageState(step.id)
          if (aggregate) {
            return {
              ...step,
              status: aggregate.status as ProcessingStep['status'],
              message: aggregate.message
            }
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
          pollTimerRef.current = setTimeout(poll, 5000)
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

      <div className="container-custom py-8 space-y-6">
        <ProgressSteps currentStep={currentStep} />

        <Card>
          <div className="flex flex-col space-y-2">
            <label className="text-sm font-medium text-gray-700">Project</label>
            <select
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              {[...projects, { project_id: 'default-project', name: 'Default Project' }]
                .filter((project, index, arr) => arr.findIndex(p => p.project_id === project.project_id) === index)
                .map(project => (
                  <option key={project.project_id} value={project.project_id}>
                    {project.name}
                  </option>
                ))}
            </select>
          </div>
        </Card>

        <Card className="mb-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Drawing Comparison
            </h1>
            <p className="text-gray-600">
              Upload your baseline and revised drawings to analyze changes
            </p>
          </div>

          {!isProcessing ? (
            <>
              <div className="grid md:grid-cols-2 gap-6 mb-8">
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

              <div className="text-center">
                <Button
                  onClick={handleStartProcessing}
                  disabled={!canCompare}
                  size="lg"
                  className="px-8 py-3"
                >
                  Compare Drawings
                </Button>
                <p className="text-sm text-gray-500 mt-2">
                  Supported formats: PDF, DWG, DXF, PNG, JPG (Max 70MB each)
                </p>
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
        </Card>

        {!isProcessing && (
          <div className="mt-12">
            <RecentSessions />
          </div>
        )}
      </div>
    </div>
  )
}
