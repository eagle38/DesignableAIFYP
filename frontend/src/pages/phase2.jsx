import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import "../SculptStudio.css";

const CLAY="#b8a18e",CLAY_HOVER="#c9b29f",CLAY_SEL="#d4a870",GRID_SIZE=20;
const PART_DEFS={seat:{y:2.5,snapRole:"root"},backrest:{y:3.5,snapRole:"back"},headrest:{y:5.8,snapRole:"top"},armrest_l:{y:3.2,snapRole:"left"},armrest_r:{y:3.2,snapRole:"right"},leg:{y:0,snapRole:"bottom"},lumbar:{y:3.0,snapRole:"lumbar"}};
const SNAP_ZONES={back:{x:0,y:1.0,z:-1.3},top:{x:0,y:3.3,z:-1.3},left:{x:-1.7,y:0.7,z:0},right:{x:1.7,y:0.7,z:0},lumbar:{x:0,y:0.5,z:-1.2},leg_fl:{x:-1.2,y:-1.25,z:1.0},leg_fr:{x:1.2,y:-1.25,z:1.0},leg_bl:{x:-1.2,y:-1.25,z:-1.0},leg_br:{x:1.2,y:-1.25,z:-1.0}};

/* Brush types — grab and pinch are the primary intuitive tools */
const BRUSH_TYPES = ["grab","sidescale","pinch","push","smooth","flatten","crease"];
const BRUSH_LABELS = {grab:"Grab",sidescale:"Side Scale",pinch:"Pinch",push:"Push",smooth:"Smooth",flatten:"Flatten",crease:"Crease"};
const BRUSH_HINTS = {
  grab:"Click & drag to pull/push the surface in any direction",
  sidescale:"Click a face & drag to scale that entire side uniformly. Shift = opposite side",
  pinch:"Click to sharpen edges. Shift+click to round/expand",
  push:"Click to push in. Shift+click to pull out",
  smooth:"Drag over rough areas to smooth them",
  flatten:"Drag to create flat surfaces",
  crease:"Drag to create sharp ridges",
};

function clayMat(c=CLAY){return new THREE.MeshStandardMaterial({color:new THREE.Color(c),metalness:0.05,roughness:0.7});}
function gaussian(d,r){return Math.exp(-(d*d)/(2*(r*0.5)*(r*0.5)));}
function getNeighborMap(geo){const idx=geo.index,count=geo.attributes.position.count,map=Array.from({length:count},()=>[]);if(idx){const a=idx.array;for(let i=0;i<a.length;i+=3){const x=a[i],y=a[i+1],z=a[i+2];[x,y,z].forEach((v,vi)=>{const others=[x,y,z].filter((_,oi)=>oi!==vi);others.forEach(o=>{if(!map[v].includes(o))map[v].push(o);});});}}return map;}
function clonePos(geo){return new Float32Array(geo.attributes.position.array);}

// Geometry builders
function buildFlatSeat(){const g=new THREE.BoxGeometry(3,0.3,2.8,16,4,16);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);const e=Math.min(Math.abs(Math.abs(x)-1.5),Math.abs(Math.abs(z)-1.4));if(e<0.2&&y>0.1)p.setY(i,y-(0.2-e)*0.3);}g.computeVertexNormals();return g;}
function buildBucketSeat(){const g=new THREE.BoxGeometry(3,0.5,2.8,20,6,20);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);if(y>0){const d=Math.sqrt((x/1.5)**2+(z/1.4)**2);p.setY(i,y-Math.max(0,1-d)*0.25);}}g.computeVertexNormals();return g;}
function buildContouredSeat(){const g=new THREE.BoxGeometry(3.2,0.4,3.0,20,6,20);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);if(y>0){p.setY(i,y-Math.max(0,(1-(x/1.6)**2)*0.2-(z/1.5)*0.08));if(z>1.2)p.setY(i,y-(z-1.2)*0.15);}}g.computeVertexNormals();return g;}
function buildRoundSeat(){const g=new THREE.CylinderGeometry(1.5,1.5,0.3,32,6);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);if(y>0.1)p.setY(i,y-Math.max(0,1-Math.sqrt(x*x+z*z)/1.5)*0.1);}g.computeVertexNormals();return g;}
function buildStraightBack(){return new THREE.BoxGeometry(2.8,2.5,0.25,16,16,4);}
function buildCurvedBack(){const g=new THREE.BoxGeometry(2.8,2.8,0.3,16,16,6);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);const t=(y+1.4)/2.8;p.setZ(i,z-Math.sin(t*Math.PI)*0.3+(1-Math.abs(x/1.4))*0.1);}g.computeVertexNormals();return g;}
function buildHighBack(){const g=new THREE.BoxGeometry(2.6,3.8,0.25,14,20,4);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);const t=(y+1.9)/3.8;p.setX(i,x*(1-t*0.15));p.setZ(i,z-t*0.4);}g.computeVertexNormals();return g;}
function buildShellBack(){const g=new THREE.SphereGeometry(1.8,20,20,0,Math.PI*2,0,Math.PI*0.6);const p=g.attributes.position;for(let i=0;i<p.count;i++)p.setZ(i,Math.min(p.getZ(i),0.3));g.computeVertexNormals();g.scale(1,1.4,0.8);return g;}
function buildPillowHead(){const g=new THREE.BoxGeometry(1.8,0.8,0.35,12,8,6);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);p.setZ(i,z*Math.max(0.3,Math.min(1,(1-(x/0.9)**4)*(1-(y/0.4)**4))));}g.computeVertexNormals();return g;}
function buildCradleHead(){const g=new THREE.BoxGeometry(1.6,0.9,0.4,12,8,8);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);if(z>0)p.setZ(i,z-Math.max(0,(1-(x/0.8)**2)*(1-(y/0.45)**2))*0.15);}g.computeVertexNormals();return g;}
function buildTrackArm(){const g=new THREE.BoxGeometry(0.4,0.25,2.2,6,4,14);g.computeVertexNormals();return g;}
function buildRolledArm(){const g=new THREE.CylinderGeometry(0.25,0.25,2.2,16,10,false,0,Math.PI);g.rotateX(Math.PI/2);g.rotateZ(Math.PI/2);return g;}
function buildSculptedArm(){const g=new THREE.BoxGeometry(0.45,0.3,2.4,8,6,16);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);p.setY(i,y+Math.sin(z/1.2*Math.PI*0.5)*0.05);if(z>0.8){const t=1-(z-0.8)/1.6*0.4;p.setX(i,x*t);p.setY(i,p.getY(i)*t);}}g.computeVertexNormals();return g;}
function buildStraightLeg(){return new THREE.CylinderGeometry(0.12,0.1,2.5,8,8);}
function buildTaperedLeg(){return new THREE.CylinderGeometry(0.15,0.08,2.5,8,8);}
function buildSplayedLeg(){return new THREE.CylinderGeometry(0.12,0.1,2.6,8,8);}
function buildLumbarPad(){const g=new THREE.BoxGeometry(2.0,0.8,0.3,12,8,6);const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);if(z>0)p.setZ(i,z+Math.max(0,(1-(x/1.0)**2)*(1-(y/0.4)**2))*0.12);}g.computeVertexNormals();return g;}

const INVENTORY=[
  {category:"Seats",items:[{id:"seat_blob",name:"Basic Blob",type:"seat",build:()=>new THREE.SphereGeometry(1.5,20,20),scaleY:0.25},{id:"seat_flat",name:"Flat Platform",type:"seat",build:buildFlatSeat},{id:"seat_bucket",name:"Bucket",type:"seat",build:buildBucketSeat},{id:"seat_contour",name:"Contoured",type:"seat",build:buildContouredSeat},{id:"seat_round",name:"Round Stool",type:"seat",build:buildRoundSeat}]},
  {category:"Backrests",items:[{id:"back_blob",name:"Basic Blob",type:"backrest",build:()=>new THREE.SphereGeometry(1.4,18,18),scaleY:1.8,scaleZ:0.2},{id:"back_straight",name:"Straight",type:"backrest",build:buildStraightBack},{id:"back_curved",name:"Curved",type:"backrest",build:buildCurvedBack},{id:"back_high",name:"High-Back",type:"backrest",build:buildHighBack},{id:"back_shell",name:"Shell",type:"backrest",build:buildShellBack}]},
  {category:"Headrests",items:[{id:"head_blob",name:"Basic Blob",type:"headrest",build:()=>new THREE.SphereGeometry(0.6,14,14),scaleX:1.5,scaleZ:0.5},{id:"head_pillow",name:"Pillow",type:"headrest",build:buildPillowHead},{id:"head_cradle",name:"Cradle",type:"headrest",build:buildCradleHead}]},
  {category:"Armrests",items:[{id:"arm_blob",name:"Basic Blob",type:"armrest_l",build:()=>new THREE.SphereGeometry(0.5,12,12),scaleX:0.5,scaleZ:2.2},{id:"arm_track",name:"Track",type:"armrest_l",build:buildTrackArm},{id:"arm_rolled",name:"Rolled",type:"armrest_l",build:buildRolledArm},{id:"arm_sculpted",name:"Sculpted",type:"armrest_l",build:buildSculptedArm}]},
  {category:"Legs",items:[{id:"leg_blob",name:"Basic Blob",type:"leg",build:()=>new THREE.SphereGeometry(0.3,10,10),scaleY:4},{id:"leg_straight",name:"Straight",type:"leg",build:buildStraightLeg},{id:"leg_tapered",name:"Tapered",type:"leg",build:buildTaperedLeg},{id:"leg_splayed",name:"Splayed",type:"leg",build:buildSplayedLeg}]},
  {category:"Support",items:[{id:"lumbar_pad",name:"Lumbar Pad",type:"lumbar",build:buildLumbarPad}]},
];

/* ═══════════════════════════════════════════════════════════════════════ */

export default function SculptStudio(){
  const navigate=useNavigate();
  const mountRef=useRef(null);
  const sceneRef=useRef(null);
  const cameraRef=useRef(null);
  const rendererRef=useRef(null);
  const controlsRef=useRef(null);
  const rafRef=useRef(null);
  const partsRef=useRef([]);
  const snapGlowsRef=useRef([]);
  const raycaster=useRef(new THREE.Raycaster());
  const mouse=useRef(new THREE.Vector2());
  const partIdCounter=useRef(0);
  const brushIndRef=useRef(null);

  const[placedParts,setPlacedParts]=useState([]);
  const[selectedPartId,setSelectedPartId]=useState(null);
  const[openCat,setOpenCat]=useState(null);
  const[hasSeat,setHasSeat]=useState(false);
  const[toolMode,setToolMode]=useState("select");
  const[brushType,setBrushType]=useState("grab"); // default to grab — most intuitive
  const[brushSize,setBrushSize]=useState(0.8);
  const[brushStrength,setBrushStrength]=useState(0.5);
  const[partScale,setPartScale]=useState({x:100,y:100,z:100});

  const sculptingRef=useRef(false);
  const movingRef=useRef({active:false,plane:null,offset:new THREE.Vector3()});
  const undoStackRef=useRef([]);
  const neighborMapsRef=useRef({});

  // Grab tool state — needs to track initial hit point and compute 3D deltas from mouse movement
  const grabRef=useRef({
    active:false,
    hitPointWorld:new THREE.Vector3(),   // initial hit point in world space
    hitPointLocal:new THREE.Vector3(),   // initial hit point in local space
    plane:null,                          // plane for projecting mouse movement
    lastWorld:new THREE.Vector3(),       // last projected world point (for delta)
    mesh:null,                           // mesh being grabbed
    basePositions:null,                  // Float32Array — positions at start of grab
  });

  /* ── Scene init ─────────────────────────────────────────────────── */
  useEffect(()=>{
    if(!mountRef.current)return;
    const initTimer=requestAnimationFrame(()=>{
      const ct=mountRef.current;if(!ct)return;
      const w=ct.clientWidth,h=ct.clientHeight;if(!w||!h)return;

      const scene=new THREE.Scene();scene.background=new THREE.Color("#0f0e0c");sceneRef.current=scene;
      const camera=new THREE.PerspectiveCamera(45,w/h,0.1,100);camera.position.set(6,5,8);camera.lookAt(0,2,0);cameraRef.current=camera;
      const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(w,h);renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;ct.appendChild(renderer.domElement);rendererRef.current=renderer;
      const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=0.08;controls.target.set(0,2,0);controls.minDistance=3;controls.maxDistance=25;controls.maxPolarAngle=Math.PI*0.85;controlsRef.current=controls;

      scene.add(new THREE.AmbientLight(0xfff5eb,0.6));
      scene.add(new THREE.HemisphereLight(0xfff5eb,0x1a1714,0.5));
      const key=new THREE.DirectionalLight(0xfff5eb,1.2);key.position.set(5,8,4);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.near=1;key.shadow.camera.far=20;key.shadow.camera.left=-6;key.shadow.camera.right=6;key.shadow.camera.top=6;key.shadow.camera.bottom=-6;scene.add(key);
      const fill=new THREE.DirectionalLight(0xb8c8d8,0.5);fill.position.set(-3,4,-2);scene.add(fill);
      const rim=new THREE.DirectionalLight(0xffe8d0,0.4);rim.position.set(0,1,-5);scene.add(rim);

      const floor=new THREE.Mesh(new THREE.PlaneGeometry(GRID_SIZE,GRID_SIZE),new THREE.MeshStandardMaterial({color:"#1a1916",metalness:0.1,roughness:0.95}));
      floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;scene.add(floor);
      const lm=new THREE.LineBasicMaterial({color:0x2a2826,transparent:true,opacity:0.5});
      for(let i=-GRID_SIZE/2;i<=GRID_SIZE/2;i++){
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(i,0.01,-GRID_SIZE/2),new THREE.Vector3(i,0.01,GRID_SIZE/2)]),lm));
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-GRID_SIZE/2,0.01,i),new THREE.Vector3(GRID_SIZE/2,0.01,i)]),lm));
      }

      const bi=new THREE.Mesh(new THREE.RingGeometry(0.75,0.8,32),new THREE.MeshBasicMaterial({color:0xc8602a,transparent:true,opacity:0.5,side:THREE.DoubleSide,depthTest:false}));
      bi.visible=false;scene.add(bi);brushIndRef.current=bi;

      console.log("Scene init OK. Canvas:",w,"x",h);

      (function animate(){rafRef.current=requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);})();

      const onResize=()=>{const w2=ct.clientWidth,h2=ct.clientHeight;if(!w2||!h2)return;camera.aspect=w2/h2;camera.updateProjectionMatrix();renderer.setSize(w2,h2);};
      window.addEventListener("resize",onResize);
      ct._cleanup=()=>{window.removeEventListener("resize",onResize);cancelAnimationFrame(rafRef.current);renderer.dispose();controls.dispose();if(ct.contains(renderer.domElement))ct.removeChild(renderer.domElement);};
    });
    return()=>{cancelAnimationFrame(initTimer);if(mountRef.current?._cleanup)mountRef.current._cleanup();};
  },[]);

  useEffect(()=>{const bi=brushIndRef.current;if(!bi||!sceneRef.current)return;sceneRef.current.remove(bi);bi.geometry.dispose();bi.geometry=new THREE.RingGeometry(brushSize*0.95,brushSize,32);sceneRef.current.add(bi);},[brushSize]);

  /* ── Helpers ─────────────────────────────────────────────────────── */
  const showSnapZones=useCallback((pt)=>{if(!sceneRef.current)return;snapGlowsRef.current.forEach(g=>sceneRef.current.remove(g));snapGlowsRef.current=[];if(!hasSeat&&pt!=="seat")return;let zones=[];if(pt==="backrest")zones=[SNAP_ZONES.back];else if(pt==="headrest")zones=[SNAP_ZONES.top];else if(pt==="armrest_l")zones=[SNAP_ZONES.left];else if(pt==="leg")zones=[SNAP_ZONES.leg_fl,SNAP_ZONES.leg_fr,SNAP_ZONES.leg_bl,SNAP_ZONES.leg_br];else if(pt==="lumbar")zones=[SNAP_ZONES.lumbar];zones.forEach(z=>{const g=new THREE.Mesh(new THREE.SphereGeometry(0.3,16,16),new THREE.MeshBasicMaterial({color:0xc8602a,transparent:true,opacity:0.2}));g.position.set(z.x,z.y+2.5,z.z);sceneRef.current.add(g);snapGlowsRef.current.push(g);});},[hasSeat]);
  const hideSnapZones=useCallback(()=>{if(!sceneRef.current)return;snapGlowsRef.current.forEach(g=>sceneRef.current.remove(g));snapGlowsRef.current=[];},[]);

  const placePart=useCallback((item)=>{
    if(!sceneRef.current)return;
    const id=`part_${partIdCounter.current++}`;
    const geo=item.build();geo.computeVertexNormals();
    const mesh=new THREE.Mesh(geo,clayMat());
    if(item.scaleX)mesh.scale.x=item.scaleX;if(item.scaleY)mesh.scale.y=item.scaleY;if(item.scaleZ)mesh.scale.z=item.scaleZ;
    mesh.castShadow=true;mesh.receiveShadow=true;
    let pt=item.type;
    if(pt==="armrest_l"&&partsRef.current.find(p=>p.type==="armrest_l"))pt="armrest_r";
    const def=PART_DEFS[pt]||PART_DEFS.seat;
    if(hasSeat&&pt!=="seat"){let sp;if(pt==="leg"){const lc=partsRef.current.filter(p=>p.type==="leg").length;sp=SNAP_ZONES[["leg_fl","leg_fr","leg_bl","leg_br"][lc%4]];}else if(pt==="armrest_r")sp=SNAP_ZONES.right;else sp=SNAP_ZONES[PART_DEFS[pt]?.snapRole||"back"];if(sp)mesh.position.set(sp.x,sp.y+2.5,sp.z);else mesh.position.set(0,def.y,0);}else mesh.position.set(0,def.y,0);
    mesh.userData={id,type:pt,inventoryId:item.id};sceneRef.current.add(mesh);
    console.log("Placed",item.name,"at",mesh.position.toArray(),"scale",mesh.scale.toArray());
    neighborMapsRef.current[id]=getNeighborMap(geo);
    undoStackRef.current.push({id,positions:clonePos(geo)});
    partsRef.current.push({id,type:pt,inventoryId:item.id,mesh});
    if(pt==="seat")setHasSeat(true);
    setPlacedParts(prev=>[...prev,{id,type:pt,name:item.name}]);
    setSelectedPartId(id);setToolMode("select");hideSnapZones();
    if(controlsRef.current){controlsRef.current.target.copy(mesh.position);controlsRef.current.update();}
  },[hasSeat,hideSnapZones]);

  const deleteSelected=useCallback(()=>{if(!selectedPartId||!sceneRef.current)return;const idx=partsRef.current.findIndex(p=>p.id===selectedPartId);if(idx===-1)return;const part=partsRef.current[idx];sceneRef.current.remove(part.mesh);part.mesh.geometry?.dispose();part.mesh.material?.dispose();partsRef.current.splice(idx,1);delete neighborMapsRef.current[selectedPartId];if(part.type==="seat")setHasSeat(partsRef.current.some(p=>p.type==="seat"));setPlacedParts(prev=>prev.filter(p=>p.id!==selectedPartId));setSelectedPartId(null);setToolMode("select");},[selectedPartId]);

  const undoSculpt=useCallback(()=>{if(!selectedPartId)return;const stack=undoStackRef.current.filter(s=>s.id===selectedPartId);if(!stack.length)return;const last=stack[stack.length-1];const part=partsRef.current.find(p=>p.id===selectedPartId);if(!part)return;part.mesh.geometry.attributes.position.array.set(last.positions);part.mesh.geometry.attributes.position.needsUpdate=true;part.mesh.geometry.computeVertexNormals();const gi=undoStackRef.current.lastIndexOf(last);if(gi>=0)undoStackRef.current.splice(gi,1);},[selectedPartId]);

  /* ── Clean Up — curvature-aware Laplacian smooth ────────────────── */
  const[cleanupStrength,setCleanupStrength]=useState(50); // 0-100, maps to 2-12 passes

  const cleanupMesh=useCallback(()=>{
    if(!selectedPartId)return;
    const part=partsRef.current.find(p=>p.id===selectedPartId);
    if(!part)return;
    const geo=part.mesh.geometry;
    const pos=geo.attributes.position;
    const neighbors=neighborMapsRef.current[selectedPartId];
    if(!neighbors)return;

    // Save undo snapshot before cleanup
    undoStackRef.current.push({id:selectedPartId,positions:clonePos(geo)});

    const passes=Math.max(2,Math.round(cleanupStrength/100*12));
    const count=pos.count;

    // Compute per-vertex crease weight (0=smooth area, 1=sharp crease)
    // Sharp creases should be preserved, smooth areas get more smoothing
    const computeCreaseWeights=()=>{
      geo.computeVertexNormals();
      const norms=geo.attributes.normal;
      const weights=new Float32Array(count);

      for(let i=0;i<count;i++){
        if(!neighbors[i]||!neighbors[i].length){weights[i]=1;continue;}
        const nx=norms.getX(i),ny=norms.getY(i),nz=norms.getZ(i);
        let minDot=1;
        // Compare this vertex's normal with each neighbor's normal
        for(const ni of neighbors[i]){
          const nnx=norms.getX(ni),nny=norms.getY(ni),nnz=norms.getZ(ni);
          const dot=nx*nnx+ny*nny+nz*nnz; // 1=same direction, -1=opposite
          if(dot<minDot)minDot=dot;
        }
        // minDot < 0.5 means sharp angle (>60°) → preserve (low smooth weight)
        // minDot > 0.85 means gentle curve → smooth aggressively
        const sharpness=1-Math.max(0,Math.min(1,(minDot-0.3)/0.6));
        weights[i]=Math.max(0.05,1-sharpness*0.9); // never fully zero
      }
      return weights;
    };

    for(let pass=0;pass<passes;pass++){
      // Recompute crease weights each pass (normals change as we smooth)
      const weights=computeCreaseWeights();

      // Laplacian smooth: move each vertex toward its neighbor average
      // Store new positions in temp array to avoid read-write conflicts
      const newPos=new Float32Array(count*3);
      for(let i=0;i<count;i++){
        const vx=pos.getX(i),vy=pos.getY(i),vz=pos.getZ(i);
        if(!neighbors[i]||!neighbors[i].length){
          newPos[i*3]=vx;newPos[i*3+1]=vy;newPos[i*3+2]=vz;continue;
        }
        // Compute neighbor centroid
        let ax=0,ay=0,az=0;
        for(const ni of neighbors[i]){ax+=pos.getX(ni);ay+=pos.getY(ni);az+=pos.getZ(ni);}
        const n=neighbors[i].length;
        ax/=n;ay/=n;az/=n;

        // Blend toward centroid, weighted by crease weight and pass strength
        // Earlier passes are stronger, later passes are gentler (diminishing returns)
        const passStr=0.5*(1-pass/(passes*1.5)); // 0.5 → ~0.17 over passes
        const w=weights[i]*passStr;
        newPos[i*3]=vx+(ax-vx)*w;
        newPos[i*3+1]=vy+(ay-vy)*w;
        newPos[i*3+2]=vz+(az-vz)*w;
      }

      // Apply new positions
      for(let i=0;i<count;i++){
        pos.setXYZ(i,newPos[i*3],newPos[i*3+1],newPos[i*3+2]);
      }
    }

    // Final: one pass of Taubin smoothing (slight inflate after smooth to prevent shrinkage)
    {
      const inflateStr=0.15;
      const newPos2=new Float32Array(count*3);
      for(let i=0;i<count;i++){
        const vx=pos.getX(i),vy=pos.getY(i),vz=pos.getZ(i);
        if(!neighbors[i]||!neighbors[i].length){newPos2[i*3]=vx;newPos2[i*3+1]=vy;newPos2[i*3+2]=vz;continue;}
        let ax=0,ay=0,az=0;
        for(const ni of neighbors[i]){ax+=pos.getX(ni);ay+=pos.getY(ni);az+=pos.getZ(ni);}
        const n=neighbors[i].length;ax/=n;ay/=n;az/=n;
        // Inflate: move AWAY from centroid slightly
        newPos2[i*3]=vx-(ax-vx)*inflateStr;
        newPos2[i*3+1]=vy-(ay-vy)*inflateStr;
        newPos2[i*3+2]=vz-(az-vz)*inflateStr;
      }
      for(let i=0;i<count;i++)pos.setXYZ(i,newPos2[i*3],newPos2[i*3+1],newPos2[i*3+2]);
    }

    pos.needsUpdate=true;
    geo.computeVertexNormals();
  },[selectedPartId,cleanupStrength]);

  useEffect(()=>{if(!selectedPartId)return;const p=partsRef.current.find(pp=>pp.id===selectedPartId);if(p)setPartScale({x:Math.round(p.mesh.scale.x*100),y:Math.round(p.mesh.scale.y*100),z:Math.round(p.mesh.scale.z*100)});},[selectedPartId]);
  const applyScale=useCallback((axis,val)=>{const p=partsRef.current.find(pp=>pp.id===selectedPartId);if(!p)return;p.mesh.scale[axis]=Math.max(0.1,Math.min(4,val/100));setPartScale(prev=>({...prev,[axis]:val}));},[selectedPartId]);

  /* ── Raycasting ─────────────────────────────────────────────────── */
  const updateMouse=useCallback((e)=>{
    if(!rendererRef.current)return;
    const rect=rendererRef.current.domElement.getBoundingClientRect();
    mouse.current.x=((e.clientX-rect.left)/rect.width)*2-1;
    mouse.current.y=-((e.clientY-rect.top)/rect.height)*2+1;
    raycaster.current.setFromCamera(mouse.current,cameraRef.current);
  },[]);

  const getHit=useCallback((e)=>{
    updateMouse(e);
    const hits=raycaster.current.intersectObjects(partsRef.current.map(p=>p.mesh),true);
    if(!hits.length)return null;
    let obj=hits[0].object;while(obj.parent&&!obj.userData.id)obj=obj.parent;
    const part=partsRef.current.find(p=>p.mesh===obj||p.id===obj.userData?.id);
    return part?{part,hit:hits[0]}:null;
  },[updateMouse]);

  /* Project mouse onto a plane in world space — returns world-space point */
  const projectOnPlane=useCallback((e,plane)=>{
    updateMouse(e);
    const pt=new THREE.Vector3();
    raycaster.current.ray.intersectPlane(plane,pt);
    return pt;
  },[updateMouse]);

  /* ── Sculpt brush application ───────────────────────────────────── */
  const applySculptBrush=useCallback((hit,mesh,invert,deltaWorld)=>{
    const geo=mesh.geometry,pos=geo.attributes.position;
    const point=mesh.worldToLocal(hit.point.clone());
    const normal=hit.face.normal.clone();
    const r=brushSize,str=brushStrength*0.02;
    const neighbors=neighborMapsRef.current[mesh.userData.id];

    // For grab: compute local-space delta from world-space delta
    let localDelta;
    if(deltaWorld){
      const invMat=new THREE.Matrix4().copy(mesh.matrixWorld).invert();
      const rotMat=new THREE.Matrix3().setFromMatrix4(invMat);
      localDelta=deltaWorld.clone().applyMatrix3(rotMat);
    }

    for(let i=0;i<pos.count;i++){
      const vx=pos.getX(i),vy=pos.getY(i),vz=pos.getZ(i);
      const dx=vx-point.x,dy=vy-point.y,dz=vz-point.z;
      const dist=Math.sqrt(dx*dx+dy*dy+dz*dz);
      if(dist>r)continue;

      const f=gaussian(dist,r);

      switch(brushType){
        case "grab":{
          // Move vertices in the direction of mouse drag, weighted by distance from grab point
          if(!localDelta)break;
          const w=f*brushStrength*2.0;
          pos.setX(i,vx+localDelta.x*w);
          pos.setY(i,vy+localDelta.y*w);
          pos.setZ(i,vz+localDelta.z*w);
          break;
        }
        case "sidescale":{
          // Scale the entire side of the mesh that this face belongs to.
          // "Side" = all vertices whose position along the face normal direction
          // is within the top 40% of the mesh extent on that axis.
          // invert = scale the opposite side instead.

          // Get face normal in world space, then convert to local space direction
          const faceNormalWorld=hit.face.normal.clone().transformDirection(mesh.matrixWorld).normalize();
          const invMat=new THREE.Matrix4().copy(mesh.matrixWorld).invert();
          const rotMat=new THREE.Matrix3().setFromMatrix4(invMat);
          const faceNormalLocal=faceNormalWorld.clone().applyMatrix3(rotMat).normalize();

          // Apply invert: flip to opposite side if Shift held
          const sideNormal=invert?faceNormalLocal.clone().negate():faceNormalLocal;

          // Find the extent of the mesh along this normal direction
          let minProj=Infinity,maxProj=-Infinity;
          for(let j=0;j<pos.count;j++){
            const proj=pos.getX(j)*sideNormal.x+pos.getY(j)*sideNormal.y+pos.getZ(j)*sideNormal.z;
            if(proj<minProj)minProj=proj;
            if(proj>maxProj)maxProj=proj;
          }
          const extent=maxProj-minProj;
          // Threshold: vertices in the top 40% of the extent along this normal are "on this side"
          const threshold=minProj+extent*0.6;

          // Scale amount based on brush strength and frame delta
          const scaleDelta=str*6;

          const proj0=point.x*sideNormal.x+point.y*sideNormal.y+point.z*sideNormal.z;
          const vertProj=vx*sideNormal.x+vy*sideNormal.y+vz*sideNormal.z;
          if(vertProj<threshold)break; // not on this side

          // Weight: vertices closer to the face edge (boundary of threshold) move less,
          // vertices at the extreme tip move the most — smooth transition
          const sideWeight=Math.max(0,Math.min(1,(vertProj-threshold)/(extent*0.4)));

          pos.setX(i,vx+sideNormal.x*scaleDelta*sideWeight);
          pos.setY(i,vy+sideNormal.y*scaleDelta*sideWeight);
          pos.setZ(i,vz+sideNormal.z*scaleDelta*sideWeight);
          break;
        }
        case "pinch":{
          // Invert=false: pull vertices toward brush center (sharpen)
          // Invert=true: push vertices away from brush center (expand/round)
          const w=f*str*3;
          const dir=invert?1:-1;
          pos.setX(i,vx+dx*w*dir);
          pos.setY(i,vy+dy*w*dir);
          pos.setZ(i,vz+dz*w*dir);
          break;
        }
        case "push":{
          const d=invert?1:-1;
          const w=f*str;
          pos.setX(i,vx+normal.x*w*d);
          pos.setY(i,vy+normal.y*w*d);
          pos.setZ(i,vz+normal.z*w*d);
          break;
        }
        case "smooth":{
          if(!neighbors?.[i]?.length)break;
          let ax=0,ay=0,az=0;
          neighbors[i].forEach(ni=>{ax+=pos.getX(ni);ay+=pos.getY(ni);az+=pos.getZ(ni);});
          const n=neighbors[i].length;
          const w=f*str*3;
          pos.setX(i,vx+(ax/n-vx)*w);
          pos.setY(i,vy+(ay/n-vy)*w);
          pos.setZ(i,vz+(az/n-vz)*w);
          break;
        }
        case "flatten":{
          const dot2=(vx-point.x)*normal.x+(vy-point.y)*normal.y+(vz-point.z)*normal.z;
          const w=f*str*5;
          pos.setX(i,vx-normal.x*dot2*w);
          pos.setY(i,vy-normal.y*dot2*w);
          pos.setZ(i,vz-normal.z*dot2*w);
          break;
        }
        case "crease":{
          const w=f*str*2;
          pos.setX(i,vx-dx*w);
          pos.setY(i,vy-dy*w);
          pos.setZ(i,vz-dz*w);
          break;
        }
      }
    }
    pos.needsUpdate=true;geo.computeVertexNormals();
  },[brushType,brushSize,brushStrength]);

  /* ── Pointer handlers ───────────────────────────────────────────── */
  const handlePointerDown=useCallback((e)=>{
    // MOVE MODE
    if(toolMode==="move"&&selectedPartId){
      const selPart=partsRef.current.find(p=>p.id===selectedPartId);
      if(selPart){
        updateMouse(e);
        let plane;
        if(e.shiftKey){
          // VERTICAL MOVE: plane faces the camera horizontally, so dragging moves part up/down
          // We use a vertical plane whose normal is the camera's horizontal look direction
          const camDir=new THREE.Vector3();
          cameraRef.current.getWorldDirection(camDir);
          camDir.y=0; // flatten to horizontal
          camDir.normalize();
          plane=new THREE.Plane().setFromNormalAndCoplanarPoint(camDir,selPart.mesh.position);
        }else{
          // HORIZONTAL MOVE: plane is flat on the XZ floor at the part's Y
          plane=new THREE.Plane().setFromNormalAndCoplanarPoint(new THREE.Vector3(0,1,0),selPart.mesh.position);
        }
        const intersect=new THREE.Vector3();
        if(raycaster.current.ray.intersectPlane(plane,intersect)){
          movingRef.current={active:true,plane,offset:selPart.mesh.position.clone().sub(intersect),vertical:e.shiftKey};
          if(controlsRef.current)controlsRef.current.enabled=false;
        }
      }
      return;
    }

    // SCULPT MODE
    if(toolMode==="sculpt"&&selectedPartId){
      const result=getHit(e);
      if(result&&result.part.id===selectedPartId){
        // Save undo snapshot
        undoStackRef.current.push({id:selectedPartId,positions:clonePos(result.part.mesh.geometry)});

        if(brushType==="grab"){
          // GRAB: create a plane at the hit point facing the camera for projecting mouse deltas
          const camDir=new THREE.Vector3();
          cameraRef.current.getWorldDirection(camDir);
          const grabPlane=new THREE.Plane().setFromNormalAndCoplanarPoint(camDir.negate(),result.hit.point);
          grabRef.current={
            active:true,
            hitPointWorld:result.hit.point.clone(),
            hitPointLocal:result.part.mesh.worldToLocal(result.hit.point.clone()),
            plane:grabPlane,
            lastWorld:result.hit.point.clone(),
            mesh:result.part.mesh,
            basePositions:clonePos(result.part.mesh.geometry),
          };
        }else{
          sculptingRef.current=true;
          applySculptBrush(result.hit,result.part.mesh,e.shiftKey,null);
        }

        if(controlsRef.current)controlsRef.current.enabled=false;
      }
      return;
    }

    // SELECT MODE
    const result=getHit(e);
    partsRef.current.forEach(p=>{if(p.mesh.material)p.mesh.material.color.set(CLAY);});
    if(result){setSelectedPartId(result.part.id);result.part.mesh.material.color.set(CLAY_SEL);}
    else setSelectedPartId(null);
  },[toolMode,selectedPartId,getHit,updateMouse,applySculptBrush,brushType]);

  const handlePointerMove=useCallback((e)=>{
    // MOVING PART
    if(movingRef.current.active&&selectedPartId){
      const selPart=partsRef.current.find(p=>p.id===selectedPartId);if(!selPart)return;
      const pt=projectOnPlane(e,movingRef.current.plane);
      if(pt){
        const newPos=pt.add(movingRef.current.offset);
        if(movingRef.current.vertical){
          // Only update Y — keep X and Z locked during vertical drag
          selPart.mesh.position.y=newPos.y;
        }else{
          selPart.mesh.position.copy(newPos);
        }
      }
      return;
    }

    // GRAB TOOL DRAGGING
    if(grabRef.current.active){
      const currentWorld=projectOnPlane(e,grabRef.current.plane);
      if(!currentWorld)return;
      const deltaWorld=currentWorld.clone().sub(grabRef.current.lastWorld);
      grabRef.current.lastWorld.copy(currentWorld);

      // Rebuild hit object from stored data for applySculptBrush
      const fakeHit={point:grabRef.current.mesh.localToWorld(grabRef.current.hitPointLocal.clone()),face:{normal:new THREE.Vector3(0,1,0)}};
      // Recompute proper face normal from current geometry at grab point
      const mesh=grabRef.current.mesh;
      updateMouse(e);
      const hits=raycaster.current.intersectObject(mesh,false);
      if(hits.length>0)fakeHit.face=hits[0].face;

      applySculptBrush({point:mesh.localToWorld(grabRef.current.hitPointLocal.clone()),face:fakeHit.face},mesh,false,deltaWorld);
      return;
    }

    // OTHER SCULPT BRUSHES DRAGGING
    if(sculptingRef.current&&selectedPartId){
      const result=getHit(e);
      if(result&&result.part.id===selectedPartId)applySculptBrush(result.hit,result.part.mesh,e.shiftKey,null);
      return;
    }

    // HOVER: brush indicator + highlight
    const result=getHit(e);
    const bi=brushIndRef.current;
    if(toolMode==="sculpt"&&result&&result.part.id===selectedPartId&&bi){
      bi.visible=true;bi.position.copy(result.hit.point);
      const n=result.hit.face.normal.clone().transformDirection(result.part.mesh.matrixWorld);
      bi.lookAt(result.hit.point.clone().add(n));
    }else if(bi)bi.visible=false;

    partsRef.current.forEach(p=>{if(p.id!==selectedPartId&&p.mesh.material)p.mesh.material.color.set(CLAY);});
    if(result&&result.part.id!==selectedPartId&&toolMode==="select")result.part.mesh.material.color.set(CLAY_HOVER);
    if(rendererRef.current){
      const cursor=toolMode==="sculpt"&&result?"crosshair":toolMode==="move"&&selectedPartId?"grab":result?"pointer":"default";
      rendererRef.current.domElement.style.cursor=cursor;
    }
  },[toolMode,selectedPartId,getHit,applySculptBrush,projectOnPlane,updateMouse]);

  const handlePointerUp=useCallback(()=>{
    if(movingRef.current.active){movingRef.current.active=false;if(controlsRef.current)controlsRef.current.enabled=true;}
    if(grabRef.current.active){grabRef.current.active=false;grabRef.current.mesh=null;grabRef.current.basePositions=null;if(controlsRef.current)controlsRef.current.enabled=true;}
    if(sculptingRef.current){sculptingRef.current=false;if(controlsRef.current)controlsRef.current.enabled=true;}
  },[]);

  /* ══════════════════════════════════════════════════════════════════ */
  const selPart=placedParts.find(p=>p.id===selectedPartId);

  return(
    <div className="ss-root">
      <header className="ss-header">
        <button className="ss-back" onClick={()=>navigate("/")}>← Back</button>
        <span className="ss-logo">Designable<span className="ss-dot">.</span></span>
        <span className="ss-title">3D Sculpt Studio</span>
        {selectedPartId&&(
          <div className="ss-tool-bar">
            <button className={`ss-tool-btn ${toolMode==="select"?"active":""}`} onClick={()=>setToolMode("select")} title="Select">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M3 2l10 6-5.5 1.5L6 15z"/></svg>
              <span>Select</span>
            </button>
            <button className={`ss-tool-btn ${toolMode==="move"?"active":""}`} onClick={()=>setToolMode("move")} title="Drag to move · Hold Shift to move up/down">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M8 2v12M2 8h12"/><path d="M8 2L6 4M8 2l2 2M8 14l-2-2M8 14l2-2M2 8l2-2M2 8l2 2M14 8l-2-2M14 8l-2 2"/></svg>
              <span>Move</span>
            </button>
            <button className={`ss-tool-btn ${toolMode==="sculpt"?"active":""}`} onClick={()=>setToolMode("sculpt")} title="Sculpt">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10 2l4 4-7 7H3v-4z"/><path d="M8 4l4 4"/></svg>
              <span>Sculpt</span>
            </button>
            {toolMode==="move"&&<span className="ss-tool-hint">Shift + drag = up/down</span>}
          </div>
        )}
        <div className="ss-header-actions">
          {selectedPartId&&<button className="ss-hbtn danger" onClick={deleteSelected}>Delete</button>}
          <button className="ss-hbtn" onClick={()=>{partsRef.current.forEach(p=>sceneRef.current?.remove(p.mesh));partsRef.current=[];setPlacedParts([]);setSelectedPartId(null);setHasSeat(false);partIdCounter.current=0;neighborMapsRef.current={};undoStackRef.current=[];grabRef.current={active:false,hitPointWorld:new THREE.Vector3(),hitPointLocal:new THREE.Vector3(),plane:null,lastWorld:new THREE.Vector3(),mesh:null,basePositions:null};}}>Clear All</button>
        </div>
      </header>

      <div className="ss-body">
        <aside className="ss-inventory">
          <div className="ss-inv-head">Parts Inventory</div>
          {INVENTORY.map(cat=>{const isOpen=openCat===cat.category;return(
            <div key={cat.category} className="ss-inv-cat">
              <button className={`ss-inv-cat-btn ${isOpen?"open":""}`} onClick={()=>setOpenCat(isOpen?null:cat.category)}><span>{cat.category}</span><svg className={`ss-inv-chev ${isOpen?"open":""}`} width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round"/></svg></button>
              {isOpen&&<div className="ss-inv-items">{cat.items.map(item=><button key={item.id} className="ss-inv-item" onClick={()=>placePart(item)} onMouseEnter={()=>showSnapZones(item.type)} onMouseLeave={hideSnapZones}><div className="ss-inv-item-icon"><div className="ss-inv-blob"/></div><span className="ss-inv-item-name">{item.name}</span></button>)}</div>}
            </div>
          );})}
          {placedParts.length>0&&<div className="ss-placed"><div className="ss-placed-head">Assembled</div>{placedParts.map(p=><button key={p.id} className={`ss-placed-item ${selectedPartId===p.id?"selected":""}`} onClick={()=>{setSelectedPartId(p.id);setToolMode("select");partsRef.current.forEach(pp=>{if(pp.mesh.material)pp.mesh.material.color.set(pp.id===p.id?CLAY_SEL:CLAY);});}}><span className="ss-placed-dot"/><span>{p.name}</span><span className="ss-placed-type">{p.type}</span></button>)}</div>}
        </aside>

        <div className="ss-canvas" ref={mountRef} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerLeave={handlePointerUp}/>

        <aside className="ss-props">
          {selectedPartId&&selPart?<div className="ss-props-content">
            <div className="ss-props-head">{selPart.name}</div>
            <div className="ss-props-type">{selPart.type}</div>

            <div className="ss-props-section"><div className="ss-props-stitle">Scale</div>
              {["x","y","z"].map(a=><div key={a} className="ss-scale-row"><label>{a.toUpperCase()}</label><input type="range" min="10" max="400" value={partScale[a]} onChange={e=>applyScale(a,+e.target.value)}/><span>{partScale[a]}%</span></div>)}
            </div>

            {toolMode==="sculpt"&&<div className="ss-props-section"><div className="ss-props-stitle">Brush</div>
              <div className="ss-brush-grid">
                {BRUSH_TYPES.map(bt=><button key={bt} className={`ss-brush-btn ${brushType===bt?"active":""}`} onClick={()=>setBrushType(bt)}>{BRUSH_LABELS[bt]}</button>)}
              </div>
              <div className="ss-brush-info">{BRUSH_HINTS[brushType]}</div>
              <div className="ss-scale-row"><label>Size</label><input type="range" min="10" max="250" value={Math.round(brushSize*100)} onChange={e=>setBrushSize(+e.target.value/100)}/><span>{Math.round(brushSize*100)}%</span></div>
              <div className="ss-scale-row"><label>Power</label><input type="range" min="5" max="100" value={Math.round(brushStrength*100)} onChange={e=>setBrushStrength(+e.target.value/100)}/><span>{Math.round(brushStrength*100)}%</span></div>
              <button className="ss-props-btn" onClick={undoSculpt}>Undo Stroke</button>
            </div>}

            <div className="ss-props-section"><div className="ss-props-stitle">Clean Up</div>
              <div className="ss-brush-info">Smooths rough surfaces while preserving sharp edges you created intentionally</div>
              <div className="ss-scale-row"><label>Str</label><input type="range" min="10" max="100" value={cleanupStrength} onChange={e=>setCleanupStrength(+e.target.value)}/><span>{cleanupStrength}%</span></div>
              <button className="ss-props-btn ss-cleanup-btn" onClick={cleanupMesh}>✦ Clean Up Mesh</button>
            </div>

            <div className="ss-props-section"><div className="ss-props-stitle">Actions</div><button className="ss-props-btn" onClick={deleteSelected}>Remove Part</button></div>
          </div>:<div className="ss-props-empty"><p>Select a part to view properties</p><p className="ss-props-sub">Click items from the inventory to place them</p></div>}
        </aside>
      </div>
    </div>
  );
}