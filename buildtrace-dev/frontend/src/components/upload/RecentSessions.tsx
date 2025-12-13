'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { clsx } from 'clsx'
import { Eye, FileText, FolderOpen, List, LayoutGrid, ChevronDown, ChevronRight, Trash2, RefreshCw } from 'lucide-react'
import { apiClient } from '@/lib/api'
import Button from '@/components/ui/Button'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { JobSummaryRow, JobStage, Project } from '@/types'
import { useAuthStore } from '@/store/authStore'

type StageSummaryItem = {
  stage: JobStage['stage']
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progressLabel?: string
  message?: string
}

type ViewMode = 'flat' | 'byProject'

interface ProjectWithJobs {
  project: Project
  jobs: JobSummaryRow[]
}

export default function RecentSessions() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [sessions, setSessions] = useState<JobSummaryRow[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [stageSummaries, setStageSummaries] = useState<Record<string, StageSummaryItem[]>>({})
  const [stagesLoading, setStagesLoading] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('flat')
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())

  const summarizeStages = (stages: JobStage[]): StageSummaryItem[] => {
    const summary: StageSummaryItem[] = []
    const orderedStages: JobStage['stage'][] = ['ocr', 'diff', 'summary']

    orderedStages.forEach((stageKey) => {
      const entries = stages.filter((stage) => stage.stage === stageKey)
      if (!entries.length) {
        return
      }

      const total = entries.length
      const completed = entries.filter((stage) => stage.status === 'completed' || stage.status === 'skipped').length
      const failedStage = entries.find((stage) => stage.status === 'failed')
      const inProgressStage = entries.find((stage) => stage.status === 'in_progress')

      let status: StageSummaryItem['status'] = 'pending'
      let message: string | undefined

      if (failedStage) {
        status = 'failed'
        message = failedStage.error_message || 'Failed'
      } else if (inProgressStage) {
        status = 'in_progress'
      } else if (completed === total) {
        status = 'completed'
      }

      summary.push({
        stage: stageKey,
        status,
        message,
        progressLabel: total > 1 ? `${completed}/${total}` : undefined
      })
    })

    return summary
  }

  const loadStageSummaries = useCallback(async (jobs: JobSummaryRow[]) => {
    if (!jobs.length) {
      setStageSummaries({})
      return
    }

    setStagesLoading(true)

    try {
      const entries = await Promise.all(
        jobs.map(async (job) => {
          try {
            const response = await apiClient.getJobStages(job.job_id)
            return [job.job_id, summarizeStages(response.stages || [])] as const
          } catch (error) {
            console.warn(`Failed to load stages for job ${job.job_id}`, error)
            return [job.job_id, []] as const
          }
        })
      )

      setStageSummaries(Object.fromEntries(entries))
    } finally {
      setStagesLoading(false)
    }
  }, [])

  const loadJobs = useCallback(async () => {
    if (!user) return
    setIsLoading(true)
    try {
      // Load jobs and projects in parallel
      const [jobsResponse, projectsData] = await Promise.all([
        apiClient.listJobs({ userId: user.user_id, limit: 20 }),
        apiClient.getProjects(user.user_id)
      ])
      const jobs = jobsResponse.jobs || []
      setSessions(jobs)
      setProjects(projectsData as Project[] || [])
      loadStageSummaries(jobs)
      
      // Auto-expand first project if in byProject mode
      if (projectsData?.length > 0) {
        setExpandedProjects(new Set([projectsData[0].project_id]))
      }
    } catch (error) {
      console.error('Failed to load jobs', error)
      setSessions([])
      setProjects([])
      setStageSummaries({})
    } finally {
      setIsLoading(false)
    }
  }, [user, loadStageSummaries])
  
  // Group jobs by project
  const projectsWithJobs = useMemo((): ProjectWithJobs[] => {
    const projectMap = new Map<string, ProjectWithJobs>()
    
    // Initialize with all projects
    projects.forEach(project => {
      projectMap.set(project.project_id, { project, jobs: [] })
    })
    
    // Group jobs by project
    sessions.forEach(job => {
      const projectEntry = projectMap.get(job.project_id)
      if (projectEntry) {
        projectEntry.jobs.push(job)
      }
    })
    
    // Return only projects with jobs, sorted by most recent activity
    return Array.from(projectMap.values())
      .filter(p => p.jobs.length > 0)
      .sort((a, b) => {
        const aLatest = a.jobs[0]?.created_at || ''
        const bLatest = b.jobs[0]?.created_at || ''
        return bLatest.localeCompare(aLatest)
      })
  }, [sessions, projects])
  
  const toggleProjectExpand = (projectId: string) => {
    setExpandedProjects(prev => {
      const next = new Set(prev)
      if (next.has(projectId)) {
        next.delete(projectId)
      } else {
        next.add(projectId)
      }
      return next
    })
  }

  useEffect(() => {
    if (!user) return
    loadJobs()
  }, [user, loadJobs])

  const formatDate = (dateString?: string) => {
    if (!dateString) return '—'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Format relative time like "1 day ago", "2 days ago"
  const formatRelativeTime = (dateString?: string) => {
    if (!dateString) return '—'
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min${diffMins === 1 ? '' : 's'} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
    if (diffDays === 1) return '1 day ago'
    if (diffDays < 30) return `${diffDays} days ago`
    return formatDate(dateString)
  }

  // Truncate file name for display
  const truncateFileName = (name?: string, maxLength: number = 16) => {
    if (!name) return '—'
    if (name.length <= maxLength) return name
    const ext = name.includes('.') ? name.substring(name.lastIndexOf('.')) : ''
    const baseName = name.substring(0, name.lastIndexOf('.') || name.length)
    const truncatedBase = baseName.substring(0, maxLength - ext.length - 4)
    return `${truncatedBase}....${ext}`
  }

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { color: string; label: string }> = {
      completed: { color: 'bg-green-100 text-green-800', label: 'Completed' },
      processing: { color: 'bg-yellow-100 text-yellow-800', label: 'Processing' },
      failed: { color: 'bg-red-100 text-red-800', label: 'Failed' },
      pending: { color: 'bg-blue-100 text-blue-800', label: 'Pending' }
    }

    const config = statusConfig[status] || statusConfig.pending

    return (
      <span className={clsx(
        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
        config.color
      )}>
        {config.label}
      </span>
    )
  }

  const stageStatusClass = (status: StageSummaryItem['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 text-green-700 border border-green-200'
      case 'in_progress':
        return 'bg-blue-50 text-blue-700 border border-blue-200'
      case 'failed':
        return 'bg-red-50 text-red-700 border border-red-200'
      default:
        return 'bg-gray-50 text-gray-600 border border-gray-200'
    }
  }

  const formatStageLabel = (stage: JobStage['stage']) => {
    if (stage === 'ocr') return 'OCR'
    if (stage === 'diff') return 'Diff'
    return 'Summary'
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl shadow-card p-8">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-6"></div>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Render job row (reused in both views)
  const renderJobRow = (session: JobSummaryRow) => (
    <tr 
      key={session.job_id} 
      className="hover:bg-gray-50 border-b border-gray-100"
      data-testid={`row-comparison-${session.job_id}`}
    >
      <td className="py-4 px-4 text-sm text-gray-500" data-testid="text-date">
        {formatRelativeTime(session.created_at)}
      </td>
      <td className="py-4 px-4 text-sm text-gray-700" title={session.baseline_name}>
        {truncateFileName(session.baseline_name)}
      </td>
      <td className="py-4 px-4 text-sm text-gray-700" title={session.revised_name}>
        {truncateFileName(session.revised_name)}
      </td>
      <td className="py-4 px-4 text-center">
        <span className={clsx(
          'inline-flex items-center justify-center min-w-[2rem] px-2 py-0.5 rounded text-sm font-medium',
          session.change_count && session.change_count > 0 
            ? 'text-green-600' 
            : 'text-gray-400 border border-dashed border-gray-300'
        )}>
          {session.change_count || 0}
        </span>
      </td>
      <td className="py-4 px-4">
        <span className={clsx(
          'inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold uppercase tracking-wide',
          session.status === 'completed' ? 'bg-green-100 text-green-700' :
          session.status === 'in_progress' || session.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
          session.status === 'failed' ? 'bg-red-100 text-red-700' :
          'bg-gray-100 text-gray-600'
        )}>
          {session.status === 'in_progress' ? 'Processing' : session.status}
        </span>
      </td>
      <td className="py-4 px-4">
        <div className="flex items-center space-x-1">
          <button
            onClick={() => router.push(`/results?jobId=${session.job_id}`)}
            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="View results"
            data-testid={`button-view-${session.job_id}`}
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={() => {
              if (confirm('Are you sure you want to delete this comparison?')) {
                // TODO: Implement delete API
                console.log('Delete job:', session.job_id)
              }
            }}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Delete comparison"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  )

  return (
    <div className="bg-white rounded-2xl shadow-card p-8">
      {/* Header with view toggle */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-gray-900" data-testid="recent-comparisons-title">
          Recent Comparisons
        </h2>
        <div className="flex items-center space-x-3">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('flat')}
              className={clsx(
                'flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                viewMode === 'flat' 
                  ? 'bg-white text-blue-600 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              )}
            >
              <List className="w-4 h-4" />
              <span>List</span>
            </button>
            <button
              onClick={() => setViewMode('byProject')}
              className={clsx(
                'flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                viewMode === 'byProject' 
                  ? 'bg-white text-blue-600 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              )}
            >
              <LayoutGrid className="w-4 h-4" />
              <span>By Project</span>
            </button>
          </div>
          
          {user && (
            <Button
              variant="ghost"
              size="sm"
              onClick={loadJobs}
              className="flex items-center space-x-2"
              disabled={isLoading}
            >
              <RefreshCw className={clsx("w-4 h-4", isLoading && "animate-spin")} />
              <span>Refresh</span>
            </Button>
          )}
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No comparisons yet</h3>
          <p className="text-gray-500">
            Upload your first pair of drawings to get started
          </p>
        </div>
      ) : viewMode === 'flat' ? (
        /* Flat List View */
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="table-recent-comparisons">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Baseline</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Revised</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Changes</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(renderJobRow)}
            </tbody>
          </table>
        </div>
      ) : (
        /* Project Grouped View */
        <div className="space-y-4">
          {projectsWithJobs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FolderOpen className="w-10 h-10 text-gray-400 mx-auto mb-3" />
              <p>No projects with comparisons found</p>
            </div>
          ) : (
            projectsWithJobs.map(({ project, jobs }) => (
              <div key={project.project_id} className="border border-gray-200 rounded-xl overflow-hidden">
                {/* Project Header */}
                <button
                  onClick={() => toggleProjectExpand(project.project_id)}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <FolderOpen className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-gray-900">{project.name}</h3>
                      <p className="text-sm text-gray-500">
                        {jobs.length} comparison{jobs.length !== 1 ? 's' : ''}
                        {project.location && ` • ${project.location}`}
                      </p>
                    </div>
                  </div>
                  {expandedProjects.has(project.project_id) ? (
                    <ChevronDown className="w-5 h-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-500" />
                  )}
                </button>
                
                {/* Jobs Table (expanded) */}
                {expandedProjects.has(project.project_id) && (
                  <div className="bg-white">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-100">
                          <th className="text-left py-2 px-4 text-xs font-medium text-gray-500 uppercase">Date</th>
                          <th className="text-left py-2 px-4 text-xs font-medium text-gray-500 uppercase">Baseline</th>
                          <th className="text-left py-2 px-4 text-xs font-medium text-gray-500 uppercase">Revised</th>
                          <th className="text-center py-2 px-4 text-xs font-medium text-gray-500 uppercase">Changes</th>
                          <th className="text-left py-2 px-4 text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="text-left py-2 px-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map(renderJobRow)}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

