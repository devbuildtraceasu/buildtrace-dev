#!/usr/bin/env python3
"""
Quadrant-based RAG flow:
1) Rasterize a PDF page.
2) Split into 4 quadrants, caption each with OpenAI vision (default gpt-5.1).
3) Embed captions (OpenAI text-embedding-3-small).
4) For each question, pick the most similar region, then call GPT with that region's caption + image to answer.

Outputs are kept in a separate folder (default: Perp_plan/output_quadrants) and do not touch previous run files.
"""

import argparse
import base64
import io
import json
import os
import sys
import tempfile
from datetime import datetime
from dataclasses import dataclass
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
CAPTION_MODEL_DEFAULT = "gpt-5.1"


@dataclass
class Region:
    region_id: str
    bbox: Tuple[float, float, float, float]  # normalized [x0,y0,x1,y1]
    description: str = ""


@dataclass
class RetrievalStrategy:
    intent: str  # e.g., metadata, count, location
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


def requires_aggregation(question: str) -> bool:
    q = question.lower()
    agg_keywords = [
        "how many",
        "number of",
        "count",
        "total",
        "list",
        "all ",
        "list all",
        "show all",
        "give me all",
        "enumerate",
        "catalog",
        "provide all",
    ]
    return any(kw in q for kw in agg_keywords)


def determine_retrieval_strategy(question: str) -> RetrievalStrategy:
    q = question.lower()
    metadata_keywords = [
        "title block",
        "title",
        "sheet",
        "scale",
        "legend",
        "grid",
        "metadata",
        "sheet number",
        "project",
        "revision",
    ]
    location_keywords = [
        "where",
        "location",
        "located",
        "situated",
        "which quadrant",
        "which region",
    ]

    if any(kw in q for kw in metadata_keywords):
        return RetrievalStrategy(
            intent="metadata",
            mode="single",
            top_k=3,
            prefer_full_page=True,
            fallback_k=3,
            description="Prefer full-page/title-block regions for metadata/title questions.",
        )

    if any(kw in q for kw in location_keywords):
        return RetrievalStrategy(
            intent="location",
            mode="multi",
            top_k=3,
            include_full_page=True,
            similarity_threshold=0.3,
            aggregation=True,
            description="Location query; aggregate top-3 regions with similarity threshold.",
        )

    if requires_aggregation(question):
        return RetrievalStrategy(
            intent="count",
            mode="multi",
            top_k=5,
            include_full_page=True,
            aggregation=True,
            description="Count/list query; aggregate up to top-5 regions.",
        )

    return RetrievalStrategy(
        intent="default",
        mode="single",
        top_k=2,
        description="Default retrieval: single-region answer with top-2 consideration.",
    )


def determine_scope_filter(question: str, embeddings: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    if not embeddings:
        return {}
    q = question.lower()
    if "project" in q:
        preference = ["project_id", "drawing_id", "sheet_id"]
    elif "drawing" in q:
        preference = ["drawing_id", "sheet_id", "project_id"]
    else:
        preference = ["sheet_id", "drawing_id", "project_id"]

    for key in preference:
        values = {emb.get("metadata", {}).get(key) for emb in embeddings if emb.get("metadata", {}).get(key)}
        values = {v for v in values if v}
        if len(values) == 1:
            value = values.pop()
            return {"key": key, "value": value}
    return {}


def apply_scope_filter(embeddings: List[Dict[str, Any]], scope_filter: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    key = scope_filter.get("key") if scope_filter else None
    value = scope_filter.get("value") if scope_filter else None
    if not key or value is None:
        return embeddings
    filtered = [emb for emb in embeddings if emb.get("metadata", {}).get(key) == value]
    return filtered or embeddings


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
    print(f"[PDF] Converting page {page_num+1} at {dpi} dpi...")
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
    def __init__(self, api_key: str, model_name: str = CAPTION_MODEL_DEFAULT, debug_dir: Optional[Path] = None, save_raw: bool = False):
        if not OPENAI_AVAILABLE:
            fail_missing_dep("openai", "Install with: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.debug_dir = debug_dir
        self.save_raw = save_raw
        print(f"[OpenAI] Caption model: {model_name}")

    def caption(self, image_path: Path, drawing_name: str, page_num: int, region: Region, max_tokens: int = 800) -> Optional[str]:
        if PIL is None:
            fail_missing_dep("Pillow", "Install with: pip install pillow")
        try:
            with PIL.Image.open(image_path) as img:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                print(f"  [Caption-OAI] Image size: {img.size}, bytes: {len(img_bytes)/1024:.1f} KB")
        except Exception as e:
            print(f"  [Caption-OAI] Failed to load image: {e}")
            return None

        prompt = f"""Provide an exhaustive, retrieval-ready caption for this architectural drawing region.
- List rooms and numbers, doors/windows, annotations, dimensions, legends, title block info, schedules.
- Include any visible text (labels, notes, revisions, sheet number, project/client).
- Be exhaustive; this caption will substitute for the image in retrieval.
Drawing: {drawing_name}, page {page_num}, region: {region.region_id} ({region.description or "no description"})"""

        try:
            kwargs = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "You describe architectural drawings with exhaustive detail for retrieval."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    },
                ],
                "max_completion_tokens": max_tokens,
            }
            if not any(tag in self.model_name for tag in ["gpt-4.1", "gpt-5.1"]):
                kwargs["temperature"] = 0.2

            resp = self.client.chat.completions.create(**kwargs)
            caption_text = resp.choices[0].message.content
            print(f"  [Caption-OAI] ✓ Generated {len(caption_text)} chars for {region.region_id}")
            if self.save_raw and self.debug_dir:
                self.debug_dir.mkdir(parents=True, exist_ok=True)
                (self.debug_dir / f"openai_caption_{region.region_id}.txt").write_text(caption_text)
            return caption_text
        except Exception as e:
            print(f"  [Caption-OAI] ❌ Failed for {region.region_id}: {e}")
            return None


class EmbeddingGenerator:
    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        if not OPENAI_AVAILABLE:
            fail_missing_dep("openai", "Install with: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, text: str) -> List[float]:
        return self.client.embeddings.create(model=self.model, input=text).data[0].embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a * mag_b else 0.0


def make_image_part(image_path: Path) -> Optional[Dict[str, Any]]:
    if not image_path or not image_path.exists():
        return None
    try:
        img_bytes = image_path.read_bytes()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    except Exception as exc:
        print(f"[RAG] Warning: failed to load image {image_path}: {exc}")
        return None


def answer_with_regions(
    question: str,
    regions: List[Dict[str, Any]],
    client: OpenAI,
    answer_model: str,
    strategy: RetrievalStrategy,
    aggregation_hint: bool,
) -> str:
    if not regions:
        return "Not enough evidence to answer the question."

    system_lines = [
        "You are an expert on architectural drawings.",
        "Answer using only the provided regional evidence (captions + images).",
        "If information is missing from every region, reply that evidence is insufficient.",
    ]
    if strategy.mode == "multi":
        system_lines.append("Aggregate findings across all regions that follow.")
    else:
        system_lines.append("Rely solely on the provided region.")
    if aggregation_hint or strategy.aggregation:
        system_lines.append("When quantities are requested, sum or list findings across all regions before answering.")
    if strategy.intent == "location":
        system_lines.append("Map each answer element to the referenced region_id/quadrant when possible.")
    if strategy.intent == "metadata":
        system_lines.append("Focus on sheet-level metadata such as title blocks, legends, revisions, and scale notes.")

    system_prompt = " ".join(system_lines)

    user_content: List[Dict[str, Any]] = [{"type": "text", "text": f"Question: {question}"}]
    if strategy.mode == "multi":
        user_content.append({"type": "text", "text": "Evidence from selected regions:"})

    for idx, payload in enumerate(regions, start=1):
        meta = payload["embedding"].get("metadata", {})
        caption = meta.get("caption_text", "")
        region_id = meta.get("region_id")
        drawing = meta.get("drawing_name")
        page_number = meta.get("page_number")
        region_lines = [
            f"Region {idx}: id={region_id}, similarity={payload['similarity']:.3f}",
            f"Project={meta.get('project_id')} drawing={drawing} sheet={meta.get('sheet_id')} page={page_number}",
            f"Crop path: {meta.get('crop_path')}",
            f"Caption:\n{caption}",
        ]
        user_content.append({"type": "text", "text": "\n".join(region_lines)})
        image_part = make_image_part(Path(meta.get("crop_path", "")))
        if image_part:
            user_content.append(image_part)

    kwargs: Dict[str, Any] = {
        "model": answer_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.15,
    }
    if any(tag in answer_model for tag in ["gpt-4.1", "gpt-5.1"]):
        kwargs["max_completion_tokens"] = 500
    else:
        kwargs["max_tokens"] = 500

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def serialize_region(entry: Dict[str, Any]) -> Dict[str, Any]:
    meta = entry["embedding"].get("metadata", {})
    return {
        "region_id": meta.get("region_id"),
        "similarity": entry["similarity"],
        "project_id": meta.get("project_id"),
        "drawing_name": meta.get("drawing_name"),
        "sheet_id": meta.get("sheet_id"),
        "page_number": meta.get("page_number"),
        "crop_path": meta.get("crop_path"),
        "region_uri": meta.get("region_uri"),
        "caption_excerpt": (meta.get("caption_text", "")[:200] + ("..." if len(meta.get("caption_text", "")) > 200 else "")),
    }


def select_regions(
    scored_regions: List[Dict[str, Any]],
    strategy: RetrievalStrategy,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not scored_regions:
        return [], []

    threshold = strategy.similarity_threshold
    filtered = [entry for entry in scored_regions if threshold is None or entry["similarity"] >= threshold]
    if not filtered:
        return [], []

    considered_count = strategy.top_k
    if strategy.mode == "single":
        considered_count = max(strategy.top_k, strategy.fallback_k or strategy.top_k)

    considered = filtered[:considered_count]
    selected: List[Dict[str, Any]] = []

    if not considered:
        return [], []

    if strategy.mode == "single":
        if strategy.prefer_full_page:
            for entry in considered:
                if entry["embedding"].get("metadata", {}).get("region_id") == "full_page":
                    selected = [entry]
                    break
        if not selected:
            selected = [considered[0]]
    else:
        selected = list(considered[: strategy.top_k])
        if strategy.include_full_page:
            full_candidate = next(
                (entry for entry in filtered if entry["embedding"].get("metadata", {}).get("region_id") == "full_page"),
                None,
            )
            if full_candidate:
                selected = [full_candidate] + [entry for entry in selected if entry is not full_candidate]

        deduped: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for entry in selected:
            rid = entry["embedding"].get("metadata", {}).get("region_id")
            if not rid or rid in seen:
                continue
            deduped.append(entry)
            seen.add(rid)
        selected = deduped[: strategy.top_k]

    return selected, considered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quadrant-based RAG over a drawing page.")
    parser.add_argument("--pdf", type=Path, required=True, help="Path to PDF.")
    parser.add_argument("--page", type=int, default=0, help="Zero-based page index.")
    parser.add_argument("--dpi", type=int, default=300, help="Rasterization DPI (default 300).")
    parser.add_argument("--questions", type=Path, required=True, help="Path to questions file.")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output_quadrants", help="Output folder.")
    parser.add_argument("--caption-model", type=str, default=CAPTION_MODEL_DEFAULT, help="OpenAI vision model (default gpt-5.1).")
    parser.add_argument("--caption-max-tokens", type=int, default=4000, help="Max completion tokens for captions.")
    parser.add_argument("--save-raw", action="store_true", help="Save raw captions.")
    parser.add_argument("--answer-model", type=str, default=ANSWER_MODEL, help="OpenAI model for answering (default gpt-5.1; must support vision to use image).")
    return parser.parse_args()


def load_questions(path: Path) -> List[str]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    qs = []
    for line in lines:
        if ")" in line and line[0].isdigit():
            q = line.split(")", 1)[-1].strip()
            if q:
                qs.append(q)
        elif "?" in line or len(line) > 5:
            qs.append(line)
    return qs


def main() -> None:
    args = parse_args()
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
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
    print(f"[Setup] Questions loaded: {len(questions)}")

    project_id = args.pdf.stem
    drawing_id = args.pdf.stem
    sheet_id = f"{args.pdf.stem}_page_{args.page + 1}"

    quadrants = [
        Region("q1_top_left", clamp_bbox([0.0, 0.0, 0.5, 0.5]), "top-left quadrant"),
        Region("q2_top_right", clamp_bbox([0.5, 0.0, 1.0, 0.5]), "top-right quadrant"),
        Region("q3_bottom_left", clamp_bbox([0.0, 0.5, 0.5, 1.0]), "bottom-left quadrant"),
        Region("q4_bottom_right", clamp_bbox([0.5, 0.5, 1.0, 1.0]), "bottom-right quadrant"),
    ]
    full_region = Region("full_page", clamp_bbox([0.0, 0.0, 1.0, 1.0]), "full page")

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        page_img = process_pdf_to_image(args.pdf, args.page, args.dpi, tmp)

        captioner = OpenAIRegionCaptioner(openai_key, model_name=args.caption_model, debug_dir=run_output, save_raw=args.save_raw)
        embedder = EmbeddingGenerator(openai_key)
        all_embeddings: List[Dict[str, Any]] = []
        captions: List[Dict[str, Any]] = []

        # Caption full page at full scale
        full_caption = captioner.caption(page_img, args.pdf.stem, args.page + 1, full_region, max_tokens=args.caption_max_tokens)
        captions.append({"region_id": full_region.region_id, "caption": full_caption or ""})
        if full_caption:
            all_embeddings.append({
                "object_type": "caption",
                "description": f"Caption for {full_region.region_id}",
                "embedding": embedder.embed(full_caption),
                "metadata": {
                    "project_id": project_id,
                    "drawing_id": drawing_id,
                    "drawing_name": args.pdf.stem,
                    "sheet_id": sheet_id,
                    "page_number": args.page + 1,
                    "region_id": full_region.region_id,
                    "caption_text": full_caption,
                    "crop_path": str(page_img),
                    "region_uri": str(page_img),
                },
            })

        for region in quadrants:
            crop_path = crop_image(page_img, region.bbox, tmp, region.region_id)
            caption = captioner.caption(crop_path, args.pdf.stem, args.page + 1, region, max_tokens=args.caption_max_tokens)
            captions.append({"region_id": region.region_id, "caption": caption or ""})
            if caption:
                cap_emb = {
                    "object_type": "caption",
                    "description": f"Caption for {region.region_id}",
                    "embedding": embedder.embed(caption),
                    "metadata": {
                        "project_id": project_id,
                        "drawing_id": drawing_id,
                        "drawing_name": args.pdf.stem,
                        "sheet_id": sheet_id,
                        "page_number": args.page + 1,
                        "region_id": region.region_id,
                        "caption_text": caption,
                        "crop_path": str(crop_path),
                        "region_uri": str(crop_path),
                    },
                }
                all_embeddings.append(cap_emb)

        # Save captions and embeddings
        (run_output / "captions.json").write_text(json.dumps(captions, indent=2))
        embeddings_meta = [
            {
                "object_type": e["object_type"],
                "description": e["description"],
                "metadata": e["metadata"],
            }
            for e in all_embeddings
        ]
        (run_output / "embeddings_metadata.json").write_text(json.dumps(embeddings_meta, indent=2))
        (run_output / "embeddings_full.json").write_text(json.dumps(all_embeddings, indent=2))
        print(f"[Output] Saved captions and embeddings to {run_output}")

        # Retrieval + answer
        client = embedder.client
        results = []
        for q in questions:
            strategy = determine_retrieval_strategy(q)
            scope_filter = determine_scope_filter(q, all_embeddings)
            scoped_embeddings = apply_scope_filter(all_embeddings, scope_filter)
            q_emb = client.embeddings.create(model=EMBEDDING_MODEL, input=q).data[0].embedding

            scored: List[Dict[str, Any]] = []
            for emb in scoped_embeddings:
                sim = cosine_similarity(q_emb, emb["embedding"])
                scored.append({"similarity": float(sim), "embedding": emb})
            scored.sort(key=lambda item: item["similarity"], reverse=True)

            print(f"[Retrieval] Q: {q}")
            print(f"  Strategy: {strategy.intent} ({strategy.description})")
            print(f"  Scope filter: {scope_filter or 'none'} | candidates: {len(scoped_embeddings)}")

            selected, considered = select_regions(scored, strategy)
            for idx, entry in enumerate(considered, start=1):
                meta = entry["embedding"].get("metadata", {})
                marker = "✓" if entry in selected else "-"
                print(
                    f"    {marker} rank={idx} region={meta.get('region_id')} sim={entry['similarity']:.3f} page={meta.get('page_number')}"
                )
            extra_selected = [entry for entry in selected if entry not in considered]
            for entry in extra_selected:
                meta = entry["embedding"].get("metadata", {})
                print(
                    f"    ✓ rank=manual region={meta.get('region_id')} sim={entry['similarity']:.3f} page={meta.get('page_number')}"
                )

            if not selected:
                print("  [Retrieval] No regions passed similarity threshold; responding with not-enough-evidence.")
                results.append(
                    {
                        "question": q,
                        "answer": "Not enough evidence to answer based on the retrieved regions.",
                        "strategy": strategy.intent,
                        "mode": strategy.mode,
                        "scope_filter": scope_filter,
                        "regions_used": [],
                        "regions_considered": [serialize_region(entry) for entry in considered],
                    }
                )
                continue

            needs_agg = strategy.aggregation or requires_aggregation(q)
            answer_text = answer_with_regions(q, selected, client, args.answer_model, strategy, needs_agg)
            provenance_used = [serialize_region(entry) for entry in selected]
            provenance_considered = [serialize_region(entry) for entry in considered]
            preview = answer_text[:200] + ("..." if len(answer_text) > 200 else "")
            print(f"  [Answer] {preview}")

            results.append(
                {
                    "question": q,
                    "answer": answer_text,
                    "strategy": strategy.intent,
                    "mode": strategy.mode,
                    "needs_aggregation": needs_agg,
                    "scope_filter": scope_filter,
                    "regions_used": provenance_used,
                    "regions_considered": provenance_considered,
                }
            )

        (run_output / "rag_results.json").write_text(json.dumps(results, indent=2))
        print(f"[Output] Saved RAG results to {run_output / 'rag_results.json'}")
        print("[Done] Quadrant RAG complete.")


if __name__ == "__main__":
    main()
