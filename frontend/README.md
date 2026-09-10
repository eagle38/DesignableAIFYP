# DesignableAI

**AI-Powered Furniture Design and Ergonomics Assistant**

Upload a hand-drawn furniture sketch and receive real-time part detection, ergonomic analysis, and AI-driven design feedback. Reshape any part, apply real materials, place the result in a photorealistic room, or design something entirely new in a browser-based 3D sculpting studio.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Backend Pipeline](#backend-pipeline)
- [Frontend Features](#frontend-features)
- [3D Sculpt Studio](#3d-sculpt-studio)
- [Room Visualizer](#room-visualizer)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [API Reference](#api-reference)

---

## Overview

Furniture design has a gap at the beginning of the process. A designer sketches an idea on paper, but any real evaluation — are the proportions right, is the seat depth ergonomic, does the backrest height make sense for this chair type — requires expensive CAD software, formal training, or a physical prototype.

DesignableAI closes that gap. The system reads a hand-drawn sketch, identifies every individual part, measures it, checks it against ergonomic benchmarks specific to that furniture type, and returns grounded design feedback in seconds.

From there the design stays live. Parts can be reshaped and the ergonomic consequences recalculate immediately. Materials can be applied and previewed on the actual sketch. The result can be dropped into a real room to check scale and aesthetic fit. And for users starting without a sketch, a full 3D sculpting environment lets them build a piece from scratch.

---

## Tech Stack

**Frontend**
- React 18 (Vite)
- React Router
- Canvas2D API — sketch rendering, mask overlays, texture compositing
- Three.js (WebGL2) — 3D sculpting environment
- React Markdown — LLM response rendering

**Backend**
- FastAPI (Python)
- YOLOv8 instance segmentation (trained via Roboflow)
- OpenCV — image processing and contour analysis
- Google Gemini API — design and ergonomic reasoning
- Tesseract OCR — measurement label extraction

**Model Training**
- Roboflow — dataset annotation and management
- 200+ annotated furniture sketches (chairs and tables)
- Polygon-level instance segmentation labels

---

## Architecture

```
┌─────────────┐
│   Sketch    │
│   Upload    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│                  BACKEND PIPELINE                │
│                                                  │
│  ┌────────┐   ┌────────┐   ┌──────────────────┐│
│  │  OCR   │──▶│  YOLO  │──▶│  Classification  ││
│  │ Labels │   │ Masks  │   │  (chair type)    ││
│  └────────┘   └────────┘   └────────┬─────────┘│
│                                      │          │
│                                      ▼          │
│                          ┌───────────────────┐  │
│                          │ Geometry Analyzer │  │
│                          │  · measurements   │  │
│                          │  · descriptors    │  │
│                          │  · ergonomic flags│  │
│                          └─────────┬─────────┘  │
│                                    │            │
│                                    ▼            │
│                          ┌───────────────────┐  │
│                          │  Prompt Builder   │  │
│                          │  (confidence-     │  │
│                          │   tagged data)    │  │
│                          └─────────┬─────────┘  │
│                                    │            │
│                                    ▼            │
│                          ┌───────────────────┐  │
│                          │   Gemini LLM      │  │
│                          └─────────┬─────────┘  │
└────────────────────────────────────┼────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────┐
│                    FRONTEND                      │
│                                                  │
│  Canvas Workspace  │  5-Panel Carousel           │
│  · mask overlays   │  · Dimensions               │
│  · pan / zoom      │  · Measurements             │
│  · texture layers  │  · Shape & Flags            │
│  · part selection  │  · Ergonomics & AI          │
│                    │  · Material Engine          │
│                                                  │
│  Design Assistant Chat (contextual Gemini)      │
└──────────┬───────────────────────┬──────────────┘
           │                       │
           ▼                       ▼
    ┌─────────────┐        ┌──────────────┐
    │    Room     │        │    Sculpt    │
    │  Visualizer │        │    Studio    │
    └─────────────┘        └──────────────┘
```

---

## Backend Pipeline

### 1. OCR — Measurement Label Extraction

Designers frequently write measurements directly on their sketches — `SH 43cm`, `SD 50cm`, `BH 60cm`. The pipeline reads these before anything else.

Extracted labels become the **source of truth** for measurements. Any value confirmed by an OCR label takes priority over a pixel-derived calculation, and is tagged as such so downstream consumers know which values are reliable.

**Supported label codes:**

| Code | Meaning |
|------|---------|
| `SH` | Seat Height |
| `SD` | Seat Depth |
| `SW` | Seat Width |
| `BH` | Backrest Height |
| `AH` | Armrest Height |
| `DA` | Design/Model Reference |

### 2. YOLO Instance Segmentation

A custom YOLOv8 segmentation model trained on 200+ annotated furniture sketches detects every individual part and returns a **polygon mask** — not a bounding box, but the precise traced outline of that part in the image.

**Detected chair parts:** seat, backrest, headrest, armrest, lumbar support, wing flange, shell, base, leg structure, five-star base, caster wheel, control mechanism

**Detected table parts:** table top, legs, apron, pedestal, stretcher

Detections below a **0.25 confidence threshold** are discarded. Each surviving detection returns its class label, confidence score, and polygon mask coordinates.

The polygon masks are what make everything downstream possible — geometry analysis operates on the exact shape, textures clip to the exact outline, and the canvas overlays trace the exact part.

### 3. Furniture Classification

Once parts are identified, the system classifies what type of furniture this is — office chair, Eames lounge chair, wing chair, egg shell chair, dining table, coffee table.

This matters because **ergonomic benchmarks are type-specific**. A lounge chair is expected to have a much deeper seat and lower seat height than a task chair. Applying office chair standards to a lounge chair produces meaningless failures. Classification determines which benchmark set gets applied.

The classifier also detects **hybrid designs** — sketches that combine influences from multiple archetypes — and reports the contributing influences.

### 4. Scale Resolution — px_per_mm

To convert pixel measurements into real-world millimetres, the pipeline needs a scale factor.

**How it's derived:**

1. OCR finds a seat height label (e.g. `SH 43cm` → 430mm)
2. YOLO's seat detection provides the seat mask
3. `cv2.boundingRect` on that mask gives the seat's pixel height
4. `px_per_mm = seat_height_px / 430`

If either the SH label or the seat detection is missing, `px_per_mm` stays `null` and all measurements fall back to pixel values, clearly tagged as `[APPROXIMATE]`.

### 5. Geometry Analyzer

The core analytical engine. For every detected part, it computes a full set of metrics directly from the mask polygon.

#### Dimensional Measurements

| Metric | Description |
|--------|-------------|
| `width_mm` / `width_px` | Part width, converted if scale is available |
| `height_mm` / `height_px` | Part height |
| `area_mm2` / `area_px` | Polygon area via `cv2.contourArea` |
| `curvature_radius` | Approximated radius of the dominant curve |
| `compactness` | How tightly the shape fills its bounding region |
| `scale_vs_seat` | Ratio of this part's size to the seat, for proportional checks |

Each dimensional value carries a **source tag** — `"ocr"` when confirmed by a label, `"calculated"` when derived from pixels.

#### Shape Descriptors

Six annotation-independent descriptors that characterise form rather than size. Each returns a human-readable label plus a design interpretation and an ergonomic interpretation.

| Descriptor | What It Measures |
|------------|------------------|
| `contour_smoothness` | Organic and flowing vs angular and geometric |
| `curvature` | Solid and full vs hollow and open |
| `orientation` | Dominant axis of the shape |
| `proportional_size` | Size relative to the rest of the piece |
| `symmetry` | Left/right balance across the vertical axis |
| `edge_regularity` | Consistency and uniformity of the outline |

These are computed from raw contour properties — solidity, aspect ratio, convex hull deviation, moment analysis — which means they work regardless of how the sketch was drawn or annotated.

#### Ergonomic Flags

Each part is checked against benchmark ranges for the classified furniture type. Every check returns a structured flag.

```json
{
  "field": "seat_depth",
  "measured": "560mm",
  "benchmark": "400-480mm",
  "status": "warning",
  "note": "Seat depth exceeds standard range. Users with shorter
           leg length may experience pressure behind the knee."
}
```

**Status values:**
- `ok` — within benchmark range
- `warning` — outside range but not critical
- `critical` — significantly outside range with real usability impact

### 6. Prompt Builder

Packages the complete analysis into a structured prompt for the LLM. This is where most of the output quality is determined.

**Design principles enforced in every prompt:**

- **Confidence tagging** — every measurement is explicitly marked as OCR-confirmed or pixel-approximated, so the model knows what it can assert with certainty
- **Grounding constraint** — the model may only comment on values actually present in the prompt; it cannot introduce outside furniture knowledge as fact
- **No angle claims** — angular measurements derived from 2D sketches are unreliable, so the prompt explicitly forbids recline angles, backrest angles, and any degree-based statements
- **No generic advice** — phrases like "consider ergonomic standards" or "consult a professional" are banned; every recommendation must reference a specific observed value
- **Brevity constraint** — recommendations capped at one sentence each

### 7. Gemini LLM Integration

The structured prompt goes to the Gemini API, which returns the design and ergonomic assessment. The response covers:

- **Design language analysis** — what the proportions and forms communicate about design intent
- **Part-by-part assessment** — grounded in the actual measurements and descriptors
- **Prioritised recommendations** — specific, brief, tied to observed values
- **Measurement audit** — explicit listing of which values were confirmed vs approximated

The session persists, so the Design Assistant chat can answer follow-up questions with full analysis context.

---

## Frontend Features

### Interactive Canvas Workspace

The uploaded sketch renders on a dark grid canvas with every detected part overlaid as a coloured mask.

**Colour coding by part role:**

| Role | Colour |
|------|--------|
| Seat | Terracotta `#c8602a` |
| Backrest | Sage `#6b8f71` |
| Headrest | Warm brown `#9b8264` |
| Armrest | Stone `#8a8278` |
| Shell | Clay `#b47850` |
| Base / Legs | Slate `#78736c` |
| Table Top | Sand `#b4a078` |

**Interactions:**
- **Hover** — tooltip showing shape classification and active ergonomic flags
- **Click** — select a part, opening it in the panel carousel
- **Drag** — pan the canvas
- **Scroll** — zoom toward the cursor position
- **Fit** — reset transform to fit the sketch in view

Labels render outside the sketch with dashed leader lines pointing to each part's centroid, distributed across available vertical slots to avoid overlap. Rendering accounts for `devicePixelRatio` so the canvas stays sharp on high-DPI displays.

---

### Interactive Rescaling

The defining feature of the workspace. Any detected part can be reshaped directly, and the mask polygon updates live on the canvas.

**The 2D Coordinate Pad**

Selecting a part opens a coordinate pad in the Dimensions panel. A draggable handle sits at the origin. Moving it horizontally scales width, vertically scales height — both simultaneously, in one gesture.

```
              H +
               │
               │
     W −  ─────┼─────  W +
               │
               │
              H −
```

- Range: **50% to 200%** per axis
- Handle position maps directly to scale factors
- Mask polygon transforms in real time as you drag
- Live readout shows exact percentages

**Adjacency Propagation**

Parts don't exist in isolation. When one changes, structurally connected parts adjust automatically:

- **Widening the seat** propagates to the leg structure, five-star base, caster wheels, and control mechanism at 50% of the applied scale — the base widens to maintain stability but not at full ratio
- **Heightening the backrest** translates the headrest upward proportionally, so it stays attached rather than floating or overlapping

**Geometry Recalculation**

On release, the modified mask polygons are sent to `/recalculate-geometry`. The backend re-runs the full geometry analyzer on the new shapes and returns updated measurements, shape descriptors, and ergonomic flags.

---

### Ergonomic Repercussions

Every modification has consequences, and the system makes them visible.

**The Modification Log**

The Ergonomics panel tracks every change made in the session. Each modified part shows a card with the applied deltas and its current flag states.

**Before/After Flag Comparison**

Flags that changed status as a result of a modification are highlighted with their previous state shown inline:

```
⚠  seat_depth    560mm    was ok
✓  seat_width    480mm
✕  backrest_h    340mm    was warning
```

This makes trade-offs immediately visible — widening a seat for comfort might push the overall footprint outside a target range, and you see that the moment it happens rather than discovering it later.

**AI Assessment of Modifications**

The **AI Assessment** button sends the complete modification set to Gemini — original measurements, new measurements, original flags, new flags, per part.

The model returns an evaluation of whether each change improved or worsened the design, referencing the specific values that shifted. The same prompt constraints apply — no angles, no generic advice, one sentence per recommendation.

---

### Panel Carousel

Five panels, navigable by arrows or dot indicators. For tables, the Shape panel is skipped since its descriptors are chair-specific.

#### 1. Dimensions
The 2D coordinate pad, live percentage readout, Reset, and Recalculate.

#### 2. Measurements
Grid of computed values for the selected part — width, height, area, curve radius, compactness, scale vs seat, solidity, aspect ratio. Units shown inline. Angular measurements are deliberately excluded as unreliable from 2D sketch geometry.

#### 3. Shape & Flags
All six shape descriptors with their labels, details, and dual interpretations (design and ergonomic). Below that, the full ergonomic flag list with measured value, benchmark range, status, and explanatory note.

#### 4. Ergonomics & AI
The modification log, before/after flag comparison, and AI Assessment trigger. Empty until modifications are made.

#### 5. Material Engine
Full texture library and application controls.

---

### Material Engine

Real material textures applied directly onto the sketch, clipped to each part's exact mask polygon.

**Library structure — four categories, multiple finishes each:**

| Category | Finishes |
|----------|----------|
| **Leather** | Smooth, Stitched, Pebbled, Suede, Rough |
| **Fabric** | Cotton, Pattern, Tiled, Printed, Woven, Stitched, Rough |
| **Metal** | Brushed, Matte, Rusty, Chrome |
| **Wood** | Walnut, Maple, Oak, Cherry |

Each finish contains multiple colour variants, shown as circular swatches in an expandable accordion.

**Rendering technique**

Applying a texture is a three-step Canvas2D operation:

1. **Clip** — the part's mask polygon becomes a clipping path via `ctx.clip()`, restricting all subsequent drawing to that exact outline
2. **Pattern fill** — the texture image becomes a repeating pattern via `ctx.createPattern(image, 'repeat')`, scaled with a `DOMMatrix` transform, and filled across the clipped region
3. **Multiply blend** — the original sketch redraws on top with `globalCompositeOperation = 'multiply'`, so white pixels become transparent and the pencil lines show through the texture

The result reads as a material sample rendered onto the drawing rather than a flat colour block covering it.

**Apply to All Parts**

A single action applies the active texture to every part **except legs and base structures**, which typically use a different material in real furniture. Saves manually applying wood grain to six separate parts of a shell chair.

**Texture caching**

Loaded texture images are cached in a ref-based map keyed by source path. Reapplying a previously used texture is instant with no network round trip.

---

### Design Assistant Chat

A collapsible sidebar running an ongoing Gemini conversation with full analysis context loaded.

The session retains the complete classification data, so questions can reference the analysis directly:

- *"Why did you flag the backrest?"*
- *"What would happen if I made the seat 15% wider?"*
- *"Is this closer to a task chair or a lounge chair?"*

Responses render as Markdown. The panel collapses to a vertical tab to maximise canvas space when not in use.

---

## 3D Sculpt Studio

A complete browser-based 3D furniture design environment built from scratch in Three.js. No installation, no external model files, no CAD experience required — open a tab and start shaping.

**Route:** `/sculpt`

### Parts Inventory

Every preset is **programmatically generated** from primitives with vertex displacement. There are no `.obj` or `.glb` files anywhere in the project.

| Category | Presets |
|----------|---------|
| Seats | 5 (basic blob, bucket, flat pad, tapered, rounded) |
| Backrests | 5 (shell, slat, curved, high-back, lumbar-shaped) |
| Headrests | 3 |
| Armrests | 4 |
| Legs | 4 (four-leg, pedestal, five-star, sled) |
| Support | 1 |

Construction pattern: create a subdivided primitive (`BoxGeometry` at 20×6×20 segments, or `SphereGeometry`), iterate the position attribute, displace each vertex by a mathematical function of its coordinates, then `computeVertexNormals()`.

The bucket seat, for example, measures each vertex's radial distance from centre and pushes the top surface downward proportionally — centre dips most, edges stay flat.

### Snap Zones

Parts connect magnetically. Placing a backrest snaps it behind the seat, armrests to the sides, legs underneath. Valid snap positions glow terracotta on hover.

### Tool Modes

**Select** — click to pick parts.

**Move** — drag to reposition on the horizontal plane. **Shift + drag** switches to vertical movement, using a plane whose normal is the camera's flattened look direction, so dragging up and down maps cleanly to Y-axis translation with X and Z locked.

**Sculpt** — activates the brush system.

### Sculpting Brushes

All brushes operate on `BufferGeometry` position attributes with **Gaussian falloff** — `e^(-(d²)/(2σ²))` — so deformation fades smoothly from the brush centre rather than stamping a hard circular edge.

| Brush | Behaviour |
|-------|-----------|
| **Grab** | Click and drag; the surface follows the cursor in any 3D direction |
| **Side Scale** | Click a face; the entire side scales uniformly along that axis |
| **Pinch** | Pull vertices toward centre to sharpen. Shift inverts to expand and round |
| **Push** | Push inward along surface normals. Shift pulls outward |
| **Smooth** | Average each vertex toward its neighbours |
| **Flatten** | Project vertices toward a plane at the hit point |
| **Crease** | Pull toward the brush centre to form a ridge |

**Grab — plane projection technique**

Grab is the most involved brush. An invisible plane is created at the hit point, oriented to face the camera. Each frame, the mouse ray projects onto that plane to produce a 3D world-space position. The frame-to-frame delta becomes the movement vector, converted to local space by applying the inverse of the mesh's world matrix. Every vertex within the brush radius moves by that delta, weighted by falloff.

The result is a surface that genuinely follows the cursor in three dimensions.

**Side Scale — axis-aligned face scaling**

Runs outside the per-vertex loop since it affects an entire side rather than a radius. The clicked face normal determines the dominant axis (X, Y, or Z). The mesh splits at its centre on that axis, and every vertex on the clicked side translates uniformly along the normal. Shift targets the opposite side.

Useful after detailed Grab work, when the overall proportions of one face need adjusting without disturbing the local detail.

### Clean Up — Curvature-Aware Laplacian Smoothing

Freehand sculpting leaves surfaces rough. The Clean Up tool smooths them while preserving edges that were created intentionally.

**Algorithm, per pass:**

1. **Compute crease weights** — recompute vertex normals, then compare each vertex's normal against its neighbours'. A dot product near 1 indicates a smooth region (smooth aggressively). A dot product below 0.5 indicates a sharp crease (barely smooth). This is what protects deliberate Pinch and Crease edges from being washed out.

2. **Laplacian smooth** — move each vertex toward the average position of its neighbours, weighted by its crease weight and a per-pass strength that decays across passes so the result converges rather than over-smoothing. New positions compute into a temporary buffer so all vertices derive from the same frame.

3. **Taubin anti-shrink** — standard Laplacian smoothing shrinks a mesh, since every vertex always moves inward toward its neighbour centroid. A final inflation pass moves vertices slightly *away* from their centroids, counteracting the volume loss.

A neighbour map — vertex index to connected vertex indices — is precomputed once from the index buffer for efficiency.

**Strength slider:** 10% → 2 passes (light touch-up) · 50% → 6 passes (moderate) · 100% → 12 passes (heavy polish)

An undo snapshot is saved before the operation runs.

### Material Application in 3D

The same leather, fabric, metal, and wood library, applied as Three.js texture maps via `TextureLoader`. Textures use `RepeatWrapping` with a 2×2 repeat so they tile naturally instead of stretching across the surface.

Materials use `MeshStandardMaterial` (physically based, `metalness: 0.05`, `roughness: 0.8`). `MeshPhysicalMaterial` was avoided since it requires an environment map to render correctly and appears very dark without one.

### Scene Setup

Four-light rig: `AmbientLight` for base illumination, `HemisphereLight` for sky/ground bounce, a directional key light casting `PCFSoftShadowMap` shadows, plus fill and rim lights to define form.

`OrbitControls` handles camera navigation and is disabled during active sculpt or move operations so brush strokes don't orbit the camera. Drag state lives in refs rather than state, since it must be read synchronously inside pointer handlers.

Scene initialisation is wrapped in `requestAnimationFrame` so the container has resolved its CSS dimensions before `clientWidth` and `clientHeight` are read. Canvas CSS uses `position: absolute; top: 0; left: 0` — not `width: 100% !important`, which would override the inline sizing Three.js sets and break the render resolution.

### Additional Controls

- **X / Y / Z scale sliders** — 10% to 400% per axis
- **Undo Stroke** — reverts the last brush operation from the undo stack
- **Remove Part** — deletes the selected part from the scene

---

## Room Visualizer

Places the analysed sketch — with any applied materials — into photorealistic interior environments to evaluate scale and aesthetic fit.

**Route:** `/room-preview`

### Environments

Five AI-generated interiors, each shot at a consistent 100cm camera height with a level horizon, single-point perspective, and a deliberately clear central floor zone.

| Room | Character |
|------|-----------|
| **Nordic** | White walls, pale ash floor, large window, soft daylight |
| **Warm Classic** | Cream walls, dark walnut herringbone, coffered ceiling, chandelier |
| **Industrial** | Exposed grey brick, polished concrete, black steel window frames |
| **Japandi** | Warm greige plaster, light oak, paper pendant, shoji screen |
| **Modern Luxury** | Light travertine tile, recessed lighting, floor-to-ceiling glass |

### Perspective-Accurate Placement

Each room carries calibrated floor-plane constants:

```js
{
  floorTop:   0.52,  // y-fraction where the wall/floor junction sits
  floorLeft:  0.08,  // x-fraction of the floor's left edge at the back wall
  floorRight: 0.92,  // x-fraction of the floor's right edge at the back wall
}
```

These define a trapezoid matching the photo's actual perspective. Screen coordinates map into normalised floor coordinates (`fx` left-to-right, `fy` back-to-front) and back again, so dragging the chair moves it across a plane that genuinely corresponds to the floor in the image.

**Depth scaling:** `0.65×` at the back wall → `1.1×` at the front. A deliberately gentle range — the earlier `0.35×–1.0×` curve made the chair unreadably small when pushed toward the back wall.

### Background Removal

Sketches arrive with white backgrounds, which would occlude the room. `multiply` blend alone fails on the dark Industrial and Warm Classic floors.

Instead, the sketch is pre-processed once on load into an offscreen canvas:

- Luminance computed per pixel as `0.299R + 0.587G + 0.114B`
- Above **240** → fully transparent
- Between **200–240** → proportional alpha for soft anti-aliased edges
- Below **200** → fully opaque (the pencil lines)

The processed canvas then composites cleanly over any background, light or dark.

### Material Layers

Applied textures carry through from the workspace. Since `HTMLImageElement` objects cannot survive React Router state serialisation, only texture `src` strings are passed, and the Room Visualizer reloads the images itself on mount before compositing them clipped to the transformed mask polygons.

### Controls

| Control | Action |
|---------|--------|
| **Drag** | Reposition on the floor plane with automatic depth scaling |
| **Shift + drag** | Raise or lower the chair (Y offset), shadow shrinks as it lifts |
| **Chair Size** | 40%–220% manual scale |
| **Vertical slider** | Precise Y offset, −300 to +50, with Reset |
| **Room thumbnails** | Switch environments from the sidebar |

A soft radial-gradient shadow renders beneath the chair, its opacity and spread tuned per room to match that environment's ambient lighting, and contracting as the chair is lifted off the floor.

---

## Project Structure

```
designable-ai/
├── frontend/
│   ├── public/
│   │   ├── materials/
│   │   │   ├── leather/{Smooth,Stitched,Pebbled,Suede,Rough}/
│   │   │   ├── fabric/{Cotton,Pattern,Tiled,Printed,Woven,...}/
│   │   │   ├── metal/{Brushed,Matte,Rusty,Chrome}/
│   │   │   └── wood/{Walnut,Maple,Oak,Cherry}/
│   │   ├── rooms/
│   │   │   └── room_1.jpeg … room_5.jpeg
│   │   └── hand-pencil.png
│   └── src/
│       ├── pages/
│       │   ├── LandingPage.jsx      # hero, upload, sculpt studio entry
│       │   ├── Dashboard.jsx        # analysis workspace
│       │   ├── SculptStudio.jsx     # 3D sculpting environment
│       │   ├── RoomPreview.jsx      # room visualizer
│       │   ├── Login.jsx
│       │   └── Signup.jsx
│       ├── styles/
│       │   ├── LandingPage.css
│       │   ├── SculptStudio.css
│       │   └── RoomPreview.css
│       ├── App.jsx                  # routing
│       ├── App.css                  # global styles
│       └── main.jsx                 # entry point
│
└── backend/
    ├── main.py                      # FastAPI app and endpoints
    ├── yolo_inference.py            # model loading and inference
    ├── classifier.py                # furniture type classification
    ├── geometry_analyzer.py         # measurements, descriptors, flags
    ├── prompt_builder.py            # structured LLM prompt construction
    ├── gemini_client.py             # Gemini API wrapper
    ├── ocr.py                       # measurement label extraction
    └── requirements.txt
```

### Routes

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | LandingPage | Hero, sketch upload, sculpt studio entry |
| `/dashboard` | Dashboard | Analysis workspace |
| `/sculpt` | SculptStudio | 3D sculpting environment |
| `/room-preview` | RoomPreview | Room visualizer |
| `/login` · `/signup` | Auth | Authentication |

State passes between routes via React Router location state. Direct navigation without required state redirects to the appropriate parent route.

---

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:

```env
GEMINI_API_KEY=your_key_here
ROBOFLOW_API_KEY=your_key_here
MODEL_ENDPOINT=your_model_endpoint
```

Run:

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Create `.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Run:

```bash
npm run dev
```

Open `http://localhost:5173`.

---

## API Reference

### `POST /analyze-chair`

Primary analysis endpoint.

**Request:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | Sketch image (JPG or PNG) |
| `furniture_type` | String | `chair` or `table` |

**Response:**

```json
{
  "session_id": "uuid",
  "identified_type": "Eames Lounge Chair",
  "is_hybrid": false,
  "influences": [],
  "furniture_type": "chair",
  "image_dimensions": { "width": 1024, "height": 1024 },
  "scale_factor": { "px_per_mm": 0.5, "source": "ocr_seat_height" },
  "ocr_measurements": {
    "SH": { "value": 43, "unit": "cm" },
    "SD": { "value": 50, "unit": "cm" }
  },
  "parts_with_traits": [
    {
      "label": "seat",
      "confidence": 0.94,
      "mask": [[120, 340], [220, 340], "…"],
      "bbox": [120, 340, 100, 80],
      "geometry": {
        "measurements": {
          "width_mm": 480,
          "width_source": "calculated",
          "height_mm": 500,
          "height_source": "ocr",
          "area_mm2": 240000,
          "compactness": 0.87,
          "scale_vs_seat": 1.0
        },
        "shape": {
          "contour_smoothness": {
            "label": "Organic",
            "detail": "Flowing contour with minimal angular transitions",
            "design_interpretation": "…",
            "ergonomic_interpretation": "…"
          }
        },
        "ergonomic_flags": [
          {
            "field": "seat_depth",
            "measured": "500mm",
            "benchmark": "400-480mm",
            "status": "warning",
            "note": "…"
          }
        ],
        "_raw": { "solidity": 0.91, "aspect_ratio": 0.96 }
      }
    }
  ],
  "assistant_reply": "Markdown-formatted design analysis…",
  "phase": "ANALYSIS"
}
```

---

### `POST /recalculate-geometry`

Re-runs geometry analysis on modified mask polygons after interactive rescaling.

**Request:**

```json
{
  "parts": [
    {
      "label": "seat",
      "mask": [[125, 335], "…"],
      "scale_x": 1.15,
      "scale_y": 1.0
    }
  ],
  "px_per_mm": 0.5,
  "seat_meta": null
}
```

**Response:**

```json
{
  "parts": [
    { "label": "seat", "geometry": { "measurements": {}, "shape": {}, "ergonomic_flags": [] } }
  ]
}
```

---

### `POST /ai-feedback`

Requests an LLM assessment of the modification set.

**Request:**

```json
{
  "session_id": "uuid",
  "chair_type": "Eames Lounge Chair",
  "is_hybrid": false,
  "influences": [],
  "modifications": [
    {
      "label": "seat",
      "changes": { "scaleX": 1.15, "scaleY": 1.0 },
      "original_measurements": {},
      "new_measurements": {},
      "original_flags": [],
      "new_flags": []
    }
  ],
  "classification_data": {}
}
```

**Response:**

```json
{ "feedback": "Markdown-formatted assessment of the modifications…" }
```

---

### `POST /chat`

Continues the Design Assistant conversation with full analysis context.

**Request:**

```json
{
  "message": "Why did you flag the backrest?",
  "session_id": "uuid",
  "phase": "ANALYSIS",
  "classification_data": {}
}
```

**Response:**

```json
{ "assistant_reply": "…", "phase": "ANALYSIS" }
```

---

## Design System

| Token | Value |
|-------|-------|
| Background | `#0f0e0c` |
| Surface | `#1a1714` |
| Text | `#f5f1eb` |
| Accent (primary) | `#c8602a` — terracotta |
| Accent (secondary) | `#6b8f71` — sage |
| Display type | Cormorant Garamond |
| Mono / UI type | DM Mono |


