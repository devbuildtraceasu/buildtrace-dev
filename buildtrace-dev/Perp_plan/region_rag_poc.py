#!/usr/bin/env python3
"""
Region-based RAG proof-of-concept for architectural drawings.

Flow:
1) Convert a PDF page to an image.
2) Crop one or more regions (normalized bounding boxes).
3) Ask Gemini to extract semantic objects from each region.
4) Generate embeddings for those objects.
5) Run lightweight RAG queries over the regional semantics.

Default inputs:
- PDF: testing/Temple/TempleTest_Add1.pdf (old drawing)
- Questions: vecTOR_EMBEDDING/Q_set_immediate.txt

Environment:
- GOOGLE_API_KEY or GEMINI_API_KEY for Gemini.
- OPENAI_API_KEY for embeddings + RAG responses.
"""

import argparse
import base64
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Optional deps are imported lazily so the script can show clear guidance.
try:
    from pdf2image import convert_from_path  # type: ignore
    import PIL.Image  # type: ignore
    PIL.Image.MAX_IMAGE_PIXELS = 200_000_000
except ImportError:
    convert_from_path = None  # type: ignore
    PIL = None  # type: ignore

try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# Defaults point to the Temple old drawing and immediate question set.
DEFAULT_PDF = Path("/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/Temple/TempleTest_Add1.pdf")
DEFAULT_QUESTIONS = Path("/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/vecTOR_EMBEDDING/Q_set_immediate.txt")

# Region bounding boxes are normalized floats [x_min, y_min, x_max, y_max].
DEFAULT_REGIONS = [
    {
        "id": "full_page",
        "bbox": [0.0, 0.0, 1.0, 1.0],
        "description": "Entire sheet region; safest default when unsure.",
    },
    # Add additional regions if known, e.g. title block or lobby area.
    # {"id": "title_block", "bbox": [0.70, 0.70, 0.98, 0.98], "description": "Rev/title area"},
]

EMBEDDING_MODEL = "text-embedding-3-small"
RAG_MODEL = "gpt-4o-mini"


@dataclass
class Region:
    region_id: str
    bbox: Tuple[float, float, float, float]
    description: str = ""


def fail_missing_dep(name: str, fix: str) -> None:
    print(f"ERROR: Missing dependency '{name}'. {fix}")
    sys.exit(1)


def safe_parse_json(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Best-effort JSON extraction:
    - Prefer fenced ```json blocks
    - Otherwise grab the largest {...} span
    Returns (data, error_message)
    """
    text = raw_text.strip()
    # Strip code fences if present
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

    # First attempt
    try:
        return json.loads(text), None
    except Exception as e1:
        # Try largest brace span
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate), None
            except Exception as e2:
                return None, f"{e1} | brace-scan: {e2}"
        return None, str(e1)


def clamp_bbox(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    """Clamp normalized bbox values to [0,1] and ensure ordering."""
    if len(bbox) != 4:
        raise ValueError("bbox must have four floats [x_min, y_min, x_max, y_max]")
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0.0, x0), max(0.0, y0)
    x1, y1 = min(1.0, x1), min(1.0, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"Invalid bbox after clamping: {bbox}")
    return x0, y0, x1, y1


def load_regions(path: Optional[Path]) -> List[Region]:
    if not path:
        return [Region(r["id"], clamp_bbox(r["bbox"]), r.get("description", "")) for r in DEFAULT_REGIONS]
    data = json.loads(path.read_text())
    regions = []
    for r in data:
        regions.append(Region(r["id"], clamp_bbox(r["bbox"]), r.get("description", "")))
    return regions


def load_questions(path: Path) -> List[str]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    questions: List[str] = []
    for line in lines:
        if ")" in line and line[0].isdigit():
            question = line.split(")", 1)[-1].strip()
            if question:
                questions.append(question)
        elif "?" in line or len(line) > 10:
            questions.append(line)
    return questions


def convert_pdf_page_to_image(pdf_path: Path, page_num: int, dpi: int, output_dir: Path) -> Path:
    if convert_from_path is None:
        fail_missing_dep("pdf2image", "Install with: pip install pdf2image pillow")
    print(f"[PDF] Converting {pdf_path} page {page_num + 1} to image @ {dpi} dpi...")
    images = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_num + 1, last_page=page_num + 1)
    if not images:
        raise RuntimeError("No pages returned from pdf2image")
    output_path = output_dir / f"page_{page_num + 1}.png"
    images[0].save(output_path, "PNG")
    print(f"[PDF] Saved image: {output_path}")
    return output_path


def crop_image(image_path: Path, bbox: Tuple[float, float, float, float], output_dir: Path, suffix: str) -> Path:
    if PIL is None:
        fail_missing_dep("Pillow", "Install with: pip install pillow")
    with PIL.Image.open(image_path) as img:
        width, height = img.size
        x0, y0, x1, y1 = bbox
        crop_box = (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
        region_img = img.crop(crop_box)
        output_path = output_dir / f"{image_path.stem}_{suffix}.png"
        region_img.save(output_path, "PNG")
        print(f"[CROP] {suffix}: saved {region_img.size} px to {output_path}")
        return output_path


class GeminiRegionExtractor:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", caption_model_name: str = "gemini-3-pro-image-preview", debug_dir: Optional[Path] = None, save_raw: bool = False):
        if not GEMINI_AVAILABLE:
            fail_missing_dep("google-generativeai", "Install with: pip install google-generativeai")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.caption_model = genai.GenerativeModel(caption_model_name)
        self.debug_dir = debug_dir
        self.save_raw = save_raw
        print(f"[Gemini] Using model: {model_name} (caption model: {caption_model_name})")

    def extract(self, image_path: Path, drawing_name: str, page_num: int, region: Region) -> Dict[str, Any]:
        prompt = f"""You are analyzing architectural drawings. Focus ONLY on the provided region.

Drawing: {drawing_name}, page {page_num}
Region: {region.region_id} ({region.description or "no description"})
Region bbox: normalized {region.bbox} (x_min, y_min, x_max, y_max).

Extract semantic objects in JSON with this exact schema:
{{
  "region_id": "<region_id>",
  "spaces": [...],
  "elements": [...],
  "annotations": [...]
}}

Rules:
- Only report objects visible inside the region bbox.
- Include bounding boxes as normalized coords [x_min, y_min, x_max, y_max].
- Be exhaustive but stay concise. If nothing is present, return empty lists.
"""
        try:
            response = self.model.generate_content(
                [prompt, {"mime_type": "image/png", "data": image_path.read_bytes()}],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                ),
            )
            raw_text = response.text.strip() if hasattr(response, "text") else str(response)
            if self.save_raw and self.debug_dir:
                self.debug_dir.mkdir(parents=True, exist_ok=True)
                (self.debug_dir / f"gemini_raw_{region.region_id}.txt").write_text(raw_text)

            parsed, err = safe_parse_json(raw_text)
            if parsed is None:
                print(f"[Gemini] Failed to parse JSON for region {region.region_id}: {err}")
                if self.save_raw and self.debug_dir:
                    (self.debug_dir / f"gemini_raw_{region.region_id}_parse_error.txt").write_text(raw_text)
                return {"region_id": region.region_id, "spaces": [], "elements": [], "annotations": []}

            parsed["region_id"] = region.region_id

            # If everything is empty, optionally keep the raw for inspection.
            if (
                not parsed.get("spaces")
                and not parsed.get("elements")
                and not parsed.get("annotations")
                and self.debug_dir
            ):
                (self.debug_dir / f"gemini_raw_{region.region_id}_empty.txt").write_text(raw_text)

            return parsed
        except Exception as e:  # Broad catch to keep the PoC resilient.
            print(f"[Gemini] Failed on region {region.region_id}: {e}")
            return {"region_id": region.region_id, "spaces": [], "elements": [], "annotations": []}


class OpenAIRegionCaptioner:
    """Generate captions using OpenAI vision models (e.g., gpt-4.1 / gpt-5.1)."""

    def __init__(self, api_key: str, model_name: str = "gpt-5.1", debug_dir: Optional[Path] = None, save_raw: bool = False):
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
                import io
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                print(f"  [Caption-OAI] Image bytes (no resize): {len(img_bytes)/1024:.1f} KB; size: {img.size}")
        except Exception as e:
            print(f"  [Caption-OAI] Failed to load image: {e}")
            return None

        prompt = f"""Provide a detailed, retrieval-friendly caption for this architectural drawing region.
- Mention room names/numbers, doors, windows, annotations, dimensions, legends, title block info, schedules.
- Include any visible text (labels, notes, revisions, sheet number, project/client).
- Be exhaustive; this caption will substitute for the image in retrieval.
Drawing: {drawing_name}, page {page_num}, region: {region.region_id} ({region.description or "no description"})"""

        try:
            print(f"  [Caption-OAI] Calling {self.model_name} for {region.region_id}...")
            # GPT-4.1/5.1 models use max_completion_tokens instead of max_tokens; omit temperature for them.
            kwargs = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at describing architectural drawings with exhaustive detail for retrieval.",
                    },
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
            import traceback
            traceback.print_exc()
            return None



class EmbeddingGenerator:
    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        if not OPENAI_AVAILABLE:
            fail_missing_dep("openai", "Install with: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        print(f"[OpenAI] Embedding model: {model}")

    def embed(self, text: str) -> List[float]:
        resp = self.client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding


def build_embeddings(semantic: Dict[str, Any], drawing_name: str, page_num: int, region: Region, embedder: EmbeddingGenerator) -> List[Dict[str, Any]]:
    embeddings: List[Dict[str, Any]] = []

    def push(obj_type: str, description: str, obj: Dict[str, Any], extra_meta: Dict[str, Any]) -> None:
        try:
            vector = embedder.embed(description)
        except Exception as e:
            print(f"[Embed] Failed for {obj_type} in {region.region_id}: {e}")
            return
        embeddings.append(
            {
                "object_type": obj_type,
                "description": description,
                "embedding": vector,
                "metadata": {
                    "drawing_name": drawing_name,
                    "page_number": page_num,
                    "region_id": region.region_id,
                    **extra_meta,
                },
                "object_data": obj,
            }
        )

    for idx, space in enumerate(semantic.get("spaces", [])):
        desc = f"Space {space.get('name','?')} {space.get('number','?')} in region {region.region_id}"
        push(
            "space",
            desc,
            space,
            {"space_idx": idx, "space_name": space.get("name"), "space_number": space.get("number")},
        )

    for idx, element in enumerate(semantic.get("elements", [])):
        desc = f"Element {element.get('type','?')} {element.get('label','')} in region {region.region_id}"
        push(
            "element",
            desc,
            element,
            {"element_idx": idx, "element_label": element.get("label"), "element_type": element.get("type")},
        )

    for idx, ann in enumerate(semantic.get("annotations", [])):
        desc = f"Annotation {ann.get('role','?')} '{ann.get('text','')}' in region {region.region_id}"
        push(
            "annotation",
            desc,
            ann,
            {"annotation_idx": idx, "annotation_role": ann.get("role")},
        )

    print(f"[Embed] Region {region.region_id}: {len(embeddings)} vectors")
    return embeddings


def build_caption_embedding(caption: str, drawing_name: str, page_num: int, region: Region, embedder: EmbeddingGenerator) -> Optional[Dict[str, Any]]:
    """Create a single embedding representing the image caption (image substitute)."""
    if not caption or not caption.strip():
        print(f"  [Embed] Empty caption for {region.region_id}, skipping")
        return None
    try:
        print(f"  [Embed] Generating embedding for caption ({len(caption)} chars)...")
        vector = embedder.embed(caption)
        if not vector or len(vector) == 0:
            print(f"  [Embed] Empty vector returned for {region.region_id}")
            return None
        print(f"  [Embed] ✓ Generated {len(vector)}-dim vector")
        return {
            "object_type": "caption",
            "description": f"Caption for region {region.region_id}",
            "embedding": vector,
            "metadata": {
                "drawing_name": drawing_name,
                "page_number": page_num,
                "region_id": region.region_id,
                "caption_text": caption,
            },
            "object_data": {"caption": caption},
        }
    except Exception as e:
        print(f"  [Embed] ❌ Failed for caption in {region.region_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a * mag_b else 0.0


def rag_query(question: str, embeddings: List[Dict[str, Any]], client: OpenAI, region_filter: Optional[str], top_k: int = 5) -> Dict[str, Any]:
    q_emb = client.embeddings.create(model=EMBEDDING_MODEL, input=question).data[0].embedding
    candidates = []
    for emb in embeddings:
        if region_filter and emb["metadata"].get("region_id") != region_filter:
            continue
        sim = cosine_similarity(q_emb, emb["embedding"])
        candidates.append((sim, emb))
    candidates.sort(reverse=True, key=lambda x: x[0])
    top = candidates[:top_k]

    context = []
    for sim, emb in top:
        rid = emb["metadata"].get("region_id")
        obj_type = emb["object_type"]
        context.append(f"[{rid}] {obj_type}: {emb['description']}")
        if obj_type == "caption":
            caption_text = emb["metadata"].get("caption_text") or emb["description"]
            context.append(f"  Caption (image substitute): {caption_text}")
        elif obj_type == "space":
            obj_data = emb.get("object_data", {})
            context.append(
                f"  - Name: {obj_data.get('name', 'N/A')}, Number: {obj_data.get('number', 'N/A')}, Level: {obj_data.get('level', 'N/A')}"
            )
        elif obj_type == "element":
            obj_data = emb.get("object_data", {})
            context.append(f"  - Type: {obj_data.get('type', 'N/A')}, Label: {obj_data.get('label', 'N/A')}")
        elif obj_type == "annotation":
            obj_data = emb.get("object_data", {})
            context.append(f"  - Role: {obj_data.get('role', 'N/A')}, Text: {obj_data.get('text', 'N/A')}")
        context.append(f"  Meta: {emb['metadata']}")

    system_prompt = "You are an assistant for architectural drawings. Answer using only the provided regional context."
    user_prompt = f"Context:\n" + "\n".join(context) + f"\n\nQuestion: {question}\nAnswer concisely. If unknown, say so."

    completion = client.chat.completions.create(
        model=RAG_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.1,
        max_tokens=400,
    )
    answer = completion.choices[0].message.content
    return {
        "question": question,
        "answer": answer,
        "region_filter": region_filter,
        "top_contexts": [
            {
                "similarity": float(sim),
                "object_type": emb["object_type"],
                "region_id": emb["metadata"].get("region_id"),
                "description": emb["description"],
                "metadata": emb["metadata"],
            }
            for sim, emb in top
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Region-based RAG PoC for drawings.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Path to input PDF (default: Temple old drawing).")
    parser.add_argument("--page", type=int, default=0, help="Zero-based page index to process.")
    parser.add_argument("--dpi", type=int, default=300, help="Rasterization DPI for pdf2image (default: 300 for higher detail).")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS, help="Path to questions file.")
    parser.add_argument("--regions", type=Path, help="Path to JSON list of regions with bbox.")
    parser.add_argument("--region-filter", type=str, help="Limit RAG answers to a specific region id.")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output", help="Folder for outputs.")
    parser.add_argument("--save-raw", action="store_true", help="Save raw Gemini responses per region for debugging.")
    parser.add_argument("--fail-on-empty", action="store_true", help="Exit non-zero if no embeddings were produced.")
    parser.add_argument("--caption-embeddings", dest="caption_embeddings", action="store_true", help="Generate caption embeddings per region (default: on).")
    parser.add_argument("--no-caption-embeddings", dest="caption_embeddings", action="store_false", help="Disable caption embeddings.")
    parser.add_argument("--caption-max-tokens", type=int, default=4096, help="Max tokens for caption generation (default: 4096, use 2000-4000 for faster results).")
    parser.add_argument("--caption-model", type=str, default="gemini-3-pro-image-preview", help="Gemini model for caption generation (default: gemini-3-pro-image-preview, better for images than gemini-3-pro-preview).")
    parser.add_argument("--caption-provider", type=str, choices=["gemini", "openai"], default="openai", help="Provider for captioning: gemini or openai (default: openai).")
    parser.add_argument("--openai-caption-model", type=str, default="gpt-5.1", help="OpenAI vision model for captions (default: gpt-5.1; temperature is ignored and max_completion_tokens is used for 4.1/5.1).")
    parser.set_defaults(caption_embeddings=True)
    return parser.parse_args()


def resolve_path(path: Path, workspace_root: Optional[Path] = None) -> Path:
    """Resolve a path: if relative and not found, try relative to workspace root."""
    if path.is_absolute() and path.exists():
        return path
    if path.exists():
        return path.resolve()
    # Try relative to workspace root (parent of script directory)
    if workspace_root:
        candidate = workspace_root / path
        if candidate.exists():
            return candidate.resolve()
    return path  # Return as-is if still not found (will error later)


def main() -> None:
    args = parse_args()
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not gemini_key:
        print("ERROR: Set GOOGLE_API_KEY or GEMINI_API_KEY")
        sys.exit(1)
    if not openai_key:
        print("ERROR: Set OPENAI_API_KEY")
        sys.exit(1)

    # Resolve paths relative to workspace root if needed
    workspace_root = Path(__file__).parent.parent  # Job_trial directory
    args.pdf = resolve_path(args.pdf, workspace_root)
    args.questions = resolve_path(args.questions, workspace_root)

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}")
        print(f"  Tried: {args.pdf}")
        if not args.pdf.is_absolute():
            print(f"  Also tried: {workspace_root / args.pdf}")
        sys.exit(1)
    if not args.questions.exists():
        print(f"ERROR: Questions file not found: {args.questions}")
        sys.exit(1)

    regions = load_regions(args.regions)
    questions = load_questions(args.questions)
    print(f"[Setup] Regions: {[r.region_id for r in regions]}")
    print(f"[Setup] Questions: {len(questions)} loaded")

    # Resolve output path to absolute (handle relative paths correctly)
    if not args.output.is_absolute():
        # If it starts with "Perp_plan/", resolve from workspace root
        # Otherwise, resolve from current working directory
        output_str = str(args.output)
        if output_str.startswith("Perp_plan/"):
            args.output = workspace_root / args.output
        else:
            # Resolve relative to current working directory
            args.output = (Path.cwd() / args.output).resolve()
    else:
        args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"[Setup] Output directory: {args.output}")

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        page_image = convert_pdf_page_to_image(args.pdf, args.page, args.dpi, tmp_dir)

        # Caption provider selection
        caption_provider = args.caption_provider
        if caption_provider == "gemini":
            captioner = GeminiRegionExtractor(
                gemini_key,
                model_name="gemini-2.5-flash",
                caption_model_name=args.caption_model,
                debug_dir=args.output,
                save_raw=args.save_raw,
            )
        else:
            if not openai_key:
                print("ERROR: OPENAI_API_KEY required for openai caption provider")
                sys.exit(1)
            captioner = OpenAIRegionCaptioner(openai_key, model_name=args.openai_caption_model)

        embedder = EmbeddingGenerator(openai_key)
        openai_client = embedder.client

        all_embeddings: List[Dict[str, Any]] = []
        captions: List[Dict[str, Any]] = []

        print(f"\n[Processing] Starting caption generation for {len(regions)} region(s)...")
        print(f"[Debug] caption_embeddings flag: {args.caption_embeddings}")
        for region in regions:
            print(f"\n[Region] Processing {region.region_id}...")
            region_img = crop_image(page_image, region.bbox, tmp_dir, region.region_id)
            print(f"  [Debug] Region image exists: {region_img.exists()}, size: {region_img.stat().st_size / 1024:.1f} KB")
            
            if not args.caption_embeddings:
                print(f"  [Skip] Caption embeddings disabled")
                captions.append({"region_id": region.region_id, "caption": ""})
                continue
                
            print(f"  [Debug] Calling extractor.caption()...")
            caption = captioner.caption(region_img, args.pdf.stem, args.page + 1, region, max_tokens=args.caption_max_tokens)
            print(f"  [Debug] Caption result: {repr(caption) if caption else 'None/Empty'}")
            if caption:
                print(f"  [Debug] Caption length: {len(caption)} chars, preview: {caption[:100]}...")
            captions.append({"region_id": region.region_id, "caption": caption or ""})
            
            if caption and caption.strip():
                print(f"  [Embed] Creating embedding for caption ({len(caption)} chars)...")
                cap_emb = build_caption_embedding(caption, args.pdf.stem, args.page + 1, region, embedder)
                if cap_emb:
                    all_embeddings.append(cap_emb)
                    print(f"  [Embed] ✓ Added embedding for {region.region_id}")
                else:
                    print(f"  [Embed] ❌ Failed to create embedding for {region.region_id}")
            else:
                print(f"  [Caption] ❌ No caption generated for {region.region_id} (got: {repr(caption)})")
        
        print(f"\n[Summary] Generated {len(captions)} captions, {len(all_embeddings)} embeddings")

        print(f"\n[Output] Writing results to {args.output}...")
        
        # Save captions
        captions_path = args.output / "captions.json"
        captions_path.write_text(json.dumps(captions, indent=2))
        print(f"  ✓ Saved {len(captions)} captions to {captions_path}")
        
        # Save embeddings metadata (without vectors)
        embeddings_meta = [
            {
                "object_type": e["object_type"],
                "description": e["description"],
                "metadata": e["metadata"],
            }
            for e in all_embeddings
        ]
        embeddings_path = args.output / "embeddings_metadata.json"
        embeddings_path.write_text(json.dumps(embeddings_meta, indent=2))
        print(f"  ✓ Saved {len(embeddings_meta)} embeddings metadata to {embeddings_path}")
        
        # Save FULL embeddings for local retrieval (persistent storage)
        embeddings_full_path = args.output / "embeddings_full.json"
        embeddings_full = [
            {
                "object_type": e["object_type"],
                "description": e["description"],
                "embedding": e["embedding"],  # Full vector
                "metadata": e["metadata"],
                "object_data": e.get("object_data", {}),
            }
            for e in all_embeddings
        ]
        embeddings_full_path.write_text(json.dumps(embeddings_full, indent=2))
        print(f"  ✓ Saved {len(embeddings_full)} FULL embeddings (with vectors) to {embeddings_full_path}")
        print(f"  📦 Embedding database ready for retrieval!")

        if not all_embeddings:
            msg = "\n[Warn] ⚠️  No embeddings generated!"
            print(msg)
            print("  Possible causes:")
            print("  - Gemini caption generation failed (check --save-raw output)")
            print("  - Image too large (try --dpi 200)")
            print("  - API errors (check API keys)")
            if args.fail_on_empty:
                sys.exit(2)
            # Still run RAG with empty embeddings to show the issue
            results = [{"question": q, "answer": "No embeddings available to answer this question.", "error": "no_embeddings"} for q in questions]
        else:
            # RAG queries
            print(f"\n[RAG] Running {len(questions)} queries with {len(all_embeddings)} embeddings...")
            results = []
            for q in questions:
                print(f"  [RAG] Query: {q}")
                result = rag_query(q, all_embeddings, openai_client, args.region_filter)
                results.append(result)
                print(f"    Answer: {result['answer'][:100]}...")

        rag_path = args.output / "rag_results.json"
        rag_path.write_text(json.dumps(results, indent=2))
        print(f"\n  ✓ Saved {len(results)} RAG results to {rag_path}")
        print("\n[Done] Region-based RAG PoC complete.")


if __name__ == "__main__":
    main()
