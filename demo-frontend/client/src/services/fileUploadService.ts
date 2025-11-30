import { apiRequest } from "@/lib/queryClient";
import { supabase } from "@/lib/supabaseClient";
import { type UploadedFile } from "@shared/schema";

export interface FileUploadResult {
  success: boolean;
  file?: UploadedFile;
  error?: string;
}

export class FileUploadService {
  async uploadFile(file: File): Promise<FileUploadResult> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      // For file uploads, we need to use fetch directly since apiRequest expects JSON
      const session = await supabase.auth.getSession();
      const accessToken = session.data.session?.access_token;
      const response = await fetch('/api/files/upload', {
        method: 'POST',
        body: formData,
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Upload failed: ${text}`);
      }

      const uploadedFile = await response.json();

      return {
        success: true,
        file: uploadedFile,
      };
    } catch (error) {
      console.error('File upload failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed',
      };
    }
  }

  async deleteFile(fileId: string): Promise<boolean> {
    try {
      await apiRequest('DELETE', `/api/files/${fileId}`);
      return true;
    } catch (error) {
      console.error('File deletion failed:', error);
      return false;
    }
  }

  async getUserFiles(): Promise<UploadedFile[]> {
    try {
      const response = await apiRequest('GET', '/api/files');
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch user files:', error);
      return [];
    }
  }
}

export const fileUploadService = new FileUploadService();