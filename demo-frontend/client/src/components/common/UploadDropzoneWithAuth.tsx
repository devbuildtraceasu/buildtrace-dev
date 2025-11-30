import { useState, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { CloudUpload, FileText, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { validateFile, formatFileSize } from "@/features/uploads/services/validation";
import { fileUploadService, type FileUploadResult } from "@/services/fileUploadService";
import { type UploadedFile } from "@shared/schema";

interface UploadDropzoneWithAuthProps {
  label: string;
  uploadedFile: UploadedFile | null;
  onFileUploaded: (file: UploadedFile | null) => void;
  className?: string;
}

export default function UploadDropzoneWithAuth({ 
  label, 
  uploadedFile, 
  onFileUploaded, 
  className,
}: UploadDropzoneWithAuthProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileUpload = useCallback(async (selectedFile: File) => {
    const validation = validateFile(selectedFile);
    
    if (!validation.valid) {
      toast({
        title: "Invalid file",
        description: validation.error,
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);
    
    try {
      const result: FileUploadResult = await fileUploadService.uploadFile(selectedFile);
      
      if (result.success && result.file) {
        onFileUploaded(result.file);
        toast({
          title: "File uploaded successfully",
          description: `${selectedFile.name} has been uploaded.`,
        });
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (error) {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : 'Please try again.',
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  }, [onFileUploaded, toast]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  const handleClick = useCallback(() => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  }, [isUploading]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  const handleRemoveFile = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (uploadedFile) {
      const success = await fileUploadService.deleteFile(uploadedFile.id);
      if (success) {
        onFileUploaded(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        toast({
          title: "File removed",
          description: "File has been deleted from the server.",
        });
      } else {
        toast({
          title: "Failed to remove file",
          description: "Please try again.",
          variant: "destructive",
        });
      }
    }
  }, [uploadedFile, onFileUploaded, toast]);

  if (uploadedFile) {
    return (
      <div className={cn("space-y-4", className)}>
        <label className="block text-sm font-medium text-gray-700">{label}</label>
        <div 
          className="border border-green-300 bg-green-50 rounded-xl p-4"
          data-testid={`dropzone-${label.toLowerCase().replace(/\s+/g, '-')}-filled`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <FileText className="text-red-500 h-8 w-8 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-900" data-testid="filename">
                  {uploadedFile.originalName}
                </p>
                <p className="text-xs text-gray-500" data-testid="filesize">
                  {formatFileSize(uploadedFile.fileSize)}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveFile}
              className="text-gray-400 hover:text-red-500"
              data-testid="button-remove-file"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
          isDragging
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 hover:border-gray-400 hover:bg-gray-50",
          isUploading && "opacity-50 cursor-not-allowed"
        )}
        data-testid={`dropzone-${label.toLowerCase().replace(/\s+/g, '-')}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg"
          onChange={handleFileInputChange}
          className="hidden"
          disabled={isUploading}
        />
        <CloudUpload 
          className={cn(
            "mx-auto h-12 w-12 mb-4",
            isUploading ? "text-gray-400" : "text-gray-400"
          )} 
        />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {isUploading ? "Uploading..." : "Drop your file here"}
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          {isUploading ? "Please wait..." : "or click to browse"}
        </p>
        <p className="text-xs text-gray-400">PDF, DWG, DXF, PNG, JPG • Max 50MB</p>
      </div>
    </div>
  );
}