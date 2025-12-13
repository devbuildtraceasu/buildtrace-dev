#!/usr/bin/env python3
"""
Approach 2: Combined-context RAG planner.

Differences vs approach 1:
- Captions full page + quadrants but immediately build a combined_context summary that aggregates
  legend/title info with quadrant details (counts, locations, etc.).
- Retrieval planner always injects the combined_context first, then selectively adds only the
  regions required by a question (no more auto-loading all 5 chunks).
- Provenance includes the combined summary plus the minimal region set used so QA can iterate
  without losing context.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:
    from pdf2image import convert_from_path
    import PIL.Image
    PIL.Image.MAX_IMAGE_PIXELS = 200_000_000
except ImportError:
    convert_from_path = None  # type: ignore
    PIL = None  # type: ignore

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

EMBEDDING_MODEL = "text-embedding-3-small"
ANSWER_MODEL = "gpt-5.1"
CAPTION_MODEL = "gpt-5.1"
COMBINER_MODEL = "gpt-5.1"


@dataclass
class Region:
    region_id: str
    bbox: Tuple[float, float, float, float]
    description: str = ""


@dataclass
class RetrievalStrategy:
    intent: str
    mode: str  # "single" or "multi"
    top_k: int
    prefer_full_page: bool = False
    fallback_k: int = 0
    include_full_page: bool = False
    similarity_threshold: Optional[float] = None
    aggregation: bool = False
    description: str = ""


def fail_missing_dep(name: str, fix: str) -> None:
    print(f"ERROR: Missing dependency '{name}'. {fix}")
    sys.exit(1)


def safe_parse_json(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    text = raw_text.strip()
    if "```json" in text:
        try:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        except Exception:
            pass
    elif "```" in text:
        try:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        except Exception:
            pass
    try:
        return json.loads(text), None
    except Exception as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate), None
            except Exception as exc2:
                return None, f"{exc} | brace-scan: {exc2}"
        return None, str(exc)


def clamp_bbox(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0.0, x0), max(0.0, y0)
    x1, y1 = min(1.0, x1), min(1.0, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"Invalid bbox: {bbox}")
    return x0, y0, x1, y1


def process_pdf_to_image(pdf_path: Path, page_num: int, dpi: int, output_dir: Path) -> Path:
    if convert_from_path is None:
        fail_missing_dep("pdf2image", "Install with: pip install pdf2image pillow")
    images = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_num + 1, last_page=page_num + 1)
    if not images:
        raise RuntimeError("No pages found in PDF")
    img_path = output_dir / f"page_{page_num+1}.png"
    images[0].save(img_path, "PNG")
    print(f"[PDF] Saved image: {img_path}")
    return img_path


def crop_image(image_path: Path, bbox: Tuple[float, float, float, float], output_dir: Path, suffix: str) -> Path:
    if PIL is None:
        fail_missing_dep("Pillow", "Install with: pip install pillow")
    with PIL.Image.open(image_path) as img:
        w, h = img.size
        x0, y0, x1, y1 = bbox
        crop_box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
        cropped = img.crop(crop_box)
        out_path = output_dir / f"{image_path.stem}_{suffix}.png"
        cropped.save(out_path, "PNG")
        print(f"[CROP] {suffix}: {cropped.size} -> {out_path}")
        return out_path


class OpenAIRegionCaptioner:
    def __init__(self, api_key: str, model_name: str = CAPTION_MODEL, debug_dir: Optional[Path] = None):
        if not OPENAI_AVAILABLE:
            fail_missing_dep("openai", "Install with: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.debug_dir = debug_dir

    def caption(self, image_path: Path, drawing_name: str, page_num: int, region: Region, max_tokens: int) -> Optional[str]:
        if PIL is None:
            fail_missing_dep("Pillow", "Install with: pip install pillow")
        with PIL.Image.open(image_path) as img:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
        prompt = (
            "Provide an exhaustive caption for this architectural drawing region. "
            "List spaces, annotations, dimensions, tags, and any visible text. "
            "This will feed into RAG, so preserve the wording on sheet."
        )
        content = [
            {"type": "text", "text": f"Drawing {drawing_name} page {page_num} region {region.region_id} ({region.description})"},
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"}},
        ]
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You describe architectural drawing regions in meticulous detail."},
                {"role": "user", "content": content},
            ],
            max_completion_tokens=max_tokens,
            temperature=0.2,
        )
        caption_text = resp.choices[0].message.content
        if self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            (self.debug_dir / f"caption_{region.region_id}.txt").write_text(caption_text)
        return caption_text


class EmbeddingGenerator:
    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        if not OPENAI_AVAILABLE:
            fail_missing_dep("openai", "Install with: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, text: str) -> List[float]:
        return self.client.embeddings.create(model=self.model, input=text).data[0].embedding


class CombinedContextBuilder:
    def __init__(self, api_key: str, model_name: str = COMBINER_MODEL):
        if not OPENAI_AVAILABLE:
            fail_missing_dep("openai", "Install with: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def build(self, caption_records: List[Dict[str, str]], drawing_name: str, page_number: int) -> Dict[str, Any]:
        instructions = (
            "You will receive captions for the full page and up to four quadrant regions. "
            "Create a single JSON payload that aggregates all knowledge so quadrants inherit "
            "legend/title-block context. Name the primary narrative 'combined_context'. "
            "Also summarize aggregated counts (doors, restrooms, grids, etc.) and per-region highlights."
        )
        region_lines = []
        for record in caption_records:
            region_lines.append(
                f"Region {record['region_id']}: {record['caption'][:4000]}"
            )
        content = [{"type": "text", "text": instructions}, {"type": "text", "text": "\n\n".join(region_lines)}]
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an architect CoT combiner. Respond ONLY with valid JSON containing: "
                        "combined_context (string, rich summary), aggregated_counts (list of objects with 'item', 'total', 'regions'), "
                        "and region_summaries (list of objects with 'region_id' and 'key_points')."
                    ),
                },
                {"role": "user", "content": content},
            ],
            max_completion_tokens=1200,
            temperature=0,
        )
        raw = resp.choices[0].message.content
        data, err = safe_parse_json(raw)
        if err:
            print(f"[Combined] JSON parse fallback: {err}")
        if not data:
            data = {
                "combined_context": "\n".join(region_lines),
                "aggregated_counts": [],
                "region_summaries": caption_records,
            }
        data.setdefault("combined_context", "\n".join(region_lines))
        data.setdefault("aggregated_counts", [])
        data.setdefault("region_summaries", caption_records)
        data["drawing_name"] = drawing_name
        data["page_number"] = page_number
        return data


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a * mag_b else 0.0


def requires_aggregation(question: str) -> bool:
    q = question.lower()
    agg_terms = ["how many", "number of", "count", "list", "all ", "total", "show all", "enumerate"]
    return any(term in q for term in agg_terms)


def determine_retrieval_strategy(question: str) -> RetrievalStrategy:
    q = question.lower()
    metadata_terms = ["title", "sheet", "scale", "legend", "grid", "revision", "metadata"]
    location_terms = ["where", "location", "located", "quadrant", "region"]
    if any(term in q for term in metadata_terms):
        return RetrievalStrategy(
            intent="metadata",
            mode="single",
            top_k=2,
            prefer_full_page=True,
            fallback_k=2,
            description="Sheet/title/legend question; rely on combined summary + full page if needed",
        )
    if any(term in q for term in location_terms):
        return RetrievalStrategy(
            intent="location",
            mode="multi",
            top_k=3,
            include_full_page=True,
            similarity_threshold=0.3,
            aggregation=True,
            description="Location query; use combined summary + top-3 quadrants",
        )
    if requires_aggregation(question):
        return RetrievalStrategy(
            intent="count",
            mode="multi",
            top_k=4,
            include_full_page=True,
            aggregation=True,
            description="Count/list query; aggregated summary + targeted quadrants",
        )
    return RetrievalStrategy(
        intent="default",
        mode="single",
        top_k=2,
        fallback_k=2,
        description="Default factual question",
    )


def plan_contexts(
    strategy: RetrievalStrategy,
    combined_entry: Dict[str, Any],
    scored_regions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    contexts: List[Dict[str, Any]] = [
        {
            "kind": "combined",
            "text": combined_entry["metadata"].get("combined_context", ""),
            "aggregated_counts": combined_entry["metadata"].get("aggregated_counts", []),
            "region_summaries": combined_entry["metadata"].get("region_summaries", []),
            "metadata": combined_entry["metadata"],
        }
    ]
    threshold = (
        strategy.similarity_threshold
        if strategy.similarity_threshold is not None
        else (0.25 if strategy.mode == "multi" else 0.18)
    )
    max_considered = strategy.top_k if strategy.mode == "multi" else max(strategy.top_k, strategy.fallback_k or strategy.top_k)
    considered = scored_regions[:max_considered]
    selected: List[Dict[str, Any]] = []

    if strategy.mode == "single":
        chosen = None
        if strategy.prefer_full_page:
            for entry in considered:
                if entry["embedding"]["metadata"].get("region_id") == "full_page" and entry["similarity"] >= threshold:
                    chosen = entry
                    break
        if not chosen:
            for entry in considered:
                if entry["similarity"] >= threshold:
                    chosen = entry
                    break
        if chosen:
            selected = [chosen]
    else:
        for entry in considered:
            if entry["similarity"] < threshold:
                continue
            selected.append(entry)
            if len(selected) >= strategy.top_k:
                break
        if strategy.include_full_page and not any(
            item["embedding"]["metadata"].get("region_id") == "full_page" for item in selected
        ):
            fp_entry = next(
                (
                    entry
                    for entry in scored_regions
                    if entry["embedding"]["metadata"].get("region_id") == "full_page" and entry["similarity"] >= threshold
                ),
                None,
            )
            if fp_entry:
                selected = [fp_entry] + selected[: max(0, strategy.top_k - 1)]

        deduped: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for entry in selected:
            rid = entry["embedding"]["metadata"].get("region_id")
            if not rid or rid in seen:
                continue
            deduped.append(entry)
            seen.add(rid)
        selected = deduped[: strategy.top_k]

    for entry in selected:
        contexts.append({"kind": "region", "embedding": entry["embedding"], "similarity": entry["similarity"]})

    return contexts, considered, selected


def make_image_part(image_path: Path) -> Optional[Dict[str, Any]]:
    if not image_path.exists():
        return None
    try:
        img_bytes = image_path.read_bytes()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
    except Exception as exc:
        print(f"[Planner] Could not load image {image_path}: {exc}")
        return None
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def answer_with_contexts(
    question: str,
    contexts: List[Dict[str, Any]],
    client: OpenAI,
    answer_model: str,
    strategy: RetrievalStrategy,
) -> str:
    system_lines = [
        "You are an expert architectural assistant.",
        "Always ground responses strictly in the provided combined summary and any extra regions.",
        "If evidence is missing, explicitly state that it was not found.",
    ]
    if strategy.intent == "location":
        system_lines.append("Describe locations with region_ids/quadrants.")
    if strategy.aggregation or requires_aggregation(question):
        system_lines.append("Aggregate counts across all referenced regions before answering.")
    system_prompt = " ".join(system_lines)

    user_content: List[Dict[str, Any]] = [{"type": "text", "text": f"Question: {question}"}]
    for payload in contexts:
        if payload["kind"] == "combined":
            agg_lines = []
            for count_row in payload.get("aggregated_counts", []):
                agg_lines.append(
                    f"- {count_row.get('item')}: total={count_row.get('total')} regions={count_row.get('regions')}"
                )
            combined_block = [
                "Combined context summary (legend + quadrants):",
                payload.get("text", ""),
            ]
            if agg_lines:
                combined_block.append("Aggregated counts:\n" + "\n".join(agg_lines))
            user_content.append({"type": "text", "text": "\n".join(combined_block)})
        else:
            meta = payload["embedding"].get("metadata", {})
            caption = meta.get("caption_text", "")
            text_block = [
                f"Region evidence: {meta.get('region_id')} (sim={payload['similarity']:.3f})",
                f"Project={meta.get('project_id')} sheet={meta.get('sheet_id')} page={meta.get('page_number')}",
                caption,
            ]
            user_content.append({"type": "text", "text": "\n".join(text_block)})
            image_part = make_image_part(Path(meta.get("crop_path", "")))
            if image_part:
                user_content.append(image_part)

    resp = client.chat.completions.create(
        model=answer_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.15,
        max_completion_tokens=600,
    )
    return resp.choices[0].message.content


def serialize_region(entry: Dict[str, Any]) -> Dict[str, Any]:
    meta = entry["embedding"].get("metadata", {})
    return {
        "region_id": meta.get("region_id"),
        "similarity": entry["similarity"],
        "project_id": meta.get("project_id"),
        "sheet_id": meta.get("sheet_id"),
        "page_number": meta.get("page_number"),
        "crop_path": meta.get("crop_path"),
    }


def load_questions(path: Path) -> List[str]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    questions = []
    for line in lines:
        if ")" in line and line[0].isdigit():
            q = line.split(")", 1)[-1].strip()
            if q:
                questions.append(q)
        else:
            questions.append(line)
    return questions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Approach 2: Combined-context region RAG")
    parser.add_argument("--pdf", type=Path, required=True, help="Path to PDF")
    parser.add_argument("--page", type=int, default=0, help="Zero-based page index")
    parser.add_argument("--dpi", type=int, default=300, help="Rasterization DPI")
    parser.add_argument("--questions", type=Path, required=True, help="Questions file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "output",
        help="Base output directory where run folders will be created",
    )
    parser.add_argument("--caption-max-tokens", type=int, default=2500, help="Max caption tokens")
    parser.add_argument("--save-raw", action="store_true", help="Store raw captions and combined context")
    parser.add_argument("--answer-model", type=str, default=ANSWER_MODEL, help="Vision-capable answer model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: Set OPENAI_API_KEY")
        sys.exit(1)
    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}")
        sys.exit(1)
    if not args.questions.exists():
        print(f"ERROR: Questions file not found: {args.questions}")
        sys.exit(1)

    base_output = args.output.resolve()
    base_output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output = base_output / f"{args.pdf.stem}_{timestamp}"
    run_output.mkdir(parents=True, exist_ok=True)
    print(f"[Setup] Output directory: {run_output}")

    questions = load_questions(args.questions)
    print(f"[Setup] Loaded {len(questions)} questions")

    regions = [
        Region("full_page", clamp_bbox([0.0, 0.0, 1.0, 1.0]), "full sheet"),
        Region("q1_top_left", clamp_bbox([0.0, 0.0, 0.5, 0.5]), "top-left quadrant"),
        Region("q2_top_right", clamp_bbox([0.5, 0.0, 1.0, 0.5]), "top-right quadrant"),
        Region("q3_bottom_left", clamp_bbox([0.0, 0.5, 0.5, 1.0]), "bottom-left quadrant"),
        Region("q4_bottom_right", clamp_bbox([0.5, 0.5, 1.0, 1.0]), "bottom-right quadrant"),
    ]

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        page_img = process_pdf_to_image(args.pdf, args.page, args.dpi, tmp)
        captioner = OpenAIRegionCaptioner(openai_key, debug_dir=run_output if args.save_raw else None)
        embedder = EmbeddingGenerator(openai_key)
        combiner = CombinedContextBuilder(openai_key)

        captions: List[Dict[str, Any]] = []
        embeddings: List[Dict[str, Any]] = []

        for region in regions:
            if region.region_id == "full_page":
                crop_path = page_img
            else:
                crop_path = crop_image(page_img, region.bbox, tmp, region.region_id)
            caption = captioner.caption(crop_path, args.pdf.stem, args.page + 1, region, args.caption_max_tokens)
            captions.append({"region_id": region.region_id, "caption": caption or "", "crop_path": str(crop_path)})
            if caption:
                emb_entry = {
                    "embedding": embedder.embed(caption),
                    "metadata": {
                        "project_id": args.pdf.stem,
                        "drawing_id": args.pdf.stem,
                        "sheet_id": f"{args.pdf.stem}_page_{args.page + 1}",
                        "drawing_name": args.pdf.stem,
                        "page_number": args.page + 1,
                        "region_id": region.region_id,
                        "caption_text": caption,
                        "crop_path": str(crop_path),
                    },
                }
                embeddings.append(emb_entry)

        (run_output / "captions.json").write_text(json.dumps(captions, indent=2))
        print(f"[Output] Saved raw captions")

        combined_payload = combiner.build(captions, args.pdf.stem, args.page + 1)
        (run_output / "combined_context.json").write_text(json.dumps(combined_payload, indent=2))
        print("[Combined] Built combined_context summary")

        combined_entry = {
            "embedding": embedder.embed(combined_payload.get("combined_context", "")),
            "metadata": {
                "project_id": args.pdf.stem,
                "drawing_id": args.pdf.stem,
                "sheet_id": f"{args.pdf.stem}_page_{args.page + 1}",
                "drawing_name": args.pdf.stem,
                "page_number": args.page + 1,
                "region_id": "combined_context",
                "combined_context": combined_payload.get("combined_context", ""),
                "aggregated_counts": combined_payload.get("aggregated_counts", []),
                "region_summaries": combined_payload.get("region_summaries", []),
            },
        }

        embeddings_meta = [
            {
                "metadata": emb["metadata"],
            }
            for emb in embeddings
        ]
        (run_output / "embeddings_metadata.json").write_text(json.dumps(embeddings_meta, indent=2))
        (run_output / "embeddings_full.json").write_text(json.dumps(embeddings, indent=2))

        results: List[Dict[str, Any]] = []
        for question in questions:
            strategy = determine_retrieval_strategy(question)
            q_emb = embedder.embed(question)
            scored = [
                {"similarity": cosine_similarity(q_emb, emb["embedding"]), "embedding": emb}
                for emb in embeddings
            ]
            scored.sort(key=lambda item: item["similarity"], reverse=True)
            contexts, considered, selected = plan_contexts(strategy, combined_entry, scored)

            print(f"[Planner] Q: {question}")
            print(f"  Strategy: {strategy.intent} ({strategy.description})")
            print("  Considered regions:")
            for idx, entry in enumerate(considered, start=1):
                meta = entry["embedding"].get("metadata", {})
                marker = "✓" if entry in selected else "-"
                print(
                    f"    {marker} rank={idx} region={meta.get('region_id')} sim={entry['similarity']:.3f}"
                )

            answer = answer_with_contexts(question, contexts, embedder.client, args.answer_model, strategy)
            preview = answer[:180] + ("..." if len(answer) > 180 else "")
            print(f"  [Answer] {preview}")

            results.append(
                {
                    "question": question,
                    "answer": answer,
                    "strategy": strategy.intent,
                    "contexts_used": [
                        {
                            "kind": payload["kind"],
                            "region_id": payload["metadata"].get("region_id") if payload["kind"] == "combined" else payload["embedding"].get("metadata", {}).get("region_id"),
                        }
                        for payload in contexts
                    ],
                    "regions_considered": [serialize_region(entry) for entry in considered],
                }
            )

        (run_output / "rag_results.json").write_text(json.dumps(results, indent=2))
        print(f"[Done] Results saved to {run_output / 'rag_results.json'}")


if __name__ == "__main__":
    main()
