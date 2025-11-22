# OAuth 2.0 Setup Guide

## Current Configuration

### Google Cloud Console Setup
1. **Redirect URI in Google Console**: `http://localhost:5001/api/v1/auth/google/callback`
   - This is the **backend** callback URL where Google sends the authorization code
   - ✅ This is correct and should NOT be changed

2. **Backend Configuration**:
   - `GOOGLE_REDIRECT_URI`: `http://localhost:5001/api/v1/auth/google/callback` (backend callback)
   - `FRONTEND_URL`: `http://localhost:3000` (where users should land after login)

### How It Works

1. User clicks "Sign in with Google" on frontend (`localhost:3000`)
2. Frontend calls backend: `GET /api/v1/auth/google/login`
3. Backend returns Google OAuth URL
4. Frontend redirects user to Google login page
5. User authenticates with Google
6. Google redirects to: `http://localhost:5001/api/v1/auth/google/callback` (backend)
7. Backend processes the callback, creates/updates user, stores session
8. Backend redirects to: `http://localhost:3000/?auth=success&user_id=...` (frontend)
9. Frontend detects `auth=success` in URL and fetches user info

## Environment Variables

Add to your `.env` file:

```bash
# OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5001/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3000
```

## For Production

When deploying:

1. **Update Google Cloud Console**:
   - Add production redirect URI: `https://yourdomain.com/api/v1/auth/google/callback`

2. **Update `.env`**:
   ```bash
   FRONTEND_URL=https://yourdomain.com
   GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/google/callback
   ```

## Important Notes

- ✅ **Redirect URI in Google Console** = Backend callback URL (`/api/v1/auth/google/callback`)
- ✅ **FRONTEND_URL** = Where users land after successful login
- ✅ These are **different URLs** - backend processes OAuth, then redirects to frontend

## Testing

1. Make sure both servers are running:
   - Backend: `http://localhost:5001`
   - Frontend: `http://localhost:3000`

2. Visit `http://localhost:3000` - should redirect to `/login`

3. Click "Sign in with Google"

4. After Google login, you should be redirected back to `http://localhost:3000/?auth=success&user_id=...`

5. Frontend should detect the success and fetch user info

