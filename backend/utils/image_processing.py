

from typing import List, Dict, Tuple, Optional
from collections import defaultdict


def _avg_bbox(bboxes: List[List[float]]) -> List[float]:
    """Compute average normalized bbox."""
    if not bboxes:
        return [0, 0, 0, 0]
    n = len(bboxes)
    sx = sy = sw = sh = 0.0
    for x, y, w, h in bboxes:
        sx += x
        sy += y
        sw += w
        sh += h
    return [sx / n, sy / n, sw / n, sh / n]


def _norm_bbox_to_pixels(norm_xywh: List[float], image_size: Tuple[int, int]) -> Dict[str, int]:
    """Convert normalized bbox (xywh center-based) to pixel coordinates."""
    img_w, img_h = image_size
    x, y, w, h = norm_xywh

    cx = x * img_w
    cy = y * img_h
    pw = max(1, int(w * img_w))
    ph = max(1, int(h * img_h))

    tlx = int(cx - pw / 2)
    tly = int(cy - ph / 2)

    return {
        "top_left_x": tlx,
        "top_left_y": tly,
        "width_px": pw,
        "height_px": ph,
        "area_px_est": pw * ph
    }


def clean_yolo_output(
    raw_yolo: List[Dict],
    image_size: Optional[Tuple[int, int]] = None,
    low_confidence_threshold: float = 0.5
):
    """
    Takes raw YOLO JSON detections and cleans them into:
      - structured (machine readable) summary
      - concise summary text
      - designer assistant summary text
    """

    parts = defaultdict(list)
    low_conf = []

    for det in raw_yolo:
        part_name = det.get("part_name", "unknown")
        conf = float(det.get("confidence", 0.0))
        bbox = det.get("normalized_bbox_xywh", [0, 0, 0, 0])
        area_proxy = int(det.get("mask_pixel_area_proxy", 0))

        entry = {
            "id": det.get("id"),
            "part_name": part_name,
            "confidence": conf,
            "normalized_bbox_xywh": bbox,
            "mask_pixel_area_proxy": area_proxy
        }

        # pixel bbox if image size provided
        if image_size:
            entry["bbox_px"] = _norm_bbox_to_pixels(bbox, image_size)

        parts[part_name].append(entry)

        if conf < low_confidence_threshold:
            low_conf.append(entry)

    structured = {
        "image_size": {"provided": bool(image_size)},
        "parts": [],
        "low_confidence_detections": low_conf,
        "dominant_parts": []
    }

    # Build part summaries
    for pname, entries in parts.items():
        count = len(entries)
        avg_conf = sum(e["confidence"] for e in entries) / count
        total_area = sum(e["mask_pixel_area_proxy"] for e in entries)

        avg_bbox = _avg_bbox([e["normalized_bbox_xywh"] for e in entries])

        part_summary = {
            "part_name": pname,
            "count": count,
            "average_confidence": round(avg_conf, 3),
            "total_mask_pixel_area_proxy": total_area,
            "average_normalized_bbox_xywh": [round(x, 4) for x in avg_bbox],
            "instances": entries,
        }

        if image_size:
            part_summary["average_bbox_px"] = _norm_bbox_to_pixels(avg_bbox, image_size)

        # significance score: area * confidence
        part_summary["significance_score"] = round(total_area * avg_conf, 2)

        structured["parts"].append(part_summary)

    # sort parts by significance descending
    structured["parts"].sort(key=lambda x: x["significance_score"], reverse=True)
    structured["dominant_parts"] = [p["part_name"] for p in structured["parts"][:3]]

    # ------------------------------
    # Build concise text summary
    # ------------------------------
    concise_lines = ["Detected chair parts summary:"]
    for p in structured["parts"]:
        concise_lines.append(
            f"- {p['part_name']}: count={p['count']}, avg_conf={p['average_confidence']}, area_proxy={p['total_mask_pixel_area_proxy']}"
        )
    if low_conf:
        concise_lines.append("\nLow-confidence detections:")
        for e in low_conf:
            concise_lines.append(f"  * {e['part_name']} (id={e['id']}, conf={e['confidence']:.3f})")

    concise_text = "\n".join(concise_lines)

    # ------------------------------
    # Build designer descriptive summary
    # ------------------------------
    designer_lines = ["I analyzed the sketch and detected the following chair components:\n"]

    for p in structured["parts"]:
        area = p["total_mask_pixel_area_proxy"]
        if area >= 30000:
            size_tag = "large"
        elif area >= 8000:
            size_tag = "medium"
        else:
            size_tag = "small"

        designer_lines.append(
            f"• {p['part_name']} — {p['count']} instance(s), {size_tag} (avg confidence {p['average_confidence']})."
        )

    designer_lines.append("\nDominant components: " + ", ".join(structured["dominant_parts"]) + ".\n")

    designer_lines.extend([
        "Notes for design refinement:",
        "- All detected parts can be recolored or receive material/texture assignments.",
        "- Start with the dominant components for strong visual impact.",
        "- If any detections seem incorrect, consider rechecking low-confidence areas.",
        "",
        "Which part would you like to customize first, or do you want stylistic/material recommendations?"
    ])

    designer_text = "\n".join(designer_lines)

    return structured, concise_text, designer_text
