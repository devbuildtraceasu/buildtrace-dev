import { useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { CloudUpload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { validateFile, createFileRef, formatFileSize } from "@/features/uploads/services/validation";
import { FileRef } from "@/features/comparison/models";
import { useToast } from "@/hooks/use-toast";

interface UploadDropzoneProps {
  label: string;
  file: FileRef | null;
  onFileSelect: (file: FileRef | null) => void;
  className?: string;
}

export default function UploadDropzone({ 
  label, 
  file, 
  onFileSelect, 
  className 
}: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileSelection = useCallback((selectedFile: File) => {
    const validation = validateFile(selectedFile);
    
    if (!validation.valid) {
      toast({
        title: "Invalid file",
        description: validation.error,
        variant: "destructive",
      });
      return;
    }

    const fileRef = createFileRef(selectedFile);
    onFileSelect(fileRef);
  }, [onFileSelect, toast]);

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
      handleFileSelection(files[0]);
    }
  }, [handleFileSelection]);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  }, [handleFileSelection]);

  const handleRemoveFile = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [onFileSelect]);

  if (file) {
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
                <p className="font-medium text-gray-900" data-testid="file-name">{file.name}</p>
                <p className="text-sm text-gray-500" data-testid="file-size">
                  {formatFileSize(file.size)}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveFile}
              className="text-red-600 hover:text-red-700"
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
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
          {
            "drag-over": isDragging,
            "border-gray-300 hover:border-primary hover:bg-blue-50": !isDragging,
          }
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        data-testid={`dropzone-${label.toLowerCase().replace(/\s+/g, '-')}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg"
          onChange={handleFileInputChange}
          className="hidden"
          data-testid="file-input"
        />
        <CloudUpload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <p className="text-lg font-medium text-gray-600 mb-2">Drop your file here</p>
        <p className="text-sm text-gray-500 mb-4">or click to browse</p>
        <p className="text-xs text-gray-400">PDF, DWG, DXF, PNG, JPG • Max 50MB</p>
      </div>
    </div>
  );
}
