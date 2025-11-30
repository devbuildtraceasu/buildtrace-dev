'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Header from '@/components/layout/Header'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { apiClient } from '@/lib/api'
import OverlayImageViewer from '@/components/results/OverlayImageViewer'
import ViewModeToggle from '@/components/results/ViewModeToggle'
import ChangesList from '@/components/results/ChangesList'
import ChangeDetailsPanel from '@/components/results/ChangeDetailsPanel'
import { ViewMode, ChangeItem, ChangeDetails } from '@/components/results/types'
import SummaryPanel from '@/components/results/SummaryPanel'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { useAuthStore } from '@/store/authStore'
import { DiffResultEntry, JobResults } from '@/types'
import { ArrowLeft, CheckCircle, AlertTriangle, FileText, Layers } from 'lucide-react'
import { parseSummaryToChanges, changeItemToDetails } from '@/utils/parseChanges'
import { parseCategoriesFromSummary, calculateChangeKPIs, Category } from '@/utils/parseCategories'
import { Search, Download, Eye, EyeOff, Settings, Info, DollarSign, Calendar } from 'lucide-react'

// JobResults interface is now imported from types

// KPI Tile Component
function KpiTile({ 
  label, 
  value, 
  color,
  icon: Icon 
}: { 
  label: string
  value: number | string
  color: 'green' | 'red' | 'yellow' | 'blue'
  icon?: React.ElementType
}) {
  const colorClasses = {
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
  }

  return (
    <div className={`px-6 py-4 rounded-lg border ${colorClasses[color]} flex items-center space-x-3`}>
      {Icon && <Icon className="w-5 h-5" />}
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-sm opacity-80">{label}</p>
      </div>
    </div>
  )
}

export default function ResultsPage() {
  const params = useSearchParams()
  const router = useRouter()
  const { user, isAuthenticated } = useAuthStore()
  const [mounted, setMounted] = useState(false)
  const [jobId, setJobId] = useState('')
  const [results, setResults] = useState<JobResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDiffId, setSelectedDiffId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('overlay')
  const [selectedChangeId, setSelectedChangeId] = useState<string | null>(null)
  const [changes, setChanges] = useState<ChangeItem[]>([])
  const [changeDetails, setChangeDetails] = useState<ChangeDetails | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showComparison, setShowComparison] = useState(true)
  const [showDebugInfo, setShowDebugInfo] = useState(false)
  const [baselineFileName, setBaselineFileName] = useState<string>('')
  const [revisedFileName, setRevisedFileName] = useState<string>('')

  useEffect(() => {
    setMounted(true)
  }, [])

  // Define fetchResults before using it in useEffect
  const fetchResults = useCallback(async (id: string) => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const response: any = await apiClient.getJobResults(id)
      setResults(response)
      if (response?.diffs?.length) {
        setSelectedDiffId(response.diffs[0].diff_result_id)
      } else {
        setSelectedDiffId(null)
      }
      
      // File names are now included in the response
      if (response.baseline_file_name) {
        setBaselineFileName(response.baseline_file_name)
      }
      if (response.revised_file_name) {
        setRevisedFileName(response.revised_file_name)
      }
    } catch (err: any) {
      console.error('Error fetching job results:', err)
      setError(err.message || 'Failed to load job results')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const queryJobId = params.get('jobId')
    if (queryJobId) {
      setJobId(queryJobId)
      fetchResults(queryJobId)
    }
  }, [params, fetchResults])

  // Calculate selectedDiff BEFORE early return (needed for useEffect dependencies)
  const selectedDiff = results?.diffs?.find((diff) => diff.diff_result_id === selectedDiffId)

  // Parse changes from summary when diff changes - MUST BE BEFORE EARLY RETURN
  useEffect(() => {
    try {
      if (selectedDiff?.summary?.summary_text) {
        const parsedChanges = parseSummaryToChanges(
          selectedDiff.summary.summary_text,
          selectedDiff.drawing_name,
          selectedDiff.page_number
        )
        setChanges(parsedChanges)
        
        // Auto-select first change if available
        if (parsedChanges.length > 0 && !selectedChangeId) {
          setSelectedChangeId(parsedChanges[0].id)
        }
      } else {
        setChanges([])
        setSelectedChangeId(null)
      }
    } catch (err) {
      console.error('Error parsing changes:', err)
      setChanges([])
      setSelectedChangeId(null)
    }
  }, [selectedDiff, selectedChangeId])

  // Update change details when selection changes - MUST BE BEFORE EARLY RETURN
  useEffect(() => {
    const loadChangeDetails = async () => {
      try {
        if (selectedChangeId && changes.length > 0 && selectedDiff) {
          const selectedChange = changes.find(c => c.id === selectedChangeId)
          if (selectedChange) {
            // Fetch image URLs for thumbnails
            let overlayUrl: string | undefined
            let baselineUrl: string | undefined
            let revisedUrl: string | undefined
            
            try {
              const imagesResponse = await apiClient.getAllImageUrls(selectedDiff.diff_result_id)
              overlayUrl = imagesResponse.overlay_image_url
              baselineUrl = imagesResponse.baseline_image_url || undefined
              revisedUrl = imagesResponse.revised_image_url || undefined
            } catch (e) {
              console.debug('Could not load image URLs for change details:', e)
            }
            
            const details = changeItemToDetails(selectedChange, overlayUrl, baselineUrl, revisedUrl)
            setChangeDetails(details)
          }
        } else {
          setChangeDetails(null)
        }
      } catch (err) {
        console.error('Error creating change details:', err)
        setChangeDetails(null)
      }
    }
    
    loadChangeDetails()
  }, [selectedChangeId, changes, selectedDiff])

  // Prevent hydration mismatch - MUST BE AFTER ALL HOOKS
  if (!mounted || !isAuthenticated || !user) {
    return null
  }

  const handleSubmit = useCallback((event: React.FormEvent) => {
    event.preventDefault()
    if (jobId) {
      fetchResults(jobId)
    }
  }, [jobId, fetchResults])

  // Use KPIs and categories from backend if available, otherwise calculate from frontend
  const kpis = results?.kpis || (() => {
    const allChanges = changes.length > 0 ? changes : 
      (results?.diffs?.flatMap(d => {
        if (d.summary?.summary_text) {
          return parseSummaryToChanges(d.summary.summary_text, d.drawing_name, d.page_number)
        }
        return []
      }) || [])
    return calculateChangeKPIs(allChanges)
  })()
  
  // Use categories from backend if available, otherwise parse from summaries
  const categories = results?.categories || (() => {
    const allSummaries = results?.diffs?.map(d => d.summary?.summary_text).filter(Boolean).join(' ') || ''
    return parseCategoriesFromSummary(allSummaries)
  })()
  
  // Get drawing number from selected diff
  const drawingNumber = selectedDiff?.drawing_name || selectedDiff?.page_number 
    ? `Page-${selectedDiff.page_number || 'N/A'}` 
    : undefined

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container-custom py-8 space-y-6">
        {/* Header with Back Button and File Names */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button 
              variant="ghost" 
              onClick={() => router.push('/')}
              className="flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Comparison Results</h1>
              {(baselineFileName || revisedFileName) && (
                <p className="text-sm text-gray-600 mt-1">
                  {baselineFileName} vs {revisedFileName}
                </p>
              )}
            </div>
          </div>
        </div>
        
        {/* Drawing Number Chip */}
        {drawingNumber && (
          <Card className="bg-white">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Drawing Number:</span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                {drawingNumber}
              </span>
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                Auto-detected from drawing
              </span>
            </div>
          </Card>
        )}

        {/* Job ID Search */}
        <Card>
          <form className="flex flex-col md:flex-row md:items-end gap-4" onSubmit={handleSubmit}>
            <div className="flex-1">
              <label className="text-sm font-medium text-gray-700">Job ID</label>
              <input
                type="text"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 mt-1"
                placeholder="Enter a job ID"
              />
            </div>
            <Button type="submit" disabled={!jobId || loading}>
              {loading ? 'Loading...' : 'Load Results'}
            </Button>
          </form>
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </Card>

        {/* Loading State */}
        {loading && (
          <Card>
            <div className="flex flex-col items-center justify-center py-16">
              <LoadingSpinner size="lg" />
              <p className="text-gray-500 mt-4">Loading comparison results...</p>
            </div>
          </Card>
        )}

        {/* Results */}
        {results && !loading && (
          <div className="space-y-6">
            {/* Status Banner */}
            {results.status !== 'completed' && (
              <Card className="bg-amber-50 border-amber-200">
                <div className="flex items-center space-x-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                  <div>
                    <p className="font-medium text-amber-800">
                      Job Status: {results.status}
                    </p>
                    {results.message && (
                      <p className="text-sm text-amber-600">{results.message}</p>
                    )}
                  </div>
                </div>
              </Card>
            )}

            {/* Toolbar */}
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowComparison(!showComparison)}
                    className="flex items-center space-x-1"
                  >
                    {showComparison ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    <span>Hide Comparison</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      // TODO: Implement export report
                      alert('Export Report functionality coming soon')
                    }}
                    className="flex items-center space-x-1"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export Report</span>
                  </Button>
                </div>
                
                <div className="flex items-center space-x-2 flex-1 max-w-md">
                  <Search className="w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search drawing num..."
                    className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                  />
                </div>
                
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDebugInfo(!showDebugInfo)}
                    className="flex items-center space-x-1"
                  >
                    <Info className="w-4 h-4" />
                    <span>Debug Info</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex items-center space-x-1"
                  >
                    <Settings className="w-4 h-4" />
                    <span>View Mode</span>
                  </Button>
                </div>
              </div>
            </Card>

            {/* KPI Tiles - Updated to match demo: Added, Modified, Removed */}
            <div className="grid grid-cols-3 gap-4">
              <KpiTile 
                label="Added" 
                value={kpis.added} 
                color="green"
                icon={CheckCircle}
              />
              <KpiTile 
                label="Modified" 
                value={kpis.modified} 
                color="blue"
                icon={Layers}
              />
              <KpiTile 
                label="Removed" 
                value={kpis.removed} 
                color="red"
                icon={AlertTriangle}
              />
            </div>
            
            {/* By Category List */}
            <Card>
              <h3 className="text-lg font-semibold mb-4">By Category</h3>
              <div className="space-y-2">
                {(Object.keys(categories) as Category[]).map((category) => {
                  const count = categories[category]
                  if (count === 0) return null
                  return (
                    <div key={category} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                      <span className="text-sm font-medium text-gray-700">{category}</span>
                      <span className="text-sm font-semibold text-gray-900">{count}</span>
                    </div>
                  )
                })}
                {Object.values(categories).every(c => c === 0) && (
                  <p className="text-sm text-gray-500 py-4 text-center">No category data available</p>
                )}
              </div>
            </Card>

            {/* Job Info */}
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Job Overview</h2>
                  <p className="text-sm text-gray-500 mt-1">ID: {results.job_id}</p>
                </div>
                {results.completed_at && (
                  <div className="text-right">
                    <p className="text-sm text-gray-500">Completed</p>
                    <p className="text-sm font-medium text-gray-700">
                      {new Date(results.completed_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </Card>

            {/* Page Selector */}
            {results.diffs && results.diffs.length > 0 && (
              <Card>
                <h3 className="text-lg font-semibold mb-4">Select Drawing / Page</h3>
                <div className="flex flex-wrap gap-3">
                  {results.diffs.map((diff, index) => (
                    <button
                      key={diff.diff_result_id}
                      onClick={() => setSelectedDiffId(diff.diff_result_id)}
                      className={`
                        px-4 py-3 rounded-lg border-2 transition-all text-left min-w-[150px]
                        ${diff.diff_result_id === selectedDiffId 
                          ? 'border-blue-500 bg-blue-50 shadow-md' 
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                        }
                      `}
                    >
                      <p className="font-medium text-gray-900">
                        {diff.drawing_name || `Page ${diff.page_number ?? index + 1}`}
                      </p>
                      <div className="flex items-center space-x-2 mt-1">
                        {diff.changes_detected ? (
                          <>
                            <span className="w-2 h-2 rounded-full bg-yellow-500" />
                            <span className="text-xs text-yellow-700">
                              {diff.change_count} change{diff.change_count !== 1 ? 's' : ''}
                            </span>
                          </>
                        ) : (
                          <>
                            <span className="w-2 h-2 rounded-full bg-green-500" />
                            <span className="text-xs text-green-700">No changes</span>
                          </>
                        )}
                      </div>
                      {diff.alignment_score !== undefined && (
                        <p className="text-xs text-gray-500 mt-1">
                          Alignment: {Math.round(diff.alignment_score * 100)}%
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              </Card>
            )}

            {/* Selected Page Details */}
            {selectedDiff && (
              <>
                {/* Change Summary Banner */}
                <Card className={selectedDiff.changes_detected ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200'}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {selectedDiff.changes_detected ? (
                        <AlertTriangle className="w-5 h-5 text-yellow-600" />
                      ) : (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      )}
                      <div>
                        <p className={`font-medium ${selectedDiff.changes_detected ? 'text-yellow-800' : 'text-green-800'}`}>
                          {selectedDiff.drawing_name || `Page ${selectedDiff.page_number}`}
                        </p>
                        <p className={`text-sm ${selectedDiff.changes_detected ? 'text-yellow-600' : 'text-green-600'}`}>
                          {selectedDiff.changes_detected 
                            ? `${selectedDiff.change_count} change${selectedDiff.change_count !== 1 ? 's' : ''} detected` 
                            : 'No changes detected between versions'
                          }
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Alignment Score</p>
                      <p className="text-lg font-bold text-gray-700">
                        {selectedDiff.alignment_score !== undefined 
                          ? `${Math.round(selectedDiff.alignment_score * 100)}%` 
                          : 'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </Card>

                {/* View Mode Toggle */}
                <Card>
                  <ViewModeToggle 
                    currentMode={viewMode} 
                    onModeChange={setViewMode}
                  />
                </Card>

                {/* Overlay Image Viewer - Conditionally shown */}
                {showComparison && (
                  <OverlayImageViewer 
                    diffResultId={selectedDiff.diff_result_id}
                    viewMode={viewMode}
                  />
                )}

                {/* Changes List and Details - Side by Side */}
                {changes.length > 0 && (
                  <div className="grid lg:grid-cols-2 gap-6">
                    <ChangesList
                      changes={changes}
                      selectedChangeId={selectedChangeId}
                      onSelectChange={setSelectedChangeId}
                    />
                    <ChangeDetailsPanel change={changeDetails} />
                  </div>
                )}

                {/* Summary Panel */}
                <SummaryPanel diffResultId={selectedDiff.diff_result_id} />
                
                {/* Ask About Changes Panel */}
                <Card>
                  <h3 className="text-lg font-semibold mb-4">Ask About Changes</h3>
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          // TODO: Implement cost impact analysis
                          alert('Cost Impact analysis coming soon')
                        }}
                        className="flex items-center space-x-1"
                      >
                        <DollarSign className="w-4 h-4" />
                        <span>Cost Impact</span>
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          // TODO: Implement schedule impact analysis
                          alert('Schedule Impact analysis coming soon')
                        }}
                        className="flex items-center space-x-1"
                      >
                        <Calendar className="w-4 h-4" />
                        <span>Schedule Impact</span>
                      </Button>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        placeholder="Ask a question about the changes..."
                        className="flex-1 border border-gray-300 rounded-md px-4 py-2 text-sm"
                        disabled
                      />
                      <Button
                        variant="primary"
                        size="sm"
                        disabled
                      >
                        Ask
                      </Button>
                    </div>
                    <p className="text-xs text-gray-500">AI assistant functionality coming soon</p>
                  </div>
                </Card>
              </>
            )}
            
            {/* Debug Info Panel */}
            {showDebugInfo && results && (
              <Card>
                <h3 className="text-lg font-semibold mb-4">Debug Info</h3>
                <pre className="bg-gray-100 p-4 rounded text-xs overflow-auto max-h-96">
                  {JSON.stringify(results, null, 2)}
                </pre>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
