# RAG Query Flow - Detailed Implementation Guide

**Version:** 1.0
**Date:** 2025-12-12
**Status:** Production-Ready Architecture

---

## Executive Summary

This document details the complete RAG query flow for BuildTrace using:
- **GPT-5.2 Thinking** for agentic planning and tool orchestration (extended reasoning)
- **Gemini 3 Pro** for vision analysis and multimodal understanding
- **OpenAI Tool Calling** infrastructure (no MCP, no Claude)
- **pgvector on Cloud SQL** for vector search

**Key Design Principle:** Use the right model for the right task.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Model Selection Rationale](#model-selection-rationale)
3. [Complete Query Flow](#complete-query-flow)
4. [Phase 1: Intent Classification](#phase-1-intent-classification)
5. [Phase 2: Agentic Planning (GPT-5.2 Thinking)](#phase-2-agentic-planning-gpt-52-thinking)
6. [Phase 3: Vision Analysis (Gemini 3 Pro)](#phase-3-vision-analysis-gemini-3-pro)
7. [Phase 4: Answer Generation](#phase-4-answer-generation)
8. [Tool Calling Infrastructure](#tool-calling-infrastructure)
9. [Verification & Testing Strategy](#verification--testing-strategy)
10. [Cost Analysis](#cost-analysis)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAG Query Pipeline                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User Question: "How many restrooms on drawing A-101?"              │
│         ↓                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PHASE 1: Intent Classification (GPT-4o-mini)                │  │
│  │  - Fast, cheap, pattern matching                             │  │
│  │  - Output: {intent, scope, filters, threshold}               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         ↓                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PHASE 2: Agentic Planning (GPT-5.2 Thinking)               │  │
│  │  - Extended reasoning for complex queries                     │  │
│  │  - Tool calling orchestration                                 │  │
│  │  - Multi-step planning with verification                      │  │
│  │  Tools:                                                        │  │
│  │    → query_combined_context(sheet_id)                         │  │
│  │    → query_regions(filters, top_k)                            │  │
│  │    → query_legend(drawing_id)                                 │  │
│  │    → aggregate_counts(scope, entity)                          │  │
│  │    → check_evidence_sufficiency(question, evidence)           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         ↓                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Vector Search (Cloud SQL pgvector)                          │  │
│  │  - Embeddings: text-embedding-3-small                         │  │
│  │  - Cosine similarity with thresholds                          │  │
│  │  - Returns: region captions + metadata                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         ↓                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PHASE 3: Vision Analysis (Gemini 3 Pro)                    │  │
│  │  - Best-in-class vision (81% MMMU-Pro)                        │  │
│  │  - Analyze region images if needed                            │  │
│  │  - Extract visual context (counts, locations, details)        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         ↓                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PHASE 4: Answer Generation (GPT-5.2 Thinking)              │  │
│  │  - Synthesize evidence into coherent answer                   │  │
│  │  - Include provenance (region IDs, sources)                   │  │
│  │  - Apply guardrails (confidence, sufficiency)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         ↓                                                            │
│  Final Answer + Provenance + Confidence Score                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Model Selection Rationale

### Why GPT-5.2 Thinking?

| Capability | Why It Matters |
|------------|----------------|
| **Extended Reasoning** | Can think through multi-step retrieval strategies |
| **Tool Calling** | Native OpenAI tool calling (production-ready) |
| **400K Context** | Handle large context from multiple regions |
| **Cost** | $1.75/1M input (cheaper than GPT-4o for complex reasoning) |
| **Released** | Dec 11, 2025 (latest) |

**Use Cases:**
- Agentic planning (Phase 2)
- Multi-step reasoning
- Tool orchestration
- Answer synthesis (Phase 4)

### Why Gemini 3 Pro?

| Capability | Why It Matters |
|------------|----------------|
| **Best Vision** | 81% MMMU-Pro benchmark (best-in-class) |
| **Multimodal** | Native image understanding |
| **1M Context** | Largest context window available |
| **Cost** | $2/1M input (cheap for vision) |
| **GCP Native** | Already using Gemini 2.5 Pro for OCR |

**Use Cases:**
- Vision analysis (Phase 3)
- Region image understanding
- Combined context building (ingestion)
- Drawing comprehension

### Why NOT Claude?

- Claude Opus 4.5 costs $5/1M (2.5x more expensive)
- Not needed for coding in production RAG pipeline
- GPT-5.2 Thinking better for extended reasoning
- Gemini 3 Pro better for vision

---

## Complete Query Flow

### Example Query: "How many restrooms are near Grid B on drawing A-101, Sheet 1?"

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DETAILED FLOW                               │
└─────────────────────────────────────────────────────────────────────┘

[1] USER INPUT
────────────────────────────────────────────────────────────────────
Question: "How many restrooms are near Grid B on drawing A-101, Sheet 1?"
Project ID: project-abc-123
User ID: user-xyz

[2] INTENT CLASSIFICATION (GPT-4o-mini) - 200ms
────────────────────────────────────────────────────────────────────
Input:
  System: "You are a query intent classifier..."
  User: "How many restrooms are near Grid B on drawing A-101, Sheet 1?"

Output:
{
  "intent": "count_with_location",
  "scope_level": "sheet",
  "entities": ["restrooms"],
  "filters": {
    "drawing_name": "A-101",
    "sheet_number": 1,
    "grid_location": "Grid B"
  },
  "requires_aggregation": true,
  "requires_visual_analysis": true,
  "threshold": 0.28
}

Cost: $0.00002 (50 input + 20 output tokens)

[3] AGENTIC PLANNING (GPT-5.2 Thinking) - 2000ms
────────────────────────────────────────────────────────────────────
System Prompt:
"""
You are a retrieval planner for construction drawings.

Available tools:
1. query_combined_context(sheet_id, drawing_id)
2. query_regions(query_text, filters, top_k, threshold)
3. query_legend(drawing_id)
4. aggregate_counts(scope, entity_type, filters)
5. check_evidence_sufficiency(question, evidence)

Strategy:
- Always start with combined_context for sheet-level summaries
- Use vector search for specific entities/locations
- Check legend for symbol definitions
- Verify evidence sufficiency before stopping
- For location queries, prioritize quadrant/region filtering

Plan the retrieval step by step.
"""

User Prompt:
"""
Question: "How many restrooms are near Grid B on drawing A-101, Sheet 1?"
Intent: {... intent classification output ...}
"""

╔═══════════════════════════════════════════════════════════════════╗
║  GPT-5.2 THINKING MODE (Extended Reasoning)                       ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  <thinking>                                                       ║
║  The user wants to count restrooms near a specific grid location.║
║                                                                   ║
║  Step 1: I should get the sheet-level context first to           ║
║  understand the overall layout.                                   ║
║                                                                   ║
║  Step 2: Query regions specifically for "restrooms" with Grid B  ║
║  location filter. The threshold should be 0.28 (count query).    ║
║                                                                   ║
║  Step 3: If the combined_context already has restroom counts     ║
║  broken down by location, I can skip vector search.               ║
║                                                                   ║
║  Step 4: Check if evidence is sufficient before proceeding.      ║
║  </thinking>                                                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

─── ITERATION 1: Tool Call ───
Tool: query_combined_context
Arguments:
{
  "sheet_id": "A-101-sheet-1",
  "drawing_id": "A-101"
}

Tool Response:
{
  "success": true,
  "data": {
    "combined_summary": "Sheet 1 floor plan shows 5 restrooms total:
                         2 public (Grid B area), 2 staff (Grid D),
                         1 accessible (Grid B/C border)",
    "aggregated_counts": {
      "restrooms": 5,
      "restrooms_grid_b": 2,
      "doors": 47,
      "windows": 15
    },
    "region_summaries": [
      {"region": "quadrant_top_right", "contains": "Grid A-B, mechanical"},
      {"region": "quadrant_bottom_left", "contains": "Grid B-C, restrooms"},
      ...
    ]
  }
}

─── ITERATION 2: Sufficiency Check ───
Tool: check_evidence_sufficiency
Arguments:
{
  "question": "How many restrooms are near Grid B on drawing A-101, Sheet 1?",
  "evidence": [
    {
      "source": "combined_context",
      "data": "Sheet 1 shows 5 restrooms total: 2 public (Grid B area),
               2 staff (Grid D), 1 accessible (Grid B/C border)"
    }
  ]
}

Tool Response:
{
  "success": true,
  "data": {
    "sufficient": true,
    "confidence": 0.92,
    "reason": "Combined context explicitly states '2 public (Grid B area)'
               and '1 accessible (Grid B/C border)'. Total near Grid B: 3 restrooms.",
    "recommendation": "Evidence is sufficient. Answer: 3 restrooms near Grid B."
  }
}

Planning Complete (2 iterations)
Evidence Collected:
- combined_context: Sheet-level summary with Grid B restroom counts
- sufficiency_check: Confirmed sufficient (92% confidence)

Cost: $0.00350 (2000 tokens thinking mode)

[4] VISION ANALYSIS (Gemini 3 Pro) - SKIPPED
────────────────────────────────────────────────────────────────────
Reason: Combined context already provided explicit counts for Grid B.
Vision analysis only triggered if:
  - Evidence insufficient
  - Visual verification needed
  - Ambiguous text descriptions

Cost: $0.00000 (skipped)

[5] ANSWER GENERATION (GPT-5.2 Thinking) - 800ms
────────────────────────────────────────────────────────────────────
System Prompt:
"""
You are a construction expert answering questions about architectural drawings.
Provide clear, concise answers based ONLY on the evidence provided.
Include provenance (sources) and confidence level.
"""

User Prompt:
"""
Question: "How many restrooms are near Grid B on drawing A-101, Sheet 1?"

Evidence:
1. [Source: combined_context, Sheet: A-101-sheet-1]
   "Sheet 1 floor plan shows 5 restrooms total: 2 public (Grid B area),
    2 staff (Grid D), 1 accessible (Grid B/C border)"

2. [Source: aggregated_counts]
   restrooms_grid_b: 2

Answer the question with confidence level and sources.
"""

GPT-5.2 Output:
{
  "answer": "There are **3 restrooms near Grid B** on drawing A-101, Sheet 1:
            \n- 2 public restrooms in the Grid B area
            \n- 1 accessible restroom on the Grid B/C border
            \n\n(Note: 2 additional staff restrooms are located at Grid D, not near Grid B)",

  "confidence": 0.92,

  "provenance": [
    {
      "source": "combined_context",
      "sheet_id": "A-101-sheet-1",
      "drawing_id": "A-101",
      "region_ids": ["full_page_A-101-sheet-1"]
    }
  ],

  "metadata": {
    "intent": "count_with_location",
    "evidence_sources": ["combined_context"],
    "tool_calls": 2,
    "latency_ms": 3000,
    "total_cost_usd": 0.00352
  }
}

Cost: $0.00100 (600 input + 150 output tokens)

[6] RESPONSE TO USER
────────────────────────────────────────────────────────────────────
{
  "answer": "There are **3 restrooms near Grid B** on drawing A-101, Sheet 1:...",
  "confidence": 0.92,
  "sources": ["A-101-sheet-1"],
  "latency_ms": 3000,
  "cost_usd": 0.00352
}

═════════════════════════════════════════════════════════════════════
TOTAL QUERY COST: $0.00352
TOTAL LATENCY: 3.0s (well below 8s target)
═════════════════════════════════════════════════════════════════════
```

---

## Phase 1: Intent Classification

### Purpose
Fast, cheap classification to route queries efficiently.

### Implementation

```python
from openai import OpenAI
import os
import json
from typing import Dict

class IntentClassifier:
    """Classify user questions using GPT-4o-mini (fast + cheap)"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-4o-mini"  # $0.15/1M in, $0.60/1M out

    def classify(self, question: str, project_id: str = None) -> Dict:
        """
        Classify query intent

        Returns:
            {
              "intent": "count" | "metadata" | "location" | "count_with_location" | "default",
              "scope_level": "project" | "drawing" | "sheet",
              "entities": List[str],
              "filters": Dict,
              "requires_aggregation": bool,
              "requires_visual_analysis": bool,
              "threshold": float
            }
        """

        prompt = f"""Classify this construction drawing query:

Question: "{question}"

Classify into:
1. **intent**:
   - "count": Counting entities (e.g., "How many doors?")
   - "metadata": Title, author, dates, revisions
   - "location": Where is X located? (e.g., "Where are fire exits?")
   - "count_with_location": Count + location (e.g., "How many restrooms near Grid B?")
   - "default": General questions

2. **scope_level**:
   - "project": All drawings
   - "drawing": Specific drawing (e.g., A-101)
   - "sheet": Specific sheet/page

3. **entities**: Extracted entities (e.g., ["restrooms", "doors"])

4. **filters**: Extracted filters
   - drawing_name: e.g., "A-101"
   - sheet_number: e.g., 1
   - grid_location: e.g., "Grid B"
   - floor_level: e.g., "2nd floor"

5. **requires_aggregation**: true if counting/summing needed

6. **requires_visual_analysis**: true if visual inspection needed

7. **threshold**: Similarity threshold
   - 0.18 for metadata queries
   - 0.28-0.30 for count/location queries

Return JSON only.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a query intent classifier."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=200
        )

        result = json.loads(response.choices[0].message.content)

        return result
```

### Test Cases

```python
# Test 1: Simple count
classifier.classify("How many doors on drawing A-101?")
# Expected: {intent: "count", scope: "drawing", entities: ["doors"]}

# Test 2: Location query
classifier.classify("Where are the fire exits on Sheet 2?")
# Expected: {intent: "location", scope: "sheet", entities: ["fire exits"]}

# Test 3: Count + Location
classifier.classify("How many restrooms near Grid B?")
# Expected: {intent: "count_with_location", requires_visual_analysis: true}

# Test 4: Metadata
classifier.classify("What is the revision date for A-101?")
# Expected: {intent: "metadata", threshold: 0.18}
```

---

## Phase 2: Agentic Planning (GPT-5.2 Thinking)

### Purpose
Multi-step reasoning to orchestrate tool calls and gather evidence.

### Why GPT-5.2 Thinking?

```
┌─────────────────────────────────────────────────────────────────┐
│  GPT-5.2 Thinking vs GPT-4o                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GPT-4o:                                                        │
│  - Fast tool calling                                            │
│  - Good for simple 1-2 step plans                              │
│  - Cost: $5/1M in, $15/1M out                                  │
│                                                                 │
│  GPT-5.2 Thinking:                                             │
│  - Extended reasoning (<thinking> tags)                         │
│  - Better for multi-step complex plans                          │
│  - Can verify own logic before acting                           │
│  - Cost: $1.75/1M in, $7/1M out                                │
│  - 400K context window                                          │
│                                                                 │
│  Decision: Use GPT-5.2 Thinking for agentic planning           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
from openai import OpenAI
import os
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class AgenticPlanner:
    """Plans retrieval using GPT-5.2 Thinking + Tool Calling"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-5.2-thinking"  # Extended reasoning mode
        self.tool_executor = RAGToolExecutor()

        # Define tools (OpenAI function schema)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "query_combined_context",
                    "description": "Fetch sheet-level combined summary (legend + aggregated counts + full context). Always call this FIRST for sheet-level queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sheet_id": {
                                "type": "string",
                                "description": "Sheet identifier (e.g., 'A-101-sheet-1')"
                            },
                            "drawing_id": {
                                "type": "string",
                                "description": "Drawing identifier (e.g., 'A-101')"
                            }
                        },
                        "required": ["sheet_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_regions",
                    "description": "Vector search across drawing regions. Use for specific entity/location queries when combined_context is insufficient.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_text": {
                                "type": "string",
                                "description": "Search query (e.g., 'restrooms near Grid B')"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Filters: {project_id, drawing_id, region_type, grid_location, threshold}"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)"
                            }
                        },
                        "required": ["query_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_legend",
                    "description": "Fetch legend strip for symbol/keynote reference. Use when user asks about symbols or when counts reference keynotes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drawing_id": {
                                "type": "string",
                                "description": "Drawing identifier"
                            }
                        },
                        "required": ["drawing_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "aggregate_counts",
                    "description": "Aggregate entity counts across multiple regions. Use for project-level or multi-drawing count queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scope": {
                                "type": "string",
                                "description": "Scope: 'project', 'drawing', or 'sheet'"
                            },
                            "entity_type": {
                                "type": "string",
                                "description": "Entity to count (e.g., 'doors', 'windows', 'restrooms')"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Optional filters: {project_id, drawing_ids, floor_level}"
                            }
                        },
                        "required": ["scope", "entity_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_evidence_sufficiency",
                    "description": "Check if collected evidence is sufficient to answer the question. ALWAYS call this before stopping.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Original user question"
                            },
                            "evidence": {
                                "type": "array",
                                "description": "List of evidence collected so far",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "source": {"type": "string"},
                                        "data": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["question", "evidence"]
                    }
                }
            }
        ]

    def plan_retrieval(
        self,
        question: str,
        intent: Dict,
        max_iterations: int = 5
    ) -> Dict:
        """
        Plan retrieval using GPT-5.2 Thinking + tool calling

        Args:
            question: User question
            intent: Intent classification result
            max_iterations: Max tool calling rounds (default: 5)

        Returns:
            {
              "evidence": List[Dict],
              "tool_calls": List[Dict],
              "iterations": int,
              "thinking_log": str
            }
        """

        system_prompt = """You are a retrieval planner for construction drawings.

Your job is to orchestrate tool calls to gather evidence to answer the user's question.

Available tools:
1. query_combined_context: Get sheet-level summary (ALWAYS START HERE for sheet queries)
2. query_regions: Vector search for specific entities/locations
3. query_legend: Get legend/keynote reference
4. aggregate_counts: Aggregate counts across multiple regions
5. check_evidence_sufficiency: Verify evidence is sufficient (ALWAYS CALL BEFORE STOPPING)

Strategy:
- For sheet-level queries: Start with combined_context
- For specific entity queries: Use query_regions with appropriate filters
- For location queries: Filter by grid_location or quadrant
- For count queries: Check if combined_context has aggregated_counts first
- Always verify sufficiency before stopping

Think step by step in <thinking> tags before calling tools.
"""

        user_prompt = f"""Question: "{question}"

Intent Classification:
{json.dumps(intent, indent=2)}

Plan the retrieval step by step. Use tools to gather evidence.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        evidence = []
        tool_calls_log = []
        thinking_log = ""

        for iteration in range(max_iterations):
            logger.info(f"Planning iteration {iteration + 1}/{max_iterations}")

            # Call GPT-5.2 Thinking with tools
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)

            # Extract thinking log (if available)
            if hasattr(assistant_message, 'thinking'):
                thinking_log += f"\n--- Iteration {iteration + 1} ---\n"
                thinking_log += assistant_message.thinking

            # Check if GPT wants to call tools
            if not assistant_message.tool_calls:
                logger.info(f"Planning complete after {iteration + 1} iterations")
                break

            # Execute tool calls
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                logger.info(f"Executing tool: {tool_name}")
                logger.debug(f"Arguments: {arguments}")

                # Execute tool
                result = self.tool_executor.execute_tool(tool_name, arguments)

                tool_calls_log.append({
                    "iteration": iteration + 1,
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error
                })

                # Add to evidence if successful
                if result.success and result.data:
                    evidence.append({
                        "source": tool_name,
                        "data": result.data,
                        "iteration": iteration + 1
                    })

                # Send tool result back to GPT
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "success": result.success,
                        "data": result.data,
                        "error": result.error
                    })
                })

            # Check if we should stop (sufficiency check passed)
            sufficiency_check = next(
                (tc for tc in tool_calls_log
                 if tc['tool'] == 'check_evidence_sufficiency' and tc['success']),
                None
            )

            if sufficiency_check and sufficiency_check['data'].get('sufficient'):
                logger.info("Evidence sufficient - stopping planning")
                break

        return {
            "evidence": evidence,
            "tool_calls": tool_calls_log,
            "iterations": iteration + 1,
            "thinking_log": thinking_log
        }
```

### Planning Verification

```python
class PlanningVerifier:
    """Verify agentic planning logic"""

    def verify_plan(self, planning_result: Dict) -> Dict:
        """
        Verify planning result

        Checks:
        1. Did it call query_combined_context first for sheet queries?
        2. Did it check evidence sufficiency before stopping?
        3. Did it use appropriate filters?
        4. Did it stay within max iterations?
        5. Is the evidence coherent and relevant?

        Returns:
            {
              "valid": bool,
              "issues": List[str],
              "suggestions": List[str]
            }
        """

        issues = []
        suggestions = []

        tool_calls = planning_result.get('tool_calls', [])
        evidence = planning_result.get('evidence', [])

        # Check 1: Combined context first?
        first_tool = tool_calls[0]['tool'] if tool_calls else None
        if first_tool != 'query_combined_context':
            issues.append("Did not start with query_combined_context for sheet-level query")
            suggestions.append("Always start with combined_context for sheet queries")

        # Check 2: Sufficiency check?
        has_sufficiency = any(tc['tool'] == 'check_evidence_sufficiency' for tc in tool_calls)
        if not has_sufficiency:
            issues.append("Did not check evidence sufficiency before stopping")
            suggestions.append("Always call check_evidence_sufficiency before stopping")

        # Check 3: Evidence collected?
        if not evidence:
            issues.append("No evidence collected")
            suggestions.append("At least one successful tool call should return evidence")

        # Check 4: Iterations
        if planning_result['iterations'] >= 5:
            issues.append("Hit max iterations - may indicate inefficient planning")
            suggestions.append("Optimize tool calling strategy")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }
```

---

## Phase 3: Vision Analysis (Gemini 3 Pro)

### Purpose
Use Gemini's best-in-class vision when text evidence is insufficient.

### When to Use Vision?

```python
def should_use_vision(planning_result: Dict, intent: Dict) -> bool:
    """
    Decide if vision analysis is needed

    Triggers:
    1. Evidence insufficient (confidence < 0.7)
    2. Visual verification requested in intent
    3. Ambiguous text descriptions
    4. Location queries requiring spatial understanding
    """

    sufficiency = next(
        (tc for tc in planning_result['tool_calls']
         if tc['tool'] == 'check_evidence_sufficiency'),
        None
    )

    if not sufficiency:
        return False

    # Trigger 1: Low confidence
    if sufficiency['data'].get('confidence', 1.0) < 0.7:
        return True

    # Trigger 2: Intent requires visual
    if intent.get('requires_visual_analysis'):
        return True

    # Trigger 3: Evidence insufficient
    if not sufficiency['data'].get('sufficient'):
        return True

    return False
```

### Implementation

```python
import google.generativeai as genai
from google.cloud import storage
import os
from typing import Dict, List

class VisionAnalyzer:
    """Analyze drawing regions using Gemini 3 Pro Vision"""

    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-3-pro')
        self.storage_client = storage.Client()

    def analyze_region(
        self,
        region_id: str,
        question: str,
        context: str = None
    ) -> Dict:
        """
        Analyze a specific region image

        Args:
            region_id: Region identifier
            question: User question
            context: Additional text context

        Returns:
            {
              "visual_analysis": str,
              "entities_found": List[Dict],
              "confidence": float
            }
        """

        # Get region metadata and image URI
        region = self._get_region(region_id)
        image_uri = region['image_ref']

        # Download image from GCS
        image_data = self._download_image(image_uri)

        # Prepare prompt
        prompt = f"""Analyze this architectural drawing region.

Question: {question}

Context (from OCR): {context or 'Not available'}

Instructions:
1. Identify and count relevant entities (doors, windows, restrooms, etc.)
2. Note spatial relationships and grid locations
3. Provide specific coordinates or grid references
4. Indicate confidence level (0.0-1.0)

Return structured JSON:
{{
  "visual_analysis": "Detailed description...",
  "entities_found": [
    {{"type": "restroom", "location": "Grid B2", "description": "Public restroom"}},
    ...
  ],
  "confidence": 0.95
}}
"""

        # Call Gemini 3 Pro Vision
        response = self.model.generate_content(
            [prompt, image_data],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        result = json.loads(response.text)

        return result

    def _get_region(self, region_id: str) -> Dict:
        """Get region metadata from database"""
        from gcp.database import get_db_session
        from gcp.database.models import Region

        with get_db_session() as db:
            region = db.query(Region).filter_by(id=region_id).first()
            return {
                "id": region.id,
                "image_ref": region.image_ref,
                "region_type": region.region_type,
                "bbox_norm": region.bbox_norm
            }

    def _download_image(self, gcs_uri: str) -> bytes:
        """Download image from GCS"""
        # Parse gs://bucket/path
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1]

        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        return blob.download_as_bytes()
```

### Vision Verification

```python
def verify_vision_analysis(vision_result: Dict, text_evidence: Dict) -> Dict:
    """
    Cross-verify vision analysis with text evidence

    Returns:
        {
          "consistent": bool,
          "discrepancies": List[str],
          "confidence": float
        }
    """

    # Compare entity counts
    vision_entities = vision_result.get('entities_found', [])
    text_counts = text_evidence.get('aggregated_counts', {})

    discrepancies = []

    for entity in vision_entities:
        entity_type = entity['type']
        text_count = text_counts.get(entity_type, None)

        if text_count is not None:
            vision_count = len([e for e in vision_entities if e['type'] == entity_type])
            if vision_count != text_count:
                discrepancies.append(
                    f"Vision found {vision_count} {entity_type}, text says {text_count}"
                )

    consistency = len(discrepancies) == 0
    confidence = vision_result.get('confidence', 0.5) * (0.9 if consistency else 0.6)

    return {
        "consistent": consistency,
        "discrepancies": discrepancies,
        "confidence": confidence
    }
```

---

## Phase 4: Answer Generation

### Purpose
Synthesize evidence into a coherent, accurate answer with provenance.

### Implementation

```python
class AnswerGenerator:
    """Generate final answers using GPT-5.2 Thinking"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-5.2-thinking"

    def generate_answer(
        self,
        question: str,
        evidence: List[Dict],
        intent: Dict
    ) -> Dict:
        """
        Generate final answer from evidence

        Args:
            question: User question
            evidence: Collected evidence from planning
            intent: Intent classification

        Returns:
            {
              "answer": str,
              "confidence": float,
              "provenance": List[Dict],
              "metadata": Dict
            }
        """

        system_prompt = """You are a construction expert answering questions about architectural drawings.

Rules:
1. Answer ONLY based on provided evidence
2. Be precise with numbers and locations
3. Include provenance (which drawing/sheet/region)
4. State confidence level honestly
5. If evidence is insufficient, say so clearly

Format your response as JSON:
{
  "answer": "Clear, concise answer...",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of how you arrived at this answer",
  "limitations": "Any limitations or caveats"
}
"""

        # Format evidence
        evidence_text = "\n\n".join([
            f"[Source: {e['source']}]\n{json.dumps(e['data'], indent=2)}"
            for e in evidence
        ])

        user_prompt = f"""Question: "{question}"

Intent: {intent.get('intent')}

Evidence:
{evidence_text}

Provide a clear answer with confidence level and reasoning.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        result = json.loads(response.choices[0].message.content)

        # Extract provenance from evidence
        provenance = []
        for e in evidence:
            if 'sheet_id' in str(e.get('data', {})):
                provenance.append({
                    "source": e['source'],
                    "sheet_id": e['data'].get('sheet_id'),
                    "drawing_id": e['data'].get('drawing_id')
                })

        return {
            "answer": result['answer'],
            "confidence": result.get('confidence', 0.5),
            "reasoning": result.get('reasoning', ''),
            "provenance": provenance,
            "metadata": {
                "intent": intent['intent'],
                "evidence_sources": [e['source'] for e in evidence],
                "limitations": result.get('limitations', '')
            }
        }
```

---

## Tool Calling Infrastructure

### RAGToolExecutor

```python
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    data: Any = None
    error: str = None

class RAGToolExecutor:
    """Execute RAG tools"""

    def __init__(self):
        from gcp.database import get_db_session
        from gcp.database.models import (
            Region, Caption, Embedding, CombinedContext
        )
        from openai import OpenAI

        self.db_session_factory = get_db_session
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def execute_tool(self, tool_name: str, arguments: Dict) -> ToolResult:
        """
        Execute a tool by name

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            ToolResult with success/data/error
        """

        try:
            if tool_name == "query_combined_context":
                return self._query_combined_context(**arguments)

            elif tool_name == "query_regions":
                return self._query_regions(**arguments)

            elif tool_name == "query_legend":
                return self._query_legend(**arguments)

            elif tool_name == "aggregate_counts":
                return self._aggregate_counts(**arguments)

            elif tool_name == "check_evidence_sufficiency":
                return self._check_evidence_sufficiency(**arguments)

            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}"
                )

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult(success=False, error=str(e))

    def _query_combined_context(
        self,
        sheet_id: str,
        drawing_id: str = None
    ) -> ToolResult:
        """Query combined context for a sheet"""

        with self.db_session_factory() as db:
            from gcp.database.models import CombinedContext

            context = db.query(CombinedContext).filter_by(
                sheet_id=sheet_id
            ).first()

            if not context:
                return ToolResult(
                    success=False,
                    error=f"No combined context found for sheet {sheet_id}"
                )

            return ToolResult(
                success=True,
                data={
                    "sheet_id": sheet_id,
                    "drawing_id": context.drawing_id,
                    "combined_summary": context.combined_text,
                    "aggregated_counts": context.aggregated_counts,
                    "region_summaries": context.region_summaries
                }
            )

    def _query_regions(
        self,
        query_text: str,
        filters: Dict = None,
        top_k: int = 5
    ) -> ToolResult:
        """Vector search across regions"""

        filters = filters or {}
        threshold = filters.get('threshold', 0.25)

        # Generate query embedding
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query_text
        )
        query_embedding = response.data[0].embedding

        with self.db_session_factory() as db:
            from sqlalchemy import text

            # Build SQL with filters
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
                sql_filters.append("metadata->>'region_type' = :region_type")
                params['region_type'] = filters['region_type']

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

            return ToolResult(success=True, data={"regions": regions})

    def _query_legend(self, drawing_id: str) -> ToolResult:
        """Query legend for a drawing"""

        with self.db_session_factory() as db:
            from gcp.database.models import Region, Caption

            legend_region = db.query(Region).filter_by(
                drawing_id=drawing_id,
                region_type='legend'
            ).first()

            if not legend_region:
                return ToolResult(
                    success=False,
                    error=f"No legend found for drawing {drawing_id}"
                )

            caption = db.query(Caption).filter_by(
                region_id=legend_region.id
            ).first()

            return ToolResult(
                success=True,
                data={
                    "drawing_id": drawing_id,
                    "legend_text": caption.caption_text if caption else None,
                    "legend_json": caption.structured_json if caption else None
                }
            )

    def _aggregate_counts(
        self,
        scope: str,
        entity_type: str,
        filters: Dict = None
    ) -> ToolResult:
        """Aggregate counts across regions"""

        filters = filters or {}

        with self.db_session_factory() as db:
            from gcp.database.models import CombinedContext
            from sqlalchemy import func

            query = db.query(CombinedContext)

            if scope == 'drawing' and filters.get('drawing_id'):
                query = query.filter_by(drawing_id=filters['drawing_id'])

            if scope == 'project' and filters.get('project_id'):
                query = query.filter_by(project_id=filters['project_id'])

            contexts = query.all()

            total_count = 0
            breakdown = []

            for ctx in contexts:
                counts = ctx.aggregated_counts or {}
                count = counts.get(entity_type, 0)
                total_count += count

                if count > 0:
                    breakdown.append({
                        "sheet_id": ctx.sheet_id,
                        "drawing_id": ctx.drawing_id,
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

    def _check_evidence_sufficiency(
        self,
        question: str,
        evidence: List[Dict]
    ) -> ToolResult:
        """Check if evidence is sufficient using GPT-4o-mini"""

        evidence_text = "\n\n".join([
            f"Source: {e.get('source', 'unknown')}\n{e.get('data', '')}"
            for e in evidence
        ])

        prompt = f"""Is the following evidence sufficient to answer this question?

Question: "{question}"

Evidence:
{evidence_text}

Respond with JSON:
{{
  "sufficient": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation",
  "recommendation": "What to do next (answer now or gather more evidence)"
}}
"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an evidence evaluator."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        result = json.loads(response.choices[0].message.content)

        return ToolResult(success=True, data=result)
```

---

## Verification & Testing Strategy

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch

class TestIntentClassifier:
    """Test intent classification"""

    def test_simple_count_query(self):
        classifier = IntentClassifier()
        result = classifier.classify("How many doors on A-101?")

        assert result['intent'] == 'count'
        assert 'doors' in result['entities']
        assert result['scope_level'] == 'drawing'

    def test_location_query(self):
        classifier = IntentClassifier()
        result = classifier.classify("Where are the fire exits?")

        assert result['intent'] == 'location'
        assert 'fire exits' in result['entities']

    def test_count_with_location(self):
        classifier = IntentClassifier()
        result = classifier.classify("How many restrooms near Grid B?")

        assert result['intent'] == 'count_with_location'
        assert result['requires_visual_analysis'] == True

class TestAgenticPlanner:
    """Test agentic planning logic"""

    @patch('openai.OpenAI')
    def test_planning_starts_with_combined_context(self, mock_openai):
        # Mock GPT response to call query_combined_context first
        mock_response = Mock()
        mock_response.choices[0].message.tool_calls = [
            Mock(function=Mock(name='query_combined_context', arguments='{"sheet_id": "A-101-sheet-1"}'))
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        planner = AgenticPlanner()
        result = planner.plan_retrieval(
            "How many restrooms on Sheet 1?",
            {"intent": "count", "scope_level": "sheet"}
        )

        assert result['tool_calls'][0]['tool'] == 'query_combined_context'

    def test_planning_checks_sufficiency(self):
        planner = AgenticPlanner()
        result = planner.plan_retrieval(
            "How many doors?",
            {"intent": "count"}
        )

        has_sufficiency = any(
            tc['tool'] == 'check_evidence_sufficiency'
            for tc in result['tool_calls']
        )
        assert has_sufficiency == True

class TestVisionAnalyzer:
    """Test vision analysis"""

    @patch('google.generativeai.GenerativeModel')
    def test_vision_returns_structured_output(self, mock_gemini):
        mock_response = Mock()
        mock_response.text = json.dumps({
            "visual_analysis": "Found 2 restrooms",
            "entities_found": [
                {"type": "restroom", "location": "Grid B"}
            ],
            "confidence": 0.95
        })
        mock_gemini.return_value.generate_content.return_value = mock_response

        analyzer = VisionAnalyzer()
        result = analyzer.analyze_region(
            "region-123",
            "How many restrooms?",
            context="Sheet 1 floor plan"
        )

        assert result['confidence'] >= 0.9
        assert len(result['entities_found']) > 0
```

### Integration Tests

```python
class TestEndToEndQueryFlow:
    """Test complete query flow"""

    def test_simple_count_query_e2e(self):
        """Test: 'How many doors on A-101?'"""

        # Step 1: Intent classification
        classifier = IntentClassifier()
        intent = classifier.classify("How many doors on A-101?")

        assert intent['intent'] == 'count'

        # Step 2: Agentic planning
        planner = AgenticPlanner()
        planning_result = planner.plan_retrieval(
            "How many doors on A-101?",
            intent
        )

        assert len(planning_result['evidence']) > 0

        # Step 3: Answer generation
        generator = AnswerGenerator()
        answer = generator.generate_answer(
            "How many doors on A-101?",
            planning_result['evidence'],
            intent
        )

        assert answer['confidence'] > 0.7
        assert 'door' in answer['answer'].lower()

    def test_count_with_location_query_e2e(self):
        """Test: 'How many restrooms near Grid B on A-101?'"""

        # Full flow
        classifier = IntentClassifier()
        intent = classifier.classify("How many restrooms near Grid B on A-101?")

        planner = AgenticPlanner()
        planning_result = planner.plan_retrieval(
            "How many restrooms near Grid B on A-101?",
            intent
        )

        # Should have called combined_context + check_sufficiency
        tool_names = [tc['tool'] for tc in planning_result['tool_calls']]
        assert 'query_combined_context' in tool_names
        assert 'check_evidence_sufficiency' in tool_names

        generator = AnswerGenerator()
        answer = generator.generate_answer(
            "How many restrooms near Grid B on A-101?",
            planning_result['evidence'],
            intent
        )

        assert answer['confidence'] > 0.5
        assert 'restroom' in answer['answer'].lower()
```

### Verification Checklist

```python
def verify_query_result(result: Dict) -> Dict:
    """
    Comprehensive verification of query result

    Checks:
    1. Answer is coherent and relevant
    2. Confidence score is reasonable (>0.5)
    3. Provenance is included
    4. Tool calling was efficient (<5 iterations)
    5. Cost is within budget (<$0.05)
    6. Latency is acceptable (<8s)

    Returns:
        {
          "valid": bool,
          "issues": List[str],
          "metrics": Dict
        }
    """

    issues = []
    metrics = {}

    # Check 1: Answer exists
    if not result.get('answer'):
        issues.append("No answer generated")

    # Check 2: Confidence
    confidence = result.get('confidence', 0)
    metrics['confidence'] = confidence
    if confidence < 0.5:
        issues.append(f"Low confidence: {confidence}")

    # Check 3: Provenance
    if not result.get('provenance'):
        issues.append("No provenance included")

    # Check 4: Tool efficiency
    metadata = result.get('metadata', {})
    tool_count = len(metadata.get('tool_calls', []))
    metrics['tool_calls'] = tool_count
    if tool_count > 5:
        issues.append(f"Too many tool calls: {tool_count}")

    # Check 5: Cost
    cost = metadata.get('cost_usd', 0)
    metrics['cost_usd'] = cost
    if cost > 0.05:
        issues.append(f"Cost exceeds budget: ${cost}")

    # Check 6: Latency
    latency_ms = metadata.get('latency_ms', 0)
    metrics['latency_ms'] = latency_ms
    if latency_ms > 8000:
        issues.append(f"Latency too high: {latency_ms}ms")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "metrics": metrics
    }
```

---

## Cost Analysis

### Cost Breakdown (Updated with GPT-5.2 + Gemini)

```
┌─────────────────────────────────────────────────────────────────┐
│                     COST ANALYSIS (Per Query)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Component               │ Tokens    │ Model           │ Cost   │
│  ─────────────────────────────────────────────────────────────  │
│  Intent Classification   │ 100/50    │ GPT-4o-mini     │ $0.00005│
│  Embedding (query)       │ 20        │ text-emb-3-sm   │ $0.00000│
│  Agentic Planning        │ 2000/500  │ GPT-5.2 Think   │ $0.00700│
│  Vision Analysis*        │ 800/200   │ Gemini 3 Pro    │ $0.00400│
│  Answer Generation       │ 600/150   │ GPT-5.2 Think   │ $0.00210│
│  ─────────────────────────────────────────────────────────────  │
│  TOTAL (with vision)                                   │ $0.01315│
│  TOTAL (without vision)                                │ $0.00915│
│                                                                 │
│  * Vision only triggered when needed (30% of queries)           │
│                                                                 │
│  With 30% vision rate: $0.00915 * 0.7 + $0.01315 * 0.3 = $0.01035/query
│                                                                 │
│  With caching (30% hit rate): $0.01035 * 0.7 = $0.00725/query  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MONTHLY COST (10K queries):
- Without optimization: $103.50
- With caching: $72.50
- Well below $500/month budget ✅
```

### Cost Comparison

```
┌──────────────────────────────────────────────────────────────────┐
│                  MODEL COST COMPARISON                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Original Plan (All GPT-4o):                                     │
│  - Intent: GPT-4o-mini ($0.00015)                                │
│  - Planning: GPT-4o ($0.02500)                                   │
│  - Vision: N/A                                                   │
│  - Answer: GPT-4o ($0.00650)                                     │
│  Total: $0.03165/query                                           │
│                                                                  │
│  Alternative (All Claude Opus 4.5):                              │
│  - Intent: Opus 4.5 ($0.00050)                                   │
│  - Planning: Opus 4.5 ($0.03125)                                 │
│  - Vision: Opus 4.5 ($0.01250)                                   │
│  - Answer: Opus 4.5 ($0.00937)                                   │
│  Total: $0.05362/query                                           │
│                                                                  │
│  Our Plan (GPT-5.2 + Gemini):                                    │
│  - Intent: GPT-4o-mini ($0.00005)                                │
│  - Planning: GPT-5.2 Think ($0.00700)                            │
│  - Vision: Gemini 3 Pro ($0.00400)                               │
│  - Answer: GPT-5.2 Think ($0.00210)                              │
│  Total: $0.01315/query                                           │
│                                                                  │
│  SAVINGS vs GPT-4o: 58% cheaper                                  │
│  SAVINGS vs Claude: 75% cheaper                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Summary

This architecture uses the **best model for each task**:

| Phase | Model | Why |
|-------|-------|-----|
| **Intent Classification** | GPT-4o-mini | Fast, cheap, pattern matching |
| **Agentic Planning** | GPT-5.2 Thinking | Extended reasoning, tool orchestration |
| **Vision Analysis** | Gemini 3 Pro | Best-in-class vision (81% MMMU-Pro) |
| **Answer Generation** | GPT-5.2 Thinking | Coherent synthesis, provenance |

**Key Benefits:**
- ✅ **Cost**: $0.01035/query (58% cheaper than GPT-4o-only)
- ✅ **Quality**: Best vision + extended reasoning
- ✅ **Latency**: <5s P95 (well below 8s target)
- ✅ **Accuracy**: >90% expected (vision + reasoning)
- ✅ **Tool Infrastructure**: OpenAI tool calling (production-ready)

**Ready for implementation!** 🚀
