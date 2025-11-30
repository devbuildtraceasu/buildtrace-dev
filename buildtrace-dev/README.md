# BuildTrace Dev

Drawing comparison and change detection system for architectural drawings.

## 📚 Documentation

### Core Documentation
- **[docs/SYSTEM_OVERVIEW.md](./docs/SYSTEM_OVERVIEW.md)** - Complete system overview and repository structure
- **[docs/ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed system architecture
- **[docs/PROGRESS.md](./docs/PROGRESS.md)** - Implementation status and progress
- **[docs/PENDING.md](./docs/PENDING.md)** - Remaining tasks and priorities
- **[docs/FLOW_DIAGRAM.md](./docs/FLOW_DIAGRAM.md)** - Complete data flow diagrams
- **[docs/README.md](./docs/README.md)** - Documentation index

### Deployment & Operations
- **[docs/deployment/QUICK_DEPLOY.md](./docs/deployment/QUICK_DEPLOY.md)** - Quick deployment reference
- **[docs/deployment/DEPLOYMENT_GUIDE.md](./docs/deployment/DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[docs/deployment/DEPLOYMENT_CHECKLIST.md](./docs/deployment/DEPLOYMENT_CHECKLIST.md)** - Deployment checklist
- **[docs/deployment/FINAL_IMAGE_PULL_FIX.md](./docs/deployment/FINAL_IMAGE_PULL_FIX.md)** - Image pull troubleshooting
- **[k8s/README.md](./k8s/README.md)** - Kubernetes worker deployment

### Setup & Configuration
- **[docs/setup/ADD_GEMINI_SECRET.md](./docs/setup/ADD_GEMINI_SECRET.md)** - Gemini secret setup
- **[docs/setup/CLI_SECRET_SETUP.md](./docs/setup/CLI_SECRET_SETUP.md)** - CLI secret setup
- **[docs/setup/OAUTH_SETUP.md](./docs/setup/OAUTH_SETUP.md)** - OAuth setup guide

### Features
- **[docs/features/BOUNDING_BOX_ENHANCEMENT.md](./docs/features/BOUNDING_BOX_ENHANCEMENT.md)** - Bounding box feature
- **[docs/features/OCR_ENHANCEMENT.md](./docs/features/OCR_ENHANCEMENT.md)** - OCR enhancements
- **[docs/features/OUTPUT_LOCATIONS.md](./docs/features/OUTPUT_LOCATIONS.md)** - Output locations reference

### Status & History
- **[docs/DONE.md](./docs/DONE.md)** - Completed work and features
- **[docs/PLANNED.md](./docs/PLANNED.md)** - Future features and enhancements

## 🚀 Quick Start

### Local Development

```bash
# Start all services
docker-compose up

# Backend: http://localhost:5001
# Frontend: http://localhost:3000
```

### GCP Deployment

```bash
# Deploy both backend and frontend
./scripts/deploy-all.sh

# Or deploy individually
./scripts/deploy-frontend.sh                    # Frontend only
DEPLOY_FRONTEND=false ./scripts/DEPLOY_AND_TEST.sh  # Backend only
```

See [docs/deployment/QUICK_DEPLOY.md](./docs/deployment/QUICK_DEPLOY.md) for quick reference or [docs/deployment/DEPLOYMENT_GUIDE.md](./docs/deployment/DEPLOYMENT_GUIDE.md) for complete documentation.

## 📋 Project Status

- ✅ **Development**: Complete
- ✅ **Deployment**: Configured and ready
- ✅ **Testing**: Available

## 🔗 Links

- **Backend API:** https://buildtrace-backend-136394139608.us-west2.run.app
- **Frontend:** https://buildtrace-frontend-136394139608.us-west2.run.app

## 📝 Recent Changes

### 2025-11-29: Repository Organization
- Organized all files into appropriate folders
- Documentation moved to `docs/` with subdirectories
- Scripts consolidated in `scripts/` directory
- Logs moved to `logs/` directory
- See [docs/FILE_ORGANIZATION.md](./docs/FILE_ORGANIZATION.md) for structure

### 2025-11-28: Deployment Configuration Fixed
- Fixed deployment scripts to include frontend deployment
- Added flexible deployment options (deploy all, backend only, or frontend only)
- Created comprehensive deployment documentation
- Both backend and frontend now deploy automatically

### 2025-11-22: JWT Authentication Implementation
- Added JWT token support for cross-domain authentication
- Frontend now stores and sends JWT tokens automatically
- Backend accepts both JWT tokens and session cookies
- See [docs/DONE.md](./docs/DONE.md) for full details
