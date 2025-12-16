# GCP Cost Summary - Past 7 Days

**Generated:** December 12, 2025  
**Project:** `buildtrace-dev`  
**Billing Account:** `013DA5-F6D60D-EAB0A7`  
**Period:** December 7-14, 2025

---

## 📊 Executive Summary

### Current Status
- ✅ **Cloud SQL:** STOPPED (saving ~$50-100/day in compute costs)
- ⚠️ **Cloud Run:** Running (estimated $0.10-0.50/day per service)
- ⚠️ **Cloud Storage:** ~1.23 GB used (~$0.03/month)
- ⚠️ **Pub/Sub:** 7 topics active (~$0.40 per million messages)
- ⚠️ **Artifact Registry:** 4 repositories (~$0.10/GB/month)

### Estimated Daily Costs (While Cloud SQL is Stopped)
- **Cloud SQL Storage:** ~$0.15/day (100GB SSD storage only)
- **Cloud Run:** ~$0.20-1.00/day (depending on traffic)
- **Cloud Storage:** ~$0.001/day (1.23 GB)
- **Pub/Sub:** ~$0.01-0.10/day (depending on message volume)
- **Artifact Registry:** ~$0.01/day
- **Total Estimated:** ~$0.37-1.26/day

### Estimated Daily Costs (If Cloud SQL was Running)
- **Cloud SQL Compute:** ~$50-100/day (db-perf-optimized-N-8 tier)
- **All other services:** ~$0.37-1.26/day
- **Total Estimated:** ~$50-101/day

**💰 Savings from stopping Cloud SQL: ~$50-100/day**

---

## 🔧 Service Breakdown

### 1. Cloud SQL (`buildtrace-dev-db`)

| Property | Value |
|----------|-------|
| **Status** | STOPPED |
| **Tier** | db-perf-optimized-N-8 |
| **Disk Size** | 100 GB (SSD) |
| **Activation Policy** | NEVER (stopped) |
| **Current Cost** | ~$0.15/day (storage only) |
| **If Running** | ~$50-100/day (compute + storage) |

**Cost Breakdown (if running):**
- Compute: ~$48-98/day
- Storage (100GB SSD): ~$1.50/day
- Backups: ~$0.50/day
- **Total:** ~$50-100/day

**Current Savings:** ~$50-100/day by keeping it stopped

---

### 2. Cloud Run Services

**Services:**
- `buildtrace-backend` (2 vCPU, 2 GiB, min 1 instance)
- `buildtrace-frontend` (1 vCPU, 512 MiB, min 0 instances)
- `buildtrace-ocr-worker` (if deployed)
- `buildtrace-diff-worker` (if deployed)
- `buildtrace-summary-worker` (if deployed)

**Estimated Costs:**
- **Backend (always on):** ~$0.20-0.50/day
- **Frontend (on-demand):** ~$0.05-0.20/day
- **Workers (on-demand):** ~$0.10-0.30/day per worker
- **Total:** ~$0.20-1.00/day

**Cost Factors:**
- CPU time: $0.00002400 per vCPU-second
- Memory: $0.00000250 per GiB-second
- Requests: $0.40 per million
- Egress: $0.12 per GB

---

### 3. Cloud Storage

**Buckets:**
| Bucket | Size | Storage Class | Estimated Cost |
|--------|------|---------------|----------------|
| `buildtrace-dev-input-buildtrace-dev` | 1.23 GB | STANDARD | ~$0.03/month |
| `buildtrace-dev-processed-buildtrace-dev` | 0 GB | STANDARD | ~$0.00 |
| `buildtrace-dev-artifacts-buildtrace-dev` | 0 GB | STANDARD | ~$0.00 |
| `buildtrace-dev-logs-buildtrace-dev` | 0 GB | STANDARD | ~$0.00 |

**Total Storage:** ~1.23 GB  
**Estimated Cost:** ~$0.03/month (~$0.001/day)

**Cost Breakdown:**
- Standard storage: $0.023 per GB/month
- Operations: $0.05 per 10,000 operations
- Egress: $0.12 per GB

---

### 4. Pub/Sub

**Topics (7 total):**
- `buildtrace-dev-ocr-queue`
- `buildtrace-dev-diff-queue`
- `buildtrace-dev-summary-queue`
- `buildtrace-dev-orchestrator-queue`
- `buildtrace-dev-ocr-dlq`
- `buildtrace-dev-diff-dlq`
- `buildtrace-dev-summary-dlq`

**Estimated Costs:**
- **Messages:** $0.40 per million messages
- **Storage:** $0.27 per GB/month (if messages retained)
- **Estimated Daily:** ~$0.01-0.10/day (depends on volume)

---

### 5. Artifact Registry

**Repositories (4 total):**
- `buildtrace`
- `buildtrace-base-images`
- `buildtrace-repo`
- `cloud-run-source-deploy`

**Estimated Costs:**
- **Storage:** $0.10 per GB/month
- **Estimated Daily:** ~$0.01/day (depends on image sizes)

---

## 💰 Cost Optimization Recommendations

### Immediate Actions (Already Done)
1. ✅ **Stopped Cloud SQL** - Saving ~$50-100/day

### Additional Optimizations

1. **Cloud Run:**
   - Set min instances to 0 for non-critical services
   - Use Cloud Scheduler to scale down during off-hours
   - Consider smaller instance sizes if possible

2. **Cloud Storage:**
   - Enable lifecycle policies (already configured)
   - Move old data to Nearline/Coldline storage classes
   - Delete unused buckets

3. **Pub/Sub:**
   - Review message volumes
   - Consider batching messages
   - Clean up unused topics

4. **Artifact Registry:**
   - Delete old/unused images
   - Use retention policies

---

## 📈 How to View Exact Costs

### Method 1: GCP Console (Recommended)
```
https://console.cloud.google.com/billing/013DA5-F6D60D-EAB0A7/reports?project=buildtrace-dev
```

### Method 2: Enable Billing Export to BigQuery
1. Go to: Billing > Billing Export
2. Enable export to BigQuery
3. Query:
```sql
SELECT 
  service.description,
  SUM(cost) as total_cost,
  currency
FROM `project.dataset.gcp_billing_export_v1_013DA5_F6D60D_EAB0A7`
WHERE _PARTITIONTIME >= TIMESTAMP('2025-12-07')
  AND _PARTITIONTIME < TIMESTAMP('2025-12-15')
GROUP BY service.description, currency
ORDER BY total_cost DESC
```

### Method 3: Use Scripts
```bash
# Quick cost check
./scripts/get-cost-summary.sh

# Detailed service check
./scripts/check-costs.sh
```

---

## 🎯 Cost Targets

### Current (With Cloud SQL Stopped)
- **Target:** <$2/day
- **Estimated:** $0.37-1.26/day ✅

### If Cloud SQL Running
- **Target:** <$120/day
- **Estimated:** $50-101/day ✅

---

## 📝 Notes

- Costs are estimates based on GCP pricing as of December 2025
- Actual costs may vary based on usage patterns
- Cloud SQL stopped on December 12, 2025
- Check GCP Console for real-time billing data

---

**Last Updated:** December 12, 2025  
**Next Review:** Weekly
