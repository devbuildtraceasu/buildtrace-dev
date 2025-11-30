# File Organization Guide

**Created:** November 29, 2025  
**Purpose:** Document the organized file structure

---

## Directory Structure

```
buildtrace-dev/
├── README.md                    # Main project README
├── ARCHITECTURE.md              # System architecture (kept at root for visibility)
├── docker-compose.yml           # Docker Compose configuration
│
├── docs/                        # All documentation
│   ├── README.md                # Documentation index
│   ├── SYSTEM_OVERVIEW.md       # System overview
│   ├── PROGRESS.md              # Implementation progress
│   ├── PENDING.md               # Remaining tasks
│   ├── FLOW_DIAGRAM.md          # Flow diagrams
│   ├── CLEANUP_LOG.md           # Cleanup log
│   ├── FILE_ORGANIZATION.md     # This file
│   │
│   ├── setup/                   # Setup and configuration guides
│   │   ├── ADD_GEMINI_SECRET.md
│   │   ├── CLI_SECRET_SETUP.md
│   │   └── OAUTH_SETUP.md
│   │
│   ├── deployment/              # Deployment documentation
│   │   ├── DEPLOYMENT_CHECKLIST.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── QUICK_DEPLOY.md
│   │   └── FINAL_IMAGE_PULL_FIX.md
│   │
│   ├── features/                # Feature documentation
│   │   ├── BOUNDING_BOX_ENHANCEMENT.md
│   │   ├── OCR_ENHANCEMENT.md
│   │   └── OUTPUT_LOCATIONS.md
│   │
│   ├── status/                  # Status and history
│   │   ├── DONE.md
│   │   └── PLANNED.md
│   │
│   └── DOCUMENTATION_SUMMARY.md # Documentation refactoring summary
│
├── scripts/                     # All executable scripts
│   ├── deploy-workers-gke.sh
│   ├── fix-image-pull.sh
│   ├── restart-nodes-for-image-pull.sh
│   ├── verify-pubsub.sh
│   ├── create_gemini_secret.sh
│   ├── deploy-all.sh
│   ├── deploy-frontend.sh
│   ├── DEPLOY_AND_TEST.sh
│   ├── test_oauth_flow.sh
│   └── test_ssh.sh
│
├── logs/                        # Log files
│   ├── deploy-sync-processing.log
│   ├── deployment.log
│   └── DEPLOYMENT_STATUS.txt
│
├── backend/                     # Backend application
│   └── ...
│
├── frontend/                    # Frontend application
│   └── ...
│
├── k8s/                         # Kubernetes manifests
│   └── ...
│
└── post_git_push/               # Git-related files
    └── ...
```

---

## File Organization Rules

### Root Directory
**Keep at root:**
- `README.md` - Main project README
- `ARCHITECTURE.md` - System architecture (kept for visibility)
- `docker-compose.yml` - Docker Compose configuration

### Documentation (`docs/`)
- **Core docs:** System overview, progress, pending tasks, flow diagrams
- **Setup guides:** Configuration and setup instructions
- **Deployment docs:** Deployment guides and checklists
- **Feature docs:** Feature-specific documentation
- **Status docs:** Completed work and planned features

### Scripts (`scripts/`)
- All executable shell scripts
- Deployment scripts
- Test scripts
- Utility scripts

### Logs (`logs/`)
- Deployment logs
- Processing logs
- Status files

### Backend (`backend/`)
- Application code
- Tests
- Backend-specific documentation

### Frontend (`frontend/`)
- Application code
- Frontend-specific files

### Kubernetes (`k8s/`)
- Kubernetes manifests
- Deployment configurations

---

## Migration Summary

### Files Moved

**Documentation → `docs/`:**
- Setup guides → `docs/setup/`
- Deployment docs → `docs/deployment/`
- Feature docs → `docs/features/`
- Status docs → `docs/`

**Scripts → `scripts/`:**
- All `.sh` scripts moved to `scripts/`

**Logs → `logs/`:**
- All `.log` files and status files moved to `logs/`

---

## Benefits

1. **Clear Organization:** Files grouped by purpose
2. **Easy Navigation:** Logical folder structure
3. **Reduced Clutter:** Root directory contains only essential files
4. **Better Maintainability:** Related files grouped together
5. **Scalability:** Easy to add new files in appropriate locations

---

## Updating References

If any files reference moved files, update paths:
- Documentation links
- Script paths in documentation
- CI/CD scripts
- README files

---

**Status:** ✅ File organization complete  
**Last Updated:** November 29, 2025

