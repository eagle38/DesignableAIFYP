"""
main.py — DesignableAI v2.2
==========================
FastAPI backend with three endpoints:

  POST /analyze-chair     (multipart file) → Full pipeline
  POST /analyze-chair     (JSON body)      → Chat follow-up
  POST /recalculate-geometry               → Re-run geometry on modified masks
  POST /ai-feedback                        → LLM assessment of user modifications
"""

import uvicorn
import tempfile
import os
import uuid
import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from visions_utils import ocr_extract_lines, parse_measurements_from_lines
from yolov8_inference import run_inference_on_image
from chair_classification import normalize_parts, classify_chair, _CANONICAL_LOWER
from table_classification import normalize_table_parts, classify_table, build_table_prompt_context
from geometry_analyzer import (
    analyze_geometry,
    compute_px_per_mm,
    compute_spatial_relations,
    get_part_role,
)
from prompt_builder import build_expert_prompt, detect_phase, build_modification_feedback_prompt
from gemini_client import call_designable_ai


_TABLE_CANONICAL_LOWER = {
    "table_top": "table_top",
    "tabletop": "table_top",
    "top": "table_top",
    "surface": "table_top",
    "deck": "table_top",
    "leg": "leg",
    "legs": "leg",
    "table_leg": "leg",
    "support": "leg",
    "post": "leg",
    "apron": "apron",
    "table_apron": "apron",
    "skirt": "apron",
    "frieze": "apron",
    "pedestal": "pedestal",
    "column": "pedestal",
    "center_post": "pedestal",
    "stretcher": "stretcher",
    "cross_brace": "stretcher",
    "strut": "stretcher",
    "trestle": "stretcher",
}

app = FastAPI(title="DesignableAI v2.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _contour_bbox(mask_data) -> tuple:
    try:
        pts = np.array(mask_data, dtype=np.int32)
        if pts.size == 0: return None
        x, y, w, h = cv2.boundingRect(pts)
        return (x, y, w, h)
    except Exception:
        return None


def _extract_seat_meta(detections: list) -> dict:
    for det in detections:
        mask_data = det.get("mask")
        if det.get("part_name", "").lower() == "seat" and mask_data:
            try:
                pts = np.array(mask_data, dtype=np.int32)
                if pts.size > 0:
                    _, _, w, h = cv2.boundingRect(pts)
                    return {"height": h, "width": w}
            except Exception:
                pass
    return {}


def _canonicalize_part_name(raw_name: str, furniture_type: str) -> Optional[str]:
    if not raw_name:
        return None

    key = raw_name.lower().strip().replace(" ", "_").replace("-", "_")
    while "__" in key:
        key = key.replace("__", "_")

    if furniture_type == "table":
        direct = _TABLE_CANONICAL_LOWER.get(key)
        if direct:
            return direct

        candidates = [key]
        if key.endswith("ss"):
            candidates.append(key[:-1])
        if key.endswith("s"):
            candidates.append(key[:-1])
        if key.startswith("table_"):
            stripped = key[len("table_"):]
            candidates.append(stripped)
            if stripped.endswith("s"):
                candidates.append(stripped[:-1])

        for candidate in candidates:
            mapped = _TABLE_CANONICAL_LOWER.get(candidate)
            if mapped:
                return mapped

        # Heuristic fallback for noisy detector labels
        if "top" in key or "tabletop" in key or "surface" in key or "deck" in key:
            return "table_top"
        if "leg" in key or "support" in key:
            return "leg"
        if "apron" in key or "skirt" in key or "frieze" in key or "trim" in key:
            return "apron"
        if "pedestal" in key or "column" in key or "center_post" in key:
            return "pedestal"
        if "stretcher" in key or "brace" in key or "strut" in key or "trestle" in key:
            return "stretcher"
        return None

    return _CANONICAL_LOWER.get(key)


# ---------------------------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------------------------

class RecalcPart(BaseModel):
    label: str
    mask: List[List[float]]
    scale_x: float = 1.0
    scale_y: float = 1.0

class RecalcRequest(BaseModel):
    parts: List[RecalcPart]
    px_per_mm: Optional[float] = None
    seat_meta: Optional[Dict[str, Any]] = None

class ModificationEntry(BaseModel):
    label: str
    changes: Dict[str, Any]
    original_measurements: Dict[str, Any] = {}
    new_measurements: Dict[str, Any] = {}
    original_flags: List[Dict[str, Any]] = []
    new_flags: List[Dict[str, Any]] = []

class AIFeedbackRequest(BaseModel):
    session_id: str = "visualizer"
    chair_type: str = "Unknown"
    is_hybrid: bool = False
    influences: List[str] = []
    modifications: List[ModificationEntry]
    classification_data: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.post("/analyze-chair")
async def analyze_chair(request: Request, file: UploadFile = None, furniture_type: str = "chair"):

    # ── CHAT FOLLOW-UP ──────────────────────────────────────────────────
    if file is None:
        body             = await request.json()
        user_message     = body.get("message", "")
        session_id       = body.get("session_id", "default_user")
        current_phase    = body.get("phase", "ANALYSIS")
        analysis_data    = body.get("classification_data", {})

        if not user_message:
            raise HTTPException(status_code=400, detail="No message provided.")

        current_phase = detect_phase(user_message, current_phase)

        prompt_payload = build_expert_prompt(
            analysis_data,
            current_phase=current_phase,
            is_followup=True,
            user_message=user_message,
        )

        assistant_reply = call_designable_ai(session_id, prompt_payload)

        return {
            "assistant_reply": assistant_reply,
            "phase":           current_phase,
            "session_id":      session_id,
        }

    # ── IMAGE UPLOAD ─────────────────────────────────────────────────────
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        tmp.write(await file.read())

    try:
        selected_type = (furniture_type or "chair").strip().lower()
        if selected_type not in {"chair", "table"}:
            raise HTTPException(status_code=400, detail="furniture_type must be 'chair' or 'table'.")

        ocr_lines    = ocr_extract_lines(temp_path)
        measurements = parse_measurements_from_lines(ocr_lines)
        detections   = run_inference_on_image(temp_path, conf_thresh=0.25, furniture_type=selected_type)
        seat_meta    = _extract_seat_meta(detections)
        px_per_mm    = compute_px_per_mm(measurements, seat_meta)
        
        if selected_type == "chair":
            parts_set = normalize_parts(detections)
            classification = classify_chair(parts_set)
            identified_type = classification["type"]
            is_hybrid       = classification["is_hybrid"]
            influences      = classification.get("influences", [])
        else:
            parts_set = normalize_table_parts(detections)
            table_type, confidence = classify_table(parts_set)
            identified_type = table_type
            is_hybrid       = False
            influences      = []

        parts_with_traits = []
        parts_for_spatial = []

        img = cv2.imread(temp_path)
        img_h, img_w = img.shape[:2] if img is not None else (800, 600)

        # ── Detect duplicate labels and assign left/right suffixes ────
        # First pass: collect all canonical labels and their mask centroids
        label_instances = {}  # canon -> list of (detection, centroid_x)
        for det in detections:
            raw_name = det.get("part_name", "")
            mask_data = det.get("mask")
            canon = _canonicalize_part_name(raw_name, selected_type)
            if not canon or not mask_data:
                continue
            # Compute centroid X for left/right determination
            pts = np.array(mask_data, dtype=np.int32)
            cx = float(pts.reshape(-1, 2)[:, 0].mean()) if pts.size > 0 else 0
            if canon not in label_instances:
                label_instances[canon] = []
            label_instances[canon].append((det, cx))

        # Second pass: build parts, suffixing duplicates
        for canon, instances in label_instances.items():
            if len(instances) > 1:
                # Sort by centroid X: leftmost first
                instances.sort(key=lambda x: x[1])
                suffixes = ["_left", "_right"] if len(instances) == 2 else [f"_{i+1}" for i in range(len(instances))]
            else:
                suffixes = [""]

            for (det, cx), suffix in zip(instances, suffixes):
                mask_data = det.get("mask")
                unique_label = canon + suffix

                geometry = analyze_geometry(
                    mask_points=mask_data, part_label=canon,  # use canonical for geometry analysis
                    seat_metadata=seat_meta if seat_meta else None,
                    px_per_mm=px_per_mm,
                )
                if geometry is None:
                    continue

                bbox = _contour_bbox(mask_data)

                parts_with_traits.append({
                    "label": unique_label,    # unique label with suffix
                    "canonical": canon,        # original canonical label for role lookup
                    "geometry": geometry,
                    "mask": mask_data,
                    "bbox": list(bbox) if bbox else None,
                })
                parts_for_spatial.append({
                    "label": canon,            # spatial relations use canonical labels
                    "mask": mask_data,
                    "bbox": bbox,
                    "geometry": geometry,
                })

        spatial_relations = compute_spatial_relations(parts_for_spatial)

        analysis_data = {
            "furniture_type":   selected_type,
            "identified_type":   identified_type,
            "is_hybrid":         is_hybrid,
            "influences":        influences,
            "canonical_parts":   sorted(list(parts_set)),
            "parts_with_traits": parts_with_traits,
            "spatial_relations": spatial_relations,
            "measurements":      measurements,
            "scale_factor": {
                "px_per_mm": round(px_per_mm, 4) if px_per_mm else None,
                "anchor":    "SH label + seat bounding box" if px_per_mm else "not established",
            },
            "image_dimensions": { "width": img_w, "height": img_h },
        }

        prompt_payload  = build_expert_prompt(analysis_data, current_phase="ANALYSIS", is_followup=False)
        session_id      = f"{uuid.uuid4()}_{file.filename}_{selected_type}"
        assistant_reply = call_designable_ai(session_id, prompt_payload)

        return {
            "analysis":        analysis_data,
            "assistant_reply": assistant_reply,
            "phase":           "ANALYSIS",
            "session_id":      session_id,
        }

    except Exception as e:
        import traceback
        print(f"[DesignableAI] Pipeline error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/recalculate-geometry")
async def recalculate_geometry(req: RecalcRequest):
    """
    Recalculates geometry for parts after client-side resizing.
    """
    try:
        results = []
        parts_for_spatial = []
        seat_meta = req.seat_meta or {}

        for part in req.parts:
            mask = np.array(part.mask, dtype=np.float64)
            centroid = mask.mean(axis=0)
            scaled = (mask - centroid) * np.array([part.scale_x, part.scale_y]) + centroid
            scaled_list = scaled.astype(np.int32).tolist()

            geometry = analyze_geometry(
                mask_points=scaled_list, part_label=part.label,
                seat_metadata=seat_meta if seat_meta else None,
                px_per_mm=req.px_per_mm,
            )
            if geometry is None: continue

            bbox = _contour_bbox(scaled_list)
            results.append({ "label": part.label, "geometry": geometry, "mask": scaled_list, "bbox": list(bbox) if bbox else None })
            parts_for_spatial.append({ "label": part.label, "mask": scaled_list, "bbox": bbox, "geometry": geometry })

        spatial_relations = compute_spatial_relations(parts_for_spatial)
        return { "parts": results, "spatial_relations": spatial_relations }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")


@app.post("/ai-feedback")
async def ai_feedback(req: AIFeedbackRequest):
    """
    Sends modification data to the LLM for ergonomic assessment.
    Returns a focused analysis of the changes the user made in the visualizer.
    """
    try:
        prompt_payload = build_modification_feedback_prompt(
            chair_type=req.chair_type,
            is_hybrid=req.is_hybrid,
            influences=req.influences,
            modifications=[m.dict() for m in req.modifications],
            classification_data=req.classification_data or {},
        )

        feedback = call_designable_ai(req.session_id, prompt_payload)

        return { "feedback": feedback }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI feedback failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)