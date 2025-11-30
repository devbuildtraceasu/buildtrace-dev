// BuildTrace AI - Results Page JavaScript

class ResultsPage {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.processingStatus = window.processingStatus || 'unknown';
        this.changes = [];
        this.selectedChangeIndex = null;
        this.chatHistory = [];
        this.suggestedQuestions = [];
        this.drawingComparisons = [];
        this.currentDrawingIndex = null;
        this.currentZoom = 1;
        this.currentViewMode = 'overlay';
        this.panOffset = { x: 0, y: 0 };
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.lastPanOffset = { x: 0, y: 0 };
        this.statusCheckInterval = null;

        this.initializeEventListeners();

        // Check if still processing
        if (this.processingStatus === 'processing') {
            this.showProcessingIndicator();
            this.startStatusPolling();
        } else if (this.processingStatus === 'error') {
            // Show error with retry option immediately
            this.checkSessionStatusAndShowError();
        } else {
            this.loadData();
        }
    }

    initializeEventListeners() {
        // Tab switching
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // View mode switching
        const viewBtns = document.querySelectorAll('.view-btn');
        viewBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchViewMode(e.target.dataset.view));
        });

        // Drawing selector
        const drawingSelector = document.getElementById('drawing-selector');
        if (drawingSelector) {
            drawingSelector.addEventListener('change', (e) => this.selectDrawing(e.target.value));
        }

        // Zoom controls
        document.getElementById('zoom-in')?.addEventListener('click', () => this.zoom(1.2));
        document.getElementById('zoom-out')?.addEventListener('click', () => this.zoom(0.8));
        document.getElementById('zoom-reset')?.addEventListener('click', () => this.resetZoom());


        // Initialize panning
        this.initializePanning();

        // Chat functionality
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-chat');

        if (chatInput) {
            chatInput.addEventListener('input', () => {
                if (sendBtn) {
                    sendBtn.disabled = chatInput.value.trim() === '';
                }
            });

            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey && chatInput.value.trim()) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendChatMessage());
        }
    }

    async loadData() {
        try {
            // Load changes data
            await this.loadChanges();

            // Load drawing comparisons
            await this.loadDrawingComparisons();

            // Load suggested questions
            await this.loadSuggestedQuestions();

            // Load chat history
            await this.loadChatHistory();

        } catch (error) {
            console.error('Error loading data:', error);
            this.showMessage('Error loading data: ' + error.message, 'error');
        }
    }

    async loadDrawingComparisons() {
        try {
            const response = await fetch(`/api/drawings/${this.sessionId}`);
            if (response.ok) {
                const data = await response.json();
                this.drawingComparisons = data.comparisons || [];
                const status = data.status || {};

                this.populateDrawingSelector();
                this.updateDrawingSummary();

                // Auto-select first drawing if available
                if (this.drawingComparisons.length > 0) {
                    // Set the dropdown value
                    const selector = document.getElementById('drawing-selector');
                    if (selector) {
                        selector.value = '0';
                    }
                    // Load the first drawing
                    this.selectDrawing('0');
                } else {
                    // No drawings available - show detailed error message
                    const placeholder = document.querySelector('.no-image-placeholder');
                    if (placeholder) {
                        placeholder.style.display = 'block';

                        let message = '';
                        let icon = '📋';

                        if (status.overlays_created === 0 && status.overlays_failed === 0) {
                            icon = '⚠️';
                            message = `
                                <div class="placeholder-icon">${icon}</div>
                                <p><strong>No Drawing Overlays Generated</strong></p>
                                <p style="font-size: 0.9rem; color: #9ca3af;">
                                    Possible reasons:
                                    <br>• No matching drawings found between old and new PDFs
                                    <br>• Drawing names could not be extracted from PDFs
                                    <br>• PDF processing failed during comparison
                                </p>
                                <p style="font-size: 0.8rem; color: #6b7280; margin-top: 10px;">
                                    Check that your PDFs contain comparable drawings with similar names.
                                </p>
                            `;
                        } else if (status.overlays_failed > 0) {
                            icon = '❌';
                            message = `
                                <div class="placeholder-icon">${icon}</div>
                                <p><strong>Overlay Generation Failed</strong></p>
                                <p style="font-size: 0.9rem; color: #9ca3af;">
                                    ${status.overlays_failed} overlay(s) failed to generate.
                                    ${status.error_message ? '<br>Error: ' + status.error_message : ''}
                                </p>
                            `;
                        } else {
                            message = `
                                <div class="placeholder-icon">${icon}</div>
                                <p>No overlay comparisons available</p>
                                <p style="font-size: 0.9rem; color: #9ca3af;">Processing may still be in progress.</p>
                            `;
                        }

                        placeholder.innerHTML = message;
                    }
                }
            }
        } catch (error) {
            console.error('Error loading drawing comparisons:', error);
            // Show error state
            const placeholder = document.querySelector('.no-image-placeholder');
            if (placeholder) {
                placeholder.style.display = 'block';
                placeholder.innerHTML = `
                    <div class="placeholder-icon">⚠️</div>
                    <p>Error loading drawing comparisons</p>
                `;
            }
        }
    }

    updateDrawingSummary() {
        // Count Added vs Modified drawings based on drawing names
        let addedCount = 0;
        let modifiedCount = 0;

        // Simple heuristic: drawings that appear to be new versions (with common patterns) are "Modified"
        // All others are considered "Added"
        for (const comparison of this.drawingComparisons) {
            const drawingName = comparison.drawing_name || '';

            // Check if this looks like a revision/modification
            // Common patterns: "Rev A", "Rev B", "R1", "R2", "V2", "V3", etc.
            const revisionPatterns = [
                /rev\s*[a-z0-9]/i,    // Rev A, Rev 1, etc.
                /r[0-9]/i,            // R1, R2, etc.
                /v[0-9]/i,            // V1, V2, etc.
                /-[0-9]/,             // -1, -2, etc.
                /\([0-9]\)/,          // (1), (2), etc.
            ];

            const hasRevisionPattern = revisionPatterns.some(pattern => pattern.test(drawingName));

            if (hasRevisionPattern) {
                modifiedCount++;
            } else {
                addedCount++;
            }
        }

        // Update the UI
        const addedElement = document.getElementById('added-drawings-count');
        const modifiedElement = document.getElementById('modified-drawings-count');

        if (addedElement) {
            addedElement.textContent = addedCount;
        }
        if (modifiedElement) {
            modifiedElement.textContent = modifiedCount;
        }
    }

    populateDrawingSelector() {
        const selector = document.getElementById('drawing-selector');
        if (!selector) return;

        // Clear existing options except the first one
        while (selector.options.length > 1) {
            selector.remove(1);
        }

        // Add drawing options
        this.drawingComparisons.forEach((comparison, index) => {
            const option = document.createElement('option');
            option.value = index.toString();
            option.textContent = comparison.drawing_name;
            selector.appendChild(option);
        });
    }

    selectDrawing(indexStr) {
        const index = parseInt(indexStr);
        if (isNaN(index) || index < 0 || index >= this.drawingComparisons.length) {
            return;
        }

        this.currentDrawingIndex = index;
        const comparison = this.drawingComparisons[index];

        // Update current drawing name display
        const drawingNameElement = document.getElementById('current-drawing-name');
        if (drawingNameElement) {
            drawingNameElement.textContent = comparison.drawing_name;
        }

        // Hide placeholder and show the overlay image
        const placeholder = document.querySelector('.no-image-placeholder');
        const overlayImage = document.getElementById('overlay-image');

        if (placeholder) {
            placeholder.style.display = 'none';
        }

        if (overlayImage) {
            overlayImage.style.display = 'block';
        }

        // Load images based on current view mode
        this.loadImagesForView(comparison);
    }

    loadImagesForView(comparison) {
        const baseUrl = '';  // URLs from API are already complete

        // Show loading state
        const placeholder = document.querySelector('.no-image-placeholder');
        if (placeholder) {
            placeholder.style.display = 'block';
            placeholder.innerHTML = `
                <div class="placeholder-icon">⏳</div>
                <p>Loading images...</p>
            `;
        }

        // Update overlay image
        const overlayImg = document.getElementById('overlay-image');
        if (overlayImg && comparison.overlay_image) {
            overlayImg.onload = () => {
                // Hide loading state when image loads
                if (placeholder) {
                    placeholder.style.display = 'none';
                }
                overlayImg.style.display = 'block';
            };
            overlayImg.onerror = () => {
                console.error('Failed to load overlay image:', comparison.overlay_image);
                if (placeholder) {
                    placeholder.style.display = 'block';
                    placeholder.innerHTML = `
                        <div class="placeholder-icon">⚠️</div>
                        <p>Failed to load overlay image</p>
                    `;
                }
            };
            // The path from API already contains the full relative path
            overlayImg.src = baseUrl + comparison.overlay_image;
            console.log('Loading overlay image:', overlayImg.src);
        }

        // Update side-by-side images
        const oldImg = document.getElementById('old-image');
        const newImg = document.getElementById('new-image');
        if (oldImg && comparison.old_image) {
            oldImg.src = baseUrl + comparison.old_image;
            console.log('Loading old image:', oldImg.src);
        }
        if (newImg && comparison.new_image) {
            newImg.src = baseUrl + comparison.new_image;
            console.log('Loading new image:', newImg.src);
        }


        // Reset zoom when loading new images
        this.resetZoom();
    }

    switchViewMode(mode) {
        // Update buttons
        const viewBtns = document.querySelectorAll('.view-btn');
        viewBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });

        // Update view modes
        const viewModes = document.querySelectorAll('.view-mode');
        viewModes.forEach(viewMode => {
            viewMode.classList.remove('active');
        });

        const targetView = document.getElementById(`${mode}-view`);
        if (targetView) {
            targetView.classList.add('active');
        }

        this.currentViewMode = mode;

        // Reset zoom when switching modes
        this.resetZoom();
    }

    zoom(factor) {
        this.currentZoom *= factor;
        this.currentZoom = Math.max(0.5, Math.min(3, this.currentZoom));
        this.applyZoom();
    }

    resetZoom() {
        this.currentZoom = 1;
        this.panOffset = { x: 0, y: 0 };
        this.applyZoom();
    }

    applyZoom() {
        const zoomLevel = document.getElementById('zoom-level');
        if (zoomLevel) {
            zoomLevel.textContent = `${Math.round(this.currentZoom * 100)}%`;
        }

        // Apply zoom and pan to all visible images
        this.applyTransform();
    }

    applyTransform() {
        // Apply panning to image wrappers
        const wrappers = document.querySelectorAll('.view-mode.active .image-wrapper');
        wrappers.forEach(wrapper => {
            wrapper.style.transform = `translate(${this.panOffset.x}px, ${this.panOffset.y}px)`;
        });

        // Apply zoom to images
        const images = document.querySelectorAll('.view-mode.active img');
        images.forEach(img => {
            img.style.transform = `scale(${this.currentZoom})`;
            img.style.transformOrigin = 'center';
        });
    }


    initializePanning() {
        // Add event listeners to all image containers
        const imageContainers = document.querySelectorAll('.image-container');
        imageContainers.forEach(container => {
            this.addPanningToContainer(container);
            this.addScrollZoomToContainer(container);
        });
    }

    addPanningToContainer(container) {
        let startPan = { x: 0, y: 0 };
        let currentPan = { x: 0, y: 0 };
        let isDragging = false;

        const startDrag = (e) => {
            // Only start dragging if not on a button or control
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                return;
            }

            isDragging = true;
            container.style.cursor = 'grabbing';

            const clientX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
            const clientY = e.clientY || (e.touches && e.touches[0].clientY) || 0;

            startPan = {
                x: clientX - this.panOffset.x,
                y: clientY - this.panOffset.y
            };

            e.preventDefault();
        };

        const doDrag = (e) => {
            if (!isDragging) return;

            const clientX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
            const clientY = e.clientY || (e.touches && e.touches[0].clientY) || 0;

            this.panOffset = {
                x: clientX - startPan.x,
                y: clientY - startPan.y
            };

            this.applyTransform();
            e.preventDefault();
        };

        const endDrag = () => {
            if (isDragging) {
                isDragging = false;
                container.style.cursor = 'grab';
            }
        };

        // Mouse events
        container.addEventListener('mousedown', startDrag);
        document.addEventListener('mousemove', doDrag);
        document.addEventListener('mouseup', endDrag);
        document.addEventListener('mouseleave', endDrag);

        // Touch events
        container.addEventListener('touchstart', startDrag, { passive: false });
        document.addEventListener('touchmove', doDrag, { passive: false });
        document.addEventListener('touchend', endDrag);
        document.addEventListener('touchcancel', endDrag);

        // Prevent context menu on right click
        container.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
    }

    addScrollZoomToContainer(container) {
        container.addEventListener('wheel', (e) => {
            // Prevent default scroll behavior
            e.preventDefault();

            // Check if it's a pinch gesture (Ctrl key is pressed on trackpad pinch)
            const isPinch = e.ctrlKey || e.metaKey;

            // Determine zoom direction and speed
            const delta = e.deltaY;
            const zoomSpeed = isPinch ? 0.01 : 0.002; // More sensitive for pinch gestures

            // Calculate zoom factor
            let zoomFactor = 1;
            if (delta < 0) {
                // Scrolling up or pinching out - zoom in
                zoomFactor = 1 + Math.abs(delta) * zoomSpeed;
            } else {
                // Scrolling down or pinching in - zoom out
                zoomFactor = 1 - Math.abs(delta) * zoomSpeed;
            }

            // Get mouse position relative to container for zoom center
            const rect = container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            // Store old zoom for calculating pan offset adjustment
            const oldZoom = this.currentZoom;

            // Apply zoom with limits
            this.currentZoom *= zoomFactor;
            this.currentZoom = Math.max(0.5, Math.min(5, this.currentZoom)); // Allow up to 5x zoom with scroll

            // Calculate zoom center offset to zoom toward mouse position
            if (this.currentZoom !== oldZoom) {
                const zoomRatio = this.currentZoom / oldZoom;

                // Adjust pan offset to zoom toward mouse position
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;

                // Calculate the difference from center to mouse position
                const offsetX = mouseX - centerX;
                const offsetY = mouseY - centerY;

                // Adjust pan to keep the point under the mouse stable
                this.panOffset.x = this.panOffset.x * zoomRatio - offsetX * (zoomRatio - 1);
                this.panOffset.y = this.panOffset.y * zoomRatio - offsetY * (zoomRatio - 1);
            }

            // Apply the transformation
            this.applyTransform();

            // Update zoom display
            const zoomLevel = document.getElementById('zoom-level');
            if (zoomLevel) {
                zoomLevel.textContent = `${Math.round(this.currentZoom * 100)}%`;
            }
        }, { passive: false });
    }

    async loadChanges() {
        try {
            const response = await fetch(`/api/changes/${this.sessionId}`);
            if (!response.ok) {
                throw new Error('Failed to load changes');
            }

            const data = await response.json();
            this.changes = data.changes || [];
            this.renderChangesList();

        } catch (error) {
            console.error('Error loading changes:', error);
            this.showEmptyChanges('Error loading changes data');
        }
    }

    async loadSuggestedQuestions() {
        try {
            const response = await fetch(`/api/chat/${this.sessionId}/suggested`);
            if (response.ok) {
                const data = await response.json();
                this.suggestedQuestions = data.suggestions || [];
                this.renderSuggestedQuestions();
            }
        } catch (error) {
            console.error('Error loading suggested questions:', error);
        }
    }

    async loadChatHistory() {
        try {
            const response = await fetch(`/api/chat/${this.sessionId}/history`);
            if (response.ok) {
                const data = await response.json();
                this.chatHistory = data.history || [];
                this.renderChatHistory();
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    renderChangesList() {
        const changesList = document.getElementById('changes-list');
        if (!changesList) return;

        if (this.changes.length === 0) {
            this.showEmptyChanges('No changes detected in the analysis');
            return;
        }

        changesList.innerHTML = '';

        this.changes.forEach((change, index) => {
            const changeItem = document.createElement('div');
            changeItem.className = 'change-item';
            changeItem.dataset.index = index;

            const detailCount = Array.isArray(change.details) ? change.details.length : 0;

            // Format the description to be more concise
            // Get the critical change content instead of markdown header
            let shortDescription;
            if (change.critical_change && change.critical_change.content) {
                // Use the actual critical change content from restructured data
                shortDescription = change.critical_change.content;
            } else if (change.description) {
                // Fallback to description for database mode
                shortDescription = change.description;
            } else {
                shortDescription = 'Changes detected';
            }

            if (shortDescription.length > 60) {
                shortDescription = shortDescription.substring(0, 57) + '...';
            }

            changeItem.innerHTML = `
                <div class="change-number">${change.drawing_number}:</div>
                <div class="change-description">${shortDescription}</div>
                <div class="change-details-count">${detailCount} changes</div>
            `;

            changeItem.addEventListener('click', () => this.selectChange(index));
            changesList.appendChild(changeItem);
        });

        // Auto-select first change
        if (this.changes.length > 0) {
            this.selectChange(0);
        }
    }

    selectChange(index) {
        if (index < 0 || index >= this.changes.length) return;

        // Update UI selection
        const changeItems = document.querySelectorAll('.change-item');
        changeItems.forEach((item, i) => {
            item.classList.toggle('active', i === index);
        });

        this.selectedChangeIndex = index;
        const selectedChange = this.changes[index];
        this.renderChangeDetails(selectedChange);

        // Find and select the corresponding drawing
        const drawingNumber = selectedChange.drawing_number;
        if (drawingNumber) {
            // Find the index of the drawing that matches this drawing number
            const drawingIndex = this.drawingComparisons.findIndex(
                comparison => comparison.drawing_name === drawingNumber
            );

            if (drawingIndex !== -1) {
                // Select the drawing in the viewer
                this.selectDrawing(drawingIndex.toString());

                // Update the dropdown selector to match
                const selector = document.getElementById('drawing-selector');
                if (selector) {
                    selector.value = drawingIndex.toString();
                }

                // Add a temporary indicator to show the sync
                this.showSyncIndicator(drawingNumber);

                // Smooth scroll to the drawing viewer section
                const viewerSection = document.querySelector('.comparison-viewer');
                if (viewerSection) {
                    viewerSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        }
    }

    renderChangeDetails(change) {
        const detailsTitle = document.getElementById('details-title');
        const detailsContent = document.getElementById('details-content');

        if (!detailsTitle || !detailsContent) return;

        detailsTitle.textContent = `${change.drawing_number} - Change Details`;

        // Parse details - handle both arrays and JSON strings
        let details = [];
        if (Array.isArray(change.details)) {
            details = change.details;
        } else if (typeof change.details === 'string') {
            try {
                const parsed = JSON.parse(change.details);
                details = Array.isArray(parsed) ? parsed : [change.details];
            } catch (e) {
                details = [change.details];
            }
        }

        // Parse recommendations - handle both arrays and JSON strings
        let recommendations = [];
        if (Array.isArray(change.recommendations)) {
            recommendations = change.recommendations;
        } else if (typeof change.recommendations === 'string') {
            try {
                const parsed = JSON.parse(change.recommendations);
                recommendations = Array.isArray(parsed) ? parsed : [change.recommendations];
            } catch (e) {
                recommendations = [change.recommendations];
            }
        }

        detailsContent.innerHTML = `
            ${details.length > 0 ? `
                <div class="change-details">
                    <h4>🔍 Detected Changes</h4>
                    <div class="changes-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Change Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${details.map((detail, index) => `
                                    <tr>
                                        <td class="change-number">${index + 1}</td>
                                        <td class="change-description">${this.formatChangeDetail(detail)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : `
                <div class="no-changes">
                    <p>🔍 No specific changes detected</p>
                </div>
            `}

            ${recommendations.length > 0 ? `
                <div class="change-recommendations">
                    <h4>💡 Recommendations</h4>
                    <div class="recommendations-list">
                        ${recommendations.map((rec, index) => `
                            <div class="recommendation-item">
                                <span class="rec-number">${index + 1}</span>
                                <span class="rec-text">${this.formatRecommendation(rec)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}

            <div class="related-drawings">
                <h4>📐 Related Drawings</h4>
                <div class="drawing-badge">
                    <span class="drawing-number">${change.drawing_number}</span>
                </div>
            </div>
        `;
    }

    formatChangeDetail(detail) {
        if (!detail) return 'No details available';

        // Clean up markdown formatting and make it more readable
        let formatted = detail.toString()
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
            .replace(/- \*\*Impact\*\*:/g, '<br><strong>Impact:</strong>') // Impact formatting
            .replace(/- \*\*Timeline\*\*:/g, '<br><strong>Timeline:</strong>') // Timeline formatting
            .replace(/- \*\*Cost\*\*:/g, '<br><strong>Cost:</strong>') // Cost formatting
            .replace(/- \*\*Labor\*\*:/g, '<br><strong>Labor:</strong>'); // Labor formatting

        // Remove leading dashes and clean up
        formatted = formatted.replace(/^[\-\•]\s*/, '').trim();

        return formatted;
    }

    formatRecommendation(rec) {
        if (!rec) return 'No recommendation available';

        // Format recommendations with better styling
        let formatted = rec.toString()
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
            .replace(/^[\-\•]\s*/, '') // Remove leading bullets
            .trim();

        return formatted;
    }

    showEmptyChanges(message) {
        const changesList = document.getElementById('changes-list');
        if (!changesList) return;

        changesList.innerHTML = `
            <div class="placeholder">
                <div class="placeholder-icon">📋</div>
                <p>${message}</p>
            </div>
        `;
    }

    switchTab(tabName) {
        // Update tab buttons
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        // If switching to chat tab and no messages, load suggested questions
        if (tabName === 'chat' && this.chatHistory.length === 0) {
            this.renderSuggestedQuestions();
        }
    }

    renderSuggestedQuestions() {
        const suggestedContainer = document.getElementById('suggested-questions');
        if (!suggestedContainer || this.suggestedQuestions.length === 0) return;

        suggestedContainer.innerHTML = `
            <div style="margin-bottom: 8px; font-size: 0.9rem; color: #64748b;">
                Suggested questions:
            </div>
            ${this.suggestedQuestions.map(question =>
                `<div class="question-chip" onclick="window.resultsPage.askQuestion('${question.replace(/'/g, "\\'")}')">${question}</div>`
            ).join('')}
        `;
    }

    renderChatHistory() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        // Keep the welcome message if no history
        if (this.chatHistory.length === 0) return;

        // Clear and render all messages
        chatMessages.innerHTML = `
            <div class="assistant-message">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <p>Hello! I'm your BuildTrace AI Assistant. I can help you with:</p>
                    <ul>
                        <li>Cost estimation for your detected changes</li>
                        <li>Project scheduling and timeline planning</li>
                        <li>Permit and regulatory requirements</li>
                        <li>Material specifications and procurement</li>
                        <li>Construction best practices and safety</li>
                    </ul>
                    <p>What would you like to know about your project?</p>
                </div>
            </div>
        `;

        this.chatHistory.forEach(message => {
            if (message.role === 'user' || message.role === 'assistant') {
                this.appendChatMessage(message.role, message.content, false);
            }
        });

        this.scrollChatToBottom();
    }

    askQuestion(question) {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value = question;
            chatInput.focus();

            // Enable send button
            const sendBtn = document.getElementById('send-chat');
            if (sendBtn) {
                sendBtn.disabled = false;
            }
        }
    }

    async sendChatMessage() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-chat');

        if (!chatInput || !sendBtn) return;

        const message = chatInput.value.trim();
        if (!message) return;

        // Disable input while processing
        chatInput.disabled = true;
        sendBtn.disabled = true;

        try {
            // Add user message to UI
            this.appendChatMessage('user', message);

            // Clear input
            chatInput.value = '';

            // Hide suggested questions
            const suggestedContainer = document.getElementById('suggested-questions');
            if (suggestedContainer) {
                suggestedContainer.style.display = 'none';
            }

            // Show typing indicator
            this.showTypingIndicator();

            // Send to backend
            const response = await fetch(`/api/chat/${this.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to send message');
            }

            const data = await response.json();

            // Remove typing indicator
            this.hideTypingIndicator();

            // Add assistant response
            this.appendChatMessage('assistant', data.response);

        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            this.appendChatMessage('assistant', 'I apologize, but I encountered an error. Please try again.');
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    appendChatMessage(role, content, scroll = true) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `${role}-message`;

        const avatar = role === 'user' ? '👤' : '🤖';

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                ${this.formatMessage(content)}
            </div>
        `;

        chatMessages.appendChild(messageDiv);

        if (scroll) {
            this.scrollChatToBottom();
        }
    }

    formatMessage(content) {
        // Convert simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
            .replace(/- (.*?)(\n|$)/g, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'assistant-message typing-indicator';
        typingDiv.id = 'typing-indicator';

        typingDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        chatMessages.appendChild(typingDiv);
        this.scrollChatToBottom();

        // Add CSS for typing animation if not already added
        if (!document.getElementById('typing-animation-css')) {
            const style = document.createElement('style');
            style.id = 'typing-animation-css';
            style.textContent = `
                .typing-dots {
                    display: flex;
                    gap: 4px;
                    padding: 8px 0;
                }
                .typing-dots span {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: #9ca3af;
                    animation: typing 1.4s infinite ease-in-out;
                }
                .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
                .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
                @keyframes typing {
                    0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
                    40% { opacity: 1; transform: scale(1); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollChatToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    showSyncIndicator(drawingNumber) {
        // Remove any existing indicator
        const existingIndicator = document.querySelector('.sync-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        // Add indicator next to the current drawing name
        const drawingNameElement = document.getElementById('current-drawing-name');
        if (drawingNameElement) {
            const indicator = document.createElement('span');
            indicator.className = 'sync-indicator';
            indicator.textContent = 'Linked from Changes';
            drawingNameElement.parentNode.appendChild(indicator);

            // Remove the indicator after animation completes
            setTimeout(() => {
                indicator.remove();
            }, 3000);
        }
    }

    showMessage(message, type = 'info') {
        // Create and show message (similar to app.js implementation)
        const existingMessages = document.querySelectorAll('.message');
        existingMessages.forEach(msg => msg.remove());

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;

        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(messageDiv, container.firstChild);

            setTimeout(() => {
                messageDiv.remove();
            }, 5000);
        }
    }

    showProcessingIndicator() {
        // Show processing overlay on the main content area
        const changesPanel = document.querySelector('.changes-panel');
        const detailsPanel = document.querySelector('.details-panel');

        if (changesPanel) {
            changesPanel.innerHTML = `
                <h3>Processing Drawings...</h3>
                <div class="processing-indicator">
                    <div class="spinner"></div>
                    <p>Analyzing drawings and generating comparisons...</p>
                    <div class="processing-status" id="processing-status-live">Initializing...</div>
                </div>
            `;
        }

        if (detailsPanel) {
            const detailsContent = detailsPanel.querySelector('#details-content');
            if (detailsContent) {
                detailsContent.innerHTML = `
                    <div class="processing-placeholder">
                        <div class="spinner"></div>
                        <h4>Processing in Progress</h4>
                        <p>Your drawings are being analyzed. Results will appear here automatically when ready.</p>
                    </div>
                `;
            }
        }

        // Hide viewer initially during processing
        const viewerContent = document.getElementById('viewer-content');
        if (viewerContent) {
            viewerContent.style.opacity = '0.5';
            viewerContent.style.pointerEvents = 'none';
        }
    }

    startStatusPolling() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }

        this.statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/session/${this.sessionId}/status`);
                if (!response.ok) return;

                const status = await response.json();

                // Update processing status message
                const statusElement = document.getElementById('processing-status-live');
                if (statusElement) {
                    let statusMessage = 'Processing...';
                    if (status.message) {
                        statusMessage = status.message;
                    } else if (status.status === 'processing') {
                        statusMessage = 'Analyzing drawings and generating overlays...';
                    }
                    statusElement.textContent = statusMessage;
                }

                // Check if processing is complete
                if (status.status === 'completed') {
                    clearInterval(this.statusCheckInterval);
                    this.hideProcessingIndicator();
                    await this.loadData(); // Load the actual results
                } else if (status.status === 'error') {
                    clearInterval(this.statusCheckInterval);
                    this.showProcessingError(status.error || 'Processing failed');
                }
            } catch (error) {
                console.warn('Status polling error:', error);
                // Continue polling on network errors
            }
        }, 5000); // Poll every 5 seconds
    }

    hideProcessingIndicator() {
        // Re-enable viewer
        const viewerContent = document.getElementById('viewer-content');
        if (viewerContent) {
            viewerContent.style.opacity = '1';
            viewerContent.style.pointerEvents = 'auto';
        }

        // Clear the processing indicator - the loadData() call will populate with real content
    }

    showProcessingError(errorMessage) {
        const changesPanel = document.querySelector('.changes-panel');
        if (changesPanel) {
            changesPanel.innerHTML = `
                <h3>Processing Failed</h3>
                <div class="error-indicator">
                    <div class="error-icon">❌</div>
                    <p>Sorry, there was an error processing your drawings:</p>
                    <div class="error-message">${errorMessage}</div>
                    <div class="retry-actions">
                        <button onclick="window.resultsPage.retrySession()" class="retry-btn">
                            🔄 Retry Processing
                        </button>
                        <button onclick="window.location.href='/'" class="new-comparison-btn">
                            ➕ New Comparison
                        </button>
                    </div>
                </div>
            `;
        }
    }

    async checkSessionStatusAndShowError() {
        try {
            // Get current session status to show appropriate error message
            const response = await fetch(`/api/session/${this.sessionId}/status`);
            if (response.ok) {
                const status = await response.json();
                if (status.status === 'error') {
                    const errorMessage = status.error || 'Unknown error occurred during processing';
                    this.showProcessingError(errorMessage);
                } else {
                    // If not actually an error, try loading data
                    this.loadData();
                }
            } else {
                this.showProcessingError('Failed to load session status');
            }
        } catch (error) {
            console.error('Error checking session status:', error);
            this.showProcessingError('Failed to load session information');
        }
    }

    async retrySession() {
        try {
            // Show loading state
            const retryBtn = document.querySelector('.retry-btn');
            if (retryBtn) {
                retryBtn.innerHTML = '<span class="spinner-small"></span> Retrying...';
                retryBtn.disabled = true;
            }

            // Call retry endpoint
            const response = await fetch(`/api/session/${this.sessionId}/retry`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to retry session');
            }

            const result = await response.json();

            // Show success message and start polling
            this.showProcessingIndicator();
            this.startStatusPolling();

        } catch (error) {
            console.error('Retry error:', error);

            // Reset button state
            const retryBtn = document.querySelector('.retry-btn');
            if (retryBtn) {
                retryBtn.innerHTML = '🔄 Retry Processing';
                retryBtn.disabled = false;
            }

            // Show error message
            alert(`Failed to retry: ${error.message}`);
        }
    }
}

// Global functions
function openFolder(folderPath) {
    // In a real implementation, this might open the folder in a file explorer
    // For now, we'll just show an alert
    alert(`Opening folder: ${folderPath}`);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Get session ID from the page (set by the template)
    const sessionId = window.sessionId || document.body.dataset.sessionId;
    if (sessionId) {
        window.resultsPage = new ResultsPage(sessionId);
    } else {
        console.error('No session ID found');
    }
});