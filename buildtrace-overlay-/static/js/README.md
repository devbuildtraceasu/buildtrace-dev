# BuildTrace JavaScript Modular Architecture

This document describes the modular JavaScript architecture for the BuildTrace application.

## Overview

The BuildTrace application has been refactored from monolithic JavaScript files into a clean, modular ES6 architecture. This improves maintainability, testability, and code organization.

## Architecture

### Directory Structure

```
static/js/
├── modules/
│   ├── shared/          # Shared utilities and services
│   │   ├── ApiClient.js # Centralized API communication
│   │   └── Utils.js     # Common utility functions
│   ├── app/             # Upload page modules
│   │   ├── FileUploadManager.js   # File upload handling
│   │   ├── ProcessingWorkflow.js  # Processing workflow management
│   │   └── UIStateManager.js      # UI state management
│   └── results/         # Results page modules
│       ├── ImageViewer.js      # Image viewing functionality
│       ├── DrawingManager.js   # Drawing data management
│       ├── ChangesAnalyzer.js  # Change detection analysis
│       └── ChatInterface.js    # AI chat functionality
├── AppController.js     # Main controller for upload page
├── ResultsController.js # Main controller for results page
├── main.js             # ES6 module loader
├── app.js              # Legacy app script (preserved)
├── results.js          # Legacy results script (preserved)
└── README.md           # This documentation
```

## Module Descriptions

### Shared Modules

#### ApiClient.js
- Centralized API communication
- Standardized error handling
- Support for JSON and FormData requests
- Upload progress tracking

#### Utils.js
- Common utility functions
- File validation
- UI helpers
- Date formatting
- Message display

### App Page Modules

#### FileUploadManager.js
- Handles drag-and-drop file uploads
- File validation (type, size)
- UI updates for file selection
- File removal functionality

#### ProcessingWorkflow.js
- Manages the file processing pipeline
- Handles upload and processing steps
- Progress tracking and status updates
- Error handling and recovery

#### UIStateManager.js
- Manages UI state transitions
- Step progression visualization
- Button state management
- Processing UI display

### Results Page Modules

#### ImageViewer.js
- Advanced image viewing functionality
- Zoom and pan controls
- View mode switching (overlay/side-by-side)
- Mouse and touch interactions

#### DrawingManager.js
- Drawing comparison data management
- Drawing selection and navigation
- Summary calculations
- Drawing filtering and search

#### ChangesAnalyzer.js
- Change detection data handling
- Change filtering and categorization
- Detailed change analysis
- Integration with drawing viewer

#### ChatInterface.js
- AI chat functionality
- Message history management
- Suggested questions
- Real-time typing indicators

## Controllers

### AppController.js
Main controller for the upload page that coordinates:
- File upload management
- Processing workflow
- UI state updates
- Recent comparisons display

### ResultsController.js
Main controller for the results page that coordinates:
- Image viewing
- Drawing management
- Changes analysis
- Chat interface
- Tab navigation

## Module Loader

### main.js
ES6 module loader that:
- Detects browser ES6 module support
- Identifies current page type
- Loads appropriate controller
- Provides fallback for legacy browsers

## Usage

### For Modern Browsers (ES6 Modules)

```html
<!DOCTYPE html>
<html>
<head>
    <title>BuildTrace</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body class="app-page">
    <!-- Page content -->

    <!-- Load modular system -->
    <script type="module" src="/static/js/main.js"></script>

    <!-- Fallback for older browsers -->
    <script nomodule src="/static/js/app.js"></script>
</body>
</html>
```

### Legacy Browser Support

The system automatically falls back to the original monolithic scripts for browsers that don't support ES6 modules.

## Benefits

### Modularity
- Each module has a single responsibility
- Clear separation of concerns
- Easy to understand and maintain

### Reusability
- Shared modules can be used across pages
- Components can be easily extracted for other projects
- Consistent API patterns

### Testability
- Individual modules can be unit tested
- Mock dependencies easily
- Isolated functionality testing

### Performance
- Only load required modules
- Better caching strategies
- Reduced bundle sizes

### Maintainability
- Easier to locate and fix bugs
- Clear dependency relationships
- Consistent code patterns

## Development Guidelines

### Adding New Modules

1. Create module in appropriate directory
2. Export a class or utility object
3. Use ES6 import/export syntax
4. Follow existing naming conventions
5. Update controller to integrate module

### Module Communication

- Use callbacks for event communication
- Pass data through method parameters
- Avoid global state when possible
- Use the controller as coordination layer

### Error Handling

- Handle errors within modules
- Propagate errors to controllers
- Use consistent error messaging
- Provide user feedback through Utils.showMessage

### Backward Compatibility

- Legacy scripts are preserved
- Automatic fallback for unsupported browsers
- Gradual migration strategy supported

## Browser Support

### ES6 Modules Supported
- Chrome 61+
- Firefox 60+
- Safari 10.1+
- Edge 16+

### Legacy Fallback
- Internet Explorer 11
- Older Chrome/Firefox versions
- Any browser without module support

## Future Enhancements

- TypeScript migration
- Unit testing framework
- Webpack bundling
- Service worker integration
- Progressive Web App features

## Migration from Legacy Code

The original functionality has been preserved while improving organization:
- All existing features maintained
- Same API endpoints used
- Identical user experience
- Enhanced error handling
- Better performance monitoring

## Troubleshooting

### Module Loading Issues
1. Check browser developer console for errors
2. Verify file paths are correct
3. Ensure server serves .js files with correct MIME type
4. Test with module support detection

### Legacy Fallback Problems
1. Verify legacy scripts exist
2. Check nomodule attribute support
3. Test in targeted browsers
4. Review console for script loading errors

For more information or issues, please refer to the main BuildTrace documentation.