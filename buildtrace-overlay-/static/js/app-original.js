// BuildTrace AI - Main Application JavaScript

class BuildTraceApp {
    constructor() {
        this.oldFile = null;
        this.newFile = null;
        this.sessionId = null;
        this.isProcessing = false;

        this.initializeEventListeners();
        this.loadRecentComparisons();
    }

    initializeEventListeners() {
        // File upload areas
        this.setupFileUpload('old');
        this.setupFileUpload('new');

        // Form submission
        const form = document.getElementById('upload-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Compare button
        const compareBtn = document.getElementById('compare-btn');
        if (compareBtn) {
            compareBtn.addEventListener('click', (e) => this.handleCompareClick(e));
        }
    }

    setupFileUpload(type) {
        const uploadArea = document.getElementById(`${type}-upload-area`);
        const fileInput = document.getElementById(`${type}-file`);
        const fileInfo = document.getElementById(`${type}-file-info`);

        if (!uploadArea || !fileInput || !fileInfo) return;

        // Click to browse
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(type, e.target.files[0]);
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');

            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelect(type, e.dataTransfer.files[0]);
            }
        });
    }

    handleFileSelect(type, file) {
        // Validate file type
        const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
        const allowedExtensions = ['.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg'];

        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        const isValidType = allowedTypes.includes(file.type) || allowedExtensions.includes(fileExtension);

        if (!isValidType) {
            this.showMessage('Invalid file type. Please select PDF, DWG, DXF, PNG, or JPG files.', 'error');
            return;
        }

        // Validate file size (70MB)
        if (file.size > 70 * 1024 * 1024) {
            this.showMessage('File size too large. Maximum size is 70MB.', 'error');
            return;
        }

        // Store file
        if (type === 'old') {
            this.oldFile = file;
        } else {
            this.newFile = file;
        }

        // Update UI
        this.updateFileDisplay(type, file);
        this.updateCompareButton();
        this.updateSteps();
    }

    updateFileDisplay(type, file) {
        const uploadArea = document.getElementById(`${type}-upload-area`);
        const fileInfo = document.getElementById(`${type}-file-info`);
        const fileName = fileInfo.querySelector('.file-name');
        const fileSize = fileInfo.querySelector('.file-size');

        if (!uploadArea || !fileInfo || !fileName || !fileSize) return;

        // Hide upload area, show file info
        uploadArea.style.display = 'none';
        fileInfo.style.display = 'block';

        // Update file details
        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);
    }

    updateCompareButton() {
        const compareBtn = document.getElementById('compare-btn');
        if (!compareBtn) return;

        const hasFiles = this.oldFile && this.newFile;
        compareBtn.disabled = !hasFiles || this.isProcessing;

        if (hasFiles && !this.isProcessing) {
            compareBtn.textContent = 'Compare Drawings';
        } else if (this.isProcessing) {
            compareBtn.textContent = 'Processing...';
        } else {
            compareBtn.textContent = 'Upload Both Files First';
        }
    }

    updateSteps() {
        const steps = document.querySelectorAll('.step');

        // Step 1: Upload Old
        if (this.oldFile) {
            steps[0]?.classList.add('active');
        }

        // Step 2: Upload New
        if (this.newFile) {
            steps[1]?.classList.add('active');
        }

        // Step 3: Process (when both files uploaded)
        if (this.oldFile && this.newFile && !this.isProcessing) {
            steps[2]?.classList.add('active');
        }
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        await this.startProcessing();
    }

    async handleCompareClick(e) {
        e.preventDefault();
        if (!this.oldFile || !this.newFile || this.isProcessing) {
            return;
        }
        await this.startProcessing();
    }

    async startProcessing() {
        if (this.isProcessing) return;

        this.isProcessing = true;
        this.updateCompareButton();

        try {
            // Show processing UI
            this.showProcessingUI();

            // Upload files
            this.updateProcessingStep('upload', 'completed');
            this.updateProcessingStep('extract', 'active');
            this.updateProcessingStatus('Uploading files...');

            const uploadResult = await this.uploadFiles();
            this.sessionId = uploadResult.session_id;

            // Process drawings
            this.updateProcessingStatus('Processing drawings...');
            this.updateProcessingStep('extract', 'completed');
            this.updateProcessingStep('convert', 'active');

            const processResult = await this.processDrawings();

            if (processResult.success) {
                if (processResult.status === 'processing') {
                    // Async processing - show intermediate status and start polling
                    this.updateProcessingStatus(processResult.message || 'Processing started...');
                    this.startPollingForResults();
                } else {
                    // Synchronous processing completed
                    this.handleProcessingComplete(processResult);
                }
            } else {
                throw new Error(processResult.error || 'Processing failed');
            }

        } catch (error) {
            console.error('Processing error:', error);
            this.showMessage(`Error: ${error.message}`, 'error');
            this.hideProcessingUI();
        }

        this.isProcessing = false;
        this.updateCompareButton();
    }

    handleProcessingComplete(processResult) {
        // Show success and redirect
        this.updateProcessingStep('convert', 'completed');
        this.updateProcessingStep('align', 'completed');
        this.updateProcessingStep('analyze', 'completed');
        const overlays = processResult.overlays_created || 0;
        const time = processResult.processing_time || 0;
        this.updateProcessingStatus(`Processing complete! Generated ${overlays} overlays in ${time.toFixed(1)}s`);

        // Update final step
        const steps = document.querySelectorAll('.step');
        steps[3]?.classList.add('active');

        // Redirect to results page
        setTimeout(() => {
            window.location.href = `/results/${this.sessionId}`;
        }, 2000);
    }

    async startPollingForResults() {
        const maxAttempts = 120; // 10 minutes with 5-second intervals
        let attempts = 0;

        const pollInterval = setInterval(async () => {
            attempts++;
            try {
                const response = await fetch(`/api/session/${this.sessionId}/status`);
                const statusData = await response.json();

                if (statusData.status === 'completed') {
                    clearInterval(pollInterval);
                    // Use the actual summary data from the endpoint
                    this.handleProcessingComplete({
                        overlays_created: statusData.summary?.overlays_created || 0,
                        processing_time: statusData.total_time || 0
                    });
                } else if (statusData.status === 'error') {
                    clearInterval(pollInterval);
                    const errorMsg = statusData.session_metadata?.error || statusData.error || 'Processing failed';
                    throw new Error(errorMsg);
                } else if (attempts >= maxAttempts) {
                    clearInterval(pollInterval);
                    throw new Error('Processing timeout - please check results page manually');
                } else {
                    // Update progress if available
                    if (statusData.current_step) {
                        this.updateProcessingStatus(`Processing: ${statusData.current_step}`);
                    }
                }
            } catch (error) {
                clearInterval(pollInterval);
                console.error('Polling error:', error);
                this.showMessage(`Error checking status: ${error.message}`, 'error');
                this.hideProcessingUI();
                this.isProcessing = false;
                this.updateCompareButton();
            }
        }, 5000); // Poll every 5 seconds
    }

    async uploadFiles() {
        const formData = new FormData();
        formData.append('old_file', this.oldFile);
        formData.append('new_file', this.newFile);

        // Include project_id if available
        const projectIdInput = document.getElementById('selected-project-id');
        if (projectIdInput && projectIdInput.value) {
            formData.append('project_id', projectIdInput.value);
        }

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }

        return await response.json();
    }

    async processDrawings() {
        if (!this.sessionId) {
            throw new Error('No session ID available');
        }

        const response = await fetch(`/process/${this.sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Processing failed');
        }

        return await response.json();
    }

    showProcessingUI() {
        const uploadSection = document.querySelector('.upload-section');
        const processingSection = document.getElementById('processing-monitor');

        if (uploadSection) uploadSection.style.display = 'none';
        if (processingSection) processingSection.style.display = 'block';
    }

    hideProcessingUI() {
        const uploadSection = document.querySelector('.upload-section');
        const processingSection = document.getElementById('processing-monitor');

        if (uploadSection) uploadSection.style.display = 'block';
        if (processingSection) processingSection.style.display = 'none';
    }

    updateProcessingStatus(message) {
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    updateProcessingStep(stepId, status) {
        const stepElement = document.getElementById(`proc-${stepId}`);
        if (!stepElement) return;

        const spinner = stepElement.querySelector('.spinner-small');
        const check = stepElement.querySelector('.check');

        if (status === 'completed') {
            if (spinner) spinner.style.display = 'none';
            if (check) {
                check.style.display = 'inline';
                check.textContent = '✓';
            } else {
                // Create check element if it doesn't exist
                const newCheck = document.createElement('span');
                newCheck.className = 'check';
                newCheck.textContent = '✓';
                newCheck.style.display = 'inline';
                stepElement.insertBefore(newCheck, stepElement.firstChild);
                if (spinner) spinner.remove();
            }
        } else if (status === 'active') {
            if (check) check.style.display = 'none';
            if (spinner) {
                spinner.style.display = 'inline-block';
            } else {
                // Create spinner element if it doesn't exist
                const newSpinner = document.createElement('span');
                newSpinner.className = 'spinner-small';
                stepElement.insertBefore(newSpinner, stepElement.firstChild);
            }
        }
    }

    showMessage(message, type = 'info') {
        // Remove existing messages
        const existingMessages = document.querySelectorAll('.message');
        existingMessages.forEach(msg => msg.remove());

        // Create new message
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;

        // Insert at the top of the container
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(messageDiv, container.firstChild);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                messageDiv.remove();
            }, 5000);
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    removeFile(type) {
        if (type === 'old') {
            this.oldFile = null;
        } else {
            this.newFile = null;
        }

        // Reset UI
        const uploadArea = document.getElementById(`${type}-upload-area`);
        const fileInfo = document.getElementById(`${type}-file-info`);
        const fileInput = document.getElementById(`${type}-file`);

        if (uploadArea) uploadArea.style.display = 'block';
        if (fileInfo) fileInfo.style.display = 'none';
        if (fileInput) fileInput.value = '';

        this.updateCompareButton();
        this.updateSteps();
    }

    async loadRecentComparisons() {
        try {
            const response = await fetch('/api/sessions/recent');
            if (!response.ok) {
                throw new Error('Failed to load recent sessions');
            }

            const data = await response.json();
            this.displayRecentComparisons(data.sessions || []);

        } catch (error) {
            console.error('Error loading recent comparisons:', error);
            const container = document.getElementById('recent-comparisons-list');
            if (container) {
                container.innerHTML = `
                    <div class="empty-comparisons">
                        <div class="empty-comparisons-icon">📁</div>
                        <p>No recent comparisons available</p>
                    </div>
                `;
            }
        }
    }

    displayRecentComparisons(sessions) {
        const container = document.getElementById('recent-comparisons-list');
        if (!container) return;

        if (sessions.length === 0) {
            container.innerHTML = `
                <div class="empty-comparisons">
                    <div class="empty-comparisons-icon">📋</div>
                    <p>No recent comparisons yet</p>
                    <p style="font-size: 0.9rem; margin-top: 10px;">Upload your first set of drawings to get started!</p>
                </div>
            `;
            return;
        }

        // Create comparison cards
        const cardsHTML = sessions.map(session => {
            const date = new Date(session.created_at);
            const formattedDate = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            const processingTime = session.total_time ? `${session.total_time.toFixed(1)}s` : 'N/A';

            return `
                <div class="comparison-card" onclick="window.location.href='/results/${session.id}'">
                    <h3>${session.project_name}</h3>
                    <div class="comparison-meta">
                        <div class="comparison-meta-item">
                            <span class="icon">📅</span>
                            <span>${formattedDate}</span>
                        </div>
                        <div class="comparison-meta-item">
                            <span class="icon">📄</span>
                            <span>${session.comparison_count} ${session.comparison_count === 1 ? 'comparison' : 'comparisons'}</span>
                        </div>
                        <div class="comparison-meta-item">
                            <span class="icon">⏱️</span>
                            <span>Processing time: ${processingTime}</span>
                        </div>
                    </div>
                    <div class="comparison-status">
                        ✅ Completed
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = cardsHTML;
    }
}

// Global function for remove file buttons
function removeFile(type) {
    if (window.buildTraceApp) {
        window.buildTraceApp.removeFile(type);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.buildTraceApp = new BuildTraceApp();
});