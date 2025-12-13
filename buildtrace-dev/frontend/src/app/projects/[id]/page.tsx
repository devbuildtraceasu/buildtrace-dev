'use client'

import React, { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Header from '@/components/layout/Header'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import { Project, Document, Drawing, Comparison } from '@/types'
import { 
  ArrowLeft, Upload, GitCompare, FileText, Image, 
  ChevronRight, CheckCircle, Clock, AlertCircle, Download, Eye, X
} from 'lucide-react'

type TabType = 'documents' | 'drawings' | 'comparisons'

export default function ProjectDetailPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = params?.id as string
  
  const { user, isAuthenticated } = useAuthStore()
  const [project, setProject] = useState<Project | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [drawings, setDrawings] = useState<Drawing[]>([])
  const [comparisons, setComparisons] = useState<Comparison[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabType>('documents')
  const [uploading, setUploading] = useState(false)
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null)
  const [documentUrl, setDocumentUrl] = useState<string | null>(null)
  const [loadingDocUrl, setLoadingDocUrl] = useState(false)
  const [viewingDrawing, setViewingDrawing] = useState<Drawing | null>(null)
  const [drawingUrl, setDrawingUrl] = useState<string | null>(null)
  const [loadingDrawingUrl, setLoadingDrawingUrl] = useState(false)

  useEffect(() => {
    const fetchProjectData = async () => {
      if (!projectId) return
      
      try {
        setLoading(true)
        const [projectData, docsData, drawingsData, comparisonsData] = await Promise.all([
          apiClient.getProject(projectId),
          apiClient.getProjectDocuments(projectId),
          apiClient.getProjectDrawings(projectId),
          apiClient.getProjectComparisons(projectId)
        ])
        
        setProject(projectData as Project)
        setDocuments(docsData as Document[])
        setDrawings(drawingsData as Drawing[])
        setComparisons(comparisonsData as Comparison[])
      } catch (error) {
        console.error('Error fetching project data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchProjectData()
  }, [projectId])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !projectId) return
    
    setUploading(true)
    try {
      const newDoc = await apiClient.uploadDocument(projectId, file)
      setDocuments([...documents, newDoc as Document])
      
      // Refresh data after upload
      setTimeout(async () => {
        const [docsData, drawingsData] = await Promise.all([
          apiClient.getProjectDocuments(projectId),
          apiClient.getProjectDrawings(projectId)
        ])
        setDocuments(docsData as Document[])
        setDrawings(drawingsData as Drawing[])
      }, 2500)
    } catch (error) {
      console.error('Error uploading document:', error)
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'processing':
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />
      case 'error':
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return null
    }
  }

  const tabs: { id: TabType; label: string; count: number }[] = [
    { id: 'documents', label: 'Documents', count: documents.length },
    { id: 'drawings', label: 'Drawings', count: drawings.length },
    { id: 'comparisons', label: 'Comparisons', count: comparisons.length }
  ]

  const handleViewDocument = async (doc: Document) => {
    setViewingDocument(doc)
    setLoadingDocUrl(true)
    try {
      // Fetch signed URL from backend
      const response = await apiClient.getDocumentUrl(doc.document_id)
      setDocumentUrl(response?.url || null)
    } catch (error) {
      console.error('Error fetching document URL:', error)
      setDocumentUrl(null)
    } finally {
      setLoadingDocUrl(false)
    }
  }

  const handleDownloadDocument = async (doc: Document) => {
    try {
      const response = await apiClient.getDocumentUrl(doc.document_id)
      if (response?.url) {
        // Open download in new tab
        const link = document.createElement('a')
        link.href = response.url
        link.download = doc.name
        link.target = '_blank'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
    } catch (error) {
      console.error('Error downloading document:', error)
    }
  }

  const closeViewer = () => {
    setViewingDocument(null)
    setDocumentUrl(null)
  }

  const handleViewDrawing = async (drawing: Drawing) => {
    setViewingDrawing(drawing)
    setLoadingDrawingUrl(true)
    try {
      const response = await apiClient.getDrawingUrl(drawing.drawing_id)
      setDrawingUrl(response?.url || null)
    } catch (error) {
      console.error('Error fetching drawing URL:', error)
      setDrawingUrl(null)
    } finally {
      setLoadingDrawingUrl(false)
    }
  }

  const handleDownloadDrawing = async (drawing: Drawing) => {
    try {
      const response = await apiClient.getDrawingUrl(drawing.drawing_id)
      if (response?.url) {
        const link = document.createElement('a')
        link.href = response.url
        link.download = `${drawing.name}.png`
        link.target = '_blank'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
    } catch (error) {
      console.error('Error downloading drawing:', error)
    }
  }

  const closeDrawingViewer = () => {
    setViewingDrawing(null)
    setDrawingUrl(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center space-x-4 mb-8">
            <button className="flex items-center text-gray-600 hover:text-gray-900">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Projects
            </button>
            <div className="h-8 bg-gray-200 rounded w-48 animate-pulse"></div>
          </div>
          
          <div className="flex space-x-4 mb-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-gray-200 rounded w-32 animate-pulse"></div>
            ))}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white rounded-xl p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-3"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Card className="text-center py-12">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Project not found</h3>
            <Button variant="primary" onClick={() => router.push('/projects')}>
              Back to Projects
            </Button>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => router.push('/projects')}
              className="flex items-center text-gray-600 hover:text-gray-900 bg-white px-3 py-2 rounded-lg border border-gray-200"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Projects
            </button>
            <h1 className="text-xl font-bold text-gray-900">{project.name}</h1>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button
              variant="secondary"
              onClick={() => router.push('/')}
              className="flex items-center space-x-2"
            >
              <GitCompare className="w-4 h-4" />
              <span>Compare Documents</span>
            </Button>
            
            <label className="cursor-pointer">
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileUpload}
                disabled={uploading}
              />
              <div className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                <Upload className="w-4 h-4" />
                <span>{uploading ? 'Uploading...' : 'Upload Document'}</span>
              </div>
            </label>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'documents' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">All Documents</h2>
            {documents.length === 0 ? (
              <Card className="text-center py-8">
                <FileText className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">No documents uploaded yet</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {documents.map((doc) => (
                  <div
                    key={doc.document_id}
                    className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between hover:border-blue-300 transition-colors group"
                  >
                    <div 
                      className="flex items-center space-x-4 flex-1 cursor-pointer"
                      onClick={() => handleViewDocument(doc)}
                    >
                      <div className="w-12 h-12 bg-red-50 rounded-lg flex items-center justify-center">
                        <FileText className="w-6 h-6 text-red-500" />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900 group-hover:text-blue-600">{doc.name}</h3>
                        <div className="flex items-center space-x-3 text-sm text-gray-500">
                          <span>{doc.page_count} pages</span>
                          <span>•</span>
                          <span>{formatFileSize(doc.file_size)}</span>
                          <span>•</span>
                          <span className="capitalize">{doc.version}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(doc.status)}
                      <span className={`text-sm capitalize ${
                        doc.status === 'ready' ? 'text-green-600' :
                        doc.status === 'processing' ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {doc.status}
                      </span>
                      {/* Action Buttons */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleViewDocument(doc)
                        }}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="View Document"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDownloadDocument(doc)
                        }}
                        className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Download Document"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'drawings' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">All Drawings</h2>
            {drawings.length === 0 ? (
              <Card className="text-center py-8">
                <Image className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">No drawings extracted yet</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {drawings.map((drawing) => (
                  <div
                    key={drawing.drawing_id}
                    className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between hover:border-blue-300 transition-colors group"
                  >
                    <div 
                      className="flex items-center space-x-4 flex-1 cursor-pointer"
                      onClick={() => handleViewDrawing(drawing)}
                    >
                      <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center">
                        <Image className="w-6 h-6 text-blue-500" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="font-medium text-gray-900 group-hover:text-blue-600">{drawing.name}</h3>
                          {drawing.auto_detected && (
                            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                              Auto-detected
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">
                          From {drawing.source_document} • Version: {drawing.version}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleViewDrawing(drawing)
                        }}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="View Drawing"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDownloadDrawing(drawing)
                        }}
                        className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Download Drawing"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'comparisons' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">All Comparisons</h2>
              <Button 
                variant="primary" 
                size="sm"
                onClick={() => router.push('/')}
                className="flex items-center space-x-2"
              >
                <GitCompare className="w-4 h-4" />
                <span>New Comparison</span>
              </Button>
            </div>
            {comparisons.length === 0 ? (
              <Card className="text-center py-8">
                <GitCompare className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500 mb-4">No comparisons created yet</p>
                <Button variant="primary" onClick={() => router.push('/')}>
                  Start a Comparison
                </Button>
              </Card>
            ) : (
              <div className="space-y-4">
                {comparisons.map((comparison) => (
                  <div
                    key={comparison.comparison_id}
                    className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-blue-300 transition-all"
                  >
                    {/* Header row */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          comparison.status === 'completed' ? 'bg-green-100' :
                          comparison.status === 'processing' || comparison.status === 'in_progress' ? 'bg-yellow-100' :
                          comparison.status === 'failed' ? 'bg-red-100' : 'bg-purple-100'
                        }`}>
                          <GitCompare className={`w-6 h-6 ${
                            comparison.status === 'completed' ? 'text-green-600' :
                            comparison.status === 'processing' || comparison.status === 'in_progress' ? 'text-yellow-600' :
                            comparison.status === 'failed' ? 'text-red-600' : 'text-purple-600'
                          }`} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">
                            {comparison.baseline_drawing_name || 'Baseline'} vs {comparison.revised_drawing_name || 'Revised'}
                          </h3>
                          <span className="text-xs font-mono text-gray-400">
                            BT-{comparison.job_id?.substring(0, 8).toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(comparison.status)}
                        <span className={`text-sm font-medium capitalize ${
                          comparison.status === 'completed' ? 'text-green-600' :
                          comparison.status === 'processing' || comparison.status === 'in_progress' ? 'text-yellow-600' :
                          comparison.status === 'failed' ? 'text-red-600' :
                          'text-gray-600'
                        }`}>
                          {comparison.status === 'in_progress' ? 'Processing' : comparison.status}
                        </span>
                      </div>
                    </div>
                    
                    {/* Stats row */}
                    <div className="flex items-center space-x-6 text-sm text-gray-500 mb-4">
                      <div className="flex items-center space-x-1">
                        <span className="font-medium text-gray-700">{comparison.change_count || 0}</span>
                        <span>changes detected</span>
                      </div>
                      {comparison.created_at && (
                        <div className="flex items-center space-x-1">
                          <Clock className="w-4 h-4" />
                          <span>{new Date(comparison.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                        </div>
                      )}
                    </div>
                    
                    {/* Action row */}
                    <div className="flex items-center justify-end pt-3 border-t border-gray-100">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => router.push(`/results?jobId=${comparison.job_id}`)}
                        className="flex items-center space-x-2"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Results</span>
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Document Viewer Modal */}
      {viewingDocument && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <FileText className="w-6 h-6 text-red-500" />
                <div>
                  <h3 className="font-semibold text-gray-900">{viewingDocument.name}</h3>
                  <p className="text-sm text-gray-500">
                    {viewingDocument.page_count} pages • {formatFileSize(viewingDocument.file_size)}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleDownloadDocument(viewingDocument)}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </button>
                <button
                  onClick={closeViewer}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-4 bg-gray-100">
              {loadingDocUrl ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-500">Loading document...</p>
                  </div>
                </div>
              ) : documentUrl ? (
                <iframe
                  src={documentUrl}
                  className="w-full h-[70vh] rounded-lg border border-gray-200"
                  title={viewingDocument.name}
                />
              ) : (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <p className="text-gray-600 mb-2">Unable to load document preview</p>
                    <p className="text-sm text-gray-500 mb-4">The document may still be processing or unavailable</p>
                    <button
                      onClick={() => handleDownloadDocument(viewingDocument)}
                      className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors mx-auto"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download Instead</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Drawing Viewer Modal */}
      {viewingDrawing && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <Image className="w-6 h-6 text-blue-500" />
                <div>
                  <h3 className="font-semibold text-gray-900">{viewingDrawing.name}</h3>
                  <p className="text-sm text-gray-500">
                    From {viewingDrawing.source_document} • Version: {viewingDrawing.version}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleDownloadDrawing(viewingDrawing)}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </button>
                <button
                  onClick={closeDrawingViewer}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-4 bg-gray-100 flex items-center justify-center">
              {loadingDrawingUrl ? (
                <div className="text-center">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                  <p className="text-gray-500">Loading drawing...</p>
                </div>
              ) : drawingUrl ? (
                <img
                  src={drawingUrl}
                  alt={viewingDrawing.name}
                  className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-lg"
                />
              ) : (
                <div className="text-center">
                  <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-2">Unable to load drawing preview</p>
                  <p className="text-sm text-gray-500 mb-4">The drawing may still be processing or unavailable</p>
                  <button
                    onClick={() => handleDownloadDrawing(viewingDrawing)}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors mx-auto"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Instead</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
