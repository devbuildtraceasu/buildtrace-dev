# BuildTrace - Pending Tasks

**Last Updated:** November 29, 2025 (Evening)  
**Priority Order:** Critical → High → Medium → Low

---

## 🟢 RESOLVED (Previously Critical)

### ✅ GKE Worker Deployment - COMPLETE

All worker deployment issues have been resolved:

| Issue | Resolution |
|-------|------------|
| ImagePullBackOff | Switched to Artifact Registry, removed imagePullSecrets |
| libGL.so.1 missing | Added libgl1-mesa-glx to Dockerfile |
| poppler-utils missing | Added poppler-utils to Dockerfile |
| Cloud SQL connection | Added Cloud SQL Proxy sidecar |
| Pub/Sub permissions | Granted pubsub.subscriber/publisher roles |
| GCS permissions | Granted storage.objectViewer, fixed path normalization |
| Diff OOMKilled | Increased memory to 28Gi, created high-memory node pool |
| GPT-5 timeouts | Switched to GPT-4o (3x faster) |
| Numpy serialization | Implemented NumpyJSONEncoder |
| Missing DB columns | Added diff_metadata, summary_metadata columns |
| Single-page diff limitation | Diff pipeline now iterates through every page sequentially |
| Jobs not visible in UI | `/api/v1/jobs` GET endpoint + frontend widget show recent jobs |
| Missing default projects | OAuth callback now creates “My First Project” for each user |
| `diff_metadata` mismatch | Code paths now write/read the correct column |

**End-to-End Pipeline:** ✅ Working  
**Completed Job:** `51413b10-a816-40ee-b151-18e7f53252de`

---

## 🔴 CRITICAL (Immediate Action Required)

No outstanding critical issues. Continue monitoring worker health and user experience.

## 🟠 HIGH PRIORITY (This Week)

### 2. Monitoring & Alerting Setup

**Status:** ⏳ Pending

**Actions Required:**
- [ ] Create Cloud Monitoring dashboards:
  - [ ] Worker health and processing times
  - [ ] Job throughput and completion rates
  - [ ] Pub/Sub queue depths
  - [ ] API response times and error rates
  - [ ] OAuth/login error rates
- [ ] Configure alerting policies:
  - [ ] 5xx error spikes (> 5% for 5 minutes)
  - [ ] Worker pod failures
  - [ ] Job completion time > 10 minutes
  - [ ] Pub/Sub backlog > 100 messages
  - [ ] Database connection errors
- [ ] Set up notification channels (email/Slack)

---

### 3. Rate Limiting Implementation

**Status:** ⏳ Pending

**Actions Required:**
- [ ] Research Flask rate limiting libraries
- [ ] Implement rate limiting middleware
- [ ] Configure limits per endpoint:
  - [ ] Upload endpoints: 10 requests/minute
  - [ ] Job creation: 5 requests/minute
  - [ ] API endpoints: 60 requests/minute
- [ ] Add rate limit headers to responses
- [ ] Document rate limits in API docs
- [ ] Test rate limiting behavior

---

## 🟡 MEDIUM PRIORITY (Next 2 Weeks)

### 4. Token Refresh & Revocation

**Status:** ⏳ Pending

**Actions Required:**
- [ ] Design refresh token flow
- [ ] Implement refresh token generation
- [ ] Create refresh token endpoint
- [ ] Update frontend to handle token refresh
- [ ] Implement token revocation endpoint
- [ ] Add token blacklist (database or cache)
- [ ] Update JWT expiry to shorter duration (1 hour)
- [ ] Test token refresh flow

---

### 5. Frontend Chatbot UI Integration

**Status:** ⏳ Pending

**Actions Required:**
- [ ] Create ChatAssistant component
- [ ] Integrate with ResultsPage
- [ ] Add conversation history display
- [ ] Add message input and send functionality
- [ ] Handle loading and error states
- [ ] Style chatbot UI
- [ ] Test chatbot integration end-to-end

**Note:** Backend chatbot API already implemented (`blueprints/chat.py`)

---

### 6. CI/CD Pipeline Setup

**Status:** ⏳ Pending

**Actions Required:**
- [ ] GitHub Actions workflow
- [ ] Automated testing
- [ ] Automated deployment
- [ ] Smoke tests (`/api/v1/auth/google/login`, `/api/v1/auth/me`, `/health`)

---

## 🟢 LOW PRIORITY (Future Enhancements)

### 7. Operational Hardening

**Status:** ⏳ Pending

**Actions Required:**
- [ ] Runbooks creation:
  - [ ] Redeploying Cloud Run services
  - [ ] Rotating secrets
  - [ ] Re-linking Cloud SQL
  - [ ] Worker deployment and scaling
  - [ ] Database backup and restore
- [ ] Disaster recovery plan
- [ ] Performance optimization
- [ ] Cost optimization review

---

### 8. Feature Enhancements

**Status:** ⏳ Pending

**Drawing & Upload Experience:**
- [ ] Multi-file dropzone with drag-select
- [ ] Upload progress persistence
- [ ] Background job queue display
- [ ] Batch compare support

**Results & Insights:**
- [ ] Comparison gallery with thumbnails
- [ ] AI summary refinement workflow
- [ ] Download package (PNG + PDF)
- [ ] Change metrics dashboard

**Collaboration & Workflow:**
- [ ] Project member management
- [ ] Comment threads on jobs
- [ ] Activity log
- [ ] Notification hooks (Slack/email)

**Integrations & Automation:**
- [ ] API keys for external access
- [ ] Webhooks for job completion
- [ ] CLI helper tool

---

## 📋 Known Issues & Technical Debt

### Current Issues
1. **Frontend Recent Comparisons Empty** - User's completed jobs don't appear
2. **No Rate Limiting** - API is unprotected from abuse
3. **No Token Refresh** - JWT tokens expire after 7 days, no refresh mechanism
4. **No Monitoring** - No visibility into system health
5. **No Alerting** - No notifications for failures

### Technical Debt
1. **Synchronous Fallback** - Workers have sync fallback, should be removed once Pub/Sub is stable
2. **Error Handling** - Some error cases not fully handled
3. **Logging** - Could be more comprehensive
4. **Testing** - Need more integration tests
5. **Documentation** - Some code lacks inline documentation

---

## 🎯 Sprint Planning

### Sprint 1 (Completed)
- [x] Restart GKE nodes
- [x] Resolve image pull issues
- [x] Fix Cloud SQL Proxy connection
- [x] Fix Pub/Sub permissions
- [x] Fix GCS permissions
- [x] Fix Diff worker OOM
- [x] Switch to GPT-4o
- [x] Fix numpy serialization
- [x] Add missing DB columns
- [x] Verify workers processing
- [x] End-to-end job completion

### Sprint 2 (Current)
- [ ] Fix frontend recent comparisons
- [ ] Monitoring setup
- [ ] Rate limiting
- [ ] Worker documentation

### Sprint 3 (Next Week)
- [ ] Token refresh
- [ ] Alerting setup
- [ ] CI/CD pipeline
- [ ] Runbooks

---

## 📝 Session Notes (Nov 29, 2025)

### What Was Done
1. Diagnosed and fixed 10+ deployment issues
2. Created high-memory node pool for diff worker
3. Switched from GPT-5 to GPT-4o for better performance
4. Implemented Pub/Sub flow control to prevent OOM
5. Fixed numpy type serialization
6. Added missing database columns
7. Completed first end-to-end job successfully

### Key Learnings
- GPT-5 is 3x slower than GPT-4o for vision tasks
- Diff processing requires 28GB+ memory for large images
- Pub/Sub flow control is essential for memory-intensive workers
- Cloud SQL Proxy sidecar is required for GKE workers

### Next Session
- Fix frontend recent comparisons display
- Set up monitoring dashboards
- Implement rate limiting

---

**For current progress, see [PROGRESS.md](./PROGRESS.md)**  
**For system overview, see [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)**

