'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'react-hot-toast'
import { apiClient } from '@/lib/api'
import { DrawingComparison, ChangeDetail } from '@/types'
import Header from '@/components/layout/Header'
import DrawingViewer from '@/components/results/DrawingViewer'
import ChangesList from '@/components/results/ChangesList'
import ChatAssistant from '@/components/results/ChatAssistant'
import ResultsOverview from '@/components/results/ResultsOverview'
import Card from '@/components/ui/Card'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import Button from '@/components/ui/Button'
import { ArrowLeft } from 'lucide-react'

interface ResultsPageProps {
  sessionId: string
}

const ResultsPage: React.FC<ResultsPageProps> = ({ sessionId }) => {
  const router = useRouter()
  const [drawings, setDrawings] = useState<DrawingComparison[]>([])
  const [changes, setChanges] = useState<ChangeDetail[]>([])
  const [selectedDrawingIndex, setSelectedDrawingIndex] = useState(0)
  const [selectedChangeIndex, setSelectedChangeIndex] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadResultsData()
  }, [sessionId])

  const loadResultsData = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Load drawings and changes in parallel
      const [drawingsResponse, changesResponse] = await Promise.all([
        apiClient.getDrawingImages(sessionId),
        apiClient.getChangeDetails(sessionId)
      ])

      if (drawingsResponse.success && drawingsResponse.data?.drawings) {
        setDrawings(drawingsResponse.data.drawings)
      }

      if (changesResponse.success && changesResponse.data?.changes) {
        setChanges(changesResponse.data.changes)
      }

      // Auto-select first change if available
      if (changesResponse.data?.changes && changesResponse.data.changes.length > 0) {
        setSelectedChangeIndex(0)
      }

    } catch (error: any) {
      console.error('Failed to load results:', error)
      setError(error.message || 'Failed to load results')
      toast.error('Failed to load results')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDrawingSelect = (index: number) => {
    setSelectedDrawingIndex(index)
  }

  const handleChangeSelect = (index: number) => {
    setSelectedChangeIndex(index)

    // Find corresponding drawing and auto-select it
    const change = changes[index]
    if (change) {
      const drawingIndex = drawings.findIndex(
        d => d.drawing_name === change.drawing_number
      )
      if (drawingIndex >= 0) {
        setSelectedDrawingIndex(drawingIndex)
      }
    }
  }

  const handleBackToUpload = () => {
    router.push('/')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container-custom py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="text-gray-500 mt-4">Loading comparison results...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container-custom py-8">
          <Card className="text-center py-12">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Failed to Load Results
            </h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <div className="space-x-4">
              <Button onClick={loadResultsData} variant="primary">
                Try Again
              </Button>
              <Button onClick={handleBackToUpload} variant="secondary">
                Back to Upload
              </Button>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="container-custom py-6">
        {/* Header Actions */}
        <div className="flex items-center justify-between mb-6">
          <Button
            onClick={handleBackToUpload}
            variant="ghost"
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>New Comparison</span>
          </Button>

          <h1 className="text-2xl font-bold text-gray-900">
            Comparison Results
          </h1>

          <div /> {/* Spacer for flex layout */}
        </div>

        {/* Results Overview */}
        <ResultsOverview
          drawings={drawings}
          changes={changes}
          sessionId={sessionId}
        />

        {/* Main Content Layout */}
        <div className="grid lg:grid-cols-3 gap-6 mt-8">
          {/* Drawing Viewer - Takes up 2 columns */}
          <div className="lg:col-span-2">
            <DrawingViewer
              drawings={drawings}
              selectedIndex={selectedDrawingIndex}
              onDrawingSelect={handleDrawingSelect}
              selectedChange={selectedChangeIndex !== null ? changes[selectedChangeIndex] : null}
            />
          </div>

          {/* Changes List - Takes up 1 column */}
          <div className="space-y-6">
            <ChangesList
              changes={changes}
              selectedIndex={selectedChangeIndex}
              onChangeSelect={handleChangeSelect}
            />
          </div>
        </div>

        {/* Chat Assistant */}
        <div className="mt-8">
          <ChatAssistant
            sessionId={sessionId}
            drawings={drawings}
            changes={changes}
          />
        </div>
      </div>
    </div>
  )
}

export default ResultsPage