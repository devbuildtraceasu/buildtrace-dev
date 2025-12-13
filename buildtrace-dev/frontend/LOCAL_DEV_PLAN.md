# Frontend Local Dev Plan

## Goals
1. Recreate the BuildTrace mockups locally without backend dependency.
2. Provide deterministic mock data for projects, jobs, job results so every UX state works offline.
3. Ensure components render without OAuth by injecting a fake authenticated user.

## Approach
- Introduce a `USE_MOCK_API=true` flag (env or runtime) to redirect `apiClient` to mock handlers.
- Store mock datasets under `src/mocks/` (projects, jobs, job results).
- Update `apiClient` to return mock promises when enabled.
- Seed `authStore` with a fake user (e.g., `dev@test.com`) when mock mode is on.
- Replace `window.location` OAuth redirect with stub in mock mode.

## Tasks
1. Create `src/mocks/data.ts` with sample user, projects, jobs, job results (multi-page diff data).
2. Add `src/mocks/apiClient.ts` that mimics async API responses using the mock data.
3. Update `src/lib/api.ts` to switch between real axios client and mock client based on `process.env.NEXT_PUBLIC_USE_MOCKS` or `window.__USE_MOCKS__`.
4. Update auth store init to auto-login fake user when mocks enabled.
5. Provide `npm run dev:mock` script that sets `NEXT_PUBLIC_USE_MOCKS=true` and disables OAuth button (or converts to noop).
6. Validate upload flow, processing monitor, and results page using mock data.

## Notes
- Keep real API path untouched to avoid regression.
- Mock job results should include multiple `diffs` with `summary.summary_text` so parsing logic is exercised.
- Provide at least one job with `changes_detected=false` to test the green banner state.
