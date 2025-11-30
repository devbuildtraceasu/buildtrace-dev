[30 tools called]

## Comparison Summary

- **`buildtrace-overlay-` (reference build)** runs everything inside a single Flask app: uploads go into a `Session`, the server immediately runs `complete_drawing_pipeline()` (PDF → PNG → multi-sheet matching → overlays → AI summary) and stores the results back on that same session. There is no Pub/Sub; the whole pipeline is synchronous.  
  ```190:206:buildtrace-overlay-/drawing_comparison.py
  ...creates overlays for every matching sheet name inside a PDF pair and returns counts for `matches_found`, `successful_overlays`, etc.
  ```
  ```346:448:buildtrace-overlay-/app.py
  `/api/process-uploaded-files` downloads both PDFs, calls `chunked_process_documents`/`complete_drawing_pipeline`, and marks the session `completed` once the single request finishes.
  ```
  ```150:177:buildtrace-overlay-/gcp/infrastructure/job_processor.py
  The background “job processor” still just calls `complete_drawing_pipeline(...)` once and stores the combined results on the original session.
  ```

- **`buildtrace-dev` (your current build)** replaced that monolith with an async workflow: uploads create `DrawingVersion` rows under a `Project`, an `OrchestratorService` spawns a `Job` with four `JobStage` rows (two OCR, diff, summary), and three separate workers consume Pub/Sub messages.  
  ```67:126:buildtrace-dev/backend/services/orchestrator.py
  Two OCR stages plus one diff and one summary stage are created for every job and the corresponding Pub/Sub messages are published.
  ```

### Fundamental Differences / Gaps

1. **Multi-sheet comparison logic disappeared.**  
   The reference pipeline matches *every page* that shares a drawing name (`compare_drawing_sets` loops over every PNG match). In the new repo, `DiffPipeline` only rasterizes the *first page* of each PDF (`pdf_to_png(..., page_index=0)`) and produces exactly one overlay per job. That means multi-sheet PDFs are no longer compared sheet-by-sheet.  
   ```75:143:buildtrace-dev/backend/processing/diff_pipeline.py
   # Convert first page of each PDF to PNG
   old_png_path = pdf_to_png(... page_index=0)
   new_png_path = pdf_to_png(... page_index=0)
   ```
   → If you upload a 10-page baseline vs 10-page revision, the new system will only ever diff page 1, whereas the overlay build produced 10 separate overlays and summaries. That is a fundamental behavioral regression.

2. **Front-end “Recent Comparisons” is unimplemented.**  
   In overlay, sessions were persisted and listed; in the new React app the component is a stub that intentionally never calls an API, so the table will always be empty regardless of backend data.  
   ```20:35:buildtrace-dev/frontend/src/components/upload/RecentSessions.tsx
   // For now, show empty state since we don't have a sessions API yet
   setIsLoading(false)
   ```
   → Even though jobs complete successfully, nothing drives that UI.

3. **Projects & ownership don’t line up with OAuth users.**  
   `list_projects` filters by `user_id`, but uploads default to the hard-coded `default-project`, and `DrawingUploadService` refuses to proceed unless that `Project` row already exists (and is owned by the uploading user).  
   ```35:48:buildtrace-dev/backend/blueprints/projects.py
   if user_id:
       query = query.filter(Project.user_id == user_id)
   ...
   return {'projects': [...]}
   ```
   ```87:90:buildtrace-dev/backend/services/drawing_service.py
   project = db.query(Project).filter_by(id=project_id).first()
   if not project:
       raise DrawingUploadError('Project not found')
   ```
   Unless you insert a project whose `user_id` matches the Google OAuth user (`4581…`), `/api/v1/projects?user_id=...` will remain empty and uploads referencing `default-project` will eventually fail once that placeholder project is removed. In the overlay build the project/session rows were tied directly to the logged-in user, so the dashboard populated automatically.

4. **Data model mismatch between old “Session/Comparison” UX and new “Job/DiffResult” backend.**  
   Overlay stored overlays and AI summaries on `sessions`, `comparisons`, and `analysis_results`. The new build writes to `jobs`, `job_stages`, `diff_results`, and `change_summaries`, but the frontend still talks about “sessions” and never queries the new tables. Until you expose `/api/v1/jobs` (or similar) and update the UI to consume it, users will have no way to list completed comparisons—even though the workers finished them.

### Is the new pipeline “correct”?

- **Uploading & processing**: when a valid project exists, uploading the baseline + revision does create a `Job`, both OCR stages run, diff and summary workers complete, and results land in `diff_results` / `change_summaries`. So the core stages do function.
- **Feature parity**: compared to `buildtrace-overlay-`, the new code currently processes only one sheet per upload pair and no longer exposes the processed results the way the UI expects. For anyone relying on multi-sheet comparisons or the “recent comparisons” view, that is a functional gap.

### Recommendations

1. **Decide on multi-sheet strategy**: either restore the overlay logic (split PDFs and create one `DrawingVersion` per sheet) or update `DiffPipeline`/`JobStage` to iterate through every page/drawing name. Without that, the new system will miss most drawings.

2. **Expose completed jobs**: add an API (e.g., `/api/v1/jobs?user_id=`) that returns the latest jobs with summary metadata, then update `RecentSessions` to call it. Alternatively, re-implement the session listing from the overlay build using the new tables.

3. **Fix project ownership**: when a user signs in, ensure there is at least one `Project` row owned by that user (seed a “Default Project”) so `/api/v1/projects?user_id=...` returns something and uploads don’t rely on a shared placeholder.

4. **Verify DiffResult schema usage**: in `DiffPipeline` you still pass `metadata=` when constructing `DiffResult`, but the SQLAlchemy model renamed the column to `diff_metadata`. Align those names to avoid silent failures when running new migrations.

Once those gaps are addressed, the async worker architecture in `buildtrace-dev` will match the original end-to-end behavior more closely.