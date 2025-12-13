'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Header from '@/components/layout/Header'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import { Project } from '@/types'
import { FolderOpen, Plus, FileText, Image, GitCompare, Calendar, MapPin } from 'lucide-react'

export default function ProjectsPage() {
  const router = useRouter()
  const { user, isAuthenticated } = useAuthStore()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')
  const [newProjectLocation, setNewProjectLocation] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true)
        const data = await apiClient.getProjects(user?.user_id)
        setProjects(data as Project[])
      } catch (error) {
        console.error('Error fetching projects:', error)
      } finally {
        setLoading(false)
      }
    }
    
    if (isAuthenticated && user?.user_id) {
      fetchProjects()
    } else {
      setLoading(false)
    }
  }, [isAuthenticated, user?.user_id])

  const handleCreateProject = async () => {
    if (!newProjectName.trim() || !user?.user_id) return
    
    setCreating(true)
    try {
      const newProject = await apiClient.createProject({
        name: newProjectName,
        description: newProjectDescription,
        location: newProjectLocation,
        user_id: user.user_id
      })
      setProjects([...projects, newProject as Project])
      setShowNewProjectModal(false)
      setNewProjectName('')
      setNewProjectDescription('')
      setNewProjectLocation('')
    } catch (error) {
      console.error('Error creating project:', error)
    } finally {
      setCreating(false)
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
            <p className="text-gray-500 mt-1">Manage your construction drawing projects</p>
          </div>
        </div>

        {/* Projects Grid - Always show with "New Project" card */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-2xl p-8 animate-pulse shadow-sm">
                <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-full mb-6"></div>
                <div className="flex space-x-4">
                  <div className="h-4 bg-gray-200 rounded w-24"></div>
                  <div className="h-4 bg-gray-200 rounded w-24"></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {/* New Project Card - Always first */}
            <div
              onClick={() => setShowNewProjectModal(true)}
              className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border-2 border-dashed border-blue-300 p-8 hover:shadow-lg hover:border-blue-400 hover:from-blue-100 hover:to-indigo-100 transition-all cursor-pointer flex flex-col items-center justify-center min-h-[280px]"
            >
              <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mb-4">
                <Plus className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-blue-700 mb-2">Create New Project</h3>
              <p className="text-blue-600 text-center text-sm">
                Start a new construction drawing comparison project
              </p>
            </div>

            {/* Existing Project Cards */}
            {projects.map((project) => (
              <div
                key={project.project_id}
                onClick={() => router.push(`/projects/${project.project_id}`)}
                className="bg-white rounded-2xl border border-gray-200 p-8 hover:shadow-xl hover:border-blue-300 hover:-translate-y-1 transition-all cursor-pointer min-h-[280px] flex flex-col"
              >
                {/* Project Header */}
                <div className="flex items-start space-x-4 mb-4">
                  <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
                    <FolderOpen className="w-7 h-7 text-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-xl font-bold text-gray-900 truncate">{project.name}</h3>
                    {project.location && (
                      <div className="flex items-center text-gray-500 mt-1">
                        <MapPin className="w-4 h-4 mr-1" />
                        <span className="text-sm truncate">{project.location}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Description */}
                {project.description && (
                  <p className="text-gray-600 line-clamp-2 mb-4 flex-grow">{project.description}</p>
                )}
                
                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 py-4 border-t border-gray-100">
                  <div className="text-center">
                    <div className="flex items-center justify-center mb-1">
                      <FileText className="w-4 h-4 text-blue-500" />
                    </div>
                    <p className="text-lg font-bold text-gray-900">{project.document_count || 0}</p>
                    <p className="text-xs text-gray-500">Documents</p>
                  </div>
                  <div className="text-center border-x border-gray-100">
                    <div className="flex items-center justify-center mb-1">
                      <Image className="w-4 h-4 text-green-500" />
                    </div>
                    <p className="text-lg font-bold text-gray-900">{project.drawing_count || 0}</p>
                    <p className="text-xs text-gray-500">Drawings</p>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center mb-1">
                      <GitCompare className="w-4 h-4 text-purple-500" />
                    </div>
                    <p className="text-lg font-bold text-gray-900">{project.comparison_count || 0}</p>
                    <p className="text-xs text-gray-500">Comparisons</p>
                  </div>
                </div>
                
                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-gray-400 pt-3 border-t border-gray-50">
                  <div className="flex items-center">
                    <Calendar className="w-3 h-3 mr-1" />
                    <span>Updated {formatDate(project.updated_at)}</span>
                  </div>
                  <span className="text-blue-500 font-medium">View →</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 w-full max-w-lg mx-4 shadow-2xl">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                <FolderOpen className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Create New Project</h2>
                <p className="text-sm text-gray-500">Set up a new drawing comparison project</p>
              </div>
            </div>
            
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Project Name *
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g., Downtown Office Tower"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  <div className="flex items-center">
                    <MapPin className="w-4 h-4 mr-1 text-gray-500" />
                    Location
                  </div>
                </label>
                <input
                  type="text"
                  value={newProjectLocation}
                  onChange={(e) => setNewProjectLocation(e.target.value)}
                  placeholder="e.g., San Francisco, CA"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  placeholder="Brief description of the project..."
                  rows={3}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all resize-none"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-8 pt-6 border-t border-gray-100">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowNewProjectModal(false)
                  setNewProjectName('')
                  setNewProjectDescription('')
                  setNewProjectLocation('')
                }}
                className="px-6"
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || creating}
                className="px-6"
              >
                {creating ? 'Creating...' : 'Create Project'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

