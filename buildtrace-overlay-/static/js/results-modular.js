/**
 * Main Results Page Entry Point
 * Loads and initializes the modular results page components
 */

// Import the main ResultsPage module
import ResultsPage from './results/ResultsPage.js';

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    // Get session ID from global variable (set by the template)
    const sessionId = window.sessionId;

    if (!sessionId) {
        console.error('No session ID provided');
        return;
    }

    console.log('Initializing Results Page for session:', sessionId);

    // Create and initialize the results page
    const resultsPage = new ResultsPage(sessionId);

    try {
        await resultsPage.initialize();
        console.log('Results page initialized successfully');
    } catch (error) {
        console.error('Failed to initialize results page:', error);
    }
});