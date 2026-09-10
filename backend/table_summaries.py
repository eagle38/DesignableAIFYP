# table_summaries.py — DesignableAI Table Furniture Type
# ========================================================
# Comprehensive table design summaries with ergonomic benchmarks
# and construction guidance, parallel to chair_summaries.py structure

TABLE_SUMMARIES = {
    "Dining Table": {
        "character": (
            "A dining table designed for seated meals with multiple place settings. "
            "Defined by top surface dimensions (length, width), comfortable seating height, "
            "and base design (four-leg, pedestal, or trestle). The visual balance between "
            "top mass and base proportion defines the design language."
        ),
        "ergonomic_benchmarks": {
            "TH": {
                "ideal": (700, 780),
                "unit": "mm",
                "note": "Table height. Standard dining: 730-760mm. Users sit with elbows at 90 degrees when seated. Too low forces forward lean; too high creates shoulder strain."
            },
            "TL": {
                "ideal": (1200, 2400),
                "unit": "mm",
                "note": "Table length. For 4 people: 1200-1500mm. For 6-8 people: 1800-2400mm. Affects circulation space and server access around the table."
            },
            "TW": {
                "ideal": (800, 1000),
                "unit": "mm",
                "note": "Table width. Standard: 900-1000mm allows place settings on both sides (350mm per side) plus 200mm center serving space. Narrower than 800mm restricts place setting layout."
            },
            "LH": {
                "ideal": (700, 760),
                "unit": "mm",
                "note": "Leg height from floor. Should align with table apron (50-80mm below top). Affects sightline clarity and visual weight distribution."
            },
            "LS": {
                "ideal": (400, 800),
                "unit": "mm",
                "note": "Leg spacing (distance from edge to leg center). Wider spacing (700-800mm) maximizes knee clearance for seated diners; narrower (400-500mm) improves structural stability."
            },
            "CW": {
                "ideal": (50, 100),
                "unit": "mm",
                "note": "Clearance width (apron depth). Must allow knees to tuck under table: minimum 200mm knee height clearance from floor to apron bottom."
            },
        },
        "construction": (
            "Top: solid wood (25-38mm thickness) or veneered plywood (15mm veneer + 12mm core). "
            "Apron: hardwood frame 40-50mm depth, mortise-and-tenon joints to legs. "
            "Legs: hardwood or metal, 40-60mm section, minimum 1.5-inch dia if round. "
            "Base bracing: cross-stretchers or corner blocks to resist racking under dynamic load. "
            "Top fastening: figure-eight fasteners or wooden breadboard ends to allow seasonal wood movement. "
            "For extendable tables: self-storing leaf system or leaf support brackets; "
            "alignment hardware must keep leaves flush when extended."
        ),
    },
    "Coffee Table": {
        "character": (
            "A low table for living room use, centering a seating arrangement. "
            "Dimensions are constrained by proximity to seating: 12-18 inches lower than adjacent chair seats. "
            "Design emphasis is on proportion and visual lightness — a coffee table should not block sightlines "
            "across a room. Top-heavy or clunky bases feel oppressive in intimate seating layouts."
        ),
        "ergonomic_benchmarks": {
            "TH": {
                "ideal": (380, 450),
                "unit": "mm",
                "note": "Coffee table height. Should be 12-18 inches (300-450mm) lower than seat height. At 450mm, allows easy reach from 600mm sofa seat. Too low (under 380mm) creates visual instability."
            },
            "TL": {
                "ideal": (1000, 1500),
                "unit": "mm",
                "note": "Table length. Should be roughly 2/3 the length of the seating it serves. A 1200-1500mm coffee table suits a standard 2-3 person sofa."
            },
            "TW": {
                "ideal": (600, 900),
                "unit": "mm",
                "note": "Table width. Should allow 300-450mm of clear space between table edge and seat edge for foot clearance and traffic. Narrower than 600mm feels cramped; wider than 900mm dominates small rooms."
            },
            "LH": {
                "ideal": (300, 450),
                "unit": "mm",
                "note": "Leg height. Lower legs (near table height or integrated base) make the table feel more anchored visually. Tall spindly legs make a heavy top look precarious."
            },
            "TO": {
                "ideal": 0.2,
                "unit": "ratio",
                "note": "Top overhang (ratio of top area beyond support base). Coffee tables can overhang 15-25% — this creates visual lightness. Overhangs over 30% create tipover risk."
            },
        },
        "construction": (
            "Top: solid wood, veneered plywood, or glass (6mm minimum tempered). Glass tops must have polished/beveled edges and stable base (center-of-gravity within base footprint). "
            "Base: single pedestal, four slim legs, or hidden frame. "
            "For glass: stainless steel or powder-coat steel frame corners. "
            "No apron needed — coffee tables rely on base geometry for visual lightness. "
            "Stability is critical: base footprint must exceed top footprint when accounting for overhang."
        ),
    },
    "Work Table": {
        "character": (
            "A functional table for tasks: writing, computer work, crafting, or assembly. "
            "Ergonomic precision is paramount — height, depth, and surface flatness directly affect user comfort and accuracy. "
            "Design should minimize visual clutter to support focus (minimal decoration, clean sightlines)."
        ),
        "ergonomic_benchmarks": {
            "TH": {
                "ideal": (700, 780),
                "unit": "mm",
                "note": "Work table height. For seated work: 700-750mm allows elbows at 90 degrees when hands rest on work surface. Standing work: 1000-1100mm. Adjustable height (600-800mm range) is ideal for variable tasks."
            },
            "TL": {
                "ideal": (1200, 1800),
                "unit": "mm",
                "note": "Table length. Single-user: 1200-1400mm. Multi-user or assembly work: 1600-1800mm. Affects reach distance to materials and tools."
            },
            "TW": {
                "ideal": (600, 900),
                "unit": "mm",
                "note": "Table depth. Minimum 600mm for laptop + materials. Ideal 750-900mm for two-handed work (e.g., drafting, assembly). Too deep (over 900mm) creates reaching strain."
            },
            "LH": {
                "ideal": (700, 780),
                "unit": "mm",
                "note": "Leg height must match table height precisely. Legs that are lower create surface angle and work instability."
            },
            "LS": {
                "ideal": (600, 900),
                "unit": "mm",
                "note": "Leg spacing. For seated work, legs should be 150-250mm inboard from table edges to allow knee clearance (minimum 300mm clearance from floor to apron)."
            },
            "SR": {
                "ideal": 0.01,
                "unit": "mm/m",
                "note": "Surface flatness (maximum deviation per meter). Precision work requires <1mm deviation per meter. Standard: <2mm. This is critical — build with straight-grain hardwood and check regularly."
            },
        },
        "construction": (
            "Top: solid hardwood (maple or birch for work tables — better flatness and durability than softwood). "
            "Thickness: 28-38mm for rigid surfaces. Veneer not recommended unless backed by substantial core. "
            "Apron: steel or hardwood frame, minimum 50mm depth, cross-braced to prevent any flex. "
            "Legs: steel tubing (25x25mm minimum) or hardwood, bolted to frame with grade 8 fasteners. "
            "Adjustability: if height-adjustable, use electric lift or precision screw mechanism (not spring-loaded). "
            "Cable management: integrated channels or under-table trays for power and data."
        ),
    },
    "Conference Table": {
        "character": (
            "A large formal table for meetings and presentations. "
            "Design must support sightlines (all attendees see all participants and any displayed content). "
            "Length creates formality; width must allow documentation, laptops, and comfortable arm positioning. "
            "Base design impacts perception: heavy/ornate suggests traditional authority; "
            "sleek/minimal suggests modern efficiency."
        ),
        "ergonomic_benchmarks": {
            "TH": {
                "ideal": (700, 780),
                "unit": "mm",
                "note": "Conference table height: same as dining (700-750mm). Allows comfortable writing and seated posture for long meetings."
            },
            "TL": {
                "ideal": (2400, 6000),
                "unit": "mm",
                "note": "Table length. For 8 people: 2400-3000mm. For 12-16 people: 3600-6000mm. Length affects sightline angle and meeting dynamics (longer tables can feel formal/hierarchical)."
            },
            "TW": {
                "ideal": (1000, 1400),
                "unit": "mm",
                "note": "Table width. Must accommodate laptop, documents, and elbow space for both sides: 1000-1200mm standard. Wider (1200-1400mm) if screen sharing or document display center-table."
            },
            "CW": {
                "ideal": (600, 800),
                "unit": "mm",
                "note": "Knee clearance (apron-to-floor). Minimum 600mm for comfortable leg extension during long meetings. Too shallow (under 500mm) creates fidgeting and circulation issues."
            },
            "AC": {
                "ideal": 2.4,
                "unit": "m per person",
                "note": "Seating allocation per person (table length / number of seats). Conference standard: 2.0-2.4m per seat allows comfortable arm reach and documentation space."
            },
        },
        "construction": (
            "Top: veneered plywood (18-25mm) or solid wood sections joined with mortise-and-tenon or biscuit joinery. "
            "For very long tables (4m+): built in sections with alignment hardware to maintain top flush at seams. "
            "Apron: substantial frame (60-80mm depth), hidden base for clean line when viewed from sitting position. "
            "Legs: twin-pedestal base (conference standard) or four-leg base for shorter tables. "
            "Power/data: built-in cable tray or pop-up power boxes at intervals (every 1.5-2m). "
            "Finish: matte or satin to minimize screen glare during presentations."
        ),
    },
    "Side Table": {
        "character": (
            "A small accent table beside seating or against a wall. "
            "Primary function is display/storage of a lamp, drink, or decorative object. "
            "Design emphasis is on proportion and visual balance in context — "
            "too large overwhelms the space; too small looks insignificant."
        ),
        "ergonomic_benchmarks": {
            "TH": {
                "ideal": (550, 650),
                "unit": "mm",
                "note": "Side table height. Should be at armrest height (550-650mm) for easy reach from seated position. Too low feels awkward to access; too high blocks sightlines."
            },
            "TL": {
                "ideal": (400, 600),
                "unit": "mm",
                "note": "Table length (or diameter if round). Small room: 400-500mm. Standard: 500-600mm. Affects how much surface area is available for lamp + object."
            },
            "TW": {
                "ideal": (400, 600),
                "unit": "mm",
                "note": "Table width (or depth if rectangular). Should match or slightly exceed length for balanced proportion. Too narrow (under 350mm) feels precarious."
            },
            "TO": {
                "ideal": 0.3,
                "unit": "ratio",
                "note": "Top-to-base ratio. Side tables can be top-heavy visually — overhangs of 20-30% are acceptable. Overhangs over 40% create tipover risk in households with children/pets."
            },
        },
        "construction": (
            "Top: solid wood, glass, or marble (12-20mm thickness). "
            "Base: single pedestal (safest for tight spaces), four slim legs, or sculptural form. "
            "For pedestal: base diameter should be 30-50% of top diameter for visual stability. "
            "Material: can be more decorative than large dining tables — wood, metal, stone, or mixed materials acceptable. "
            "Stability: single-pedestal or tripod bases are inherently tipover risks — test with 20kg sideways load."
        ),
    },
    "Generic Table": {
        "character": (
            "A multipurpose table without specific optimization for dining, work, or display. "
            "Analyze based on its likely context (dining, living room, workspace) inferred from proportions."
        ),
        "ergonomic_benchmarks": {
            "TH": {
                "ideal": (700, 800),
                "unit": "mm",
                "note": "General table height range. Most tables fall between 700-800mm. Determine specific ideal based on context."
            },
            "TL": {
                "ideal": (1000, 2400),
                "unit": "mm",
                "note": "General length range. 1000-1500mm for small/side tables; 1500-2400mm for dining; 2400+ for conference."
            },
            "TW": {
                "ideal": (600, 1200),
                "unit": "mm",
                "note": "General width range. 600-800mm for work; 900-1000mm for dining; 400-600mm for side/accent."
            },
            "LS": {
                "ideal": (400, 900),
                "unit": "mm",
                "note": "Leg spacing affects both comfort (knee clearance) and stability. Wider spacing reduces structural stiffness but improves legroom."
            },
        },
        "construction": (
            "Evaluate based on top/base proportion and detected joinery. "
            "Ask: Is the base proportional to the top mass? "
            "Are stress points (top-to-apron, apron-to-leg) visible or do they imply strong joinery? "
            "Does the base design suggest the intended load (light display or heavy work)?"
        ),
    },
}

# Fallback for unknown table types
_DEFAULT_TABLE_SUMMARY = TABLE_SUMMARIES["Generic Table"]

if __name__ == "__main__":
    print("Table summaries loaded:")
    for table_type in TABLE_SUMMARIES.keys():
        print(f"  - {table_type}")
