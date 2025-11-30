/**
 * BuildTrace AI - Modular Application Entry Point
 * Orchestrates all application modules for the main upload interface
 */

import FileUploader from './app/FileUploader.js';
import ProcessingMonitor from './app/ProcessingMonitor.js';
import RecentSessions from './app/RecentSessions.js';
import Utils from './shared/Utils.js';

class BuildTraceApp {
    constructor() {
        this.fileUploader = new FileUploader();
        this.processingMonitor = new ProcessingMonitor();
        this.recentSessions = new RecentSessions();

        this.initialize();
    }

    async initialize() {
        // Initialize all modules
        this.fileUploader.initialize();

        // Load recent sessions asynchronously (don't wait)
        this.recentSessions.initialize().catch(error => {
            console.error('Failed to load recent sessions:', error);
        });

        // Set up global event handlers
        this.setupGlobalEventHandlers();

        // Make removeFile function globally available for HTML onclick handlers
        window.removeFile = (type) => this.fileUploader.removeFile(type);
    }

    setupGlobalEventHandlers() {
        // Handle form submission
        const form = document.getElementById('upload-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Handle compare button click
        const compareBtn = document.getElementById('compare-btn');
        if (compareBtn) {
            compareBtn.addEventListener('click', (e) => this.handleCompareClick(e));
        }
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        await this.startProcessing();
    }

    async handleCompareClick(e) {
        e.preventDefault();
        const files = this.fileUploader.getFiles();
        if (!files.oldFile || !files.newFile) {
            Utils.showToast('Please upload both files before comparing', 'error');
            return;
        }
        await this.startProcessing();
    }

    async startProcessing() {
        const files = this.fileUploader.getFiles();

        if (!files.oldFile || !files.newFile) {
            Utils.showToast('Please upload both files before processing', 'error');
            return;
        }

        try {
            // Start processing and handle completion
            await this.processingMonitor.processFiles(
                files.oldFile,
                files.newFile,
                (sessionId) => {
                    // On successful completion, redirect to results
                    setTimeout(() => {
                        window.location.href = `/results/${sessionId}`;
                    }, 2000);

                    // Refresh recent sessions to include the new one
                    this.recentSessions.refresh();
                }
            );
        } catch (error) {
            console.error('Processing failed:', error);
            // Error is already handled by ProcessingMonitor, no need to show additional toast
        }
    }

    // Method to refresh recent sessions (can be called externally)
    refreshRecentSessions() {
        this.recentSessions.refresh();
    }

    // Method to reset the application state
    reset() {
        this.fileUploader.reset();
        this.processingMonitor.hideProcessingSection();
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.buildTraceApp = new BuildTraceApp();
});

export default BuildTraceApp;