'use client'

import React, { useEffect, useState, useCallback } from 'react'
import Card from '@/components/ui/Card'
import TextArea from '@/components/ui/TextArea'
import Button from '@/components/ui/Button'
import { apiClient } from '@/lib/api'
import { SummaryRecord } from '@/types'
import { Sparkles, RefreshCw, Edit3, Clock, CheckCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface SummaryPanelProps {
  diffResultId: string
  isProcessing?: boolean
}

export default function SummaryPanel({ diffResultId, isProcessing = false }: SummaryPanelProps) {
  const [summaries, setSummaries] = useState<SummaryRecord[]>([])
  const [activeSummary, setActiveSummary] = useState<SummaryRecord | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedSummaryId, setSelectedSummaryId] = useState<string | null>(null)
  const [summaryHeadline, setSummaryHeadline] = useState('')
  const [summaryDetails, setSummaryDetails] = useState('')

  const loadSummaries = useCallback(async (silent: boolean = false) => {
    setMessage(null)
    if (!silent) {
      setIsLoading(true)
    }
    try {
      const response: any = await apiClient.getSummaries(diffResultId)
      const active = response?.active_summary || null
      const allSummaries: SummaryRecord[] = response?.summaries || []

      setSummaries(allSummaries)
      // Prefer the active summary from backend, otherwise fall back to first
      const initial = active || allSummaries[0] || null
      setActiveSummary(initial)
      setSelectedSummaryId(initial?.summary_id || null)

      // Heuristic split: first paragraph as headline, rest as details
      const fullText = initial?.summary_text || ''
      const [first, ...rest] = fullText.split('\n\n')
      setSummaryHeadline(first || '')
      setSummaryDetails(rest.join('\n\n') || '')
    } catch (error) {
      if (!silent) {
        setMessage('Failed to load summaries')
      }
    } finally {
      if (!silent) {
        setIsLoading(false)
      }
    }
  }, [diffResultId])

  useEffect(() => {
    loadSummaries()
  }, [loadSummaries])

  // Poll for summary when processing (silent updates to avoid flicker)
  useEffect(() => {
    if (isProcessing && !activeSummary) {
      const interval = setInterval(() => {
        loadSummaries(true) // Silent refresh - no loading spinner
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [isProcessing, activeSummary, loadSummaries])

  const handleSave = async () => {
    if (!activeSummary) return
    try {
      const combined = [summaryHeadline.trim(), summaryDetails.trim()]
        .filter(Boolean)
        .join('\n\n')

      await apiClient.updateSummary(activeSummary.summary_id, combined)
      setMessage('Summary updated')
      setIsEditing(false)
      await loadSummaries()
    } catch (error: any) {
      setMessage(error.message || 'Failed to update summary')
    }
  }

  const handleRegenerate = async (overlayId?: string) => {
    try {
      setIsRegenerating(true)
      await apiClient.regenerateSummary(diffResultId, overlayId)
      setMessage('AI summary regeneration started...')
      // Start polling for the new summary
      setTimeout(() => loadSummaries(), 3000)
    } catch (error: any) {
      setMessage(error.message || 'Failed to queue summary regeneration')
    } finally {
      setIsRegenerating(false)
    }
  }

  // Helper: determine if a summary record is AI-generated
  const isAiSource = (summary?: SummaryRecord | null) => {
    if (!summary) return false
    const src = (summary.source || '').toLowerCase()
    const model = (summary.ai_model_used || '').toLowerCase()
    // Check for various AI sources - exclude failed and pending states
    const isFailedOrPending = src.includes('failed') || src === 'pending'
    return (
      !isFailedOrPending && (
        src === 'ai' ||
        src === 'gpt-4-vision' ||
        src === 'gemini' ||
        model.includes('gpt') ||
        model.includes('gemini')
      )
    )
  }

  // Check if currently selected summary is from AI (for icon/styling)
  const isAiSummary = isAiSource(activeSummary)

  // Derive AI variants (AI-1, AI-2, ...) from available summaries
  const aiSummaries = summaries.filter(s => isAiSource(s))

  const getSummaryLabel = (summary: SummaryRecord, index: number) => {
    const model = summary.ai_model_used || ''
    const lowerModel = model.toLowerCase()
    // Prefer explicit model hints when available
    if (lowerModel.includes('gemini')) {
      return `AI-1 (Gemini)`
    }
    if (lowerModel.includes('gpt')) {
      return `AI-2 (GPT)`
    }
    // Fallback to index-based label
    return `AI-${index + 1}`
  }

  // Loading/Processing state - waiting for AI summary
  if (isLoading || (isProcessing && !activeSummary)) {
    return (
      <Card className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <h2 className="text-xl font-semibold">AI Summary</h2>
            <p className="text-sm text-gray-500">Powered by GPT-4 Vision</p>
          </div>
        </div>

        <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6 border border-purple-100">
          <div className="flex items-center justify-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-purple-500 border-t-transparent" />
            <div>
              <p className="font-medium text-purple-800">Generating AI Summary...</p>
              <p className="text-sm text-purple-600">Analyzing drawing changes with computer vision</p>
            </div>
          </div>
        </div>
      </Card>
    )
  }

  // No summary available yet
  if (!activeSummary && !isProcessing) {
    return (
      <Card className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
            <Clock className="w-5 h-5 text-gray-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold">AI Summary</h2>
            <p className="text-sm text-gray-500">No summary available</p>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-6 border border-gray-200 text-center">
          <p className="text-gray-600 mb-4">Summary will be generated automatically by AI</p>
          <Button 
            onClick={() => handleRegenerate()}
            disabled={isRegenerating}
            className="flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`} />
            <span>{isRegenerating ? 'Generating...' : 'Generate AI Summary'}</span>
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isAiSummary 
              ? 'bg-gradient-to-br from-purple-500 to-blue-500' 
              : 'bg-gray-100'
          }`}>
            {isAiSummary ? (
              <Sparkles className="w-5 h-5 text-white" />
            ) : (
              <Edit3 className="w-5 h-5 text-gray-500" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-semibold">AI Summary</h2>
            {/* AI engine selector / source info */}
            <div className="flex items-center space-x-2 mt-1">
              {aiSummaries.length > 1 ? (
                <>
                  {aiSummaries.map((summary, index) => {
                    const label = getSummaryLabel(summary, index)
                    const isSelected = summary.summary_id === selectedSummaryId
                    return (
                      <button
                        key={summary.summary_id}
                        type="button"
                        onClick={() => {
                          setActiveSummary(summary)
                          setSelectedSummaryId(summary.summary_id)
                          const fullText = summary.summary_text || ''
                          const [first, ...rest] = fullText.split('\n\n')
                          setSummaryHeadline(first || '')
                          setSummaryDetails(rest.join('\n\n') || '')
                        }}
                        className={[
                          'px-2 py-0.5 rounded-full text-xs border',
                          isSelected
                            ? 'bg-purple-600 text-white border-purple-600'
                            : 'bg-white text-gray-600 border-gray-300'
                        ].join(' ')}
                      >
                        {label}
                      </button>
                    )
                  })}
                </>
              ) : (
                <div className="flex items-center space-x-1">
                  {isAiSummary ? (
                    <>
                      <CheckCircle className="w-3 h-3 text-green-500" />
                      <span className="text-sm text-green-600">
                        Generated by {activeSummary?.source || activeSummary?.ai_model_used || 'AI'}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm text-gray-500">Source: {activeSummary?.source || 'Manual'}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {!isEditing && (
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => setIsEditing(true)}
              className="text-gray-500"
            >
              <Edit3 className="w-4 h-4" />
            </Button>
          )}
          <Button 
            variant="secondary" 
            size="sm"
            onClick={() => handleRegenerate(activeSummary?.overlay_id)}
            disabled={isRegenerating}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${isRegenerating ? 'animate-spin' : ''}`} />
            {isRegenerating ? 'Regenerating...' : 'Regenerate'}
          </Button>
        </div>
      </div>

      {message && (
        <p className={`text-sm ${message.includes('Failed') ? 'text-red-600' : 'text-blue-600'}`}>
          {message}
        </p>
      )}

      {/* Summary Content */}
      {isEditing ? (
        <div className="space-y-4">
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              Summary Headline
            </label>
            <TextArea
              rows={2}
              value={summaryHeadline}
              onChange={(e) => setSummaryHeadline(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              Detailed Change Notes (used as context for cost & schedule analysis)
            </label>
            <TextArea
              rows={8}
              value={summaryDetails}
              onChange={(e) => setSummaryDetails(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <div className="flex gap-3 flex-wrap">
            <Button
              onClick={handleSave}
              disabled={!summaryHeadline.trim() && !summaryDetails.trim()}
            >
              Save Summary
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                const fullText = activeSummary?.summary_text || ''
                const [first, ...rest] = fullText.split('\n\n')
                setSummaryHeadline(first || '')
                setSummaryDetails(rest.join('\n\n') || '')
              }}
            >
              Reset from AI
            </Button>
            <Button
              variant="ghost"
              onClick={() => setIsEditing(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <label className="block text-xs font-semibold text-gray-500 mb-2">
              Summary Headline
            </label>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {summaryHeadline || '_No summary headline available yet._'}
              </ReactMarkdown>
            </div>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <label className="block text-xs font-semibold text-gray-500 mb-2">
              Detailed Change Notes (used as context for cost & schedule analysis)
            </label>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {summaryDetails || '_No detailed notes yet. Tap edit to add context._'}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
