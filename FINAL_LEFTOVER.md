# Final Leftover Tasks - BuildTrace Development Plan

Based on the architecture plan in `composer_plan/architecture2.md`, this document lists the remaining tasks organized by phase.

## Current Status Summary

- ✅ **Phase 1**: Foundation Setup - COMPLETE
- ✅ **Phase 2**: Orchestrator & Job Management - COMPLETE
- ✅ **Phase 3**: Processing Pipeline Extraction - COMPLETE
- ✅ **Phase 4**: Manual Overlay & Summary Management - COMPLETE
- 🚧 **Phase 5**: Flask Refactoring - IN PROGRESS
- 🚧 **Phase 6**: Testing & Optimization - IN PROGRESS
- ⏳ **Phase 7**: Migration & Rollout - PENDING

---

## Phase 4: Manual Overlay & Summary Management ✅

- `projects`, `overlays`, and `summaries` blueprints implemented and wired into the app
- Overlay storage/versioning, summary regeneration, and orchestrator integrations delivered
- Frontend results dashboard with JSON overlay editor + summary panel released
- Docker Compose stack enables Postgres + backend + frontend for end-to-end local testing

---

## Phase 5: Flask Refactoring (Week 10-11)

### 5.1 Remaining Blueprints 🚧
- `blueprints/auth.py`: refresh token rotation, logout-everywhere, RBAC middleware
- Membership APIs (invite/remove project members) still outstanding

### 5.2 Async Processing Cleanup 🚧
- Remove legacy synchronous modules once Pub/Sub workers are deployed in cloud
- Keep synchronous fallback only for local/dev via explicit flag

### 5.3 Service Layer Completion 🚧
- Build `services/job_service.py` for reusable job queries/stats
- Extract project CRUD helpers to `services/project_service.py`
- Ensure every blueprint uses service layer instead of inline SQLAlchemy logic

---

## Phase 6: Testing & Optimization (Week 12)

### 6.1 Comprehensive Testing 🚧
- Expand worker unit tests (diff/summary error paths, overlay regeneration)
- Add API integration tests for auth/projects/overlays/summaries
- Build end-to-end smoke test hitting the Docker Compose environment

### 6.2 Performance & Observability 🚧
- Add Prometheus metrics + Grafana dashboards (job throughput, queue depth, worker errors)
- Configure alerting (PagerDuty/Slack) for worker failures and backlog thresholds
- Execute load/performance testing of OCR/diff/summary stages

### 6.3 Security & Hardening 🚧
- Rate limiting, request tracing, and enhanced audit export to GCS/BigQuery
- Secrets management for containers (Cloud Secret Manager / Docker secrets)
- Automated backups for Postgres + storage buckets

---

## Phase 7: Migration & Rollout (Week 13)

### 7.1 Container Deployment ⏳
- Publish backend/frontend/worker images to Artifact Registry
- Terraform or Deployment Manager scripts for GKE/Cloud Run + Pub/Sub resources
- Configure CI/CD pipeline to build, test, and deploy containers on merge

### 7.2 Production Rollout ⏳
- Plan blue/green deployment strategy
- Data migration checklist (legacy tables → new schema)
- Post-rollout monitoring plan & rollback procedures

### 7.3 Documentation & Training ⏳
- Developer onboarding guide for new architecture
- Runbooks for support staff (restart workers, inspect queues, rotate keys)
- Product documentation for overlay editor + results dashboard
