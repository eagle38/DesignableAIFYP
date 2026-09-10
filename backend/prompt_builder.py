# prompt_builder.py — DesignableAI v2
# =====================================
# Builds the final LLM prompt by injecting:
#   - Structured geometry data with CONFIDENCE TAGS (OCR = high trust, calculated = approximate)
#   - Per-part verbal shape descriptors + real measurements
#   - Ergonomic flags with benchmark values
#   - Spatial relations between parts
#   - Phase-specific instructions (routed via keyword, no extra API call)
#
# The LLM is explicitly forbidden from generic advice.
# Every claim it makes must reference a specific value from the sketch data.

from typing import List, Dict, Any, Optional
from table_summaries import TABLE_SUMMARIES


# ---------------------------------------------------------------------------
# 1. CHAIR SUMMARIES  (construction + ergonomic baselines per type)
# ---------------------------------------------------------------------------
# Kept inline here so the prompt builder is self-contained.
# Add more types as you train new YOLO classes.

CHAIR_SUMMARIES = {
    "Wing Chair": {
        "character": (
            "A high-back upholstered chair with 'wing' flanges projecting forward from the "
            "backrest. Originally designed to shield the sitter from fireplace drafts. The wings "
            "are the structural and visual centrepiece — their angle and height define the whole chair."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (420, 460), "unit": "mm", "note": "Seat height. Too low forces the spine into a C-curve on sit-down."},
            "SD":  {"ideal": (430, 520), "unit": "mm", "note": "Seat depth. Deeper than 520mm means shorter users' lower back won't reach the backrest."},
            "BH":  {"ideal": (600, 750), "unit": "mm", "note": "Back height. Under 600mm won't support shoulders; over 750mm risks pushing head forward."},
            "SW":  {"ideal": (480, 560), "unit": "mm", "note": "Seat width. Narrower than 480mm restricts posture shifts."},
            "AH":  {"ideal": (560, 640), "unit": "mm", "note": "Armrest height from floor. Subtract SH to get clearance above seat (ideal: 180-250mm)."},
        },
        "construction": (
            "The wing-to-backrest joint is the highest-risk point. Wings act as levers — "
            "reinforced steel brackets or deep double-dowel joinery are non-negotiable. "
            "Frame: hardwood (beech or oak) at minimum 32mm section for the backrest rails. "
            "Seat: 8-way hand-tied spring deck or high-density foam (minimum 40kg/m³) over webbing. "
            "Upholstery: wings must be pulled tight at the corner joint to prevent fabric bunching."
        ),
    },
    "Ergonomic Office Chair": {
        "character": (
            "A task chair built around adjustability. The five-star base, caster wheels, and "
            "height-adjustable cylinder are the defining structural elements. Every dimension "
            "should be treated as a variable, not a fixed value."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (400, 520), "unit": "mm", "note": "Adjustable range. Fixed height defeats the purpose of an office chair."},
            "SD":  {"ideal": (380, 480), "unit": "mm", "note": "Shallower than a lounge chair — allows the user to sit forward for active tasks."},
            "BH":  {"ideal": (450, 550), "unit": "mm", "note": "Mid-back support targeting the lumbar curve. Not a full wing-back."},
            "SW":  {"ideal": (440, 520), "unit": "mm", "note": "Wide enough for posture shifts without feeling unstable."},
            "AH":  {"ideal": "adjustable", "unit": "", "note": "Fixed armrests on an office chair are a design error — they prevent the chair from sliding under a desk."},
        },
        "construction": (
            "Pneumatic cylinder must be class 4 (EN 1335 certified) minimum. "
            "Five-star base: 650-700mm diameter for stability, aluminium or reinforced nylon. "
            "Lumbar: adjustable lumbar pad or flexible lumbar zone — not a fixed foam ridge. "
            "Casters: twin-wheel, 50mm diameter minimum for carpet."
        ),
    },
    "Standard Chair": {
        "character": (
            "A general-purpose upholstered chair. The design intent is primarily comfort and "
            "aesthetics — ergonomic precision matters less than in task seating, but the "
            "seat depth and armrest height still need to fit the intended user."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (400, 460), "unit": "mm", "note": "Standard seat height for comfortable entry and exit."},
            "SD":  {"ideal": (450, 530), "unit": "mm", "note": "Deeper than task seating is acceptable for lounge use."},
            "BH":  {"ideal": (500, 650), "unit": "mm", "note": "Mid-to-high back for a standard armchair."},
            "SW":  {"ideal": (480, 580), "unit": "mm", "note": "Generous width for a relaxed seating posture."},
            "AH":  {"ideal": (560, 650), "unit": "mm", "note": "From floor. Subtract SH to verify elbow clearance."},
        },
        "construction": (
            "Frame: hardwood at 28-32mm section. Seat: sinuous spring or foam-over-webbing. "
            "Armrest joints: mortise and tenon, glued and pinned. "
            "Back: fabric or leather over foam — minimum 28kg/m³ seat foam density."
        ),
    },
    "Eames Lounge Chair": {
        "character": (
            "The iconic 670/671 lounge chair and ottoman. Defined by molded plywood shells, "
            "leather cushions, and a die-cast aluminium base. A reclined, low-seated lounge "
            "posture — designed for long reading and listening sessions, not task work."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (350, 420), "unit": "mm", "note": "Low seat height for a lounge posture. Much lower than standard seating."},
            "SD":  {"ideal": (480, 560), "unit": "mm", "note": "Deep seat to support the reclined posture — user is not sitting upright."},
            "BH":  {"ideal": (550, 680), "unit": "mm", "note": "High enough to support the head in the reclined position."},
            "SW":  {"ideal": (500, 580), "unit": "mm", "note": "Generous width for comfortable lounging."},
            "AH":  {"ideal": (480, 560), "unit": "mm", "note": "Low arm height matching the reclined posture — not a task arm height."},
        },
        "construction": (
            "Shells: molded plywood (7-ply walnut or rosewood veneer) — the curve is structural. "
            "Cushions: leather over high-density foam, button-through fixings to the shell. "
            "Base: die-cast aluminium, 5-arm, manual swivel — NOT a gas lift. "
            "Shell-to-shell: aluminium shock mounts allowing micro-movement — critical for the floating feel. "
            "If substituting materials: maintain shell rigidity — a flexible shell collapses the whole system."
        ),
    },
    "Egg Shell chair": {
        "character": (
            "Arne Jacobsen's 1958 Egg chair — a fully upholstered fibreglass shell on a "
            "four-star aluminium swivel base. The shell wraps the sitter completely, providing "
            "acoustic and visual privacy. The silhouette IS the design statement."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (380, 430), "unit": "mm", "note": "Low lounge seat height — entry and exit require more effort than standard seating."},
            "SD":  {"ideal": (500, 580), "unit": "mm", "note": "Deep seat within the shell — depth is constrained by shell opening width."},
            "BH":  {"ideal": (900, 1050), "unit": "mm", "note": "Total shell height from floor — must clear the user's head when seated."},
            "SW":  {"ideal": (800, 950), "unit": "mm", "note": "Total shell width — must allow comfortable shoulder entry."},
            "AH":  {"ideal": (520, 600), "unit": "mm", "note": "Integrated arm within shell — not a separate armrest."},
        },
        "construction": (
            "Shell: fibreglass or moulded plastic — the curve provides structural rigidity. A flat shell is not an egg chair. "
            "Upholstery: fully upholstered inside and out — the inner surface contacts body across back, sides, and head. "
            "Base: four-star aluminium with swivel and tilt mechanism. "
            "Shell-to-base: single central column — entire shell load passes through this joint. "
            "Critical: shell opening width must allow a standard adult (shoulder breadth 420-500mm) to enter and exit comfortably."
        ),
    },
    "Sofa Armchair": {
        "character": (
            "A generously proportioned sofa chair defined by a sofa-style armrest. "
            "The design priority is enveloping comfort — deeper, wider, and softer than "
            "a standard armchair. The arm style (rolled vs track) is the primary aesthetic decision."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (380, 450), "unit": "mm", "note": "Lower than a standard chair — the deep seat requires a lower entry height."},
            "SD":  {"ideal": (520, 620), "unit": "mm", "note": "Intentionally deep for lounging. Risk is slouching — not reaching the backrest."},
            "BH":  {"ideal": (500, 650), "unit": "mm", "note": "Mid-to-high back for a semi-reclined lounge posture."},
            "SW":  {"ideal": (560, 700), "unit": "mm", "note": "Wide seat is central to the sofa-chair identity."},
            "AH":  {"ideal": (520, 620), "unit": "mm", "note": "Sofa arms are typically higher relative to the low seat — verify elbow clearance."},
        },
        "construction": (
            "Frame: hardwood at 32-38mm section — wide seat requires stronger cross-rails than a standard armchair. "
            "Seat: 8-way hand-tied spring deck or high-density pocket springs. "
            "Arm joint: the sofa arm-to-frame joint is the highest-stress point — mortise and tenon plus corner blocks. "
            "A rolled arm requires a separate stuffed arm pad; a track arm is simpler and lower cost."
        ),
    },
    "Unique Design Concept": {
        "character": (
            "A custom or experimental form that doesn't map cleanly to a standard typology. "
            "Analysis should focus on what the geometry actually suggests rather than "
            "comparing it to a canonical reference."
        ),
        "ergonomic_benchmarks": {
            "SH":  {"ideal": (400, 480), "unit": "mm", "note": "General seated comfort range."},
            "SD":  {"ideal": (420, 530), "unit": "mm", "note": "General range — adjust based on intended use."},
            "BH":  {"ideal": (450, 700), "unit": "mm", "note": "Wide range depending on design intent."},
            "SW":  {"ideal": (450, 580), "unit": "mm", "note": "General seated comfort range."},
            "AH":  {"ideal": (550, 650), "unit": "mm", "note": "From floor. Verify elbow clearance vs seat height."},
        },
        "construction": (
            "No standard construction template applies. Focus on identifying the highest-stress "
            "joints in the geometry and specifying joinery accordingly."
        ),
    },
}

# Fallback for unknown types
_DEFAULT_SUMMARY = CHAIR_SUMMARIES["Standard Chair"]


# ---------------------------------------------------------------------------
# 2. PHASE ROUTING  (keyword-based, zero extra API calls)
# ---------------------------------------------------------------------------

PHASE_RULES = {
    "ANALYSIS": {
        "trigger_keywords": [],  # default phase — always the first response
        "objective": "Conduct a precise part-by-part audit of the uploaded sketch.",
        "instruction": """
For EACH detected part, you MUST cover both:
  A) DESIGN IMPACT — what does this geometry say about the chair's visual language,
     style, and character? Reference the specific shape descriptors.
  B) ERGONOMIC IMPACT — how does this geometry affect the human body? Reference the
     specific measurements and any flagged benchmarks. Design and ergonomics are
     SEPARATE discussions — do not mix them.

If this is a HYBRID CHAIR:
  - Open by acknowledging the specific creative decision the user has made
    (e.g. "You've placed a Professional Office base under a Traditional Wing chair").
  - For each part, identify which typology it belongs to and what that means
    in the context of the other typology present.
  - Explicitly call out TYPOLOGY CONFLICTS from the benchmark audit — where a
    single dimension satisfies one chair type but violates the other. The user
    must be told which typology they need to commit to for that dimension.
  - Celebrate the creative ambition while being honest about the structural
    and ergonomic challenges the combination creates.

Structure your response as:
1. Chair type identification — for hybrids, name both influences.
2. One section per part using ## Part Name as the heading.
   Under each: two clearly labelled sub-sections: Design and Ergonomics.
3. Measurement audit: go through each OCR label and compare to the benchmark.
   For hybrids, flag typology conflicts explicitly.
4. One focused next question to move the project forward.
""",
    },
    "ERGONOMICS": {
        "trigger_keywords": [
            "comfort", "comfortable", "ergonomic", "back pain", "posture", "hurt",
            "ache", "support", "pressure", "circulation", "fatigue", "height",
            "depth", "fit", "elderly", "grandmother", "child", "tall", "short",
            "measure", "measurement", "dimension", "size", "adjust"
        ],
        "objective": "Deep-dive into ergonomic fit for the user's stated context.",
        "instruction": """
Focus entirely on the measurements and ergonomic flags from the sketch data.
- Reference EVERY measurement by its exact value (e.g. 'your SD of 560mm').
- Compare each to the benchmark range and explain the physical consequence clearly.
- If the user mentioned a specific person (elderly, child, tall user), relate each 
  measurement directly to that person's likely body dimensions.
- Mark OCR-sourced values as confirmed. Mark calculated values as approximate.
- End with the single most important adjustment they should make first.
""",
    },
    "CONSTRUCTION": {
        "trigger_keywords": [
            "build", "make", "construct", "fabricate", "wood", "material", "foam",
            "fabric", "joint", "joinery", "spring", "frame", "upholster", "workshop",
            "cut", "assemble", "glue", "bolt", "screw", "weld", "manufacture"
        ],
        "objective": "Provide specific construction guidance grounded in the sketch geometry.",
        "instruction": """
Focus on how to physically build this specific chair.
- Reference the detected part geometry when specifying joinery 
  (e.g. 'the sharp wing flange creates high leverage at the joint — use X').
- Specify wood species, section dimensions, foam density, fabric type.
- Call out the highest-risk structural points in this specific design.
- Give an assembly order that accounts for upholstery access.
- Speak like a master carpenter, not a textbook.
""",
    },
    "INTENT_SYNC": {
        "trigger_keywords": [
            "vibe", "feel", "aesthetic", "style", "look", "modern", "traditional",
            "cozy", "minimal", "luxurious", "industrial", "scandinavian", "mid-century",
            "living room", "office", "bedroom", "cafe", "restaurant", "hotel",
            "gift", "who", "for", "purpose", "use"
        ],
        "objective": "Match the design geometry to the user's stated intent or context.",
        "instruction": """
Compare the sketch's actual geometry against the user's stated intent or context.
- Be specific: 'Your sharp armrest edges read as architectural/modern — this 
  contradicts a cozy brief.' Not: 'Sharp edges may not suit all styles.'
- If geometry and intent clash, explain exactly which parts to change and how.
- If they align, confirm it with specific evidence from the sketch data.
- Do not give generic style advice. Every point must reference a detected part.
""",
    },
}


def detect_phase(user_message: str, current_phase: str = "ANALYSIS") -> str:
    """
    Routes the conversation phase using keyword matching.
    No LLM call needed. Returns the most specific matching phase,
    or keeps the current phase if no keywords match.

    Priority order: CONSTRUCTION > ERGONOMICS > INTENT_SYNC > keep current
    """
    msg_lower = user_message.lower()

    # Check in priority order
    for phase in ("CONSTRUCTION", "ERGONOMICS", "INTENT_SYNC"):
        keywords = PHASE_RULES[phase]["trigger_keywords"]
        if any(kw in msg_lower for kw in keywords):
            return phase

    return current_phase


# ---------------------------------------------------------------------------
# 3. DATA FORMATTING  (converts geometry output into LLM-readable text)
# ---------------------------------------------------------------------------

def _confidence_tag(source: str) -> str:
    """Returns a confidence label the LLM is instructed to reference."""
    if source == "ocr":
        return "[CONFIRMED from sketch label]"
    elif source == "calculated":
        return "[APPROXIMATE — calculated from pixel geometry]"
    return "[SOURCE UNKNOWN]"


def _format_measurements(measurements: dict, ocr_measurements: dict, part_label: str) -> str:
    """
    Formats the measurement block for a single part.
    Tags each value with its confidence level.
    """
    lines = []

    # OCR-sourced dimensions (high trust) — only for parts that have a direct label
    # e.g. seat gets SD and SW, backrest gets BH
    PART_TO_OCR_KEYS = {
        "seat":      ["SD", "SW", "SH"],
        "backrest":  ["BH"],
        "armrest":   ["AH"],
        "headrest":  ["BH"],  # proxy
    }

    relevant_ocr = PART_TO_OCR_KEYS.get(part_label.lower().split("_")[0], [])
    for key in relevant_ocr:
        if key in ocr_measurements:
            m = ocr_measurements[key]
            val = m.get("value")
            unit = m.get("unit", "")
            # normalise to mm for display
            if unit.lower() in ("cm", "centimeter", "centimetre"):
                val_mm = round(float(val) * 10)
                lines.append(f"  {key}: {val}{unit} = {val_mm}mm {_confidence_tag('ocr')}")
            elif unit.lower() in ("in", "inch", "inches"):
                val_mm = round(float(val) * 25.4)
                lines.append(f"  {key}: {val}{unit} = {val_mm}mm {_confidence_tag('ocr')}")
            else:
                lines.append(f"  {key}: {val}{unit} {_confidence_tag('ocr')}")

    # Calculated dimensions from pixel geometry
    m = measurements or {}

    if "width_mm" in m:
        lines.append(f"  Width: {m['width_mm']}mm {_confidence_tag('calculated')}")
    elif "width_px" in m:
        lines.append(f"  Width: {m['width_px']}px (no scale factor available) {_confidence_tag('calculated')}")

    if "height_mm" in m:
        lines.append(f"  Height: {m['height_mm']}mm {_confidence_tag('calculated')}")
    elif "height_px" in m:
        lines.append(f"  Height: {m['height_px']}px (no scale factor available) {_confidence_tag('calculated')}")

    if "recline_angle_deg" in m:
        lines.append(f"  Recline angle: ~{m['recline_angle_deg']}° from vertical {_confidence_tag('calculated')}")

    if "inner_edge_angle_deg" in m and m["inner_edge_angle_deg"] is not None:
        lines.append(f"  Sharpest inner corner: ~{m['inner_edge_angle_deg']}° {_confidence_tag('calculated')}")

    if "curvature_radius" in m and m["curvature_radius"] is not None:
        unit = m.get("curvature_radius_unit", "px")
        lines.append(f"  Mean curvature radius: ~{m['curvature_radius']}{unit} {_confidence_tag('calculated')}")

    if "dominant_angle_deg" in m:
        lines.append(f"  Dominant axis angle: {m['dominant_angle_deg']}° {_confidence_tag('calculated')}")

    if "scale_vs_seat" in m and m["scale_vs_seat"] is not None:
        lines.append(f"  Scale vs seat height: {m['scale_vs_seat']}× {_confidence_tag('calculated')}")

    return "\n".join(lines) if lines else "  No measurements available."


def _format_shape(shape: dict) -> str:
    """
    Formats the verbal shape descriptor block for a single part.
    Outputs the generic geometric detail first, then the label-specific
    design and ergonomic interpretations when they exist.
 
    Updated for geometry_analyzer v3 descriptor keys.
    """
    if not shape:
        return "  No shape data available."
 
    lines = []
 
    smoothness = shape.get("contour_smoothness", {})
    curv       = shape.get("curvature", {})
    orient     = shape.get("orientation", {})
    prop_size  = shape.get("proportional_size", {})
    symmetry   = shape.get("symmetry", {})
    regularity = shape.get("edge_regularity", {})
 
    def _fmt(descriptor: dict, field_name: str):
        """Formats one descriptor with its generic detail and label-specific interpretations."""
        if not descriptor:
            return
        lines.append(f"  {field_name}: {descriptor.get('label', '?')}")
        if descriptor.get('detail'):
            lines.append(f"    Geometry: {descriptor['detail']}")
        # Label-specific interpretations
        if "design_interpretation" in descriptor:
            lines.append(f"    DESIGN: {descriptor['design_interpretation']}")
        if "ergonomic_interpretation" in descriptor:
            lines.append(f"    ERGONOMICS: {descriptor['ergonomic_interpretation']}")
 
    # Primary descriptors (with possible label-specific interpretations)
    _fmt(smoothness, "Contour smoothness")
    _fmt(curv,       "Surface curvature")
    _fmt(orient,     "Orientation")
 
    # Proportional size — has width_note and height_note instead of interpretations
    if prop_size:
        lines.append(f"  Proportional size: {prop_size.get('label', '?')}")
        if prop_size.get('detail'):
            lines.append(f"    Assessment: {prop_size['detail']}")
        if prop_size.get('width_note'):
            lines.append(f"    Width: {prop_size['width_note']}")
        if prop_size.get('height_note'):
            lines.append(f"    Height: {prop_size['height_note']}")
 
    # Secondary descriptors (no label-specific interpretations, geometry only)
    if symmetry:
        lines.append(f"  Symmetry: {symmetry.get('label', '?')}")
        if symmetry.get('detail'):
            lines.append(f"    {symmetry['detail']}")
 
    if regularity:
        lines.append(f"  Edge regularity: {regularity.get('label', '?')}")
        if regularity.get('detail'):
            lines.append(f"    {regularity['detail']}")
 
    return "\n".join(lines)
def _format_ergo_flags(flags: list) -> str:
    """Formats ergonomic flags with clear status indicators."""
    if not flags:
        return "  No ergonomic flags for this part."

    lines = []
    status_icons = {"ok": "OK", "warning": "WARNING", "critical": "CRITICAL"}
    for f in flags:
        icon = status_icons.get(f.get("status", ""), "?")
        lines.append(
            f"  [{icon}] {f.get('field', '?').upper()}: "
            f"measured {f.get('measured', '?')} vs benchmark {f.get('benchmark', '?')}"
        )
        lines.append(f"    → {f.get('note', '')}")

    return "\n".join(lines)


def _format_spatial_relations(relations: dict) -> str:
    """Formats the part-to-part spatial relationship block."""
    if not relations:
        return "No spatial relation data available."

    lines = []

    if "seat_to_backrest_angle_deg" in relations:
        lines.append(
            f"Seat-to-backrest opening angle: {relations['seat_to_backrest_angle_deg']}° "
            f"{_confidence_tag('calculated')}"
        )
    if "seat_to_backrest_note" in relations:
        lines.append(f"  → {relations['seat_to_backrest_note']}")

    if "backrest_to_seat_width_ratio" in relations:
        lines.append(
            f"Backrest/seat width ratio: {relations['backrest_to_seat_width_ratio']} "
            f"{_confidence_tag('calculated')}"
        )
    if "width_ratio_note" in relations:
        lines.append(f"  → {relations['width_ratio_note']}")

    if "armrest_above_seat_px" in relations:
        arm_label = relations.get("armrest_label", "armrest")
        lines.append(
            f"{arm_label} clearance above seat: {relations['armrest_above_seat_px']}px "
            f"{_confidence_tag('calculated')}"
        )
    if "armrest_height_note" in relations:
        lines.append(f"  → {relations['armrest_height_note']}")

    if "shell_inner_width_mm" in relations:
        lines.append(
            f"Egg shell inner width: {relations['shell_inner_width_mm']}mm "
            f"{_confidence_tag('calculated')}"
        )
    if "shell_width_note" in relations:
        lines.append(f"  → {relations['shell_width_note']}")

    if "headrest_gap_note" in relations:
        lines.append(f"Headrest-to-backrest connection: {relations['headrest_gap_note']}")

    return "\n".join(lines) if lines else "No relational data computed."


def _format_ocr_benchmark_audit(
    ocr_measurements: dict,
    chair_type: str,
    furniture_type: str = "chair"
) -> str:
    """
    Produces a full measurement audit comparing every OCR label to its benchmark.
    This is the section the LLM uses for the ERGONOMICS phase.
    
    Parameters
    ----------
    ocr_measurements : dict
        OCR-detected measurements from the image
    chair_type : str
        Identified type (chair, table type, etc.)
    furniture_type : str
        "chair" or "table" to route to appropriate summaries
    """
    if furniture_type == "table":
        summary = TABLE_SUMMARIES.get(chair_type, TABLE_SUMMARIES.get("Generic Table"))
    else:
        summary = CHAIR_SUMMARIES.get(chair_type, _DEFAULT_SUMMARY)
    
    benchmarks = summary.get("ergonomic_benchmarks", {})

    if not ocr_measurements:
        return "No OCR measurement labels detected in this sketch."

    lines = ["Measurement audit vs ergonomic benchmarks:"]

    def to_mm(value, unit):
        unit = (unit or "").lower().strip()
        if unit in ("mm",):
            return float(value)
        if unit in ("cm", "centimeter", "centimetre"):
            return float(value) * 10
        if unit in ("in", "inch", "inches", '"'):
            return float(value) * 25.4
        return float(value)  # assume mm as fallback

    for key, m in ocr_measurements.items():
        if key == "other":
            continue
        val_raw = m.get("value")
        unit = m.get("unit", "mm")
        if val_raw is None:
            continue

        val_mm = to_mm(val_raw, unit)
        bench = benchmarks.get(key)

        if bench:
            ideal = bench.get("ideal")
            b_unit = bench.get("unit", "mm")
            note = bench.get("note", "")

            if isinstance(ideal, tuple):
                lo, hi = ideal
                if val_mm < lo:
                    status = "WARNING — below ideal range"
                    diff = round(lo - val_mm)
                    detail = f"{diff}mm below the minimum. {note}"
                elif val_mm > hi:
                    status = "CRITICAL — above ideal range"
                    diff = round(val_mm - hi)
                    detail = f"{diff}mm above the maximum. {note}"
                else:
                    status = "OK — within range"
                    detail = note
                lines.append(
                    f"\n  {key} = {val_raw}{unit} ({val_mm:.0f}mm) | "
                    f"Ideal: {lo}–{hi}mm | {status}"
                )
                lines.append(f"    → {detail}")
            else:
                # Non-numeric benchmark (e.g. "adjustable")
                lines.append(
                    f"\n  {key} = {val_raw}{unit} | Note: {ideal} — {note}"
                )
        else:
            furniture_label = "table" if furniture_type == "table" else "chair"
            lines.append(f"\n  {key} = {val_raw}{unit} — no benchmark defined for this {furniture_label} type.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. SYSTEM PROMPT TEMPLATE
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are the Lead Furniture Architect at DesignableAI.

CORE BEHAVIOUR:
- You speak like a senior maker in a workshop who has just looked at the user's actual sketch.
- You are FORBIDDEN from giving generic furniture advice. Every single claim you make 
  must reference a specific value, shape descriptor, or flag from [SKETCH DATA] below.
- When you cite a measurement, always state whether it is CONFIRMED (from OCR label) 
  or APPROXIMATE (calculated from pixels). This is critical for the user's trust.
- Discuss DESIGN IMPACT and ERGONOMIC IMPACT as separate topics for each part. 
  They are different: design is about visual language and character; ergonomics is 
  about how the geometry affects the human body.
- Be direct. If a dimension is problematic, say so and give the specific fix.
- Use plain workshop language: 'pressure point', 'leverage', 'clearance', 'bottoming out'.
  Avoid: 'aesthetic typology', 'nuanced interplay', 'sophisticated tension'.
- End every response with exactly ONE focused question or suggested next action.

CURRENT PHASE: {phase}
PHASE OBJECTIVE: {phase_objective}
PHASE INSTRUCTIONS:
{phase_instruction}

---
[SKETCH DATA — every value below came from the user's actual uploaded sketch]

{sketch_data}
---
"""


# ---------------------------------------------------------------------------
# 5. SKETCH DATA BLOCK BUILDER
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# INFLUENCE → CHAIR_SUMMARIES KEY
# Maps the string values from SIGNATURE_PARTS (chair_classification.py)
# to the exact keys used in CHAIR_SUMMARIES above.
# When a new chair type is added to SIGNATURE_PARTS, add it here too.
# ---------------------------------------------------------------------------
INFLUENCE_TO_SUMMARY_KEY = {
    "Traditional Wing":    "Wing Chair",
    "Eames Lounge":        "Eames Lounge Chair",
    "Professional Office": "Ergonomic Office Chair",
    "Deep Comfort Sofa":   "Sofa Armchair",
    "Mid-Century Egg":     "Egg Shell chair",
}


def _get_hybrid_character(influences: list) -> str:
    """
    Builds a hybrid character description by combining the character strings
    of both influences and explicitly naming the creative tension between them.
    """
    if not influences:
        return "A hybrid chair blending multiple typologies."

    descs = []
    for inf in influences:
        key = INFLUENCE_TO_SUMMARY_KEY.get(inf)
        if key and key in CHAIR_SUMMARIES:
            descs.append(f"{inf}: {CHAIR_SUMMARIES[key]['character']}")

    tension_notes = {
        frozenset(["Traditional Wing", "Professional Office"]): (
            "HYBRID TENSION: Wing chairs are formal lounge pieces; office chairs are task-oriented "
            "and adjustable. The key conflict is between a fixed upright wing structure and the "
            "ergonomic need for recline and lumbar adjustment. Every part must be evaluated against "
            "both intents — does it serve the lounge character or the task function?"
        ),
        frozenset(["Traditional Wing", "Deep Comfort Sofa"]): (
            "HYBRID TENSION: Both typologies are comfort-focused but differ in arm language. "
            "The wing creates vertical enclosure; the sofa arm creates horizontal mass. "
            "The visual competition between wing height and arm width is the central design challenge."
        ),
        frozenset(["Traditional Wing", "Mid-Century Egg"]): (
            "HYBRID TENSION: Both provide enclosure but through opposite geometries — "
            "the wing uses flat planes projecting forward; the egg uses a continuous curved shell. "
            "This is a high-ambition hybrid. The junction between shell and wing is structurally complex."
        ),
        frozenset(["Traditional Wing", "Eames Lounge"]): (
            "HYBRID TENSION: Wing chairs sit upright; Eames lounges recline low. "
            "The seat height and backrest angle will be the most contested dimensions — "
            "one typology pulls toward 430mm SH, the other toward 380mm."
        ),
        frozenset(["Professional Office", "Deep Comfort Sofa"]): (
            "HYBRID TENSION: Office chairs prioritise adjustability and task posture; "
            "sofa chairs prioritise fixed comfort and visual weight. "
            "A sofa arm on an office base creates a strong visual contrast — "
            "evaluate whether the seat depth serves task work or lounging."
        ),
        frozenset(["Mid-Century Egg", "Eames Lounge"]): (
            "HYBRID TENSION: Both are mid-century icons but their structures are fundamentally different — "
            "the egg is a single enveloping shell; the Eames lounge is a multi-piece plywood system. "
            "Combining them requires deciding which structural logic governs."
        ),
        frozenset(["Deep Comfort Sofa", "Mid-Century Egg"]): (
            "HYBRID TENSION: The sofa arm adds horizontal visual mass to the base of a form "
            "that is defined by vertical enclosure. This is an unusual combination — "
            "the bolster arm will widen the visual footprint significantly."
        ),
    }

    influence_set = frozenset(influences[:2])
    tension = tension_notes.get(influence_set, (
        f"HYBRID TENSION: This design blends {' and '.join(influences)}. "
        "Evaluate each part against both typologies and flag where they conflict."
    ))

    result = "\n".join(descs)
    result += f"\n{tension}"
    return result


def _get_hybrid_benchmark_audit(ocr_measurements: dict, influences: list) -> str:
    """
    For hybrid chairs: runs the benchmark audit against all influencing chair types
    and surfaces conflicts where the two typologies disagree on ideal values.
    """
    if not ocr_measurements:
        return "No OCR measurement labels detected in this sketch."

    def to_mm(value, unit):
        unit = (unit or "").lower().strip()
        if unit in ("mm",): return float(value)
        if unit in ("cm", "centimeter", "centimetre"): return float(value) * 10
        if unit in ("in", "inch", "inches", '"'): return float(value) * 25.4
        return float(value)

    lines = ["Hybrid measurement audit — each label checked against ALL influencing typologies:"]

    for key, m in ocr_measurements.items():
        if key == "other":
            continue
        val_raw = m.get("value")
        unit    = m.get("unit", "mm")
        if val_raw is None:
            continue
        val_mm = to_mm(val_raw, unit)

        lines.append(f"\n  {key} = {val_raw}{unit} ({val_mm:.0f}mm)")

        results_per_type = []
        for inf in influences:
            summary_key = INFLUENCE_TO_SUMMARY_KEY.get(inf)
            if not summary_key:
                continue
            summary = CHAIR_SUMMARIES.get(summary_key, {})
            bench   = summary.get("ergonomic_benchmarks", {}).get(key)
            if not bench:
                continue
            ideal = bench.get("ideal")
            note  = bench.get("note", "")
            if isinstance(ideal, tuple):
                lo, hi = ideal
                if val_mm < lo:
                    status = f"WARNING — {round(lo - val_mm)}mm below {inf} minimum ({lo}mm)"
                elif val_mm > hi:
                    status = f"CRITICAL — {round(val_mm - hi)}mm above {inf} maximum ({hi}mm)"
                else:
                    status = f"OK for {inf} ({lo}–{hi}mm)"
                results_per_type.append(f"    [{inf}]: {status} — {note}")
            else:
                results_per_type.append(f"    [{inf}]: {ideal} — {note}")

        if results_per_type:
            lines.extend(results_per_type)
            # Flag direct conflicts between the two typologies
            if len(results_per_type) == 2:
                r1, r2 = results_per_type
                one_ok  = "OK for" in r1
                two_ok  = "OK for" in r2
                one_warn = "WARNING" in r1 or "CRITICAL" in r1
                two_warn = "WARNING" in r2 or "CRITICAL" in r2
                if (one_ok and two_warn) or (one_warn and two_ok):
                    lines.append(
                        f"    *** TYPOLOGY CONFLICT: This value satisfies one chair type "
                        f"but violates the other. The user must decide which typology governs this dimension. ***"
                    )
        else:
            lines.append(f"    No benchmark defined for this label across detected influences.")

    return "\n".join(lines)


def _build_sketch_data_block(
    analysis_data: dict,
    ocr_measurements: dict,
) -> str:
    """
    Assembles the full [SKETCH DATA] block that gets injected into the system prompt.
    This is the single source of truth the LLM reasons from.
    """
    chair_type = analysis_data.get("identified_type", "Unknown")
    furniture_type = analysis_data.get("furniture_type", "chair").lower()
    is_hybrid  = analysis_data.get("is_hybrid", False)
    influences = analysis_data.get("influences", [])
    parts      = analysis_data.get("parts_with_traits", [])
    relations  = analysis_data.get("spatial_relations", {})

    # Route to appropriate summaries based on furniture type
    if furniture_type == "table":
        summary = TABLE_SUMMARIES.get(chair_type, TABLE_SUMMARIES.get("Generic Table"))
    else:
        summary = CHAIR_SUMMARIES.get(chair_type, _DEFAULT_SUMMARY)

    lines = []

    # ── Furniture type ──────────────────────────────────────────────────────
    furniture_label = furniture_type.upper() if furniture_type == "table" else "CHAIR"
    lines.append(f"{furniture_label} TYPE: {chair_type}")
    if is_hybrid:
        lines.append(f"HYBRID: Yes")
        lines.append(f"INFLUENCES: {', '.join(influences)}")
        lines.append(f"CHARACTER:\n{_get_hybrid_character(influences)}")
    else:
        lines.append(f"CHARACTER: {summary['character']}")
    lines.append("")

    # ── Per-part data ───────────────────────────────────────────────────────
    # Chair-type context notes — tells the LLM what the same geometry means
    # differently depending on the chair/table this part belongs to.
    CHAIR_TYPE_PART_CONTEXT = {
        "Wing Chair": {
            "armrest":            "On a wing chair, armrests are secondary to the wings and backrest. Their height relative to the seat matters more than their width.",
            "armrest_sofa":       "On a wing chair, a sofa-style arm creates an unusual hybrid — the bolster arm competes visually with the wings. Evaluate whether this is intentional.",
            "wing_flanage":       "On a wing chair, the wings ARE the chair. Their geometry defines the entire design language and carries the highest structural risk.",
            "backrest":           "On a wing chair, the backrest is the structural backbone connecting the wings. Its height and recline set the overall posture.",
            "seat":               "On a wing chair, the seat depth is the most critical ergonomic dimension — wing chairs are notorious for seats that are too deep for the user to reach the backrest.",
            "leg_structure":      "On a wing chair, legs are largely hidden under upholstery — their structural section matters more than their visual form.",
        },
        "Ergonomic Office Chair": {
            "armrest":            "On an office chair, wide fixed armrests are a functional conflict — they prevent the chair from sliding under a desk. Adjustability is more important than proportion.",
            "five_star_base":     "On an office chair, the five-star base diameter is a safety specification (EN 1335 minimum 650mm), not an aesthetic choice.",
            "backrest":           "On an office chair, the backrest should target the lumbar zone specifically — a high fixed back that cannot recline is a design error for task seating.",
            "seat":               "On an office chair, a seat that is too deep prevents the user from sitting back properly during active tasks. Shallow is better than deep here.",
            "lumbar_support":     "On an office chair, lumbar support is the most ergonomically critical component. Height-adjustability is strongly preferred over a fixed position.",
            "control_mechanism":  "On an office chair, the control mechanism determines the entire recline behaviour. Its geometry affects the tilt axis location relative to the user's hip.",
        },
        "Eames Lounge Chair": {
            "eames_lounge_cushion": "On an Eames lounge chair, the arm cushion IS the character — its curve and proportion directly reference the 670/671. Deviation from the organic form is a significant design departure.",
            "eames_base":           "On an Eames lounge, the base spread defines the floating visual footprint. A base narrower than the shell width will make the chair feel unstable.",
            "backrest":             "On an Eames lounge, the backrest recline is steep by intention — this chair is for relaxing, not task work. Ergonomic concerns shift from lumbar support to head and shoulder comfort.",
            "seat":                 "On an Eames lounge, the seat is low and reclined. Seat height (SH) will typically be 350-400mm — lower than standard seating. Entry and exit require more physical effort.",
        },
        "Egg Shell chair": {
            "armrest_egg":  "This IS the egg chair — the shell silhouette is the entire design. Every geometric attribute (height, curvature, solidity) defines how enveloping, private, and dramatic the chair reads.",
            "eames_base":   "On an egg chair, the base must balance a tall, heavy shell. Stability during the user leaning sideways into the shell is the primary structural concern.",
            "seat":         "On an egg chair, the seat is contained within the shell — its depth is constrained by the shell opening. Entry and exit usability depends on the shell opening width.",
        },
        "Sofa Armchair": {
            "armrest_sofa": "On a sofa, the arm style defines the entire aesthetic register — rolled arm signals traditional, track arm signals contemporary. This is the highest-impact design decision on a sofa.",
            "seat":         "On a sofa, seat depth is intentionally generous (520-580mm) to allow lounging. The ergonomic risk is the opposite of a task chair — it is too easy to slouch.",
            "backrest":     "On a sofa, the backrest is typically softer and more reclined than a chair. Lumbar support comes from cushion density rather than backrest geometry.",
        },
        "Standard Chair": {
            "armrest":      "On an unclassified design, evaluate the armrest purely against user intent — is this chair for tasks, lounging, or dining? The answer changes what wide or tall means.",
            "backrest":     "On an unclassified design, the backrest geometry is the strongest signal of intent. Its recline angle tells you whether this is task, lounge, or dining seating.",
            "seat":         "On an unclassified design, use the seat proportions and the SH label to infer intent. A high narrow seat suggests dining or bar seating; a low wide seat suggests lounge.",
        },
        "Dining Table": {
            "top":          "On a dining table, the top surface defines seating capacity and place setting layout. Length (TL) and width (TW) determine how many diners comfortably fit. Top thickness signals quality and load capacity.",
            "leg":          "Dining table legs are critical for both comfort and stability. Leg spacing (LS) and height (LH) determine knee clearance under the table and overall visual proportions.",
            "apron":        "The apron (frame connecting legs to top) is the structural backbone. Its depth and stiffness prevent racking when diners lean on the table or when extending/collapsing mechanisms operate.",
            "pedestal":     "A pedestal base offers maximum legroom but requires heavy reinforcement. Center of gravity and base-to-top mass ratio determine visual balance and stability during dynamic use.",
            "stretcher":    "Cross-bracing between legs resists racking and lateral movement. On dining tables, stretchers are often hidden; visible stretchers suggest a more traditional or industrial aesthetic.",
        },
        "Coffee Table": {
            "top":          "On a coffee table, the top is the visual focus — proportions and material directly impact the room's aesthetic. Top overhang (15-25%) affects both visual lightness and tipover safety.",
            "leg":          "Coffee table legs should be proportional to top mass. Spindly legs under a heavy top feel precarious; sturdy legs under a light top look clumsy. Legroom is less critical than on dining tables.",
            "pedestal":     "A pedestal base is common for coffee tables, offering visual lightness. Stability is critical — the base must be wider than top overhang to prevent tipover, especially in homes with children or pets.",
        },
        "Work Table": {
            "top":          "On a work table, surface flatness is paramount — no more than 1mm deviation per meter for precision work. Thickness (28-38mm) and material (hardwood preferred) directly affect flatness and durability under tools.",
            "leg":          "Work table legs must be rigid — flex indicates inadequate bracing and will degrade precision work. Bolt-on joints (grade 8 fasteners) are preferred over mortise-and-tenon for work tables.",
            "apron":        "The apron must be substantial (50-80mm depth) and cross-braced to minimize flex under dynamic loads. Cables may be routed through the apron for power and data.",
            "stretcher":    "Heavy-duty cross-bracing is mandatory for work tables — stretchers carry peak loads from tools and assembly forces. Visible or hidden, their stiffness is the most critical structural attribute.",
        },
        "Conference Table": {
            "top":          "On a conference table, length (TL) affects meeting dynamics — very long tables create formality and hierarchy. Width (TW) must accommodate laptops, documents, and arm space on both sides (1000-1200mm ideal).",
            "leg":          "Conference table legs should be minimal visual intrusion — a twin-pedestal or hidden base keeps sightlines clear. Stability must handle dynamic loads from people leaning and shifting during meetings.",
            "pedestal":     "Twin-pedestal bases are conference standard — they offer legroom and psychological openness compared to four-leg bases. Center of gravity is critical for a long table.",
            "stretcher":    "Conference tables rarely have visible stretchers — modern conference design favors clean lines. Internal bracing may be substantial but must be hidden within the base or pedestal.",
        },
        "Side Table": {
            "top":          "On a side table, proportions are the entire aesthetic — the top must be proportional to the base and the room. Overhang of 20-30% creates visual lightness; over 40% creates tipover risk.",
            "pedestal":     "Pedestal-based side tables must have a base diameter of 30-50% of the top diameter for visual stability. Center of gravity is critical — if the base is too narrow, the table will feel precarious.",
        },
        "Generic Table": {
            "top":          "On a generic table, infer function from top dimensions. Very small (400-600mm) suggests accent/side; medium (900-1000mm width) suggests dining; large/long suggests conference or work.",
            "leg":          "Leg spacing and height infer the table's primary use. Wide spacing (700-800mm) suggests dining focus; narrow (400-500mm) suggests work/stability focus.",
            "apron":        "Presence and depth of apron indicate structural intent. Deep apron (80-100mm) suggests dining or work; minimal apron suggests accent table.",
            "pedestal":     "Pedestal base suggests either display focus (small table) or legroom emphasis (large dining table). Base-to-top proportion is the key visual balance metric.",
            "stretcher":    "Visible stretchers suggest traditional, workshop, or industrial aesthetic. On modern designs, stretchers are typically hidden.",
        },
    }

    lines.append("PARTS DETECTED:")
    if furniture_type == "table":
        lines.append("NOTE: For tables, prioritize OCR-backed dimensions and explicit ergonomic/structural flags. Treat contour-shape descriptors as low-confidence visual cues.")

    # Build furniture context lookup — for hybrids, merge context from all influences
    if is_hybrid:
        # Merge context dicts from all influencing types
        # If two influences both have context for the same part, concatenate both
        merged_context: dict = {}
        for inf in influences:
            summary_key = INFLUENCE_TO_SUMMARY_KEY.get(inf, inf)
            inf_context = CHAIR_TYPE_PART_CONTEXT.get(summary_key, {})
            for part_key, ctx_text in inf_context.items():
                if part_key in merged_context:
                    merged_context[part_key] += f" | From {inf} perspective: {ctx_text}"
                else:
                    merged_context[part_key] = f"[{inf}] {ctx_text}"
        furniture_context = merged_context
    else:
        furniture_context = CHAIR_TYPE_PART_CONTEXT.get(chair_type, {})

    for part in parts:
        label    = part.get("label", "unknown")
        geometry = part.get("geometry") or {}
        shape    = geometry.get("shape", {})
        meas     = geometry.get("measurements", {})
        flags    = geometry.get("ergonomic_flags", [])
        role     = (geometry.get("_raw") or {}).get("role", "")

        lines.append(f"\n  [{label.upper()}]")

        # Furniture-type context — checked by label first, then by role as fallback
        ctx = furniture_context.get(label) or furniture_context.get(role)
        if ctx:
            lines.append(f"  Furniture-type context: {ctx}")

        if furniture_type == "table":
            lines.append("  Measurements:")
            lines.append(_format_measurements(meas, ocr_measurements, label))
            lines.append("  Ergonomic/structural flags:")
            lines.append(_format_ergo_flags(flags))
        else:
            lines.append("  Shape descriptors:")
            lines.append(_format_shape(shape))
            lines.append("  Measurements:")
            lines.append(_format_measurements(meas, ocr_measurements, label))
            lines.append("  Ergonomic flags:")
            lines.append(_format_ergo_flags(flags))

    # ── Spatial relations ───────────────────────────────────────────────────
    lines.append("\nSPATIAL RELATIONS BETWEEN PARTS:")
    lines.append(_format_spatial_relations(relations))

    # ── Full measurement audit ──────────────────────────────────────────────
    lines.append("\nMEASUREMENT AUDIT (OCR labels vs ergonomic benchmarks):")
    if is_hybrid and influences:
        lines.append(_get_hybrid_benchmark_audit(ocr_measurements, influences))
    else:
        if furniture_type == "table":
            lines.append(_format_ocr_benchmark_audit(ocr_measurements, chair_type, furniture_type="table"))
        else:
            lines.append(_format_ocr_benchmark_audit(ocr_measurements, chair_type))

    # ── Construction reference ──────────────────────────────────────────────
    lines.append("\nCONSTRUCTION REFERENCE:")
    if is_hybrid and influences:
        for inf in influences:
            key = INFLUENCE_TO_SUMMARY_KEY.get(inf)
            if key and key in CHAIR_SUMMARIES:
                lines.append(f"  [{inf}]: {CHAIR_SUMMARIES[key]['construction']}")
    else:
        lines.append(summary["construction"])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. PUBLIC API
# ---------------------------------------------------------------------------

def build_expert_prompt(
    analysis_data: dict,
    current_phase: str = "ANALYSIS",
    is_followup: bool = False,
    user_message: str = ""
) -> dict:
    """
    Primary function called by main.py.

    Parameters
    ----------
    analysis_data : dict
        Full output from the image analysis pipeline, including:
        - identified_type, is_hybrid, influences
        - parts_with_traits (each with geometry from analyze_geometry v2)
        - spatial_relations (from compute_spatial_relations)
        - measurements (OCR output from parse_measurements_from_lines)
        - canonical_parts

    current_phase : str
        One of: ANALYSIS, ERGONOMICS, CONSTRUCTION, INTENT_SYNC

    is_followup : bool
        True for chat messages after the initial upload.

    user_message : str
        The user's actual message — used for phase routing on follow-ups.

    Returns
    -------
    dict with keys: system_prompt, prompt, phase
    """
    ocr_measurements = analysis_data.get("measurements", {})
    furniture_type = analysis_data.get("furniture_type", "chair").lower()

    # Phase routing — only re-route on follow-up messages
    if is_followup and user_message:
        current_phase = detect_phase(user_message, current_phase)

    phase_config = PHASE_RULES.get(current_phase, PHASE_RULES["ANALYSIS"])
    phase_instruction = phase_config["instruction"].strip()

    # Table-only concise mode (chairs remain unchanged)
    if furniture_type == "table":
        phase_instruction += (
            "\n\n"
            "TABLE-ONLY CONCISE MODE:\n"
            "- Keep output precise and concise (max 6 bullets OR ~140 words).\n"
            "- Use short, direct statements.\n"
            "- Only include findings supported by [SKETCH DATA].\n"
            "- For every recommendation, cite at least one concrete label/value (e.g., TH/TL/TW/LH/LS).\n"
            "- Avoid repeating the same point or re-listing full sketch context.\n"
            "- Do NOT use seating/body-contact language for tables (e.g., pressure point, bottoming out).\n"
            "- Do NOT infer spill-risk/concavity hazards from contour descriptors alone; require explicit flag or OCR-backed evidence.\n"
            "- Prioritize OCR dimensions and explicit WARNING/CRITICAL flags over visual-shape speculation."
        )

    # Build the sketch data block
    sketch_data = _build_sketch_data_block(analysis_data, ocr_measurements)

    # Build the system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        phase=current_phase,
        phase_objective=phase_config["objective"],
        phase_instruction=phase_instruction,
        sketch_data=sketch_data,
    )

    # Build the user-facing prompt
    if is_followup:
        if furniture_type == "table":
            user_prompt = f"{user_message}\n\nPlease answer concisely and only with table-specific points from this sketch."
        else:
            user_prompt = user_message
    else:
        item_type = analysis_data.get("identified_type", "item")
        parts_list = ", ".join(analysis_data.get("canonical_parts", []))
        if furniture_type == "table":
            user_prompt = (
                f"I've uploaded a sketch of a {item_type}. "
                f"Detected parts: {parts_list}. "
                f"Please provide a concise table audit: top 3 findings and top 3 fixes."
            )
        else:
            user_prompt = (
                f"I've just uploaded a sketch of a {item_type}. "
                f"Detected parts: {parts_list}. "
                f"Please conduct your full Expert Audit."
            )

    return {
        "system_prompt": system_prompt.strip(),
        "prompt": user_prompt,
        "phase": current_phase,
    }

# ---------------------------------------------------------------------------
# 8. MODIFICATION FEEDBACK PROMPT
# ---------------------------------------------------------------------------
 
MODIFICATION_FEEDBACK_TEMPLATE = """You are the Lead Furniture Architect at DesignableAI.
 
The user has been adjusting their chair design in the interactive visualizer.
Below is a summary of every modification they made. Your job is to assess the
ergonomic and structural consequences of these specific changes.
 
RULES:
- Reference EVERY measurement change by its exact before/after values.
- If a flag changed status (e.g. ok → warning), explain the physical consequence.
- If a change IMPROVES ergonomics, say so clearly — the user should know what works.
- If a change creates a NEW problem, be direct and give the specific fix.
- Do NOT repeat generic advice. Every sentence must reference a specific number.
- If shape was modified (sharpened or smoothed), explain how the edge profile
  change affects both the visual language and body contact.
- End with a prioritised list: what to keep, what to adjust further.
- Keep it concise — this is a focused assessment, not a full audit.
 
CHAIR TYPE: {chair_type}
{hybrid_line}
 
MODIFICATIONS:
{modifications_block}
 
ORIGINAL CONTEXT:
{original_context}
"""
 
def _format_modification_entry(mod: dict) -> str:
    """Formats a single modification entry for the LLM prompt."""
    label = mod.get("label", "unknown")
    changes = mod.get("changes", {})
    orig_meas = mod.get("original_measurements", {})
    new_meas = mod.get("new_measurements", {})
    orig_flags = mod.get("original_flags", [])
    new_flags = mod.get("new_flags", [])
 
    lines = [f"\n  [{label.upper()}]"]
 
    # Describe what was changed
    change_parts = []
    sx = changes.get("scaleX", 1)
    sy = changes.get("scaleY", 1)
    sl = changes.get("shapeLevel", 0)
 
    if sx != 1:
        pct = (sx - 1) * 100
        direction = "wider" if pct > 0 else "narrower"
        change_parts.append(f"Width scaled to {sx:.0%} ({abs(pct):.0f}% {direction})")
    if sy != 1:
        pct = (sy - 1) * 100
        direction = "taller" if pct > 0 else "shorter"
        change_parts.append(f"Height scaled to {sy:.0%} ({abs(pct):.0f}% {direction})")
    if sl != 0:
        if sl > 0:
            change_parts.append(f"Shape smoothed by {sl} level(s) — more organic/rounded")
        else:
            change_parts.append(f"Shape sharpened by {abs(sl)} level(s) — more angular/geometric")
 
    lines.append(f"  Changes: {'; '.join(change_parts) if change_parts else 'None'}")
 
    # Before/after measurements
    def compare(key, unit="mm"):
        orig = orig_meas.get(key)
        new = new_meas.get(key)
        if orig is not None and new is not None and orig != new:
            return f"    {key}: {orig}{unit} → {new}{unit} (Δ {new - orig:+.1f}{unit})"
        return None
 
    meas_lines = []
    for key in ["width_mm", "height_mm", "width_px", "height_px",
                 "recline_angle_deg", "inner_edge_angle_deg",
                 "curvature_radius", "area_px"]:
        unit = "°" if "angle" in key or "deg" in key else ("px" if "px" in key else "mm")
        line = compare(key, unit)
        if line:
            meas_lines.append(line)
 
    if meas_lines:
        lines.append("  Measurement changes:")
        lines.extend(meas_lines)
 
    # Flag changes
    flag_changes = []
    for i, nf in enumerate(new_flags):
        if i < len(orig_flags):
            of = orig_flags[i]
            if of.get("status") != nf.get("status"):
                flag_changes.append(
                    f"    {nf.get('field', '?').upper()}: {of.get('status', '?')} → {nf.get('status', '?')} "
                    f"(measured: {of.get('measured', '?')} → {nf.get('measured', '?')}, "
                    f"benchmark: {nf.get('benchmark', '?')})"
                )
                flag_changes.append(f"      → {nf.get('note', '')}")
        else:
            # New flag that didn't exist before
            flag_changes.append(
                f"    NEW [{nf.get('status', '?').upper()}] {nf.get('field', '?').upper()}: "
                f"{nf.get('measured', '?')} vs {nf.get('benchmark', '?')}"
            )
            flag_changes.append(f"      → {nf.get('note', '')}")
 
    if flag_changes:
        lines.append("  Ergonomic flag changes:")
        lines.extend(flag_changes)
    else:
        lines.append("  Ergonomic flags: no status changes detected.")
 
    return "\n".join(lines)
 
 
def build_modification_feedback_prompt(
    chair_type: str,
    is_hybrid: bool,
    influences: list,
    modifications: list,
    classification_data: dict,
) -> dict:
    """
    Builds a focused prompt for the /ai-feedback endpoint.
 
    Parameters
    ----------
    chair_type      : str — identified chair type
    is_hybrid       : bool
    influences      : list of influence strings for hybrids
    modifications   : list of modification dicts from the frontend
    classification_data : original analysis_data for context
 
    Returns
    -------
    dict with keys: system_prompt, prompt, phase
    """
    # Build modifications block
    mod_lines = []
    for mod in modifications:
        mod_lines.append(_format_modification_entry(mod))
    modifications_block = "\n".join(mod_lines) if mod_lines else "No modifications recorded."
 
    # Hybrid line
    hybrid_line = ""
    if is_hybrid and influences:
        hybrid_line = f"HYBRID: Yes — influences: {', '.join(influences)}"
 
    # Original context — abbreviated summary of the chair
    orig_parts = classification_data.get("parts_with_traits", [])
    part_names = [p.get("label", "?") for p in orig_parts]
    original_context = f"Detected parts: {', '.join(part_names)}"
 
    # Add spatial relations if available
    relations = classification_data.get("spatial_relations", {})
    if relations:
        rel_lines = []
        if "seat_to_backrest_angle_deg" in relations:
            rel_lines.append(f"  Seat-to-backrest angle: {relations['seat_to_backrest_angle_deg']}°")
        if "backrest_to_seat_width_ratio" in relations:
            rel_lines.append(f"  Backrest/seat width ratio: {relations['backrest_to_seat_width_ratio']}")
        if "armrest_above_seat_px" in relations:
            rel_lines.append(f"  Armrest clearance above seat: {relations['armrest_above_seat_px']}px")
        if rel_lines:
            original_context += "\nOriginal spatial relations:\n" + "\n".join(rel_lines)
 
    system_prompt = MODIFICATION_FEEDBACK_TEMPLATE.format(
        chair_type=chair_type,
        hybrid_line=hybrid_line,
        modifications_block=modifications_block,
        original_context=original_context,
    )
 
    user_prompt = (
        "I've made these adjustments to my chair design in the visualizer. "
        "Give me a focused ergonomic and structural assessment of these specific changes. "
        "What improved? What got worse? What should I adjust next?"
    )
 
    return {
        "system_prompt": system_prompt.strip(),
        "prompt": user_prompt,
        "phase": "ERGONOMICS",
    }
 
 
# ---------------------------------------------------------------------------
# 7. QUICK TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Simulated data matching the wing chair sketch shown
    test_data = {
        "identified_type": "Wing Chair",
        "is_hybrid": False,
        "influences": [],
        "canonical_parts": ["backrest", "seat", "armrest", "wing_flanage", "leg_structure"],
        "measurements": {
            "SH": {"value": 43, "unit": "cm"},
            "SD": {"value": 56, "unit": "cm"},
            "BH": {"value": 65, "unit": "cm"},
            "SW": {"value": 50, "unit": "cm"},
            "AH": {"value": 58, "unit": "cm"},
            "DA": {"value": 100, "unit": ""},
        },
        "parts_with_traits": [
            {
                "label": "backrest",
                "geometry": {
                    "shape": {
                        "edge":       {"label": "organic / fluid",        "detail": "18 vertices — no hard corners anywhere."},
                        "curvature":  {"label": "semi-contoured",          "detail": "Solidity 0.88 — mild concavity suggesting a gentle lumbar curve."},
                        "orientation":{"label": "tall / vertical emphasis","detail": "Aspect ratio 0.71 — strong vertical reach, formal and supportive."},
                        "complexity": {"label": "moderate profile",        "detail": "Medium vertex density — a few character details on an otherwise clean form."},
                    },
                    "measurements": {
                        "height_mm": 623, "width_mm": 441,
                        "recline_angle_deg": 97,
                        "dominant_angle_deg": 88.3,
                        "solidity": 0.882,
                        "scale_vs_seat": 1.41,
                        "scale_label": "dominant (significantly taller than seat)",
                    },
                    "ergonomic_flags": [
                        {"field": "recline", "measured": "97°", "benchmark": "95–110°", "status": "ok",
                         "note": "Recline angle is within the ergonomic comfort zone."}
                    ],
                }
            },
            {
                "label": "seat",
                "geometry": {
                    "shape": {
                        "edge":       {"label": "semi-curved / transitional", "detail": "12 vertices — mix of straight runs and gentle curves."},
                        "curvature":  {"label": "flat / linear",               "detail": "Solidity 0.94 — fills its convex hull almost completely."},
                        "orientation":{"label": "wide / horizontal emphasis",  "detail": "Aspect ratio 1.31 — emphasises lateral spread."},
                        "complexity": {"label": "simple / clean profile",      "detail": "Low vertex density — minimal and precise."},
                    },
                    "measurements": {
                        "height_mm": 441, "width_mm": 481,
                        "dominant_angle_deg": 4.1,
                        "solidity": 0.94,
                        "scale_vs_seat": 1.0,
                    },
                    "ergonomic_flags": [
                        {"field": "depth", "measured": "560mm", "benchmark": "430–520mm", "status": "critical",
                         "note": "Seat depth 560mm exceeds 520mm — shorter users' lower back won't reach the backrest."}
                    ],
                }
            },
        ],
        "spatial_relations": {
            "seat_to_backrest_angle_deg": 187,
            "seat_to_backrest_note": "Opening angle 187° — this seems extreme; verify the backrest mask isn't including the wing flanges.",
            "backrest_to_seat_width_ratio": 0.92,
            "width_ratio_note": "Backrest width is 92% of seat width — a clean, unified proportion.",
        },
    }

    result = build_expert_prompt(test_data, current_phase="ANALYSIS", is_followup=False)
    print("=== SYSTEM PROMPT (first 3000 chars) ===\n")
    print(result["system_prompt"][:3000])
    print("\n=== USER PROMPT ===\n")
    print(result["prompt"])
    print("\n=== DETECTED PHASE ===\n")
    print(result["phase"])

    print("\n\n=== ERGONOMICS PHASE TEST ===\n")
    followup = build_expert_prompt(
        test_data,
        current_phase="ANALYSIS",
        is_followup=True,
        user_message="I want to gift this to my grandmother who has back pain"
    )
    print(f"Routed to phase: {followup['phase']}")
    print(followup["system_prompt"][:1500])