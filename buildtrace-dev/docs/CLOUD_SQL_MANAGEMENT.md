# Cloud SQL Instance Management

**Last Updated:** December 12, 2025  
**Instance:** `buildtrace-dev-db`  
**Project:** `buildtrace-dev`  
**Region:** `us-west2`

---

## Quick Reference

### Stop Instance (Save Costs)
```bash
./scripts/stop-cloud-sql.sh
```

### Start Instance
```bash
./scripts/start-cloud-sql.sh
```

### Check Status
```bash
gcloud sql instances describe buildtrace-dev-db \
  --project=buildtrace-dev \
  --format="value(settings.activationPolicy,state)"
```

---

## Instance Details

| Property | Value |
|----------|-------|
| **Instance Name** | `buildtrace-dev-db` |
| **Connection Name** | `buildtrace-dev:us-west2:buildtrace-dev-db` |
| **Database** | `buildtrace_db` |
| **User** | `buildtrace_user` |
| **Version** | PostgreSQL 17 |
| **Tier** | `db-perf-optimized-N-8` |
| **High Availability** | Yes (Regional) |
| **Automatic Backups** | Yes (Daily) |

---

## Cost Management

### Stopping the Instance

**When to Stop:**
- Development/testing environments not in use
- Cost optimization during low-usage periods
- Emergency cost control

**What Happens:**
- ✅ Compute charges stop immediately
- ✅ All database connections fail
- ✅ All services using the database will show errors
- ⚠️ Data remains safe (not deleted)
- ⚠️ You still pay for:
  - Storage (disk size)
  - Backups (if enabled)
  - Reserved IP addresses (if any)

**Impact:**
- Backend API will fail database operations
- All workers (OCR, Diff, Summary) will fail
- Frontend may show errors for database-dependent features

### Starting the Instance

**Restart Time:** 2-5 minutes

**After Restart:**
- All services will automatically reconnect
- No data loss
- Full functionality restored

---

## Manual Commands

### Stop Instance
```bash
gcloud sql instances patch buildtrace-dev-db \
  --project=buildtrace-dev \
  --activation-policy=NEVER
```

### Start Instance
```bash
gcloud sql instances patch buildtrace-dev-db \
  --project=buildtrace-dev \
  --activation-policy=ALWAYS
```

### Check Current Status
```bash
gcloud sql instances describe buildtrace-dev-db \
  --project=buildtrace-dev \
  --format="yaml(settings.activationPolicy,state)"
```

**Expected Output:**
- **Stopped:** `activationPolicy: NEVER`, `state: STOPPED`
- **Running:** `activationPolicy: ALWAYS`, `state: RUNNABLE`

---

## Troubleshooting

### Instance Won't Stop
- Check you have `cloudsql.instances.update` permission
- Verify project ID is correct
- Check if instance is in a maintenance window

### Services Still Failing After Restart
- Wait 2-5 minutes for full startup
- Check instance state: `gcloud sql instances describe buildtrace-dev-db`
- Verify Cloud Run services have correct connection string
- Check service logs for connection errors

### Connection Errors
- Verify `INSTANCE_CONNECTION_NAME` environment variable
- Check service account has Cloud SQL Client role
- Verify network connectivity (Cloud Run → Cloud SQL)

---

## Related Documentation

- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Full deployment setup
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Database architecture details
- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) - System overview

---

## Scripts Location

- `scripts/stop-cloud-sql.sh` - Interactive stop script
- `scripts/start-cloud-sql.sh` - Interactive start script

---

**Last Updated:** December 12, 2025
