'use client'

import React, { useRef, useState, useCallback } from 'react'
import { clsx } from 'clsx'
import { Upload, File, X } from 'lucide-react'
import { toast } from 'react-hot-toast'

interface FileUploaderProps {
  title: string
  description: string
  file: File | null
  onFileSelect: (file: File | null) => void
  onRemoveFile: () => void
  accept?: string
  maxSize?: number // in bytes
  className?: string
}

const FileUploader: React.FC<FileUploaderProps> = ({
  title,
  description,
  file,
  onFileSelect,
  onRemoveFile,
  accept = '.pdf,.dwg,.dxf,.png,.jpg,.jpeg',
  maxSize = 70 * 1024 * 1024, // 70MB default
  className
}) => {
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
    // Check file size
    if (file.size > maxSize) {
      toast.error(`File size must be less than ${formatFileSize(maxSize)}`)
      return false
    }

    // Check file type
    const acceptedTypes = accept.split(',').map(type => type.trim().toLowerCase())
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    const mimeType = file.type.toLowerCase()

    const isValidExtension = acceptedTypes.some(type =>
      type.startsWith('.') ? fileExtension === type : mimeType.includes(type)
    )

    if (!isValidExtension) {
      toast.error(`File type not supported. Accepted types: ${accept}`)
      return false
    }

    return true
  }

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (validateFile(selectedFile)) {
      onFileSelect(selectedFile)
      toast.success(`${selectedFile.name} uploaded successfully`)
    }
  }, [onFileSelect, maxSize, accept])

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
    // Reset input value to allow selecting the same file again
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
    <div className={clsx('w-full', className)}>
      <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>

      {!file ? (
        <div
          className={clsx(
            'upload-area',
            'min-h-[200px] flex flex-col items-center justify-center',
            'border-2 border-dashed rounded-lg p-6 cursor-pointer transition-colors',
            {
              'border-buildtrace-primary bg-blue-50': isDragOver,
              'border-gray-300 hover:border-buildtrace-primary': !isDragOver
            }
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <Upload className={clsx(
            'w-12 h-12 mb-4',
            isDragOver ? 'text-buildtrace-primary' : 'text-gray-400'
          )} />

          <p className="text-gray-600 text-center mb-2 font-medium">
            {description}
          </p>

          <p className="text-sm text-gray-500 text-center">
            or click to browse
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleInputChange}
            className="hidden"
          />
        </div>
      ) : (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="flex items-center space-x-3">
            <File className="w-8 h-8 text-buildtrace-primary flex-shrink-0" />

            <div className="flex-grow min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {file.name}
              </p>
              <p className="text-xs text-gray-500">
                {formatFileSize(file.size)}
              </p>
            </div>

            <button
              onClick={handleRemove}
              className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-red-100 hover:bg-red-200 text-red-600 transition-colors"
              title="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-500 mt-2">
        Supported: {accept.toUpperCase()} (Max {formatFileSize(maxSize)})
      </p>
    </div>
  )
}

export default FileUploader