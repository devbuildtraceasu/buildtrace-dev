/**
 * Utils Module
 * Common utility functions shared across the application
 */
class Utils {
    /**
     * Format file size for display
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Format date for display
     */
    static formatDate(date) {
        if (!date) return '';
        const d = new Date(date);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
    }

    /**
     * Format relative time (e.g., "2 hours ago")
     */
    static formatRelativeTime(date) {
        if (!date) return '';

        const now = new Date();
        const then = new Date(date);
        const seconds = Math.floor((now - then) / 1000);

        const intervals = [
            { label: 'year', seconds: 31536000 },
            { label: 'month', seconds: 2592000 },
            { label: 'day', seconds: 86400 },
            { label: 'hour', seconds: 3600 },
            { label: 'minute', seconds: 60 },
            { label: 'second', seconds: 1 }
        ];

        for (const interval of intervals) {
            const count = Math.floor(seconds / interval.seconds);
            if (count >= 1) {
                return `${count} ${interval.label}${count !== 1 ? 's' : ''} ago`;
            }
        }

        return 'just now';
    }

    /**
     * Truncate text with ellipsis
     */
    static truncateText(text, maxLength = 100) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Debounce function calls
     */
    static debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Show toast notification
     */
    static showToast(message, type = 'info', duration = 3000) {
        // Remove any existing toasts
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            color: white;
            font-weight: 500;
        `;

        // Set background color based on type
        switch (type) {
            case 'success':
                toast.style.background = '#10b981';
                break;
            case 'error':
                toast.style.background = '#ef4444';
                break;
            case 'warning':
                toast.style.background = '#f59e0b';
                break;
            default:
                toast.style.background = '#3b82f6';
        }

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    /**
     * Copy text to clipboard
     */
    static async copyToClipboard(text) {
        try {
            if (navigator.clipboard) {
                await navigator.clipboard.writeText(text);
                this.showToast('Copied to clipboard', 'success');
            } else {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                this.showToast('Copied to clipboard', 'success');
            }
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            this.showToast('Failed to copy to clipboard', 'error');
        }
    }

    /**
     * Validate file type
     */
    static isValidFileType(file, acceptedTypes = ['.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg']) {
        // Check both MIME types and file extensions (like the original app)
        const allowedMimeTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

        // Valid if either MIME type matches OR file extension matches
        const isValidMimeType = allowedMimeTypes.includes(file.type);
        const isValidExtension = acceptedTypes.includes(fileExtension);

        return isValidMimeType || isValidExtension;
    }

    /**
     * Validate file size
     */
    static isValidFileSize(file, maxSizeMB = 70) {
        const maxSizeBytes = maxSizeMB * 1024 * 1024;
        return file.size <= maxSizeBytes;
    }

    /**
     * Generate unique ID
     */
    static generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Parse JSON safely
     */
    static parseJSON(str, defaultValue = null) {
        try {
            return JSON.parse(str);
        } catch (error) {
            return defaultValue;
        }
    }

    /**
     * Check if element is in viewport
     */
    static isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    /**
     * Smooth scroll to element
     */
    static scrollToElement(element, offset = 0) {
        const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
        const offsetPosition = elementPosition - offset;

        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }

    /**
     * Add loading spinner to element
     */
    static addLoadingSpinner(element, message = 'Loading...') {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner-container';
        spinner.innerHTML = `
            <div class="spinner"></div>
            <p>${message}</p>
        `;
        spinner.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.9);
            z-index: 1000;
        `;
        element.style.position = 'relative';
        element.appendChild(spinner);
        return spinner;
    }

    /**
     * Remove loading spinner
     */
    static removeLoadingSpinner(spinner) {
        if (spinner && spinner.parentNode) {
            spinner.remove();
        }
    }
}

export default Utils;