/**
 * ProcessingMonitor Module
 * Handles file processing, progress tracking, and status updates
 */
import apiClient from '../shared/ApiClient.js';
import Utils from '../shared/Utils.js';

class ProcessingMonitor {
    constructor() {
        this.sessionId = null;
        this.processingSteps = [
            { id: 'proc-upload', label: 'Files uploaded' },
            { id: 'proc-extract', label: 'Extracting drawing names' },
            { id: 'proc-convert', label: 'Converting to images' },
            { id: 'proc-align', label: 'Aligning drawings' },
            { id: 'proc-analyze', label: 'AI analysis' }
        ];
        this.currentStep = 0;
    }

    async processFiles(oldFile, newFile, onComplete) {
        try {
            this.showProcessingSection();
            this.resetSteps();

            // Check file sizes and decide upload method
            const totalSize = oldFile.size + newFile.size;
            const maxDirectUploadSize = 15 * 1024 * 1024; // 15MB to be safe with Cloud Run's 32MB limit (accounting for base64 encoding overhead)

            console.log(`Total file size: ${Utils.formatFileSize(totalSize)}, threshold: ${Utils.formatFileSize(maxDirectUploadSize)}`);

            if (totalSize > maxDirectUploadSize) {
                // Use direct Cloud Storage upload for large files
                console.log(`🚀 Files too large for direct upload (${Utils.formatFileSize(totalSize)}), using Cloud Storage`);
                await this.processFilesViaCloudStorage(oldFile, newFile, onComplete);
            } else {
                // Use legacy direct upload for smaller files
                console.log(`📤 Files small enough for direct upload (${Utils.formatFileSize(totalSize)}), using legacy method`);
                await this.processFilesDirectly(oldFile, newFile, onComplete);
            }
        } catch (error) {
            console.error('Processing error:', error);
            this.showError(error.message);
            throw error;
        }
    }

    async processFilesDirectly(oldFile, newFile, onComplete) {
        // Create form data
        const formData = new FormData();
        formData.append('old_file', oldFile);
        formData.append('new_file', newFile);

        // Update status and start first step
        this.updateStatus('Uploading files...');
        this.updateStep(0, 'processing');

        // Submit for upload only (new app flow)
        const uploadResponse = await apiClient.submitComparison(formData, (progress) => {
            this.updateUploadProgress(progress);
        });

        // Check if we got a valid upload response
        if (!uploadResponse) {
            throw new Error('No response received from server');
        }

        if (uploadResponse.session_id) {
            this.sessionId = uploadResponse.session_id;
            this.updateStep(0, 'completed');

            // Now process the uploaded files
            this.updateStatus('Processing drawings...');
            this.updateStep(1, 'processing');

            const processResponse = await apiClient.processSession(this.sessionId);

            if (processResponse.success) {
                if (processResponse.status === 'processing') {
                    // Background processing - start polling for status
                    this.updateStatus('Processing drawings in background...', 'processing');
                    await this.pollSessionStatus(this.sessionId, onComplete);
                } else {
                    // Synchronous processing (legacy)
                    await this.simulateProcessingSteps();
                    if (onComplete) {
                        onComplete(this.sessionId);
                    }
                }
            } else {
                throw new Error(processResponse.error || 'Processing failed');
            }
        } else if (uploadResponse.error) {
            // Server returned upload error
            throw new Error(uploadResponse.error);
        } else {
            throw new Error('Upload failed - no session ID returned');
        }
    }

    async processFilesViaCloudStorage(oldFile, newFile, onComplete) {
        this.updateStatus('Preparing large file upload...');
        this.updateStep(0, 'processing');

        try {
            console.log('🌤️ Starting Cloud Storage upload process');

            // Step 1: Get signed upload URLs
            console.log('📡 Requesting signed upload URLs...');
            const uploadUrlResponse = await apiClient.getUploadUrls([
                { name: oldFile.name, type: 'old' },
                { name: newFile.name, type: 'new' }
            ]);

            console.log('📡 Upload URL response:', uploadUrlResponse);

            if (!uploadUrlResponse.session_id || !uploadUrlResponse.upload_urls) {
                throw new Error('Failed to get upload URLs: Missing session_id or upload_urls');
            }

            this.sessionId = uploadUrlResponse.session_id;
            const uploadUrls = uploadUrlResponse.upload_urls;

            // Step 2: Upload files directly to Cloud Storage
            this.updateStatus('Uploading files to cloud storage...');

            const uploadPromises = [];

            // Upload old file
            if (uploadUrls.old) {
                uploadPromises.push(
                    this.uploadToCloudStorage(oldFile, uploadUrls.old.upload_url, 'old')
                );
            }

            // Upload new file
            if (uploadUrls.new) {
                uploadPromises.push(
                    this.uploadToCloudStorage(newFile, uploadUrls.new.upload_url, 'new')
                );
            }

            await Promise.all(uploadPromises);
            this.updateStep(0, 'completed');

            // Step 3: Process the uploaded files
            this.updateStatus('Processing drawings...');
            this.updateStep(1, 'processing');

            const processResponse = await apiClient.processUploadedFiles(this.sessionId, {
                old: uploadUrls.old,
                new: uploadUrls.new
            });

            if (processResponse.success) {
                this.updateStatus('Processing drawings in background...', 'processing');
                await this.pollSessionStatus(this.sessionId, onComplete);
            } else {
                throw new Error(processResponse.error || 'Processing failed');
            }

        } catch (error) {
            console.error('Cloud Storage upload error:', error);
            throw new Error(`Upload failed: ${error.message}`);
        }
    }

    async uploadToCloudStorage(file, uploadUrl, fileType) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const progress = (event.loaded / event.total) * 100;
                    this.updateUploadProgress(progress, fileType);
                }
            };

            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    console.log(`✅ ${fileType} file uploaded successfully to Cloud Storage`);
                    resolve();
                } else {
                    console.error(`❌ Upload failed for ${fileType}:`, xhr.status, xhr.statusText, xhr.responseText);
                    reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.statusText}`));
                }
            };

            xhr.onerror = () => {
                console.error(`❌ Network error during ${fileType} file upload`);
                reject(new Error(`Network error during ${fileType} file upload`));
            };

            console.log(`📤 Uploading ${fileType} file to:`, uploadUrl);

            // Use PUT method for our direct upload endpoint
            xhr.open('PUT', uploadUrl);
            xhr.setRequestHeader('Content-Type', 'application/pdf');
            xhr.send(file);
        });
    }

    async pollSessionStatus(sessionId, onComplete) {
        const maxAttempts = 120; // 10 minutes with 5 second intervals
        let attempts = 0;

        return new Promise((resolve, reject) => {
            const pollInterval = setInterval(async () => {
                attempts++;

                try {
                    const response = await fetch(`/api/session/${sessionId}/status`);

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }

                    const status = await response.json();

                    if (status.status === 'completed') {
                        clearInterval(pollInterval);

                        // Complete all processing steps
                        this.updateStep(1, 'completed');
                        this.updateStep(2, 'completed');
                        this.updateStep(3, 'completed');
                        this.updateStep(4, 'completed');
                        this.setProgress(100);
                        this.updateStatus('Processing completed!');

                        if (onComplete) {
                            onComplete(sessionId);
                        }
                        resolve();

                    } else if (status.status === 'error') {
                        clearInterval(pollInterval);
                        const errorMsg = status.error || 'Processing failed';
                        this.showError(errorMsg);
                        reject(new Error(errorMsg));

                    } else if (status.status === 'processing') {
                        // Update progress based on time elapsed (smoother progression)
                        const baseProgress = 25; // Upload step completed
                        const remainingProgress = 70; // Available for processing
                        const timeProgress = Math.min(remainingProgress, (attempts / maxAttempts) * remainingProgress);
                        const totalProgress = baseProgress + timeProgress;

                        this.setProgress(totalProgress);

                        // Update processing steps based on progress
                        if (totalProgress > 30) this.updateStep(1, 'completed');
                        if (totalProgress > 50) this.updateStep(2, 'completed');
                        if (totalProgress > 70) this.updateStep(3, 'completed');

                        this.updateStatus(`Processing... (${Math.round(totalProgress)}%)`);
                    }

                    if (attempts >= maxAttempts) {
                        clearInterval(pollInterval);
                        const timeoutMsg = 'Processing is taking longer than expected. You can safely close this page and check your results later.';
                        this.updateStatus(timeoutMsg, 'warning');

                        // Don't reject - let user navigate away
                        resolve();
                    }

                } catch (error) {
                    console.warn('Polling error:', error);

                    // Network error - show user-friendly message but keep trying
                    this.updateStatus('Connection issue - retrying...', 'warning');

                    if (attempts >= maxAttempts) {
                        clearInterval(pollInterval);
                        const networkMsg = 'Lost connection to server. Processing may still be running. Please check your results later.';
                        this.updateStatus(networkMsg, 'warning');
                        resolve(); // Don't reject - let user navigate away
                    }
                }
            }, 5000); // Poll every 5 seconds
        });
    }

    async simulateProcessingSteps() {
        const steps = [
            { duration: 2000, status: 'Extracting drawing names...' },
            { duration: 3000, status: 'Converting to images...' },
            { duration: 3000, status: 'Aligning drawings...' },
            { duration: 4000, status: 'Running AI analysis...' }
        ];

        for (let i = 0; i < steps.length; i++) {
            this.updateStep(i + 1, 'processing');
            this.updateStatus(steps[i].status);

            await new Promise(resolve => setTimeout(resolve, steps[i].duration));

            this.updateStep(i + 1, 'completed');
        }

        this.updateStatus('Processing complete!');
    }

    showProcessingSection() {
        const uploadSection = document.querySelector('.upload-section');
        const processingSection = document.getElementById('processing-section');

        if (uploadSection) uploadSection.style.display = 'none';
        if (processingSection) processingSection.style.display = 'block';

        // Update main steps
        const step3 = document.getElementById('step-3');
        if (step3) step3.classList.add('active');
    }

    hideProcessingSection() {
        const uploadSection = document.querySelector('.upload-section');
        const processingSection = document.getElementById('processing-section');

        if (uploadSection) uploadSection.style.display = 'block';
        if (processingSection) processingSection.style.display = 'none';
    }

    resetSteps() {
        this.currentStep = 0;
        this.processingSteps.forEach((step, index) => {
            this.updateStep(index, 'pending');
        });
    }

    updateStep(stepIndex, status) {
        if (stepIndex < 0 || stepIndex >= this.processingSteps.length) return;

        const stepElement = document.getElementById(this.processingSteps[stepIndex].id);
        if (!stepElement) return;

        // Remove all status classes
        stepElement.classList.remove('completed', 'processing', 'error');

        // Update icon and status
        const icon = stepElement.querySelector('span:first-child');
        if (!icon) return;

        switch (status) {
            case 'completed':
                icon.innerHTML = '<span class="check">✓</span>';
                stepElement.classList.add('completed');
                break;
            case 'processing':
                icon.innerHTML = '<span class="spinner-small"></span>';
                stepElement.classList.add('processing');
                break;
            case 'error':
                icon.innerHTML = '<span class="error-icon">✗</span>';
                stepElement.classList.add('error');
                break;
            default:
                icon.innerHTML = '<span class="spinner-small"></span>';
        }
    }

    updateStatus(message) {
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    updateUploadProgress(progress) {
        const progressText = `Uploading files... ${Math.round(progress)}%`;
        this.updateStatus(progressText);
    }

    setProgress(progress) {
        // Update progress bar if it exists
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        // Update progress text if it exists
        const progressText = document.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${Math.round(progress)}%`;
        }
    }

    showError(message) {
        // Hide processing section immediately to show failure prominently
        this.hideProcessingSection();

        // Show error at the top of the page prominently
        this.showErrorAtTop(message);

        // Also show toast for immediate feedback
        if (typeof Utils !== 'undefined' && Utils.showToast) {
            Utils.showToast(`Processing failed: ${message}`, 'error', 8000);
        }
    }

    showErrorAtTop(message) {
        // Remove any existing error messages
        const existingError = document.querySelector('.upload-error');
        if (existingError) {
            existingError.remove();
        }

        // Create error message element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'upload-error';
        errorDiv.innerHTML = `
            <div style="
                background: #fee2e2;
                border: 1px solid #fca5a5;
                border-radius: 8px;
                padding: 16px;
                margin: 20px 0;
                color: #dc2626;
                display: flex;
                align-items: center;
                justify-content: space-between;
            ">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">❌</span>
                    <div>
                        <strong>Upload Failed</strong>
                        <div style="margin-top: 4px; font-size: 14px;">${message}</div>
                    </div>
                </div>
                <button
                    onclick="this.parentElement.parentElement.remove()"
                    style="
                        background: none;
                        border: none;
                        font-size: 18px;
                        cursor: pointer;
                        color: #dc2626;
                        padding: 4px 8px;
                    "
                    title="Dismiss"
                >×</button>
            </div>
        `;

        // Insert at the top of the container, right after header
        const container = document.querySelector('.container');
        const header = document.querySelector('.header');
        if (container && header) {
            header.parentNode.insertBefore(errorDiv, header.nextSibling);
        } else if (container) {
            container.insertBefore(errorDiv, container.firstChild);
        }

        // Auto-remove after 15 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 15000);
    }

    getSessionId() {
        return this.sessionId;
    }
}

export default ProcessingMonitor;