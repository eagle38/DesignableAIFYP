import json
from typing import List, Dict, Any

# === Canonical mapping (original labels -> canonical names) ===
CANONICAL = {
    "Headrest": "headrest",
    "Seat": "seat",
    "Backrest": "backrest",
    "Armrest": "armrest",
    "egg_armrest": "armrest_egg",
    "sofa_armrest": "armrest_sofa",
    "Eames_lounge": "eames_lounge",
    "Eames_base": "eames_base",
    "5_Star_Base": "five_star_base",
    "Caster_Wheel": "caster_wheel",
    "Control_Mechanism": "control_mechanism",
    "Leg_Structure": "leg_structure",
    "Lumbar_Support": "lumbar_support",
    "Wing_Flange": "wing_flanage",
    "Base": "base",
    # labels to ignore (map to None)
    "AH_Label": None, "BH_Label": None, "DA_Label": None,
    "SD_Label": None, "SH_Label": None, "SW_Label": None,
}
SIGNATURE_PARTS = {
    "wing_flanage": "Traditional Wing",
    "eames_base": "Eames Lounge",
    "five_star_base": "Professional Office",
    "armrest_sofa": "Deep Comfort Sofa",
    "armrest_egg": "Mid-Century Egg"
}

# Build a lowercase-keyed mapping for case-insensitive lookups
_CANONICAL_LOWER = {k.lower(): v for k, v in CANONICAL.items()}


def normalize_parts(raw_detections: List[Dict[str, Any]]) -> set:
    """
    Convert the raw detection list (each item is a dict with "part_name", ...) into
    a set of canonical part names. Ignores labels mapped to None or unknown labels.
    Case-insensitive.
    """
    parts = set()
    for obj in raw_detections:
        raw_name = obj.get("part_name", "")
        if not raw_name:
            continue

        # lookup case-insensitively
        canon = _CANONICAL_LOWER.get(raw_name.lower())
        if canon:
            parts.add(canon)
        else:
            # fallback heuristics for common patterns (optional)
            rn = raw_name.lower()
            if "arm" in rn and "egg" in rn:
                parts.add("armrest_egg")
            elif "arm" in rn and "sofa" in rn:
                parts.add("armrest_sofa")
            elif "arm" in rn:
                parts.add("armrest")
            elif "seat" in rn or "cushion" in rn:
                parts.add("seat")
            elif "back" in rn:
                parts.add("backrest")
            # otherwise ignore unknown labels (or you can log them)
    return parts


def classify_chair(parts: set) -> dict:
    """
    Returns a dictionary containing the identified type and 
    whether it is a custom hybrid.
    """
    # Find which signature parts are in this specific sketch
    found_signatures = [SIGNATURE_PARTS[p] for p in parts if p in SIGNATURE_PARTS]
    
    # 1. HYBRID CHECK (Concern 1)
    if len(found_signatures) > 1:
        return {
            "type": "Custom Hybrid Chair",
            "is_hybrid": True,
            "influences": found_signatures
        }
    
    # 2. STANDARD CHAIR CHECK
    if "wing_flanage" in parts:
        return {"type": "Wing Chair", "is_hybrid": False}
    
    if "five_star_base" in parts or "caster_wheel" in parts:
        return {"type": "Ergonomic Office Chair", "is_hybrid": False}
        
    if "eames_base" in parts or "eames_lounge" in parts:
        return {"type": "Eames Lounge Chair", "is_hybrid": False}
    
    if "armrest_sofa" in parts:
        return {"type": "Sofa Armchair", "is_hybrid": False}
    
    if "armrest_egg" in parts:
        return {"type": "Egg Shell chair", "is_hybrid": False}

    return {"type": "Standard Chair", "is_hybrid": False}

  


def build_llama_prompt(image_id: str, parts: set, chair_type: str) -> str:
    """
    Build a simple prompt for LLaMA (kept here for future integration).
    """
    parts_list = ", ".join(sorted(parts))
    return f"""You are design assistant inside the DesignableAI app.

Image ID: {image_id}

Detected chair components: {parts_list}
Predicted chair type: {chair_type}

Your tasks:
1. Confirm or correct the chair type.
2. Describe the chair briefly.
3. Recommend 3 customization ideas (colors, materials, finishes).
4. Keep the output clear and designer-friendly.
"""


def classify_json(raw_json: List[Dict[str, Any]], image_id: str = "uploaded_image") -> Dict[str, Any]:
    """
    Primary function your backend should call.

    Parameters:
      - raw_json: list of detection dicts as produced by your inference (in memory)
      - image_id: optional identifier for the image (filename, uuid, etc.)

    Returns a dict with:
      - canonical_parts: sorted list of canonical part names
      - identified_type: predicted chair type
      - llama_prompt: (optional) prompt string for LLaMA (kept for next step)
    """
    parts = normalize_parts(raw_json)
    chair_type = classify_chair(parts)
    prompt = build_llama_prompt(image_id, parts, chair_type)

    return {
        "canonical_parts": sorted(list(parts)),
        "identified_type": chair_type,
        "llama_prompt": prompt # SHOULD I REMOVE THIS?
    }


# Backwards-compatible helper: accepts a path to a JSON file (keeps your test flow)
def process(json_path: str, image_id: str = "uploaded_image") -> Dict[str, Any]:
    """
    Load a saved JSON file (detected parts) and classify it.
    """
    with open(json_path, "r") as f:
        raw = json.load(f)
    return classify_json(raw, image_id=image_id)


if __name__ == "__main__":
    # legacy test runner:
    out = process("detected_chair_parts.json")
    print(json.dumps(out, indent=2))
