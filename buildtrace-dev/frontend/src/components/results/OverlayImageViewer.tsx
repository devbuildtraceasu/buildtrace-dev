'use client'

import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { apiClient } from '@/lib/api'
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Download, Move, Hand, MousePointer } from 'lucide-react'
import { ViewMode } from './types'

type InteractionMode = 'pan' | 'pointer'

interface OverlayImageViewerProps {
  diffResultId: string
  viewMode?: ViewMode
  className?: string
  diffMetadata?: any // Optional metadata with baseline_image_ref and revised_image_ref
}

export default function OverlayImageViewer({ 
  diffResultId, 
  viewMode = 'overlay',
  className,
  diffMetadata
}: OverlayImageViewerProps) {
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null)
  const [baselineUrl, setBaselineUrl] = useState<string | null>(null)
  const [revisedUrl, setRevisedUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(10) // Start at 10% for large drawings
  const [drawingName, setDrawingName] = useState<string | null>(null)
  const [pageNumber, setPageNumber] = useState<number | null>(null)
  
  // Pan state for synchronized dragging
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  
  // Interaction mode: pan (hand) or pointer
  const [interactionMode, setInteractionMode] = useState<InteractionMode>('pan')
  
  const containerRef = useRef<HTMLDivElement>(null)
  const imageContainerRef = useRef<HTMLDivElement>(null)
  const sideBySide = viewMode === 'side-by-side' && baselineUrl && revisedUrl

  useEffect(() => {
    const loadImages = async () => {
      setLoading(true)
      setError(null)
      
      let hasBaseline = false
      let hasRevised = false
      let hasOverlay = false
      
      try {
        // Load all images (baseline/revised/overlay) - this endpoint reads from diff_metadata
        // and works even if overlay isn't ready yet (during OCR)
        try {
          const allImagesResponse = await apiClient.getAllImageUrls(diffResultId)
          if (allImagesResponse.baseline_image_url) {
            setBaselineUrl(allImagesResponse.baseline_image_url)
            hasBaseline = true
          }
          if (allImagesResponse.revised_image_url) {
            setRevisedUrl(allImagesResponse.revised_image_url)
            hasRevised = true
          }
          if (allImagesResponse.overlay_image_url) {
            setOverlayUrl(allImagesResponse.overlay_image_url)
            hasOverlay = true
          }
          if (allImagesResponse.drawing_name) {
            setDrawingName(allImagesResponse.drawing_name)
          }
          if (allImagesResponse.page_number) {
            setPageNumber(allImagesResponse.page_number)
          }
        } catch (e) {
          console.debug('Could not load images from getAllImageUrls:', e)
        }
        
        // Also try overlay-specific endpoint (for drawing name/page number)
        try {
          const overlayResponse = await apiClient.getOverlayImageUrl(diffResultId)
          if (overlayResponse.overlay_image_url && !hasOverlay) {
            setOverlayUrl(overlayResponse.overlay_image_url)
            hasOverlay = true
          }
          if (overlayResponse.drawing_name && !drawingName) {
            setDrawingName(overlayResponse.drawing_name)
          }
          if (overlayResponse.page_number && !pageNumber) {
            setPageNumber(overlayResponse.page_number)
          }
        } catch (e) {
          // Overlay might not be ready yet - that's okay, we can still show baseline/revised
          console.debug('Overlay not available yet (this is normal during OCR):', e)
        }
        
        // Only show error if we have no images at all
        if (!hasBaseline && !hasRevised && !hasOverlay) {
          // Only show error if metadata suggests images should be available
          if (diffMetadata && (diffMetadata.baseline_image_ref || diffMetadata.revised_image_ref)) {
            // Images should be available but failed to load
            setError('Images are still loading...')
          } else {
            setError('No images available yet')
          }
        }
      } catch (err: any) {
        console.error('Error loading images:', err)
        // Only show error if we have no images at all
        if (!hasBaseline && !hasRevised && !hasOverlay) {
          setError(err.message || 'Failed to load images')
        }
      } finally {
        setLoading(false)
      }
    }

    if (diffResultId) {
      loadImages()
    }
  }, [diffResultId, diffMetadata])

  // Reset pan position when view mode changes
  useEffect(() => {
    setPanPosition({ x: 0, y: 0 })
  }, [viewMode])

  // Determine which image to display based on view mode
  const imageUrl = useMemo(() => {
    switch (viewMode) {
      case 'baseline':
        return baselineUrl
      case 'revised':
        return revisedUrl
      default:
        return overlayUrl
    }
  }, [viewMode, overlayUrl, baselineUrl, revisedUrl])

  // Zoom centered on viewport center (since transform origin is center)
  const handleWheelZoom = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    
    // Calculate new zoom (centered zoom with center transform origin)
    const zoomDelta = e.deltaY > 0 ? -5 : 5
    const newZoom = Math.max(5, Math.min(300, zoom + zoomDelta))
    
    // With center transform origin, we just update zoom
    // Pan position adjusts how the centered content moves
    setZoom(newZoom)
  }, [zoom])

  const handleZoomIn = useCallback(() => {
    const increment = zoom < 20 ? 5 : zoom < 50 ? 10 : 25
    setZoom(prev => Math.min(prev + increment, 300))
  }, [zoom])

  const handleZoomOut = useCallback(() => {
    const decrement = zoom <= 20 ? 5 : zoom <= 50 ? 10 : 25
    setZoom(prev => Math.max(prev - decrement, 5))
  }, [zoom])

  const handleResetZoom = () => {
    setZoom(10)
    setPanPosition({ x: 0, y: 0 })
  }

  const handleFitToScreen = () => {
    setZoom(10)
    setPanPosition({ x: 0, y: 0 })
  }

  const handleDownload = () => {
    const url = sideBySide ? overlayUrl : imageUrl
    if (!url) return
    const link = document.createElement('a')
    link.href = url
    link.download = `overlay_${drawingName || pageNumber || diffResultId}.png`
    link.target = '_blank'
    link.click()
  }

  // Mouse drag handlers for panning (only in pan mode)
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return // Only left click
    if (interactionMode !== 'pan') return // Only drag in pan mode
    setIsDragging(true)
    setDragStart({ x: e.clientX - panPosition.x, y: e.clientY - panPosition.y })
    e.preventDefault()
  }, [panPosition, interactionMode])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || interactionMode !== 'pan') return
    setPanPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    })
  }, [isDragging, dragStart, interactionMode])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleMouseLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  if (loading) {
    return (
      <Card className={className}>
        <div className="flex flex-col items-center justify-center py-16">
          <LoadingSpinner size="lg" />
          <p className="text-gray-500 mt-4">Loading overlay image...</p>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className={className}>
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
            <span className="text-red-600 text-2xl">!</span>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Unable to load overlay</h3>
          <p className="text-gray-500">{error}</p>
        </div>
      </Card>
    )
  }

  return (
    <Card className={className}>
      {/* Header with title and controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-4 border-b border-gray-200">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {sideBySide ? 'Side by Side Comparison' : 'Drawing Comparison Overlay'}
          </h2>
          {(drawingName || pageNumber) && (
            <p className="text-sm text-gray-500 mt-1">
              {drawingName || `Page ${pageNumber}`}
            </p>
          )}
        </div>
        
        {/* Zoom and View Controls */}
        <div className="flex items-center space-x-2">
          {/* Interaction Mode Toggle */}
          <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-2">
            <Button 
              variant={interactionMode === 'pan' ? 'primary' : 'ghost'} 
              size="sm" 
              onClick={() => setInteractionMode('pan')}
              title="Pan Tool (drag to move)"
              className={`px-2 py-1 ${interactionMode === 'pan' ? 'bg-blue-600 text-white' : ''}`}
            >
              <Hand className="w-4 h-4" />
            </Button>
            <Button 
              variant={interactionMode === 'pointer' ? 'primary' : 'ghost'} 
              size="sm" 
              onClick={() => setInteractionMode('pointer')}
              title="Pointer Tool"
              className={`px-2 py-1 ${interactionMode === 'pointer' ? 'bg-blue-600 text-white' : ''}`}
            >
              <MousePointer className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="w-px h-6 bg-gray-300 mx-2" />
          
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleZoomOut}
            disabled={zoom <= 5}
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </Button>
          
          <span className="text-sm font-medium text-gray-600 min-w-[50px] text-center">
            {zoom}%
          </span>
          
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleZoomIn}
            disabled={zoom >= 300}
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          
          <div className="w-px h-6 bg-gray-300 mx-2" />
          
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleResetZoom}
            title="Reset Zoom & Pan"
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
          
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleFitToScreen}
            title="Fit to Screen"
          >
            <Maximize2 className="w-4 h-4" />
          </Button>
          
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleDownload}
            title="Download"
          >
            <Download className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center space-x-4 mb-4 pb-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-green-500 rounded" />
          <span className="text-sm text-gray-600">Additions</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-red-500 rounded" />
          <span className="text-sm text-gray-600">Removals</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-yellow-500 rounded" />
          <span className="text-sm text-gray-600">Modifications</span>
        </div>
        <div className="flex items-center space-x-2 ml-auto text-gray-500">
          {interactionMode === 'pan' ? (
            <>
              <Hand className="w-4 h-4" />
              <span className="text-sm">Pan mode: drag to move, scroll to zoom at cursor</span>
            </>
          ) : (
            <>
              <MousePointer className="w-4 h-4" />
              <span className="text-sm">Pointer mode: scroll to zoom at cursor</span>
            </>
          )}
        </div>
      </div>

      {/* Image Viewer Container */}
      <div 
        ref={containerRef}
        className="relative overflow-hidden bg-gray-100 rounded-lg border border-gray-200"
        style={{ height: '600px' }}
      >
        {sideBySide ? (
          /* Side-by-Side View with Synchronized Panning */
          <div 
            ref={imageContainerRef}
            className="flex h-full select-none"
            style={{ cursor: interactionMode === 'pan' ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            onWheel={handleWheelZoom}
          >
            {/* Baseline Image */}
            <div className="flex-1 overflow-hidden border-r border-gray-300 relative">
              <div className="absolute top-2 left-2 z-10 bg-blue-600 text-white text-xs font-semibold px-2 py-1 rounded">
                BASELINE (OLD)
              </div>
              <div
                className="h-full w-full flex items-center justify-center"
                style={{
                  transform: `translate(${panPosition.x}px, ${panPosition.y}px) scale(${zoom / 100})`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.1s ease-out'
                }}
              >
                <img
                  src={baselineUrl!}
                  alt="Baseline drawing"
                  className="max-w-none pointer-events-none"
                  style={{ imageRendering: zoom > 100 ? 'pixelated' : 'auto' }}
                  draggable={false}
                  onError={() => setError('Failed to load baseline image')}
                />
              </div>
            </div>
            
            {/* Revised Image */}
            <div className="flex-1 overflow-hidden relative">
              <div className="absolute top-2 left-2 z-10 bg-green-600 text-white text-xs font-semibold px-2 py-1 rounded">
                REVISED (NEW)
              </div>
              <div
                className="h-full w-full flex items-center justify-center"
                style={{
                  transform: `translate(${panPosition.x}px, ${panPosition.y}px) scale(${zoom / 100})`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.1s ease-out'
                }}
              >
                <img
                  src={revisedUrl!}
                  alt="Revised drawing"
                  className="max-w-none pointer-events-none"
                  style={{ imageRendering: zoom > 100 ? 'pixelated' : 'auto' }}
                  draggable={false}
                  onError={() => setError('Failed to load revised image')}
                />
              </div>
            </div>
          </div>
        ) : imageUrl ? (
          /* Single Image View (Overlay, Baseline Only, or Revised Only) */
          <div 
            ref={imageContainerRef}
            className="h-full w-full overflow-hidden select-none"
            style={{ cursor: interactionMode === 'pan' ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            onWheel={handleWheelZoom}
          >
            <div
              className="h-full w-full flex items-center justify-center"
              style={{
                transform: `translate(${panPosition.x}px, ${panPosition.y}px) scale(${zoom / 100})`,
                transformOrigin: 'center center',
                transition: isDragging ? 'none' : 'transform 0.1s ease-out'
              }}
            >
              <img
                src={imageUrl}
                alt={`${viewMode} view for ${drawingName || `Page ${pageNumber}`}`}
                className="max-w-none pointer-events-none"
                style={{ imageRendering: zoom > 100 ? 'pixelated' : 'auto' }}
                draggable={false}
                onError={() => setError('Failed to load image')}
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500 text-sm">
            No image available for this view mode.
          </div>
        )}
      </div>

      {/* Footer info */}
      <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-500">
        <p>
          {sideBySide 
            ? 'Drag to pan both images together. Use zoom controls to examine details.'
            : 'Drag to pan. Use zoom controls to examine details. Colors indicate changes between versions.'
          }
        </p>
      </div>
    </Card>
  )
}
