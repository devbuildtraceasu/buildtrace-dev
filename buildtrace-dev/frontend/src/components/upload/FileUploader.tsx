'use client'

import React, { useRef, useState, useCallback } from 'react'
import { Upload, File, X } from 'lucide-react'
import { clsx } from 'clsx'

interface FileUploaderProps {
  title: string
  description: string
  file: File | null
  onFileSelect: (file: File | null) => void
  onRemoveFile: () => void
  accept?: string
  maxSize?: number
  className?: string
}

export default function FileUploader({
  title,
  description,
  file,
  onFileSelect,
  onRemoveFile,
  accept = '.pdf,.dwg,.dxf,.png,.jpg,.jpeg',
  maxSize = 70 * 1024 * 1024,
  className
}: FileUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const validateFile = (file: File): boolean => {
    if (file.size > maxSize) {
      alert(`File size must be less than ${formatFileSize(maxSize)}`)
      return false
    }
    return true
  }

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (validateFile(selectedFile)) {
      onFileSelect(selectedFile)
    }
  }, [onFileSelect, maxSize])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }, [handleFileSelect])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
    e.target.value = ''
  }, [handleFileSelect])

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onRemoveFile()
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className={clsx('space-y-4', className)}>
      <label className="block text-sm font-medium text-gray-700">{title}</label>
      
      {!file ? (
        <div
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={clsx(
            "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
            isDragOver
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          )}
          data-testid={`dropzone-${title.toLowerCase().replace(/\s+/g, '-')}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleInputChange}
            className="hidden"
          />
          <Upload 
            className={clsx(
              "mx-auto h-12 w-12 mb-4",
              "text-gray-400"
            )} 
          />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Drop your file here
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            or click to browse
          </p>
          <p className="text-xs text-gray-400">PDF, DWG, DXF, PNG, JPG • Max {formatFileSize(maxSize)}</p>
        </div>
      ) : (
        <div 
          className="border border-green-300 bg-green-50 rounded-xl p-4"
          data-testid={`dropzone-${title.toLowerCase().replace(/\s+/g, '-')}-filled`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <File className="text-red-500 h-8 w-8 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-900" data-testid="filename">
                  {file.name}
                </p>
                <p className="text-xs text-gray-500" data-testid="filesize">
                  {formatFileSize(file.size)}
                </p>
              </div>
            </div>
            <button
              onClick={handleRemove}
              className="text-gray-400 hover:text-red-500 transition-colors"
              title="Remove file"
              data-testid="button-remove-file"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
