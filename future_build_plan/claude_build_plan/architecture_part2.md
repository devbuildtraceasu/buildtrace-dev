# BuildTrace Architecture v4 - Part 2: Frontend, Deployment & Implementation
## Codebase-Aware Next Version (Flask-Based with Page-Level Pub/Sub)

_Last updated: November 18, 2025_

This is Part 2 of the architecture document, covering frontend design, GKE deployment, and implementation roadmap.

---

## 6. Frontend Architecture (Based on Design Screenshots)

### 6.1 Frontend Design Analysis

Based on the provided screenshots, the new frontend design features:

**Key UI Elements:**
1. **Project Dashboard**: Grid/list view of projects with status indicators
2. **Drawing Versions**: Timeline/list view showing version history
3. **Comparison Initiation**: Select two versions to compare
4. **Vertical Carousel**: Scrollable list of comparison results (main innovation!)
5. **Real-Time Progress**: Progress bars and status indicators
6. **Comparison Cards**: Individual cards showing:
   - Drawing name (e.g., "A-101")
   - Thumbnail/preview of overlay
   - Status badge (Processing, Complete, Failed)
   - Summary excerpt
   - Change count
   - Actions (View Details, Download, etc.)
7. **Detail View**: Full-screen comparison with:
   - Side-by-side viewers
   - Overlay editor
   - Change list
   - AI assistant chat
   - Manual corrections

### 6.2 Frontend Technology Stack

```typescript
// Keep from demo-frontend
- React 18.3.1
- TypeScript 5.6.3
- Vite 5.4.19
- Zustand (state management)
- React Query (server state)
- Tailwind CSS + shadcn/ui
- WebSocket client (socket.io-client)
- PDF.js (drawing viewing)
```

### 6.3 Frontend Structure

```typescript
buildtrace-frontend/
├── src/
│   ├── pages/
│   │   ├── Landing.tsx                     # Public landing page
│   │   ├── Dashboard.tsx                   # Project dashboard (NEW)
│   │   ├── projects/
│   │   │   ├── ProjectsList.tsx            # Grid/list of projects (NEW)
│   │   │   ├── ProjectDetail.tsx           # Single project view (NEW)
│   │   │   ├── CreateProject.tsx           # Create project dialog
│   │   │   └── ProjectSettings.tsx         # Project settings page
│   │   ├── drawings/
│   │   │   ├── DrawingVersions.tsx         # Version timeline (NEW)
│   │   │   ├── UploadDrawing.tsx           # Upload new version
│   │   │   └── CompareVersions.tsx         # Select versions to compare
│   │   ├── comparisons/
│   │   │   ├── ComparisonSession.tsx       # Main comparison view (NEW)
│   │   │   │   → Vertical carousel of results
│   │   │   │   → Real-time progress updates
│   │   │   ├── ComparisonDetail.tsx        # Full-screen detail view
│   │   │   └── ComparisonHistory.tsx       # Past comparisons
│   │   └── profile/
│   │       └── UserProfile.tsx             # User settings
│   ├── components/
│   │   ├── projects/
│   │   │   ├── ProjectCard.tsx             # Project card with stats
│   │   │   ├── ProjectGrid.tsx             # Responsive grid layout
│   │   │   └── CreateProjectDialog.tsx
│   │   ├── drawings/
│   │   │   ├── DrawingVersionCard.tsx      # Version card with metadata
│   │   │   ├── VersionTimeline.tsx         # Visual timeline
│   │   │   └── CompareVersionsDialog.tsx   # Version selector
│   │   ├── comparisons/
│   │   │   ├── ComparisonCarousel.tsx      # MAIN: Vertical carousel (NEW)
│   │   │   ├── ComparisonCard.tsx          # Individual result card (NEW)
│   │   │   ├── ProgressBar.tsx             # Stage progress (OCR/Diff/Summary)
│   │   │   ├── StatusBadge.tsx             # Status indicator
│   │   │   ├── ComparisonViewers.tsx       # PDF/overlay viewers
│   │   │   ├── OverlayEditor.tsx           # Manual editing canvas
│   │   │   ├── ChangesList.tsx             # Detected changes list
│   │   │   ├── AskPanel.tsx                # AI assistant chat
│   │   │   └── SummarySection.tsx          # AI-generated summary
│   │   ├── common/
│   │   │   ├── AppLayout.tsx               # Main layout with nav
│   │   │   ├── Sidebar.tsx                 # Navigation sidebar
│   │   │   ├── Header.tsx                  # Top header with user menu
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   └── WebSocketIndicator.tsx      # Connection status
│   │   └── ui/                             # shadcn/ui components
│   ├── features/
│   │   ├── projects/
│   │   │   ├── hooks/
│   │   │   │   ├── useProjects.ts          # React Query hooks
│   │   │   │   └── useProjectStore.ts      # Zustand store
│   │   │   ├── services/
│   │   │   │   └── projectService.ts       # API calls
│   │   │   └── types.ts
│   │   ├── drawings/
│   │   │   ├── hooks/
│   │   │   │   ├── useDrawingVersions.ts
│   │   │   │   └── useDrawingStore.ts
│   │   │   ├── services/
│   │   │   │   └── drawingService.ts
│   │   │   └── types.ts
│   │   ├── comparisons/
│   │   │   ├── hooks/
│   │   │   │   ├── useComparisonSession.ts  # Main session hook (NEW)
│   │   │   │   ├── useWebSocket.ts          # WebSocket connection (NEW)
│   │   │   │   ├── useComparisonStore.ts    # Enhanced store
│   │   │   │   └── useRealtimeProgress.ts   # Real-time updates (NEW)
│   │   │   ├── services/
│   │   │   │   ├── comparisonService.ts
│   │   │   │   ├── overlayService.ts
│   │   │   │   └── websocketService.ts      # WebSocket client (NEW)
│   │   │   └── types.ts
│   │   └── auth/
│   │       ├── hooks/
│   │       │   └── useAuth.ts
│   │       └── services/
│   │           └── authService.ts
│   ├── lib/
│   │   ├── api.ts                          # HTTP client (Axios/Fetch)
│   │   ├── websocket.ts                    # Socket.io client
│   │   ├── supabaseClient.ts               # Supabase auth
│   │   └── utils.ts
│   └── types/
│       ├── api.ts                          # API response types
│       ├── models.ts                       # Domain models
│       └── websocket.ts                    # WebSocket event types
```

### 6.4 Key Frontend Components

#### 6.4.1 ComparisonCarousel.tsx (Main Innovation)

```typescript
// components/comparisons/ComparisonCarousel.tsx

import React, { useEffect, useState } from 'react';
import { useWebSocket } from '@/features/comparisons/hooks/useWebSocket';
import ComparisonCard from './ComparisonCard';
import ProgressBar from './ProgressBar';

interface ComparisonCarouselProps {
  sessionId: string;
}

export function ComparisonCarousel({ sessionId }: ComparisonCarouselProps) {
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [progress, setProgress] = useState({
    ocr: { total: 0, completed: 0 },
    diff: { total: 0, completed: 0 },
    summary: { total: 0, completed: 0 }
  });
  
  // WebSocket connection for real-time updates
  const { isConnected, events } = useWebSocket(sessionId);
  
  useEffect(() => {
    // Listen for real-time events
    events.on('page_ocr_complete', (data) => {
      setProgress(prev => ({
        ...prev,
        ocr: { ...prev.ocr, completed: prev.ocr.completed + 1 }
      }));
    });
    
    events.on('pair_diff_complete', (data) => {
      // Add new comparison to carousel!
      const newComparison: Comparison = {
        id: data.comparison_id,
        drawingName: data.drawing_name,
        overlayUrl: data.overlay_url,
        status: 'processing', // Summary not ready yet
        alignmentScore: data.alignment_score
      };
      
      setComparisons(prev => [...prev, newComparison]);
      
      setProgress(prev => ({
        ...prev,
        diff: { ...prev.diff, completed: prev.diff.completed + 1 }
      }));
    });
    
    events.on('summary_complete', (data) => {
      // Update existing comparison with summary
      setComparisons(prev => prev.map(comp => 
        comp.drawingName === data.drawing_name
          ? {
              ...comp,
              status: 'completed',
              summary: data.summary,
              changesCount: data.changes_count,
              criticalChange: data.critical_change
            }
          : comp
      ));
      
      setProgress(prev => ({
        ...prev,
        summary: { ...prev.summary, completed: prev.summary.completed + 1 }
      }));
    });
    
    events.on('session_complete', () => {
      toast.success('All comparisons complete!');
    });
    
    return () => {
      events.removeAllListeners();
    };
  }, [events]);
  
  return (
    <div className="flex flex-col h-screen">
      {/* Header with progress */}
      <div className="sticky top-0 bg-white border-b p-4 z-10">
        <h1 className="text-2xl font-bold mb-4">Comparison Results</h1>
        
        <div className="space-y-2">
          <ProgressBar
            label="OCR Processing"
            current={progress.ocr.completed}
            total={progress.ocr.total}
          />
          <ProgressBar
            label="Alignment & Diff"
            current={progress.diff.completed}
            total={progress.diff.total}
          />
          <ProgressBar
            label="AI Analysis"
            current={progress.summary.completed}
            total={progress.summary.total}
          />
        </div>
        
        <div className="flex items-center gap-2 mt-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      {/* Vertical carousel of results */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {comparisons.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Loader2 className="w-8 h-8 animate-spin mb-4" />
            <p>Processing drawings...</p>
            <p className="text-sm">Results will appear here as pages complete</p>
          </div>
        ) : (
          comparisons.map((comparison) => (
            <ComparisonCard
              key={comparison.id}
              comparison={comparison}
              onClick={() => navigate(`/comparisons/${comparison.id}`)}
            />
          ))
        )}
      </div>
    </div>
  );
}
```

#### 6.4.2 ComparisonCard.tsx

```typescript
// components/comparisons/ComparisonCard.tsx

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Download, Edit } from 'lucide-react';

interface ComparisonCardProps {
  comparison: Comparison;
  onClick: () => void;
}

export function ComparisonCard({ comparison, onClick }: ComparisonCardProps) {
  const statusColors = {
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  };
  
  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer" onClick={onClick}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className="text-xl">{comparison.drawingName}</CardTitle>
          <Badge className={statusColors[comparison.status]}>
            {comparison.status}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          {/* Overlay preview */}
          <div className="col-span-1">
            {comparison.overlayUrl ? (
              <img
                src={comparison.overlayUrl}
                alt={`${comparison.drawingName} overlay`}
                className="w-full h-32 object-cover rounded border"
              />
            ) : (
              <div className="w-full h-32 bg-gray-100 rounded border flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            )}
          </div>
          
          {/* Summary & stats */}
          <div className="col-span-2 space-y-2">
            {comparison.summary ? (
              <>
                <p className="text-sm text-gray-600 line-clamp-2">
                  {comparison.summary}
                </p>
                
                <div className="flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1">
                    <span className="font-semibold">{comparison.changesCount}</span>
                    <span className="text-gray-600">changes</span>
                  </span>
                  
                  {comparison.alignmentScore && (
                    <span className="flex items-center gap-1">
                      <span className="font-semibold">
                        {(comparison.alignmentScore * 100).toFixed(0)}%
                      </span>
                      <span className="text-gray-600">aligned</span>
                    </span>
                  )}
                </div>
                
                {comparison.criticalChange && (
                  <div className="bg-red-50 border border-red-200 rounded p-2 text-sm">
                    <span className="font-semibold text-red-800">Critical: </span>
                    <span className="text-red-700">{comparison.criticalChange}</span>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Generating summary...</span>
              </div>
            )}
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <Button size="sm" variant="default">
            <Eye className="w-4 h-4 mr-1" />
            View Details
          </Button>
          <Button size="sm" variant="outline">
            <Edit className="w-4 h-4 mr-1" />
            Edit Overlay
          </Button>
          <Button size="sm" variant="outline">
            <Download className="w-4 h-4 mr-1" />
            Download
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### 6.4.3 useWebSocket.ts Hook

```typescript
// features/comparisons/hooks/useWebSocket.ts

import { useEffect, useState, useRef } from 'react';
import io, { Socket } from 'socket.io-client';

export function useWebSocket(sessionId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  
  useEffect(() => {
    // Connect to Flask-SocketIO
    const socket = io(import.meta.env.VITE_API_URL, {
      transports: ['websocket', 'polling'],
      auth: {
        token: localStorage.getItem('auth_token')
      }
    });
    
    socketRef.current = socket;
    
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      
      // Join session room
      socket.emit('join_session', { session_id: sessionId });
    });
    
    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });
    
    socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
    
    return () => {
      if (socketRef.current) {
        socketRef.current.emit('leave_session', { session_id: sessionId });
        socketRef.current.disconnect();
      }
    };
  }, [sessionId]);
  
  return {
    isConnected,
    socket: socketRef.current,
    events: socketRef.current
  };
}
```

#### 6.4.4 useRealtimeProgress.ts Hook

```typescript
// features/comparisons/hooks/useRealtimeProgress.ts

import { useEffect, useState } from 'react';
import { useWebSocket } from './useWebSocket';

interface Progress {
  ocr: { total: number; completed: number; percentage: number };
  diff: { total: number; completed: number; percentage: number };
  summary: { total: number; completed: number; percentage: number };
}

export function useRealtimeProgress(sessionId: string) {
  const [progress, setProgress] = useState<Progress>({
    ocr: { total: 0, completed: 0, percentage: 0 },
    diff: { total: 0, completed: 0, percentage: 0 },
    summary: { total: 0, completed: 0, percentage: 0 }
  });
  
  const { events } = useWebSocket(sessionId);
  
  useEffect(() => {
    // Fetch initial progress
    fetch(`/api/sessions/${sessionId}`)
      .then(res => res.json())
      .then(data => {
        setProgress(data.progress);
      });
    
    // Listen for real-time updates
    events?.on('page_ocr_complete', () => {
      setProgress(prev => ({
        ...prev,
        ocr: {
          ...prev.ocr,
          completed: prev.ocr.completed + 1,
          percentage: ((prev.ocr.completed + 1) / prev.ocr.total) * 100
        }
      }));
    });
    
    events?.on('pair_diff_complete', () => {
      setProgress(prev => ({
        ...prev,
        diff: {
          ...prev.diff,
          completed: prev.diff.completed + 1,
          percentage: ((prev.diff.completed + 1) / prev.diff.total) * 100
        }
      }));
    });
    
    events?.on('summary_complete', () => {
      setProgress(prev => ({
        ...prev,
        summary: {
          ...prev.summary,
          completed: prev.summary.completed + 1,
          percentage: ((prev.summary.completed + 1) / prev.summary.total) * 100
        }
      }));
    });
    
    return () => {
      events?.removeAllListeners();
    };
  }, [sessionId, events]);
  
  return progress;
}
```

---

## 7. GKE Deployment Architecture

### 7.1 Cluster Configuration

```yaml
# gke-cluster.yaml
apiVersion: container.cnrm.cloud.google.com/v1beta1
kind: ContainerCluster
metadata:
  name: buildtrace-prod
spec:
  location: us-central1
  initialNodeCount: 1
  removeDefaultNodePool: true
  releaseChannel:
    channel: REGULAR
  networkingMode: VPC_NATIVE
  ipAllocationPolicy:
    useIpAliases: true
  addonsConfig:
    httpLoadBalancing:
      disabled: false
    networkPolicyConfig:
      disabled: false
  networkPolicy:
    enabled: true
    provider: CALICO
  workloadIdentityConfig:
    workloadPool: buildtrace.svc.id.goog
```

### 7.2 Node Pools

```yaml
# node-pools.yaml

---
# Web/API node pool
apiVersion: container.cnrm.cloud.google.com/v1beta1
kind: ContainerNodePool
metadata:
  name: web-standard
spec:
  clusterRef:
    name: buildtrace-prod
  location: us-central1
  initialNodeCount: 2
  autoscaling:
    enabled: true
    minNodeCount: 2
    maxNodeCount: 5
  management:
    autoRepair: true
    autoUpgrade: true
  nodeConfig:
    machineType: n1-standard-4
    diskSizeGb: 50
    diskType: pd-standard
    oauthScopes:
      - https://www.googleapis.com/auth/cloud-platform
    labels:
      node-pool: web-standard
    tags:
      - buildtrace-web

---
# Worker node pool (CPU-optimized)
apiVersion: container.cnrm.cloud.google.com/v1beta1
kind: ContainerNodePool
metadata:
  name: workers-cpu
spec:
  clusterRef:
    name: buildtrace-prod
  location: us-central1
  initialNodeCount: 3
  autoscaling:
    enabled: true
    minNodeCount: 1
    maxNodeCount: 10
  management:
    autoRepair: true
    autoUpgrade: true
  nodeConfig:
    machineType: n1-highcpu-8
    diskSizeGb: 100
    diskType: pd-standard
    oauthScopes:
      - https://www.googleapis.com/auth/cloud-platform
    labels:
      node-pool: workers-cpu
    tags:
      - buildtrace-workers
```

### 7.3 Kubernetes Deployments

#### 7.3.1 API Service Deployment

```yaml
# deployments/api-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: prod-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
    spec:
      nodeSelector:
        node-pool: web-standard
      containers:
      - name: api
        image: gcr.io/buildtrace/api-service:latest
        ports:
        - containerPort: 5000
          name: http
        - containerPort: 5000
          name: websocket
          protocol: TCP
        env:
        - name: FLASK_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: GCP_PROJECT_ID
          value: "buildtrace"
        - name: GCS_BUCKET_NAME
          value: "buildtrace-prod-drawings"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: prod-app
spec:
  selector:
    app: api-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
    name: http
  type: ClusterIP
```

#### 7.3.2 OCR Worker Deployment

```yaml
# deployments/ocr-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocr-worker
  namespace: prod-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ocr-worker
  template:
    metadata:
      labels:
        app: ocr-worker
    spec:
      nodeSelector:
        node-pool: workers-cpu
      containers:
      - name: worker
        image: gcr.io/buildtrace/ocr-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: GCP_PROJECT_ID
          value: "buildtrace"
        - name: WORKER_TYPE
          value: "ocr"
        resources:
          requests:
            memory: "8Gi"
            cpu: "4000m"
          limits:
            memory: "16Gi"
            cpu: "8000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 30

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ocr-worker-hpa
  namespace: prod-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ocr-worker
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 7.3.3 Diff Worker Deployment

```yaml
# deployments/diff-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: diff-worker
  namespace: prod-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: diff-worker
  template:
    metadata:
      labels:
        app: diff-worker
    spec:
      nodeSelector:
        node-pool: workers-cpu
      containers:
      - name: worker
        image: gcr.io/buildtrace/diff-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: GCP_PROJECT_ID
          value: "buildtrace"
        - name: WORKER_TYPE
          value: "diff"
        resources:
          requests:
            memory: "8Gi"
            cpu: "4000m"
          limits:
            memory: "16Gi"
            cpu: "8000m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: diff-worker-hpa
  namespace: prod-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: diff-worker
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### 7.3.4 Summary Worker Deployment

```yaml
# deployments/summary-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: summary-worker
  namespace: prod-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: summary-worker
  template:
    metadata:
      labels:
        app: summary-worker
    spec:
      nodeSelector:
        node-pool: workers-cpu
      containers:
      - name: worker
        image: gcr.io/buildtrace/summary-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: GCP_PROJECT_ID
          value: "buildtrace"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-credentials
              key: api_key
        - name: WORKER_TYPE
          value: "summary"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: summary-worker-hpa
  namespace: prod-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: summary-worker
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

#### 7.3.5 Orchestrator Deployment

```yaml
# deployments/orchestrator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: prod-app
spec:
  replicas: 2  # For high availability
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      nodeSelector:
        node-pool: web-standard
      containers:
      - name: orchestrator
        image: gcr.io/buildtrace/orchestrator:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: GCP_PROJECT_ID
          value: "buildtrace"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: prod-app
spec:
  selector:
    app: orchestrator
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8084
  type: ClusterIP
```

#### 7.3.6 Frontend Deployment

```yaml
# deployments/frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: prod-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      nodeSelector:
        node-pool: web-standard
      containers:
      - name: nginx
        image: gcr.io/buildtrace/frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: prod-app
spec:
  selector:
    app: frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

### 7.4 Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: buildtrace-ingress
  namespace: prod-app
  annotations:
    kubernetes.io/ingress.class: "gce"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    kubernetes.io/ingress.global-static-ip-name: "buildtrace-ip"
    networking.gke.io/managed-certificates: "buildtrace-cert"
spec:
  tls:
  - hosts:
    - api.buildtrace.ai
    - app.buildtrace.ai
    secretName: buildtrace-tls
  rules:
  - host: api.buildtrace.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
  - host: app.buildtrace.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

### 7.5 Pub/Sub Topics & Subscriptions

```bash
# setup-pubsub.sh

#!/bin/bash

PROJECT_ID="buildtrace"

# Create topics
gcloud pubsub topics create ocr-pages-topic --project=$PROJECT_ID
gcloud pubsub topics create diff-pairs-topic --project=$PROJECT_ID
gcloud pubsub topics create summary-overlays-topic --project=$PROJECT_ID
gcloud pubsub topics create ocr-completions-topic --project=$PROJECT_ID
gcloud pubsub topics create diff-completions-topic --project=$PROJECT_ID
gcloud pubsub topics create summary-completions-topic --project=$PROJECT_ID

# Create subscriptions for workers
gcloud pubsub subscriptions create ocr-worker-sub \
    --topic=ocr-pages-topic \
    --ack-deadline=600 \
    --message-retention-duration=7d \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create diff-worker-sub \
    --topic=diff-pairs-topic \
    --ack-deadline=600 \
    --message-retention-duration=7d \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create summary-worker-sub \
    --topic=summary-overlays-topic \
    --ack-deadline=600 \
    --message-retention-duration=7d \
    --project=$PROJECT_ID

# Create subscriptions for orchestrator
gcloud pubsub subscriptions create ocr-completions-sub \
    --topic=ocr-completions-topic \
    --ack-deadline=60 \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create diff-completions-sub \
    --topic=diff-completions-topic \
    --ack-deadline=60 \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create summary-completions-sub \
    --topic=summary-completions-topic \
    --ack-deadline=60 \
    --project=$PROJECT_ID

echo "Pub/Sub setup complete!"
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Database schema and worker extraction

**Tasks**:
- [ ] Create new database tables (`page_jobs`, `page_results`, `manual_overlays`, `change_summaries`)
- [ ] Run database migration scripts
- [ ] Update SQLAlchemy models
- [ ] Extract OCR worker from existing code
- [ ] Extract Diff worker from existing code
- [ ] Extract Summary worker from existing code
- [ ] Test workers locally with mock Pub/Sub

**Deliverables**:
- ✅ Updated database schema
- ✅ Three worker services (OCR, Diff, Summary)
- ✅ Unit tests for each worker

### Phase 2: Pub/Sub Integration (Weeks 3-4)

**Goal**: Set up Pub/Sub messaging and orchestrator

**Tasks**:
- [ ] Set up GCP Pub/Sub topics and subscriptions
- [ ] Implement Pub/Sub publisher in workers
- [ ] Build orchestrator service
- [ ] Implement completion event handlers
- [ ] Test end-to-end page-level processing
- [ ] Add retry logic and error handling

**Deliverables**:
- ✅ Working Pub/Sub infrastructure
- ✅ Orchestrator service
- ✅ Integration tests

### Phase 3: Flask API Enhancement (Weeks 5-6)

**Goal**: Enhance API with WebSocket and new endpoints

**Tasks**:
- [ ] Add Flask-SocketIO to API service
- [ ] Implement WebSocket event broadcasting
- [ ] Add project management endpoints
- [ ] Add drawing version endpoints
- [ ] Update comparison creation endpoint (page-level jobs)
- [ ] Add manual overlay endpoints
- [ ] Test WebSocket connections

**Deliverables**:
- ✅ Enhanced Flask API
- ✅ WebSocket support
- ✅ API documentation

### Phase 4: Frontend Development (Weeks 7-8)

**Goal**: Build new frontend with vertical carousel

**Tasks**:
- [ ] Set up React project structure
- [ ] Build project management pages
- [ ] Build drawing version pages
- [ ] Implement WebSocket client
- [ ] Build `ComparisonCarousel` component
- [ ] Build `ComparisonCard` component
- [ ] Implement real-time progress updates
- [ ] Add manual overlay editor
- [ ] Build detail view
- [ ] Polish UI/UX

**Deliverables**:
- ✅ Complete React frontend
- ✅ Real-time updates working
- ✅ Vertical carousel populated incrementally

### Phase 5: GKE Deployment (Weeks 9-10)

**Goal**: Deploy to GKE with monitoring

**Tasks**:
- [ ] Create GKE cluster
- [ ] Configure node pools
- [ ] Set up namespaces
- [ ] Create Docker images for all services
- [ ] Push images to GCR
- [ ] Deploy Kubernetes manifests
- [ ] Configure Ingress and Load Balancer
- [ ] Set up Cloud SQL connection
- [ ] Configure GCS buckets
- [ ] Set up Prometheus monitoring
- [ ] Set up Grafana dashboards
- [ ] Configure alerting rules
- [ ] Set up CI/CD pipeline (Cloud Build)

**Deliverables**:
- ✅ Production GKE deployment
- ✅ Monitoring and alerting
- ✅ CI/CD pipeline

### Phase 6: Testing & Optimization (Weeks 11-12)

**Goal**: Load testing and performance tuning

**Tasks**:
- [ ] Load test with concurrent uploads
- [ ] Test worker auto-scaling
- [ ] Optimize database queries
- [ ] Implement caching (Redis)
- [ ] Optimize image processing
- [ ] Add database indexes
- [ ] Security audit
- [ ] Documentation
- [ ] Training materials

**Deliverables**:
- ✅ Performance benchmarks
- ✅ Optimization improvements
- ✅ Complete documentation

---

## 9. Monitoring & Observability

### 9.1 Prometheus Metrics

```python
# metrics.py (Add to each service)

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Job metrics
jobs_enqueued = Counter(
    'buildtrace_jobs_enqueued_total',
    'Total jobs enqueued',
    ['job_type']
)

jobs_completed = Counter(
    'buildtrace_jobs_completed_total',
    'Total jobs completed',
    ['job_type']
)

jobs_failed = Counter(
    'buildtrace_jobs_failed_total',
    'Total jobs failed',
    ['job_type', 'error_type']
)

# Processing time
job_duration = Histogram(
    'buildtrace_job_duration_seconds',
    'Job processing duration',
    ['job_type'],
    buckets=[10, 30, 60, 120, 300, 600]
)

# Queue depth
queue_depth = Gauge(
    'buildtrace_queue_depth',
    'Number of pending jobs in queue',
    ['job_type']
)

# WebSocket connections
websocket_connections = Gauge(
    'buildtrace_websocket_connections',
    'Number of active WebSocket connections'
)

# API metrics
api_requests = Counter(
    'buildtrace_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_latency = Histogram(
    'buildtrace_api_latency_seconds',
    'API request latency',
    ['endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)
```

### 9.2 Grafana Dashboards

**Dashboard 1: System Overview**
```json
{
  "title": "BuildTrace System Overview",
  "panels": [
    {
      "title": "Jobs Processed (24h)",
      "targets": [
        {
          "expr": "sum(rate(buildtrace_jobs_completed_total[24h])) by (job_type)"
        }
      ]
    },
    {
      "title": "Queue Depth",
      "targets": [
        {
          "expr": "buildtrace_queue_depth"
        }
      ]
    },
    {
      "title": "Error Rate",
      "targets": [
        {
          "expr": "rate(buildtrace_jobs_failed_total[5m])"
        }
      ]
    },
    {
      "title": "Active WebSocket Connections",
      "targets": [
        {
          "expr": "buildtrace_websocket_connections"
        }
      ]
    }
  ]
}
```

**Dashboard 2: Processing Pipeline**
```json
{
  "title": "BuildTrace Processing Pipeline",
  "panels": [
    {
      "title": "OCR Processing Time (p95)",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(buildtrace_job_duration_seconds_bucket{job_type='ocr'}[5m]))"
        }
      ]
    },
    {
      "title": "Diff Processing Time (p95)",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(buildtrace_job_duration_seconds_bucket{job_type='diff'}[5m]))"
        }
      ]
    },
    {
      "title": "Summary Processing Time (p95)",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(buildtrace_job_duration_seconds_bucket{job_type='summary'}[5m]))"
        }
      ]
    }
  ]
}
```

### 9.3 Alerting Rules

```yaml
# alerts.yaml
groups:
- name: buildtrace
  rules:
  - alert: HighJobFailureRate
    expr: rate(buildtrace_jobs_failed_total[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High job failure rate detected"
      description: "Job failure rate is {{ $value }} per second"
      
  - alert: LongQueueDepth
    expr: buildtrace_queue_depth > 100
    for: 10m
    annotations:
      summary: "Queue depth is high"
      description: "Queue depth is {{ $value }}"
      
  - alert: SlowProcessing
    expr: histogram_quantile(0.95, buildtrace_job_duration_seconds) > 600
    for: 5m
    annotations:
      summary: "Jobs taking too long"
      description: "95th percentile job duration is {{ $value }} seconds"
      
  - alert: HighAPILatency
    expr: histogram_quantile(0.95, buildtrace_api_latency_seconds) > 5
    for: 5m
    annotations:
      summary: "API latency is high"
      description: "95th percentile API latency is {{ $value }} seconds"
      
  - alert: WebSocketConnectionsDrop
    expr: rate(buildtrace_websocket_connections[5m]) < -10
    for: 2m
    annotations:
      summary: "WebSocket connections dropping rapidly"
      description: "WebSocket connections decreased by {{ $value }} in last 5 minutes"
```

---

## 10. Cost Estimation

### 10.1 GKE Costs

**Node Pools**:
- **web-standard**: n1-standard-4 × 3 nodes × $0.19/hour × 730 hours = ~$417/month
- **workers-cpu**: n1-highcpu-8 × 5 nodes (avg) × $0.30/hour × 730 hours = ~$1,095/month
- **Total GKE**: ~$1,512/month

### 10.2 Other GCP Costs

- **Cloud SQL** (db-n1-standard-2): ~$150/month
- **GCS Storage** (1TB): ~$20/month
- **Pub/Sub**: ~$40/month (10M messages)
- **Load Balancer**: ~$18/month
- **Cloud Monitoring**: ~$50/month

**Total Monthly Cost**: ~$1,790/month

### 10.3 Cost Optimization Strategies

1. **Preemptible VMs** for worker nodes: Save 60-80%
2. **Auto-scaling** to scale down during off-hours
3. **GCS Lifecycle Policies**: Move old data to Nearline storage
4. **Committed Use Discounts**: 37% savings on 1-year commit

**Optimized Monthly Cost**: ~$1,000/month

---

## 11. Security Checklist

- [ ] Enable GKE Workload Identity
- [ ] Use Secret Manager for credentials
- [ ] Enable Cloud SQL IAM authentication
- [ ] Implement RBAC in Kubernetes
- [ ] Enable network policies
- [ ] Use TLS for all external traffic
- [ ] Scan Docker images for vulnerabilities
- [ ] Implement rate limiting on API
- [ ] Enable audit logging
- [ ] Set up DDoS protection (Cloud Armor)

---

## 12. Testing Strategy

### 12.1 Unit Tests

```python
# tests/test_workers.py

def test_ocr_worker_processes_page():
    """Test OCR worker extracts drawing name and creates PNG"""
    # Mock Pub/Sub message
    message = {
        'page_job_id': 'test-job-123',
        'drawing_id': 'drawing-456',
        'page_number': 0,
        'storage_path': 'gs://test/drawing.pdf'
    }
    
    result = process_ocr_message(message)
    
    assert result.drawing_name == 'A-101'
    assert result.png_path is not None

def test_diff_worker_creates_overlay():
    """Test diff worker aligns and creates overlay"""
    # Test implementation
    pass

def test_summary_worker_generates_summary():
    """Test summary worker calls OpenAI and formats results"""
    # Test implementation
    pass
```

### 12.2 Integration Tests

```python
# tests/integration/test_pipeline.py

async def test_complete_pipeline():
    """Test full pipeline from upload to summary"""
    # 1. Upload files
    session_id = await upload_comparison(old_pdf, new_pdf)
    
    # 2. Wait for OCR completion
    await wait_for_stage('ocr', session_id, timeout=300)
    
    # 3. Check diff results
    comparisons = await get_comparisons(session_id)
    assert len(comparisons) > 0
    
    # 4. Wait for summaries
    await wait_for_stage('summary', session_id, timeout=300)
    
    # 5. Verify results
    session = await get_session(session_id)
    assert session.status == 'completed'
```

### 12.3 Load Tests

```python
# tests/load/locustfile.py

from locust import HttpUser, task, between

class BuildTraceUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def create_comparison(self):
        files = {
            'baseline': open('test_data/old.pdf', 'rb'),
            'revised': open('test_data/new.pdf', 'rb')
        }
        self.client.post('/api/comparisons', files=files)
    
    @task
    def check_status(self):
        session_id = self.session_id  # From previous create
        self.client.get(f'/api/sessions/{session_id}')
```

Run: `locust -f tests/load/locustfile.py --users 50 --spawn-rate 5`

---

## 13. Next Steps

1. **Review this architecture** with team
2. **Validate frontend design** against screenshots
3. **Create detailed Jira tickets** from roadmap
4. **Set up development environment**
5. **Start Phase 1**: Database migration

---

## 14. Conclusion

This architecture provides:

✅ **Flask-based implementation** (team familiarity)
✅ **Page-level Pub/Sub processing** (real-time progress)
✅ **Vertical carousel frontend** (incremental results)
✅ **GKE deployment** (scalable, production-ready)
✅ **12-week implementation plan** (realistic timeline)
✅ **Comprehensive monitoring** (Prometheus + Grafana)
✅ **Cost-optimized** (~$1,000/month with optimizations)

**Key Innovation**: Page-by-page processing with real-time updates allows users to see results immediately as each drawing comparison completes, populating the vertical carousel incrementally.

---

**END OF PART 2**

For questions or clarifications, contact the engineering team.

---

_Last updated: November 18, 2025_

