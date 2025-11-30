/**
 * RecentSessions Module
 * Handles loading and displaying recent comparison sessions
 */
import apiClient from '../shared/ApiClient.js';
import Utils from '../shared/Utils.js';

class RecentSessions {
    constructor() {
        this.sessions = [];
    }

    async initialize() {
        // Show loading skeleton immediately
        this.renderLoadingSkeleton();

        // Load sessions and render when ready
        await this.loadRecentSessions();
        this.renderSessions();
    }

    renderLoadingSkeleton() {
        const container = document.getElementById('recent-comparisons-list');
        if (!container) return;

        container.innerHTML = `
            <div class="sessions-table-container">
                <div style="padding: 20px; text-align: center;">
                    <div class="loading-skeleton" style="display: inline-block;">
                        <div style="width: 20px; height: 20px; border: 2px solid #f3f3f3; border-radius: 50%; border-top-color: #3b82f6; animation: spin 1s linear infinite;"></div>
                    </div>
                    <p style="margin-top: 10px; color: #64748b;">Loading recent comparisons...</p>
                </div>
            </div>
        `;
    }

    async loadRecentSessions() {
        try {
            const response = await apiClient.fetchRecentSessions();
            this.sessions = response.sessions || [];
            console.log(`Loaded ${this.sessions.length} recent sessions`);
        } catch (error) {
            console.error('Failed to load recent sessions:', error);
            this.sessions = [];
        }
    }

    renderSessions() {
        const container = document.getElementById('recent-comparisons-list');
        if (!container) return;

        // Clear loading placeholder
        container.innerHTML = '';

        if (this.sessions.length === 0) {
            this.renderEmptyState(container);
            return;
        }

        // Render table
        container.innerHTML = this.renderSessionsTable();

        // Add event listeners for action buttons
        this.attachEventListeners(container);
    }

    renderSessionsTable() {
        const tableRows = this.sessions.map(session => this.renderTableRow(session)).join('');

        return `
            <div class="sessions-table-container">
                <table class="sessions-table">
                    <thead>
                        <tr>
                            <th class="date-col">Date</th>
                            <th class="baseline-col">Baseline</th>
                            <th class="revised-col">Revised</th>
                            <th class="changes-col">Changes</th>
                            <th class="status-col">Status</th>
                            <th class="actions-col">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderTableRow(session) {
        const createdAt = Utils.formatRelativeTime(session.created_at);
        const absoluteDate = new Date(session.created_at).toLocaleString();
        const status = this.getSessionStatus(session);
        const statusClass = this.getStatusClass(session);
        const baselineFilename = this.truncateFilename(session.baseline_filename || 'N/A');
        const revisedFilename = this.truncateFilename(session.revised_filename || 'N/A');
        const changesText = this.getChangesText(session);

        return `
            <tr class="session-row" data-session-id="${session.id}">
                <td class="date-col" title="${absoluteDate}">${createdAt}</td>
                <td class="baseline-col" title="${session.baseline_filename || 'N/A'}">${baselineFilename}</td>
                <td class="revised-col" title="${session.revised_filename || 'N/A'}">${revisedFilename}</td>
                <td class="changes-col">${changesText}</td>
                <td class="status-col">
                    <span class="status-badge ${statusClass}">${status}</span>
                </td>
                <td class="actions-col">
                    <button class="action-btn view-btn" data-action="view" data-session-id="${session.id}" title="View Results">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                    </button>
                    <button class="action-btn delete-btn" data-action="delete" data-session-id="${session.id}" title="Delete Session">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3,6 5,6 21,6"></polyline>
                            <path d="m19,6v14a2,2 0,0 1,-2,2H7a2,2 0,0 1,-2,-2V6m3,0V4a2,2 0,0 1,2,-2h4a2,2 0,0 1,2,2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                    </button>
                </td>
            </tr>
        `;
    }

    renderEmptyState(container) {
        container.innerHTML = `
            <div class="empty-comparisons">
                <div class="empty-comparisons-icon">📋</div>
                <h3>No Recent Comparisons</h3>
                <p>Start by uploading your first set of drawings to compare.</p>
            </div>
        `;
    }

    getSessionStatus(session) {
        if (session.status === 'completed') {
            return 'Completed';
        } else if (session.status === 'processing') {
            return 'Processing...';
        } else if (session.status === 'failed') {
            return 'Failed';
        } else {
            return 'In Progress';
        }
    }

    getStatusClass(session) {
        switch (session.status) {
            case 'completed':
                return 'status-completed';
            case 'processing':
                return 'status-processing';
            case 'failed':
                return 'status-failed';
            default:
                return 'status-in-progress';
        }
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        } else if (seconds < 3600) {
            return `${Math.round(seconds / 60)}m`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.round((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    async refresh() {
        const container = document.getElementById('recent-comparisons-list');
        if (container) {
            container.innerHTML = `
                <div class="loading-placeholder" style="text-align: center; padding: 40px;">
                    <div class="spinner"></div>
                    <p style="color: #64748b;">Loading recent comparisons...</p>
                </div>
            `;
        }

        await this.loadRecentSessions();
        this.renderSessions();
    }

    // Method to add a new session to the list (when a new comparison completes)
    addSession(session) {
        this.sessions.unshift(session); // Add to beginning

        // Limit to 10 most recent sessions
        if (this.sessions.length > 10) {
            this.sessions = this.sessions.slice(0, 10);
        }

        this.renderSessions();
    }

    // Method to update session status (when processing completes)
    updateSessionStatus(sessionId, status, additionalData = {}) {
        const sessionIndex = this.sessions.findIndex(s => s.id === sessionId);
        if (sessionIndex !== -1) {
            this.sessions[sessionIndex] = {
                ...this.sessions[sessionIndex],
                status,
                ...additionalData
            };
            this.renderSessions();
        }
    }

    // Event listener attachment
    attachEventListeners(container) {
        container.addEventListener('click', (e) => {
            const button = e.target.closest('.action-btn');
            if (!button) return;

            const action = button.dataset.action;
            const sessionId = button.dataset.sessionId;

            if (action === 'view') {
                this.viewSession(sessionId);
            } else if (action === 'delete') {
                this.confirmDeleteSession(sessionId);
            }
        });
    }

    // Helper methods for table rendering
    truncateFilename(filename, maxLength = 20) {
        if (!filename || filename === 'N/A') return filename;
        if (filename.length <= maxLength) return filename;

        const extension = filename.split('.').pop();
        const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'));
        const truncatedName = nameWithoutExt.substring(0, maxLength - extension.length - 4) + '...';
        return truncatedName + '.' + extension;
    }

    getChangesText(session) {
        if (session.status === 'processing') {
            return '<span class="processing-text">Processing...</span>';
        } else if (session.status === 'error' || session.status === 'failed') {
            return '<span class="error-text">Error</span>';
        } else if (session.changes_count > 0) {
            return `<span class="changes-count">${session.changes_count}</span>`;
        } else {
            return '<span class="no-changes">0</span>';
        }
    }

    // Action handlers
    viewSession(sessionId) {
        window.location.href = `/results/${sessionId}`;
    }

    async confirmDeleteSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        const sessionName = session ?
            `${session.baseline_filename || 'Unknown'} vs ${session.revised_filename || 'Unknown'}` :
            'this session';

        if (confirm(`Are you sure you want to delete ${sessionName}? This action cannot be undone.`)) {
            await this.deleteSession(sessionId);
        }
    }

    async deleteSession(sessionId) {
        try {
            // Show loading state
            const row = document.querySelector(`tr[data-session-id="${sessionId}"]`);
            if (row) {
                row.style.opacity = '0.5';
                const deleteBtn = row.querySelector('.delete-btn');
                if (deleteBtn) {
                    deleteBtn.disabled = true;
                    deleteBtn.innerHTML = '<span class="spinner-small"></span>';
                }
            }

            await apiClient.deleteSession(sessionId);

            // Remove session from local array
            this.sessions = this.sessions.filter(s => s.id !== sessionId);

            // Re-render table
            this.renderSessions();

            console.log(`Session ${sessionId} deleted successfully`);

        } catch (error) {
            console.error('Failed to delete session:', error);

            // Restore row state
            const row = document.querySelector(`tr[data-session-id="${sessionId}"]`);
            if (row) {
                row.style.opacity = '1';
                const deleteBtn = row.querySelector('.delete-btn');
                if (deleteBtn) {
                    deleteBtn.disabled = false;
                    deleteBtn.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3,6 5,6 21,6"></polyline>
                            <path d="m19,6v14a2,2 0,0 1,-2,2H7a2,2 0,0 1,-2,-2V6m3,0V4a2,2 0,0 1,2,-2h4a2,2 0,0 1,2,2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                    `;
                }
            }

            alert('Failed to delete session. Please try again.');
        }
    }
}

export default RecentSessions;