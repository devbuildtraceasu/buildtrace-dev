'use client'

import React, { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'react-hot-toast'
import Header from '@/components/layout/Header'
import FileUploader from '@/components/upload/FileUploader'
import ProcessingMonitor from '@/components/upload/ProcessingMonitor'
import RecentSessions from '@/components/upload/RecentSessions'
import ProgressSteps from '@/components/upload/ProgressSteps'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { apiClient } from '@/lib/api'
import { ProcessingStep } from '@/types'

export default function UploadPage() {
  const router = useRouter()
  const [oldFile, setOldFile] = useState<File | null>(null)
  const [newFile, setNewFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([])
  const [uploadProgress, setUploadProgress] = useState(0)

  const canCompare = oldFile && newFile && !isProcessing

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
    if (!oldFile || !newFile) {
      toast.error('Please upload both files before processing')
      return
    }

    setIsProcessing(true)
    setCurrentStep(3)
    setUploadProgress(0)

    try {
      // Initialize processing steps
      const steps: ProcessingStep[] = [
        { id: 'upload', name: 'Uploading files', status: 'active', progress: 0 },
        { id: 'extract', name: 'Extracting drawing names', status: 'pending' },
        { id: 'convert', name: 'Converting to images', status: 'pending' },
        { id: 'align', name: 'Aligning drawings', status: 'pending' },
        { id: 'analyze', name: 'AI analysis', status: 'pending' }
      ]
      setProcessingSteps(steps)

      // Prepare form data
      const formData = new FormData()
      formData.append('old_file', oldFile)
      formData.append('new_file', newFile)

      // Upload files with progress tracking
      const uploadResponse = await apiClient.submitComparison(
        formData,
        (progress) => {
          setUploadProgress(progress)
          setProcessingSteps(prev => prev.map(step =>
            step.id === 'upload'
              ? { ...step, progress }
              : step
          ))
        }
      )

      // Mark upload as completed
      setProcessingSteps(prev => prev.map(step =>
        step.id === 'upload'
          ? { ...step, status: 'completed', progress: 100 }
          : step.id === 'extract'
          ? { ...step, status: 'active' }
          : step
      ))

      if (!uploadResponse.success || !uploadResponse.data?.session_id) {
        throw new Error(uploadResponse.error || 'Upload failed')
      }

      const sessionId = uploadResponse.data.session_id

      // Start processing
      const processResponse = await apiClient.processSession(sessionId)

      if (!processResponse.success) {
        throw new Error(processResponse.error || 'Processing failed')
      }

      // Simulate step progression (in real app, you'd poll the API)
      const stepIds = ['extract', 'convert', 'align', 'analyze']

      for (let i = 0; i < stepIds.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000))

        setProcessingSteps(prev => prev.map(step => {
          if (step.id === stepIds[i]) {
            return { ...step, status: 'completed' }
          } else if (step.id === stepIds[i + 1]) {
            return { ...step, status: 'active' }
          }
          return step
        }))
      }

      // All steps completed
      setCurrentStep(4)
      toast.success('Processing completed successfully!')

      // Navigate to results page
      setTimeout(() => {
        router.push(`/results/${sessionId}`)
      }, 1500)

    } catch (error: any) {
      console.error('Processing failed:', error)
      toast.error(error.message || 'Processing failed')

      // Mark current step as failed
      setProcessingSteps(prev => prev.map(step =>
        step.status === 'active'
          ? { ...step, status: 'failed', message: error.message }
          : step
      ))
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReset = () => {
    setOldFile(null)
    setNewFile(null)
    setIsProcessing(false)
    setCurrentStep(1)
    setProcessingSteps([])
    setUploadProgress(0)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="container-custom py-8">
        {/* Progress Steps */}
        <ProgressSteps currentStep={currentStep} />

        {/* Main Upload Interface */}
        <div className="mt-8">
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
                {/* File Upload Section */}
                <div className="grid md:grid-cols-2 gap-6 mb-8">
                  <FileUploader
                    title="Baseline Drawing (Old)"
                    description="Drag & drop your baseline drawing here"
                    file={oldFile}
                    onFileSelect={(file) => handleFileSelect('old', file)}
                    onRemoveFile={() => handleRemoveFile('old')}
                    accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg"
                    maxSize={70 * 1024 * 1024} // 70MB
                  />

                  <FileUploader
                    title="Revised Drawing (New)"
                    description="Drag & drop your revised drawing here"
                    file={newFile}
                    onFileSelect={(file) => handleFileSelect('new', file)}
                    onRemoveFile={() => handleRemoveFile('new')}
                    accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg"
                    maxSize={70 * 1024 * 1024} // 70MB
                  />
                </div>

                {/* Compare Button */}
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
              /* Processing Monitor */
              <ProcessingMonitor
                steps={processingSteps}
                onReset={handleReset}
              />
            )}
          </Card>
        </div>

        {/* Recent Sessions */}
        {!isProcessing && (
          <div className="mt-12">
            <RecentSessions />
          </div>
        )}
      </div>
    </div>
  )
}