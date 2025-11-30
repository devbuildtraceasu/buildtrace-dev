import io
import math
import os
import re
from typing import Dict, List, Optional, Set, Tuple

import fitz
import random
try:
    import numpy as np
except Exception:
    np = None

# Minimal configuration: set the two input PDFs and an output path
PDF_A = "pdfs/Q-103/Q-103_old.pdf"
PDF_B = "pdfs/Q-103/Q-103_new.pdf"  # set this to your second drawing
OUTPUT_OVERLAY_PDF = PDF_B.replace("_new.pdf", "_overlay.pdf")


# -------------------- PDF Layer Introspection Helpers --------------------

# Safe xref helpers (avoid RuntimeError: code=7)
def _safe_xref_object(doc: fitz.Document, xref: int) -> Optional[str]:
    try:
        if hasattr(doc, "xref_is_free") and doc.xref_is_free(xref):
            return None
    except Exception:
        pass
    try:
        s = doc.xref_object(xref)
        return s if s else None
    except RuntimeError as e:
        if "code=7" in str(e):
            return None
        raise


def _safe_xref_stream(doc: fitz.Document, xref: int) -> Optional[bytes]:
    try:
        if hasattr(doc, "xref_is_free") and doc.xref_is_free(xref):
            return None
    except Exception:
        pass
    try:
        return doc.xref_stream(xref)
    except RuntimeError as e:
        if "code=7" in str(e):
            return None
        raise

def _get_page_content_xrefs(doc: fitz.Document, page: fitz.Page) -> List[int]:
    page_obj = _safe_xref_object(doc, page.xref) or ""
    refs = re.findall(r"/Contents\s*\[(.*?)\]", page_obj, re.S)
    if refs:
        contents = re.findall(r"(\d+)\s+0\s+R", refs[0])
    else:
        contents = re.findall(r"/Contents\s+(\d+)\s+0\s+R", page_obj)
    return [int(x) for x in contents]


def _collect_used_tokens(doc: fitz.Document) -> Set[str]:
    tokens: Set[str] = set()
    pat = re.compile(rb"/OC\s*/([^\s]+)\s+BDC", re.IGNORECASE)
    for page in doc:
        for cr in _get_page_content_xrefs(doc, page):
            bs = _safe_xref_stream(doc, cr) or b""
            tokens.update(t.decode("latin-1","ignore").lower()
                          for t in pat.findall(bs))
    return tokens



def _build_token_and_name_maps(doc: fitz.Document) -> Tuple[Dict[str,int], Dict[int,str]]:
    tok2xref: Dict[str,int] = {}
    props_pat = re.compile(r"/Properties\s+(\d+)\s+0\s+R", re.IGNORECASE)
    kv_pat    = re.compile(r"/([oO][cC]\d+)\s+(\d+)\s+0\s+R")
    inline_pat= re.compile(r"/Properties\s*<<(.*?)>>", re.S | re.IGNORECASE)
    name_paren= re.compile(r"/Name\s*\((.*?)\)")
    name_sym  = re.compile(r"/Name\s*/([^\s/>]+)")

    # Don't swallow failures broadly; most xrefs are fine.
    for xref in range(1, doc.xref_length()):
        s = _safe_xref_object(doc, xref) or ""
        for px in props_pat.findall(s):
            pobj = _safe_xref_object(doc, int(px)) or ""
            for t, rx in kv_pat.findall(pobj):
                tok2xref[t.lower()] = int(rx)
        inline = inline_pat.search(s)
        if inline:
            for t, rx in kv_pat.findall(inline.group(1)):
                tok2xref[t.lower()] = int(rx)

    xref2name: Dict[int,str] = {}
    for xref in range(1, doc.xref_length()):
        s = _safe_xref_object(doc, xref) or ""
        if re.search(r"/Type\s*/OCG", s, re.IGNORECASE):
            m = name_paren.search(s) or name_sym.search(s)
            if m:
                xref2name[xref] = m.group(1)
    return tok2xref, xref2name


# Page-scoped layer introspection
def _collect_used_tokens_for_page(doc: fitz.Document, page: fitz.Page) -> Set[str]:
    tokens: Set[str] = set()
    page_obj = _safe_xref_object(doc, page.xref) or ""
    refs = re.findall(r"/Contents\s*\[(.*?)\]", page_obj, re.S)
    if refs:
        contents = [int(x) for x in re.findall(r"(\d+)\s+0\s+R", refs[0])]
    else:
        contents = [int(x) for x in re.findall(r"/Contents\s+(\d+)\s+0\s+R", page_obj)]
    for cr in contents:
        bs = _safe_xref_stream(doc, cr)
        if not bs:
            continue
        for t in re.findall(rb"/OC\s*/([^\s]+)\s+BDC", bs):
            tokens.add(t.decode("latin-1", "ignore").lower())
    return tokens


def _build_token_and_name_maps_for_page(doc: fitz.Document, page_index: int) -> Tuple[Dict[str,int], Dict[int,str]]:
    page = doc[page_index]
    page_obj = _safe_xref_object(doc, page.xref) or ""

    res_inline = re.search(r"/Resources\s*<<(.*?)>>", page_obj, re.S)
    res_ref = re.search(r"/Resources\s+(\d+)\s+0\s+R", page_obj)
    resources = ""
    if res_inline:
        resources = res_inline.group(1)
    elif res_ref:
        rx = int(res_ref.group(1))
        resources = _safe_xref_object(doc, rx) or ""

    props_inline = re.search(r"/Properties\s*<<(.*?)>>", resources, re.S)
    props_ref = re.search(r"/Properties\s+(\d+)\s+0\s+R", resources)
    props = ""
    if props_inline:
        props = props_inline.group(1)
    elif props_ref:
        px = int(props_ref.group(1))
        props = _safe_xref_object(doc, px) or ""

    tok2xref: Dict[str,int] = {}
    for t, rx in re.findall(r"/(oc[0-9A-Za-z_]+)\s+(\d+)\s+0\s+R", props):
        tok2xref[t.lower()] = int(rx)

    xref2name: Dict[int,str] = {}
    for ox in set(tok2xref.values()):
        oc = _safe_xref_object(doc, ox) or ""
        if "/Type /OCG" in oc:
            m = re.search(r"/Name\s*\((.*?)\)", oc, re.S) or re.search(r"/Name\s*/([^\s/>]+)", oc)
            if m:
                xref2name[ox] = m.group(1)
        elif "/Type /OCMD" in oc:
            m_arr = re.search(r"/OCGs\s*\[(.*?)\]", oc, re.S)
            if m_arr:
                for ocx in [int(n) for n in re.findall(r"\b(\d+)\s+0\s+R\b", m_arr.group(1))]:
                    ocg = _safe_xref_object(doc, ocx) or ""
                    m = re.search(r"/Name\s*\((.*?)\)", ocg, re.S) or re.search(r"/Name\s*/([^\s/>]+)", ocg)
                    if m:
                        xref2name[ocx] = m.group(1)
    return tok2xref, xref2name


def _find_matching_emc(text: str, start_idx: int) -> Optional[int]:
    depth = 1
    for m in re.finditer(r"\b(BMC|BDC|EMC)\b", text[start_idx:]):
        op = m.group(1)
        if op in ("BMC", "BDC"):
            depth += 1
        elif op == "EMC":
            depth -= 1
            if depth == 0:
                return start_idx + m.end()
    return None


def _filter_stream_by_tokens(bs: bytes, allowed_tokens: Set[str]) -> bytes:
    if not bs: return b""
    text = bs.decode("latin-1","ignore")
    pat = re.compile(r"/OC\s*/([^\s]+)\s+BDC", re.IGNORECASE)
    kept = []
    for m in pat.finditer(text):
        token = m.group(1).lower()
        end_idx = _find_matching_emc(text, m.end())
        if end_idx and token in allowed_tokens:
            kept.append(text[m.start():end_idx])
    return ("\n".join(kept)).encode("latin-1","ignore")



def _make_layer_only_doc(pdf_path: str, layer_name: str, page_index: int) -> fitz.Document:
    base = fitz.open(pdf_path)
    try:
        tok2xref, xref2name = _build_token_and_name_maps_for_page(base, page_index)
        allowed_tokens = {t.lower() for t, xr in tok2xref.items() if xref2name.get(xr) == layer_name}

        # Work on a copy, modify only the specified page's content streams
        doc = fitz.open(pdf_path)
        pidx = max(0, min(page_index, len(doc) - 1))
        page = doc[pidx]
        for cr in _get_page_content_xrefs(doc, page):
            bs = _safe_xref_stream(doc, cr) or b""
            new_bs = _filter_stream_by_tokens(bs, allowed_tokens)
            doc.update_stream(cr, new_bs if new_bs.strip() else b" ")
        return doc
    finally:
        base.close()


# -------------------- Geometry Extraction and Transform Estimation --------------------

def _to_xy(obj) -> Tuple[float, float]:
    """Return (x, y) for a fitz.Point, fitz.Rect-like (x,y), or (x,y) tuple/list."""
    if hasattr(obj, "x") and hasattr(obj, "y"):
        return float(obj.x), float(obj.y)
    if isinstance(obj, (tuple, list)) and len(obj) >= 2 and all(isinstance(v, (int, float)) for v in obj[:2]):
        return float(obj[0]), float(obj[1])
    raise TypeError(f"Unsupported coordinate object: {type(obj)}")


def _extract_point_cloud(page: fitz.Page, curve_subdivide_steps: int = 8) -> List[Tuple[float, float]]:
    """Extract a coarse point cloud from vector drawings of a page.
    Lines are added directly; Bezier curves are uniformly sampled.
    """
    points: List[Tuple[float, float]] = []
    drawings = page.get_drawings()

    def _add_line(p0: Tuple[float, float], p1: Tuple[float, float]):
        points.append((float(p0[0]), float(p0[1])))
        points.append((float(p1[0]), float(p1[1])))

    def _sample_cubic(p0, p1, p2, p3, steps: int):
        p0x, p0y = _to_xy(p0)
        p1x, p1y = _to_xy(p1)
        p2x, p2y = _to_xy(p2)
        p3x, p3y = _to_xy(p3)
        for i in range(steps + 1):
            t = i / steps
            mt = 1 - t
            x = (
                mt * mt * mt * p0x
                + 3 * mt * mt * t * p1x
                + 3 * mt * t * t * p2x
                + t * t * t * p3x
            )
            y = (
                mt * mt * mt * p0y
                + 3 * mt * mt * t * p1y
                + 3 * mt * t * t * p2y
                + t * t * t * p3y
            )
            points.append((x, y))

    for d in drawings:
        path = d["items"]
        cursor: Optional[Tuple[float, float]] = None
        for it in path:
            op = it[0]
            if op == "l":
                if len(it) >= 3 and isinstance(it[1], (int, float)):
                    p1 = (float(it[1]), float(it[2]))
                else:
                    p1 = _to_xy(it[1])
                if cursor is not None:
                    _add_line(cursor, p1)
                cursor = p1
            elif op == "m":
                if len(it) >= 3 and isinstance(it[1], (int, float)):
                    cursor = (float(it[1]), float(it[2]))
                else:
                    cursor = _to_xy(it[1])
            elif op == "c":
                if len(it) == 7 and isinstance(it[1], (int, float)):
                    p0 = cursor
                    p1 = (float(it[1]), float(it[2]))
                    p2 = (float(it[3]), float(it[4]))
                    p3 = (float(it[5]), float(it[6]))
                else:
                    p0 = cursor
                    p1 = it[1]
                    p2 = it[2]
                    p3 = it[3]
                if p0 is not None:
                    _sample_cubic(p0, p1, p2, p3, curve_subdivide_steps)
                    cursor = _to_xy(p3)
            elif op == "re":
                if len(it) >= 5 and isinstance(it[1], (int, float)):
                    x, y, w, h = float(it[1]), float(it[2]), float(it[3]), float(it[4])
                else:
                    rect = it[1]
                    x, y = float(rect.x0), float(rect.y0)
                    w, h = float(rect.width), float(rect.height)
                _add_line((x, y), (x + w, y))
                _add_line((x + w, y), (x + w, y + h))
                _add_line((x + w, y + h), (x, y + h))
                _add_line((x, y + h), (x, y))
            # ignore other ops for now

    return points


def _compute_stats(points: List[Tuple[float, float]]) -> Optional[Dict[str, float]]:
    if not points:
        return None
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)

    # PCA orientation
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs) / len(xs)
    vy = sum((y - my) ** 2 for y in ys) / len(ys)
    vxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
    angle = 0.5 * math.atan2(2 * vxy, (vx - vy))  # radians

    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "center_x": cx,
        "center_y": cy,
        "width": max_x - min_x,
        "height": max_y - min_y,
        "angle_rad": angle,
    }


def _estimate_similarity_transform(stats_a: Dict[str, float], stats_b: Dict[str, float]) -> Tuple[float, float, float, float]:
    """Estimate scale, rotation(deg), translation(tx, ty) that maps B -> A.
    - scale is average of width/height ratios
    - rotation is difference of principal angles
    - translation aligns centers after applying rotation & scale
    """
    width_a = max(stats_a["width"], 1e-6)
    height_a = max(stats_a["height"], 1e-6)
    width_b = max(stats_b["width"], 1e-6)
    height_b = max(stats_b["height"], 1e-6)

    scale_w = width_a / width_b
    scale_h = height_a / height_b
    scale = 0.5 * (scale_w + scale_h)

    theta_a = stats_a["angle_rad"]
    theta_b = stats_b["angle_rad"]
    rot_rad = theta_a - theta_b
    rot_deg = math.degrees(rot_rad)

    tx = stats_a["center_x"] - stats_b["center_x"]
    ty = stats_a["center_y"] - stats_b["center_y"]

    return scale, rot_deg, tx, ty


def _layers_match(stats_a: Dict[str, float], stats_b: Dict[str, float], angle_tol_deg: float = 5.0, scale_tol: float = 0.15) -> bool:
    if not stats_a or not stats_b:
        return False
    # angles similar?
    dtheta = abs(math.degrees(stats_a["angle_rad"] - stats_b["angle_rad"])) % 180.0
    dtheta = min(dtheta, 180.0 - dtheta)
    if dtheta > angle_tol_deg:
        return False
    # aspect ratios similar?
    ar_a = stats_a["width"] / max(stats_a["height"], 1e-6)
    ar_b = stats_b["width"] / max(stats_b["height"], 1e-6)
    if abs(ar_a - ar_b) / max(ar_a, ar_b) > scale_tol:
        return False
    return True


def _match_score(stats_a: Dict[str, float], stats_b: Dict[str, float]) -> float:
    """Compute a soft similarity score in [0, 1] based on angle and aspect ratio.
    Higher is better.
    """
    if not stats_a or not stats_b:
        return 0.0
    dtheta = abs(math.degrees(stats_a["angle_rad"] - stats_b["angle_rad"])) % 180.0
    dtheta = min(dtheta, 180.0 - dtheta)
    angle_score = max(0.0, 1.0 - dtheta / 10.0)

    ar_a = stats_a["width"] / max(stats_a["height"], 1e-6)
    ar_b = stats_b["width"] / max(stats_b["height"], 1e-6)
    ar_rel = abs(ar_a - ar_b) / max(ar_a, ar_b)
    ratio_score = max(0.0, 1.0 - ar_rel / 0.25)

    return 0.5 * (angle_score + ratio_score)


def _layer_size_density_weight(
    points_a: List[Tuple[float, float]],
    points_b: List[Tuple[float, float]],
    stats_a: Dict[str, float],
    stats_b: Dict[str, float],
    size_alpha: float = 0.5,
    density_alpha: float = 0.5,
) -> float:
    """Compute a raw weight favoring larger, denser layers.
    - size term ~ (avg area)^size_alpha
    - density term ~ (avg point density)^density_alpha
    """
    eps = 1e-6
    area_a = max(stats_a["width"] * stats_a["height"], eps)
    area_b = max(stats_b["width"] * stats_b["height"], eps)
    area_avg = 0.5 * (area_a + area_b)
    pa = max(len(points_a), 1)
    pb = max(len(points_b), 1)
    dens_a = pa / area_a
    dens_b = pb / area_b
    dens_avg = 0.5 * (dens_a + dens_b)
    size_term = area_avg ** max(0.0, size_alpha)
    dens_term = (dens_avg + eps) ** max(0.0, density_alpha)
    return float(size_term * dens_term)


# -------------------- Vector ICP Refinement --------------------

def _np_from_points(points: List[Tuple[float, float]]) -> "np.ndarray":
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be Nx2")
    return arr


def _rotation_matrix_from_degrees(deg: float) -> "np.ndarray":
    theta = math.radians(deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=np.float64)


def _apply_similarity_np(points: "np.ndarray", scale: float, rot_deg: float, tx: float, ty: float) -> "np.ndarray":
    R = _rotation_matrix_from_degrees(rot_deg)
    transformed = scale * (points @ R.T)
    transformed[:, 0] += tx
    transformed[:, 1] += ty
    return transformed


def _umeyama_similarity(src: "np.ndarray", dst: "np.ndarray") -> Tuple[float, float, Tuple[float, float]]:
    """Return (scale, rot_deg, (tx, ty)) mapping src -> dst in least squares sense.
    Uses Umeyama method for similarity transform in 2D.
    """
    if src.shape[0] == 0 or dst.shape[0] == 0:
        return 1.0, 0.0, (0.0, 0.0)
    mean_src = src.mean(axis=0)
    mean_dst = dst.mean(axis=0)
    X = src - mean_src
    Y = dst - mean_dst
    cov = (X.T @ Y) / max(1, src.shape[0])
    U, S, Vt = np.linalg.svd(cov)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[1, :] *= -1
        R = Vt.T @ U.T
    var_src = (X ** 2).sum() / max(1, src.shape[0])
    scale = float((S * np.array([1.0, 1.0], dtype=np.float64)).sum() / max(var_src, 1e-12))
    t = mean_dst - scale * (mean_src @ R.T)
    rot_deg = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    return scale, rot_deg, (float(t[0]), float(t[1]))


def _subsample_points(points: List[Tuple[float, float]], max_points: int = 1500, seed: int = 42) -> List[Tuple[float, float]]:
    if len(points) <= max_points:
        return points
    rng = random.Random(seed)
    return [points[i] for i in rng.sample(range(len(points)), max_points)]


def _nearest_neighbors(src: "np.ndarray", dst: "np.ndarray") -> Tuple["np.ndarray", "np.ndarray", "np.ndarray"]:
    """Return (dst_indices, distances, matched_dst_points) for each src point.
    Uses brute-force; keep sizes modest.
    """
    # Compute squared distances matrix efficiently in chunks if needed
    # For simplicity here, do full matrix; upstream caps sizes.
    d2 = ((src[:, None, :] - dst[None, :, :]) ** 2).sum(axis=2)
    idx = np.argmin(d2, axis=1)
    mind2 = d2[np.arange(d2.shape[0]), idx]
    return idx, mind2, dst[idx]


def _icp_refine_similarity(
    points_b: List[Tuple[float, float]],
    points_a: List[Tuple[float, float]],
    init_scale: float,
    init_rot_deg: float,
    init_tx: float,
    init_ty: float,
    max_iter: int = 20,
    trim_frac: float = 0.2,
    max_points: int = 1500,
    tol: float = 1e-3,
) -> Tuple[float, float, float, float]:
    """Refine a similarity transform mapping B -> A using ICP on vector points.
    Returns (scale, rot_deg, tx, ty).
    """
    if np is None:
        return init_scale, init_rot_deg, init_tx, init_ty
    pts_b = _np_from_points(_subsample_points(points_b, max_points))
    pts_a = _np_from_points(_subsample_points(points_a, max_points))
    if pts_b.shape[0] < 10 or pts_a.shape[0] < 10:
        return init_scale, init_rot_deg, init_tx, init_ty

    s = float(init_scale)
    r = float(init_rot_deg)
    t = np.array([init_tx, init_ty], dtype=np.float64)

    prev_error = None
    for _ in range(max_iter):
        # Transform B with current params
        Tb = _apply_similarity_np(pts_b, s, r, t[0], t[1])
        # Find nearest neighbors in A
        nn_idx, d2, nn_pts = _nearest_neighbors(Tb, pts_a)
        # Trim worst matches
        if trim_frac > 0.0:
            keep = max(10, int((1.0 - trim_frac) * Tb.shape[0]))
            order = np.argsort(d2)
            sel = order[:keep]
            X = pts_b[sel]
            Y = nn_pts[sel]
            err = float(d2[sel].mean())
        else:
            X = pts_b
            Y = nn_pts
            err = float(d2.mean())

        # Compute delta transform mapping transformed-B to neighbors, or directly B->A?
        # We compute similarity mapping original B points X -> Y
        ds, dr, (dtx, dty) = _umeyama_similarity(_apply_similarity_np(X, s, r, t[0], t[1]), Y)
        # Compose: new transform = delta ∘ current
        R_delta = _rotation_matrix_from_degrees(dr)
        R_curr = _rotation_matrix_from_degrees(r)
        s = float(ds * s)
        t = (ds * (R_delta @ t)) + np.array([dtx, dty], dtype=np.float64)
        R_new = R_delta @ R_curr
        r = math.degrees(math.atan2(R_new[1, 0], R_new[0, 0]))

        if prev_error is not None and abs(prev_error - err) < tol:
            break
        prev_error = err

    return float(s), float(r), float(t[0]), float(t[1])


def _refine_translation_fixed_sr(
    points_b: List[Tuple[float, float]],
    points_a: List[Tuple[float, float]],
    scale: float,
    rot_deg: float,
    init_tx: float,
    init_ty: float,
    max_iter: int = 15,
    trim_frac: float = 0.2,
    max_points: int = 2000,
    tol: float = 1e-3,
) -> Tuple[float, float]:
    """Refine only translation (tx, ty) with fixed scale/rotation using vector points.
    Returns (tx, ty).
    """
    if np is None:
        return init_tx, init_ty
    pts_b = _np_from_points(_subsample_points(points_b, max_points))
    pts_a = _np_from_points(_subsample_points(points_a, max_points))
    if pts_b.shape[0] < 10 or pts_a.shape[0] < 10:
        return init_tx, init_ty

    t = np.array([init_tx, init_ty], dtype=np.float64)
    prev_step = None
    for _ in range(max_iter):
        Tb = _apply_similarity_np(pts_b, scale, rot_deg, t[0], t[1])
        nn_idx, d2, nn_pts = _nearest_neighbors(Tb, pts_a)
        residuals = nn_pts - Tb
        # Trim largest residuals if requested
        if trim_frac > 0.0:
            keep = max(10, int((1.0 - trim_frac) * residuals.shape[0]))
            order = np.argsort((residuals[:, 0] ** 2 + residuals[:, 1] ** 2))
            sel = order[:keep]
            step = residuals[sel].mean(axis=0)
        else:
            step = residuals.mean(axis=0)

        t = t + step
        if prev_step is not None and np.linalg.norm(step - prev_step) < tol:
            break
        prev_step = step

    return float(t[0]), float(t[1])


# -------------------- Colored Raster Overlay --------------------

def _render_page_rgba(page: fitz.Page, matrix: fitz.Matrix) -> Tuple[int, int, bytes]:
    pm = page.get_pixmap(matrix=matrix, alpha=True)
    return pm.width, pm.height, pm.samples  # RGBA bytes


def _transform_corners(a: float, b: float, c: float, d: float, rect: fitz.Rect) -> Tuple[float, float, float, float]:
    # Transform page rect corners with matrix [[a,c],[b,d]] and no translation
    pts = [
        (rect.x0, rect.y0),
        (rect.x1, rect.y0),
        (rect.x1, rect.y1),
        (rect.x0, rect.y1),
    ]
    xs = [a * x + c * y for (x, y) in pts]
    ys = [b * x + d * y for (x, y) in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _mask_from_rgba(img_rgba, lum_thresh: int, alpha_thresh: int):
    from PIL import ImageChops
    gray = img_rgba.convert("L")
    alpha = img_rgba.getchannel("A")
    lum_mask = gray.point(lambda v: 255 if v < lum_thresh else 0).convert("1")
    a_mask = alpha.point(lambda a: 255 if a > alpha_thresh else 0).convert("1")
    return ImageChops.logical_and(lum_mask, a_mask)


def _soft_ink_mask_from_rgba(img_rgba, mask_gamma: float = 1.2, alpha_gamma: float = 1.0):
    """Return a soft ink mask (L, 0..255) proportional to darkness and alpha.
    ink = ((1 - luminance) ** mask_gamma) * (alpha ** alpha_gamma)
    """
    from PIL import ImageChops
    gray = img_rgba.convert("L")
    alpha = img_rgba.getchannel("A")

    # Darkness component: 255 - gray
    darkness = ImageChops.invert(gray)

    # Apply gamma LUTs
    def _build_lut(gamma: float):
        if gamma is None or abs(gamma - 1.0) < 1e-6:
            return [i for i in range(256)]
        return [int(round(((i / 255.0) ** gamma) * 255)) for i in range(256)]

    darkness_gamma = darkness.point(_build_lut(mask_gamma))
    alpha_gamma_img = alpha.point(_build_lut(alpha_gamma))

    # Multiply darkness and alpha (PIL multiply scales by 255 automatically)
    ink = ImageChops.multiply(darkness_gamma, alpha_gamma_img)
    return ink  # L image


def _build_colored_overlay_image(
    pdf_a: str,
    pdf_b: str,
    stats_a: Dict[str, float],
    stats_b: Dict[str, float],
    scale: float,
    rot_deg: float,
    zoom: float = 4.0,
    mask_gamma: float = 1.2,
    alpha_gamma: float = 1.0,
    edge_threshold: int = 40,
    draw_lines: bool = True,
    line_color: Tuple[int, int, int] = (20, 20, 20),
    overlap_color: Tuple[int, int, int] = (200, 200, 200),
    overlap_buffer_px: int = 2,
    translation_override: Optional[Tuple[float, float]] = None,
    page_index_a: int = 0,
    page_index_b: int = 0,
):
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageOps
    except Exception as e:
        print("Pillow is required for colored overlay. Please install with: pip install pillow")
        return None

    doc_a = fitz.open(pdf_a)
    doc_b = fitz.open(pdf_b)
    try:
        page_a = doc_a[page_index_a]
        page_b = doc_b[page_index_b]

        # Render A at zoom (RGBA)
        Z = zoom
        MA = fitz.Matrix(Z, Z)
        wa, ha, rgba_a = _render_page_rgba(page_a, MA)
        img_a = Image.frombytes("RGBA", (wa, ha), rgba_a)

        # Render B with scale & rotation about origin (RGBA)
        theta = math.radians(rot_deg)
        S = scale * Z
        a = S * math.cos(theta)
        b = S * math.sin(theta)
        c = -S * math.sin(theta)
        d = S * math.cos(theta)
        MB0 = fitz.Matrix(a, b, c, d, 0, 0)
        wb0, hb0, rgba_b0 = _render_page_rgba(page_b, MB0)
        img_b0 = Image.frombytes("RGBA", (wb0, hb0), rgba_b0)

        # Compute B page bounding box in its transformed space
        minx, miny, maxx, maxy = _transform_corners(a, b, c, d, page_b.rect)

        # Map the B->A translation vector (doc units) into A's pixel space.
        # Use A's render matrix (MA = fitz.Matrix(Z, Z)) for consistency.
        tx_doc, ty_doc = (0.0, 0.0)
        if translation_override is not None:
            tx_doc, ty_doc = translation_override

        dx_pix_A = Z * tx_doc
        # Treat ty_doc in page (top-left origin, y-down) coordinates: no sign flip
        dy_pix_A = Z * ty_doc

        # Compute floating paste offsets so we can achieve subpixel alignment
        if abs(scale - 1.0) < 1e-9 and abs(rot_deg) < 1e-9:
            hb = float(page_b.rect.height)
            offset_x_f = dx_pix_A
            offset_y_f = ha - (Z * hb) - dy_pix_A
        else:
            # For B's rendered image, the pixel position of B's doc origin is (-minx, maxy).
            # For A, the pixel position of the translated origin is (dx_pix_A, ha + dy_pix_A).
            offset_x_f = dx_pix_A + minx
            offset_y_f = (ha + dy_pix_A) - maxy

        # Optional robust vertical correction using 1D profile cross-correlation
        if np is not None:
            try:
                A_soft_tmp = _soft_ink_mask_from_rgba(img_a, mask_gamma=mask_gamma, alpha_gamma=alpha_gamma)
                B_soft_0 = _soft_ink_mask_from_rgba(img_b0, mask_gamma=mask_gamma, alpha_gamma=alpha_gamma)
                pa = np.asarray(A_soft_tmp, dtype=np.float32).sum(axis=1)
                pb = np.asarray(B_soft_0, dtype=np.float32).sum(axis=1)
                if pa.max() > 0:
                    pa = pa / max(1e-6, float(np.linalg.norm(pa)))
                if pb.max() > 0:
                    pb = pb / max(1e-6, float(np.linalg.norm(pb)))
                # Full cross-correlation; lag > 0 means pb needs to move down in A
                corr = np.correlate(pa, pb, mode="full")
                # Map index to lag: idx -> lag = idx - (len(pb) - 1)
                best_idx = int(np.argmax(corr))
                lag = best_idx - (len(pb) - 1)
                # Constrain to a reasonable window (e.g., 10% of A height)
                max_shift = max(10, int(0.1 * ha))
                if -max_shift <= lag <= max_shift:
                    offset_y_f += float(lag)
            except Exception:
                pass

        # Subpixel paste: split into integer + fractional parts and pre-shift B by the fractional amount
        ox_int = int(math.floor(offset_x_f))
        oy_int = int(math.floor(offset_y_f))
        ox_frac = float(offset_x_f - ox_int)
        oy_frac = float(offset_y_f - oy_int)

        if (abs(ox_frac) > 1e-6) or (abs(oy_frac) > 1e-6):
            # Shift content left/up inside the image by fractional parts before pasting at integer coords
            # PIL affine uses output->input mapping; to shift content by (+dx, +dy), set c,f to (-dx, -dy)
            img_b_shift = img_b0.transform(
                (wb0, hb0),
                Image.AFFINE,
                (1.0, 0.0, -ox_frac, 0.0, 1.0, -oy_frac),
                resample=Image.BILINEAR,
            )
        else:
            img_b_shift = img_b0

        b_on_a = Image.new("RGBA", (wa, ha), color=(0, 0, 0, 0))
        b_on_a.paste(img_b_shift, (ox_int, oy_int), mask=img_b_shift.getchannel("A"))

        # Build soft ink masks (L 0..255) using opacity and luminance
        A_soft = _soft_ink_mask_from_rgba(img_a, mask_gamma=mask_gamma, alpha_gamma=alpha_gamma)
        B_soft = _soft_ink_mask_from_rgba(b_on_a, mask_gamma=mask_gamma, alpha_gamma=alpha_gamma)

        # Split into overlap and exclusive contributions
        # If a buffer is requested, dilate masks before computing overlap to treat near pixels as overlapping
        if overlap_buffer_px and overlap_buffer_px > 0:
            try:
                k = int(max(1, 2 * overlap_buffer_px + 1))
                A_dil = A_soft.filter(ImageFilter.MaxFilter(k))
                B_dil = B_soft.filter(ImageFilter.MaxFilter(k))
                overlap = ImageChops.darker(A_dil, B_dil)
            except Exception:
                overlap = ImageChops.darker(A_soft, B_soft)
        else:
            overlap = ImageChops.darker(A_soft, B_soft)
        a_only = ImageChops.subtract(A_soft, overlap)
        b_only = ImageChops.subtract(B_soft, overlap)

        # Optional gentle re-gamma on masks to improve visual contrast
        def _apply_mask_gamma(img_l: "Image.Image", gamma: float):
            if gamma is None or abs(gamma - 1.0) < 1e-6:
                return img_l
            lut = [int(round(((i / 255.0) ** gamma) * 255)) for i in range(256)]
            return img_l.point(lut)

        a_only = _apply_mask_gamma(a_only, 1.0)
        b_only = _apply_mask_gamma(b_only, 1.0)
        overlap = _apply_mask_gamma(overlap, 1.0)

        # Compose colored result on white bg using soft masks
        base = Image.new("RGB", (wa, ha), color=(255, 255, 255))
        red = Image.new("RGB", (wa, ha), color=(255, 0, 0))
        green = Image.new("RGB", (wa, ha), color=(0, 255, 0))
        gray = Image.new("RGB", (wa, ha), color=overlap_color)

        base = Image.composite(red, base, a_only)
        base = Image.composite(green, base, b_only)
        base = Image.composite(gray, base, overlap)

        # Edge-preserving line overlay to keep strokes visible under shading
        if draw_lines:
            gray_a = img_a.convert("L")
            gray_b = b_on_a.convert("L")
            # Edge detection and emphasis
            edges_a = ImageOps.autocontrast(gray_a.filter(ImageFilter.FIND_EDGES))
            edges_b = ImageOps.autocontrast(gray_b.filter(ImageFilter.FIND_EDGES))

            # Weight edges by ink presence to avoid noise from backgrounds
            edges_a = ImageChops.multiply(edges_a, ImageOps.autocontrast(A_soft))
            edges_b = ImageChops.multiply(edges_b, ImageOps.autocontrast(B_soft))

            # Threshold
            def _edge_threshold(img_l: "Image.Image", th: int):
                th = max(0, min(255, int(th)))
                return img_l.point(lambda v: 0 if v < th else v)

            edge_mask_a = _edge_threshold(edges_a, edge_threshold)
            edge_mask_b = _edge_threshold(edges_b, edge_threshold)

            # Combine both line masks
            line_mask = ImageChops.lighter(edge_mask_a, edge_mask_b)

            # Draw lines on top with variable alpha from line_mask
            base_rgba = base.convert("RGBA")
            lines_rgb = Image.new("RGB", (wa, ha), color=line_color)
            lines_rgba = lines_rgb.convert("RGBA")
            lines_rgba.putalpha(line_mask)
            base_rgba = Image.alpha_composite(base_rgba, lines_rgba)
            base = base_rgba.convert("RGB")

        out = io.BytesIO()
        base.save(out, format="PNG")
        return (wa, ha, out.getvalue(), page_a.rect)
    finally:
        doc_a.close()
        doc_b.close()


def _write_colored_overlay_pdf(out_path: str, page_rect: fitz.Rect, img_w: int, img_h: int, png_bytes: bytes):
    doc = fitz.open()
    try:
        page = doc.new_page(width=page_rect.width, height=page_rect.height)
        page.insert_image(page_rect, stream=png_bytes)
        doc.save(out_path)
    finally:
        doc.close()


# -------------------- Vector Recoloring and Overlay (Text + Paths) --------------------

def _fmt_rgb01(rgb: Tuple[int, int, int]) -> str:
    r = max(0, min(255, int(rgb[0]))) / 255.0
    g = max(0, min(255, int(rgb[1]))) / 255.0
    b = max(0, min(255, int(rgb[2]))) / 255.0
    return f"{r:.4f} {g:.4f} {b:.4f}"


def _recolor_stream_bytes(bs: bytes, fill_rgb: Tuple[int, int, int], stroke_rgb: Tuple[int, int, int]) -> bytes:
    if not bs:
        return bs
    text = bs.decode("latin-1", "ignore")

    # Force our colors at stream start
    fill_s = _fmt_rgb01(fill_rgb)
    stroke_s = _fmt_rgb01(stroke_rgb)
    prefix = f"{fill_s} rg\n{stroke_s} RG\n"

    # Neutralize complex colorspace settings to avoid overrides
    text = re.sub(r"(?m)^.*\b(?:cs|CS|sc|SC|scn|SCN)\b.*$\n?", "", text)

    # Replace any existing color settings with our fixed colors
    # Non-stroking RGB
    text = re.sub(r"(?:(?:[-+]?\d*\.\d+|[-+]?\d+)\s+){3}rg\b", f"{fill_s} rg", text)
    # Stroking RGB
    text = re.sub(r"(?:(?:[-+]?\d*\.\d+|[-+]?\d+)\s+){3}RG\b", f"{stroke_s} RG", text)
    # Non-stroking Gray
    text = re.sub(r"(?:[-+]?\d*\.\d+|[-+]?\d+)\s+g\b", f"{fill_s} rg", text)
    # Stroking Gray
    text = re.sub(r"(?:[-+]?\d*\.\d+|[-+]?\d+)\s+G\b", f"{stroke_s} RG", text)
    # Non-stroking CMYK
    text = re.sub(r"(?:(?:[-+]?\d*\.\d+|[-+]?\d+)\s+){4}k\b", f"{fill_s} rg", text)
    # Stroking CMYK
    text = re.sub(r"(?:(?:[-+]?\d*\.\d+|[-+]?\d+)\s+){4}K\b", f"{stroke_s} RG", text)

    return (prefix + text).encode("latin-1", "ignore")


def _make_recolored_single_page_doc(pdf_path: str, page_index: int, fill_rgb: Tuple[int, int, int], stroke_rgb: Tuple[int, int, int]) -> fitz.Document:
    src = fitz.open(pdf_path)
    try:
        dst = fitz.open()
        dst.insert_pdf(src, from_page=max(0, page_index), to_page=max(0, page_index))
    finally:
        src.close()

    # Rewrite content streams for the single page in dst (index 0)
    page = dst[0]
    for cr in _get_page_content_xrefs(dst, page):
        bs = _safe_xref_stream(dst, cr) or b""
        new_bs = _recolor_stream_bytes(bs, fill_rgb=fill_rgb, stroke_rgb=stroke_rgb)
        try:
            dst.update_stream(cr, new_bs if new_bs else b" ")
        except RuntimeError:
            # Ignore non-updatable streams
            pass
    return dst


def _write_vector_overlay_pdf(
    out_path: str,
    pdf_a: str,
    pdf_b: str,
    tx_doc: float,
    ty_doc: float,
    page_index_a: int,
    page_index_b: int,
    color_a: Tuple[int, int, int] = (255, 0, 0),
    color_b: Tuple[int, int, int] = (0, 255, 0),
):
    # Prepare recolored one-page docs for A (red) and B (green)
    doc_a_col = _make_recolored_single_page_doc(pdf_a, page_index_a, fill_rgb=color_a, stroke_rgb=color_a)
    doc_b_col = _make_recolored_single_page_doc(pdf_b, page_index_b, fill_rgb=color_b, stroke_rgb=color_b)

    try:
        pa = doc_a_col[0]
        pb = doc_b_col[0]
        rect_a = pa.rect
        rect_b = pb.rect

        out_doc = fitz.open()
        try:
            out_page = out_doc.new_page(width=rect_a.width, height=rect_a.height)

            # Place A at origin (no transform)
            dst_rect_a = fitz.Rect(0, 0, rect_a.width, rect_a.height)
            out_page.show_pdf_page(dst_rect_a, doc_a_col, 0)

            # Place B translated by (tx, ty) in PDF doc units (y-up)
            dst_rect_b = fitz.Rect(
                rect_b.x0 + tx_doc,
                rect_b.y0 + ty_doc,
                rect_b.x1 + tx_doc,
                rect_b.y1 + ty_doc,
            )
            out_page.show_pdf_page(dst_rect_b, doc_b_col, 0)

            out_doc.save(out_path)
        finally:
            out_doc.close()
    finally:
        try:
            doc_a_col.close()
        except Exception:
            pass
        try:
            doc_b_col.close()
        except Exception:
            pass

# -------------------- Main Orchestration --------------------

def _list_layer_names_for_page(pdf_path: str, page_index: int) -> Set[str]:
    doc = fitz.open(pdf_path)
    try:
        tok2xref, xref2name = _build_token_and_name_maps_for_page(doc, page_index)
        used = _collect_used_tokens_for_page(doc, doc[page_index])
        names: Set[str] = set()
        for t in used:
            xr = tok2xref.get(t)
            if xr and xr in xref2name:
                names.add(xref2name[xr])
        return names
    finally:
        doc.close()


def _top_k_matching_layers(
    pdf_a: str,
    pdf_b: str,
    k: int = 5,
    page_index_a: int = 0,
    page_index_b: int = 0,
) -> List[Tuple[str, float, float, Dict[str, float], Dict[str, float], int, int]]:
    names_a = _list_layer_names_for_page(pdf_a, page_index_a)
    names_b = _list_layer_names_for_page(pdf_b, page_index_b)
    common = sorted(names_a.intersection(names_b))
    results: List[Tuple[str, float, float, Dict[str, float], Dict[str, float], int, int]] = []
    if not common:
        return results

    for name in common:
        doc_a_layer = _make_layer_only_doc(pdf_a, name, page_index_a)
        doc_b_layer = _make_layer_only_doc(pdf_b, name, page_index_b)
        try:
            pa = doc_a_layer[page_index_a]
            pb = doc_b_layer[page_index_b]
            points_a = _extract_point_cloud(pa)
            points_b = _extract_point_cloud(pb)
            stats_a = _compute_stats(points_a)
            stats_b = _compute_stats(points_b)
            if not stats_a or not stats_b:
                continue
            if _layers_match(stats_a, stats_b):
                base_score = _match_score(stats_a, stats_b)
                weight = _layer_size_density_weight(points_a, points_b, stats_a, stats_b)
                score = base_score * (1.0 + 0.0)  # base usage; weight applied later in voting/averaging
                results.append((name, score, weight, stats_a, stats_b, len(points_a), len(points_b)))
        finally:
            doc_a_layer.close()
            doc_b_layer.close()

    results.sort(key=lambda t: t[1] * (t[2] ** 0.0), reverse=True)
    return results[:k]


def overlay_two_drawings(pdf_a: str, pdf_b: str, out_pdf: str, page_index_a: int = 0, page_index_b: int = 0) -> Optional[str]:
    """High-level API:
    - Find a common layer whose geometry matches between two drawings
    - Estimate a similarity transform (scale, rotate, translate)
    - Create a colored raster overlay: A-only red, B-only green, overlap gray (configurable)
    - Transparency in original PDFs is honored via alpha in RGBA renders
    Returns output path if success, else None.
    """
    top_matches = _top_k_matching_layers(pdf_a, pdf_b, k=5, page_index_a=page_index_a, page_index_b=page_index_b)
    if not top_matches:
        return None
    # Best match (top-1)
    best_name, best_score, best_weight, best_stats_a, best_stats_b, _, _ = top_matches[0]

    # Compute per-layer translations for voting (scale=1, rot=0 only)
    translations: List[Tuple[float, float]] = []
    weights: List[float] = []
    for name_i, _, w_i, s_a, s_b, _, _ in top_matches:
        # Initial guess by center difference
        tx0 = s_a["center_x"] - s_b["center_x"]
        ty0 = s_a["center_y"] - s_b["center_y"]
        # Refine translation using vector points for this layer
        try:
            doc_a_layer = _make_layer_only_doc(pdf_a, name_i, page_index_a)
            doc_b_layer = _make_layer_only_doc(pdf_b, name_i, page_index_b)
            pa = doc_a_layer[page_index_a]
            pb = doc_b_layer[page_index_b]
            pts_a = _extract_point_cloud(pa)
            pts_b = _extract_point_cloud(pb)
        finally:
            try:
                doc_a_layer.close()
            except Exception:
                pass
            try:
                doc_b_layer.close()
            except Exception:
                pass
        if pts_a and pts_b:
            tx_i, ty_i = _refine_translation_fixed_sr(
                points_b=pts_b,
                points_a=pts_a,
                scale=1.0,
                rot_deg=0.0,
                init_tx=tx0,
                init_ty=ty0,
            )
        else:
            tx_i, ty_i = tx0, ty0
        translations.append((tx_i, ty_i))
        weights.append(float(max(w_i, 1e-9)))

    # Quantize and vote on translation only
    TRANS_BIN = 2.0  # doc units

    def _bin_val(v: float, step: float) -> int:
        return int(round(v / step))

    vote_map: Dict[Tuple[int, int], List[int]] = {}
    weight_map: Dict[Tuple[int, int], float] = {}
    for idx, (tx_i, ty_i) in enumerate(translations):
        key = (
            _bin_val(tx_i, TRANS_BIN),
            _bin_val(ty_i, TRANS_BIN),
        )
        vote_map.setdefault(key, []).append(idx)
        weight_map[key] = weight_map.get(key, 0.0) + weights[idx]

    # Determine winning bin; tie-break uses the best match's bin
    # Select bin with maximum total weight; tie-break by best layer's bin
    max_weight = -1.0
    winning_keys: List[Tuple[int, int]] = []
    for key, wsum in weight_map.items():
        if wsum > max_weight + 1e-12:
            max_weight = wsum
            winning_keys = [key]
        elif abs(wsum - max_weight) <= 1e-12:
            winning_keys.append(key)

    if len(winning_keys) == 1:
        win_key = winning_keys[0]
    else:
        best_tx, best_ty = translations[0]
        best_key = (
            _bin_val(best_tx, TRANS_BIN),
            _bin_val(best_ty, TRANS_BIN),
        )
        win_key = best_key if best_key in winning_keys else winning_keys[0]

    # Average parameters for the winning bin
    idxs = vote_map[win_key]
    voted_layer_names = ", ".join(top_matches[i][0] for i in idxs)
    print(f"Voted translation: {len(idxs)} vote(s) from layers: {voted_layer_names}")
    # Weighted averages
    wsum = sum(weights[i] for i in idxs)
    if wsum <= 0:
        wsum = float(len(idxs))
        wnorm = [1.0 / wsum for _ in idxs]
    else:
        wnorm = [weights[i] / wsum for i in idxs]
    avg_tx = sum(wnorm[k] * translations[idxs[k]][0] for k in range(len(idxs)))
    avg_ty = sum(wnorm[k] * translations[idxs[k]][1] for k in range(len(idxs)))
    print(f"Translation params: tx={avg_tx:.2f}, ty={avg_ty:.2f} (doc units)")

    # Refine translation once more using FULL PAGE vector geometry (page coords).
    # This avoids losing parent transforms present outside OCG blocks.
    try:
        doc_a_full = fitz.open(pdf_a)
        doc_b_full = fitz.open(pdf_b)
        pa_full = doc_a_full[page_index_a]
        pb_full = doc_b_full[page_index_b]
        pts_a_full = _extract_point_cloud(pa_full)
        pts_b_full = _extract_point_cloud(pb_full)
    finally:
        try:
            doc_a_full.close()
        except Exception:
            pass
        try:
            doc_b_full.close()
        except Exception:
            pass

    if pts_a_full and pts_b_full:
        fin_tx, fin_ty = _refine_translation_fixed_sr(
            points_b=pts_b_full,
            points_a=pts_a_full,
            scale=1.0,
            rot_deg=0.0,
            init_tx=avg_tx,
            init_ty=avg_ty,
        )
        # Also compute frame-based alignment for robust baselines
        sa_full = _compute_stats(pts_a_full)
        sb_full = _compute_stats(pts_b_full)
        ty_frame = fin_ty
        tx_frame = fin_tx
        if sa_full and sb_full:
            try:
                # Vertical: use both top and bottom edges if heights are consistent
                dy_top = float(sa_full["max_y"] - sb_full["max_y"])   # top alignment (PDF y-up)
                dy_bottom = float(sa_full["min_y"] - sb_full["min_y"]) # bottom alignment
                height_a = float(sa_full["height"]) if sa_full["height"] is not None else 0.0
                height_b = float(sb_full["height"]) if sb_full["height"] is not None else 0.0
                heights_ok = (max(height_a, height_b) > 0.0 and abs(height_a - height_b) / max(height_a, height_b) < 0.02)
                edges_agree = abs(dy_top - dy_bottom) < 1.0
                ty_frame = 0.5 * (dy_top + dy_bottom) if (heights_ok and edges_agree) else dy_top
            except Exception:
                pass
            try:
                # Horizontal: prefer left/right-consistent frame delta
                dx_left = float(sa_full["min_x"] - sb_full["min_x"])
                dx_right = float(sa_full["max_x"] - sb_full["max_x"])
                width_a = float(sa_full["width"]) if sa_full["width"] is not None else 0.0
                width_b = float(sb_full["width"]) if sb_full["width"] is not None else 0.0
                widths_ok = (
                    max(width_a, width_b) > 0.0
                    and abs(width_a - width_b) / max(width_a, width_b) < 0.02
                )
                sides_agree = abs(dx_left - dx_right) < 1.0
                if widths_ok and sides_agree:
                    tx_frame = 0.5 * (dx_left + dx_right)
            except Exception:
                pass
        print(
            f"Global translation refine: tx={fin_tx:.2f}, ty={fin_ty:.2f}; frame-tx={tx_frame:.2f}, frame-ty={ty_frame:.2f}"
        )
        use_tx, use_ty = tx_frame, ty_frame
    else:
        use_tx, use_ty = avg_tx, avg_ty

    res = _build_colored_overlay_image(
        pdf_a, pdf_b, best_stats_a, best_stats_b, 1.0, 0.0,
        zoom=4.0,
        translation_override=(use_tx, use_ty),
        page_index_a=page_index_a,
        page_index_b=page_index_b,
    )
    if not res:
        return None
    img_w, img_h, png_bytes, page_rect = res
    _write_colored_overlay_pdf(out_pdf, page_rect, img_w, img_h, png_bytes)
    return out_pdf


# -------------------- Public API for pipeline integration --------------------

def create_vector_overlay_for_drawing(
    pdf_a: str,
    pdf_b: str,
    drawing_name: str,
    min_votes: int = 4,
    zoom: float = 4.0,
) -> Dict[str, Optional[object]]:
    """
    Attempt to create a vector-based colored overlay for a specific drawing name.

    - Locates the page index in each PDF where the drawing name appears
    - Uses layer geometry to vote on translation
    - If no significant layers or votes < min_votes, returns success=False

    Returns dict with keys:
      { 'success': bool, 'votes': int, 'png_bytes': Optional[bytes], 'page_rect': Optional[fitz.Rect] }
    """
    try:
        from extract_drawing import extract_drawing_names
    except Exception as e:
        print(f"  Layer-based: cannot import extract_drawing (error: {e})")
        return {"success": False, "votes": 0, "png_bytes": None, "page_rect": None, "translation": None, "page_index_a": None, "page_index_b": None}

    try:
        info_a = extract_drawing_names(pdf_a)
        info_b = extract_drawing_names(pdf_b)
    except Exception as e:
        print(f"  Layer-based: drawing name extraction failed ({e})")
        return {"success": False, "votes": 0, "png_bytes": None, "page_rect": None, "translation": None, "page_index_a": None, "page_index_b": None}

    page_index_a = None
    page_index_b = None
    for row in info_a:
        if row.get("drawing_name") == drawing_name:
            page_index_a = int(row.get("page", 1)) - 1
            break
    for row in info_b:
        if row.get("drawing_name") == drawing_name:
            page_index_b = int(row.get("page", 1)) - 1
            break

    if page_index_a is None or page_index_b is None:
        print("  Layer-based: drawing page not found in one or both PDFs")
        return {"success": False, "votes": 0, "png_bytes": None, "page_rect": None, "translation": None, "page_index_a": page_index_a, "page_index_b": page_index_b}

    try:
        top_matches = _top_k_matching_layers(
            pdf_a, pdf_b, k=5, page_index_a=page_index_a, page_index_b=page_index_b
        )
        if not top_matches:
            print("  Layer-based: no significant layers found on this page pair")
            return {"success": False, "votes": 0, "png_bytes": None, "page_rect": None, "error": "no significant layers"}

        translations: List[Tuple[float, float]] = []
        weights: List[float] = []
        for name_i, _, w_i, s_a, s_b, _, _ in top_matches:
            tx0 = s_a["center_x"] - s_b["center_x"]
            ty0 = s_a["center_y"] - s_b["center_y"]
            try:
                doc_a_layer = _make_layer_only_doc(pdf_a, name_i, page_index_a)
                doc_b_layer = _make_layer_only_doc(pdf_b, name_i, page_index_b)
                pa = doc_a_layer[page_index_a]
                pb = doc_b_layer[page_index_b]
                pts_a = _extract_point_cloud(pa)
                pts_b = _extract_point_cloud(pb)
            finally:
                try:
                    doc_a_layer.close()
                except Exception:
                    pass
                try:
                    doc_b_layer.close()
                except Exception:
                    pass
            if pts_a and pts_b:
                tx_i, ty_i = _refine_translation_fixed_sr(
                    points_b=pts_b,
                    points_a=pts_a,
                    scale=1.0,
                    rot_deg=0.0,
                    init_tx=tx0,
                    init_ty=ty0,
                )
            else:
                tx_i, ty_i = tx0, ty0
            translations.append((tx_i, ty_i))
            weights.append(float(max(w_i, 1e-9)))

        TRANS_BIN = 2.0

        def _bin_val(v: float, step: float) -> int:
            return int(round(v / step))

        vote_map: Dict[Tuple[int, int], List[int]] = {}
        weight_map: Dict[Tuple[int, int], float] = {}
        for idx, (tx_i, ty_i) in enumerate(translations):
            key = (_bin_val(tx_i, TRANS_BIN), _bin_val(ty_i, TRANS_BIN))
            vote_map.setdefault(key, []).append(idx)
            weight_map[key] = weight_map.get(key, 0.0) + weights[idx]

        max_weight = -1.0
        winning_keys: List[Tuple[int, int]] = []
        for key, wsum in weight_map.items():
            if wsum > max_weight + 1e-12:
                max_weight = wsum
                winning_keys = [key]
            elif abs(wsum - max_weight) <= 1e-12:
                winning_keys.append(key)

        if len(winning_keys) == 1:
            win_key = winning_keys[0]
        else:
            best_tx, best_ty = translations[0]
            best_key = (_bin_val(best_tx, TRANS_BIN), _bin_val(best_ty, TRANS_BIN))
            win_key = best_key if best_key in winning_keys else winning_keys[0]

        idxs = vote_map[win_key]
        votes = len(idxs)
        if votes < int(min_votes):
            print(f"  Layer-based: low vote count (votes={votes} < {min_votes})")
            # avg_tx/avg_ty not defined yet on this branch; return without translation
            return {"success": False, "votes": votes, "png_bytes": None, "page_rect": None, "translation": None, "page_index_a": page_index_a, "page_index_b": page_index_b, "error": "low votes"}

        wsum = sum(weights[i] for i in idxs)
        if wsum <= 0:
            wsum = float(len(idxs))
            wnorm = [1.0 / wsum for _ in idxs]
        else:
            wnorm = [weights[i] / wsum for i in idxs]
        avg_tx = sum(wnorm[k] * translations[idxs[k]][0] for k in range(len(idxs)))
        avg_ty = sum(wnorm[k] * translations[idxs[k]][1] for k in range(len(idxs)))

        try:
            doc_a_full = fitz.open(pdf_a)
            doc_b_full = fitz.open(pdf_b)
            pa_full = doc_a_full[page_index_a]
            pb_full = doc_b_full[page_index_b]
            pts_a_full = _extract_point_cloud(pa_full)
            pts_b_full = _extract_point_cloud(pb_full)
        finally:
            try:
                doc_a_full.close()
            except Exception:
                pass
            try:
                doc_b_full.close()
            except Exception:
                pass

        use_tx, use_ty = avg_tx, avg_ty
        if pts_a_full and pts_b_full:
            fin_tx, fin_ty = _refine_translation_fixed_sr(
                points_b=pts_b_full,
                points_a=pts_a_full,
                scale=1.0,
                rot_deg=0.0,
                init_tx=avg_tx,
                init_ty=avg_ty,
            )
            # Apply the same frame-based refinement in the name-based path
            sa_full = _compute_stats(pts_a_full)
            sb_full = _compute_stats(pts_b_full)
            ty_frame = fin_ty
            tx_frame = fin_tx
            if sa_full and sb_full:
                try:
                    dy_top = float(sa_full["max_y"] - sb_full["max_y"])   
                    dy_bottom = float(sa_full["min_y"] - sb_full["min_y"]) 
                    height_a = float(sa_full["height"]) if sa_full["height"] is not None else 0.0
                    height_b = float(sb_full["height"]) if sb_full["height"] is not None else 0.0
                    heights_ok = (max(height_a, height_b) > 0.0 and abs(height_a - height_b) / max(height_a, height_b) < 0.02)
                    edges_agree = abs(dy_top - dy_bottom) < 1.0
                    ty_frame = 0.5 * (dy_top + dy_bottom) if (heights_ok and edges_agree) else dy_top
                except Exception:
                    pass
                try:
                    dx_left = float(sa_full["min_x"] - sb_full["min_x"]) 
                    dx_right = float(sa_full["max_x"] - sb_full["max_x"]) 
                    width_a = float(sa_full["width"]) if sa_full["width"] is not None else 0.0
                    width_b = float(sb_full["width"]) if sb_full["width"] is not None else 0.0
                    widths_ok = (
                        max(width_a, width_b) > 0.0
                        and abs(width_a - width_b) / max(width_a, width_b) < 0.02
                    )
                    sides_agree = abs(dx_left - dx_right) < 1.0
                    if widths_ok and sides_agree:
                        tx_frame = 0.5 * (dx_left + dx_right)
                except Exception:
                    pass
            use_tx, use_ty = tx_frame, ty_frame

        res = _build_colored_overlay_image(
            pdf_a,
            pdf_b,
            {"width": 1.0, "height": 1.0, "angle_rad": 0.0, "center_x": 0.0, "center_y": 0.0, "min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0},
            {"width": 1.0, "height": 1.0, "angle_rad": 0.0, "center_x": 0.0, "center_y": 0.0, "min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0},
            1.0,
            0.0,
            zoom=zoom,
            translation_override=(use_tx, use_ty),
            page_index_a=page_index_a,
            page_index_b=page_index_b,
        )
        if not res:
            print("  Layer-based: rendering failed")
            return {"success": False, "votes": votes, "png_bytes": None, "page_rect": None, "translation": (use_tx, use_ty), "page_index_a": page_index_a, "page_index_b": page_index_b, "error": "rendering failed"}
        img_w, img_h, png_bytes, page_rect = res
        return {"success": True, "votes": votes, "png_bytes": png_bytes, "page_rect": page_rect, "translation": (use_tx, use_ty), "page_index_a": page_index_a, "page_index_b": page_index_b}
    except Exception as e:
        print(f"  Layer-based: exception during vector overlay ({e})")
        try:
            import traceback
            traceback.print_exc()
        except Exception:
            pass
        return {"success": False, "votes": 0, "png_bytes": None, "page_rect": None, "translation": None, "page_index_a": None, "page_index_b": None, "error": str(e)}


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUTPUT_OVERLAY_PDF), exist_ok=True)
    result = overlay_two_drawings(PDF_A, PDF_B, OUTPUT_OVERLAY_PDF)
    if result:
        print(f"Overlay created at: {result}")
    else:
        print("No sufficiently matching common layer found. Nothing was overlaid.")