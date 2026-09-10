import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../RoomPreview.css";

/* ═══════════════════════════════════════════════════════════════════════
   ROOMS — each has a photo path + calibrated floor zone
   floorTop: y fraction (0-1) where the floor begins (wall/floor junction)
   floorLeft/Right: x fraction of floor edges at the back wall
   These are calibrated by eye to match each photo's perspective
   ═══════════════════════════════════════════════════════════════════════ */

const ROOMS = [
  {
    id: "nordic",
    name: "Nordic",
    label: "Nordic Minimal",
    src: "/rooms/room_1.jpeg",
    floorTop: 0.52,     // floor starts at 52% down the image
    floorLeft: 0.08,    // left edge of floor at back
    floorRight: 0.92,   // right edge of floor at back
    shadow: "rgba(80,60,40,0.18)",
    shadowFloor: "rgba(80,60,40,0.08)",
  },
  {
    id: "warm",
    name: "Warm Classic",
    label: "Warm Classic",
    src: "/rooms/room_2.jpeg",
    floorTop: 0.56,
    floorLeft: 0.05,
    floorRight: 0.95,
    shadow: "rgba(40,20,5,0.25)",
    shadowFloor: "rgba(40,20,5,0.12)",
  },
  {
    id: "industrial",
    name: "Industrial",
    label: "Industrial Loft",
    src: "/rooms/room_3.png",
    floorTop: 0.58,
    floorLeft: 0.04,
    floorRight: 0.96,
    shadow: "rgba(0,0,0,0.35)",
    shadowFloor: "rgba(0,0,0,0.18)",
  },
  {
    id: "japandi",
    name: "Japandi",
    label: "Japandi",
    src: "/rooms/room_4.jpeg",
    floorTop: 0.54,
    floorLeft: 0.06,
    floorRight: 0.94,
    shadow: "rgba(50,40,30,0.18)",
    shadowFloor: "rgba(50,40,30,0.08)",
  },
  {
    id: "luxury",
    name: "Modern Luxury",
    label: "Modern Luxury",
    src: "/rooms/room_5.jpeg",
    floorTop: 0.50,
    floorLeft: 0.05,
    floorRight: 0.95,
    shadow: "rgba(30,25,20,0.22)",
    shadowFloor: "rgba(30,25,20,0.1)",
  },
];

/* ═══════════════════════════════════════════════════════════════════════
   FLOOR PLANE MATH — calibrated per room photo
   fx: 0=left edge, 1=right edge of floor
   fy: 0=back wall, 1=front (camera)
   Returns pixel x,y on canvas and depth scale factor
   ═══════════════════════════════════════════════════════════════════════ */

function floorToScreen(fx, fy, canvasW, canvasH, room) {
  const yBack = room.floorTop * canvasH;
  const yFront = canvasH;
  const y = yBack + (yFront - yBack) * fy;

  // Floor edges converge at back wall, spread to full width at front
  const leftBack  = room.floorLeft  * canvasW;
  const rightBack = room.floorRight * canvasW;
  const leftFront  = 0;
  const rightFront = canvasW;

  const leftEdge  = leftBack  + (leftFront  - leftBack)  * fy;
  const rightEdge = rightBack + (rightFront - rightBack) * fy;
  const x = leftEdge + (rightEdge - leftEdge) * fx;

  // Depth scale: gentler range so chair stays large enough at back
  // 0.65 at back wall, 1.1 at front — much more natural than 0.35-1.0
  const depth = 0.65 + 0.45 * fy;

  return { x, y, depth };
}

function screenToFloor(sx, sy, canvasW, canvasH, room) {
  const yBack = room.floorTop * canvasH;
  const yFront = canvasH;
  if (sy < yBack) return null;

  const fy = Math.max(0, Math.min(1, (sy - yBack) / (yFront - yBack)));

  const leftBack   = room.floorLeft  * canvasW;
  const rightBack  = room.floorRight * canvasW;
  const leftFront  = 0;
  const rightFront = canvasW;
  const leftEdge   = leftBack  + (leftFront  - leftBack)  * fy;
  const rightEdge  = rightBack + (rightFront - rightBack) * fy;

  const fx = Math.max(0.02, Math.min(0.98, (sx - leftEdge) / (rightEdge - leftEdge)));
  return { fx, fy };
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════ */

export default function RoomPreview() {
  const navigate = useNavigate();
  const location = useLocation();
 const { imgUrl, curParts, serializableTextures, imgD } = location.state || {};
const [textures, setTextures] = useState({});

// Reload texture images from src strings
useEffect(() => {
  if (!serializableTextures) return;
  const loaded = {};
  let pending = Object.keys(serializableTextures).length;
  if (pending === 0) return;
  Object.entries(serializableTextures).forEach(([label, { src }]) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      loaded[label] = { src, image: img };
      pending--;
      if (pending === 0) setTextures({ ...loaded });
    };
    img.src = src;
  });
}, [serializableTextures]);

  const [imgObj, setImgObj] = useState(null);
  const [roomIdx, setRoomIdx] = useState(0);
  const [chairPos, setChairPos] = useState({ fx: 0.5, fy: 0.6 });
  const [chairSize, setChairSize] = useState(1.0);
  
  const [chairY, setChairY] = useState(0); // pixel offset up/down
    const lastPointerY = useRef(0);
  const [isDragging, setIsDragging] = useState(false);
  const [roomImgs, setRoomImgs] = useState({});

  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const dragRef = useRef({ active: false });

  // Load chair image
  // Load chair image and pre-process to remove white background
  const processedCanvasRef = useRef(null);

  useEffect(() => {
    if (!imgUrl) { navigate("/dashboard", { replace: true }); return; }
    const img = new Image();
    img.onload = () => {
      setImgObj(img);
      // Create offscreen canvas with white background removed
      const oc = document.createElement("canvas");
      oc.width = img.naturalWidth;
      oc.height = img.naturalHeight;
      const ctx = oc.getContext("2d");
      ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, oc.width, oc.height);
      const d = data.data;
      for (let i = 0; i < d.length; i += 4) {
        const r = d[i], g = d[i+1], b = d[i+2];
        // Brightness threshold: pixels brighter than 240 become transparent
        // Edge pixels (220-240) get partial transparency for smooth edges
        const brightness = (r * 0.299 + g * 0.587 + b * 0.114);
        if (brightness > 240) {
          d[i+3] = 0; // fully transparent
        } else if (brightness > 200) {
          // Soft edge — partial transparency
          d[i+3] = Math.round(255 * (1 - (brightness - 200) / 40));
        }
        // Dark pixels (lines) stay fully opaque
      }
      ctx.putImageData(data, 0, 0);
      processedCanvasRef.current = oc;
      setImgObj(img); // trigger redraw
    };
    img.src = imgUrl;
  }, [imgUrl, navigate]);
  // Preload all room images
  useEffect(() => {
    ROOMS.forEach(r => {
      const img = new Image();
      img.onload = () => setRoomImgs(prev => ({ ...prev, [r.id]: img }));
      img.src = r.src;
    });
  }, []);

  const room = ROOMS[roomIdx];

  /* ── Draw chair on canvas ─────────────────────────────────────── */
  const drawChair = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imgObj) return;
    const ctx = canvas.getContext("2d");
    const cw = canvas.width, ch = canvas.height;

    ctx.clearRect(0, 0, cw, ch);

    const { x, y, depth } = floorToScreen(chairPos.fx, chairPos.fy, cw, ch, room);

    // Base height: 280px at depth 1.0. Scales with depth and user size slider.
    const baseH = 280 * depth * chairSize;
    const aspect = imgD ? imgD.width / imgD.height : 1;
    const chairW = baseH * aspect;
    const chairH = baseH;

    // ── Shadow ────────────────────────────────────────────────────
    ctx.save();
    // Soft elliptical shadow on floor
    const sGrad = ctx.createRadialGradient(x, y, 0, x, y, chairW * 0.55);
    sGrad.addColorStop(0, room.shadow);
    sGrad.addColorStop(0.6, room.shadowFloor);
    sGrad.addColorStop(1, "transparent");
    ctx.fillStyle = sGrad;
    ctx.beginPath();
   ctx.ellipse(x, y + 2, chairW * 0.48 * (1 - Math.max(0, -chairY) / 300), Math.max(4, 18 * depth), 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // ── Chair sketch — multiply blend ─────────────────────────────
   // ── Chair sketch — draw with pre-processed transparent background
   const chairSrc = processedCanvasRef.current || imgObj;
    const drawY = y + chairY; // apply vertical offset
    ctx.save();
    ctx.drawImage(chairSrc, x - chairW / 2, drawY - chairH, chairW, chairH);
    ctx.restore();

    // ── Texture layers ────────────────────────────────────────────
    if (curParts && textures && imgD) {
      Object.entries(textures).forEach(([label, tex]) => {
        if (!tex.image) return;
        const part = curParts.find(p => p.label === label);
        if (!part) return;
        const mk = part.cm || part.mask;
        if (!mk || mk.length < 3) return;

        const pts = mk.map(([px, py]) => {
          const nx = px / imgD.width;
          const ny = py / imgD.height;
           const cx = x - chairW / 2 + nx * chairW;
          const cy = y - chairH + ny * chairH;
          return [cx, cy];
        });

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
        ctx.closePath();
        ctx.clip();
        try {
          const pattern = ctx.createPattern(tex.image, "repeat");
          if (pattern) {
            const sc = (chairH / imgD.height) * 0.25;
            pattern.setTransform(new DOMMatrix().scale(sc, sc));
            ctx.fillStyle = pattern;
            ctx.fillRect(x - chairW, y - chairH * 2, chairW * 2, chairH * 2);
          }
        } catch (e) {}
     ctx.globalCompositeOperation = "multiply";
        ctx.drawImage(chairSrc, x - chairW / 2, drawY - chairH, chairW, chairH);
        ctx.restore();
      });
    }
 }, [imgObj, chairPos, chairSize, chairY, room, curParts, textures, imgD, processedCanvasRef]);

  useEffect(() => { drawChair(); }, [drawChair]);

  /* ── Canvas resize ─────────────────────────────────────────────── */
  useEffect(() => {
    const resize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      drawChair();
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [drawChair]);

  /* ── Pointer handlers ──────────────────────────────────────────── */
  const handlePointerDown = useCallback((e) => {
    dragRef.current.active = true;
    dragRef.current.shift = e.shiftKey;
    lastPointerY.current = e.clientY;
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback((e) => {
    if (!dragRef.current.active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (e.shiftKey || dragRef.current.shift) {
      // Shift held — move chair up/down on Y axis
      const dy = e.clientY - lastPointerY.current;
      lastPointerY.current = e.clientY;
      setChairY(prev => prev + dy);
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const sx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const sy = (e.clientY - rect.top) * (canvas.height / rect.height);
    const floor = screenToFloor(sx, sy, canvas.width, canvas.height, room);
    if (floor) setChairPos(floor);
    lastPointerY.current = e.clientY;
  }, [room]);

  const handlePointerUp = useCallback(() => {
    dragRef.current.active = false;
    setIsDragging(false);
  }, []);

  if (!imgObj) return (
    <div className="rp-loading">Loading room...</div>
  );

  return (
    <div className="rp-overlay">
      {/* Header */}
      <div className="rp-header">
        <span className="rp-logo">Designable<span className="rp-dot">.</span></span>
        <span className="rp-title">Room Visualizer</span>

        {/* Room tabs */}
       

        <button className="rp-close" onClick={() => navigate(-1)}>← Back to Dashboard</button>
      </div>

      {/* Main */}
      <div className="rp-main">
        <div className="rp-room-bg" ref={containerRef}>
          {/* Room photo */}
          <img
            src={room.src}
            alt={room.label}
            className="rp-room-photo"
            draggable="false"
          />

          {/* Chair canvas overlay */}
          <canvas
            ref={canvasRef}
            className={`rp-chair-canvas ${isDragging ? "grabbing" : ""}`}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          />

          {/* Room label badge */}
          <div className="rp-room-badge">{room.label}</div>

          {/* Drag hint */}
          {!isDragging && (
            <div className="rp-drag-hint">Drag to position the chair</div>
          )}
        </div>

        {/* Controls */}
        <aside className="rp-controls">
          <div className="rp-ctrl-section">
            <div className="rp-ctrl-label">Chair Size</div>
            <div className="rp-size-row">
              <input type="range" min="40" max="220" value={Math.round(chairSize * 100)}
                onChange={e => setChairSize(+e.target.value / 100)}
                className="rp-slider"/>
              <span className="rp-size-val">{Math.round(chairSize * 100)}%</span>
            </div>
          </div>

          

          <div className="rp-ctrl-section">
            <div className="rp-ctrl-label">Vertical</div>
            <div className="rp-size-row">
              <input type="range" min="-300" max="50" value={-chairY}
                onChange={e => setChairY(-e.target.value)}
                className="rp-slider"/>
              <button style={{
                background:"transparent",border:"1px solid rgba(245,241,235,0.08)",
                borderRadius:"2px",color:"rgba(245,241,235,0.4)",
                fontFamily:"DM Mono,monospace",fontSize:"0.55rem",
                letterSpacing:"0.08em",cursor:"pointer",padding:"4px 8px",
                whiteSpace:"nowrap",flexShrink:0
              }} onClick={()=>setChairY(0)}>Reset</button>
            </div>
            <div className="rp-pos-hint">Or hold Shift + drag</div>
          </div>

         

          <div className="rp-ctrl-section">
            <div className="rp-ctrl-label">Rooms</div>
            <div className="rp-room-thumbs">
              {ROOMS.map((r, i) => (
                <button key={r.id} className={`rp-room-thumb ${roomIdx===i?"active":""}`}
                  onClick={() => setRoomIdx(i)} title={r.label}>
                  <img src={r.src} alt={r.label} draggable="false"/>
                  <span>{r.name}</span>
                </button>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}