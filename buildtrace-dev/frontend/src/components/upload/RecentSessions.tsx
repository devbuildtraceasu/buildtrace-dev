'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { clsx } from 'clsx'
import { Eye, Clock, FileText, Calendar } from 'lucide-react'
import { apiClient } from '@/lib/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { JobSummaryRow, JobStage } from '@/types'
import { useAuthStore } from '@/store/authStore'

type StageSummaryItem = {
  stage: JobStage['stage']
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progressLabel?: string
  message?: string
}

export default function RecentSessions() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [sessions, setSessions] = useState<JobSummaryRow[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [stageSummaries, setStageSummaries] = useState<Record<string, StageSummaryItem[]>>({})
  const [stagesLoading, setStagesLoading] = useState(false)

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
      const response = await apiClient.listJobs({ userId: user.user_id, limit: 5 })
      const jobs = response.jobs || []
      setSessions(jobs)
      loadStageSummaries(jobs)
    } catch (error) {
      console.error('Failed to load jobs', error)
      setSessions([])
      setStageSummaries({})
    } finally {
      setIsLoading(false)
    }
  }, [user, loadStageSummaries])

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
      <Card>
        <div className="text-center py-12">
          <LoadingSpinner size="lg" />
          <p className="text-gray-500 mt-4">Loading recent comparisons...</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Recent Comparisons</h2>
        {user && (
        <Button
          variant="ghost"
          size="sm"
            onClick={loadJobs}
          className="flex items-center space-x-2"
            disabled={isLoading}
        >
          <Clock className="w-4 h-4" />
          <span>Refresh</span>
        </Button>
        )}
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No comparisons yet</h3>
          <p className="text-gray-500">
            Upload your first pair of drawings to get started
          </p>
        </div>
      ) : (
        <div className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Job ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sessions.map((session) => (
                  <tr key={session.job_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(session.created_at)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {session.job_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(session.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                      <div className="flex flex-col items-center space-y-2">
                        <div className="flex flex-wrap justify-center gap-2">
                          {(stageSummaries[session.job_id] || []).map((stage) => (
                            <span
                              key={`${session.job_id}-${stage.stage}`}
                              className={clsx(
                                'px-2 py-1 rounded-full text-xs font-medium min-w-[80px] text-center',
                                stageStatusClass(stage.status)
                              )}
                            >
                              {formatStageLabel(stage.stage)}
                              {stage.progressLabel ? ` · ${stage.progressLabel}` : ''}
                              {stage.status === 'failed' && stage.message ? ' ⚠' : ''}
                            </span>
                          ))}
                          {!stageSummaries[session.job_id]?.length && (
                            <span className="text-xs text-gray-400">
                              {stagesLoading ? 'Loading stages…' : 'No stage data'}
                            </span>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/results?jobId=${session.job_id}`)}
                          className="flex items-center space-x-1"
                        >
                          <Eye className="w-4 h-4" />
                          <span>View</span>
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  )
}

