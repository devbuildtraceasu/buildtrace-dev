# BuildTrace Frontend

A modern Next.js frontend for the BuildTrace AI drawing comparison platform, reorganized from raw JavaScript into a modular, TypeScript-based application.

## Features

- 🔐 **Authentication System** - Login/signup with email or Google OAuth
- 📤 **File Upload** - Drag & drop interface for drawing files (PDF, DWG, DXF, PNG, JPG)
- 🔄 **Processing Monitor** - Real-time feedback during file processing
- 🖼️ **Drawing Viewer** - Interactive overlay and side-by-side comparison views
- 📋 **Changes Analysis** - Detailed list of detected changes with AI insights
- 💬 **AI Assistant** - Chat interface for cost, scheduling, and construction questions
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile devices

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Forms**: React Hook Form
- **HTTP Client**: Axios
- **UI Components**: Custom components with Lucide React icons
- **Notifications**: React Hot Toast

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page (redirects to upload)
│   ├── login/             # Login page
│   ├── signup/            # Signup page
│   └── results/[sessionId]/ # Results page
├── components/
│   ├── layout/            # Layout components (Header, etc.)
│   ├── pages/             # Page-level components
│   ├── results/           # Results page components
│   │   ├── DrawingViewer.tsx
│   │   ├── ChangesList.tsx
│   │   ├── ChatAssistant.tsx
│   │   └── ResultsOverview.tsx
│   ├── upload/            # Upload page components
│   │   ├── FileUploader.tsx
│   │   ├── ProcessingMonitor.tsx
│   │   ├── RecentSessions.tsx
│   │   └── ProgressSteps.tsx
│   ├── ui/                # Reusable UI components
│   └── providers/         # Context providers
├── lib/                   # Utilities and configurations
│   └── api.ts            # API client
├── store/                 # Zustand stores
│   └── authStore.ts      # Authentication state
└── types/                # TypeScript type definitions
    └── index.ts
```

## Component Architecture

### Page Structure

- **Login Page** (`/login`) - Authentication with email/password or Google OAuth
- **Upload Page** (`/`) - Main interface for uploading drawing pairs
- **Results Page** (`/results/[sessionId]`) - Analysis results with multiple views

### Modular Components

#### Upload Flow
- `FileUploader` - Drag & drop file upload with validation
- `ProgressSteps` - Visual progress indicator
- `ProcessingMonitor` - Real-time processing status
- `RecentSessions` - Table of previous comparisons

#### Results Flow
- `DrawingViewer` - Interactive image viewer with zoom/pan controls
- `ChangesList` - Categorized list of detected changes
- `ChatAssistant` - AI-powered Q&A interface
- `ResultsOverview` - Summary statistics and metrics

### UI Components
- `Button` - Styled button with loading states
- `Input` - Form input with error handling
- `Card` - Container component with consistent styling
- `LoadingSpinner` - Reusable loading indicator

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Running BuildTrace backend API

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.local.example .env.local
```

4. The `.env.local` is already configured to use the deployed Cloud Run backend:
```bash
# Uses your production Cloud Run service with real database & storage
NEXT_PUBLIC_API_URL=https://buildtrace-overlay-lioa4ql2nq-uc.a.run.app
```

5. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000` and will connect to your **production backend** with:
- **Cloud SQL PostgreSQL** database with real data
- **Google Cloud Storage** for file storage
- **Cloud Run** backend service
- **AI analysis** with OpenAI integration

### Build for Production

```bash
npm run build
npm start
```

## API Integration

The frontend communicates with the BuildTrace backend through a centralized API client (`src/lib/api.ts`) that handles:

- Authentication (login, logout, signup)
- File uploads with progress tracking
- Session management
- Drawing and analysis data retrieval
- Chat functionality

### Key API Endpoints

- `POST /auth/login` - User authentication
- `POST /upload` - File upload
- `POST /process/{sessionId}` - Start processing
- `GET /api/drawings/{sessionId}` - Get drawing images
- `GET /api/changes/{sessionId}` - Get change analysis
- `POST /api/chat` - Send chat message

## State Management

### Authentication Store (Zustand)

Manages user authentication state:
- Login/logout functionality
- User profile data
- Authentication status
- Persistent storage

### Component State

Local component state for:
- Form data and validation
- UI interactions (modals, dropdowns)
- File upload progress
- View modes and preferences

## Styling

### Tailwind CSS

Utility-first CSS framework with custom design system:

- **Colors**: Custom BuildTrace color palette
- **Components**: Pre-built component classes
- **Responsive**: Mobile-first responsive design
- **Dark Mode**: Ready for future dark mode support

### Custom CSS Classes

Global component classes in `globals.css`:
- `.btn-primary`, `.btn-secondary` - Button variants
- `.input-field` - Form input styling
- `.card` - Container styling
- `.upload-area` - File upload zones

## Development

### Code Organization

- **Separation of Concerns**: UI components, business logic, and API calls are clearly separated
- **Reusability**: Common UI components are extracted and reusable
- **Type Safety**: Comprehensive TypeScript types for all data structures
- **Error Handling**: Consistent error handling and user feedback

### Best Practices

- **Component Composition**: Small, focused components that compose together
- **Custom Hooks**: Reusable logic extracted into custom hooks
- **Error Boundaries**: Graceful error handling and recovery
- **Accessibility**: ARIA labels and keyboard navigation
- **Performance**: Lazy loading and optimized bundle size

### Development Tools

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Development server with hot reload
npm run dev
```

## Deployment

The frontend is configured for deployment on:

- **Vercel** (recommended for Next.js)
- **Netlify**
- **AWS Amplify**
- **Docker** containers

### Environment Variables

Production deployment requires:
- `NEXT_PUBLIC_API_URL` - Backend API URL
- Additional variables based on features used

## Migration from Original Code

This Next.js application replaces the original JavaScript files:

### Original → New Structure

- `templates/index.html` → `app/page.tsx` (Upload Page)
- `templates/results.html` → `app/results/[sessionId]/page.tsx`
- `templates/auth/login.html` → `app/login/page.tsx`
- `static/js/app-modular.js` → `components/pages/UploadPage.tsx`
- `static/js/results/` → `components/results/`
- `static/js/shared/ApiClient.js` → `lib/api.ts`

### Key Improvements

- **Type Safety**: Full TypeScript support with comprehensive types
- **Component Architecture**: Modular, reusable components
- **State Management**: Centralized state with Zustand
- **Error Handling**: Comprehensive error handling and user feedback
- **Performance**: Optimized bundle size and loading times
- **Developer Experience**: Hot reload, type checking, and modern tooling
- **Maintainability**: Clear separation of concerns and consistent patterns

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for new data structures
3. Include error handling for new API calls
4. Test components on different screen sizes
5. Update this README for significant changes

## Support

For questions about the frontend application, please refer to the main BuildTrace documentation or create an issue in the project repository.