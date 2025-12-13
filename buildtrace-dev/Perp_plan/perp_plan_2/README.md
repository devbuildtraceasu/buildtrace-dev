# perp_plan_2 – Approach 2 (Combined Context Planner)

Approach 2 keeps the core PDF→image→caption flow but introduces two major upgrades:

1. **Smarter planner** – Every question starts with the combined context summary and only the
   minimum set of regions required by the detected intent. No more loading all 5 chunks into the
   answer model. Metadata/title questions usually rely on the combined summary + full page;
   location/count questions add only the top-K quadrants that clear the similarity threshold.
2. **`combined_context` aggregator** – After captioning the full sheet and the four quadrants,
   we call the LLM to produce a deduplicated, count-aware summary. This aggregated payload blends
   legend/title-block info with quadrant details so individual regions inherit sheet context.

## How to run

```bash
cd perp_plan_2
python3 approach2_combined_rag.py \
  --pdf ../testing/Temple/TempleTest_Add1.pdf \
  --page 0 \
  --dpi 300 \
  --questions ../rag_integration_test/q_sample.txt \
  --output output
```

Each invocation writes to `output/<drawing_name>_<YYYYMMDD_HHMMSS>/`, storing:

- `captions.json` – raw captions per region.
- `combined_context.json` – LLM-produced combined summary with aggregated counts.
- `embeddings_full.json` / `embeddings_metadata.json` – region metadata for debugging.
- `rag_results.json` – per-question answers plus which contexts were used.

## Planner intent buckets

- **metadata/title** → combined summary + (optionally) full page.
- **count/list** → combined summary + top-4 quadrants clearing threshold (aggregation on).
- **location** → combined summary + top-3 quadrants (0.3 similarity floor, include full page if absent).
- **default** → combined summary + highest-sim single region.

Combined summary is *always* injected first so every question sees legend/title context even when
only a single quadrant is used for targeted evidence.
