'use client'

import React, { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Header from '@/components/layout/Header'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { apiClient } from '@/lib/api'
import OverlayEditor from '@/components/results/OverlayEditor'
import SummaryPanel from '@/components/results/SummaryPanel'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { useAuthStore } from '@/store/authStore'

interface JobResults {
  job_id: string
  status: string
  completed_at?: string
  diff?: {
    diff_result_id: string
    changes_detected: boolean
    change_count: number
  }
  summary?: {
    summary_id: string
    summary_text: string
  }
}

export default function ResultsPage() {
  const params = useSearchParams()
  const router = useRouter()
  const { user, isAuthenticated } = useAuthStore()
  const [jobId, setJobId] = useState('')
  const [results, setResults] = useState<JobResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const queryJobId = params.get('jobId')
    if (queryJobId) {
      setJobId(queryJobId)
      fetchResults(queryJobId)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  if (!isAuthenticated || !user) {
    return null
  }

  const fetchResults = async (id: string) => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const response: any = await apiClient.getJobResults(id)
      if (response.status !== 'completed') {
        setError('Job is not completed yet. Please try again later.')
      }
      setResults(response)
    } catch (err: any) {
      setError(err.message || 'Failed to load job results')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (jobId) {
      fetchResults(jobId)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container-custom py-8 space-y-6">
        <Card>
          <form className="flex flex-col md:flex-row md:items-end gap-4" onSubmit={handleSubmit}>
            <div className="flex-1">
              <label className="text-sm font-medium text-gray-700">Job ID</label>
              <input
                type="text"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
                placeholder="Enter a job ID"
              />
            </div>
            <Button type="submit" disabled={!jobId || loading}>
              {loading ? 'Loading...' : 'Load Results'}
            </Button>
            <Button type="button" variant="secondary" onClick={() => router.push('/')}>Back to Upload</Button>
          </form>
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </Card>

        {loading && (
          <Card>
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          </Card>
        )}

        {results && results.status === 'completed' && (
          <div className="space-y-6">
            <Card>
              <h2 className="text-xl font-semibold mb-2">Job Overview</h2>
              <p className="text-sm text-gray-600">Job ID: {results.job_id}</p>
              <p className="text-sm text-gray-600">Status: {results.status}</p>
              {results.completed_at && (
                <p className="text-sm text-gray-600">Completed: {new Date(results.completed_at).toLocaleString()}</p>
              )}
              {results.diff && (
                <p className="text-sm text-gray-600">
                  Changes Detected: {results.diff.change_count} ({results.diff.changes_detected ? 'Yes' : 'No'})
                </p>
              )}
            </Card>

            {results.diff?.diff_result_id && (
              <OverlayEditor diffResultId={results.diff.diff_result_id} userId={user.user_id} />
            )}

            {results.diff?.diff_result_id && (
              <SummaryPanel diffResultId={results.diff.diff_result_id} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
