'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { clsx } from 'clsx'
import { Eye, Trash2, Clock, FileText, Calendar } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { apiClient } from '@/lib/api'
import { ProcessingSession } from '@/types'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

const RecentSessions: React.FC = () => {
  const router = useRouter()
  const [sessions, setSessions] = useState<ProcessingSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadRecentSessions()
  }, [])

  const loadRecentSessions = async () => {
    try {
      setIsLoading(true)
      const response = await apiClient.getRecentSessions()
      if (response.success && response.data?.sessions) {
        setSessions(response.data.sessions)
      }
    } catch (error: any) {
      console.error('Failed to load recent sessions:', error)
      toast.error('Failed to load recent comparisons')
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewResults = (sessionId: string) => {
    router.push(`/results/${sessionId}`)
  }

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this comparison?')) {
      return
    }

    try {
      setDeletingIds(prev => new Set(prev).add(sessionId))
      await apiClient.deleteSession(sessionId)
      setSessions(prev => prev.filter(session => session.id !== sessionId))
      toast.success('Comparison deleted successfully')
    } catch (error: any) {
      console.error('Failed to delete session:', error)
      toast.error('Failed to delete comparison')
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(sessionId)
        return newSet
      })
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      completed: { color: 'bg-green-100 text-green-800', label: 'Completed' },
      processing: { color: 'bg-yellow-100 text-yellow-800', label: 'Processing' },
      failed: { color: 'bg-red-100 text-red-800', label: 'Failed' },
      pending: { color: 'bg-blue-100 text-blue-800', label: 'Pending' }
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending

    return (
      <span className={clsx(
        'status-badge inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
        config.color
      )}>
        {config.label}
      </span>
    )
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
        <Button
          variant="ghost"
          size="sm"
          onClick={loadRecentSessions}
          className="flex items-center space-x-2"
        >
          <Clock className="w-4 h-4" />
          <span>Refresh</span>
        </Button>
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
                    Baseline Drawing
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Revised Drawing
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
                  <tr key={session.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(session.created_at)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {session.baseline_filename || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {session.revised_filename || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(session.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                      <div className="flex items-center justify-center space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewResults(session.id)}
                          disabled={session.status !== 'completed'}
                          className="flex items-center space-x-1"
                        >
                          <Eye className="w-4 h-4" />
                          <span>View</span>
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteSession(session.id)}
                          disabled={deletingIds.has(session.id)}
                          className="flex items-center space-x-1 text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          {deletingIds.has(session.id) ? (
                            <LoadingSpinner size="sm" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
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

export default RecentSessions