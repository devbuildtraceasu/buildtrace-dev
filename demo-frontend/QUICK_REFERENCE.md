# BuildTrace Frontend - Quick Reference Guide

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## 📁 Key File Locations

### Entry Points
- **Client Entry**: `client/src/main.tsx`
- **App Root**: `client/src/App.tsx`
- **Router**: `client/src/router.tsx`
- **Server Entry**: `server/index.ts`

### Pages
- **Home**: `client/src/pages/home/index.tsx`
- **Comparison**: `client/src/pages/comparison/index.tsx`
- **Landing**: `client/src/pages/Landing.tsx`

### State Management
- **Comparison Store**: `client/src/features/comparison/state/useComparisonStore.ts`
- **Recent Store**: `client/src/features/recent/state/useRecentStore.ts`
- **Query Client**: `client/src/lib/queryClient.ts`

### API Integration
- **API Helper**: `client/src/lib/queryClient.ts` (apiRequest function)
- **File Upload**: `client/src/services/fileUploadService.ts`
- **Server Routes**: `server/routes.ts`

### Authentication
- **Client Auth**: `client/src/lib/supabaseClient.ts`
- **Auth Hook**: `client/src/hooks/useAuth.ts`
- **Server Auth**: `server/authMiddleware.ts`

### Database
- **Schema**: `shared/schema.ts`
- **DB Connection**: `server/db.ts`
- **Storage Layer**: `server/storage.ts`

## 🔑 Key Concepts

### State Management
- **Zustand**: Client-side UI state (comparison, view mode, zoom)
- **React Query**: Server state caching (though polling is manual)
- **Local Storage**: Recent comparisons history

### Data Flow
1. User action → Component handler
2. API call via `apiRequest()` → Express server
3. Server → Database/Supabase Storage
4. Response → Update Zustand store
5. Store update → Component re-render

### Authentication Flow
1. User signs in on Landing page
2. Supabase creates session
3. JWT token stored in browser
4. Token included in API requests
5. Server validates token via `requireAuth` middleware

### Comparison Workflow
1. Upload baseline file → `POST /api/files/upload`
2. Upload revised file → `POST /api/files/upload`
3. Start comparison → `POST /api/compare/pdf`
4. Navigate to `/compare/:id`
5. Poll `GET /api/comparisons/:id` every 5s
6. Display results when `status === 'completed'`

## 🎨 Component Structure

```
App
├── Router
│   ├── Landing (unauthenticated)
│   └── AppLayout (authenticated)
│       ├── HomePage
│       │   ├── Stepper
│       │   ├── UploadDropzoneWithAuth (x2)
│       │   └── RecentComparisonsTable
│       └── ComparisonPage
│           ├── ComparisonToolbar
│           ├── ViewModeToggle
│           ├── ComparisonViewers
│           │   └── PdfViewer (x2)
│           ├── SummarySection
│           ├── ChangesList
│           ├── ChangeDetailsPanel
│           └── AskPanel
```

## 📡 API Endpoints Quick Reference

### Files
- `POST /api/files/upload` - Upload file
- `GET /api/files` - List user files
- `GET /api/files/:id/download` - Download file
- `DELETE /api/files/:id` - Delete file

### Comparisons
- `POST /api/compare/pdf` - Start comparison
- `GET /api/comparisons` - List comparisons
- `GET /api/comparisons/:id` - Get comparison
- `GET /api/comparisons/:id/overlay` - Get overlay PDF
- `POST /api/assistants/followup` - AI assistant question

## 🔧 Environment Variables

### Client (Vite)
```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
```

### Server
```env
DATABASE_URL=postgresql://...
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
COMPARE_API_URL=http://localhost:8000/compare/pdf
PORT=5001
NODE_ENV=development
```

## 🗄️ Database Schema

### Tables
- **users**: User accounts
- **uploaded_files**: File metadata
- **comparisons**: Comparison records

### Key Fields
- `comparisons.status`: `'pending' | 'processing' | 'completed' | 'failed'`
- `comparisons.pageMapping`: `Array<[drawingCode, oldPageIndex, newPageIndex]>`
- `comparisons.kpis`: `{ added: number, modified: number, removed: number }`

## 🎯 Common Tasks

### Add a New Page
1. Create component in `client/src/pages/`
2. Add route in `client/src/router.tsx`
3. Add navigation link in `AppLayout` if needed

### Add a New API Endpoint
1. Add route handler in `server/routes.ts`
2. Use `requireAuth` middleware for protected routes
3. Call `storage` methods for database operations
4. Use `apiRequest` in frontend to call endpoint

### Add a New Component
1. Create in appropriate directory:
   - `components/common/` - Shared components
   - `components/comparison/` - Comparison-specific
   - `components/ui/` - Base UI components
2. Import and use in pages/components

### Update State Management
- **UI State**: Add to Zustand store in `features/*/state/`
- **Server State**: Use React Query or manual polling
- **Local State**: Use `useState` in components

## 🐛 Debugging Tips

### Check Authentication
```typescript
const { user, isAuthenticated } = useAuth();
console.log('User:', user, 'Authenticated:', isAuthenticated);
```

### Check Comparison State
```typescript
const state = useComparisonStore();
console.log('Comparison State:', state);
```

### Check API Response
```typescript
const res = await apiRequest('GET', '/api/comparisons/:id');
const data = await res.json();
console.log('API Response:', data);
```

### View Supabase Storage
- Go to Supabase Dashboard → Storage → `drawings` bucket
- Files stored as: `{userId}/{timestamp}_{filename}`

## 📦 Key Dependencies

### Core
- `react`, `react-dom` - UI framework
- `react-router-dom` - Routing
- `zustand` - State management
- `@tanstack/react-query` - Server state

### UI
- `tailwindcss` - Styling
- `@radix-ui/*` - Component primitives
- `lucide-react` - Icons
- `framer-motion` - Animations

### Backend
- `express` - Server framework
- `@supabase/supabase-js` - Supabase client
- `drizzle-orm` - Database ORM
- `pg` - PostgreSQL client

### PDF
- `pdfjs-dist` - PDF rendering
- `jspdf` - PDF generation

## 🔄 Migration Checklist (Next.js)

- [ ] Initialize Next.js project
- [ ] Install all dependencies
- [ ] Migrate components (add 'use client' where needed)
- [ ] Convert pages to Next.js routes
- [ ] Convert API routes to Next.js API routes
- [ ] Update authentication (Supabase Auth Helpers)
- [ ] Update environment variables (NEXT_PUBLIC_*)
- [ ] Test all routes and features
- [ ] Optimize for production

## 📚 Additional Resources

- **Full Documentation**: See `FRONTEND_DOCUMENTATION.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **API Docs**: See `documentation/API.md`
- **Database**: See `documentation/DATABASE.md`

