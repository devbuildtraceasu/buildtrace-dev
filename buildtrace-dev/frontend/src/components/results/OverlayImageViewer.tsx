'use client'

import React, { useEffect, useState, useRef } from 'react'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { apiClient } from '@/lib/api'
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Download } from 'lucide-react'
import { ViewMode } from './types'

interface OverlayImageViewerProps {
  diffResultId: string
  viewMode?: ViewMode
  className?: string
}

export default function OverlayImageViewer({ 
  diffResultId, 
  viewMode = 'overlay',
  className 
}: OverlayImageViewerProps) {
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null)
  const [baselineUrl, setBaselineUrl] = useState<string | null>(null)
  const [revisedUrl, setRevisedUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(100)
  const [drawingName, setDrawingName] = useState<string | null>(null)
  const [pageNumber, setPageNumber] = useState<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const loadImages = async () => {
      setLoading(true)
      setError(null)
      
      try {
        // Load overlay image
        const overlayResponse = await apiClient.getOverlayImageUrl(diffResultId)
        if (overlayResponse.overlay_image_url) {
          setOverlayUrl(overlayResponse.overlay_image_url)
          setDrawingName(overlayResponse.drawing_name || null)
          setPageNumber(overlayResponse.page_number || null)
        }
        
        // Load all images (baseline/revised)
        try {
          const allImagesResponse = await apiClient.getAllImageUrls(diffResultId)
          if (allImagesResponse.baseline_image_url) {
            setBaselineUrl(allImagesResponse.baseline_image_url)
          } else {
            setBaselineUrl(null)
          }
          if (allImagesResponse.revised_image_url) {
            setRevisedUrl(allImagesResponse.revised_image_url)
          } else {
            setRevisedUrl(null)
          }
        } catch (e) {
          // Baseline/revised URLs are optional
          console.debug('Could not load baseline/revised URLs:', e)
          setBaselineUrl(null)
          setRevisedUrl(null)
        }
        
        if (!overlayResponse.overlay_image_url) {
          setError('No overlay image available')
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load images')
      } finally {
        setLoading(false)
      }
    }

    if (diffResultId) {
      loadImages()
    }
  }, [diffResultId])

  // Determine which image to display based on view mode
  const getDisplayImageUrl = (): string | null => {
    switch (viewMode) {
      case 'overlay':
        return overlayUrl
      case 'baseline':
        return baselineUrl
      case 'revised':
        return revisedUrl
      case 'side-by-side':
        return overlayUrl // For now, show overlay. Can enhance later with side-by-side layout
      default:
        return overlayUrl
    }
  }

  const imageUrl = getDisplayImageUrl()

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 25, 300))
  }

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 25, 25))
  }

  const handleResetZoom = () => {
    setZoom(100)
  }

  const handleFitToScreen = () => {
    if (containerRef.current) {
      // Simple fit - set zoom to 100% which should fit in most cases
      setZoom(100)
    }
  }

  const handleDownload = () => {
    if (imageUrl) {
      const link = document.createElement('a')
      link.href = imageUrl
      link.download = `overlay_${drawingName || pageNumber || diffResultId}.png`
      link.target = '_blank'
      link.click()
    }
  }

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
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Drawing Comparison Overlay</h2>
          {(drawingName || pageNumber) && (
            <p className="text-sm text-gray-500 mt-1">
              {drawingName || `Page ${pageNumber}`}
            </p>
          )}
        </div>
        
        {/* Zoom and View Controls */}
        <div className="flex items-center space-x-2">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleZoomOut}
            disabled={zoom <= 25}
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
            title="Reset Zoom"
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

      {/* Legend - only show for overlay mode */}
      {viewMode === 'overlay' && (
        <div className="flex items-center space-x-6 mb-4 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-green-500 rounded" />
            <span className="text-gray-600">Additions</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-500 rounded" />
            <span className="text-gray-600">Removals</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-yellow-500 rounded" />
            <span className="text-gray-600">Modifications</span>
          </div>
        </div>
      )}

      {/* Image Container */}
      <div 
        ref={containerRef}
        className="relative overflow-auto bg-gray-100 rounded-lg border border-gray-200"
        style={{ maxHeight: '70vh', minHeight: '400px' }}
      >
        {viewMode === 'side-by-side' ? (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium mb-2">Side-by-Side View</p>
              <p className="text-sm">This view requires page-specific image URLs from PDFs.</p>
              <p className="text-sm mt-2">Currently showing overlay view instead.</p>
              {overlayUrl && (
                <div 
                  className="inline-block mt-4"
                  style={{ 
                    transform: `scale(${zoom / 100})`,
                    transformOrigin: 'top left',
                    transition: 'transform 0.2s ease-out'
                  }}
                >
                  <img
                    src={overlayUrl}
                    alt="Overlay drawing"
                    className="max-w-full border border-gray-300 rounded"
                    style={{ 
                      imageRendering: zoom > 100 ? 'pixelated' : 'auto'
                    }}
                    onError={() => setError('Failed to load overlay image')}
                  />
                </div>
              )}
            </div>
          </div>
        ) : (viewMode === 'baseline' || viewMode === 'revised') ? (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium mb-2">
                {viewMode === 'baseline' ? 'Baseline' : 'Revised'} View
              </p>
              <p className="text-sm">This view requires page-specific image extraction from PDFs.</p>
              <p className="text-sm mt-2">Currently showing overlay view instead.</p>
              {overlayUrl && (
                <div 
                  className="inline-block mt-4"
                  style={{ 
                    transform: `scale(${zoom / 100})`,
                    transformOrigin: 'top left',
                    transition: 'transform 0.2s ease-out'
                  }}
                >
                  <img
                    src={overlayUrl}
                    alt="Overlay drawing"
                    className="max-w-full border border-gray-300 rounded"
                    style={{ 
                      imageRendering: zoom > 100 ? 'pixelated' : 'auto'
                    }}
                    onError={() => setError('Failed to load overlay image')}
                  />
                </div>
              )}
            </div>
          </div>
        ) : imageUrl ? (
          <div 
            className="inline-block min-w-full"
            style={{ 
              transform: `scale(${zoom / 100})`,
              transformOrigin: 'top left',
              transition: 'transform 0.2s ease-out'
            }}
          >
            <img
              src={imageUrl}
              alt={`${viewMode} view for ${drawingName || `Page ${pageNumber}`}`}
              className="max-w-none"
              style={{ 
                display: 'block',
                imageRendering: zoom > 100 ? 'pixelated' : 'auto'
              }}
              onError={() => setError('Failed to load image')}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <p>No image available for {viewMode} view</p>
          </div>
        )}
      </div>

      {/* Footer info */}
      <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-500">
        <p>
          Use zoom controls to examine details. Colors indicate changes between versions.
        </p>
      </div>
    </Card>
  )
}
