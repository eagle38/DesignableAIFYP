"""
geometry_analyzer.py  — DesignableAI v3.0
==========================================
Complete rewrite focused on SKETCH-ACCURATE descriptors.

Key changes from v2:
  - `edge` descriptor REPLACED by `contour_smoothness` — measures how
    closely the mask fits an ellipse, annotation-independent.
  - NEW `proportional_size` — role-based size context ("narrow for a seat")
  - NEW `symmetry` — left-right symmetry score of the mask polygon
  - NEW `edge_regularity` — variance in edge segment lengths
  - `complexity` REMOVED — was annotation-dependent (vertex density)
  - `curvature` (solidity) KEPT — works correctly
  - `orientation` (aspect ratio) KEPT — enhanced with size context
  - Improved curvature radius estimation using actual contour sampling
  - All thresholds reviewed and tightened

Public API (unchanged signatures):
  get_part_role(label) -> str
  analyze_geometry(mask_points, part_label, seat_metadata, px_per_mm) -> dict
  compute_spatial_relations(parts_data) -> dict
  compute_px_per_mm(measurements, seat_meta) -> float | None
"""

import math
import numpy as np
import cv2
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# PART ROLE MAP (unchanged — add new labels here only)
# ---------------------------------------------------------------------------

PART_ROLE_MAP = {
    # Chair parts
    "seat":                  "seat",
    "backrest":              "backrest",
    "headrest":              "headrest",
    "lumbar_support":        "lumbar",
    "base":                  "base",
    "armrest":               "armrest",
    "armrest_sofa":          "armrest",
    "eames_lounge_cushion":  "armrest",
    "armrest_egg":           "shell",
    "leg_structure":         "base",
    "five_star_base":        "base",
    "eames_base":            "base",
    "caster_wheel":          "base",
    "control_mechanism":     "base",
    "wing_flanage":          "wing",
    # Table parts
    "table_top":             "top",
    "top":                   "top",
    "tabletop":              "top",
    "leg":                   "leg",
    "legs":                  "leg",
    "base_frame":            "base",
    "eames_lounge" :     "armrest", 
    
   
   
}

def get_part_role(label: str) -> str:
    return PART_ROLE_MAP.get(label.lower(), "unknown")


# ---------------------------------------------------------------------------
# THRESHOLDS (v3 — reviewed and tightened)
# ---------------------------------------------------------------------------

# Smoothness: ellipse deviation thresholds
_SMOOTH_ROUND       = 0.08   # ≤ this = very round/organic
_SMOOTH_MIXED       = 0.18   # ≤ this = mixed/transitional
# above = angular/geometric

# Curvature (solidity) — unchanged, works well
_FLAT_MIN_SOLIDITY  = 0.92
_CONTOURED_MAX      = 0.85

# Orientation (aspect ratio)
_WIDE_MIN_AR        = 1.25
_TALL_MAX_AR        = 0.75

# Symmetry
_SYMMETRIC_MAX      = 0.10   # ≤ this = highly symmetric
_ASYMMETRIC_MIN     = 0.25   # ≥ this = notably asymmetric

# Edge regularity (coefficient of variation of edge lengths)
_REGULAR_MAX_CV     = 0.30   # ≤ this = regular/manufactured
_IRREGULAR_MIN_CV   = 0.60   # ≥ this = irregular/organic

# Scale relative to seat
_SCALE_DOMINANT     = 1.30
_SCALE_COMPACT      = 0.50

# Proportional size: expected mm ranges per role
# (min_w, max_w, min_h, max_h) — used for proportional_size descriptor
EXPECTED_SIZE_MM = {
    "seat":     (400, 600, 380, 550), #EN 11335 EUROPEAN SEATING STANDARD
    "backrest": (350, 550, 400, 750),
    "headrest": (200, 400, 100, 280),
    "armrest":  (150, 400, 100, 300),
    "shell":    (400, 950, 700, 1100),
    "wing":     (100, 300, 200, 500),
    "lumbar":   (150, 350, 100, 220),
    "base":     (500, 750, 50, 400),
    "unknown":  (200, 600, 150, 600),
}


# ---------------------------------------------------------------------------
# SCALE FACTOR COMPUTATION (unchanged)
# ---------------------------------------------------------------------------

def compute_px_per_mm(
    measurements: dict,
    seat_meta: Optional[dict] = None
) -> Optional[float]:
    if not measurements:
        return None

    def to_mm(value, unit):
        unit = (unit or "").lower().strip()
        if unit in ("mm", "millimeter", "millimetre"):
            return float(value)
        if unit in ("cm", "centimeter", "centimetre"):
            return float(value) * 10
        if unit in ("in", "inch", "inches", '"'):
            return float(value) * 25.4
        return None

    if seat_meta and "height" in seat_meta:
        seat_px = seat_meta["height"]
        sh = measurements.get("SH") or measurements.get("sh")
        if sh:
            mm = to_mm(sh["value"], sh.get("unit", "inches"))
            if mm and mm > 0:
                return seat_px / mm
    return None


# ---------------------------------------------------------------------------
# CONTOUR SMOOTHNESS — annotation-independent
# ---------------------------------------------------------------------------
# Instead of counting vertices (which depends on annotation density),
# we fit an ellipse to the contour and measure how much the actual
# contour deviates from that ellipse. A truly round part will closely
# match regardless of how many annotation points were used.

def _contour_smoothness(contour: np.ndarray, part_label: str = "unknown") -> Tuple[float, str, str]:
    """
    Measures how closely the contour matches a fitted ellipse.
    Role-aware: base parts (legs, bases) get structural interpretations.

    Returns (deviation_score, label, detail)
    """
    pts = contour.reshape(-1, 2).astype(np.float32)
    part_name = part_label.replace("_", " ")
    r = get_part_role(part_label)

    if len(pts) < 5:
        return (0.5, "indeterminate", f"Too few points to assess {part_name} smoothness.")

    try:
        ellipse = cv2.fitEllipse(pts)
    except cv2.error:
        return (0.5, "indeterminate", f"Could not fit ellipse to {part_name} contour.")

    center, axes, angle = ellipse
    n_sample = 180
    ellipse_pts = cv2.ellipse2Poly(
        (int(center[0]), int(center[1])),
        (int(axes[0] / 2), int(axes[1] / 2)),
        int(angle), 0, 360, int(360 / n_sample)
    )

    if len(ellipse_pts) < 3:
        return (0.5, "indeterminate", "Ellipse generation failed.")

    ellipse_arr = np.array(ellipse_pts, dtype=np.float32)
    distances = []
    step = max(1, len(pts) // 60)
    for i in range(0, len(pts), step):
        pt = pts[i]
        dists = np.sqrt(np.sum((ellipse_arr - pt) ** 2, axis=1))
        distances.append(float(dists.min()))

    if not distances:
        return (0.5, "indeterminate", "No valid distance samples.")

    semi_major = max(axes[0], axes[1]) / 2
    if semi_major < 1:
        semi_major = 1

    median_dev = np.median(distances) / semi_major
    score = round(float(median_dev), 4)

    # ── Role-specific labelling ──────────────────────────────────────
    if r == "base":
        # Base parts: ellipse fit describes the leg spread pattern, not surface curvature
        if score <= _SMOOTH_ROUND:
            label = "uniform leg spread"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the legs spread in a "
                f"balanced, symmetrical pattern. The mask outline is circular because the leg "
                f"tips form a uniform radial footprint, providing even weight distribution."
            )
        elif score <= _SMOOTH_MIXED:
            label = "semi-uniform stance"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the leg arrangement has "
                f"a mostly balanced spread with some asymmetry. The stance is stable but not "
                f"perfectly radial."
            )
        else:
            label = "angular / structured frame"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the base structure has "
                f"distinct straight edges and angular joints. This is typical of rectilinear "
                f"or sled-style base construction."
            )
    elif r == "wing":
        if score <= _SMOOTH_ROUND:
            label = "smooth wing profile"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the wing follows a "
                f"smooth, continuous curve from backrest to tip. Traditional ear-wing form."
            )
        elif score <= _SMOOTH_MIXED:
            label = "mixed wing profile"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the wing has both curved "
                f"and straight sections, blending heritage and modern elements."
            )
        else:
            label = "angular wing profile"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the wing has sharp, "
                f"architectural lines. A modernist reinterpretation of the traditional ear."
            )
    else:
        # Standard parts: seat, backrest, armrest, headrest, etc.
        if score <= _SMOOTH_ROUND:
            label = "round / organic"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the {part_name}'s contour "
                f"closely follows a smooth elliptical form. This {part_name} has genuinely "
                f"curved, organic edges in the sketch."
            )
        elif score <= _SMOOTH_MIXED:
            label = "mixed / transitional"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the {part_name} has both "
                f"curved and straight sections. A blend of organic and geometric qualities."
            )
        else:
            label = "angular / geometric"
            detail = (
                f"{part_name.title()} ellipse deviation {score:.3f} — the {part_name} deviates "
                f"significantly from any smooth curve. Distinct corners and straight edges "
                f"are present in the sketch."
            )

    return (score, label, detail)


# ---------------------------------------------------------------------------
# SYMMETRY — measures left-right balance of the mask
# ---------------------------------------------------------------------------

def _measure_symmetry(contour: np.ndarray) -> Tuple[float, str, str]:
    """
    Measures left-right symmetry by comparing the left and right halves
    of the contour relative to its vertical center axis.

    Returns (asymmetry_score, label, detail)
    - 0 = perfectly symmetric, higher = more asymmetric
    """
    pts = contour.reshape(-1, 2).astype(np.float32)
    cx = pts[:, 0].mean()

    # Split into left and right of center
    left_pts = pts[pts[:, 0] <= cx]
    right_pts = pts[pts[:, 0] > cx]

    if len(left_pts) < 2 or len(right_pts) < 2:
        return (0.0, "symmetric", "Could not assess — defaulting to symmetric.")

    # Mirror right points to the left side and compare distributions
    right_mirrored = right_pts.copy()
    right_mirrored[:, 0] = 2 * cx - right_mirrored[:, 0]

    # Compare the bounding boxes of left vs mirrored-right as a simple proxy
    l_bbox = [left_pts[:, 0].min(), left_pts[:, 1].min(),
              left_pts[:, 0].max(), left_pts[:, 1].max()]
    r_bbox = [right_mirrored[:, 0].min(), right_mirrored[:, 1].min(),
              right_mirrored[:, 0].max(), right_mirrored[:, 1].max()]

    # Normalized bbox difference
    total_w = pts[:, 0].max() - pts[:, 0].min()
    total_h = pts[:, 1].max() - pts[:, 1].min()
    if total_w < 1 or total_h < 1:
        return (0.0, "symmetric", "Part too small to assess symmetry.")

    dx = (abs(l_bbox[0] - r_bbox[0]) + abs(l_bbox[2] - r_bbox[2])) / total_w
    dy = (abs(l_bbox[1] - r_bbox[1]) + abs(l_bbox[3] - r_bbox[3])) / total_h
    asym = round(float((dx + dy) / 2), 4)

    # Also compare areas of left vs right halves
    left_area = cv2.contourArea(left_pts.reshape(-1, 1, 2).astype(np.int32)) if len(left_pts) >= 3 else 0
    right_area = cv2.contourArea(right_mirrored.reshape(-1, 1, 2).astype(np.int32)) if len(right_mirrored) >= 3 else 0
    total_area = left_area + right_area
    area_diff = abs(left_area - right_area) / total_area if total_area > 0 else 0

    # Combined score
    combined = round((asym * 0.5 + area_diff * 0.5), 4)

    if combined <= _SYMMETRIC_MAX:
        label = "symmetric"
        detail = f"Symmetry score {combined:.3f} — left and right halves are well-balanced."
    elif combined <= _ASYMMETRIC_MIN:
        label = "slightly asymmetric"
        detail = f"Symmetry score {combined:.3f} — minor left-right imbalance, likely intentional perspective or sketch angle."
    else:
        label = "asymmetric"
        detail = f"Symmetry score {combined:.3f} — notable left-right imbalance. Could be intentional design or a sketching artifact."

    return (combined, label, detail)


# ---------------------------------------------------------------------------
# EDGE REGULARITY — manufactured vs handcrafted feel
# ---------------------------------------------------------------------------

def _edge_regularity(contour: np.ndarray) -> Tuple[float, str, str]:
    """
    Measures variance in edge segment lengths around the polygon.
    Regular (equal-length edges) = manufactured; irregular = organic.

    Returns (cv_score, label, detail)
    - cv_score: coefficient of variation of edge lengths (lower = more regular)
    """
    pts = contour.reshape(-1, 2).astype(np.float32)
    n = len(pts)
    if n < 4:
        return (0.5, "indeterminate", "Too few points to assess edge regularity.")

    # Compute edge lengths
    edges = []
    for i in range(n):
        dx = pts[(i + 1) % n][0] - pts[i][0]
        dy = pts[(i + 1) % n][1] - pts[i][1]
        edges.append(math.sqrt(dx * dx + dy * dy))

    edges = np.array(edges)
    mean_edge = edges.mean()
    if mean_edge < 1:
        return (0.5, "indeterminate", "Edge lengths too small to assess.")

    cv = float(edges.std() / mean_edge)
    cv = round(cv, 4)

    if cv <= _REGULAR_MAX_CV:
        label = "regular / precision"
        detail = (
            f"Edge variation {cv:.2f} — uniform segment lengths suggest a manufactured, "
            f"precision-cut form. Consistent geometry throughout."
        )
    elif cv <= _IRREGULAR_MIN_CV:
        label = "semi-regular"
        detail = (
            f"Edge variation {cv:.2f} — mostly consistent edges with some variation. "
            f"A mix of precision and organic character."
        )
    else:
        label = "irregular / freeform"
        detail = (
            f"Edge variation {cv:.2f} — highly varied segment lengths suggest an organic, "
            f"hand-shaped form. Each edge has its own character."
        )

    return (cv, label, detail)


# ---------------------------------------------------------------------------
# PROPORTIONAL SIZE — role-based width/height context
# ---------------------------------------------------------------------------

def _proportional_size(
    w_mm: Optional[float],
    h_mm: Optional[float],
    w_px: int,
    h_px: int,
    part_label: str,
    px_per_mm: Optional[float]
) -> dict:
    """
    Evaluates the width and height against expected ranges for this part's role.
    Returns a descriptor dict with label, detail, and individual width/height notes.
    """
    role = get_part_role(part_label)
    expected = EXPECTED_SIZE_MM.get(role, EXPECTED_SIZE_MM["unknown"])
    min_w, max_w, min_h, max_h = expected

    # Use mm if available, otherwise note px-only
    has_mm = w_mm is not None and h_mm is not None

    if has_mm:
        w, h = w_mm, h_mm
        unit = "mm"
    elif px_per_mm and px_per_mm > 0:
        w = round(w_px / px_per_mm, 1)
        h = round(h_px / px_per_mm, 1)
        unit = "mm (estimated)"
    else:
        # Can't do proportional assessment without scale
        return {
            "label": f"{w_px}px × {h_px}px",
            "detail": "No scale factor available — cannot assess proportions against ergonomic ranges.",
            "width_note": None,
            "height_note": None,
        }

    # Width assessment
    width_notes = []
    if w < min_w:
        width_notes.append(f"narrow — {w:.0f}{unit} is below the expected {min_w}-{max_w}{unit} range for a {role}")
    elif w > max_w:
        width_notes.append(f"wide — {w:.0f}{unit} exceeds the expected {min_w}-{max_w}{unit} range for a {role}")
    else:
        width_notes.append(f"proportional — {w:.0f}{unit} is within the expected {min_w}-{max_w}{unit} range")

    # Height assessment
    height_notes = []
    if h < min_h:
        height_notes.append(f"short — {h:.0f}{unit} is below the expected {min_h}-{max_h}{unit} range for a {role}")
    elif h > max_h:
        height_notes.append(f"tall — {h:.0f}{unit} exceeds the expected {min_h}-{max_h}{unit} range for a {role}")
    else:
        height_notes.append(f"proportional — {h:.0f}{unit} is within the expected {min_h}-{max_h}{unit} range")

    # Overall label
    w_status = "narrow" if w < min_w else ("wide" if w > max_w else "ok")
    h_status = "short" if h < min_h else ("tall" if h > max_h else "ok")

    if w_status == "ok" and h_status == "ok":
        label = "well-proportioned"
        detail = f"Width {w:.0f}{unit} and height {h:.0f}{unit} both fall within expected ranges for a {role}."
    elif w_status == "wide" and h_status == "short":
        label = "wide and low-profile"
        detail = f"Width {w:.0f}{unit} is generous but height {h:.0f}{unit} is below typical for a {role}. This creates a low, spread-out proportion."
    elif w_status == "narrow" and h_status == "tall":
        label = "narrow and tall"
        detail = f"Width {w:.0f}{unit} is below typical and height {h:.0f}{unit} exceeds expected range for a {role}. This creates a vertical, tower-like proportion."
    elif w_status == "wide":
        label = "wide"
        detail = f"Width {w:.0f}{unit} exceeds the expected range for a {role} ({min_w}-{max_w}{unit})."
    elif w_status == "narrow":
        label = "narrow"
        detail = f"Width {w:.0f}{unit} is below the expected range for a {role} ({min_w}-{max_w}{unit})."
    elif h_status == "tall":
        label = "tall"
        detail = f"Height {h:.0f}{unit} exceeds the expected range for a {role} ({min_h}-{max_h}{unit})."
    else:
        label = "short"
        detail = f"Height {h:.0f}{unit} is below the expected range for a {role} ({min_h}-{max_h}{unit})."

    return {
        "label": label,
        "detail": detail,
        "width_note": width_notes[0] if width_notes else None,
        "height_note": height_notes[0] if height_notes else None,
    }


# ---------------------------------------------------------------------------
# CURVATURE DESCRIPTOR (solidity — kept from v2, works correctly)
# ---------------------------------------------------------------------------

def _describe_curvature(solidity: float, part_label: str = "unknown") -> dict:
    part_name = part_label.replace("_", " ")
    r = get_part_role(part_label)

    if r == "base":
        # Base parts: low solidity means gaps between legs, NOT body-cradling
        if solidity >= _FLAT_MIN_SOLIDITY:
            return {"label": "solid / closed frame",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — a solid, continuous base structure with minimal gaps. Sled-style or platform base."}
        elif solidity <= _CONTOURED_MAX:
            return {"label": "open frame / leg gaps",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — significant open space between legs. The mask captures all legs as one polygon, and the low solidity reflects the visible gaps between them — not surface curvature."}
        else:
            return {"label": "semi-open frame",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — moderate gaps between structural members. A partially enclosed base with some visual lightness."}
    elif r == "wing":
        if solidity >= _FLAT_MIN_SOLIDITY:
            return {"label": "solid wing panel",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — a solid, filled wing surface. Full enclosure for the head and shoulders."}
        elif solidity <= _CONTOURED_MAX:
            return {"label": "open / sculptural wing",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — the wing has cut-outs or sculptural openings. A deconstructed wing form."}
        else:
            return {"label": "semi-enclosed wing",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — a mostly solid wing with some open or thinned sections."}
    else:
        # Standard parts: solidity describes surface curvature
        if solidity >= _FLAT_MIN_SOLIDITY:
            return {"label": "flat / linear",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — the {part_name} fills its convex hull almost completely. No cradling geometry."}
        elif solidity <= _CONTOURED_MAX:
            return {"label": "contoured / cradling",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — the {part_name} has significant concavity, curving inward to wrap the body."}
        else:
            return {"label": "semi-contoured",
                    "detail": f"{part_name.title()} solidity {solidity:.2f} — the {part_name} has mild concavity. A subtle dish or gentle crown."}


# ---------------------------------------------------------------------------
# ORIENTATION DESCRIPTOR (aspect ratio — enhanced with absolute context)
# ---------------------------------------------------------------------------

def _describe_orientation(aspect_ratio: float, w_px: int, h_px: int, part_label: str = "unknown") -> dict:
    part_name = part_label.replace("_", " ")
    r = get_part_role(part_label)

    if r == "base":
        if aspect_ratio >= _WIDE_MIN_AR:
            return {"label": "wide stance",
                    "detail": f"{part_name.title()} aspect ratio {aspect_ratio:.2f} ({w_px}px wide × {h_px}px tall) — the base spreads wider than it is tall, providing a broad, stable footprint."}
        elif aspect_ratio <= _TALL_MAX_AR:
            return {"label": "tall / elevated base",
                    "detail": f"{part_name.title()} aspect ratio {aspect_ratio:.2f} ({w_px}px wide × {h_px}px tall) — the legs are taller than the base is wide, creating an elevated, slender stance."}
        else:
            return {"label": "balanced stance",
                    "detail": f"{part_name.title()} aspect ratio {aspect_ratio:.2f} ({w_px}px wide × {h_px}px tall) — the base width and height are roughly equal."}
    else:
        if aspect_ratio >= _WIDE_MIN_AR:
            return {"label": "wide / horizontal emphasis",
                    "detail": f"{part_name.title()} aspect ratio {aspect_ratio:.2f} ({w_px}px wide × {h_px}px tall) — the {part_name}'s width dominates its height."}
        elif aspect_ratio <= _TALL_MAX_AR:
            return {"label": "tall / vertical emphasis",
                    "detail": f"{part_name.title()} aspect ratio {aspect_ratio:.2f} ({w_px}px wide × {h_px}px tall) — the {part_name}'s height dominates its width."}
        else:
            return {"label": "balanced / square proportion",
                    "detail": f"{part_name.title()} aspect ratio {aspect_ratio:.2f} ({w_px}px wide × {h_px}px tall) — the {part_name}'s width and height are roughly equal."}


# ---------------------------------------------------------------------------
# ANGLE UTILITIES (improved)
# ---------------------------------------------------------------------------

def _dominant_angle_deg(contour: np.ndarray) -> float:
    pts = contour.reshape(-1, 2).astype(np.float32)
    if len(pts) < 3:
        return 0.0
    mean, eigenvectors = cv2.PCACompute(pts, mean=None)
    vx, vy = eigenvectors[0]
    return round(math.degrees(math.atan2(float(vy), float(vx))) % 180, 1)


def _inner_edge_angle_deg(contour: np.ndarray) -> Optional[float]:
    """
    Finds the sharpest (smallest) inner angle in the polygon.
    Uses the raw contour, not the simplified one, for accuracy.
    Samples at stride to handle high-point-count masks efficiently.
    """
    pts = contour.reshape(-1, 2).astype(np.float64)
    n = len(pts)
    if n < 3:
        return None

    # For masks with many points, sample at stride
    stride = max(1, n // 40)
    min_angle = 360.0

    for i in range(0, n, stride):
        p0 = pts[(i - stride) % n]
        p1 = pts[i]
        p2 = pts[(i + stride) % n]
        v1, v2 = p0 - p1, p2 - p1
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1 or n2 < 1:
            continue
        cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        angle = math.degrees(math.acos(cos_a))
        if angle < min_angle:
            min_angle = angle

    return round(min_angle, 1) if min_angle < 360 else None


def _backrest_recline_angle(contour: np.ndarray) -> float:
    rect = cv2.minAreaRect(contour)
    angle = rect[2]
    w, h = rect[1]
    recline = abs(angle) if w < h else 90 - abs(angle)
    return round(recline, 1)


# ---------------------------------------------------------------------------
# CURVATURE RADIUS (improved sampling)
# ---------------------------------------------------------------------------

def _curvature_radius_mm(contour: np.ndarray, px_per_mm: Optional[float]) -> Optional[float]:
    pts = contour.reshape(-1, 2).astype(np.float32)
    n = len(pts)
    if n < 5:
        return None

    radii = []
    step = max(1, n // 30)
    for i in range(0, n, step):
        p0 = pts[(i - step) % n]
        p1 = pts[i]
        p2 = pts[(i + step) % n]
        a = np.linalg.norm(p1 - p0)
        b = np.linalg.norm(p2 - p1)
        c = np.linalg.norm(p2 - p0)
        cross = abs(float((p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0])))
        if cross < 1e-6 or a < 1 or b < 1 or c < 1:
            continue
        radii.append((a * b * c) / (2 * cross))

    if not radii:
        return None

    mean_r = float(np.median(radii))
    if mean_r > 2000:
        return None

    return round(mean_r / px_per_mm, 1) if (px_per_mm and px_per_mm > 0) else round(mean_r, 1)


# ---------------------------------------------------------------------------
# MEASUREMENT BLOCK (improved)
# ---------------------------------------------------------------------------

def _build_measurements(
    contour: np.ndarray,
    seat_meta: Optional[dict],
    px_per_mm: Optional[float],
    part_label: str
) -> dict:
    x, y, w_px, h_px = cv2.boundingRect(contour)
    area_px = cv2.contourArea(contour)
    perimeter_px = cv2.arcLength(contour, True)

    def px_to_mm(px):
        return round(px / px_per_mm, 1) if (px_per_mm and px_per_mm > 0) else None

    m = {
        "width_px":             int(w_px),
        "height_px":            int(h_px),
        "area_px":              int(area_px),
        "perimeter_px":         round(float(perimeter_px), 1),
        "dominant_angle_deg":   _dominant_angle_deg(contour),
        "inner_edge_angle_deg": _inner_edge_angle_deg(contour),
        "curvature_radius":     _curvature_radius_mm(contour, px_per_mm),
        "curvature_radius_unit": "mm" if px_per_mm else "px",
    }

    w_mm = px_to_mm(w_px)
    h_mm = px_to_mm(h_px)
    if w_mm is not None: m["width_mm"] = w_mm
    if h_mm is not None: m["height_mm"] = h_mm

    # Area in mm²
    if px_per_mm and px_per_mm > 0:
        m["area_mm2"] = round(area_px / (px_per_mm ** 2), 1)

    # Scale relative to seat
    if seat_meta and "height" in seat_meta and seat_meta["height"] > 0:
        rel = round(h_px / seat_meta["height"], 2)
        m["scale_vs_seat"] = rel
        if rel >= _SCALE_DOMINANT:
            m["scale_label"] = "dominant (significantly taller than seat)"
        elif rel <= _SCALE_COMPACT:
            m["scale_label"] = "compact (significantly shorter than seat)"
        else:
            m["scale_label"] = "proportional to seat"

    # Recline angle for backrests
    if get_part_role(part_label) == "backrest":
        m["recline_angle_deg"] = _backrest_recline_angle(contour)

    # Compactness (circularity): 4π × area / perimeter².  1.0 = perfect circle
    if perimeter_px > 0:
        compactness = (4 * math.pi * area_px) / (perimeter_px ** 2)
        m["compactness"] = round(compactness, 3)

    return m


# ---------------------------------------------------------------------------
# ERGONOMIC BENCHMARK FLAGS (role-based, improved)
# ---------------------------------------------------------------------------

ERGONOMIC_BENCHMARKS = {
    "seat":     {"ideal_depth_mm": (430, 520), "ideal_width_mm": (450, 550)},
    "backrest": {"ideal_recline_deg": (95, 110), "ideal_height_mm": (450, 700)},
    "armrest":  {"ideal_height_mm": (200, 260), "inner_edge_safe_deg": 45},
    "shell":    {"ideal_inner_width_mm": (450, 560)},
    "headrest": {"ideal_height_mm": (150, 250)},
    "lumbar":   {"ideal_height_mm": (150, 200)},
    "wing":     {},
    "base":     {"five_star_min_diameter_mm": 650, "five_star_max_diameter_mm": 720},
}


def _ergonomic_flags(part_label: str, measurements: dict) -> list:
    flags = []
    role = get_part_role(part_label)
    bench = ERGONOMIC_BENCHMARKS.get(role, {})

    def flag(field, value, benchmark, status, note):
        flags.append({"field": field, "measured": value,
                       "benchmark": benchmark, "status": status, "note": note})

    # Seat depth
    if role == "seat" and "height_mm" in measurements:
        d = measurements["height_mm"]
        lo, hi = bench["ideal_depth_mm"]
        if d < lo:
            flag("depth", f"{d}mm", f"{lo}-{hi}mm", "warning",
                 f"Seat depth {d}mm is shallow — lower back may not reach the backrest.")
        elif d > hi:
            flag("depth", f"{d}mm", f"{lo}-{hi}mm", "critical",
                 f"Seat depth {d}mm exceeds {hi}mm — shorter users' lower back won't reach the backrest. Reduce by {round(d-hi)}mm.")
        else:
            flag("depth", f"{d}mm", f"{lo}-{hi}mm", "ok", "Seat depth is within the ergonomic range.")

    # Seat width
    if role == "seat" and "width_mm" in measurements:
        w = measurements["width_mm"]
        lo, hi = bench["ideal_width_mm"]
        if w < lo:
            flag("width", f"{w}mm", f"{lo}-{hi}mm", "warning",
                 f"Seat width {w}mm is narrow — restricts posture shifting and may not accommodate all users.")
        elif w > hi:
            flag("width", f"{w}mm", f"{lo}-{hi}mm", "warning",
                 f"Seat width {w}mm is generous — good for comfort but smaller users may lack lateral thigh support.")
        else:
            flag("width", f"{w}mm", f"{lo}-{hi}mm", "ok", "Seat width is within the ergonomic range.")

    # Backrest recline
    if role == "backrest" and "recline_angle_deg" in measurements:
        r = measurements["recline_angle_deg"]
        lo, hi = bench["ideal_recline_deg"]
        if r < lo:
            flag("recline", f"{r}°", f"{lo}-{hi}°", "warning",
                 f"Backrest at {r}° is very upright — lumbar discs under higher compression during long sits.")
        elif r > hi:
            flag("recline", f"{r}°", f"{lo}-{hi}°", "warning",
                 f"Backrest at {r}° is a significant recline — user may slide forward.")
        else:
            flag("recline", f"{r}°", f"{lo}-{hi}°", "ok", "Recline angle is within the ergonomic comfort zone.")

    # Backrest height
    if role == "backrest" and "height_mm" in measurements:
        h = measurements["height_mm"]
        lo, hi = bench["ideal_height_mm"]
        if h < lo:
            flag("back_height", f"{h}mm", f"{lo}-{hi}mm", "warning",
                 f"Backrest height {h}mm is low — won't support upper back and shoulders.")
        elif h > hi:
            flag("back_height", f"{h}mm", f"{lo}-{hi}mm", "ok",
                 f"Backrest height {h}mm provides full back support including shoulders.")
        else:
            flag("back_height", f"{h}mm", f"{lo}-{hi}mm", "ok", "Backrest height is within the standard range.")

    # Armrest inner edge
    if role == "armrest" and "inner_edge_angle_deg" in measurements:
        a = measurements["inner_edge_angle_deg"]
        safe = bench["inner_edge_safe_deg"]
        if a is not None and a < safe:
            flag("inner_edge", f"{a}°", f">={safe}°", "critical",
                 f"{part_label}: inner edge {a}° will create a pressure point on the forearm.")
        elif a is not None:
            flag("inner_edge", f"{a}°", f">={safe}°", "ok",
                 f"{part_label}: inner edge angle is safe for forearm contact.")

    # Shell width
    if role == "shell" and "width_mm" in measurements:
        w = measurements["width_mm"]
        lo, hi = bench["ideal_inner_width_mm"]
        if w < lo:
            flag("inner_width", f"{w}mm", f"{lo}-{hi}mm", "warning",
                 f"Shell width {w}mm may be narrow for entry/exit — adult shoulder breadth is 420-500mm.")
        else:
            flag("inner_width", f"{w}mm", f"{lo}-{hi}mm", "ok",
                 f"Shell width {w}mm provides adequate shoulder clearance.")

    # Five-star base diameter
    if part_label == "five_star_base" and "width_mm" in measurements:
        w = measurements["width_mm"]
        lo = bench.get("five_star_min_diameter_mm", 650)
        hi = bench.get("five_star_max_diameter_mm", 720)
        if w < lo:
            flag("base_diameter", f"{w}mm", f">={lo}mm", "critical",
                 f"Five-star base {w}mm is below EN 1335 minimum of {lo}mm — stability risk.")
        elif w > hi:
            flag("base_diameter", f"{w}mm", f"<={hi}mm", "warning",
                 f"Base diameter {w}mm exceeds {hi}mm — foot-stub hazard.")
        else:
            flag("base_diameter", f"{w}mm", f"{lo}-{hi}mm", "ok",
                 "Base diameter is within the EN 1335 stability range.")

    return flags


# ---------------------------------------------------------------------------
# PART LABEL INTERPRETATIONS (v3 — updated for new descriptors)
# ---------------------------------------------------------------------------
# Structure: PART_LABEL_INTERPRETATIONS[label][descriptor_label] = {design, ergonomics}
# Updated to match new descriptor labels from v3 functions.

PART_LABEL_INTERPRETATIONS = {

    "seat": {
        "round / organic": {
            "design":     "A sculpted bucket seat — the form itself communicates comfort before anyone sits in it.",
            "ergonomics": "The curved form centres the sitter's weight naturally. Verify the dish depth does not restrict posture shifting.",
        },
        "mixed / transitional": {
            "design":     "A seat with both curved and straight elements — structured yet approachable.",
            "ergonomics": "Adequate comfort geometry. Check that transitions between flat and curved zones don't create ridges under upholstery.",
        },
        "angular / geometric": {
            "design":     "A thin, architectural seat pan — minimal and precise. Reads as high-design but uncompromising.",
            "ergonomics": "Angular seat edges can cut into the underside of the thigh. The front edge must be waterfall-profiled (rounded downward) before upholstery.",
        },
        "flat / linear": {
            "design":     "A platform seat — stable, neutral, and versatile. Works for dining, task, or formal seating.",
            "ergonomics": "No intrinsic body contouring. Requires denser foam (minimum 40kg/m³) to prevent pressure concentration at the sitting bones.",
        },
        "contoured / cradling": {
            "design":     "A deeply shaped seat shell — the form prioritises body-fit over visual simplicity.",
            "ergonomics": "Maximum pressure distribution. The contours must align with human hip geometry — a mismatched mold causes more discomfort than a flat seat.",
        },
        "semi-contoured": {
            "design":     "A gently contoured seat — practical middle ground between flat and sculpted.",
            "ergonomics": "Good pressure distribution with lower upholstery complexity than a deeply sculpted seat.",
        },
        "wide / horizontal emphasis": {
            "design":     "A generous seat — relaxed, lounge-oriented proportions.",
            "ergonomics": "Wide seats accommodate larger users but can leave smaller users without lateral thigh support.",
        },
        "tall / vertical emphasis": {
            "design":     "An unusually deep seat relative to width — an elongated proportion, uncommon.",
            "ergonomics": "Deep-narrow seats restrict lateral movement. Flag for review.",
        },
        "balanced / square proportion": {
            "design":     "A proportionally resolved seat — width and depth in balance.",
            "ergonomics": "Neutral proportions. Verify absolute dimensions via SD and SW labels.",
        },
    },

    "backrest": {
        "round / organic": {
            "design":     "A sculptural backrest that mirrors the spine's natural S-curve — warm, humanist, ergonomically intentional.",
            "ergonomics": "Distributes back pressure evenly. The organic form naturally accommodates the lumbar curve.",
        },
        "mixed / transitional": {
            "design":     "A gently contoured backrest — suggests ergonomic awareness without full sculptural commitment.",
            "ergonomics": "Mild lumbar accommodation. For extended sessions a separate lumbar cushion will improve support.",
        },
        "angular / geometric": {
            "design":     "Crisp, planar backrest — architectural and precise. Reads as formal or modernist.",
            "ergonomics": "Flat sharp top corners create a blade effect on the shoulder blades. Without rounding or padding, pressure points develop within 20 minutes.",
        },
        "flat / linear": {
            "design":     "A firm, upright plane — formal, structured, task-oriented.",
            "ergonomics": "No intrinsic lumbar support. User must maintain active posture or use a lumbar cushion.",
        },
        "contoured / cradling": {
            "design":     "A backrest that wraps the torso — signals premium ergonomic intent.",
            "ergonomics": "Targets the lumbar curve directly. Concave zones need rigid internal support to resist flex.",
        },
        "semi-contoured": {
            "design":     "A gently dished backrest — subtle ergonomic shaping.",
            "ergonomics": "Mild lumbar support. Adequate for most users for medium-duration sitting.",
        },
        "wide / horizontal emphasis": {
            "design":     "A broad backrest — generous, relaxed, lounge-oriented.",
            "ergonomics": "Accommodates posture shifting. Check that width stays within seat width to avoid top-heavy look.",
        },
        "tall / vertical emphasis": {
            "design":     "A commanding high back — formal, throne-like, or executive.",
            "ergonomics": "Supports the entire spine. Verify base width is sufficient to counterbalance the height.",
        },
        "balanced / square proportion": {
            "design":     "A mid-height backrest — versatile, neither casual nor formal.",
            "ergonomics": "Supports lumbar and lower thoracic spine. Upper back unsupported — acceptable for task chairs.",
        },
    },

    "armrest": {
        "round / organic": {
            "design":     "Follows the natural resting arc of the forearm — ergonomically sympathetic and visually warm.",
            "ergonomics": "No pressure points. The arm will not slide off. Safest edge profile for prolonged sitting.",
        },
        "angular / geometric": {
            "design":     "Track-style rail — clean architectural line, reads as modernist and precise.",
            "ergonomics": "Inner corners are potential pressure points on the forearm. Sharpest corner needs minimum 3mm radius before upholstery.",
        },
        "mixed / transitional": {
            "design":     "A restrained curve — structured enough to read as intentional, soft enough to avoid a clinical feel.",
            "ergonomics": "Low pressure risk. Check transition points where straight meets curve.",
        },
        "flat / linear": {
            "design":     "A flat arm surface that doubles as a ledge — practical for resting a drink or device.",
            "ergonomics": "Comfortable if wide enough. Narrow flat arm forces the elbow into unsupported overhang.",
        },
        "contoured / cradling": {
            "design":     "The arm dips where the elbow sits — a deliberate ergonomic gesture.",
            "ergonomics": "Prevents arm from sliding forward, reducing shoulder fatigue. Concave zone needs denser foam.",
        },
        "semi-contoured": {
            "design":     "A gently dished arm surface — subtle ergonomic shaping that reads as refined.",
            "ergonomics": "Mild centering effect on the forearm. Lower pressure risk than flat.",
        },
    },

    "headrest": {
        "round / organic": {
            "design":     "A pillow or cradle headrest — warm, inviting, unmistakably comfort-focused.",
            "ergonomics": "Follows the natural curve of neck and skull. Reduces lateral neck strain.",
        },
        "angular / geometric": {
            "design":     "An angular headrest — modern, architectural, assertive.",
            "ergonomics": "Sharp edges don't contact body in correct use, but if user slides down, a sharp lower edge presses into upper neck.",
        },
        "flat / linear": {
            "design":     "A flat headrest pad — simple, clean, minimal.",
            "ergonomics": "Provides a surface but doesn't cradle. Head tends to slip sideways.",
        },
    },

    "wing_flanage": {
        "smooth wing profile": {
            "design":     "The traditional ear — classic wing-chair language. A smooth, continuous curve from backrest to tip evokes fireplace warmth and heritage.",
            "ergonomics": "Curved wings cradle head and shoulders during reading or napping. The softer form distributes incidental contact pressure.",
        },
        "mixed wing profile": {
            "design":     "A softened wing — retains the protective enclosure with both curved and straight elements. Versatile across contemporary and transitional interiors.",
            "ergonomics": "Mild enclosure. The wing-to-backrest transition is structurally critical — verify the joint can handle lateral loads.",
        },
        "angular wing profile": {
            "design":     "Architectural fins — bold, modernist wings that treat the traditional form as a geometric abstraction. High visual impact.",
            "ergonomics": "Sharp wing edges aren't body-contact surfaces normally. The joint where a sharp wing meets the backrest experiences high leverage — reinforce with steel brackets or deep double-dowel joinery.",
        },
        "solid wing panel": {
            "design":     "A solid, filled wing surface — full enclosure for the head and shoulders. Maximum acoustic and visual privacy.",
            "ergonomics": "Full enclosure provides thermal retention and blocks draughts. The solid panel adds significant weight to the wing-backrest joint.",
        },
        "semi-enclosed wing": {
            "design":     "A mostly solid wing with some open sections — balances enclosure with visual lightness.",
            "ergonomics": "Good incidental head support. Lower structural complexity at the joint than a fully solid wing.",
        },
        "open / sculptural wing": {
            "design":     "A deconstructed wing with openings or sculptural cut-outs — modern and dramatic, departing from the traditional solid ear.",
            "ergonomics": "Reduced acoustic privacy and thermal enclosure. The openings reduce structural mass, which lowers leverage on the joint.",
        },
    },

    "leg_structure": {
        "uniform leg spread": {
            "design":     "The legs fan out in a balanced, symmetrical pattern — classic four-leg or splayed-leg construction. The radial footprint reads as stable and grounded.",
            "ergonomics": "Uniform spread maximises tip resistance. Verify splay angle does not create a toe-stub hazard around desk legs.",
        },
        "semi-uniform stance": {
            "design":     "The leg arrangement is mostly balanced with minor asymmetry — could be perspective distortion from the sketch angle or an intentional offset stance.",
            "ergonomics": "Slightly uneven stance still provides adequate stability for standard use. Cross-check with seat weight distribution.",
        },
        "angular / structured frame": {
            "design":     "Straight, angular leg geometry — rectilinear or sled-style construction. Clean, minimal, structurally efficient.",
            "ergonomics": "Straight legs are the most predictable under load and the easiest to specify joinery for. Maximum structural efficiency.",
        },
        "open frame / leg gaps": {
            "design":     "Visible gaps between legs create visual lightness beneath the seat — the chair appears to float. A defining characteristic of legged furniture vs platform bases.",
            "ergonomics": "Open frame allows airflow beneath the seat and easy floor cleaning. The gap width affects perceived stability — very wide gaps can make the chair feel less secure to the sitter.",
        },
        "semi-open frame": {
            "design":     "Partially enclosed base with some visible gaps — between a fully open four-leg stance and a solid platform base.",
            "ergonomics": "Moderate visual weight. Structural members are partially visible, allowing inspection of joints.",
        },
        "solid / closed frame": {
            "design":     "A solid, continuous base structure — sled-style, platform, or fully enclosed pedestal. The base reads as monolithic and grounded.",
            "ergonomics": "Solid bases provide maximum stability but prevent floor cleaning underneath. Weight is significant.",
        },
        "wide stance": {
            "design":     "Broad leg spread — the chair has a wide, grounded footprint. Visually stable and imposing.",
            "ergonomics": "Wide stance significantly improves tip resistance — especially important for high-back chairs. Verify splay angle does not create a toe-stub hazard.",
        },
        "tall / elevated base": {
            "design":     "Long, slender legs — elevates the seat, creating visual lightness and a floating quality.",
            "ergonomics": "Taller legs raise the centre of gravity. Base width must increase proportionally to maintain stability.",
        },
        "balanced stance": {
            "design":     "Proportionally neutral legs — they serve the chair body rather than making a statement of their own.",
            "ergonomics": "No structural concerns from proportion alone. Specify 32mm minimum section for hardwood legs.",
        },
    },

    "five_star_base": {
        "uniform leg spread": {
            "design":     "Classic five-star radial pattern — the industry standard for swivel office chairs. Clean, functional, precise.",
            "ergonomics": "The uniform radial spread provides equal tip resistance in all directions. EN 1335 requires minimum 650mm diameter.",
        },
        "semi-uniform stance": {
            "design":     "Mostly symmetrical five-star base with minor variation — could be perspective distortion from the sketch.",
            "ergonomics": "Adequate stability. Verify all five arms are equal length for even load distribution.",
        },
        "angular / structured frame": {
            "design":     "A crisp, angular five-star base — polished aluminium or die-cast construction with defined edges.",
            "ergonomics": "Verify arm tips have end-caps — bare metal tips scratch floors and can snag cables.",
        },
        "open frame / leg gaps": {
            "design":     "The five arms create a star pattern with open space between them — the standard visual language of contract office seating.",
            "ergonomics": "Gaps between arms allow caster movement and cable routing. The open pattern is structurally efficient.",
        },
        "semi-open frame": {
            "design":     "A five-star base with partially filled sections between arms — adds visual weight over a standard open star.",
            "ergonomics": "Additional material between arms can improve rigidity but adds weight and cost.",
        },
        "solid / closed frame": {
            "design":     "A disc or platform base rather than a traditional five-star — unusual for an office chair. Makes a bold visual statement.",
            "ergonomics": "Solid bases prevent caster debris accumulation but are heavier and harder to move.",
        },
        "wide stance": {
            "design":     "Extra-wide base radius — stability over aesthetics. Signals a heavy-duty or bariatric specification.",
            "ergonomics": "Wider than 720mm can become a foot-stub hazard and may prevent the chair fitting under standard desks.",
        },
        "balanced stance": {
            "design":     "A standard 650–700mm base — the industry norm. Correct and unremarkable.",
            "ergonomics": "Meets EN 1335 stability requirements. Adequate for standard use up to 110kg.",
        },
    },

    "eames_base": {
        "uniform leg spread": {
            "design":     "The classic Eames five-point base — die-cast aluminium arms spreading in a uniform radial pattern. Directly references the original 670 base.",
            "ergonomics": "The uniform spread provides stability for the reclined lounge posture. Base width must match or exceed the shell width.",
        },
        "semi-uniform stance": {
            "design":     "Mostly symmetrical Eames base with minor variation — likely sketch perspective.",
            "ergonomics": "Adequate stability. Verify swivel mechanism is specified — the Eames lounge uses manual swivel, not gas-lift.",
        },
        "angular / structured frame": {
            "design":     "A crisp, die-cast Eames base — sharp aluminium edges, industrial precision.",
            "ergonomics": "Base doesn't contact the body. The angular finish increases perceived quality of the whole chair.",
        },
        "open frame / leg gaps": {
            "design":     "The Eames base arms create an open star pattern beneath the shell — the gaps are integral to the floating visual language of the 670 design.",
            "ergonomics": "Open gaps between arms allow the chair to visually float. The structural load passes through each arm equally.",
        },
        "solid / closed frame": {
            "design":     "A solid disc base rather than the traditional open arms — a significant departure from the Eames vocabulary.",
            "ergonomics": "A solid base adds weight and changes the visual character entirely. Verify this is intentional.",
        },
        "wide stance": {
            "design":     "The low, wide Eames base spread — defines the floating, horizontal visual footprint of the lounge chair.",
            "ergonomics": "Wide base provides stability for the reclined posture. If narrower than the shell width, the chair will feel unstable.",
        },
        "balanced stance": {
            "design":     "A compact Eames base — proportionally restrained, the base does not assert itself visually.",
            "ergonomics": "Adequate stability for normal use. Verify base span is at least as wide as the shell at its widest.",
        },
    },

    "armrest_sofa": {
        "round / organic": {
            "design":     "A rolled or English arm — classic sofa vocabulary. Signals heritage and warmth.",
            "ergonomics": "No pressure points. Roll distributes forearm contact across a large curved surface.",
        },
        "angular / geometric": {
            "design":     "A contemporary track arm — clean, boxy, distinctly modern.",
            "ergonomics": "Inner edge must be broken before upholstery. Larger forearm contact zone means longer pressure line.",
        },
    },

    "eames_lounge_cushion": {
        "round / organic": {
            "design":     "The canonical Eames lounge form. Every curve references the 670/671 silhouette.",
            "ergonomics": "Anatomically shaped. Low wide profile keeps shoulder relaxed and elbow at natural drop angle.",
        },
        "angular / geometric": {
            "design":     "Angular reinterpretation of the Eames shell — modernised, departing from the warm oval.",
            "ergonomics": "Eames arm is primarily visual/structural. Inner contact surface still needs rounding.",
        },
    },

    "armrest_egg": {
        "round / organic": {
            "design":     "Classic cocoon silhouette — unbroken oval wrapping the sitter completely.",
            "ergonomics": "Organic inner surface distributes back and side contact. Shell depth determines neck support.",
        },
        "angular / geometric": {
            "design":     "Angular egg shell — futuristic, bold departure from Jacobsen's continuous oval.",
            "ergonomics": "Sharp outer edges don't contact body. Concern is inner surface profile and shell opening angle.",
        },
    },

    "lumbar_support": {
        "round / organic": {
            "design":     "A sculpted lumbar form — the shape communicates ergonomic intent and care.",
            "ergonomics": "Most effective form. Verify curve radius matches intended user population.",
        },
        "angular / geometric": {
            "design":     "A hard-edged lumbar panel — functional and technical in appearance.",
            "ergonomics": "Sharp-edged pad creates pressure ridge across L3-L5. Front contact face must be rounded and padded.",
        },
    },
}


def get_label_interpretation(label: str, attribute_label: str) -> Optional[dict]:
    part_interps = PART_LABEL_INTERPRETATIONS.get(label.lower())
    if not part_interps:
        return None
    return part_interps.get(attribute_label)


# ---------------------------------------------------------------------------
# RESULT BUILDER (v3)
# ---------------------------------------------------------------------------

def _build_result(
    part_label: str,
    contour: np.ndarray,
    solidity: float,
    aspect_ratio: float,
    w_px: int,
    h_px: int,
    measurements: dict,
    ergo_flags: list,
    px_per_mm: Optional[float]
) -> dict:
    # Compute all descriptors
    smooth_score, smooth_label, smooth_detail = _contour_smoothness(contour, part_label)
    sym_score, sym_label, sym_detail = _measure_symmetry(contour)
    reg_score, reg_label, reg_detail = _edge_regularity(contour)

    curvature   = _describe_curvature(solidity, part_label)
    orientation = _describe_orientation(aspect_ratio, w_px, h_px, part_label)

    # Proportional size
    w_mm = measurements.get("width_mm")
    h_mm = measurements.get("height_mm")
    prop_size = _proportional_size(w_mm, h_mm, w_px, h_px, part_label, px_per_mm)

    # Build smoothness descriptor
    smoothness = {
        "label": smooth_label,
        "detail": smooth_detail,
        "score": smooth_score,
    }

    # Build symmetry descriptor
    symmetry = {
        "label": sym_label,
        "detail": sym_detail,
        "score": sym_score,
    }

    # Build regularity descriptor
    regularity = {
        "label": reg_label,
        "detail": reg_detail,
        "score": reg_score,
    }

    # Build proportional_size descriptor
    proportional_size = {
        "label": prop_size["label"],
        "detail": prop_size["detail"],
    }
    if prop_size.get("width_note"):
        proportional_size["width_note"] = prop_size["width_note"]
    if prop_size.get("height_note"):
        proportional_size["height_note"] = prop_size["height_note"]

    # Attach label-specific interpretations to smoothness, curvature, orientation
    for descriptor in (smoothness, curvature, orientation):
        interp = get_label_interpretation(part_label, descriptor["label"])
        if interp:
            descriptor["design_interpretation"] = interp["design"]
            descriptor["ergonomic_interpretation"] = interp["ergonomics"]

    return {
        "shape": {
            "contour_smoothness": smoothness,
            "curvature":          curvature,
            "orientation":        orientation,
            "proportional_size":  proportional_size,
            "symmetry":           symmetry,
            "edge_regularity":    regularity,
        },
        "measurements":    measurements,
        "ergonomic_flags": ergo_flags,
        "_raw": {
            "smoothness_score":  smooth_score,
            "solidity":          round(solidity, 3),
            "aspect_ratio":      round(aspect_ratio, 3),
            "symmetry_score":    sym_score,
            "regularity_cv":     reg_score,
            "compactness":       measurements.get("compactness"),
            "role":              get_part_role(part_label),
        }
    }


# ---------------------------------------------------------------------------
# PUBLIC API — analyze_geometry
# ---------------------------------------------------------------------------

def analyze_geometry(
    mask_points,
    part_label: str = "unknown",
    seat_metadata: Optional[dict] = None,
    px_per_mm: Optional[float] = None
) -> Optional[dict]:
    """
    Main entry point. Call once per detected part.
    """
    if not mask_points or len(mask_points) < 3:
        return None

    contour   = np.array(mask_points, dtype=np.int32)
    area      = cv2.contourArea(contour)
    hull      = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity  = float(area) / hull_area if hull_area > 0 else 1.0
    _, _, w, h = cv2.boundingRect(contour)
    aspect_ratio = round(w / h, 3) if h > 0 else 1.0

    measurements = _build_measurements(contour, seat_metadata, px_per_mm, part_label)
    ergo_flags   = _ergonomic_flags(part_label, measurements)

    return _build_result(
        part_label, contour, solidity, aspect_ratio,
        int(w), int(h), measurements, ergo_flags, px_per_mm
    )


# ---------------------------------------------------------------------------
# MASK COORDINATE UTILITIES (unchanged from v2)
# ---------------------------------------------------------------------------

def _mask_contour(mask_data) -> Optional[np.ndarray]:
    if not mask_data:
        return None
    try:
        pts = np.array(mask_data, dtype=np.int32)
        return pts if pts.size >= 6 else None
    except Exception:
        return None

def _mask_top_y(mask_data, bbox_fallback=None) -> Optional[int]:
    c = _mask_contour(mask_data)
    if c is not None:
        return int(c.reshape(-1, 2)[:, 1].min())
    return bbox_fallback[1] if bbox_fallback else None

def _mask_bottom_y(mask_data, bbox_fallback=None) -> Optional[int]:
    c = _mask_contour(mask_data)
    if c is not None:
        return int(c.reshape(-1, 2)[:, 1].max())
    return (bbox_fallback[1] + bbox_fallback[3]) if bbox_fallback else None

def _mask_width_px(mask_data, bbox_fallback=None) -> Optional[int]:
    c = _mask_contour(mask_data)
    if c is not None:
        pts = c.reshape(-1, 2)
        return int(pts[:, 0].max() - pts[:, 0].min())
    return bbox_fallback[2] if bbox_fallback else None

def _mask_centroid(mask_data, bbox_fallback=None) -> Optional[tuple]:
    c = _mask_contour(mask_data)
    if c is not None:
        M = cv2.moments(c)
        if M["m00"] != 0:
            return (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
    if bbox_fallback:
        x, y, w, h = bbox_fallback
        return (x + w // 2, y + h // 2)
    return None


# ---------------------------------------------------------------------------
# PUBLIC API — compute_spatial_relations (unchanged from v2)
# ---------------------------------------------------------------------------

def compute_spatial_relations(parts_data: list) -> dict:
    relations = {}
    by_label = {p.get("label", ""): p for p in parts_data}

    def find_by_role(role: str):
        for p in parts_data:
            if get_part_role(p.get("label", "")) == role:
                return p
        return None

    seat    = by_label.get("seat")
    back    = by_label.get("backrest")
    armrest = find_by_role("armrest")
    shell   = find_by_role("shell")
    head    = by_label.get("headrest")

    if seat and back:
        seat_mask = seat.get("mask"); back_mask = back.get("mask")
        seat_bbox = seat.get("bbox"); back_bbox = back.get("bbox")

        seat_w = _mask_width_px(seat_mask, seat_bbox)
        back_w = _mask_width_px(back_mask, back_bbox)

        if seat_w and back_w and seat_w > 0:
            width_ratio = round(back_w / seat_w, 2)
            relations["backrest_to_seat_width_ratio"] = width_ratio
            if width_ratio < 0.85:
                relations["width_ratio_note"] = f"Backrest width is {width_ratio:.0%} of seat width — narrower. Shoulder blades may extend past the backrest edge."
            elif width_ratio > 1.05:
                relations["width_ratio_note"] = f"Backrest is {width_ratio:.0%} of seat width — wider. Throne-like silhouette but adds structural leverage."
            else:
                relations["width_ratio_note"] = f"Backrest width closely matches seat width ({width_ratio:.0%}) — clean, unified proportion."

        back_geom = back.get("geometry", {})
        recline = (back_geom.get("measurements") or {}).get("recline_angle_deg")
        if recline is not None:
            opening = round(90 + recline, 1)
            relations["seat_to_backrest_angle_deg"] = opening
            if 100 <= opening <= 115:
                relations["seat_to_backrest_note"] = f"Opening angle {opening}° — within ergonomic sweet spot (100-115°)."
            elif opening < 100:
                relations["seat_to_backrest_note"] = f"Opening angle {opening}° — very upright. Good for task work but increases disc pressure."
            else:
                relations["seat_to_backrest_note"] = f"Opening angle {opening}° — pronounced recline. User may slide forward."

        seat_centroid = _mask_centroid(seat_mask, seat_bbox)
        back_centroid = _mask_centroid(back_mask, back_bbox)
        if seat_centroid and back_centroid:
            offset = abs(back_centroid[0] - seat_centroid[0])
            relations["backrest_seat_horizontal_offset_px"] = int(offset)
            if offset > 40:
                relations["alignment_note"] = f"Backrest centroid is {offset}px offset from seat — may not be centred."

    if seat and armrest:
        seat_mask = seat.get("mask"); arm_mask = armrest.get("mask")
        seat_bbox = seat.get("bbox"); arm_bbox = armrest.get("bbox")
        arm_label = armrest.get("label", "armrest")

        seat_top = _mask_top_y(seat_mask, seat_bbox)
        arm_top = _mask_top_y(arm_mask, arm_bbox)

        if seat_top is not None and arm_top is not None:
            clearance = seat_top - arm_top
            relations["armrest_above_seat_px"] = int(clearance)
            relations["armrest_label"] = arm_label
            if clearance < 0:
                relations["armrest_height_note"] = f"{arm_label}: top appears below seat surface — verify sketch."
            elif clearance < 30:
                relations["armrest_height_note"] = f"{arm_label}: very low relative to seat — shoulder tension risk."
            else:
                relations["armrest_height_note"] = f"{arm_label}: clearance above seat looks plausible."

    if shell:
        shell_geom = shell.get("geometry", {})
        shell_w = (shell_geom.get("measurements") or {}).get("width_mm")
        if shell_w:
            relations["shell_inner_width_mm"] = shell_w
            relations["shell_width_note"] = (
                f"Egg shell width ~{shell_w}mm — "
                + ("may feel narrow. Adult shoulder breadth is 420-500mm." if shell_w < 450 else "adequate clearance."))

        if seat:
            shell_c = _mask_centroid(shell.get("mask"), shell.get("bbox"))
            seat_c = _mask_centroid(seat.get("mask"), seat.get("bbox"))
            if shell_c and seat_c:
                offset = abs(shell_c[0] - seat_c[0])
                if offset > 50:
                    relations["shell_seat_alignment_note"] = f"Shell centroid is {offset}px offset from seat."

    if back and head:
        back_top = _mask_top_y(back.get("mask"), back.get("bbox"))
        head_bot = _mask_bottom_y(head.get("mask"), head.get("bbox"))
        if back_top is not None and head_bot is not None:
            gap = back_top - head_bot
            relations["headrest_to_backrest_gap_px"] = int(gap)
            relations["headrest_gap_note"] = (
                f"Gap of {gap}px — connecting bracket must bear full lever load."
                if gap > 20 else "Headrest appears flush with backrest top — integrated look.")

    return relations