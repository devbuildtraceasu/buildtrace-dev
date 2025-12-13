'use client'

import React, { useEffect, useState, useCallback, useRef } from 'react'
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
import CostImpactReport from '@/components/results/CostImpactReport'
import ScheduleImpactReport from '@/components/results/ScheduleImpactReport'
import ChatAssistant from '@/components/results/ChatAssistant'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { useAuthStore } from '@/store/authStore'
import { DiffResultEntry, JobResults } from '@/types'
import { ArrowLeft, CheckCircle, AlertTriangle, FileText, Layers, Clock, FileDown, MapPin, Building } from 'lucide-react'
import { parseSummaryToChanges, changeItemToDetails } from '@/utils/parseChanges'
import { parseCategoriesFromSummary, calculateChangeKPIs, Category } from '@/utils/parseCategories'
import { Search, Download, Eye, EyeOff, Settings, Info, DollarSign, Calendar } from 'lucide-react'
import { CostImpactData, ScheduleImpactData, mockCostImpactData, mockScheduleImpactData } from '@/mocks/data'

// JobResults interface is now imported from types

// Helper to format Job ID as readable display name
function formatJobDisplayId(
  jobId: string,
  projectName?: string,
  drawingName?: string,
  pageNumber?: number
): string {
  // Format: BT-ProjectName-DrawingName-Sheet# or BT-xxx (fallback)
  const parts = ['BT']
  
  if (projectName) {
    // Clean project name: take first word or abbreviate
    const cleanProject = projectName.replace(/[^a-zA-Z0-9]/g, '').substring(0, 12)
    parts.push(cleanProject)
  }
  
  if (drawingName) {
    // Use drawing name as-is (usually like A-111)
    const cleanDrawing = drawingName.replace(/[^a-zA-Z0-9-]/g, '').substring(0, 10)
    parts.push(cleanDrawing)
  }
  
  if (pageNumber && pageNumber > 1) {
    parts.push(`S${pageNumber}`)
  }
  
  // If we only have BT prefix, add short job id
  if (parts.length === 1) {
    parts.push(jobId.substring(0, 8))
  }
  
  return parts.join('-')
}

// Top Stats Panel Component (like the screenshot)
function TopStatsPanel({ 
  overlaysCreated, 
  aiAnalyses, 
  processingTime, 
  addedDrawings, 
  modifiedDrawings,
  projectName,
  projectLocation
}: { 
  overlaysCreated: number
  aiAnalyses: number
  processingTime: string
  addedDrawings: number
  modifiedDrawings: number
  projectName?: string
  projectLocation?: string
}) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
      {/* Header */}
      <div className="text-center mb-6">
        <h1 className="text-3xl font-bold text-blue-600">BuildTrace AI</h1>
        <p className="text-gray-500">Comparison Results</p>
        {projectName && (
          <div className="flex items-center justify-center space-x-4 mt-2">
            <div className="flex items-center text-gray-600">
              <Building className="w-4 h-4 mr-1" />
              <span className="text-sm font-medium">{projectName}</span>
            </div>
            {projectLocation && (
              <div className="flex items-center text-gray-600">
                <MapPin className="w-4 h-4 mr-1" />
                <span className="text-sm">{projectLocation}</span>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-5 gap-4 border border-gray-200 rounded-xl p-4 bg-gray-50">
        <div className="text-center">
          <p className="text-3xl font-bold text-blue-600">{overlaysCreated}</p>
          <p className="text-sm text-gray-500">Overlays Created</p>
        </div>
        <div className="text-center border-l border-gray-200">
          <p className="text-3xl font-bold text-blue-600">{aiAnalyses}</p>
          <p className="text-sm text-gray-500">AI Analyses</p>
        </div>
        <div className="text-center border-l border-gray-200">
          <p className="text-3xl font-bold text-blue-600">{processingTime}</p>
          <p className="text-sm text-gray-500">Processing Time</p>
        </div>
        <div className="text-center border-l border-gray-200">
          <p className="text-3xl font-bold text-blue-600">{addedDrawings}</p>
          <p className="text-sm text-gray-500">Added Drawings</p>
        </div>
        <div className="text-center border-l border-gray-200">
          <p className="text-3xl font-bold text-blue-600">{modifiedDrawings}</p>
          <p className="text-sm text-gray-500">Modified Drawings</p>
        </div>
      </div>
    </div>
  )
}

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

// Subcontractor Details Panel Component
function SubcontractorDetailsPanel({ changes, categories }: { changes: ChangeItem[], categories: Record<string, number> }) {
  // Group changes by potential subcontractor trades
  const tradeMapping: Record<string, string[]> = {
    'Electrical': ['electrical', 'wiring', 'conduit', 'panel', 'outlet', 'switch', 'lighting'],
    'Plumbing': ['plumbing', 'pipe', 'drain', 'fixture', 'water', 'sewer'],
    'HVAC': ['hvac', 'duct', 'mechanical', 'air', 'ventilation', 'heating', 'cooling'],
    'Structural': ['structural', 'beam', 'column', 'foundation', 'steel', 'concrete'],
    'Drywall/Framing': ['drywall', 'framing', 'partition', 'wall', 'stud'],
    'Flooring': ['floor', 'tile', 'carpet', 'flooring'],
    'Roofing': ['roof', 'roofing', 'membrane'],
    'Fire Protection': ['fire', 'sprinkler', 'alarm', 'suppression'],
  }

  const subcontractorImpact: Record<string, { count: number, changes: string[] }> = {}

  changes.forEach(change => {
    const summaryLower = change.summary.toLowerCase()
    Object.entries(tradeMapping).forEach(([trade, keywords]) => {
      if (keywords.some(kw => summaryLower.includes(kw))) {
        if (!subcontractorImpact[trade]) {
          subcontractorImpact[trade] = { count: 0, changes: [] }
        }
        subcontractorImpact[trade].count++
        if (subcontractorImpact[trade].changes.length < 3) {
          subcontractorImpact[trade].changes.push(change.summary.substring(0, 100))
        }
      }
    })
  })

  const impactedTrades = Object.entries(subcontractorImpact).filter(([_, data]) => data.count > 0)

  if (impactedTrades.length === 0) {
    return null
  }

  return (
    <Card className="mt-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Building className="w-5 h-5 mr-2 text-blue-600" />
        Subcontractor Impact Summary
      </h3>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {impactedTrades.map(([trade, data]) => (
          <div key={trade} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-900">{trade}</h4>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">
                {data.count} change{data.count !== 1 ? 's' : ''}
              </span>
            </div>
            <ul className="text-sm text-gray-600 space-y-1">
              {data.changes.map((c, i) => (
                <li key={i} className="truncate">• {c}...</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
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
  const [activeReport, setActiveReport] = useState<'none' | 'cost' | 'schedule'>('none')
  const [costImpactData, setCostImpactData] = useState<CostImpactData | null>(null)
  const [scheduleImpactData, setScheduleImpactData] = useState<ScheduleImpactData | null>(null)
  const [loadingCostReport, setLoadingCostReport] = useState(false)
  const [loadingScheduleReport, setLoadingScheduleReport] = useState(false)
  const [jobProgress, setJobProgress] = useState<any>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Define fetchResults before using it in useEffect
  const fetchResults = useCallback(async (id: string, silent: boolean = false) => {
    if (!id) return
    if (!silent) {
      setLoading(true)
    } else {
      setIsRefreshing(true)
    }
    setError(null)
    try {
      const response: any = await apiClient.getJobResults(id)
      setResults(response)
      if (response?.diffs?.length) {
        // Only auto-select first diff if we don't have one selected
        if (!selectedDiffId) {
          setSelectedDiffId(response.diffs[0].diff_result_id)
        }
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
      if (!silent) {
        setError(err.message || 'Failed to load job results')
        setResults(null)
      }
    } finally {
      if (!silent) {
        setLoading(false)
      } else {
        setIsRefreshing(false)
      }
    }
  }, [selectedDiffId])

  useEffect(() => {
    const queryJobId = params.get('jobId')
    if (queryJobId) {
      setJobId(queryJobId)
      fetchResults(queryJobId)
    }
  }, [params, fetchResults])

  // Poll for progress while job is still processing
  // Use refs to persist values across renders and avoid infinite loops
  const lastDiffCompletedRef = useRef<number>(0)
  const lastSummaryCompletedRef = useRef<number>(0)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const fetchResultsRef = useRef(fetchResults)
  const resultsRef = useRef(results)
  
  // Keep refs updated with latest values
  useEffect(() => {
    fetchResultsRef.current = fetchResults
    resultsRef.current = results
  }, [fetchResults, results])
  
  useEffect(() => {
    if (!jobId || !results) return
    
    // Calculate summaries count inside effect to avoid dependency issues
    const summariesCount = results.diffs?.filter(d => d.summary).length || 0
    const totalDiffs = results.diffs?.length || 0
    const allSummariesComplete = totalDiffs > 0 && summariesCount >= totalDiffs
    
    // Initialize refs from current results
    lastDiffCompletedRef.current = totalDiffs
    lastSummaryCompletedRef.current = summariesCount
    
    // Only poll if job is still in progress AND summaries are not all complete
    if (results.status === 'completed' || results.status === 'failed' || allSummariesComplete) {
      setIsPolling(false)
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      return
    }
    
    setIsPolling(true)
    
    const pollProgress = async () => {
      try {
        const progress = await apiClient.getJobProgress(jobId)
        setJobProgress(progress)
        
        // Only refresh if there are actual changes (new diffs or summaries completed)
        const currentDiffCompleted = progress.progress?.diff?.completed || 0
        const currentSummaryCompleted = progress.progress?.summary?.completed || 0
        
        const hasNewDiffs = currentDiffCompleted > lastDiffCompletedRef.current
        const hasNewSummaries = currentSummaryCompleted > lastSummaryCompletedRef.current
        
        if (hasNewDiffs || hasNewSummaries) {
          // Silent refresh - don't show loading spinner
          await fetchResultsRef.current(jobId, true)
          lastDiffCompletedRef.current = currentDiffCompleted
          lastSummaryCompletedRef.current = currentSummaryCompleted
          
          // Check if we should stop polling after refresh
          const updatedResults = resultsRef.current
          const updatedSummariesCount = updatedResults?.diffs?.filter(d => d.summary).length || 0
          const updatedTotalDiffs = updatedResults?.diffs?.length || 0
          if (updatedTotalDiffs > 0 && updatedSummariesCount >= updatedTotalDiffs) {
            setIsPolling(false)
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            return
          }
        }
        
        // Check if completed
        if (progress.status === 'completed') {
          setIsPolling(false)
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
          // Final refresh (silent)
          await fetchResultsRef.current(jobId, true)
        }
      } catch (err) {
        console.debug('Error polling progress:', err)
      }
    }
    
    // Clear any existing interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }
    
    // Poll every 3 seconds
    pollingIntervalRef.current = setInterval(pollProgress, 3000)
    pollProgress() // Initial fetch
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [jobId, results?.status])

  // Reset cost/schedule reports and changes when switching between diff pages
  useEffect(() => {
    // Reset report data when page changes
    setCostImpactData(null)
    setScheduleImpactData(null)
    setActiveReport('none')
    // Reset changes for fresh parsing
    setChanges([])
    setSelectedChangeId(null)
    setChangeDetails(null)
  }, [selectedDiffId])

  // Calculate selectedDiff BEFORE early return (needed for useEffect dependencies)
  // Using a simple variable instead of useMemo to avoid hook order issues
  const selectedDiff = results?.diffs?.find((diff) => diff.diff_result_id === selectedDiffId)

  // Parse changes from summary when diff changes - MUST BE BEFORE EARLY RETURN
  useEffect(() => {
    try {
      if (selectedDiff?.summary?.summary_text) {
        // Pass both text and JSON for structured parsing
        const parsedChanges = parseSummaryToChanges(
          selectedDiff.summary.summary_text,
          selectedDiff.drawing_name,
          selectedDiff.page_number,
          selectedDiff.summary.summary_json  // Structured JSON from backend
        )
        setChanges(parsedChanges)
        
        // Auto-select first change if available
        if (parsedChanges.length > 0) {
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDiff])

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

  // Define handleSubmit BEFORE early return (hook must be called before conditional return)
  const handleSubmit = useCallback(async (event: React.FormEvent) => {
    event.preventDefault()
    const currentJobId = jobId
    if (!currentJobId) return
    
    setLoading(true)
    setError(null)
    try {
      const response: any = await apiClient.getJobResults(currentJobId)
      setResults(response)
      if (response?.diffs?.length) {
        setSelectedDiffId(response.diffs[0].diff_result_id)
      } else {
        setSelectedDiffId(null)
      }
      
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
  }, [jobId])

  // Prevent hydration mismatch - MUST BE AFTER ALL HOOKS
  // Don't use early return - render conditionally instead to avoid hooks count issues
  if (!mounted || !isAuthenticated || !user) {
    return null
  }

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

        {/* Live Progress Panel - shown when job is still processing */}
        {isPolling && jobProgress && (
          <Card className="bg-blue-50 border-blue-200">
            <div className="flex items-center space-x-3 mb-4">
              <LoadingSpinner size="sm" />
              <div>
                <h3 className="font-semibold text-blue-800">Processing Your Drawings...</h3>
                <p className="text-sm text-blue-600">Results will appear below as they complete</p>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              {/* OCR Progress */}
              <div className="bg-white rounded-lg p-3 border border-blue-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">OCR Processing</span>
                  <span className="text-sm text-blue-600">
                    {jobProgress.progress?.ocr?.completed || 0}/{jobProgress.progress?.ocr?.total || 0}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${jobProgress.progress?.ocr?.total 
                        ? (jobProgress.progress.ocr.completed / jobProgress.progress.ocr.total) * 100 
                        : 0}%` 
                    }}
                  />
                </div>
              </div>
              
              {/* Diff Progress */}
              <div className="bg-white rounded-lg p-3 border border-blue-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Comparing</span>
                  <span className="text-sm text-blue-600">
                    {jobProgress.progress?.diff?.completed || 0}/{jobProgress.progress?.diff?.total || 0}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${jobProgress.progress?.diff?.total 
                        ? (jobProgress.progress.diff.completed / jobProgress.progress.diff.total) * 100 
                        : 0}%` 
                    }}
                  />
                </div>
              </div>
              
              {/* Summary Progress */}
              <div className="bg-white rounded-lg p-3 border border-blue-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Summarizing</span>
                  <span className="text-sm text-blue-600">
                    {jobProgress.progress?.summary?.completed || 0}/{jobProgress.progress?.summary?.total || 0}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${jobProgress.progress?.summary?.total 
                        ? (jobProgress.progress.summary.completed / jobProgress.progress.summary.total) * 100 
                        : 0}%` 
                    }}
                  />
                </div>
              </div>
            </div>
            
            {/* Per-page status */}
            {jobProgress.pages && jobProgress.pages.length > 0 && (
              <div className="mt-4 pt-4 border-t border-blue-200">
                <p className="text-sm font-medium text-gray-700 mb-2">Page Status:</p>
                <div className="flex flex-wrap gap-2">
                  {jobProgress.pages.map((page: any) => (
                    <div
                      key={page.page_number}
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        page.summary_status === 'completed' 
                          ? 'bg-green-100 text-green-700' 
                          : page.diff_status === 'completed'
                          ? 'bg-blue-100 text-blue-700'
                          : page.ocr_status === 'completed'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {page.drawing_name || `P${page.page_number}`}: {
                        page.summary_status === 'completed' ? '✓ Complete' :
                        page.diff_status === 'completed' ? 'Summarizing...' :
                        page.ocr_status === 'completed' ? 'Comparing...' :
                        page.ocr_status === 'in_progress' ? 'OCR...' : 'Pending'
                      }
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        )}

        {/* Results */}
        {results && !loading && (
          <div className="space-y-6">
            {/* Top Stats Panel (like screenshot) */}
            <TopStatsPanel
              overlaysCreated={results.diffs?.length || 0}
              aiAnalyses={results.diffs?.filter(d => d.summary?.summary_text).length || 0}
              processingTime={results.completed_at && results.created_at 
                ? `${((new Date(results.completed_at).getTime() - new Date(results.created_at).getTime()) / 1000).toFixed(1)}s`
                : '—'
              }
              addedDrawings={kpis.added}
              modifiedDrawings={kpis.modified}
              projectName={results.project_name}
              projectLocation={results.project_location}
            />
            
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
                    onClick={async () => {
                      if (!jobId) return
                      try {
                        // Ensure we have latest cost & schedule data
                        const [cost, schedule] = await Promise.all([
                          apiClient.getCostImpact(jobId).catch(() => costImpactData),
                          apiClient.getScheduleImpact(jobId).catch(() => scheduleImpactData),
                        ])

                        const exportPayload = {
                          jobId,
                          generatedAt: new Date().toISOString(),
                          project: {
                            name: results?.project_name || null,
                            location: results?.project_location || null,
                            id: results?.project_id || null,
                          },
                          drawings: {
                            baseline: baselineFileName,
                            revised: revisedFileName,
                          },
                          kpis,
                          categories,
                          costImpact: cost || costImpactData || null,
                          scheduleImpact: schedule || scheduleImpactData || null,
                        }

                        const blob = new Blob(
                          [JSON.stringify(exportPayload, null, 2)],
                          { type: 'application/json' }
                        )
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `buildtrace-report-${jobId}.json`
                        a.click()
                        URL.revokeObjectURL(url)
                      } catch (err) {
                        console.error('Failed to export report:', err)
                        alert('Failed to export report. Please try again.')
                      }
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
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-lg text-sm font-mono font-semibold">
                      {formatJobDisplayId(
                        results.job_id,
                        results.project_name,
                        selectedDiff?.drawing_name || baselineFileName?.replace(/\.[^/.]+$/, ''),
                        selectedDiff?.page_number
                      )}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {results.project_name || 'Project'} / {selectedDiff?.drawing_name || baselineFileName?.replace(/\.[^/.]+$/, '') || 'Drawing'}
                  </p>
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

                {/* Overlay Image Viewer - Always show when diff is selected (even during OCR) */}
                {selectedDiff && (
                  <OverlayImageViewer 
                    diffResultId={selectedDiff.diff_result_id}
                    viewMode={viewMode}
                    diffMetadata={selectedDiff.diff_metadata}
                  />
                )}

                {/* Changes List and Details - Side by Side */}
                {changes.length > 0 && (
                  <div className="grid lg:grid-cols-2 gap-6">
                    <ChangesList
                      changes={changes}
                      selectedChangeId={selectedChangeId}
                      onSelectChange={setSelectedChangeId}
                      onRegenerate={() => {
                        apiClient.regenerateSummary(selectedDiff.diff_result_id)
                          .then(() => {
                            // Refresh after regeneration
                            fetchResults(jobId)
                          })
                          .catch(err => console.error('Failed to regenerate:', err))
                      }}
                    />
                    <ChangeDetailsPanel change={changeDetails} />
                  </div>
                )}

                {/* Summary Panel */}
                <SummaryPanel 
                  diffResultId={selectedDiff.diff_result_id} 
                  isProcessing={isPolling && !selectedDiff.summary}
                />
                
                {/* Subcontractor Details Panel */}
                <SubcontractorDetailsPanel changes={changes} categories={categories} />
                
                {/* Cost & Schedule Impact Reports - Separate Section */}
                <div className="grid lg:grid-cols-2 gap-6">
                  {/* Cost Impact Card */}
                  <Card className="border-2 border-green-200 bg-green-50/30">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold flex items-center">
                        <DollarSign className="w-5 h-5 mr-2 text-green-600" />
                        Cost Impact Report
                      </h3>
                      <div className="flex items-center space-x-2">
                        {costImpactData && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              // Generate PDF download
                              const content = JSON.stringify(costImpactData, null, 2)
                              const blob = new Blob([content], { type: 'application/json' })
                              const url = URL.createObjectURL(blob)
                              const a = document.createElement('a')
                              a.href = url
                              a.download = `cost-impact-${jobId}.json`
                              a.click()
                              URL.revokeObjectURL(url)
                            }}
                            title="Download Report"
                          >
                            <FileDown className="w-4 h-4" />
                          </Button>
                        )}
                        <Button
                          variant={activeReport === 'cost' ? 'primary' : 'secondary'}
                          size="sm"
                          disabled={loadingCostReport}
                          onClick={async () => {
                            if (activeReport === 'cost') {
                              setActiveReport('none')
                            } else {
                              setActiveReport('cost')
                              if (!costImpactData && jobId) {
                                setLoadingCostReport(true)
                                try {
                                  const data = await apiClient.getCostImpact(jobId)
                                  setCostImpactData(data as CostImpactData)
                                } catch (err) {
                                  console.error('Failed to load cost impact:', err)
                                  setCostImpactData(mockCostImpactData)
                                } finally {
                                  setLoadingCostReport(false)
                                }
                              }
                            }
                          }}
                        >
                          {loadingCostReport ? 'Loading...' : activeReport === 'cost' ? 'Hide' : 'Generate Report'}
                        </Button>
                      </div>
                    </div>
                    {loadingCostReport && (
                      <div className="flex flex-col items-center justify-center py-8">
                        <LoadingSpinner size="md" />
                        <p className="text-gray-500 mt-3 text-sm">Generating AI-powered cost analysis...</p>
                      </div>
                    )}
                    {activeReport === 'cost' && costImpactData && !loadingCostReport && (
                      <div className="mt-4">
                        <div className="bg-white rounded-lg p-4 border border-green-200">
                          <p className="text-2xl font-bold text-green-700">{costImpactData.ballparkTotal}</p>
                          <p className="text-sm text-gray-500">Estimated Total Impact</p>
                        </div>
                        <p className="text-sm text-gray-600 mt-3">{costImpactData.importantNotes}</p>
                      </div>
                    )}
                    {!costImpactData && !loadingCostReport && activeReport !== 'cost' && (
                      <p className="text-sm text-gray-500">Click "Generate Report" to analyze cost impacts of detected changes.</p>
                    )}
                  </Card>
                  
                  {/* Schedule Impact Card */}
                  <Card className="border-2 border-blue-200 bg-blue-50/30">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold flex items-center">
                        <Calendar className="w-5 h-5 mr-2 text-blue-600" />
                        Schedule Impact Report
                      </h3>
                      <div className="flex items-center space-x-2">
                        {scheduleImpactData && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const content = JSON.stringify(scheduleImpactData, null, 2)
                              const blob = new Blob([content], { type: 'application/json' })
                              const url = URL.createObjectURL(blob)
                              const a = document.createElement('a')
                              a.href = url
                              a.download = `schedule-impact-${jobId}.json`
                              a.click()
                              URL.revokeObjectURL(url)
                            }}
                            title="Download Report"
                          >
                            <FileDown className="w-4 h-4" />
                          </Button>
                        )}
                        <Button
                          variant={activeReport === 'schedule' ? 'primary' : 'secondary'}
                          size="sm"
                          disabled={loadingScheduleReport}
                          onClick={async () => {
                            if (activeReport === 'schedule') {
                              setActiveReport('none')
                            } else {
                              setActiveReport('schedule')
                              if (!scheduleImpactData && jobId) {
                                setLoadingScheduleReport(true)
                                try {
                                  const data = await apiClient.getScheduleImpact(jobId)
                                  setScheduleImpactData(data as ScheduleImpactData)
                                } catch (err) {
                                  console.error('Failed to load schedule impact:', err)
                                  setScheduleImpactData(mockScheduleImpactData)
                                } finally {
                                  setLoadingScheduleReport(false)
                                }
                              }
                            }
                          }}
                        >
                          {loadingScheduleReport ? 'Loading...' : activeReport === 'schedule' ? 'Hide' : 'Generate Report'}
                        </Button>
                      </div>
                    </div>
                    {loadingScheduleReport && (
                      <div className="flex flex-col items-center justify-center py-8">
                        <LoadingSpinner size="md" />
                        <p className="text-gray-500 mt-3 text-sm">Generating AI-powered schedule analysis...</p>
                      </div>
                    )}
                    {activeReport === 'schedule' && scheduleImpactData && !loadingScheduleReport && (
                      <div className="mt-4">
                        <div className="bg-white rounded-lg p-4 border border-blue-200">
                          <p className="text-lg font-bold text-blue-700">{scheduleImpactData.scenarios?.[1]?.impact || 'TBD'}</p>
                          <p className="text-sm text-gray-500">Typical Case Impact</p>
                        </div>
                        <p className="text-sm text-gray-600 mt-3">{scheduleImpactData.bottomLine}</p>
                      </div>
                    )}
                    {!scheduleImpactData && !loadingScheduleReport && activeReport !== 'schedule' && (
                      <p className="text-sm text-gray-500">Click "Generate Report" to analyze schedule impacts of detected changes.</p>
                    )}
                  </Card>
                </div>
                
                {/* Full Cost Impact Report (expanded) */}
                {activeReport === 'cost' && costImpactData && !loadingCostReport && (
                  <CostImpactReport 
                    data={costImpactData} 
                    onClose={() => setActiveReport('none')} 
                  />
                )}
                
                {/* Full Schedule Impact Report (expanded) */}
                {activeReport === 'schedule' && scheduleImpactData && !loadingScheduleReport && (
                  <ScheduleImpactReport 
                    data={scheduleImpactData} 
                    onClose={() => setActiveReport('none')} 
                  />
                )}
                
                {/* AI Chat Assistant */}
                <Card>
                  <ChatAssistant jobId={jobId} />
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
