# BuildTrace Dev

Drawing comparison and change detection system for architectural drawings.

## 📚 Documentation

- **[DONE.md](./DONE.md)** - Completed work and features
- **[PENDING.md](./PENDING.md)** - Current tasks and deployment issues
- **[PLANNED.md](./PLANNED.md)** - Future features and enhancements

## 🚀 Quick Start

### Local Development

```bash
# Start all services
docker-compose up

# Backend: http://localhost:5001
# Frontend: http://localhost:3000
```

### GCP Deployment

See [PENDING.md](./PENDING.md) for current deployment status and issues.

## 📋 Project Status

- ✅ **Development**: Complete
- 🚧 **Deployment**: In Progress (Cloud Run issues)
- ⏳ **Testing**: Pending deployment fixes

## 🔗 Links

- Backend API: `https://buildtrace-backend-136394139608.us-west2.run.app`
- Frontend: `https://buildtrace-frontend-otllaxbiza-wl.a.run.app`

## 📝 Recent Changes (2025-11-22)

### JWT Authentication Implementation
- Added JWT token support for cross-domain authentication
- Frontend now stores and sends JWT tokens automatically
- Backend accepts both JWT tokens and session cookies
- See [DONE.md](./DONE.md) for full details
