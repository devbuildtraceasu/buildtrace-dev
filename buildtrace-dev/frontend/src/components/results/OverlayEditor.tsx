'use client'

import React, { useEffect, useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { apiClient } from '@/lib/api'
import { OverlayRecord } from '@/types'
import TextArea from '@/components/ui/TextArea'

interface OverlayEditorProps {
  diffResultId: string
  userId: string
}

interface OverlayState {
  overlays: OverlayRecord[]
  activeOverlay?: OverlayRecord | null
  machineOverlay?: any
  activeOverlayData?: any
}

export default function OverlayEditor({ diffResultId, userId }: OverlayEditorProps) {
  const [state, setState] = useState<OverlayState | null>(null)
  const [overlayJson, setOverlayJson] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const loadOverlay = async () => {
    setMessage(null)
    const response: any = await apiClient.getOverlay(diffResultId)
    const active = response?.active_overlay || null
    setState({
      overlays: response?.overlays || [],
      activeOverlay: active,
      machineOverlay: response?.machine_overlay,
      activeOverlayData: response?.active_overlay_data,
    })
    if (response?.active_overlay_data) {
      setOverlayJson(JSON.stringify(response.active_overlay_data, null, 2))
    } else {
      setOverlayJson('{}')
    }
  }

  useEffect(() => {
    loadOverlay().catch(() => {
      setMessage('Failed to load overlay data')
    })
  }, [diffResultId])

  const handleSave = async (autoRegenerate: boolean) => {
    try {
      setIsSaving(true)
      const parsed = JSON.parse(overlayJson || '{}')
      await apiClient.createManualOverlay(diffResultId, {
        overlay_data: parsed,
        user_id: userId,
        auto_regenerate: autoRegenerate,
      })
      setMessage(autoRegenerate ? 'Overlay saved & summary regeneration queued' : 'Overlay saved')
      await loadOverlay()
    } catch (error: any) {
      setMessage(error.message || 'Failed to save overlay')
    } finally {
      setIsSaving(false)
    }
  }

  if (!state) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner />
        </div>
      </Card>
    )
  }

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold mb-2">Overlay Editor</h2>
        <p className="text-sm text-gray-500">Active overlay is shown below. You can edit the JSON and save a new manual overlay.</p>
      </div>

      {message && (
        <div className="text-sm text-blue-600">{message}</div>
      )}

      <TextArea
        value={overlayJson}
        onChange={(e) => setOverlayJson(e.target.value)}
        rows={12}
      />

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => handleSave(false)} disabled={isSaving}>
          Save Overlay
        </Button>
        <Button onClick={() => handleSave(true)} disabled={isSaving}>
          Save & Regenerate Summary
        </Button>
        <Button variant="secondary" onClick={loadOverlay} disabled={isSaving}>
          Refresh
        </Button>
      </div>

      <div className="text-sm text-gray-500">
        <p>Machine overlay reference: {state.machineOverlay ? 'available' : 'n/a'}</p>
        <p>Manual overlays: {state.overlays.length}</p>
      </div>
    </Card>
  )
}
