# Worker Status - November 29, 2025

## Current Pod States (prod-app namespace)
```
diff-worker-7dc79b98bc-b5xxl   1/1   Running            0      14m
ocr-worker-59cb7dd9d4-789j9    0/1   Running (initial)  0      50s
ocr-worker-9d48655cd-wzpkz     0/1   CrashLoopBackOff   5      6m
summary-worker-6647fb659d-zqcdh 0/1  CrashLoopBackOff   8      18m
summary-worker-77bf6d975b-swkg7 0/1  CrashLoopBackOff   8      18m
```

## Known Issues
1. **OCR Worker**
   - One pod (`59cb7dd9d4-789j9`) starting but will crash once it begins pulling Pub/Sub messages due to insufficient scopes.
   - Second pod stuck in CrashLoop with Pub/Sub access errors.

2. **Summary Workers**
   - Both pods fail with `ACCESS_TOKEN_SCOPE_INSUFFICIENT` when connecting to Pub/Sub.

3. **Root Causes**
   - Cluster originally created without Workload Identity; node SA credentials lack Pub/Sub scopes.
   - Compute default service account missing Pub/Sub roles and GCS bucket permissions (being added now).
   - Image rebuild in progress to include libGL dependencies; latest tag pushed.

## Next Steps
- Finish IAM fixes (artifact registry, GCS, Pub/Sub) for node SA.
- Confirm Workload Identity pool `buildtrace-dev.svc.id.goog` active and SA binding applied.
- Restart workers after IAM propagation (~2-3 minutes) and monitor logs.
- Once pods stable, run full job test.
