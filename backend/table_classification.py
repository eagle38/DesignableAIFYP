# table_classification.py — DesignableAI Table Part Recognition
# ================================================================
# Classify detected table parts and normalize naming conventions
# Parallel to chair_classification.py structure

def normalize_table_parts(detections):
    """
    Normalize table part detections to canonical naming.
    Handles variations in part naming from YOLO output.
    
    Args:
        detections: List of part labels from YOLO (may include typos, variations)
        
    Returns:
        set: Normalized part names in canonical form
    """
    # Mapping from detected labels to normalized canonical names
    PART_NORMALIZATION = {
        # Table top variations
        "top": "table_top",
        "tabletop": "table_top",
        "table_top": "table_top",
        "surface": "table_top",
        "deck": "table_top",
        
        # Leg variations
        "leg": "leg",
        "legs": "leg",
        "table_leg": "leg",
        "support": "leg",
        "post": "leg",
        
        # Apron (skirt) variations
        "apron": "apron",
        "skirt": "apron",
        "table_apron": "apron",
        "trim": "apron",
        "frieze": "apron",
        
        # Pedestal base
        "pedestal": "pedestal",
        "base": "pedestal",
        "column": "pedestal",
        "center_post": "pedestal",
        
        # Cross-braces/stretchers
        "stretcher": "stretcher",
        "cross_brace": "stretcher",
        "strut": "stretcher",
        "brace": "stretcher",
        "trestle": "stretcher",
        
        # Hardware/fasteners (if detected)
        "hardware": "hardware",
        "fastener": "hardware",
        "bolt": "hardware",
        "screw": "hardware",
    }
    
    def _map_fallback(key: str):
        if "top" in key or "tabletop" in key or "surface" in key or "deck" in key:
            return "table_top"
        if "leg" in key or "support" in key or "post" in key:
            return "leg"
        if "apron" in key or "skirt" in key or "frieze" in key or "trim" in key:
            return "apron"
        if "pedestal" in key or "column" in key or "center_post" in key:
            return "pedestal"
        if "stretcher" in key or "brace" in key or "strut" in key or "trestle" in key:
            return "stretcher"
        return None

    normalized = set()
    for detection in detections:
        if isinstance(detection, dict):
            detection = detection.get("part_name", "")
        if not isinstance(detection, str):
            continue
            
        detection_normalized = detection.lower().strip().replace(" ", "_").replace("-", "_")
        while "__" in detection_normalized:
            detection_normalized = detection_normalized.replace("__", "_")

        candidates = [detection_normalized]
        if detection_normalized.endswith("ss"):
            candidates.append(detection_normalized[:-1])
        if detection_normalized.endswith("s"):
            candidates.append(detection_normalized[:-1])
        if detection_normalized.startswith("table_"):
            stripped = detection_normalized[len("table_"):]
            candidates.append(stripped)
            if stripped.endswith("s"):
                candidates.append(stripped[:-1])
        
        mapped = None
        for candidate in candidates:
            mapped = PART_NORMALIZATION.get(candidate)
            if mapped:
                break

        if not mapped:
            mapped = _map_fallback(detection_normalized)

        normalized.add(mapped or detection_normalized)
    
    return normalized


def classify_table(parts_set):
    """
    Classify the table type (Dining, Coffee, Work, Conference, Side, Generic)
    based on detected parts and their characteristics.
    
    This is a heuristic classification. For production, consider:
    - User context ("where did you photograph this?")
    - Proportions (height, length, width from geometry analysis)
    - Style cues (formal vs casual, decorative vs minimal)
    
    Args:
        parts_set: Set of normalized part names from normalize_table_parts()
        
    Returns:
        tuple: (table_type_str, confidence_str)
            table_type_str: "Dining Table", "Coffee Table", "Work Table", etc.
            confidence_str: "high", "medium", "low"
    """
    
    # Rules to classify table type
    # We'll use presence/absence of parts and context clues
    
    has_table_top = "table_top" in parts_set
    has_legs = "leg" in parts_set
    has_apron = "apron" in parts_set
    has_pedestal = "pedestal" in parts_set
    has_stretcher = "stretcher" in parts_set
    
    # CHECK MORE SPECIFIC TYPES FIRST (with more parts) before general types
    
    # Work tables: functional four-leg design with cross-bracing
    # Check this BEFORE dining (which is also legs+apron but without stretchers)
    if has_legs and has_apron and has_stretcher:
        return ("Work Table", "medium")
    
    # Dining tables: four-leg with apron, no visible cross-bracing
    # (Will refine with geometry: TL > 1200mm, TW > 800mm)
    if has_legs and has_apron and has_table_top:
        return ("Dining Table", "medium")
    
    # Coffee tables: low height, minimal base (pedestal)
    # (Will refine with geometry: TH < 500mm)
    if has_pedestal and has_table_top and not has_apron:
        return ("Coffee Table", "medium")
    
    # Side tables: very small, simple pedestal with minimal parts
    # (Will refine with geometry: TL < 600mm, TW < 600mm, minimal hardware)
    if has_pedestal and has_table_top and len(parts_set) <= 2:
        return ("Side Table", "medium")
    
    # Trestle or folding table: visible stretchers between legs
    if has_stretcher and has_table_top and has_legs:
        return ("Work Table", "medium")  # Often used for work/assembly
    
    # If we only detect table top and legs, likely dining
    if has_legs and has_table_top and not has_apron:
        return ("Dining Table", "low")
    
    # Fallback: too ambiguous, return Generic
    return ("Generic Table", "low")


def build_table_prompt_context(identified_type, geometry_data, parts_set):
    """
    Build additional context for LLM prompt based on table type.
    Guides the LLM to focus on type-specific design considerations.
    
    Args:
        identified_type: str, table type (e.g., "Dining Table")
        geometry_data: dict, computed measurements (TH, TL, TW, LH, LS, etc.)
        parts_set: set, detected parts
        
    Returns:
        dict: context dict with type-specific guidance
    """
    
    context = {
        "table_type": identified_type,
        "detected_parts": sorted(list(parts_set)),
        "focus_areas": [],
        "guidance": "",
    }
    
    # Type-specific evaluation focus areas
    type_guidance = {
        "Dining Table": {
            "focus_areas": [
                "Seating capacity (inferred from TL/TW)",
                "Visual weight distribution (base vs top)",
                "Leg spacing (knee clearance for diners)",
                "Joinery quality (mortise/tenon vs bolted)",
                "Top finish (wood grain, color)",
            ],
            "guidance": (
                "Evaluate dining ergonomics: TH 700-760mm (elbow height when seated), "
                "TL scaled for party size (6-8 people: 1800-2400mm), "
                "TW 900-1000mm allows place settings on both sides. "
                "Comment on formality (pedestal=formal, four-leg=traditional, "
                "extendable=family-oriented). Assess visual balance of base to top mass."
            ),
        },
        "Coffee Table": {
            "focus_areas": [
                "Height relative to seating (12-18in lower)",
                "Proportion (2/3 length of seating)",
                "Visual lightness (overhang, base design)",
                "Safety (tipover risk if tall/narrow base)",
                "Functional use (display, storage, footrest)",
            ],
            "guidance": (
                "Evaluate living room context: TH 380-450mm (12-18in lower than seat). "
                "Assess visual balance — coffee tables feel oppressive if top-heavy. "
                "Base should be stable and not block sightlines. "
                "Comment on material (glass=modern, wood=traditional) and function "
                "(open shelf=accessible, closed=tidy)."
            ),
        },
        "Work Table": {
            "focus_areas": [
                "Ergonomic height (700-750mm seated, 1000-1100mm standing)",
                "Surface flatness (critical for precision work)",
                "Leg spacing (knee clearance 300mm minimum)",
                "Stability under load (bracing, joint quality)",
                "Cable management (for electronics)",
            ],
            "guidance": (
                "Evaluate work ergonomics: TH 700-750mm (elbows at 90deg when seated). "
                "Comment on surface flatness (must be <1mm/meter for precision work). "
                "Assess frame rigidity (flex indicates poor bracing). "
                "Check if height is adjustable (better). "
                "Look for cable management (trays, channels). "
                "Evaluate leg spacing for seated comfort (700-800mm ideal)."
            ),
        },
        "Conference Table": {
            "focus_areas": [
                "Length (affects meeting dynamics and sightlines)",
                "Width (accommodates laptops, documents, arm space)",
                "Knee clearance (600mm minimum for long meetings)",
                "Power/data integration (modern conference need)",
                "Visual formality (pedestal=formal, four-leg=collaborative)",
            ],
            "guidance": (
                "Evaluate meeting room context: TL scales with group size "
                "(8 people: 2400-3000mm, 12-16: 3600-6000mm). "
                "TW 1000-1200mm allows comfortable documentation on both sides. "
                "Comment on formality (pedestal=executive, open base=collaborative). "
                "Assess power/data infrastructure (built-in outlets vs daisy-chain). "
                "Evaluate sightline clarity (all participants see all others)."
            ),
        },
        "Side Table": {
            "focus_areas": [
                "Height (550-650mm matches armrest height)",
                "Proportion (small enough to not overwhelm space)",
                "Stability (tipover risk if base too narrow)",
                "Style (matches surrounding furniture)",
                "Functionality (room for lamp + one object)",
            ],
            "guidance": (
                "Evaluate accent role: TH 550-650mm (armrest height for easy reach). "
                "Proportion critical — table should not dominate seating zone. "
                "Check stability of base (20-30% overhang acceptable, over 40% risky). "
                "Assess style fit (decorative vs minimal, matches surrounding pieces). "
                "Comment on material and visual weight."
            ),
        },
        "Generic Table": {
            "focus_areas": [
                "Likely context (dining, work, display, accent)",
                "Overall proportions (infer function from TH/TL/TW ratio)",
                "Base design (pedestal, four-leg, trestle)",
                "Visual balance (top mass vs base support)",
                "Potential uses (what is this table designed for)",
            ],
            "guidance": (
                "Classify based on proportions: table under 500mm is likely accent/coffee; "
                "700-780mm is standard dining/work; very long (2400+mm) is formal/conference. "
                "Assess base design: pedestal suggests display or accent; "
                "four-leg suggests dining/work; trestle suggests assembly/temporary. "
                "Comment on likely primary use case and how well proportioned it is for that."
            ),
        },
    }
    
    if identified_type in type_guidance:
        context["focus_areas"] = type_guidance[identified_type]["focus_areas"]
        context["guidance"] = type_guidance[identified_type]["guidance"]
    
    return context


if __name__ == "__main__":
    # Test normalization
    test_detections = [
        "table_top",
        "leg",
        "APRON",
        "stretcher",
        "hardware",
        "unknown_part",
    ]
    normalized = normalize_table_parts(test_detections)
    print(f"Normalized parts: {normalized}")
    
    # Test classification
    table_type, confidence = classify_table(normalized)
    print(f"Classified as: {table_type} ({confidence} confidence)")
    
    # Test context building
    context = build_table_prompt_context(table_type, {}, normalized)
    print(f"Focus areas: {context['focus_areas']}")
