# Worker Status – December 3, 2025

The Kubernetes worker cluster has been decommissioned. All long‑running processors now execute as **independent Cloud Run services** wired to Pub/Sub pull subscriptions.

## Current Cloud Run Services

| Service | Description | Status | Last Deployed |
| --- | --- | --- | --- |
| `buildtrace-ocr-worker` | Handles Gemini OCR extraction and page slicing | ✅ `gcloud run services list` shows latest revision `00005` serving 100% traffic | 2025‑12‑03 16:38 UTC |
| `buildtrace-diff-worker` | Performs image alignment + overlay generation | ✅ Revision `00007` | 2025‑12‑03 16:50 UTC |
| `buildtrace-summary-worker` | Calls OpenAI/Gemini for AI summaries | ✅ Revision `00008` (token limit hotfix) | 2025‑12‑03 17:43 UTC |

### How to Verify

```bash
gcloud run services list \
  --region=us-west2 \
  --project=buildtrace-dev

# Tail an individual worker
gcloud run logs tail buildtrace-summary-worker \
  --region=us-west2
```

## Recent Health Check

- `a8c2b4e5-9dc5-47a5-aa67-443ff80f7c18` comparison ran end‑to‑end using the Cloud Run workers.
- OCR + Diff logs show streaming messages are picked up immediately after Pub/Sub publish.
- Summary worker now uses a higher `max_completion_tokens` (16k) to avoid truncated JSON outputs. Last run produced a 12‑change report with `finish_reason=stop`.

## Operational Notes

1. **No Kubernetes resources remain.** The `k8s/` manifests are retained for history only; deployment is now purely Cloud Run.
2. **Scaling:** Each worker inherits Cloud Run autoscaling (min 0, max 10). For long jobs set `min-instances=1` via:
   ```bash
   gcloud run services update buildtrace-ocr-worker \
     --region=us-west2 \
     --min-instances=1
   ```
3. **Pub/Sub Credentials:** Workers authenticate with the `buildtrace-service-account` service account; no Workload Identity tweaks required.

## Next Steps

- Continue monitoring Cloud Run metrics (error rate, concurrent requests).
- Optionally delete the obsolete GKE cluster from GCP console to avoid residual charges (already done as of Dec 3).
- Keep `deploy-workers-gke.sh` disabled; use the standard Docker build + `gcloud run deploy` flow documented in `docs/deployment/DEPLOYMENT_GUIDE.md`.
