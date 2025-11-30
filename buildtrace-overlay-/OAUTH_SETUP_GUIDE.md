# OAuth Login Setup Guide

## Problem Fixed
The OAuth login was looping because the Next.js frontend and Flask backend were not properly connected. After clicking "Continue with Google", the backend would redirect to a Flask HTML template, but the frontend expected JSON API responses.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OAuth Flow (Fixed)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User clicks "Continue with Google" (Next.js)               │
│          ↓                                                       │
│  2. Redirects to: http://localhost:5000/auth/google            │
│          ↓                                                       │
│  3. Flask redirects to Google OAuth                             │
│          ↓                                                       │
│  4. User authorizes on Google                                   │
│          ↓                                                       │
│  5. Google redirects back to: /auth/google/callback            │
│          ↓                                                       │
│  6. Flask backend:                                              │
│     • Creates/updates user in database                          │
│     • Sets Flask session cookie                                 │
│     • Redirects to: http://localhost:3000/auth/callback        │
│          ↓                                                       │
│  7. Next.js callback page:                                      │
│     • Waits for session cookie to propagate                     │
│     • Calls /auth/me to get user info                          │
│     • Updates Zustand auth state                                │
│     • Redirects to home page (/)                                │
│          ↓                                                       │
│  8. User is logged in! ✅                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Files Changed

### Frontend (Next.js)

1. **`frontend/src/app/auth/callback/page.tsx`** (NEW)
   - Handles OAuth callback from Flask backend
   - Calls `/auth/me` to sync auth state
   - Redirects to home page on success

2. **`frontend/src/store/authStore.ts`** (UPDATED)
   - Added localStorage.clear() on logout
   - Uses `/auth/me` to check authentication

3. **`frontend/.env.local`** (NEW)
   - Sets `NEXT_PUBLIC_API_URL=http://localhost:5000`
   - Ensures frontend calls local Flask backend

### Backend (Flask)

4. **`app_with_auth.py`** (UPDATED)
   - Added `/auth/me` endpoint (returns user JSON)
   - Added `/auth/logout` POST endpoint for API
   - Modified OAuth callback to redirect to Next.js callback page
   - Detects if request is from Next.js frontend

### Configuration

5. **`.gitignore`** (UPDATED)
   - Added `drawings/` folder

## Setup Instructions

### 1. Start Flask Backend

```bash
# Terminal 1
cd /Users/yuxinzhao/buildtrace-overlay
python3 app_with_auth.py
```

The backend will run on: **http://localhost:5000**

### 2. Start Next.js Frontend

```bash
# Terminal 2
cd /Users/yuxinzhao/buildtrace-overlay/frontend
npm run dev
```

The frontend will run on: **http://localhost:3000**

### 3. Test OAuth Login

1. Open browser: http://localhost:3000
2. You'll see the login page
3. Click "Continue with Google"
4. Authorize on Google
5. You'll be redirected back and logged in! ✅

## Environment Variables

### Flask Backend (.env)

```bash
# OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Frontend URL (for OAuth redirect)
FRONTEND_URL=http://localhost:3000

# Database
DATABASE_URL=your-database-url
```

### Next.js Frontend (.env.local)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## API Endpoints

### Authentication

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/me` | GET | Check if user is authenticated (returns JSON) |
| `/auth/login` | POST | Email/password login |
| `/auth/logout` | POST | Logout (API endpoint) |
| `/auth/google` | GET | Initiate Google OAuth |
| `/auth/google/callback` | GET | Handle OAuth callback (redirects to Next.js) |

## Troubleshooting

### Issue: Still seeing login loop

**Solution:**
1. Make sure Flask backend is running on port 5000
2. Make sure Next.js frontend is running on port 3000
3. Clear browser cookies and localStorage
4. Check that `.env.local` exists in `frontend/` folder

### Issue: "Network error"

**Solution:**
1. Check that `NEXT_PUBLIC_API_URL=http://localhost:5000` in `.env.local`
2. Restart Next.js dev server after changing .env.local
3. Make sure Flask backend is running

### Issue: OAuth fails with "redirect_uri_mismatch"

**Solution:**
1. Go to Google Cloud Console
2. Add authorized redirect URI: `http://localhost:5000/auth/google/callback`
3. Wait a few minutes for Google to update

## Production Deployment

For production (Cloud Run), the flow is the same but uses HTTPS:

```bash
# Backend environment variables
FRONTEND_URL=https://your-frontend-domain.com
GOOGLE_OAUTH_CLIENT_ID=production-client-id
GOOGLE_OAUTH_CLIENT_SECRET=production-client-secret

# Frontend environment variables
NEXT_PUBLIC_API_URL=https://buildtrace-overlay-lioa4ql2nq-uc.a.run.app
```

## Summary

✅ OAuth callback now redirects to Next.js instead of Flask template
✅ Frontend syncs auth state via `/auth/me` endpoint
✅ Session cookies work between Flask backend and Next.js frontend
✅ User can successfully log in with Google OAuth
✅ No more login loop!
