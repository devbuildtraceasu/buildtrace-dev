# BuildTrace Frontend

Next.js frontend for BuildTrace with async job processing support.

## Status

Frontend structure is being set up to work in parallel with backend development.

## Next Steps

1. Set up Next.js project structure
2. Update API client for new async endpoints
3. Implement job polling for status updates
4. Add overlay editor component
5. Add summary regeneration UI

## API Integration

The frontend will integrate with the new async API:

- Job-based processing instead of session-based
- Polling for job status
- Real-time updates via WebSocket (future)
- Overlay editing interface
- Summary regeneration workflow

