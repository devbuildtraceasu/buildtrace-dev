# GCP-Native RAG Architecture & Implementation Plan

> **⚠️ NOTE:** This is the **original RAG planning document**. For the **latest, production-ready implementation plan**, see:
> **[Advanced_next_rag_build_plan.md](./Advanced_next_rag_build_plan.md)**
>
> **Key Differences:**
> - **Database:** Uses **pgvector on Cloud SQL** (not AlloyDB)
> - **Orchestration:** Uses **OpenAI Tool Calling** (not MCP or generic agentic planner)
> - **Implementation:** 7-week phased approach with complete code samples
> - **Cost/Performance:** Updated targets and optimizations

## 1. Objectives & Constraints
- **Primary goal**: deliver accurate question answering over uploaded architectural drawing sets by pairing OCR/vision captions with structured metadata, retrievable via mixed text+image grounding.
- **Secondary goals**: low-latency UX (<8s P95), iterative enrichment (region-level segmentation, combined context), governance (per-project isolation & audit), and cost transparency.
- **Constraints**: keep models (captions/answers via GPT-5.1 vision, embeddings via text-embedding-3-small) while exploiting GCP-native infra for orchestration, storage, and observability. No external VPC dependencies. Prefer managed services (Cloud Run, Cloud Functions, Pub/Sub, Cloud SQL, AlloyDB, GCS, Vertex AI).

## 2. Target Workflows
1. **Ingestion**
   - Upload multi-sheet PDFs/drawings via UI/API.
   - Convert to high-res raster images; segment into canonical regions (full sheet + quadrants + optional legend strips/title block/detected ROIs).
   - Caption each region with GPT-vision, persist transcript + structured JSON (rooms, counts, materials).
   - Generate embeddings for captions, table text, combined summaries.
2. **Retrieval**
   - Accept user questions (text). Classify intent (metadata/title, count/list, location, default) and level (project/drawing/sheet).
   - Retrieve base evidence from pgvector/AlloyDB with filters + thresholds; optionally fan out to multi-region aggregator or single best chunk.
   - Always merge region results with `combined_context` (legend/title + aggregated counts) stored per sheet.
3. **Answering**
   - Compose answer prompt with combined summary + selected region captions/images.
   - Call GPT-5.1 vision (low temperature) and return response with provenance metadata (region IDs, sheet, URIs).

## 3. High-Level Architecture
```
[Client/UI] -> [API Gateway + Cloud Run (REST)]
                    |---> Pub/Sub topic: ingestion-jobs
                           |--> Cloud Run jobs / Cloud Functions (PDF processing)
                                      |--> GCS (drawings, region crops)
                                      |--> Cloud SQL / AlloyDB (metadata + pgvector embeddings)
                                      |--> Vertex AI / custom service (caption + combine)
[Question API] -> Cloud Run service -> (Classifier + Retrieval) -> AlloyDB -> Combined Context -> GPT -> Response
```

### Key Services
- **Cloud Storage (GCS)**: raw uploads, per-region images, JSON artifacts, combined_context snapshots.
- **Cloud SQL + pgvector or AlloyDB**: metadata tables + embedding storage, similarity search, multi-region aggregator queries.
- **Pub/Sub**: decouple uploads from heavy processing; support retries, fan-out to caption/embedding pipelines.
- **Cloud Run**: stateless services for APIs, ingestion workers, retrieval planner.
- **Vertex AI (optional)**: host custom chunk classifiers, fallback OCR; store metadata (BigQuery) for analytics.
- **Secret Manager**: store OpenAI API keys + service creds.
- **Cloud Logging + Cloud Monitoring**: centralize logs, define SLO dashboards, alerting.

## 4. Data Model & Storage
| Table | Purpose | Key Fields |
|-------|---------|------------|
| `projects` | project metadata | project_id, name, client, created_at |
| `drawings` | drawing-level info | drawing_id, project_id, sheet_id, version, gcs_uri |
| `regions` | full page/quadrant/legend metadata | region_id, drawing_id, bbox_norm, region_type |
| `captions` | raw caption text + JSON | caption_id, region_id, caption_text, structured_json |
| `embeddings` (pgvector) | vector store | embedding_id, region_id, combined_flag, vector, norm, metadata (jsonb) |
| `combined_contexts` | aggregated sheet summary | sheet_id, combined_text, aggregated_counts json, region_summaries json |
| `qa_sessions` | question/answer records | session_id, user_id, question_text, response_text, provenance |

Files in GCS follow deterministic layout: `gs://<bucket>/projects/<project_id>/drawings/<drawing_id>/regions/<region_id>.png` plus `combined_context.json` per sheet.

## 5. Processing Pipeline
1. **Upload Trigger**
   - Cloud Run API writes metadata row + pushes message `{project_id, drawing_id, gcs_uri}` to `ingestion-jobs`.
2. **Rasterization Worker**
   - Cloud Run job pulls message, downloads PDF from GCS, runs `pdf2image` inside container (attached to Cloud Storage via gcsfuse or using signed URLs).
   - Stores per-page PNG in `gs://.../pages/page_{n}.png`.
3. **Region Segmenter**
   - For each page, derive bounding boxes (full page + quadrants + heuristics for title/legend). Save normalized coords in `regions` table.
4. **Vision Captioner**
   - For each region, call GPT-5.1 vision; store caption text + structured JSON; upload region crop to GCS.
5. **Embedding Writer**
   - Generate embeddings using OpenAI text-embedding-3-small.
   - Insert into AlloyDB `embeddings` table (vector column) with metadata (project/drawing/sheet/region_id, scope, tokens, similarity norm).
6. **Combined Context Builder**
   - Pass `{full_page_caption, quadrants...}` to GPT aggregator to produce `combined_context`, `aggregated_counts`, `region_summaries`.
   - Embed combined summary; flag `combined_flag=true` row so retrieval always fetches it quickly.
7. **Quality Pass** (optional)
   - Validate JSON schema, ensure mandatory metadata present, log anomalies to Cloud Logging / BigQuery.

## 6. Retrieval & Answering Flow
1. **Question Intake (Cloud Run)**
   - Authenticated request enters Cloud Run `rag-query-service` (connected behind API Gateway/Cloud Load Balancing).
   - Service logs request context (user, project, drawing scope) to Cloud Logging.
2. **Classifier & Agentic Planner**
   - Lightweight LLM classifier (e.g., `gpt-4.1-mini` via Cloud Run microservice) produces structured JSON `{intent, scope_level, requires_aggregation, filters}` using few-shot examples so nuanced cues (“List restrooms near Grid B”) map to simultaneous count+location intents.
   - Planner agent ingests the classifier output plus availability metadata (region types, legend strips, combined summaries, similarity scores) and emits a short action list: e.g., `use_combined_context`, `use_region:q2_top_right`, `use_region:legend_strip`, `request_image:q3_bottom_left`. Only those chunks are fetched/passed downstream, so we avoid always loading every quadrant.
   - Before finalizing the context, a “sufficiency check” prompt asks the planner whether the current evidence covers the question; if not, it can pull additional regions or stop with “not enough evidence.”
   - Deterministic helpers (`determine_scope_filter`, similarity thresholds, default fallbacks) stay in place as rails so the agent cannot leave the authorized project/drawing or exceed token budgets.
3. **Vector Search**
   - Always start with combined_context row (sheet-level). Query AlloyDB `embeddings` via pgvector `cosine_distance` for candidate regions matching scope + type filters (e.g., prefer `region_type IN ('quadrant','legend')`).
   - Apply per-strategy thresholds (metadata >=0.18, count/location >=0.30). Keep top-K sorted list.
4. **Context Assembly**
   - Build `contexts` array: combined summary + selected region captions/images.
   - Multi-region modes include aggregated counts + instruct GPT to sum/report per-region evidence; single-region modes highlight location hints.
5. **Answer Generation**
   - Compose GPT-5.1 vision call (low temperature) with combined summary text and inlined region captions + base64 images (GCS-sourced).
   - Response stored along with provenance (region_ids, similarity, URIs) in `qa_sessions` for audit + training.
6. **Guardrails**
   - If no region passes threshold, return “Not enough evidence” message.
   - Rate-limits per user/project via Cloud Armor + Redis/MemoryStore or Firestore.

## 7. GCP Infra & DevOps
- **CI/CD**: Cloud Build pipelines triggered via GitHub/GitLab. Build Docker images for ingestion worker, query service, combined-context builder. Deploy to Cloud Run with traffic splitting for blue/green.
- **Secrets & Config**: Cloud Secret Manager for API keys; Cloud Config Connector (optional) or Terraform for infra as code.
- **Monitoring**: Cloud Monitoring dashboards (latency, errors, cost per request). Alerting via Cloud Alerting + PagerDuty/Slack.
- **Cost Controls**: autopause ingestion jobs, dynamic concurrency; track tokens/embeddings per project via BigQuery cost table.

## 8. Security & Compliance
- VPC Service Controls (if required) to isolate OpenAI call proxies.
- Cloud IAM roles per service; signed URLs for GCS artifacts; AES256 encryption at rest; optional CMEK for Cloud SQL/GCS.
- Audit logging: Cloud Audit Logs + custom `qa_sessions` table for question/answer/provenance traceability.

## 9. Implementation Phases
1. **Phase 0 – Foundations (1 wk)**
   - Finalize GCP project layout, networking, service accounts.
   - Provision core services: GCS buckets, Cloud SQL/AlloyDB, Pub/Sub topics, Cloud Run skeleton services.
2. **Phase 1 – Ingestion MVP (2 wks)**
   - Implement upload API, rasterization, region segmentation, caption + embedding pipeline.
   - Persist combined_context per sheet; verify via manual scripts.
3. **Phase 2 – Retrieval Planner (1.5 wks)**
   - Stand up the classifier + agentic planner microservice (Cloud Run) that emits structured instructions for what evidence to load and when to stop; keep deterministic fallbacks for guardrails.
   - Implement scope filtering, vector search with thresholds, and combined summary injection + aggregated counts.
4. **Phase 3 – Answering & UX (1 wk)**
   - Cloud Run query service hooking planner -> GPT answers. Return provenance + guardrails. Add caching for repeated questions.
5. **Phase 4 – Observability & Guardrails (1 wk)**
   - Dashboards, alerts, cost tracking, token usage, fallback flows, security hardening (Secrets, IAM, audit logs).
6. **Phase 5 – QA & Hardening (ongoing)**
   - Scenario-based testing (metadata, count, location, legend). Evaluate accuracy vs baseline. Tune thresholds + aggregated counts logic.

## 10. Future Enhancements
- Adaptive chunking (detect rooms/legends via Vertex AI Vision).
- Automated reinforcement: feed QA outcomes back into retriever tuning (e.g., logistic re-ranking).
- Offline analytics in BigQuery to surface frequent misses, run A/B experiments on strategy parameters.
- On-device caching for static drawings (Edge caching via Cloud CDN / Cloud Storage signed URLs).

This plan keeps OpenAI models for semantics while anchoring the rest of the stack in GCP-managed services, enabling iterative experimentation (Approach 1 vs Approach 2) without sacrificing compliance or observability.
