# Advanced Next-Gen RAG Build Plan for BuildTrace

**Version:** 1.0
**Date:** 2025-12-12
**Status:** Implementation-Ready
**Author:** Senior ML/AI Systems Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current System Analysis](#current-system-analysis)
3. [RAG Architecture Overview](#rag-architecture-overview)
4. [Agentic Pipeline Design](#agentic-pipeline-design)
5. [Technical Stack Decisions](#technical-stack-decisions)
6. [Data Model & Storage](#data-model--storage)
7. [Implementation Phases](#implementation-phases)
8. [Advanced Features Roadmap](#advanced-features-roadmap)
9. [Cost & Performance Optimization](#cost--performance-optimization)
10. [Testing & Validation Strategy](#testing--validation-strategy)

---

## Executive Summary

This plan extends BuildTrace's existing drawing comparison capabilities with an **advanced RAG (Retrieval-Augmented Generation) system** that enables natural language question-answering over architectural drawing sets. The system will leverage:

- **Multi-modal embeddings** (text + vision) for comprehensive drawing understanding
- **Agentic orchestration** using **Gemini Function Calling** (not MCP or compaction) for intelligent retrieval planning
- **Gemini 3 Pro** for all AI tasks (best vision model, 81% MMMU-Pro, released Nov 2025)
- **GCP-native infrastructure** for scalability and cost control
- **pgvector on Cloud SQL** for vector storage and similarity search
- **Iterative enrichment** with region-level segmentation and combined context

### Key Objectives

1. **Accurate Q&A**: Answer construction-related questions with <8s P95 latency and >90% accuracy
2. **Context-Aware**: Leverage existing OCR, diff, and summary data as RAG corpus
3. **Scalable**: Handle 1000+ drawing sets per project, 10K+ concurrent queries
4. **Cost-Effective**: Target <$0.05 per query (embedding + retrieval + generation)
5. **Production-Ready**: Build on existing Cloud Run + Pub/Sub architecture

### Why Not MCP or Compaction?

**MCP (Model Context Protocol):**
- Designed for desktop/IDE integration (Claude Code, Cursor)
- Requires MCP server infrastructure (not needed for cloud-native backend)
- Adds complexity for backend-to-backend communication
- Better suited for developer tools, not production APIs

**Compaction:**
- Token reduction technique for long contexts
- Not an orchestration framework
- Already handled by our prompt engineering and chunking strategy

**Gemini Function Calling (Chosen Approach):**
- Native to Google Vertex AI and Gemini API
- Best-in-class vision model (81% MMMU-Pro benchmark, released Nov 2025)
- Structured JSON schema for function definitions with deterministic tool selection
- 1M token context window (largest available)
- Most cost-effective ($2/1M input vs $5/1M for Claude Opus 4.5)
- Perfect for backend agentic workflows
- Already integrated (BuildTrace uses Gemini 2.5 Pro for OCR)
- Production-proven at scale with Google Cloud infrastructure

---

## Current System Analysis

### Existing Architecture

```
┌─────────────────────────────────────────────────────┐
│  Current BuildTrace Architecture (Production)       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Frontend (Next.js 14)                              │
│  └─> Backend (Flask, Cloud Run)                     │
│       ├─> Cloud SQL (PostgreSQL 17)                 │
│       ├─> GCS (Drawing storage)                     │
│       ├─> Pub/Sub (Async workers)                   │
│       └─> Secret Manager (API keys)                 │
│                                                     │
│  Workers (Cloud Run Jobs):                          │
│  ├─> OCR Worker (Gemini 2.5 Pro Vision)             │
│  ├─> Diff Worker (Change detection)                 │
│  └─> Summary Worker (Gemini 3 Pro analysis)         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Current Data Flow (Pre-RAG)

```
User uploads 2 PDFs
  ↓
DrawingUploadService → GCS → DrawingVersion records
  ↓
OrchestratorService creates Job + JobStages
  ↓
Pub/Sub queue: ocr-queue (2 messages)
  ↓
OCR Workers (parallel):
  - PDF → PNG (pdf2image)
  - PNG → Text + Bboxes (Gemini Vision)
  - Store OCR JSON in GCS
  ↓
Pub/Sub queue: diff-queue
  ↓
Diff Worker:
  - Load OCR results
  - Image alignment (affine transform)
  - Compare text blocks (added/deleted/modified)
  - Generate overlay JSON
  ↓
Pub/Sub queue: summary-queue
  ↓
Summary Worker:
  - Load overlay JSON
  - Call Gemini 2.5 Pro
  - Parse structured summary
  - Store ChangeSummary record
  ↓
Frontend polls job status → Display results
```

### Strengths to Leverage

1. **Robust OCR pipeline**: Gemini 2.5 Pro Vision already extracts text + bounding boxes
2. **Structured metadata**: DrawingVersion, DiffResult, ChangeSummary tables
3. **GCS storage**: Organized paths for drawings, OCR results, overlays
4. **Async processing**: Pub/Sub + Cloud Run workers scale horizontally
5. **Multi-tenant**: Organizations, Projects, Users with proper isolation
6. **Production deployment**: CI/CD, monitoring, secrets management

### Gaps to Address

1. **No embeddings**: OCR text not embedded for semantic search
2. **No vector DB**: Need pgvector extension enabled on Cloud SQL
3. **No region segmentation**: Full-page OCR only (no quadrants/legends)
4. **No combined context**: No sheet-level aggregated summaries
5. **Limited chatbot**: Gemini 3 Pro with web search but no drawing retrieval
6. **No agentic routing**: Questions answered generically, not contextually

---

## RAG Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAG-Enhanced BuildTrace                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Ingestion Pipeline (Enhanced):                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. PDF Upload → DrawingVersion                           │  │
│  │ 2. Rasterization (pdf2image 300dpi)                      │  │
│  │ 3. Region Segmentation:                                  │  │
│  │    - Full page                                           │  │
│  │    - Quadrants (4 regions)                               │  │
│  │    - Legend strip (heuristic bbox)                       │  │
│  │    - Title block (heuristic bbox)                        │  │
│  │ 4. Vision Captioning (Gemini 2.5 Pro):                   │  │
│  │    - Per-region text extraction                          │  │
│  │    - Structured JSON (rooms, counts, materials)          │  │
│  │ 5. Embedding Generation (text-embedding-3-small):        │  │
│  │    - Caption embeddings (1536-dim)                       │  │
│  │    - Combined context embeddings                         │  │
│  │ 6. Combined Context Builder (Gemini 3 Pro):              │  │
│  │    - Sheet-level summary                                 │  │
│  │    - Aggregated counts                                   │  │
│  │    - Region summaries                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Retrieval Pipeline (Agentic):                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ User Question                                            │  │
│  │   ↓                                                      │  │
│  │ Intent Classifier (Gemini 3 Pro + Function Calling):     │  │
│  │   - Intent: metadata / count / location / default        │  │
│  │   - Scope: project / drawing / sheet                     │  │
│  │   - Filters: region_type, bbox, threshold                │  │
│  │   ↓                                                      │  │
│  │ Agentic Planner (Gemini 3 Pro + Function Calling):      │  │
│  │   Tools:                                                 │  │
│  │   - query_combined_context(sheet_id)                     │  │
│  │   - query_regions(filters, top_k, threshold)             │  │
│  │   - query_legend(drawing_id)                             │  │
│  │   - aggregate_counts(scope)                              │  │
│  │   - check_sufficiency(evidence)                          │  │
│  │   ↓                                                      │  │
│  │ Vector Search (Cloud SQL pgvector):                       │  │
│  │   - Cosine similarity (thresholds: 0.18-0.30)            │  │
│  │   - Filtered by project/drawing/region_type              │  │
│  │   - Top-K ranking (K=5-20)                               │  │
│  │   ↓                                                      │  │
│  │ Context Assembly:                                        │  │
│  │   - Combined summary (always)                            │  │
│  │   - Selected region captions + images                    │  │
│  │   - Aggregated counts                                    │  │
│  │   ↓                                                      │  │
│  │ Answer Generation (Gemini 3 Pro Vision):                 │  │
│  │   - Low temperature (0.1)                                │  │
│  │   - Provenance metadata                                  │  │
│  │   - Guardrails (evidence sufficiency)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
┌────────────┐    ┌──────────────┐    ┌──────────────┐
│  Frontend  │───▶│  API Gateway │───▶│ RAG Service  │
│ (Next.js)  │    │ (Cloud Run)  │    │ (Cloud Run)  │
└────────────┘    └──────────────┘    └──────┬───────┘
                                             │
                    ┌────────────────────────┼────────────────────┐
                    ▼                        ▼                    ▼
          ┌─────────────────┐    ┌────────────────┐    ┌─────────────┐
          │ Intent Classifier│    │ Agentic Planner│    │  Retriever  │
          │  (Gemini 3 Pro) │    │ (Gemini 3 Pro) │    │ (pgvector)  │
          └─────────────────┘    └────────┬───────┘    └──────┬──────┘
                                           │                   │
                                           ▼                   ▼
                                  ┌────────────────┐  ┌─────────────┐
                                  │ Tool Executor  │  │  Cloud SQL  │
                                  │   (Python)     │  │  pgvector   │
                                  └────────┬───────┘  └─────────────┘
                                           │
                                           ▼
                                  ┌────────────────┐
                                  │ Answer Gen     │
                                  │(Gemini 3 Pro)  │
                                  └────────────────┘
```

---

## Agentic Pipeline Design

### Why Gemini Function Calling?

**Decision Matrix:**

| Criteria | MCP | Compaction | Gemini Function Calling | Winner |
|----------|-----|------------|------------------------|--------|
| Backend-native | ❌ Desktop-first | ✅ API-friendly | ✅ API-first | Gemini |
| Production-ready | ⚠️ Early stage | ✅ Mature | ✅ Production (Nov 2025) | Gemini |
| Cost | $$$ Server overhead | $ Minimal | $ **Best ($2/1M)** | **Gemini** |
| Vision Quality | N/A | N/A | ✅ **Best (81% MMMU-Pro)** | **Gemini** |
| Context Window | N/A | ✅ Long | ✅ **1M tokens** | **Gemini** |
| Flexibility | ⚠️ Limited tools | ❌ Not orchestration | ✅ 100+ functions | Gemini |
| Latency | ⚠️ Extra hops | ✅ Instant | ✅ Single call | Compaction/Gemini |
| Debuggability | ⚠️ Multi-system | ✅ Transparent | ✅ JSON logs | Compaction/Gemini |
| GCP Integration | ❌ Extra infra | ✅ Direct | ✅ **Native (Vertex AI)** | **Gemini** |
| **Overall Score** | 2/9 | 6/9 | **9/9** | **Gemini** |

**Why Gemini 3 Pro specifically:**
- Already using Gemini 2.5 Pro for OCR (easy migration)
- Best-in-class vision model (81% MMMU-Pro benchmark)
- 60% cheaper than Claude Opus 4.5 ($2/1M vs $5/1M)
- Largest context window (1M tokens vs 200K for Claude)
- Native GCP integration via Vertex AI

### Function Calling Architecture

**Function Definitions (Gemini Function Schema):**

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "query_combined_context",
        "description": "Fetch sheet-level combined summary (legend + counts + full context)",
        "parameters": {
          "type": "object",
          "properties": {
            "sheet_id": {"type": "string", "description": "Sheet identifier"},
            "drawing_id": {"type": "string", "description": "Drawing identifier"}
          },
          "required": ["sheet_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "query_regions",
        "description": "Vector search across drawing regions with filters",
        "parameters": {
          "type": "object",
          "properties": {
            "query_text": {"type": "string"},
            "filters": {
              "type": "object",
              "properties": {
                "project_id": {"type": "string"},
                "drawing_id": {"type": "string"},
                "region_type": {"type": "array", "items": {"type": "string"}},
                "threshold": {"type": "number", "minimum": 0, "maximum": 1}
              }
            },
            "top_k": {"type": "integer", "default": 5}
          },
          "required": ["query_text"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "query_legend",
        "description": "Fetch legend strip for keynote/symbol reference",
        "parameters": {
          "type": "object",
          "properties": {
            "drawing_id": {"type": "string"}
          },
          "required": ["drawing_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "aggregate_counts",
        "description": "Aggregate counts across multiple regions/drawings",
        "parameters": {
          "type": "object",
          "properties": {
            "scope": {"type": "string", "enum": ["project", "drawing", "sheet"]},
            "entity_type": {"type": "string", "description": "e.g., 'restrooms', 'doors', 'windows'"}
          },
          "required": ["scope", "entity_type"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "check_evidence_sufficiency",
        "description": "Validate if retrieved evidence is sufficient to answer question",
        "parameters": {
          "type": "object",
          "properties": {
            "question": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "object"}}
          },
          "required": ["question", "evidence"]
        }
      }
    }
  ]
}
```

### Agentic Flow (Step-by-Step)

**Example: "How many restrooms are on drawing A-101, Sheet 1?"**

```
Step 1: Intent Classification (GPT-4.1-mini)
────────────────────────────────────────────
Input:
  System: "You are an intent classifier for construction drawing queries..."
  User: "How many restrooms are on drawing A-101, Sheet 1?"

Output (JSON):
{
  "intent": "count",
  "scope_level": "sheet",
  "entities": ["restrooms"],
  "filters": {
    "drawing_name": "A-101",
    "sheet_number": 1
  },
  "requires_aggregation": true,
  "threshold": 0.25
}

Step 2: Agentic Planning (Gemini 3 Pro + Function Calling)
─────────────────────────────────────────────────
Input:
  System: "You are a retrieval planner. Use tools to gather evidence..."
  User: "How many restrooms are on drawing A-101, Sheet 1?"
  Tools: [query_combined_context, query_regions, aggregate_counts, ...]
  Intent: {intent: "count", scope_level: "sheet", ...}

Tool Call 1:
{
  "tool": "query_combined_context",
  "arguments": {
    "sheet_id": "a101-sheet1",
    "drawing_id": "a101"
  }
}

Response 1:
{
  "combined_summary": "Sheet 1 contains 3 restrooms: 2 public (men's/women's) + 1 family restroom",
  "aggregated_counts": {
    "restrooms": 3,
    "doors": 45,
    "windows": 12
  },
  "region_summaries": [...]
}

Tool Call 2 (Sufficiency Check):
{
  "tool": "check_evidence_sufficiency",
  "arguments": {
    "question": "How many restrooms are on drawing A-101, Sheet 1?",
    "evidence": [
      {"source": "combined_context", "content": "Sheet 1 contains 3 restrooms..."}
    ]
  }
}

Response 2:
{
  "sufficient": true,
  "confidence": 0.95,
  "reason": "Combined summary explicitly states restroom count"
}

Planning Decision:
  - Evidence is sufficient
  - No need to query individual regions
  - Proceed to answer generation

Step 3: Answer Generation (Gemini 3 Pro Vision)
───────────────────────────────────────────
Input:
  System: "You are a construction expert. Answer based on evidence..."
  Context:
    - Combined Summary: "Sheet 1 contains 3 restrooms..."
    - Aggregated Counts: {restrooms: 3, ...}
  User: "How many restrooms are on drawing A-101, Sheet 1?"

Output:
{
  "answer": "Drawing A-101, Sheet 1 contains **3 restrooms**:\n- 2 public restrooms (men's and women's)\n- 1 family restroom",
  "confidence": 0.95,
  "provenance": [
    {
      "source": "combined_context",
      "sheet_id": "a101-sheet1",
      "relevance": 1.0
    }
  ],
  "metadata": {
    "tokens_used": 350,
    "latency_ms": 1200
  }
}
```

### Tool Executor Implementation

**Python Implementation (backend/services/rag_tools.py):**

```python
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from gcp.database import get_db_session
from gcp.database.models import (
    DrawingVersion, Region, Caption, Embedding, CombinedContext
)
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class RAGToolExecutor:
    """Executes RAG tools called by the agentic planner"""

    def __init__(self):
        self.session_factory = get_db_session

    def query_combined_context(
        self,
        sheet_id: str,
        drawing_id: Optional[str] = None
    ) -> ToolResult:
        """
        Fetch sheet-level combined summary

        Args:
            sheet_id: Sheet identifier
            drawing_id: Optional drawing identifier for validation

        Returns:
            ToolResult with combined context data
        """
        try:
            with self.session_factory() as db:
                # Query CombinedContext table
                query = db.query(CombinedContext).filter(
                    CombinedContext.sheet_id == sheet_id
                )

                if drawing_id:
                    query = query.filter(CombinedContext.drawing_id == drawing_id)

                context = query.first()

                if not context:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"No combined context found for sheet {sheet_id}"
                    )

                return ToolResult(
                    success=True,
                    data={
                        "combined_summary": context.combined_text,
                        "aggregated_counts": context.aggregated_counts,
                        "region_summaries": context.region_summaries,
                        "metadata": {
                            "sheet_id": context.sheet_id,
                            "drawing_id": context.drawing_id,
                            "created_at": context.created_at.isoformat()
                        }
                    }
                )

        except Exception as e:
            logger.error(f"Error fetching combined context: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def query_regions(
        self,
        query_text: str,
        filters: Optional[Dict] = None,
        top_k: int = 5
    ) -> ToolResult:
        """
        Vector search across drawing regions

        Args:
            query_text: Search query
            filters: Optional filters (project_id, drawing_id, region_type, threshold)
            top_k: Number of results to return

        Returns:
            ToolResult with matching regions
        """
        try:
            filters = filters or {}
            threshold = filters.get('threshold', 0.25)

            with self.session_factory() as db:
                # Generate query embedding (using OpenAI text-embedding-3-small)
                from openai import OpenAI
                import os

                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query_text
                )
                query_embedding = response.data[0].embedding

                # Vector search using pgvector
                # Build SQL query with filters
                sql_filters = []
                params = {
                    'query_embedding': query_embedding,
                    'top_k': top_k,
                    'threshold': threshold
                }

                if filters.get('project_id'):
                    sql_filters.append("metadata->>'project_id' = :project_id")
                    params['project_id'] = filters['project_id']

                if filters.get('drawing_id'):
                    sql_filters.append("metadata->>'drawing_id' = :drawing_id")
                    params['drawing_id'] = filters['drawing_id']

                if filters.get('region_type'):
                    region_types = filters['region_type']
                    if isinstance(region_types, list):
                        sql_filters.append("metadata->>'region_type' = ANY(:region_types)")
                        params['region_types'] = region_types

                where_clause = " AND ".join(sql_filters) if sql_filters else "1=1"

                # pgvector cosine similarity query
                query_sql = f"""
                    SELECT
                        e.id,
                        e.region_id,
                        e.metadata,
                        c.caption_text,
                        c.structured_json,
                        r.bbox_norm,
                        r.region_type,
                        1 - (e.vector <=> :query_embedding::vector) as similarity
                    FROM embeddings e
                    JOIN captions c ON e.region_id = c.region_id
                    JOIN regions r ON c.region_id = r.id
                    WHERE {where_clause}
                      AND 1 - (e.vector <=> :query_embedding::vector) >= :threshold
                    ORDER BY e.vector <=> :query_embedding::vector
                    LIMIT :top_k
                """

                results = db.execute(text(query_sql), params).fetchall()

                regions = [
                    {
                        "embedding_id": row[0],
                        "region_id": row[1],
                        "metadata": row[2],
                        "caption_text": row[3],
                        "structured_json": row[4],
                        "bbox_norm": row[5],
                        "region_type": row[6],
                        "similarity": float(row[7])
                    }
                    for row in results
                ]

                return ToolResult(
                    success=True,
                    data=regions,
                    metadata={
                        "query": query_text,
                        "num_results": len(regions),
                        "top_k": top_k,
                        "threshold": threshold
                    }
                )

        except Exception as e:
            logger.error(f"Error querying regions: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def query_legend(self, drawing_id: str) -> ToolResult:
        """Fetch legend strip for keynote reference"""
        try:
            with self.session_factory() as db:
                # Find legend region
                legend = db.query(Caption).join(Region).filter(
                    Region.drawing_id == drawing_id,
                    Region.region_type == 'legend'
                ).first()

                if not legend:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"No legend found for drawing {drawing_id}"
                    )

                return ToolResult(
                    success=True,
                    data={
                        "caption_text": legend.caption_text,
                        "structured_json": legend.structured_json,
                        "drawing_id": drawing_id
                    }
                )

        except Exception as e:
            logger.error(f"Error fetching legend: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def aggregate_counts(
        self,
        scope: str,
        entity_type: str,
        scope_id: Optional[str] = None
    ) -> ToolResult:
        """Aggregate counts across multiple regions/drawings"""
        try:
            with self.session_factory() as db:
                # Query CombinedContext aggregated_counts JSONB
                if scope == "project":
                    contexts = db.query(CombinedContext).filter(
                        CombinedContext.project_id == scope_id
                    ).all()
                elif scope == "drawing":
                    contexts = db.query(CombinedContext).filter(
                        CombinedContext.drawing_id == scope_id
                    ).all()
                else:  # sheet
                    contexts = db.query(CombinedContext).filter(
                        CombinedContext.sheet_id == scope_id
                    ).all()

                # Aggregate counts
                total_count = 0
                breakdown = []

                for ctx in contexts:
                    counts = ctx.aggregated_counts or {}
                    count = counts.get(entity_type, 0)
                    if count > 0:
                        total_count += count
                        breakdown.append({
                            "sheet_id": ctx.sheet_id,
                            "count": count
                        })

                return ToolResult(
                    success=True,
                    data={
                        "entity_type": entity_type,
                        "scope": scope,
                        "total_count": total_count,
                        "breakdown": breakdown
                    }
                )

        except Exception as e:
            logger.error(f"Error aggregating counts: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def check_evidence_sufficiency(
        self,
        question: str,
        evidence: List[Dict]
    ) -> ToolResult:
        """Check if evidence is sufficient to answer question"""
        try:
            # Simple heuristic: check if evidence is non-empty and has min length
            if not evidence:
                return ToolResult(
                    success=True,
                    data={
                        "sufficient": False,
                        "confidence": 0.0,
                        "reason": "No evidence retrieved"
                    }
                )

            # Check evidence content
            total_text = " ".join([
                str(e.get('content', '')) + str(e.get('caption_text', ''))
                for e in evidence
            ])

            # Basic heuristics
            min_length = 50  # characters
            has_numbers = any(c.isdigit() for c in total_text)

            if len(total_text) < min_length:
                return ToolResult(
                    success=True,
                    data={
                        "sufficient": False,
                        "confidence": 0.3,
                        "reason": "Evidence too short"
                    }
                )

            # For count questions, check if we have numbers
            if "how many" in question.lower() and not has_numbers:
                return ToolResult(
                    success=True,
                    data={
                        "sufficient": False,
                        "confidence": 0.4,
                        "reason": "Count question but no numbers in evidence"
                    }
                )

            # Evidence seems sufficient
            return ToolResult(
                success=True,
                data={
                    "sufficient": True,
                    "confidence": 0.85,
                    "reason": "Evidence contains relevant content"
                }
            )

        except Exception as e:
            logger.error(f"Error checking sufficiency: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def execute_tool(self, tool_name: str, arguments: Dict) -> ToolResult:
        """
        Execute a tool by name

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            ToolResult
        """
        tool_map = {
            "query_combined_context": self.query_combined_context,
            "query_regions": self.query_regions,
            "query_legend": self.query_legend,
            "aggregate_counts": self.aggregate_counts,
            "check_evidence_sufficiency": self.check_evidence_sufficiency
        }

        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unknown tool: {tool_name}"
            )

        return tool_func(**arguments)
```

---

## Data Model & Storage

### New Tables (RAG-Specific)

**1. regions**
```sql
CREATE TABLE regions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    drawing_version_id VARCHAR(36) NOT NULL REFERENCES drawing_versions(id) ON DELETE CASCADE,
    drawing_id VARCHAR(36) NOT NULL,  -- Denormalized for fast queries
    project_id VARCHAR(36) NOT NULL,  -- Denormalized for filtering
    sheet_id VARCHAR(36) NOT NULL,    -- Sheet identifier (drawing_name + page)

    region_type VARCHAR(50) NOT NULL, -- 'full_page', 'quadrant', 'legend', 'title_block'
    bbox_norm JSONB NOT NULL,         -- {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0} (normalized)
    bbox_pixel JSONB,                 -- {"x": 0, "y": 0, "w": 3000, "h": 2000} (absolute pixels)

    image_ref TEXT,                   -- GCS path to region crop PNG
    page_number INTEGER,
    quadrant_position VARCHAR(20),    -- 'top_left', 'top_right', 'bottom_left', 'bottom_right'

    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB                    -- Additional metadata
);

CREATE INDEX idx_regions_drawing ON regions(drawing_id);
CREATE INDEX idx_regions_sheet ON regions(sheet_id);
CREATE INDEX idx_regions_type ON regions(region_type);
CREATE INDEX idx_regions_project ON regions(project_id);
```

**2. captions**
```sql
CREATE TABLE captions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    region_id VARCHAR(36) NOT NULL REFERENCES regions(id) ON DELETE CASCADE,

    caption_text TEXT NOT NULL,       -- Raw text from Gemini Vision
    structured_json JSONB,            -- Structured data: rooms, counts, materials, etc.

    ai_model_used VARCHAR(50),        -- e.g., 'gemini-2.5-pro', 'gpt-4o-vision'
    confidence_score FLOAT,
    processing_time_ms INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_captions_region ON captions(region_id);
```

**3. embeddings (pgvector)**
```sql
-- Requires pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    region_id VARCHAR(36) NOT NULL REFERENCES regions(id) ON DELETE CASCADE,

    vector vector(1536) NOT NULL,     -- OpenAI text-embedding-3-small (1536 dims)
    embedding_model VARCHAR(50) DEFAULT 'text-embedding-3-small',

    combined_flag BOOLEAN DEFAULT false,  -- True for combined context embeddings

    metadata JSONB NOT NULL,          -- {project_id, drawing_id, sheet_id, region_type, ...}
    norm FLOAT,                       -- Vector norm for normalization checks
    tokens_used INTEGER,              -- Embedding API token usage

    created_at TIMESTAMP DEFAULT NOW()
);

-- pgvector indexes for cosine similarity
CREATE INDEX idx_embeddings_vector_cosine ON embeddings USING ivfflat (vector vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on dataset size

CREATE INDEX idx_embeddings_region ON embeddings(region_id);
CREATE INDEX idx_embeddings_combined ON embeddings(combined_flag) WHERE combined_flag = true;

-- GIN index for metadata filtering
CREATE INDEX idx_embeddings_metadata ON embeddings USING gin(metadata);
```

**4. combined_contexts**
```sql
CREATE TABLE combined_contexts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    sheet_id VARCHAR(36) NOT NULL UNIQUE,  -- Unique per sheet
    drawing_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL,

    combined_text TEXT NOT NULL,      -- Aggregated summary from GPT-4o
    aggregated_counts JSONB,          -- {"restrooms": 3, "doors": 45, ...}
    region_summaries JSONB,           -- Array of region summaries

    embedding_id VARCHAR(36) REFERENCES embeddings(id),  -- Link to combined embedding

    ai_model_used VARCHAR(50),
    processing_time_ms INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_combined_contexts_sheet ON combined_contexts(sheet_id);
CREATE INDEX idx_combined_contexts_drawing ON combined_contexts(drawing_id);
CREATE INDEX idx_combined_contexts_project ON combined_contexts(project_id);
```

**5. qa_sessions**
```sql
CREATE TABLE qa_sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    project_id VARCHAR(36) REFERENCES projects(id),

    question_text TEXT NOT NULL,
    response_text TEXT NOT NULL,

    intent_classification JSONB,      -- Classifier output
    tool_calls JSONB,                 -- Agentic tool call log
    provenance JSONB,                 -- Source regions/sheets

    confidence_score FLOAT,
    latency_ms INTEGER,
    tokens_used JSONB,                -- {classifier: 50, planner: 200, generator: 500}

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_qa_sessions_user ON qa_sessions(user_id);
CREATE INDEX idx_qa_sessions_project ON qa_sessions(project_id);
CREATE INDEX idx_qa_sessions_created ON qa_sessions(created_at DESC);
```

### Database Choice: pgvector on Cloud SQL

**Decision: Use Cloud SQL PostgreSQL with pgvector extension**

| Feature | Cloud SQL + pgvector | Notes |
|---------|---------------------|-------|
| pgvector support | ✅ Extension available | Mature, stable (v0.5.0+) |
| Performance | ✅ Good (1-2ms for 1M vectors) | IVFFlat index optimization |
| Cost | ✅ $200-500/month | Current instance already provisioned |
| Existing schema | ✅ Already migrated | Zero migration needed |
| HA/Replication | ✅ Regional HA enabled | Automatic failover |
| Index types | ✅ IVFFlat, HNSW | HNSW for higher accuracy (PG 16+) |
| Maintenance | ✅ Managed by GCP | Auto-updates, backups |

**Why Cloud SQL (not AlloyDB):**
- **No migration risk**: Existing schema and data already on Cloud SQL
- **Lower cost**: $200-500/month vs $700+ for AlloyDB
- **Sufficient performance**: pgvector IVFFlat handles 1-10M vectors with <5ms latency
- **Proven stability**: pgvector is production-ready and widely used
- **Easy rollback**: Can disable extension if needed

**Performance Expectations:**
- **1M vectors**: 1-2ms query time (IVFFlat, probes=10)
- **10M vectors**: 5-10ms query time (IVFFlat, lists=1000, probes=20)
- **100M vectors**: Consider sharding or upgrading to HNSW index

**Optimization Strategy:**
- Use IVFFlat index initially (good balance of speed/accuracy)
- Tune `lists` parameter based on dataset size (100 for <1M, 1000 for >10M)
- Upgrade to HNSW index if query latency exceeds 10ms at scale

---

## Implementation Phases

### Phase 0: Foundations (Week 1)

**Objectives:**
- Set up RAG infrastructure
- Add new database tables
- Configure pgvector

**Tasks:**
1. Database migrations:
   ```bash
   # Create new tables
   python backend/run_migrations.py --migration=add_rag_tables.sql

   # Enable pgvector
   gcloud sql connect buildtrace-dev-db --user=postgres
   > CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. Update models (`backend/gcp/database/models.py`):
   - Add `Region`, `Caption`, `Embedding`, `CombinedContext`, `QASession` classes

3. Create GCS buckets for region crops:
   ```bash
   gsutil mb -p buildtrace-dev -c STANDARD -l us-west2 \
     gs://buildtrace-dev-regions-buildtrace-dev
   ```

4. Update service accounts:
   - Grant Cloud SQL permissions for vector operations
   - Add OpenAI embedding API quota

**Deliverables:**
- ✅ RAG tables created
- ✅ pgvector enabled
- ✅ Models updated
- ✅ GCS bucket created

---

### Phase 1: Ingestion Pipeline (Weeks 2-3)

**Objectives:**
- Enhance OCR pipeline with region segmentation
- Generate embeddings for all text
- Build combined context summaries

**Tasks:**

**1.1 Region Segmentation (`backend/processing/region_segmenter.py`):**

```python
from typing import List, Dict, Tuple
import cv2
import numpy as np

class RegionSegmenter:
    """Segments drawing pages into regions for granular OCR"""

    def segment_page(
        self,
        image: np.ndarray,
        page_number: int
    ) -> List[Dict]:
        """
        Segment page into regions

        Returns:
            List of region dicts with bbox_norm, region_type, quadrant_position
        """
        h, w = image.shape[:2]
        regions = []

        # 1. Full page region
        regions.append({
            "region_type": "full_page",
            "bbox_norm": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "bbox_pixel": {"x": 0, "y": 0, "w": w, "h": h},
            "page_number": page_number
        })

        # 2. Quadrants (4 equal regions)
        quadrants = [
            ("top_left", 0.0, 0.0, 0.5, 0.5),
            ("top_right", 0.5, 0.0, 0.5, 0.5),
            ("bottom_left", 0.0, 0.5, 0.5, 0.5),
            ("bottom_right", 0.5, 0.5, 0.5, 0.5)
        ]

        for name, x_norm, y_norm, w_norm, h_norm in quadrants:
            regions.append({
                "region_type": "quadrant",
                "quadrant_position": name,
                "bbox_norm": {"x": x_norm, "y": y_norm, "w": w_norm, "h": h_norm},
                "bbox_pixel": {
                    "x": int(x_norm * w),
                    "y": int(y_norm * h),
                    "w": int(w_norm * w),
                    "h": int(h_norm * h)
                },
                "page_number": page_number
            })

        # 3. Heuristic: Legend strip (bottom-right, typically 20% width x 100% height)
        legend_bbox = self._detect_legend(image)
        if legend_bbox:
            regions.append({
                "region_type": "legend",
                "bbox_norm": legend_bbox["norm"],
                "bbox_pixel": legend_bbox["pixel"],
                "page_number": page_number
            })

        # 4. Heuristic: Title block (bottom-right corner, typically 30% x 15%)
        title_bbox = self._detect_title_block(image)
        if title_bbox:
            regions.append({
                "region_type": "title_block",
                "bbox_norm": title_bbox["norm"],
                "bbox_pixel": title_bbox["pixel"],
                "page_number": page_number
            })

        return regions

    def _detect_legend(self, image: np.ndarray) -> Dict:
        """Heuristic: assume legend is right 20% of image"""
        h, w = image.shape[:2]
        x = int(0.8 * w)
        return {
            "norm": {"x": 0.8, "y": 0.0, "w": 0.2, "h": 1.0},
            "pixel": {"x": x, "y": 0, "w": w - x, "h": h}
        }

    def _detect_title_block(self, image: np.ndarray) -> Dict:
        """Heuristic: assume title block is bottom-right 30% x 15%"""
        h, w = image.shape[:2]
        x = int(0.7 * w)
        y = int(0.85 * h)
        return {
            "norm": {"x": 0.7, "y": 0.85, "w": 0.3, "h": 0.15},
            "pixel": {"x": x, "y": y, "w": w - x, "h": h - y}
        }
```

**1.2 Enhanced OCR Pipeline:**

Update `backend/processing/ocr_pipeline.py`:
- Add region segmentation after PDF rasterization
- Create `Region` records in DB
- Caption each region with Gemini Vision
- Store region crops in GCS

**1.3 Embedding Generation (`backend/processing/embedding_pipeline.py`):**

```python
import os
from typing import List, Dict
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class EmbeddingPipeline:
    """Generate embeddings for region captions"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "text-embedding-3-small"  # 1536 dims

    def run(self, region_ids: List[str]) -> Dict:
        """
        Generate embeddings for a batch of regions

        Args:
            region_ids: List of region IDs

        Returns:
            Dict with success count and errors
        """
        from gcp.database import get_db_session
        from gcp.database.models import Region, Caption, Embedding

        success_count = 0
        errors = []

        with get_db_session() as db:
            for region_id in region_ids:
                try:
                    # Get region and caption
                    region = db.query(Region).filter_by(id=region_id).first()
                    caption = db.query(Caption).filter_by(region_id=region_id).first()

                    if not caption:
                        errors.append(f"No caption for region {region_id}")
                        continue

                    # Generate embedding
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=caption.caption_text
                    )

                    vector = response.data[0].embedding
                    tokens_used = response.usage.total_tokens

                    # Calculate norm
                    import numpy as np
                    norm = float(np.linalg.norm(vector))

                    # Create Embedding record
                    embedding = Embedding(
                        region_id=region_id,
                        vector=vector,
                        embedding_model=self.model,
                        combined_flag=False,
                        metadata={
                            "project_id": region.project_id,
                            "drawing_id": region.drawing_id,
                            "sheet_id": region.sheet_id,
                            "region_type": region.region_type,
                            "quadrant_position": region.quadrant_position
                        },
                        norm=norm,
                        tokens_used=tokens_used
                    )

                    db.add(embedding)
                    db.commit()
                    success_count += 1

                except Exception as e:
                    logger.error(f"Error embedding region {region_id}: {e}")
                    errors.append(str(e))
                    db.rollback()

        return {
            "success_count": success_count,
            "error_count": len(errors),
            "errors": errors
        }
```

**1.4 Combined Context Builder (`backend/processing/combined_context_builder.py`):**

```python
from typing import List, Dict
import os
import json
import logging
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)

class CombinedContextBuilder:
    """Build sheet-level combined summaries using Gemini 3 Pro"""

    def __init__(self):
        aiplatform.init(project=os.getenv('GCP_PROJECT_ID'))
        self.model = GenerativeModel("gemini-3-pro")

    def run(self, sheet_id: str) -> Dict:
        """
        Build combined context for a sheet

        Args:
            sheet_id: Sheet identifier (e.g., "A-101-page1")

        Returns:
            Dict with combined context data
        """
        from gcp.database import get_db_session
        from gcp.database.models import Region, Caption, CombinedContext

        with get_db_session() as db:
            # Get all regions for this sheet
            regions = db.query(Region).filter_by(sheet_id=sheet_id).all()
            captions = db.query(Caption).join(Region).filter(
                Region.sheet_id == sheet_id
            ).all()

            if not captions:
                raise ValueError(f"No captions found for sheet {sheet_id}")

            # Prepare prompt
            full_page_caption = next(
                (c.caption_text for c in captions if c.region.region_type == 'full_page'),
                ""
            )

            quadrant_captions = [
                f"{c.region.quadrant_position}: {c.caption_text}"
                for c in captions if c.region.region_type == 'quadrant'
            ]

            legend_caption = next(
                (c.caption_text for c in captions if c.region.region_type == 'legend'),
                None
            )

            prompt = f"""You are analyzing an architectural drawing sheet. Combine the following regional OCR results into a comprehensive summary.

FULL PAGE:
{full_page_caption}

QUADRANTS:
{chr(10).join(quadrant_captions)}

LEGEND:
{legend_caption or 'Not available'}

Generate a JSON response with:
{{
  "combined_summary": "<detailed summary of the entire sheet>",
  "aggregated_counts": {{
    "rooms": <count>,
    "doors": <count>,
    "windows": <count>,
    "restrooms": <count>,
    ...
  }},
  "region_summaries": [
    {{"region": "top_left", "summary": "..."}},
    ...
  ]
}}"""

            # Call Gemini 3 Pro
            generation_config = GenerationConfig(
                temperature=0.1,
                max_output_tokens=1500,
                response_mime_type="application/json"
            )

            full_prompt = f"""You are a construction document analyzer. {prompt}"""

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )

            result = json.loads(response.text)

            # Create CombinedContext record
            drawing_id = regions[0].drawing_id if regions else None
            project_id = regions[0].project_id if regions else None

            combined_context = CombinedContext(
                sheet_id=sheet_id,
                drawing_id=drawing_id,
                project_id=project_id,
                combined_text=result['combined_summary'],
                aggregated_counts=result.get('aggregated_counts', {}),
                region_summaries=result.get('region_summaries', []),
                ai_model_used=self.model,
                processing_time_ms=int(response.usage.total_tokens * 10)  # Estimate
            )

            db.add(combined_context)
            db.commit()

            # Generate embedding for combined summary
            from .embedding_pipeline import EmbeddingPipeline
            emb_pipeline = EmbeddingPipeline()
            emb_response = emb_pipeline.client.embeddings.create(
                model=emb_pipeline.model,
                input=combined_context.combined_text
            )

            vector = emb_response.data[0].embedding

            # Create combined embedding
            from gcp.database.models import Embedding
            embedding = Embedding(
                region_id=regions[0].id,  # Link to sheet's first region
                vector=vector,
                embedding_model=emb_pipeline.model,
                combined_flag=True,
                metadata={
                    "project_id": project_id,
                    "drawing_id": drawing_id,
                    "sheet_id": sheet_id,
                    "region_type": "combined_context"
                },
                tokens_used=emb_response.usage.total_tokens
            )

            db.add(embedding)
            combined_context.embedding_id = embedding.id
            db.commit()

            return {
                "sheet_id": sheet_id,
                "combined_context_id": combined_context.id,
                "embedding_id": embedding.id
            }
```

**1.5 Pub/Sub Topics:**

Create new topics for RAG ingestion:
```bash
gcloud pubsub topics create buildtrace-dev-embedding-queue --project=buildtrace-dev
gcloud pubsub topics create buildtrace-dev-combined-context-queue --project=buildtrace-dev

gcloud pubsub subscriptions create buildtrace-dev-embedding-worker-sub \
  --topic=buildtrace-dev-embedding-queue \
  --ack-deadline=600 \
  --project=buildtrace-dev

gcloud pubsub subscriptions create buildtrace-dev-combined-context-worker-sub \
  --topic=buildtrace-dev-combined-context-queue \
  --ack-deadline=600 \
  --project=buildtrace-dev
```

**1.6 Update Orchestrator:**

Modify `backend/services/orchestrator.py` to trigger embedding + combined context workers after OCR completion.

**Deliverables:**
- ✅ Region segmentation working
- ✅ Embeddings generated for all captions
- ✅ Combined contexts created for all sheets
- ✅ GCS storage for region crops
- ✅ Pub/Sub orchestration updated

---

### Phase 2: Retrieval & Agentic Planning (Weeks 4-5)

**Objectives:**
- Build intent classifier
- Implement agentic planner with tool calling
- Create tool executor
- Integrate with existing chatbot

**Tasks:**

**2.1 Intent Classifier Service (`backend/services/intent_classifier.py`):**

```python
from typing import Dict
import os
import json
import logging
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Classify user questions to determine retrieval strategy using Gemini 3 Pro"""

    def __init__(self):
        aiplatform.init(project=os.getenv('GCP_PROJECT_ID'))
        self.model = GenerativeModel("gemini-3-pro")

    def classify(self, question: str, project_id: str = None) -> Dict:
        """
        Classify question intent

        Args:
            question: User question
            project_id: Optional project context

        Returns:
            Dict with intent, scope_level, filters, etc.
        """
        prompt = f"""You are a query intent classifier for construction drawing questions.

Classify the following question into:
1. **intent**: metadata, count, location, default
2. **scope_level**: project, drawing, sheet
3. **entities**: List of entities mentioned (e.g., ["restrooms", "doors"])
4. **filters**: Specific filters (drawing_name, sheet_number, grid_location)
5. **requires_aggregation**: True if question requires counting/summing
6. **threshold**: Similarity threshold (0.18 for metadata, 0.30 for count/location)

Question: "{question}"

Return JSON only:
{{
  "intent": "count | metadata | location | default",
  "scope_level": "project | drawing | sheet",
  "entities": ["entity1", "entity2"],
  "filters": {{
    "drawing_name": "A-101" or null,
    "sheet_number": 1 or null,
    "grid_location": "Grid B" or null
  }},
  "requires_aggregation": true | false,
  "threshold": 0.18 - 0.30
}}"""

        generation_config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=300,
            response_mime_type="application/json"
        )

        response = self.model.generate_content(
            prompt,
            generation_config=generation_config
        )

        result = json.loads(response.text)
        logger.info(f"Intent classification: {result}")

        return result
```

**2.2 Agentic Planner (`backend/services/agentic_planner.py`):**

```python
from typing import Dict, List, Any
import os
import json
import logging
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, GenerationConfig, FunctionDeclaration, Tool

from backend.services.rag_tools import RAGToolExecutor

logger = logging.getLogger(__name__)

class AgenticPlanner:
    """Plans retrieval using Gemini 3 Pro function calling"""

    def __init__(self):
        aiplatform.init(project=os.getenv('GCP_PROJECT_ID'))
        self.model = GenerativeModel("gemini-3-pro")
        self.tool_executor = RAGToolExecutor()

        # Define available functions (Gemini Function Declarations)
        query_combined_context = FunctionDeclaration(
            name="query_combined_context",
            description="Fetch sheet-level combined summary with legend + counts",
            parameters={
                "type": "object",
                "properties": {
                    "sheet_id": {"type": "string", "description": "Sheet identifier"},
                    "drawing_id": {"type": "string", "description": "Drawing identifier"}
                },
                "required": ["sheet_id"]
            }
        )

        query_regions = FunctionDeclaration(
            name="query_regions",
            description="Vector search across drawing regions",
            parameters={
                "type": "object",
                "properties": {
                    "query_text": {"type": "string", "description": "Search query"},
                    "filters": {"type": "object", "description": "Optional filters"},
                    "top_k": {"type": "integer", "description": "Number of results"}
                },
                "required": ["query_text"]
            }
        )

        query_legend = FunctionDeclaration(
            name="query_legend",
            description="Fetch legend strip for keynote reference",
            parameters={
                "type": "object",
                "properties": {
                    "drawing_id": {"type": "string", "description": "Drawing identifier"}
                },
                "required": ["drawing_id"]
            }
        )

        aggregate_counts = FunctionDeclaration(
            name="aggregate_counts",
            description="Aggregate counts across regions",
            parameters={
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "Scope (project/drawing/sheet)"},
                    "entity_type": {"type": "string", "description": "Entity type to count"}
                },
                "required": ["scope", "entity_type"]
            }
        )

        check_evidence = FunctionDeclaration(
            name="check_evidence_sufficiency",
            description="Check if evidence is sufficient to answer question",
            parameters={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "User question"},
                    "evidence": {"type": "array", "description": "Collected evidence"}
                },
                "required": ["question", "evidence"]
            }
        )

        # Create tool with all functions
        self.tools = Tool(
            function_declarations=[
                query_combined_context,
                query_regions,
                query_legend,
                aggregate_counts,
                check_evidence
            ]
        )

    def plan_retrieval(
        self,
        question: str,
        intent: Dict,
        max_iterations: int = 5
    ) -> Dict:
        """
        Plan retrieval using tool calling

        Args:
            question: User question
            intent: Intent classification result
            max_iterations: Max tool calling rounds

        Returns:
            Dict with evidence and tool call log
        """
        system_prompt = """You are a retrieval planner for construction drawings.

Use available functions to gather evidence to answer the user's question.

Strategy:
1. Start with combined_context (sheet-level summary) if available
2. Check evidence sufficiency
3. If insufficient, query specific regions or aggregate counts
4. Always include provenance (source region IDs)

Stop when evidence is sufficient or max iterations reached."""

        user_prompt = f"Question: {question}\n\nIntent: {json.dumps(intent)}"

        evidence = []
        tool_calls_log = []
        chat_history = []

        for iteration in range(max_iterations):
            # Generate content with function calling
            response = self.model.generate_content(
                [system_prompt, user_prompt] + chat_history,
                tools=[self.tools],
                generation_config=GenerationConfig(temperature=0.1)
            )

            # Check if Gemini wants to call functions
            if not response.candidates[0].content.parts:
                logger.info(f"Planning complete after {iteration + 1} iterations")
                break

            function_call = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call'):
                    function_call = part.function_call
                    break

            if not function_call:
                # No function call - planning complete
                logger.info(f"Planning complete after {iteration + 1} iterations")
                break

            # Execute function call
            tool_name = function_call.name
            arguments = dict(function_call.args)

            logger.info(f"Executing function: {tool_name} with {arguments}")

            result = self.tool_executor.execute_tool(tool_name, arguments)

            tool_calls_log.append({
                "iteration": iteration,
                "tool": tool_name,
                "arguments": arguments,
                "success": result.success,
                "data": result.data
            })

            # Add result to evidence if successful
            if result.success and result.data:
                evidence.append({
                    "source": tool_name,
                    "data": result.data
                })

            # Add function call and response to chat history for next iteration
            from vertexai.generative_models import Part
            chat_history.append(response.candidates[0].content)
            chat_history.append(Part.from_function_response(
                name=tool_name,
                response={
                    "success": result.success,
                    "data": result.data,
                    "error": result.error
                }
            ))

            # Check if we should stop (sufficiency check)
            sufficiency_check = next(
                (tc for tc in tool_calls_log if tc['tool'] == 'check_evidence_sufficiency'),
                None
            )

            if sufficiency_check and sufficiency_check['data'].get('sufficient'):
                logger.info("Evidence sufficient - stopping planning")
                break

        return {
            "evidence": evidence,
            "tool_calls": tool_calls_log,
            "iterations": iteration + 1 if evidence else 0
        }
```

**2.3 RAG Query Service (`backend/services/rag_query_service.py`):**

```python
from typing import Dict, List, Optional
from openai import OpenAI
import os
import json
import logging
from datetime import datetime

from backend.services.intent_classifier import IntentClassifier
from backend.services.agentic_planner import AgenticPlanner

logger = logging.getLogger(__name__)

class RAGQueryService:
    """Main RAG query service - orchestrates intent classification, retrieval, and answer generation"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.answer_model = os.getenv('ANSWER_MODEL', 'gpt-4o')  # Or gpt-5.1 when available

        self.classifier = IntentClassifier()
        self.planner = AgenticPlanner()

    def query(
        self,
        question: str,
        project_id: str,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Answer a question using RAG

        Args:
            question: User question
            project_id: Project ID for scoping
            user_id: Optional user ID for audit

        Returns:
            Dict with answer, provenance, metadata
        """
        start_time = datetime.now()

        # Step 1: Classify intent
        logger.info(f"[RAG] Classifying question: {question}")
        intent = self.classifier.classify(question, project_id)

        # Step 2: Plan retrieval
        logger.info(f"[RAG] Planning retrieval with intent: {intent}")
        retrieval_result = self.planner.plan_retrieval(question, intent)

        evidence = retrieval_result['evidence']
        tool_calls = retrieval_result['tool_calls']

        # Step 3: Generate answer
        logger.info(f"[RAG] Generating answer with {len(evidence)} evidence items")

        if not evidence:
            return {
                "answer": "I don't have enough information to answer this question based on the available drawings.",
                "confidence": 0.0,
                "provenance": [],
                "metadata": {
                    "intent": intent,
                    "tool_calls": tool_calls,
                    "latency_ms": (datetime.now() - start_time).total_seconds() * 1000
                }
            }

        # Format evidence for prompt
        context_text = self._format_evidence(evidence)

        prompt = f"""You are a construction expert. Answer the following question based ONLY on the provided evidence.

EVIDENCE:
{context_text}

QUESTION:
{question}

Instructions:
- Be specific and cite sources
- If the evidence is insufficient, say so
- Include relevant counts, locations, or metadata
- Format with markdown for readability

ANSWER:"""

        response = self.client.chat.completions.create(
            model=self.answer_model,
            messages=[
                {"role": "system", "content": "You are a construction document expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for accuracy
            max_completion_tokens=1000
        )

        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # Extract provenance
        provenance = self._extract_provenance(evidence)

        # Save to QA session
        self._save_qa_session(
            question=question,
            answer=answer,
            intent=intent,
            tool_calls=tool_calls,
            provenance=provenance,
            tokens_used=tokens_used,
            project_id=project_id,
            user_id=user_id
        )

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "answer": answer,
            "confidence": 0.85,  # Could compute based on similarity scores
            "provenance": provenance,
            "metadata": {
                "intent": intent,
                "tool_calls": tool_calls,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms
            }
        }

    def _format_evidence(self, evidence: List[Dict]) -> str:
        """Format evidence for prompt"""
        formatted = []

        for i, item in enumerate(evidence, 1):
            source = item['source']
            data = item['data']

            if source == 'query_combined_context':
                formatted.append(f"[Sheet Summary]\n{data.get('combined_summary', '')}\n")
                if data.get('aggregated_counts'):
                    formatted.append(f"Counts: {json.dumps(data['aggregated_counts'])}\n")

            elif source == 'query_regions':
                for region in data:
                    formatted.append(
                        f"[Region: {region['region_type']}]\n"
                        f"Similarity: {region['similarity']:.2f}\n"
                        f"{region['caption_text']}\n"
                    )

            elif source == 'query_legend':
                formatted.append(f"[Legend]\n{data.get('caption_text', '')}\n")

            elif source == 'aggregate_counts':
                formatted.append(
                    f"[Aggregated Counts - {data['scope']}]\n"
                    f"{data['entity_type']}: {data['total_count']}\n"
                )

        return "\n".join(formatted)

    def _extract_provenance(self, evidence: List[Dict]) -> List[Dict]:
        """Extract provenance from evidence"""
        provenance = []

        for item in evidence:
            data = item['data']

            if isinstance(data, dict):
                if 'sheet_id' in data:
                    provenance.append({
                        "type": "sheet",
                        "sheet_id": data['sheet_id'],
                        "source": item['source']
                    })

            elif isinstance(data, list):
                for region in data:
                    if 'region_id' in region:
                        provenance.append({
                            "type": "region",
                            "region_id": region['region_id'],
                            "similarity": region.get('similarity'),
                            "source": item['source']
                        })

        return provenance

    def _save_qa_session(self, **kwargs):
        """Save QA session to database"""
        from gcp.database import get_db_session
        from gcp.database.models import QASession

        try:
            with get_db_session() as db:
                session = QASession(
                    user_id=kwargs.get('user_id'),
                    project_id=kwargs.get('project_id'),
                    question_text=kwargs['question'],
                    response_text=kwargs['answer'],
                    intent_classification=kwargs['intent'],
                    tool_calls=kwargs['tool_calls'],
                    provenance=kwargs['provenance'],
                    confidence_score=0.85,
                    tokens_used=kwargs.get('tokens_used', 0)
                )

                db.add(session)
                db.commit()
        except Exception as e:
            logger.error(f"Error saving QA session: {e}")
```

**2.4 API Endpoint (`backend/blueprints/rag.py`):**

```python
from flask import Blueprint, request, jsonify
from backend.services.rag_query_service import RAGQueryService
import logging

logger = logging.getLogger(__name__)

rag_bp = Blueprint('rag', __name__, url_prefix='/api/v1/rag')

rag_service = RAGQueryService()

@rag_bp.route('/query', methods=['POST'])
def query():
    """
    RAG query endpoint

    Request:
        {
            "question": "How many restrooms on A-101?",
            "project_id": "proj123",
            "user_id": "user456"
        }

    Response:
        {
            "answer": "...",
            "confidence": 0.85,
            "provenance": [...],
            "metadata": {...}
        }
    """
    data = request.json

    question = data.get('question')
    project_id = data.get('project_id')
    user_id = data.get('user_id')

    if not question or not project_id:
        return jsonify({"error": "question and project_id required"}), 400

    try:
        result = rag_service.query(question, project_id, user_id)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Register blueprint in app.py
# from blueprints.rag import rag_bp
# app.register_blueprint(rag_bp)
```

**Deliverables:**
- ✅ Intent classifier working
- ✅ Agentic planner with tool calling
- ✅ Tool executor implemented
- ✅ RAG query service API endpoint
- ✅ Integration tests passing

---

### Phase 3: Answer Generation & UX (Week 6)

**Objectives:**
- Integrate RAG with frontend
- Add caching for repeated questions
- Implement guardrails and confidence scoring

**Tasks:**

**3.1 Frontend Integration (`frontend/src/lib/rag-api.ts`):**

```typescript
export interface RAGQuery {
  question: string;
  project_id: string;
  user_id?: string;
}

export interface RAGResponse {
  answer: string;
  confidence: number;
  provenance: Array<{
    type: string;
    sheet_id?: string;
    region_id?: string;
    similarity?: number;
  }>;
  metadata: {
    intent: any;
    tool_calls: any[];
    tokens_used: number;
    latency_ms: number;
  };
}

export async function queryRAG(query: RAGQuery): Promise<RAGResponse> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/rag/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(query)
  });

  if (!response.ok) {
    throw new Error(`RAG query failed: ${response.statusText}`);
  }

  return response.json();
}
```

**3.2 RAG UI Component (`frontend/src/components/rag/RAGQueryPanel.tsx`):**

```typescript
import React, { useState } from 'react';
import { queryRAG, RAGResponse } from '@/lib/rag-api';

interface Props {
  projectId: string;
  userId?: string;
}

export const RAGQueryPanel: React.FC<Props> = ({ projectId, userId }) => {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const result = await queryRAG({
        question,
        project_id: projectId,
        user_id: userId
      });

      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rag-query-panel p-4 border rounded">
      <h3 className="text-lg font-semibold mb-4">Ask about your drawings</h3>

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <textarea
            className="w-full p-2 border rounded"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., How many restrooms are on drawing A-101?"
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          disabled={loading || !question.trim()}
        >
          {loading ? 'Searching...' : 'Ask'}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded text-red-700">
          Error: {error}
        </div>
      )}

      {response && (
        <div className="mt-6">
          <div className="p-4 bg-gray-50 border rounded">
            <h4 className="font-semibold mb-2">Answer:</h4>
            <div className="prose" dangerouslySetInnerHTML={{ __html: response.answer }} />

            <div className="mt-4 text-sm text-gray-600">
              <p>Confidence: {(response.confidence * 100).toFixed(0)}%</p>
              <p>Latency: {response.metadata.latency_ms.toFixed(0)}ms</p>
              <p>Sources: {response.provenance.length} region(s)</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

**3.3 Caching Layer (`backend/services/rag_cache.py`):**

```python
import hashlib
import json
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")

class RAGCache:
    """Cache for RAG query results"""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self.redis_client = None

        if REDIS_AVAILABLE:
            try:
                import os
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))

                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True
                )
                logger.info("RAG cache initialized with Redis")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")

    def _get_cache_key(self, question: str, project_id: str) -> str:
        """Generate cache key from question + project"""
        content = f"{project_id}:{question.lower().strip()}"
        return f"rag:query:{hashlib.md5(content.encode()).hexdigest()}"

    def get(self, question: str, project_id: str) -> Optional[Dict]:
        """Get cached result"""
        if not self.redis_client:
            return None

        try:
            key = self._get_cache_key(question, project_id)
            cached = self.redis_client.get(key)

            if cached:
                logger.info(f"Cache hit for question: {question[:50]}")
                return json.loads(cached)

            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(self, question: str, project_id: str, result: Dict) -> None:
        """Cache result"""
        if not self.redis_client:
            return

        try:
            key = self._get_cache_key(question, project_id)
            self.redis_client.setex(
                key,
                self.ttl_seconds,
                json.dumps(result)
            )
            logger.info(f"Cached result for question: {question[:50]}")

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
```

Update `RAGQueryService` to use cache:

```python
# In RAGQueryService.__init__:
from backend.services.rag_cache import RAGCache
self.cache = RAGCache(ttl_seconds=3600)  # 1 hour

# In RAGQueryService.query:
# Check cache first
cached = self.cache.get(question, project_id)
if cached:
    return cached

# ... (existing logic)

# Cache result before returning
self.cache.set(question, project_id, result)
return result
```

**Deliverables:**
- ✅ Frontend RAG query panel
- ✅ Redis caching layer
- ✅ Confidence scoring
- ✅ Provenance display in UI

---

### Phase 4: Observability & Guardrails (Week 7)

**Objectives:**
- Add comprehensive logging
- Cost tracking per query
- Fallback flows for errors
- Security hardening

**Tasks:**

**4.1 Cloud Monitoring Dashboard:**

Create custom metrics:
- RAG queries per minute
- Average latency (P50, P95, P99)
- Token usage by component (classifier, planner, generator)
- Cache hit rate
- Error rate by error type

**4.2 Cost Tracking (`backend/services/cost_tracker.py`):**

```python
from typing import Dict
from gcp.database import get_db_session
from gcp.database.models import CostTracking
import logging

logger = logging.getLogger(__name__)

class CostTracker:
    """Track API costs per query"""

    # API pricing (as of Dec 2025)
    PRICING = {
        "text-embedding-3-small": {"input": 0.02 / 1_000_000},  # $0.02 per 1M tokens (OpenAI)
        "gemini-3-pro": {"input": 2.00 / 1_000_000, "output": 12.00 / 1_000_000},  # Released Nov 2025
        "gemini-2.5-pro": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000}  # Currently used for OCR
    }

    def track_query(
        self,
        qa_session_id: str,
        tokens_breakdown: Dict[str, Dict[str, int]]
    ) -> float:
        """
        Track cost for a RAG query

        Args:
            qa_session_id: QA session ID
            tokens_breakdown: {
                "classifier": {"input": 50, "output": 20},
                "planner": {"input": 200, "output": 150},
                "generator": {"input": 500, "output": 300}
            }

        Returns:
            Total cost in USD
        """
        total_cost = 0.0

        for component, tokens in tokens_breakdown.items():
            model = self._get_model_for_component(component)

            input_tokens = tokens.get("input", 0)
            output_tokens = tokens.get("output", 0)

            pricing = self.PRICING.get(model, {"input": 0, "output": 0})

            cost = (
                input_tokens * pricing["input"] +
                output_tokens * pricing["output"]
            )

            total_cost += cost

        # Save to database
        with get_db_session() as db:
            cost_record = CostTracking(
                qa_session_id=qa_session_id,
                tokens_breakdown=tokens_breakdown,
                total_cost_usd=total_cost
            )
            db.add(cost_record)
            db.commit()

        logger.info(f"Query cost: ${total_cost:.6f}")
        return total_cost

    def _get_model_for_component(self, component: str) -> str:
        mapping = {
            "classifier": "gpt-4o-mini",
            "planner": "gpt-4o",
            "generator": "gpt-4o"  # or gpt-5.1
        }
        return mapping.get(component, "gpt-4o")
```

**4.3 Guardrails (`backend/services/rag_guardrails.py`):**

```python
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RAGGuardrails:
    """Safety and quality guardrails for RAG"""

    def __init__(self):
        self.max_question_length = 500
        self.min_confidence_threshold = 0.3
        self.max_tokens_per_query = 5000

    def validate_question(self, question: str) -> Optional[str]:
        """
        Validate question before processing

        Returns:
            Error message if invalid, None if valid
        """
        if not question or not question.strip():
            return "Question cannot be empty"

        if len(question) > self.max_question_length:
            return f"Question too long (max {self.max_question_length} chars)"

        # Check for SQL injection attempts
        sql_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "EXEC"]
        if any(keyword in question.upper() for keyword in sql_keywords):
            logger.warning(f"Potential SQL injection attempt: {question}")
            return "Invalid question format"

        return None

    def validate_result(self, result: Dict) -> Optional[str]:
        """
        Validate result before returning to user

        Returns:
            Error message if invalid, None if valid
        """
        if not result.get("answer"):
            return "No answer generated"

        confidence = result.get("confidence", 0.0)
        if confidence < self.min_confidence_threshold:
            return "Confidence too low - insufficient evidence"

        tokens = result.get("metadata", {}).get("tokens_used", 0)
        if tokens > self.max_tokens_per_query:
            logger.warning(f"Token usage exceeded: {tokens} > {self.max_tokens_per_query}")

        return None
```

**Deliverables:**
- ✅ Cloud Monitoring dashboards
- ✅ Cost tracking per query
- ✅ Guardrails implemented
- ✅ Error fallback flows
- ✅ Security audit passed

---

### Phase 5: QA & Hardening (Ongoing)

**Objectives:**
- Scenario-based testing
- Accuracy evaluation
- Threshold tuning
- Performance optimization

**Test Scenarios:**

1. **Metadata Questions:**
   - "What is the title of drawing A-101?"
   - "When was Sheet 2 last revised?"
   - Expected: High accuracy (>95%), low latency (<3s)

2. **Count Questions:**
   - "How many restrooms on A-101?"
   - "Total number of doors across all drawings?"
   - Expected: Exact counts, <5s latency

3. **Location Questions:**
   - "Where are the fire exits on Sheet 1?"
   - "Show me restrooms near Grid B"
   - Expected: Specific locations, bbox coordinates

4. **Complex Multi-Drawing:**
   - "Compare restroom counts between A-101 and A-102"
   - "Which drawing has the most windows?"
   - Expected: Aggregated results, <8s latency

**Evaluation Metrics:**

- **Accuracy**: % of correct answers (manual labeling required)
- **Latency**: P50, P95, P99 response times
- **Cost**: Average cost per query
- **Cache Hit Rate**: % of cached queries
- **Error Rate**: % of failed queries

**Deliverables:**
- ✅ 100+ test questions labeled
- ✅ Accuracy >90% on test set
- ✅ P95 latency <8s
- ✅ Cost <$0.05 per query
- ✅ Production monitoring alerts configured

---

## Advanced Features Roadmap

### Phase 6: Adaptive Chunking (Weeks 8-9)

**Objective:** Use Vertex AI Vision to detect rooms, legends, title blocks automatically instead of heuristic bboxes.

**Approach:**
- Train object detection model on architectural drawings
- Detect entities: rooms, doors, windows, legends, title blocks
- Generate variable-size regions based on detected entities
- Store entity metadata in `regions.metadata` JSONB

**Tools:**
- Vertex AI AutoML Vision
- YOLOv8 for object detection
- Custom training data (100+ annotated drawings)

**Expected Improvement:**
- 30% better region relevance
- 20% higher Q&A accuracy

---

### Phase 7: Reinforcement Learning (Weeks 10-12)

**Objective:** Use user feedback to improve retrieval ranking.

**Approach:**
1. Add thumbs up/down to RAG answers
2. Log feedback in `qa_sessions.feedback` JSONB
3. Train logistic regression re-ranker:
   - Features: similarity score, region type, position, token count
   - Label: positive/negative feedback
4. Apply re-ranker after vector search, before context assembly

**Expected Improvement:**
- 15% better ranking of relevant regions
- 10% higher user satisfaction

---

### Phase 8: Multi-Modal Embeddings (Weeks 13-15)

**Objective:** Embed both text AND images for richer retrieval.

**Approach:**
- Use OpenAI CLIP or Google PaLI for multi-modal embeddings
- Generate image embeddings for region crops
- Store in separate `image_embeddings` table (vector(512))
- Hybrid search: combine text + image similarity scores

**Expected Improvement:**
- Better retrieval for visual queries ("Show me ceiling details")
- 25% higher relevance for location questions

---

## Cost & Performance Optimization

### Cost Breakdown (Per 1000 Queries)

**Current System (No RAG):**
- Gemini 2.5 Pro Vision OCR: $0.00 (one-time per drawing)
- Gemini 3 Pro Summary: $0.02 (one-time per diff)
- Total: ~$0.02 per drawing comparison

**RAG System (Per Query) - Gemini 3 Pro:**

| Component | Tokens | Model | Cost |
|-----------|--------|-------|------|
| Embedding (ingest) | 500 | text-embedding-3-small | $0.00001 |
| Intent Classifier | 100 in, 50 out | gemini-3-pro | $0.00080 |
| Agentic Planner | 500 in, 300 out | gemini-3-pro | $0.00460 |
| Answer Generator | 800 in, 400 out | gemini-3-pro | $0.00640 |
| **Total per query** | - | - | **$0.01181** |

**Note:** Gemini 3 Pro is **60% cheaper** than the original plan with Claude Opus 4.5 ($0.025/query)

**Optimization Strategies:**

1. **Caching (1-hour TTL):**
   - Expected cache hit rate: 30%
   - Effective cost: $0.01181 * 0.7 = **$0.00827/query**

2. **Batch Embeddings:**
   - Embed all regions once during ingestion
   - Amortize embedding cost across queries
   - Effective embedding cost: ~$0.00001/query

3. **Use Gemini 2.0 Flash for Classification:**
   - Even cheaper for simple tasks ($0.10/1M vs $2/1M)
   - Savings: ~$0.00070/query
   - Trade-off: Slightly lower accuracy

4. **Quantized Embeddings:**
   - Use 768-dim instead of 1536-dim (if accuracy allows)
   - 50% storage reduction, minimal accuracy loss

**Target Cost:**
- **$0.008-0.012 per query** (well below $0.05 target)
- **<$120/month** for 10K queries/month
- **4x cheaper** than original GPT-4o plan

---

### Performance Optimization

**Latency Breakdown (P95):**

| Component | Latency | Optimization |
|-----------|---------|--------------|
| Intent Classification | 200ms | Cached prompt |
| Agentic Planning | 1500ms | Parallel tool calls |
| Vector Search (pgvector) | 150ms | IVFFlat index |
| Answer Generation | 2000ms | Streaming response |
| **Total P95** | **3850ms** | **Target: <5000ms** |

**Optimization Techniques:**

1. **pgvector Index Tuning:**
   - Use IVFFlat with `lists=100` for <1M vectors
   - Increase to `lists=1000` for >10M vectors
   - Trade-off: recall vs speed (tune via `probes` parameter)

2. **Parallel Tool Execution:**
   - Execute independent tool calls in parallel
   - Example: `query_combined_context` + `query_legend` simultaneously
   - Savings: 30% latency reduction

3. **Streaming Responses:**
   - Stream answer generation to frontend
   - Show partial answers while generating
   - Perceived latency: <1s (even if total is 4s)

4. **pgvector Index Optimization:**
   - Upgrade to HNSW index (PostgreSQL 16+) for 2x faster queries
   - Better recall than IVFFlat (99% vs 95%)
   - Minimal cost increase (same instance)

---

## Testing & Validation Strategy

### Unit Tests

**Test Coverage:**
- Region segmentation: 95%+
- Embedding generation: 90%+
- Tool executor: 100%
- Intent classifier: 85%+

**Sample Test (`tests/test_rag_tools.py`):**

```python
import pytest
from backend.services.rag_tools import RAGToolExecutor

def test_query_combined_context():
    executor = RAGToolExecutor()

    # Assuming test data seeded in DB
    result = executor.query_combined_context(
        sheet_id="test-sheet-1",
        drawing_id="A-101"
    )

    assert result.success is True
    assert result.data is not None
    assert "combined_summary" in result.data
    assert "aggregated_counts" in result.data

def test_query_regions():
    executor = RAGToolExecutor()

    result = executor.query_regions(
        query_text="restrooms",
        filters={"project_id": "test-project"},
        top_k=5
    )

    assert result.success is True
    assert len(result.data) <= 5
    assert all(r["similarity"] >= 0.0 for r in result.data)
```

---

### Integration Tests

**End-to-End RAG Flow:**

```python
def test_rag_e2e():
    from backend.services.rag_query_service import RAGQueryService

    service = RAGQueryService()

    result = service.query(
        question="How many restrooms on A-101?",
        project_id="test-project",
        user_id="test-user"
    )

    assert "answer" in result
    assert result["confidence"] > 0.0
    assert len(result["provenance"]) > 0
    assert result["metadata"]["latency_ms"] < 10000  # <10s
```

---

### Load Testing

**JMeter / Locust Script:**

- Concurrent users: 100
- Queries/sec: 10
- Duration: 10 minutes
- Target: P95 latency <8s, error rate <1%

---

## Deployment Checklist

### Pre-Deployment

- [ ] All Phase 1-2 deliverables complete
- [ ] Database migrations tested on staging
- [ ] pgvector extension enabled on Cloud SQL
- [ ] pgvector IVFFlat index created
- [ ] GCS buckets provisioned
- [ ] Pub/Sub topics created
- [ ] Secret Manager updated (OpenAI keys)
- [ ] Cost tracking enabled
- [ ] Monitoring dashboards configured

### Deployment

- [ ] Deploy backend updates (Cloud Run)
- [ ] Run database migrations
- [ ] Deploy workers (embedding, combined context)
- [ ] Deploy frontend updates
- [ ] Enable RAG API endpoint
- [ ] Test on staging environment
- [ ] Load test (100 concurrent users)
- [ ] Production deployment
- [ ] Smoke test (10 sample queries)

### Post-Deployment

- [ ] Monitor error rate (<1%)
- [ ] Monitor latency (P95 <8s)
- [ ] Monitor cost (<$0.05/query)
- [ ] User feedback collection enabled
- [ ] Alerting rules active (PagerDuty/Slack)
- [ ] Documentation updated

---

## Conclusion

This plan provides a **production-ready roadmap** for implementing advanced RAG capabilities in BuildTrace using:

- **OpenAI Tool Calling** (not MCP or compaction) for agentic orchestration
- **pgvector on Cloud SQL** for scalable vector search
- **GCP-native infrastructure** for seamless integration
- **Realistic cost targets** (<$0.05/query) and latency goals (<8s P95)

The phased approach ensures incremental value delivery while maintaining production stability. Each phase has clear deliverables, test criteria, and rollback plans.

**Next Steps:**
1. Review and approve this plan
2. Set up Phase 0 infrastructure (Week 1)
3. Begin Phase 1 implementation (Weeks 2-3)
4. Iterate based on user feedback and metrics

---

**Document Status:** Ready for Implementation
**Review Date:** 2025-12-12
**Approvers:** Tech Lead, Product Manager, CTO
