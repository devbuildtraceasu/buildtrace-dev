# BuildTrace Dev - Planned Roadmap

**Last Updated**: 2025-11-22

This roadmap assumes Phase 6 QA + Phase 7 hardening complete and focuses on delivering every feature except manual overlay, per scope.

---

## 🎯 Phase 8 – Product Enhancements

### 8.1 Drawing Intake & Processing
- Multi-file upload with drag/drop + validation states
- Upload recovery (persist queue + progress)
- Background worker rollout (Pub/Sub jobs + metrics)
- Batch compare support (submit multiple pairs, auto run)

### 8.2 Results & Insight Layer
- Results dashboard with thumbnail navigation & filters
- AI summary refinement (approve / regenerate / comment)
- Export package (diff overlay PNG + PDF summary)
- Change metrics (count, impacted sheets, timestamps)

### 8.3 Collaboration & Workflow
- Project member management (Owner / Editor / Viewer roles)
- Comment threads on jobs and drawings with mentions
- Activity log (upload, diff completion, summary edits)
- Notification hooks (Slack + email when jobs finish)

### 8.4 Integration Surface
- API keys + scoped tokens for external upload automation
- Webhooks for job completion + summary updates
- CLI helper to push drawings from local / CI pipelines

---

## ⚙️ Performance & Security Backlog
- Redis/Cloud Memorystore caching for hot metadata
- Async task fan-out (separate OCR/diff/summary workers)
- Rate limiting + WAF rules before public beta
- Token refresh & revocation service (short-lived access, long-lived refresh)
- Automated backups + retention policies for Cloud SQL + GCS

---

## 📊 Observability & Ops
- Cloud Monitoring dashboards (jobs, uploads, auth latency)
- Error budget + SLO definitions for API + job pipeline
- Pager/Slack alerts wired to SLOs
- Chaos / load testing script to simulate batch uploads

---

## 📱 Experience & Accessibility
- Responsive layout polishing for upload/results pages
- Keyboard navigation + screen-reader labels for uploader + results
- Dark mode + high-contrast palette toggle
- Tutorial/onboarding overlay for first-time users

---

## 📅 High-Level Timeline (Post-QA)
| Window | Focus |
| --- | --- |
| Weeks 1-2 | Worker rollout, upload UX improvements, webhook/API key groundwork |
| Weeks 3-4 | Results dashboard, AI summary refinement, notification hooks |
| Weeks 5-6 | Collaboration features, export package, accessibility polish |
| Weeks 7+  | Performance tuning, token refresh, advanced analytics |

---

**Status**: 📋 Planning complete – execution starts after Phase 6 QA sign-off.
