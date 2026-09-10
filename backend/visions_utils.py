# vision_utils.py
import re
from typing import List, Dict
from google.cloud import vision

# ============================================================
# 1. CLIENT INITIALIZATION
# ============================================================

_client = None

def get_vision_client():
    global _client
    if _client is None:
        import os
        # 1. Get the folder where THIS file (visions_utils.py) actually lives
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Force the path to the JSON file in your Downloads/backend folder
        # Make sure the name matches your sidebar: "DesignableAI.json"
        json_path = os.path.join(current_dir, "DesignableAI.json")
        
        # 3. OVERWRITE the environment variable (this kills the /Documents/ ghost)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
        
        print(f"--- DEBUG: FORCING VISION PATH TO: {json_path} ---")
        
        _client = vision.ImageAnnotatorClient()
    return _client


# ============================================================
# 2. OCR EXTRACTION
# ============================================================

def ocr_extract_lines(image_path: str) -> List[str]:
    """
    Runs Google Cloud Vision OCR and returns cleaned text lines.
    """
    client = get_vision_client()

    with open(image_path, "rb") as f:
        content = f.read()

    image = {"content": content}
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    full_text = response.full_text_annotation.text or ""
    lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

    return lines


# ============================================================
# 3. CANONICAL LABEL MAP
# ============================================================

CANONICAL_MEAS_LABELS = {
    # Chair labels
    "AH": "AH",
    "ARM_HEIGHT": "AH",
    "ARM_H": "AH",
    "ARMHT": "AH",

    "SD": "SD",
    "SEAT_DEPTH": "SD",
    "SEAT_D": "SD",

    "SW": "SW",
    "SEAT_WIDTH": "SW",
    "SEAT_W": "SW",

    "SH": "SH",
    "SEAT_HEIGHT": "SH",
    "SEAT_H": "SH",

    "BH": "BH",
    "BACK_HEIGHT": "BH",
    "BACK_H": "BH",

    # Shared / table labels
    "LH": "LH",
    "LEG_HEIGHT": "LH",
    "LEG_H": "LH",

    "TH": "TH",
    "TABLE_HEIGHT": "TH",
    "TABLE_H": "TH",

    "TL": "TL",
    "TABLE_LENGTH": "TL",
    "TABLE_L": "TL",
    "LENGTH": "TL",

    "TW": "TW",
    "TABLE_WIDTH": "TW",
    "TABLE_W": "TW",
    "WIDTH": "TW",

    "LS": "LS",
    "LEG_SPACING": "LS",
    "LEG_SPACE": "LS",

    "CW": "CW",
    "CLEARANCE_WIDTH": "CW",

    "TO": "TO",
    "TOP_OVERHANG": "TO",

    "AC": "AC",
    "ALLOCATION": "AC",

    "SR": "SR",
    "SURFACE_REGULARITY": "SR",
}

# ============================================================
# 4. REGEX FOR MEASUREMENTS
# ============================================================

MEAS_REGEX_LABEL_FIRST = re.compile(
    r"""
    (?P<label>[A-Za-z_]{1,18})         # AH, TL, TABLE_HEIGHT, etc.
    \s*[:=\s]?\s*
    (?P<value>\d{1,4}(?:[.,]\d{1,2})?) # number like 420 or 45.5
    \s*
    (?P<unit>mm|cm|in|inch|inches|")?  # unit or none
    """,
    re.IGNORECASE | re.VERBOSE
)

MEAS_REGEX_VALUE_FIRST = re.compile(
    r"""
    (?P<value>\d{1,4}(?:[.,]\d{1,2})?)
    \s*
    (?P<unit>mm|cm|in|inch|inches|")?
    \s*[:=\s-]*\s*
    (?P<label>[A-Za-z_]{1,18})
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_measurement_label(raw_label: str) -> str:
    label_key = (raw_label or "").upper().strip()
    label_key = re.sub(r"[^A-Z_]", "", label_key)
    if not label_key:
        return ""

    direct = CANONICAL_MEAS_LABELS.get(label_key)
    if direct:
        return direct

    compact = label_key.replace("_", "")
    direct = CANONICAL_MEAS_LABELS.get(compact)
    if direct:
        return direct

    # OCR-safe aliases for common confusions
    ocr_aliases = {
        "5H": "SH",
        "8H": "BH",
        "1H": "LH",
        "T1": "TL",
        "TW": "TW",
        "TH": "TH",
        "L5": "LS",
    }
    return ocr_aliases.get(label_key, "")

# ============================================================
# 5. PARSING MEASUREMENTS
# ============================================================

def parse_measurements_from_lines(lines: List[str]) -> Dict[str, Dict]:
    """
    Parse OCR text lines into normalized measurement values.

    Returns:
    {
        "arm_height": { "raw_label": "AH", "value": 420.0, "unit": "mm", "source_line": "AH: 420 mm" },
        "seat_depth": { ... },
        "other": [...]
    }
    """
    parsed = {}

    for ln in lines:
        # normalize OCR dashes/punctuation noise without destroying content
        normalized_line = (ln or "").replace("—", "-").replace("–", "-")

        matches = []
        matches.extend(MEAS_REGEX_LABEL_FIRST.finditer(normalized_line))
        matches.extend(MEAS_REGEX_VALUE_FIRST.finditer(normalized_line))

        for match in matches:
            raw_label = match.group("label")
            raw_value = match.group("value").replace(",", ".")
            raw_unit = (match.group("unit") or "").lower().replace(".", "")

            # Convert numeric
            try:
                num = float(raw_value)
            except:
                continue

            # Normalize units → output always mm
            if raw_unit == "cm":
                value_mm = num * 10
                unit = "cm"
            elif raw_unit in ("in", "inch", "inches", '"'):
                value_mm = num * 25.4
                unit = "in"
            else:
                value_mm = num
                unit = "mm"

            canonical = _normalize_measurement_label(raw_label)

            if canonical:
                parsed[canonical] = {
                    "raw_label": raw_label,
                    "value": round(value_mm, 2),
                    "unit": "mm",
                    "source_line": normalized_line,
                }
            else:
                parsed.setdefault("other", []).append({
                    "label": raw_label,
                    "value": num,
                    "unit": raw_unit or "unknown",
                    "source_line": normalized_line
                })

    return parsed