'use client'

import React, { useEffect, useState } from 'react'
import Card from '@/components/ui/Card'
import TextArea from '@/components/ui/TextArea'
import Button from '@/components/ui/Button'
import { apiClient } from '@/lib/api'
import { SummaryRecord } from '@/types'

interface SummaryPanelProps {
  diffResultId: string
}

export default function SummaryPanel({ diffResultId }: SummaryPanelProps) {
  const [summaries, setSummaries] = useState<SummaryRecord[]>([])
  const [activeSummary, setActiveSummary] = useState<SummaryRecord | null>(null)
  const [editorValue, setEditorValue] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  const loadSummaries = async () => {
    setMessage(null)
    const response: any = await apiClient.getSummaries(diffResultId)
    const active = response?.active_summary || null
    setActiveSummary(active)
    setSummaries(response?.summaries || [])
    setEditorValue(active?.summary_text || '')
  }

  useEffect(() => {
    loadSummaries().catch(() => setMessage('Failed to load summaries'))
  }, [diffResultId])

  const handleSave = async () => {
    if (!activeSummary) return
    try {
      await apiClient.updateSummary(activeSummary.summary_id, editorValue)
      setMessage('Summary updated')
      await loadSummaries()
    } catch (error: any) {
      setMessage(error.message || 'Failed to update summary')
    }
  }

  const handleRegenerate = async (overlayId?: string) => {
    try {
      await apiClient.regenerateSummary(diffResultId, overlayId)
      setMessage('Summary regeneration queued')
    } catch (error: any) {
      setMessage(error.message || 'Failed to queue summary regeneration')
    }
  }

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold mb-2">Summary</h2>
        <p className="text-sm text-gray-500">Review or edit the latest summary. Use "Regenerate" to request a fresh summary from the async pipeline.</p>
      </div>

      {message && <p className="text-sm text-blue-600">{message}</p>}

      <TextArea
        rows={8}
        value={editorValue}
        onChange={(e) => setEditorValue(e.target.value)}
      />

      <div className="flex gap-3">
        <Button onClick={handleSave} disabled={!activeSummary}>Save Summary</Button>
        <Button variant="secondary" onClick={() => handleRegenerate(activeSummary?.overlay_id)}>Regenerate</Button>
        <Button variant="ghost" onClick={loadSummaries}>Refresh</Button>
      </div>

      <div className="text-sm text-gray-500">
        <p>Total summaries: {summaries.length}</p>
        {activeSummary && (
          <p>Active summary source: {activeSummary.source}</p>
        )}
      </div>
    </Card>
  )
}
