/**
 * FileUploader Module
 * Handles file selection, validation, and upload UI
 */
import Utils from '../shared/Utils.js';

class FileUploader {
    constructor() {
        this.oldFile = null;
        this.newFile = null;
        this.maxFileSize = 70 * 1024 * 1024; // 70MB
        this.acceptedTypes = ['.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg'];
    }

    initialize() {
        this.setupUploadAreas();
        this.setupFileInputs();
        this.updateCompareButton();
    }

    setupUploadAreas() {
        const oldUploadArea = document.getElementById('old-upload-area');
        const newUploadArea = document.getElementById('new-upload-area');

        if (oldUploadArea) {
            this.setupDropZone(oldUploadArea, 'old');
        }

        if (newUploadArea) {
            this.setupDropZone(newUploadArea, 'new');
        }
    }

    setupDropZone(dropZone, type) {
        // Click to browse
        dropZone.addEventListener('click', () => {
            const input = document.getElementById(`${type}-file`);
            if (input) input.click();
        });

        // Drag and drop events
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0], type);
            }
        });
    }

    setupFileInputs() {
        const oldInput = document.getElementById('old-file');
        const newInput = document.getElementById('new-file');

        if (oldInput) {
            oldInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelect(e.target.files[0], 'old');
                }
            });
        }

        if (newInput) {
            newInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelect(e.target.files[0], 'new');
                }
            });
        }
    }

    handleFileSelect(file, type) {
        // Validate file type
        if (!Utils.isValidFileType(file, this.acceptedTypes)) {
            Utils.showToast(
                `Invalid file type. Accepted types: ${this.acceptedTypes.join(', ')}`,
                'error'
            );
            return;
        }

        // Validate file size
        if (!Utils.isValidFileSize(file, 70)) {
            Utils.showToast('File size must be less than 70MB', 'error');
            return;
        }

        // Store file and update UI
        if (type === 'old') {
            this.oldFile = file;
            this.updateFileInfo('old', file);
            this.updateStep(1, 'completed');
            this.updateStep(2, 'active');
        } else {
            this.newFile = file;
            this.updateFileInfo('new', file);
            this.updateStep(2, 'completed');
        }

        this.updateCompareButton();
    }

    updateFileInfo(type, file) {
        const uploadArea = document.getElementById(`${type}-upload-area`);
        const fileInfo = document.getElementById(`${type}-file-info`);

        if (uploadArea) uploadArea.style.display = 'none';
        if (fileInfo) {
            fileInfo.style.display = 'flex';
            const nameElement = fileInfo.querySelector('.file-name');
            const sizeElement = fileInfo.querySelector('.file-size');

            if (nameElement) nameElement.textContent = file.name;
            if (sizeElement) sizeElement.textContent = Utils.formatFileSize(file.size);
        }
    }

    removeFile(type) {
        if (type === 'old') {
            this.oldFile = null;
            this.updateStep(1, 'active');
            this.updateStep(2, '');
        } else {
            this.newFile = null;
            if (this.oldFile) {
                this.updateStep(2, 'active');
            }
        }

        // Reset UI
        const uploadArea = document.getElementById(`${type}-upload-area`);
        const fileInfo = document.getElementById(`${type}-file-info`);
        const fileInput = document.getElementById(`${type}-file`);

        if (uploadArea) uploadArea.style.display = 'block';
        if (fileInfo) fileInfo.style.display = 'none';
        if (fileInput) fileInput.value = '';

        this.updateCompareButton();
    }

    updateCompareButton() {
        const compareBtn = document.getElementById('compare-btn');
        if (compareBtn) {
            compareBtn.disabled = !this.oldFile || !this.newFile;
            if (this.oldFile && this.newFile) {
                compareBtn.classList.add('ready');
            } else {
                compareBtn.classList.remove('ready');
            }
        }
    }

    updateStep(stepNumber, status) {
        const step = document.getElementById(`step-${stepNumber}`);
        if (!step) return;

        step.classList.remove('active', 'completed');
        if (status) {
            step.classList.add(status);
        }
    }

    getFiles() {
        return {
            oldFile: this.oldFile,
            newFile: this.newFile
        };
    }

    reset() {
        this.oldFile = null;
        this.newFile = null;

        // Reset all UI elements
        ['old', 'new'].forEach(type => {
            const uploadArea = document.getElementById(`${type}-upload-area`);
            const fileInfo = document.getElementById(`${type}-file-info`);
            const fileInput = document.getElementById(`${type}-file`);

            if (uploadArea) uploadArea.style.display = 'block';
            if (fileInfo) fileInfo.style.display = 'none';
            if (fileInput) fileInput.value = '';
        });

        // Reset steps
        this.updateStep(1, 'active');
        this.updateStep(2, '');
        this.updateStep(3, '');
        this.updateStep(4, '');

        this.updateCompareButton();
    }
}

export default FileUploader;