/**
 * ApiClient Module
 * Centralized API communication handler
 */
class ApiClient {
    constructor() {
        this.baseUrl = window.location.origin;
        this.defaultHeaders = {
            'Accept': 'application/json'
        };
    }

    /**
     * Make a GET request
     */
    async get(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'GET',
                headers: this.defaultHeaders
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`GET ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * Make a POST request
     */
    async post(endpoint, data = null, isFormData = false) {
        try {
            const options = {
                method: 'POST',
                headers: isFormData ? {} : {
                    ...this.defaultHeaders,
                    'Content-Type': 'application/json'
                }
            };

            if (data) {
                options.body = isFormData ? data : JSON.stringify(data);
            }

            const response = await fetch(`${this.baseUrl}${endpoint}`, options);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `API Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`POST ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * Upload files with progress tracking
     */
    async uploadFiles(endpoint, formData, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        resolve({ success: true });
                    }
                } else {
                    // Try to parse error response from server
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        reject(new Error(errorResponse.error || `Server error: ${xhr.status}`));
                    } catch (parseError) {
                        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
                    }
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed: Network error'));
            });

            xhr.open('POST', `${this.baseUrl}${endpoint}`);
            xhr.send(formData);
        });
    }

    /**
     * Fetch recent sessions
     */
    async fetchRecentSessions() {
        try {
            return await this.get('/api/sessions/recent');
        } catch (error) {
            console.error('Failed to fetch recent sessions:', error);
            return { sessions: [] };
        }
    }

    /**
     * Delete a session
     */
    async deleteSession(sessionId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: this.defaultHeaders
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Delete failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Delete session ${sessionId} failed:`, error);
            throw error;
        }
    }

    /**
     * Submit comparison request (upload only)
     */
    async submitComparison(formData, onProgress) {
        return await this.uploadFiles('/upload', formData, onProgress);
    }

    /**
     * Process uploaded session
     */
    async processSession(sessionId) {
        return await this.post(`/process/${sessionId}`);
    }

    /**
     * Get drawing images for a session
     */
    async getDrawingImages(sessionId) {
        return await this.get(`/api/drawings/${sessionId}`);
    }

    /**
     * Get change details for a session
     */
    async getChangeDetails(sessionId) {
        return await this.get(`/api/changes/${sessionId}`);
    }

    /**
     * Send chat message
     */
    async sendChatMessage(sessionId, message) {
        return await this.post('/api/chat', { session_id: sessionId, message });
    }

    /**
     * Get chat history
     */
    async getChatHistory(sessionId) {
        try {
            return await this.get(`/api/chat/${sessionId}/history`);
        } catch (error) {
            // Return empty history if not found
            return { messages: [] };
        }
    }

    /**
     * Get signed upload URLs for direct Cloud Storage upload
     */
    async getUploadUrls(files) {
        try {
            return await this.post('/api/upload-urls', { files });
        } catch (error) {
            console.error('Failed to get upload URLs:', error);
            throw error;
        }
    }

    /**
     * Process files that have been uploaded directly to Cloud Storage
     */
    async processUploadedFiles(sessionId, files) {
        try {
            return await this.post('/api/process-uploaded-files', {
                session_id: sessionId,
                files: files
            });
        } catch (error) {
            console.error('Failed to process uploaded files:', error);
            throw error;
        }
    }
}

// Export singleton instance
const apiClient = new ApiClient();
export default apiClient;