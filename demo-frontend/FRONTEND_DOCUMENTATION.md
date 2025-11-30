# BuildTrace AI - Frontend Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Key Features](#key-features)
6. [Data Flow](#data-flow)
7. [API Integration](#api-integration)
8. [State Management](#state-management)
9. [Component Architecture](#component-architecture)
10. [Routing & Navigation](#routing--navigation)
11. [Authentication](#authentication)
12. [File Upload & Storage](#file-upload--storage)
13. [Comparison Workflow](#comparison-workflow)
14. [PDF Viewer Integration](#pdf-viewer-integration)
15. [Configuration](#configuration)
16. [Development Setup](#development-setup)
17. [Migration to Next.js](#migration-to-nextjs)

---

## Project Overview

BuildTrace AI is a web application for intelligently detecting and analyzing changes between construction drawing versions. The frontend is a React-based single-page application (SPA) that provides:

- **File Upload**: Upload baseline and revised construction drawings (PDF, DWG, DXF, PNG, JPG)
- **AI-Powered Comparison**: Automatic detection of changes between drawing versions
- **Interactive Viewers**: Side-by-side, overlay, and single-view modes for comparing drawings
- **Change Analysis**: Categorized changes (added, modified, removed) with detailed summaries
- **AI Assistant**: Ask questions about detected changes using OpenAI integration

---

## Tech Stack

### Core Framework
- **React 18.3.1**: UI library
- **TypeScript 5.6.3**: Type safety
- **Vite 5.4.19**: Build tool and dev server

### Routing
- **React Router DOM 7.8.1**: Client-side routing

### State Management
- **Zustand 5.0.7**: Lightweight state management for comparison state
- **TanStack Query (React Query) 5.60.5**: Server state management and caching

### UI Framework
- **Tailwind CSS 3.4.17**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives (47+ components)
- **Lucide React**: Icon library
- **Framer Motion 11.13.1**: Animation library

### Backend Integration
- **Express.js**: Node.js server (monorepo structure)
- **Supabase**: Authentication and file storage
- **Drizzle ORM**: Type-safe database queries
- **PostgreSQL**: Database (via Neon or similar)

### PDF Handling
- **pdfjs-dist 5.4.54**: PDF rendering
- **jspdf 3.0.1**: PDF generation
- **html2canvas 1.4.1**: Canvas rendering

### Form Handling
- **React Hook Form 7.55.0**: Form state management
- **Zod 3.24.2**: Schema validation

### Other Libraries
- **date-fns 3.6.0**: Date utilities
- **nanoid 5.1.5**: ID generation
- **recharts 2.15.2**: Charting library

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client (Browser)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   React App  │  │  Zustand     │  │ React Query  │  │
│  │  Components  │  │  Store       │  │  Cache       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │          │
│         └──────────────────┴──────────────────┘         │
│                          │                               │
│                    API Client                            │
│              (apiRequest helper)                         │
└──────────────────────────┼───────────────────────────────┘
                           │
                           │ HTTP/REST
                           │
┌──────────────────────────┼───────────────────────────────┐
│              Express Server (Node.js)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Routes     │  │   Storage    │  │  Auth        │  │
│  │   Handler    │  │   Layer      │  │  Middleware   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │          │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
          │                  │                  │
    ┌─────▼─────┐      ┌─────▼─────┐    ┌─────▼─────┐
    │ PostgreSQL│      │ Supabase  │    │ External  │
    │  Database │      │  Storage   │    │ Compare   │
    │           │      │            │    │   API     │
    └───────────┘      └────────────┘    └───────────┘
```

### Application Structure

The application follows a **feature-based architecture** with clear separation of concerns:

1. **Pages**: Top-level route components
2. **Components**: Reusable UI components organized by domain
3. **Features**: Domain logic, services, and state management
4. **Services**: API integration and business logic
5. **Hooks**: Custom React hooks for shared logic
6. **Lib**: Utilities and client configurations

---

## Project Structure

```
demo-frontend/
├── client/                    # Frontend source code
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── common/        # Shared components
│   │   │   │   ├── KpiTile.tsx
│   │   │   │   ├── RecentComparisonsTable.tsx
│   │   │   │   ├── Stepper.tsx
│   │   │   │   ├── UploadDropzone.tsx
│   │   │   │   └── UploadDropzoneWithAuth.tsx
│   │   │   ├── comparison/   # Comparison-specific components
│   │   │   │   ├── AskPanel.tsx
│   │   │   │   ├── ChangeDetailsPanel.tsx
│   │   │   │   ├── ChangesList.tsx
│   │   │   │   ├── ComparisonToolbar.tsx
│   │   │   │   ├── ComparisonViewers.tsx
│   │   │   │   ├── SummarySection.tsx
│   │   │   │   └── ViewModeToggle.tsx
│   │   │   ├── layout/        # Layout components
│   │   │   │   └── AppLayout.tsx
│   │   │   └── ui/            # shadcn/ui components (47 files)
│   │   ├── features/          # Feature modules
│   │   │   ├── comparison/
│   │   │   │   ├── models.ts
│   │   │   │   ├── services/
│   │   │   │   │   ├── comparisonService.ts
│   │   │   │   │   └── reportService.ts
│   │   │   │   ├── state/
│   │   │   │   │   └── useComparisonStore.ts
│   │   │   │   └── mocks/
│   │   │   ├── recent/
│   │   │   │   ├── models.ts
│   │   │   │   ├── services/
│   │   │   │   │   └── recentService.ts
│   │   │   │   └── state/
│   │   │   │       └── useRecentStore.ts
│   │   │   └── uploads/
│   │   │       └── services/
│   │   │           └── validation.ts
│   │   ├── pages/             # Route pages
│   │   │   ├── home/
│   │   │   │   └── index.tsx
│   │   │   ├── comparison/
│   │   │   │   └── index.tsx
│   │   │   ├── projects/
│   │   │   │   └── index.tsx
│   │   │   ├── Landing.tsx
│   │   │   └── not-found.tsx
│   │   ├── hooks/             # Custom hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useDebounce.ts
│   │   │   ├── useKeyboardShortcuts.ts
│   │   │   ├── use-mobile.tsx
│   │   │   └── use-toast.ts
│   │   ├── lib/               # Utilities
│   │   │   ├── queryClient.ts
│   │   │   ├── supabaseClient.ts
│   │   │   └── utils.ts
│   │   ├── libs/              # Third-party integrations
│   │   │   └── pdf/
│   │   │       ├── PdfService.ts
│   │   │       └── PdfViewer.tsx
│   │   ├── services/          # API services
│   │   │   └── fileUploadService.ts
│   │   ├── styles/            # Global styles
│   │   │   └── tokens.css
│   │   ├── App.tsx            # Root component
│   │   ├── main.tsx           # Entry point
│   │   ├── router.tsx         # Route configuration
│   │   └── index.css          # Global CSS
│   └── index.html
├── server/                     # Express backend
│   ├── index.ts               # Server entry
│   ├── routes.ts              # API routes
│   ├── db.ts                  # Database connection
│   ├── storage.ts             # Data access layer
│   ├── authMiddleware.ts      # Auth middleware
│   ├── supabaseClient.ts      # Supabase server client
│   └── vite.ts                # Vite dev server setup
├── shared/                    # Shared types/schemas
│   └── schema.ts              # Drizzle schema definitions
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── drizzle.config.ts
```

---

## Key Features

### 1. File Upload System
- **Drag-and-drop interface** for file uploads
- **Multiple format support**: PDF, DWG, DXF, PNG, JPG (up to 50MB)
- **Authentication-required uploads** with Supabase JWT
- **File validation** before upload
- **Progress tracking** and error handling

### 2. Comparison Engine
- **Asynchronous processing**: Fire-and-forget comparison requests
- **Polling mechanism**: Automatic result fetching when ready
- **Status tracking**: `pending`, `processing`, `completed`, `failed`
- **Page mapping**: Automatic matching of pages between baseline and revised drawings
- **Drawing number detection**: Auto-detection from filenames

### 3. Interactive Viewers
- **Multiple view modes**:
  - Side-by-side: Baseline and revised drawings side-by-side
  - Overlay: Overlaid comparison view
  - Baseline only: Single baseline view
  - Revised only: Single revised view
- **Synchronized panning and zooming** in side-by-side mode
- **Page-specific viewing** based on drawing codes
- **PDF rendering** using pdfjs-dist

### 4. Change Analysis
- **Categorized changes**:
  - Added: New elements in revised drawing
  - Modified: Changed elements
  - Removed: Elements removed from baseline
- **KPI metrics**: Counts for each change type
- **Detailed change information**: Drawing codes, summaries, descriptions
- **Category tagging**: MEP, Electrical, Structural, etc.

### 5. AI Assistant
- **Follow-up questions** about detected changes
- **OpenAI integration** via backend proxy
- **Thread-based conversations** per drawing code
- **Context-aware responses** based on comparison results

### 6. Recent Comparisons
- **Local storage** for recent comparison history
- **Quick access** to previous comparisons
- **Metadata display**: Drawing numbers, file names, change counts

---

## Data Flow

### Comparison Creation Flow

```
1. User uploads baseline file
   └─> POST /api/files/upload
       └─> File stored in Supabase Storage
       └─> Metadata saved to PostgreSQL
       └─> Returns UploadedFile object

2. User uploads revised file
   └─> POST /api/files/upload
       └─> Same process as baseline

3. User clicks "Compare Drawings"
   └─> POST /api/compare/pdf
       └─> Creates comparison record (status: 'processing')
       └─> Proxies request to external compare API
       └─> Returns comparison_id immediately
       └─> External API processes asynchronously

4. Frontend navigates to /compare/:id
   └─> Polls GET /api/comparisons/:id every 5 seconds
       └─> When status === 'completed', displays results
       └─> Updates Zustand store with comparison data

5. Results include:
   - KPIs (added, modified, removed counts)
   - Changes array/list
   - Page mapping (drawing codes to page indices)
   - Analysis summary
   - OpenAI thread IDs
```

### State Management Flow

```
User Action
    │
    ├─> Component Event Handler
    │       │
    │       ├─> API Call (via apiRequest)
    │       │   └─> Updates React Query cache
    │       │
    │       └─> Zustand Store Update
    │           └─> Triggers component re-render
    │
    └─> Component reads from:
        - Zustand store (comparison state)
        - React Query cache (server data)
        - Component local state (UI state)
```

---

## API Integration

### API Client

The application uses a custom `apiRequest` helper that:
- Automatically includes Supabase JWT token in Authorization header
- Handles errors consistently
- Works with React Query for caching

**Location**: `client/src/lib/queryClient.ts`

```typescript
apiRequest(method: string, url: string, data?: unknown): Promise<Response>
```

### API Endpoints

#### Authentication
- `GET /api/auth/user` - Get current user info

#### File Management
- `POST /api/files/upload` - Upload a file (multipart/form-data)
- `GET /api/files` - List user's uploaded files
- `GET /api/files/:id/download` - Download file (redirects to signed URL)
- `DELETE /api/files/:id` - Delete a file

#### Comparisons
- `POST /api/compare/pdf` - Start a comparison (proxies to external API)
- `GET /api/comparisons` - List user's comparisons
- `GET /api/comparisons/:id` - Get specific comparison
- `GET /api/comparisons/:id/overlay` - Get overlay PDF signed URL
- `POST /api/comparisons` - Create comparison (manual)
- `PATCH /api/comparisons/:id` - Update comparison
- `DELETE /api/comparisons/:id` - Delete comparison

#### AI Assistant
- `POST /api/assistants/followup` - Ask follow-up question about changes

### Request/Response Patterns

**File Upload**:
```typescript
FormData → POST /api/files/upload
Response: { id, userId, fileName, originalName, mimeType, fileSize, ... }
```

**Start Comparison**:
```typescript
POST /api/compare/pdf
Body: {
  baselineFileId: string,
  revisedFileId: string,
  baselineOriginalName?: string,
  revisedOriginalName?: string,
  uploadOutputs?: boolean
}
Response: { comparison_id: string, ... }
```

**Get Comparison**:
```typescript
GET /api/comparisons/:id
Response: {
  id: string,
  status: 'processing' | 'completed' | 'failed',
  kpis: { added: number, modified: number, removed: number },
  changes: ChangesPayload,
  pageMapping: Array<[string, number, number]>,
  pageInfo: { added: number, modified: number, removed: number },
  drawingNumber?: string,
  analysisSummary?: string,
  ...
}
```

---

## State Management

### Zustand Store (Comparison State)

**Location**: `client/src/features/comparison/state/useComparisonStore.ts`

Manages comparison-specific UI state:

```typescript
interface ComparisonState {
  input: ComparisonInput | null;        // Baseline and revised file refs
  result: ComparisonResult | null;      // Comparison results
  viewMode: ViewMode;                    // "side-by-side" | "overlay" | "baseline" | "revised"
  zoom: number;                          // Zoom level (percentage)
  selectedChangeId: string | null;      // Currently selected change
  loading: boolean;                      // Loading state
  error?: string;                        // Error message
  
  // Actions
  setInput: (input: ComparisonInput | null) => void;
  setResult: (result: ComparisonResult | null) => void;
  setViewMode: (mode: ViewMode) => void;
  setZoom: (zoom: number) => void;
  selectChange: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | undefined) => void;
  reset: () => void;
}
```

**Usage**:
```typescript
const { result, viewMode, setViewMode } = useComparisonStore();
```

### React Query (Server State)

**Location**: `client/src/lib/queryClient.ts`

Manages server data caching and synchronization:

- **No automatic refetching**: `refetchOnWindowFocus: false`, `staleTime: Infinity`
- **Manual polling**: Components implement their own polling logic
- **Error handling**: Consistent error handling via `apiRequest`

### Local Storage (Recent Comparisons)

**Location**: `client/src/features/recent/services/recentService.ts`

Stores recent comparison history in browser localStorage.

---

## Component Architecture

### Component Hierarchy

```
App
└─> QueryClientProvider
    └─> TooltipProvider
        └─> Router
            ├─> Landing (unauthenticated)
            └─> AppLayout (authenticated)
                ├─> HomePage
                │   ├─> Stepper
                │   ├─> UploadDropzoneWithAuth (x2)
                │   └─> RecentComparisonsTable
                │
                └─> ComparisonPage
                    ├─> ComparisonToolbar
                    ├─> ViewModeToggle
                    ├─> ComparisonViewers
                    │   └─> PdfViewer (x2 for side-by-side)
                    ├─> SummarySection
                    ├─> ChangesList
                    ├─> ChangeDetailsPanel
                    └─> AskPanel
```

### Key Components

#### 1. **AppLayout** (`components/layout/AppLayout.tsx`)
- Navigation header with logo
- User profile display
- Logout functionality
- Wraps authenticated routes

#### 2. **HomePage** (`pages/home/index.tsx`)
- File upload interface
- Stepper component showing progress
- Compare button
- Recent comparisons table

#### 3. **ComparisonPage** (`pages/comparison/index.tsx`)
- Main comparison results view
- Polls for comparison results
- Manages comparison state
- Renders all comparison sub-components

#### 4. **ComparisonViewers** (`components/comparison/ComparisonViewers.tsx`)
- Renders PDF viewers based on view mode
- Handles synchronized panning/zooming
- Manages overlay PDF polling
- Page mapping resolution

#### 5. **PdfViewer** (`libs/pdf/PdfViewer.tsx`)
- Renders PDF pages using pdfjs-dist
- Handles zoom and pan
- Supports external pan/zoom synchronization
- Page-specific rendering

#### 6. **UploadDropzoneWithAuth** (`components/common/UploadDropzoneWithAuth.tsx`)
- Drag-and-drop file upload
- Authentication-aware
- Progress indication
- File validation

---

## Routing & Navigation

### Route Configuration

**Location**: `client/src/router.tsx`

```typescript
Routes:
  / (Landing) - Unauthenticated landing page with sign in/up
  / (HomePage) - Authenticated home page
  /compare/:id (ComparisonPage) - Comparison results view
  /projects (ProjectsPage) - Projects list (placeholder)
  * (NotFound) - 404 page
```

### Authentication-Based Routing

- **Unauthenticated**: Shows `Landing` page for all routes
- **Authenticated**: Shows `AppLayout` with protected routes

### Navigation Flow

```
Landing Page
    │ (Sign In/Up)
    ▼
Home Page
    │ (Upload files + Compare)
    ▼
Comparison Page (/compare/:id)
    │ (Poll for results)
    ▼
Results Display
```

---

## Authentication

### Authentication Provider

**Supabase Auth** is used for authentication.

**Client Setup**: `client/src/lib/supabaseClient.ts`
**Server Setup**: `server/supabaseClient.ts`

### Authentication Flow

1. **Sign Up/Sign In**: User provides email/password on Landing page
2. **Session Management**: Supabase handles session tokens
3. **JWT Token**: Included in API requests via `Authorization: Bearer <token>` header
4. **Auth Hook**: `useAuth` hook provides authentication state

### Auth Hook

**Location**: `client/src/hooks/useAuth.ts`

```typescript
const { user, isLoading, isAuthenticated } = useAuth();
```

- Monitors Supabase auth state changes
- Provides user object and loading state
- Used by Router to conditionally render routes

### Protected Routes

All API endpoints (except auth) require authentication via `requireAuth` middleware:
- Validates Supabase JWT token
- Extracts user ID from token
- Attaches `req.auth` object to request

---

## File Upload & Storage

### Upload Flow

1. **User selects/drops file** in `UploadDropzoneWithAuth`
2. **File validation** (size, type) before upload
3. **FormData creation** with file blob
4. **POST to `/api/files/upload`** with JWT token
5. **Server processing**:
   - Validates file type and size (50MB limit)
   - Uploads to Supabase Storage bucket `drawings`
   - Stores metadata in PostgreSQL `uploaded_files` table
   - Returns `UploadedFile` object
6. **Frontend updates** with uploaded file info

### File Storage

- **Supabase Storage**: Actual file storage in `drawings` bucket
- **PostgreSQL**: File metadata (id, userId, fileName, originalName, mimeType, fileSize, etc.)
- **Download URLs**: Signed URLs generated on-demand (60-second expiry)

### File Service

**Location**: `client/src/services/fileUploadService.ts`

```typescript
class FileUploadService {
  uploadFile(file: File): Promise<FileUploadResult>
  deleteFile(fileId: string): Promise<boolean>
  getUserFiles(): Promise<UploadedFile[]>
}
```

---

## Comparison Workflow

### Step-by-Step Process

1. **Upload Baseline File**
   - User uploads old/previous drawing version
   - File stored and `baselineFile` state set

2. **Upload Revised File**
   - User uploads new/current drawing version
   - File stored and `revisedFile` state set

3. **Initiate Comparison**
   - User clicks "Compare Drawings"
   - POST `/api/compare/pdf` with both file IDs
   - Comparison record created with `status: 'processing'`
   - External API called asynchronously
   - Frontend navigates to `/compare/:id`

4. **Polling for Results**
   - ComparisonPage polls `GET /api/comparisons/:id` every 5 seconds
   - When `status === 'completed'`, results displayed
   - State updated in Zustand store

5. **Results Display**
   - KPIs shown (added, modified, removed counts)
   - Changes list rendered
   - PDF viewers initialized with page mapping
   - Overlay PDFs polled and displayed when ready

### Comparison Data Structure

```typescript
ComparisonResult {
  id: string;
  drawingNumber?: string;
  autoDetectedDrawingNumber: boolean;
  kpis: {
    added: number;
    modified: number;
    removed: number;
  };
  changes: ChangesPayload | any;
  pageInfo?: {
    added: number;
    modified: number;
    removed: number;
  };
  pageMapping?: Array<[string, number, number]>; // [drawingCode, oldPageIndex, newPageIndex]
  isPartial?: boolean;
}
```

### Page Mapping

Page mapping connects drawing codes (e.g., "A-101") to page indices in baseline and revised PDFs:

```typescript
pageMapping: [
  ["A-101", 0, 0],  // Drawing A-101 is page 0 in old, page 0 in new
  ["E-200", 1, 2],  // Drawing E-200 is page 1 in old, page 2 in new
]
```

Used by `ComparisonViewers` to display correct pages for selected drawing codes.

---

## PDF Viewer Integration

### PDF Service

**Location**: `client/src/libs/pdf/PdfService.ts`

- Preloads PDF files for faster rendering
- Manages PDF document instances
- Uses `pdfjs-dist` for PDF parsing

### PDF Viewer Component

**Location**: `client/src/libs/pdf/PdfViewer.tsx`

**Features**:
- Renders specific PDF page
- Zoom control (percentage-based)
- Pan/scroll support
- External pan/zoom synchronization (for side-by-side mode)
- Canvas-based rendering

**Props**:
```typescript
interface PdfViewerProps {
  fileUrl: string;
  page?: number;              // 1-indexed page number
  scale?: number;             // Zoom percentage
  className?: string;
  onPanChange?: (scrollLeft: number, scrollTop: number) => void;
  externalPanLeft?: number;
  externalPanTop?: number;
  onZoomChange?: (zoom: number) => void;
}
```

### Overlay PDFs

- Generated by external comparison API
- Stored in Supabase Storage under `overlays/{userId}/{comparisonId}/`
- Named as `{oldIdx}_{newIdx}_overlay.pdf`
- Polled by `ComparisonViewers` until available
- Displayed in overlay view mode

---

## Configuration

### Environment Variables

**Client** (Vite):
- `VITE_SUPABASE_URL`: Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Supabase anonymous key

**Server**:
- `DATABASE_URL`: PostgreSQL connection string
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `SUPABASE_ANON_KEY`: Supabase anonymous key (fallback)
- `COMPARE_API_URL`: External comparison API URL (default: `http://localhost:8000/compare/pdf`)
- `PORT`: Server port (default: 5001)
- `NODE_ENV`: Environment (`development` | `production`)

### Build Configuration

**Vite Config** (`vite.config.ts`):
- React plugin
- Path aliases: `@/` → `client/src/`, `@shared/` → `shared/`
- Build output: `dist/public/`

**TypeScript Config** (`tsconfig.json`):
- Strict mode enabled
- Path aliases configured
- ESNext modules
- React JSX preserve

**Tailwind Config** (`tailwind.config.ts`):
- Content paths: `client/index.html`, `client/src/**/*.{js,jsx,ts,tsx}`
- Custom theme with CSS variables
- Radix UI color system
- Animation plugins

---

## Development Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- PostgreSQL database (or Neon/Supabase)
- Supabase project

### Installation

```bash
cd demo-frontend
npm install
```

### Development Server

```bash
npm run dev
```

Starts:
- Express server on port 5001 (or PORT env var)
- Vite dev server with HMR
- Database migrations (drizzle-kit push)

### Build

```bash
npm run build
```

Outputs:
- Client build: `dist/public/`
- Server build: `dist/index.js`

### Production

```bash
npm start
```

Runs built server from `dist/index.js`.

### Database Migrations

```bash
npm run db:push
```

Pushes schema changes to database using Drizzle Kit.

---

## Migration to Next.js

### Key Considerations

#### 1. **Routing**
- **Current**: React Router (client-side)
- **Next.js**: File-based routing with `app/` or `pages/` directory
- **Migration**: Convert routes to Next.js pages/routes

#### 2. **Server-Side Rendering (SSR)**
- **Current**: Client-side only (SPA)
- **Next.js**: Can use SSR/SSG for better SEO and performance
- **Recommendation**: Keep comparison pages client-side (dynamic data), use SSR for landing/home

#### 3. **API Routes**
- **Current**: Express server in `server/` directory
- **Next.js**: API routes in `app/api/` or `pages/api/`
- **Migration**: Convert Express routes to Next.js API routes

#### 4. **State Management**
- **Current**: Zustand + React Query
- **Next.js**: Same libraries work, but consider:
  - Server components for initial data fetching
  - Client components for interactive features

#### 5. **File Structure**
```
nextjs-app/
├── app/                    # App Router (Next.js 13+)
│   ├── (auth)/            # Route groups
│   │   ├── login/
│   │   └── signup/
│   ├── (dashboard)/       # Protected routes
│   │   ├── page.tsx       # Home page
│   │   ├── compare/
│   │   │   └── [id]/
│   │   │       └── page.tsx
│   │   └── projects/
│   ├── api/               # API routes
│   │   ├── files/
│   │   ├── comparisons/
│   │   └── compare/
│   ├── layout.tsx          # Root layout
│   └── globals.css
├── components/            # Shared components (same structure)
├── features/             # Feature modules (same structure)
├── lib/                   # Utilities (same structure)
└── public/               # Static assets
```

#### 6. **Authentication**
- **Current**: Supabase client-side auth
- **Next.js**: 
  - Use Supabase Auth Helpers for Next.js
  - Server-side session management
  - Middleware for route protection

#### 7. **Environment Variables**
- **Current**: `VITE_*` prefix for client
- **Next.js**: 
  - `NEXT_PUBLIC_*` for client-side
  - No prefix for server-side only

#### 8. **Build & Deployment**
- **Current**: Vite build + Express server
- **Next.js**: 
  - `next build` creates optimized production build
  - Can deploy to Vercel, Railway, or self-hosted

### Migration Steps

1. **Initialize Next.js project**
   ```bash
   npx create-next-app@latest buildtrace-nextjs --typescript --tailwind --app
   ```

2. **Install dependencies**
   - Copy dependencies from `package.json`
   - Add Next.js-specific packages if needed

3. **Migrate components**
   - Move `client/src/components/` → `components/`
   - Convert to client components where needed (`'use client'`)

4. **Migrate pages**
   - Convert `pages/home/index.tsx` → `app/(dashboard)/page.tsx`
   - Convert `pages/comparison/index.tsx` → `app/(dashboard)/compare/[id]/page.tsx`
   - Convert `pages/Landing.tsx` → `app/(auth)/login/page.tsx`

5. **Migrate API routes**
   - Convert `server/routes.ts` → `app/api/*/route.ts` files
   - Use Next.js Request/Response API

6. **Migrate shared code**
   - Move `shared/` → `lib/schema/` or keep as shared
   - Move `client/src/lib/` → `lib/`
   - Move `client/src/features/` → `features/`

7. **Update imports**
   - Replace `@/` aliases (already configured in Next.js)
   - Update path references

8. **Configure authentication**
   - Set up Supabase Auth Helpers
   - Create middleware for route protection
   - Update auth hooks

9. **Test and optimize**
   - Test all routes and features
   - Optimize images and assets
   - Configure caching strategies

### Benefits of Next.js Migration

- **Better SEO**: Server-side rendering for public pages
- **Performance**: Automatic code splitting and optimization
- **Developer Experience**: Built-in routing, API routes, and optimizations
- **Deployment**: Easy deployment to Vercel with zero config
- **Type Safety**: Better TypeScript integration

### Potential Challenges

- **Learning Curve**: Next.js App Router concepts (Server/Client Components)
- **State Management**: May need to adjust Zustand usage for SSR
- **API Migration**: Converting Express routes to Next.js API routes
- **File Upload**: May need to adjust file upload handling for Next.js

---

## Additional Notes

### Styling System

- **Tailwind CSS**: Utility-first CSS
- **CSS Variables**: Theme customization via `styles/tokens.css`
- **Radix UI**: Accessible component primitives
- **Responsive Design**: Mobile-first approach with Tailwind breakpoints

### Error Handling

- **API Errors**: Handled via `apiRequest` helper (throws on non-OK responses)
- **Component Errors**: React Error Boundaries (can be added)
- **User Feedback**: Toast notifications via `useToast` hook

### Performance Optimizations

- **PDF Preloading**: PDFs preloaded when input is available
- **Polling Throttling**: 5-second intervals for comparison polling
- **React Query Caching**: Server data cached (though polling bypasses cache)
- **Code Splitting**: Vite automatically code-splits

### Testing

- **Test IDs**: Components include `data-testid` attributes for testing
- **No test framework**: Currently no test setup (can add Vitest/Jest)

---

## Summary

This frontend is a **modern React SPA** with:
- **Type-safe** TypeScript codebase
- **Feature-based architecture** for maintainability
- **Zustand + React Query** for state management
- **Supabase** for auth and storage
- **Express backend** in monorepo
- **PDF.js** for drawing visualization
- **Tailwind + Radix UI** for modern, accessible UI

The application is well-structured for migration to **Next.js**, with clear separation between client and server code, making the transition straightforward.

