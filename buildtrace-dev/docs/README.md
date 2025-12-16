# BuildTrace Documentation

**Last Updated:** November 29, 2025

---

## 📚 Documentation Index

### Core Documentation

1. **[SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)**
   - Complete system summary
   - Repository structure
   - Technology stack
   - Key components
   - Current status

2. **[ARCHITECTURE.md](../ARCHITECTURE.md)**
   - Detailed system architecture
   - Component descriptions
   - Database schema
   - API reference
   - Deployment architecture

3. **[PROGRESS.md](./PROGRESS.md)**
   - Implementation status by phase
   - Completion percentages
   - Statistics and metrics
   - Immediate next steps

4. **[PENDING.md](./PENDING.md)**
   - Remaining tasks
   - Priority ordering
   - Known issues
   - Technical debt

5. **[FLOW_DIAGRAM.md](./FLOW_DIAGRAM.md)**
   - Complete user flow
   - Job processing flow
   - Data storage flow
   - Authentication flow
   - Worker deployment architecture
   - Error handling flow
   - Chatbot flow

---

## 🚀 Quick Start Guides

### For Developers

1. **Local Development Setup**
   - See [README.md](../README.md) for quick start
   - `docker-compose up` to start all services
   - Backend: http://localhost:5001
   - Frontend: http://localhost:3000

2. **Understanding the Codebase**
   - Start with [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
   - Review [ARCHITECTURE.md](../ARCHITECTURE.md) for component details
   - Check [FLOW_DIAGRAM.md](./FLOW_DIAGRAM.md) for data flows

3. **Contributing**
   - Check [PENDING.md](./PENDING.md) for tasks
   - Review [PROGRESS.md](./PROGRESS.md) for current status
   - Follow existing code patterns

### For Operators

1. **Deployment**
   - See [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
   - Worker deployment: [k8s/README.md](../k8s/README.md)
   - Troubleshooting: [IMAGE_PULL_SOLUTION.md](../IMAGE_PULL_SOLUTION.md)

2. **Monitoring**
   - Check [PROGRESS.md](./PROGRESS.md) for monitoring setup status
   - Worker logs: `kubectl logs -f deployment/<worker> -n prod-app`
   - API logs: Cloud Run logs in GCP Console

3. **Troubleshooting**
   - Image pull issues: [FINAL_IMAGE_PULL_FIX.md](../FINAL_IMAGE_PULL_FIX.md)
   - Worker issues: [k8s/README.md](../k8s/README.md)
   - General: [PENDING.md](./PENDING.md) Known Issues section

4. **Cost Management**
   - See [CLOUD_SQL_MANAGEMENT.md](./CLOUD_SQL_MANAGEMENT.md) for detailed guide
   - **Stop Cloud SQL:** `./scripts/stop-cloud-sql.sh` - Stops database to save costs
   - **Start Cloud SQL:** `./scripts/start-cloud-sql.sh` - Restarts database when needed
   - **Note:** Stopping Cloud SQL will cause all services to fail until restarted
   - **Cost Savings:** Compute charges stop immediately; only storage is charged while stopped

---

## 📖 Documentation by Topic

### Architecture & Design
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Complete system architecture
- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) - High-level overview
- [FLOW_DIAGRAM.md](./FLOW_DIAGRAM.md) - Data flow diagrams

### Implementation Status
- [PROGRESS.md](./PROGRESS.md) - Current progress by phase
- [PENDING.md](./PENDING.md) - Remaining tasks
- [DONE.md](../DONE.md) - Completed work
- [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) - Detailed status

### Deployment & Operations
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Deployment instructions
- [QUICK_DEPLOY.md](../QUICK_DEPLOY.md) - Quick deployment reference
- [k8s/README.md](../k8s/README.md) - Kubernetes deployment
- [WORKER_DEPLOYMENT_READY.md](../WORKER_DEPLOYMENT_READY.md) - Worker deployment status
- [CLOUD_SQL_MANAGEMENT.md](./CLOUD_SQL_MANAGEMENT.md) - Cloud SQL instance management (stop/start)

### Troubleshooting
- [FINAL_IMAGE_PULL_FIX.md](../FINAL_IMAGE_PULL_FIX.md) - Image pull issues
- [IMAGE_PULL_SOLUTION.md](../IMAGE_PULL_SOLUTION.md) - Image pull solutions
- [DEPLOYMENT_FIX_SUMMARY.md](../DEPLOYMENT_FIX_SUMMARY.md) - Deployment fixes

### Features
- [CHATBOT_IMPLEMENTATION.md](../backend/CHATBOT_IMPLEMENTATION.md) - Chatbot feature
- [OCR_ENHANCEMENT.md](../OCR_ENHANCEMENT.md) - OCR improvements
- [BOUNDING_BOX_ENHANCEMENT.md](../BOUNDING_BOX_ENHANCEMENT.md) - Bounding box features

---

## 🔍 Finding Information

### By Role

**Developer:**
- Start: [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
- Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Flows: [FLOW_DIAGRAM.md](./FLOW_DIAGRAM.md)
- Tasks: [PENDING.md](./PENDING.md)

**DevOps/Operator:**
- Deployment: [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
- Workers: [k8s/README.md](../k8s/README.md)
- Troubleshooting: [FINAL_IMAGE_PULL_FIX.md](../FINAL_IMAGE_PULL_FIX.md)
- Status: [PROGRESS.md](./PROGRESS.md)

**Product Manager:**
- Overview: [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
- Status: [PROGRESS.md](./PROGRESS.md)
- Roadmap: [PENDING.md](./PENDING.md)
- Features: [DONE.md](../DONE.md)

### By Topic

**Understanding the System:**
- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [FLOW_DIAGRAM.md](./FLOW_DIAGRAM.md)

**Current Status:**
- [PROGRESS.md](./PROGRESS.md)
- [PENDING.md](./PENDING.md)
- [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md)

**Deployment:**
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
- [k8s/README.md](../k8s/README.md)
- [QUICK_DEPLOY.md](../QUICK_DEPLOY.md)

**Troubleshooting:**
- [FINAL_IMAGE_PULL_FIX.md](../FINAL_IMAGE_PULL_FIX.md)
- [IMAGE_PULL_SOLUTION.md](../IMAGE_PULL_SOLUTION.md)
- [PENDING.md](./PENDING.md) - Known Issues section

---

## 📝 Documentation Standards

### Document Structure
- **Header:** Title, version, last updated, status
- **Table of Contents:** For documents > 100 lines
- **Sections:** Clear headings and subheadings
- **Code Blocks:** Syntax highlighting, file paths
- **Diagrams:** ASCII art or Mermaid diagrams
- **Links:** Cross-references to related docs

### Update Frequency
- **Core Docs:** Update when major changes occur
- **Status Docs:** Update weekly or after major milestones
- **Troubleshooting:** Update when issues are resolved
- **Architecture:** Update when architecture changes

### Versioning
- Major version changes: Update version number
- Minor changes: Update "Last Updated" date
- Status changes: Update status indicator

---

## 🔗 External Resources

### Google Cloud Platform
- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)

### Technologies
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

## 📧 Contact & Support

For questions or issues:
1. Check [PENDING.md](./PENDING.md) for known issues
2. Review troubleshooting guides
3. Check [PROGRESS.md](./PROGRESS.md) for current status

---

**Last Updated:** December 12, 2025  
**Maintained by:** BuildTrace Development Team

