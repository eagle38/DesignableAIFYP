import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { useNavigate } from "react-router-dom";
import "../App.css";



/* ─── CONFIG ──────────────────────────────────────────────────────────── */
const API = import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";
const UPLOAD = `${API}/analyze-chair`;
const FURNITURE_TYPES = ["chair", "table"];


/* ─── CONSTANTS ───────────────────────────────────────────────────────── */
const RC = {
  seat:    { rgb:"200,96,42",  hex:"#c8602a" },
  backrest:{ rgb:"107,143,113",hex:"#6b8f71" },
  headrest:{ rgb:"155,130,100",hex:"#9b8264" },
  armrest: { rgb:"138,130,120",hex:"#8a8278" },
  shell:   { rgb:"180,120,80", hex:"#b47850" },
  wing:    { rgb:"160,90,80",  hex:"#a05a50" },
  lumbar:  { rgb:"100,130,140",hex:"#64828c" },
  base:    { rgb:"120,115,108",hex:"#78736c" },
  // Table-specific colors
  top:     { rgb:"180,160,120",hex:"#b4a078" },
  leg:     { rgb:"120,100,80", hex:"#786450" },
  apron:   { rgb:"140,110,90", hex:"#8c6e5a" },
  pedestal:{ rgb:"100,80,60",  hex:"#645036" },
  stretcher:{rgb:"160,130,100",hex:"#a08264" },
  unknown: { rgb:"138,130,120",hex:"#8a8278" },
};
const RM = {
  seat:"seat",backrest:"backrest",headrest:"headrest",lumbar_support:"lumbar",
  base:"base",armrest:"armrest",armrest_sofa:"armrest",eames_lounge_cushion:"armrest",
  armrest_egg:"shell",leg_structure:"base",five_star_base:"base",eames_base:"base",
  caster_wheel:"base",control_mechanism:"base",wing_flanage:"wing",
  // Table-specific mappings
  table_top:"top",top:"top",tabletop:"top",surface:"top",deck:"top",
  leg:"leg",legs:"leg",table_leg:"leg",support:"leg",post:"leg",
  apron:"apron",skirt:"apron",table_apron:"apron",trim:"apron",frieze:"apron",
  pedestal:"pedestal",column:"pedestal",center_post:"pedestal",
  stretcher:"stretcher",cross_brace:"stretcher",strut:"stretcher",brace:"stretcher",trestle:"stretcher",
};
const ADJ = {
  seat:{ ch:["leg_structure","five_star_base","eames_base","base","caster_wheel","control_mechanism"] },
  backrest:{ ch:["headrest","lumbar_support","wing_flanage"] },
};

const PANEL_TITLES = ["Dimensions", "Measurements", "Shape & Flags", "Ergonomics & AI", "Material Engine"];

/* ─── MATERIAL DATA ───────────────────────────────────────────────────── */
const MATERIAL_DATA = {
  leather: {
    "Smooth": [
      { src: "/materials/leather/Smooth/brown_1.jpg", name: "Brown" },
      { src: "/materials/leather/Smooth/yellow_1.jpg", name: "Yellow" },
      { src: "/materials/leather/Smooth/Blue.jpg", name: "Blue" },
      { src: "/materials/leather/Smooth/Grey.jpg", name: "Grey" },
      { src: "/materials/leather/Smooth/White.jpg", name: "White" },
    ],
    "Stitched": [
      { src: "/materials/leather/Stitched/brown_stiched.jpg", name: "Brown" },
      { src: "/materials/leather/Stitched/grey_stitched.jpg", name: "Grey" },
      { src: "/materials/leather/Stitched/white_sticthed.jpg", name: "White" },
    ],
    "Pebbled": [
      { src: "/materials/leather/Pebbled/Red.jpg", name: "Red" },
      { src: "/materials/leather/Pebbled/white.jpg", name: "White" },
    ],
    "Suede": [
      { src: "/materials/leather/Suede/suede_brown.png", name: "Brown" },
    ],
    "Rough": [
      { src: "/materials/leather/Rough/rough_grey.png", name: "Grey" },
    ],
  },
  fabric: {
    "Cotton": [
      { src: "/materials/fabric/Cotton/blue.jpg", name: "Blue" },
      { src: "/materials/fabric/Cotton/grey.jpg", name: "Grey" },
      { src: "/materials/fabric/Cotton/olive.jpg", name: "Olive" },
      { src: "/materials/fabric/Cotton/silver.jpg", name: "Silver" },
    ],
    "Pattern": [
      { src: "/materials/fabric/Pattern/red.jpg", name: "Red" },
      { src: "/materials/fabric/Pattern/white.jpg", name: "White" },
    ],
    "Tiled": [
      { src: "/materials/fabric/Tiled/blue.jpg", name: "Blue" },
      { src: "/materials/fabric/Tiled/red.jpg", name: "Red" },
      { src: "/materials/fabric/Tiled/grey.jpg", name: "Grey" },
    ],
    "Printed": [
      { src: "/materials/fabric/Printed/sky.jpg", name: "Sky" },
      { src: "/materials/fabric/Printed/white.jpg", name: "White" },
    ],
    "Woven": [
      { src: "/materials/fabric/Woven/charcoal.jpg", name: "Charcoal" },
      { src: "/materials/fabric/Woven/grey.jpg", name: "Grey" },
      { src: "/materials/fabric/Woven/red.jpg", name: "Red" },
      { src: "/materials/fabric/Woven/silver.jpg", name: "Silver" },
    ],
    "Stitched": [
      { src: "/materials/fabric/Sticthed/blue.jpg", name: "Blue" },
      { src: "/materials/fabric/Sticthed/black.jpg", name: "Black" },
      { src: "/materials/fabric/Sticthed/red.jpg", name: "Red" },
    ],
    "Rough": [
      { src: "/materials/fabric/Rough/grey.jpg", name: "Grey" },
      { src: "/materials/fabric/Rough/silver.jpg", name: "Silver" },
      { src: "/materials/fabric/Rough/light_silver.jpg", name: "Light Silver" },
    ],
  },
  metal: {
    "Brushed": [
      { src: "/materials/metal/Brushed/grey.jpg", name: "Grey" },
      { src: "/materials/metal/Brushed/silver.jpg", name: "Silver" },
      { src: "/materials/metal/Brushed/grey_2.jpg", name: "Grey II" },
      { src: "/materials/metal/Brushed/silver_2.jpg", name: "Silver II" },
    ],
    "Matte": [
      { src: "/materials/metal/Matte/black.jpg", name: "Black" },
      { src: "/materials/metal/Matte/matte.jpg", name: "Matte" },
    ],
    "Rusty": [
      { src: "/materials/metal/Rusty/rusty.jpg", name: "Rust I" },
      { src: "/materials/metal/Rusty/rusty_2.jpg", name: "Rust II" },
      { src: "/materials/metal/Rusty/rusty_3.jpg", name: "Rust III" },
    ],
    "Chrome": [
      { src: "/materials/metal/Chrome/white.jpg", name: "Chrome" },
    ],
  },
  wood: {
    "Walnut": [
      { src: "/materials/wood/Walnut/walnut_1.jpg", name: "Walnut I" },
      { src: "/materials/wood/Walnut/walnut_2.jpg", name: "Walnut II" },
      { src: "/materials/wood/Walnut/walnut_3.jpg", name: "Walnut III" },
      { src: "/materials/wood/Walnut/walnut_4.jpg", name: "Walnut IV" },
      { src: "/materials/wood/Walnut/walnut_5.jpg", name: "Walnut V" },
      { src: "/materials/wood/Walnut/walnut_6.jpg", name: "Walnut VI" },
    ],
    "Maple": [
      { src: "/materials/wood/Maple/maple_1.jpg", name: "Maple I" },
      { src: "/materials/wood/Maple/maple_2.jpg", name: "Maple II" },
    ],
    "Oak": [
      { src: "/materials/wood/Oak/oak_1.jpg", name: "Oak I" },
      { src: "/materials/wood/Oak/oak_2.jpg", name: "Oak II" },
    ],
    "Cherry": [
      { src: "/materials/wood/Cherry/cherry.jpg", name: "Cherry" },
    ],
  },
};

function role(l){
  if(!l)return "unknown";
  const low=l.toLowerCase();
  // Direct match
  if(RM[low])return RM[low];
  // Strip _left/_right/_1/_2 suffixes and try again
  const stripped=low.replace(/_(left|right|\d+)$/,"");
  if(RM[stripped])return RM[stripped];

  // Fallback for noisy detector labels (e.g., table_legss, table_supports)
  if(/top|tabletop|surface|deck/.test(stripped))return "top";
  if(/leg|support|post/.test(stripped))return "leg";
  if(/apron|skirt|frieze|trim/.test(stripped))return "apron";
  if(/pedestal|column|center_post/.test(stripped))return "pedestal";
  if(/stretcher|brace|strut|trestle/.test(stripped))return "stretcher";

  return "unknown";
}
function rc(l){ return RC[role(l)]||RC.unknown; }
function fmt(l){ return(l||"unknown").replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase()); }
function sharp(g){ if(!g)return 0.5; const r=g._raw||{}; const s=r.smoothness_score!=null?Math.min(1,r.smoothness_score/0.3):0.5; return s*0.6+Math.max(0,Math.min(1,((r.solidity||0.9)-0.8)/0.15))*0.4; }
function cen(pts){ let x=0,y=0;for(const[a,b]of pts){x+=a;y+=b;}return[x/pts.length,y/pts.length]; }
function pip(px,py,poly){ let i=false;for(let a=0,b=poly.length-1;a<poly.length;b=a++){const[xi,yi]=poly[a],[xj,yj]=poly[b];if((yi>py)!==(yj>py)&&px<((xj-xi)*(py-yi))/(yj-yi)+xi)i=!i;}return i; }
function scaleM(m,sx,sy){ const[cx,cy]=cen(m);return m.map(([x,y])=>[cx+(x-cx)*sx,cy+(y-cy)*sy]); }
function transM(m,dx,dy){ return m.map(([x,y])=>[x+dx,y+dy]); }
function chaikin(pts,it=1){ let p=[...pts];for(let i=0;i<it;i++){const n=[];for(let j=0;j<p.length;j++){const[x1,y1]=p[j],[x2,y2]=p[(j+1)%p.length];n.push([x1*.75+x2*.25,y1*.75+y2*.25],[x1*.25+x2*.75,y1*.25+y2*.75]);}p=n;}return p; }
function simplify(pts,tol){ if(pts.length<=3)return pts;const sd=(p,a,b)=>{const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)));return(a[0]+t*dx-p[0])**2+(a[1]+t*dy-p[1])**2;};let mx=0,mi=0;for(let i=1;i<pts.length-1;i++){const d=sd(pts[i],pts[0],pts[pts.length-1]);if(d>mx){mx=d;mi=i;}}if(mx>tol*tol){const l=simplify(pts.slice(0,mi+1),tol),r=simplify(pts.slice(mi),tol);return[...l.slice(0,-1),...r];}return[pts[0],pts[pts.length-1]]; }
function applyShape(o,lv){ if(lv===0)return o.map(p=>[...p]);if(lv>0)return chaikin(o,Math.round(lv));const s=simplify(o,Math.abs(lv)*8);return s.length>=3?s:o; }
function latestAssistantReply(text){
  if(!text)return "";
  const raw=String(text).trim();
  if(!raw)return "";
  const markers=["assistant:","ai:","model:","copilot:"];
  const lower=raw.toLowerCase();
  let idx=-1;
  for(const marker of markers){
    const pos=lower.lastIndexOf(marker);
    if(pos>idx)idx=pos;
  }
  const candidate=idx>=0?raw.slice(idx).replace(/^[^:]*:\s*/i,"").trim():raw;
  const userPos=candidate.toLowerCase().lastIndexOf("user:");
  return (userPos>=0?candidate.slice(0,userPos):candidate).trim()||raw;
}

/* ═══════════════════════════════════════════════════════════════════════ */
/* MAIN                                                                     */
/* ═══════════════════════════════════════════════════════════════════════ */

export default function Dashboard(){
  /* Upload */
  const[file,setFile]=useState(null);
  const[furnitureType,setFurnitureType]=useState("chair");
  const[imgUrl,setImgUrl]=useState(null);
  const[result,setResult]=useState(null);
  const[loading,setLoading]=useState(false);
  const[uploadErr,setUploadErr]=useState("");

  const navigate = useNavigate();
  /* Session */
  const[sid,setSid]=useState(null);
  const[phase,setPhase]=useState("ANALYSIS");
  const[classData,setClassData]=useState(null);
  const[chat,setChat]=useState([]);
  const[chatIn,setChatIn]=useState("");
  const[chatBusy,setChatBusy]=useState(false);
  const[chatCollapsed,setChatCollapsed]=useState(false);
  const chatEnd=useRef(null);
  /* Viz */
  const contRef=useRef(null);
  const canRef=useRef(null);
  const imgOb=useRef(null);
  const[sel,setSel]=useState(null);
  const[hov,setHov]=useState(null);
  const[sharpMode,setSharpMode]=useState(false);
  const[imgOk,setImgOk]=useState(false);
  const[imgNat,setImgNat]=useState({w:1,h:1});
  const[tf,setTf]=useState({x:0,y:0,s:1});
  const drag=useRef({on:false,sx:0,sy:0,tx:0,ty:0,moved:false});
  /* Mods */
  const[mods,setMods]=useState({});
  const[rcGeom,setRcGeom]=useState({});
  const[aiFb,setAiFb]=useState("");
  const[aiFbLoad,setAiFbLoad]=useState(false);
  /* Textures — maps label -> { src, image (loaded HTMLImageElement) } */
  const[textures,setTextures]=useState({});
  const texCache=useRef({}); // cache loaded Image objects by src
  /* Tooltip */
  const[tooltip,setTooltip]=useState(null);
  /* Carousel panel index */
  const[panelIdx,setPanelIdx]=useState(0);
 

  const hasMods=Object.keys(mods).length>0;
  const fRef=useRef(null);

  const origParts=useMemo(()=>{
    if(!result?.parts_with_traits)return[];
    return result.parts_with_traits.filter(p=>p.mask?.length>=3);
  },[result]);
  const imgD=result?.image_dimensions||{width:800,height:600};

  const curParts=useMemo(()=>{
    return origParts.map(p=>{
      const m=mods[p.label]; const go=rcGeom[p.label];
      if(!m)return{...p,cm:p.mask,geometry:go||p.geometry};
      let mk=p.mask;
      if(m.sl&&m.sl!==0)mk=applyShape(mk,m.sl);
      if((m.sx||1)!==1||(m.sy||1)!==1)mk=scaleM(mk,m.sx||1,m.sy||1);
      if((m.tx||0)!==0||(m.ty||0)!==0)mk=transM(mk,m.tx||0,m.ty||0);
      return{...p,cm:mk,geometry:go||p.geometry};
    });
  },[origParts,mods,rcGeom]);

  useEffect(()=>{ if(!imgUrl)return; const i=new Image(); i.onload=()=>{setImgNat({w:i.naturalWidth,h:i.naturalHeight});setImgOk(true);imgOb.current=i;}; i.src=imgUrl; },[imgUrl]);
  useEffect(()=>{ chatEnd.current?.scrollIntoView({behavior:"smooth"}); },[chat]);

  const ir=useCallback(()=>{
    if(!contRef.current)return{x:0,y:0,w:1,h:1,sx:1,sy:1};
    const cw=contRef.current.clientWidth,ch=contRef.current.clientHeight,pad=40;
    const mxW=cw-pad*2,mxH=ch-pad*2,ar=imgNat.w/imgNat.h;
    let dw,dh;if(ar>mxW/mxH){dw=mxW;dh=mxW/ar;}else{dh=mxH;dw=mxH*ar;}
    return{x:(cw-dw)/2,y:(ch-dh)/2,w:dw,h:dh,sx:dw/imgD.width,sy:dh/imgD.height};
  },[imgNat,imgD]);
  const td=useCallback((px,py,r)=>[r.x+px*r.sx,r.y+py*r.sy],[]);

  /* DRAW */
  const draw=useCallback(()=>{
    const cv=canRef.current,co=contRef.current;
    if(!cv||!co||!imgOk||!imgOb.current)return;
    const ctx=cv.getContext("2d"),dpr=window.devicePixelRatio||1;
    const cw=co.clientWidth,ch=co.clientHeight;
    cv.width=cw*dpr;cv.height=ch*dpr;cv.style.width=cw+"px";cv.style.height=ch+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0);

    ctx.fillStyle="#0f0e0c";ctx.fillRect(0,0,cw,ch);
    ctx.strokeStyle="rgba(245,241,235,0.03)";ctx.lineWidth=0.5;
    for(let gx=0;gx<cw;gx+=40){ctx.beginPath();ctx.moveTo(gx,0);ctx.lineTo(gx,ch);ctx.stroke();}
    for(let gy=0;gy<ch;gy+=40){ctx.beginPath();ctx.moveTo(0,gy);ctx.lineTo(cw,gy);ctx.stroke();}

    ctx.save();ctx.translate(tf.x,tf.y);ctx.scale(tf.s,tf.s);
    const r=ir();

    const gl=ctx.createRadialGradient(r.x+r.w/2,r.y+r.h/2,r.w*0.1,r.x+r.w/2,r.y+r.h/2,r.w*0.9);
    gl.addColorStop(0,"rgba(200,96,42,0.025)");gl.addColorStop(1,"transparent");
    ctx.fillStyle=gl;ctx.fillRect(r.x-80,r.y-80,r.w+160,r.h+160);

    ctx.save();
    const rd=4;ctx.beginPath();
    ctx.moveTo(r.x+rd,r.y);ctx.lineTo(r.x+r.w-rd,r.y);ctx.arcTo(r.x+r.w,r.y,r.x+r.w,r.y+rd,rd);
    ctx.lineTo(r.x+r.w,r.y+r.h-rd);ctx.arcTo(r.x+r.w,r.y+r.h,r.x+r.w-rd,r.y+r.h,rd);
    ctx.lineTo(r.x+rd,r.y+r.h);ctx.arcTo(r.x,r.y+r.h,r.x,r.y+r.h-rd,rd);
    ctx.lineTo(r.x,r.y+rd);ctx.arcTo(r.x,r.y,r.x+rd,r.y,rd);ctx.closePath();
    ctx.shadowColor="rgba(0,0,0,0.4)";ctx.shadowBlur=35;ctx.shadowOffsetY=8;
    ctx.clip();ctx.drawImage(imgOb.current,r.x,r.y,r.w,r.h);ctx.restore();

    /* ── Render applied textures ─────────────────────────────────── */
    Object.entries(textures).forEach(([label,tex])=>{
      if(!tex.image)return;
      const part=curParts.find(p=>p.label===label);
      if(!part)return;
      const mk=part.cm||part.mask;
      const pts=mk.map(([x,y])=>td(x,y,r));

      ctx.save();
      // Clip to mask polygon
      ctx.beginPath();
      ctx.moveTo(pts[0][0],pts[0][1]);
      for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0],pts[i][1]);
      ctx.closePath();
      ctx.clip();

      // Fill with repeating texture pattern
      try{
        const pattern=ctx.createPattern(tex.image,"repeat");
        if(pattern){
          // Scale pattern down for realistic tiling
          const matrix=new DOMMatrix().scale(0.25,0.25);
          pattern.setTransform(matrix);
          ctx.fillStyle=pattern;
          ctx.fillRect(0,0,r.x+r.w+200,r.y+r.h+200);
        }
      }catch(e){/* pattern creation can fail if image not ready */}
      ctx.restore();

      // Redraw sketch on top with multiply for line visibility
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(pts[0][0],pts[0][1]);
      for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0],pts[i][1]);
      ctx.closePath();
      ctx.clip();
      ctx.globalCompositeOperation="multiply";
      ctx.drawImage(imgOb.current,r.x,r.y,r.w,r.h);
      ctx.globalCompositeOperation="source-over";
      ctx.restore();
    });

    /* ── Mask overlays ───────────────────────────────────────────── */
    curParts.forEach(p=>{
      const{label,cm,geometry}=p;const mk=cm||p.mask;const c=rc(label);
      const iS=sel===label,iH=hov===label,iM=!!mods[label],sh=sharp(geometry);
      const pts=mk.map(([x,y])=>td(x,y,r));
      ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);
      for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0],pts[i][1]);ctx.closePath();
      if(sharpMode){const rgb=sh<0.33?"107,143,113":sh<0.66?"200,170,80":"200,96,42";ctx.fillStyle=`rgba(${rgb},${iS?0.35:iH?0.25:0.14})`;}
      else ctx.fillStyle=`rgba(${c.rgb},${iS?0.28:iH?0.18:iM?0.14:0.06})`;
      ctx.fill();
      const sR=sharpMode?(sh<0.33?"107,143,113":sh<0.66?"200,170,80":"200,96,42"):c.rgb;
      ctx.strokeStyle=`rgba(${sR},${iS?0.75:iH?0.45:iM?0.3:0.15})`;
      ctx.lineWidth=iS?1.5:1;ctx.setLineDash(iS?[]:iH?[4,3]:iM?[3,2]:[]);ctx.stroke();ctx.setLineDash([]);
    });

    const all=curParts.length<=8;
    curParts.forEach((p,idx)=>{
      const{label,cm}=p;const mk=cm||p.mask;const c=rc(label);
      const iS=sel===label,iH=hov===label;
      if(!all&&!iS&&!iH)return;
      const[cx,cy]=td(...cen(mk),r);
      const side=cx<r.x+r.w/2?-1:1;
      const slot=((idx%5)-2)*32;
      const ax=side<0?r.x-22:r.x+r.w+22;
      const ay=Math.max(r.y+14,Math.min(r.y+r.h-14,cy+slot));
      const ex=side<0?r.x-4:r.x+r.w+4;

      ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(ex,ay);ctx.lineTo(cx,cy);
      ctx.strokeStyle=`rgba(${c.rgb},${iS?0.5:0.2})`;ctx.lineWidth=0.8;
      ctx.setLineDash([3,3]);ctx.stroke();ctx.setLineDash([]);

      ctx.beginPath();ctx.arc(cx,cy,2,0,Math.PI*2);ctx.fillStyle=c.hex;ctx.fill();

      const text=fmt(label);
      ctx.font="500 9px 'DM Mono',monospace";
      const tw=ctx.measureText(text).width;
      const pw=tw+16,ph=20,px=side<0?ax-pw:ax,py=ay-ph/2;
      ctx.fillStyle=iS?`rgba(${c.rgb},0.1)`:"rgba(15,14,12,0.8)";
      ctx.fillRect(px,py,pw,ph);
      ctx.strokeStyle=`rgba(${c.rgb},${iS?0.4:0.15})`;ctx.lineWidth=0.5;ctx.strokeRect(px,py,pw,ph);

      ctx.beginPath();ctx.arc(px+7,py+ph/2,2.5,0,Math.PI*2);ctx.fillStyle=c.hex;ctx.fill();
      ctx.fillStyle=iS?"rgba(245,241,235,0.9)":"rgba(245,241,235,0.5)";
      ctx.textAlign="left";ctx.textBaseline="middle";ctx.fillText(text,px+14,py+ph/2+0.5);
    });
    ctx.restore();
  },[imgOk,curParts,sel,hov,sharpMode,tf,ir,td,mods,textures]);

  useEffect(()=>{draw();},[draw]);
  useEffect(()=>{if(!contRef.current)return;const ro=new ResizeObserver(()=>draw());ro.observe(contRef.current);return()=>ro.disconnect();},[draw]);

  const ht=useCallback((cx,cy)=>{
    if(!contRef.current)return null;
    const rect=contRef.current.getBoundingClientRect();
    const mx=(cx-rect.left-tf.x)/tf.s,my=(cy-rect.top-tf.y)/tf.s;
    const r=ir();
    for(let i=curParts.length-1;i>=0;i--){
      const pts=(curParts[i].cm||curParts[i].mask).map(([x,y])=>td(x,y,r));
      if(pip(mx,my,pts))return curParts[i].label;
    }return null;
  },[curParts,tf,ir,td]);

  const onMv=useCallback(e=>{
    if(drag.current.on){
      const dx=e.clientX-drag.current.sx,dy=e.clientY-drag.current.sy;
      if(Math.abs(dx)>3||Math.abs(dy)>3)drag.current.moved=true;
      setTf(t=>({...t,x:drag.current.tx+dx,y:drag.current.ty+dy}));return;
    }
    const hit=ht(e.clientX,e.clientY);
    setHov(hit);
    if(contRef.current)contRef.current.style.cursor=hit?"pointer":"grab";
    if(hit&&contRef.current){
      const rect=contRef.current.getBoundingClientRect();
      setTooltip({label:hit,x:e.clientX-rect.left,y:e.clientY-rect.top});
    }else{setTooltip(null);}
  },[ht]);
  const onDn=useCallback(e=>{drag.current={on:true,sx:e.clientX,sy:e.clientY,tx:tf.x,ty:tf.y,moved:false};if(contRef.current)contRef.current.style.cursor="grabbing";},[tf]);
  const onUp=useCallback(()=>{drag.current.on=false;if(contRef.current)contRef.current.style.cursor="grab";},[]);
  const onCk=useCallback(e=>{if(drag.current.moved){drag.current.moved=false;return;}const hit=ht(e.clientX,e.clientY);if(hit)setSel(prev=>prev===hit?null:hit);},[ht]);
  const onWh=useCallback(e=>{e.preventDefault();const f=e.deltaY>0?0.93:1.07;setTf(t=>{const ns=Math.max(0.3,Math.min(5,t.s*f));const rect=contRef.current.getBoundingClientRect();const mx=e.clientX-rect.left,my=e.clientY-rect.top;return{s:ns,x:mx-(mx-t.x)*(ns/t.s),y:my-(my-t.y)*(ns/t.s)};});},[]);

  function handleFile(e){const f=e.target.files?.[0];if(!f)return;setFile(f);const r=new FileReader();r.onload=()=>setImgUrl(r.result);r.readAsDataURL(f);}

  async function upload(){
    if(!file)return;setLoading(true);setUploadErr("");
    try{const form=new FormData();form.append("file",file);
      const uploadUrl=`${UPLOAD}?furniture_type=${encodeURIComponent(furnitureType)}`;
      const resp=await fetch(uploadUrl,{method:"POST",body:form});
      if(!resp.ok){setUploadErr(`Failed: ${resp.status}`);return;}
      const d=await resp.json();const p=d?.analysis||{};
      setResult(p);setClassData(p);setPhase(d.phase||"ANALYSIS");setSid(d.session_id);
      setChat([{role:"assistant",content:latestAssistantReply(d.assistant_reply)}]);
      setMods({});setRcGeom({});setAiFb("");setTextures({});
    }catch(err){setUploadErr(err.message);}finally{setLoading(false);}
  }

  async function sendChat(){
    if(!chatIn.trim()||chatBusy)return;const msg=chatIn.trim();
    setChat(p=>[...p,{role:"user",content:msg}]);setChatIn("");setChatBusy(true);
    try{const resp=await fetch(UPLOAD,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:msg,session_id:sid,phase,classification_data:classData})});
      if(!resp.ok){setChat(p=>[...p,{role:"assistant",content:"Failed."}]);return;}
      const d=await resp.json();setPhase(d.phase);setChat(p=>[...p,{role:"assistant",content:latestAssistantReply(d.assistant_reply)}]);
    }catch(err){setChat(p=>[...p,{role:"assistant",content:err.message}]);}finally{setChatBusy(false);}
  }

  const uMod=useCallback((label,key,val)=>{
    setMods(prev=>{
      const c=prev[label]||{sx:1,sy:1,sl:0,tx:0,ty:0};const u={...c,[key]:val};
      if(u.sx===1&&u.sy===1&&u.sl===0&&u.tx===0&&u.ty===0){const n={...prev};delete n[label];return n;}
      const nx={...prev,[label]:u};const rl=role(label);const ru=ADJ[label]||ADJ[rl];
      if(ru){
        if(rl==="seat"&&key==="sx")ru.ch.forEach(cl=>{const cp=origParts.find(p=>p.label===cl);if(cp){const cm=nx[cl]||{sx:1,sy:1,sl:0,tx:0,ty:0};nx[cl]={...cm,sx:1+(val-1)*0.5};}});
        if(rl==="backrest"&&key==="sy"){const hp=origParts.find(p=>p.label==="headrest");if(hp){const ob=origParts.find(p=>p.label===label)?.bbox||[0,0,0,0];const hm=nx["headrest"]||{sx:1,sy:1,sl:0,tx:0,ty:0};nx["headrest"]={...hm,ty:-ob[3]*(val-1)*0.4};}}
      }return nx;
    });
  },[origParts]);

  const recalc=useCallback(async()=>{
    if(!hasMods)return;
    try{const pl=curParts.filter(p=>mods[p.label]).map(p=>({label:p.label,mask:p.cm||p.mask,scale_x:mods[p.label]?.sx||1,scale_y:mods[p.label]?.sy||1}));
      if(!pl.length)return;
      const resp=await fetch(`${API}/recalculate-geometry`,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({parts:pl,px_per_mm:result?.scale_factor?.px_per_mm||null,seat_meta:null})});
      if(resp.ok){const d=await resp.json();const ng={};(d.parts||[]).forEach(p=>{ng[p.label]=p.geometry;});setRcGeom(prev=>({...prev,...ng}));}
    }catch(err){console.error(err);}
  },[curParts,mods,result,hasMods]);

  const getAi=useCallback(async()=>{
    if(!hasMods)return;setAiFbLoad(true);setAiFb("");
    try{const ms=Object.entries(mods).map(([l,m])=>{const o=origParts.find(p=>p.label===l);const r2=rcGeom[l];
      return{label:l,changes:{scaleX:m.sx,scaleY:m.sy,shapeLevel:m.sl},original_measurements:o?.geometry?.measurements||{},new_measurements:r2?.measurements||{},original_flags:o?.geometry?.ergonomic_flags||[],new_flags:r2?.ergonomic_flags||[]};});
      const resp=await fetch(`${API}/ai-feedback`,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({session_id:sid||"v",chair_type:result?.identified_type||"Unknown",is_hybrid:result?.is_hybrid||false,influences:result?.influences||[],modifications:ms,classification_data:result})});
      if(resp.ok){const d=await resp.json();setAiFb(d.feedback||"");}else setAiFb("Failed.");
    }catch(err){setAiFb(err.message);}finally{setAiFbLoad(false);}
  },[mods,origParts,rcGeom,result,sid,hasMods]);

  /* Preserve last-selected part's data so panels never go empty once you've selected something */
  const lastSelRef=useRef(null);
  useEffect(()=>{ if(sel)lastSelRef.current=sel; },[sel]);
  const effectiveSel=sel||lastSelRef.current;

  /* Apply texture to selected part */
  const applyTexture=useCallback((src)=>{
    const label=sel||lastSelRef.current;
    if(!label)return;
    // Check cache first
    if(texCache.current[src]){
      setTextures(prev=>({...prev,[label]:{src,image:texCache.current[src]}}));
      return;
    }
    const img=new Image();
    img.crossOrigin="anonymous";
    img.onload=()=>{
      texCache.current[src]=img;
      setTextures(prev=>({...prev,[label]:{src,image:img}}));
    };
    img.src=src;
  },[sel]);

  const clearTexture=useCallback((label)=>{
    setTextures(prev=>{const n={...prev};delete n[label];return n;});
  },[]);

  const selData=useMemo(()=>effectiveSel?curParts.find(p=>p.label===effectiveSel):null,[effectiveSel,curParts]);
  const hovData=useMemo(()=>hov?curParts.find(p=>p.label===hov):null,[hov,curParts]);

  /* ═══════════════════════════════════════════════════════════════════ */
  /* LANDING PAGE                                                         */
  /* ═══════════════════════════════════════════════════════════════════ */
  if(!result){
    return(
      <div className="da-landing">
        {/* ── HERO SECTION ────────────────────────────────────────── */}
        <section className="da-hero">
          <div className="da-hero-grid"/>

          {/* Center image — fixed, no float */}
          <div className="da-hero-center">
            <img src="/hand-pencil.png" alt="Hand sketching" className="da-hero-img"/>
          </div>

          {/* Floating feature cards — positioned around center */}
          <div className="da-feat da-feat-1" style={{animationDelay:"0.2s"}}>
            <div className="da-feat-marker"/>
            <div className="da-feat-line"/>
            <div className="da-feat-content">
              <h3>Sketch Analysis</h3>
              <p>AI-powered geometry extraction from hand-drawn chair sketches. Every curve, angle, and proportion — measured and interpreted.</p>
            </div>
          </div>

          <div className="da-feat da-feat-2" style={{animationDelay:"0.5s"}}>
            <div className="da-feat-marker"/>
            <div className="da-feat-line"/>
            <div className="da-feat-content">
              <h3>Interactive Rescale</h3>
              <p>Adjust any part's dimensions in real-time with a 2D coordinate interface. Watch ergonomic consequences update instantly.</p>
            </div>
          </div>

          <div className="da-feat da-feat-3" style={{animationDelay:"0.8s"}}>
            <div className="da-feat-marker"/>
            <div className="da-feat-line"/>
            <div className="da-feat-content">
              <h3>Intelligence Panels</h3>
              <p>Deep measurement data, shape descriptors, and ergonomic flags — all contextualised to the specific chair part and type.</p>
            </div>
          </div>

          <div className="da-feat da-feat-4" style={{animationDelay:"1.1s"}}>
            <div className="da-feat-marker"/>
            <div className="da-feat-line"/>
            <div className="da-feat-content">
              <h3>Shape Language</h3>
              <p>Contour smoothness, curvature analysis, symmetry scoring, and edge regularity — the geometry behind the design intent.</p>
            </div>
          </div>

          <div className="da-feat da-feat-5" style={{animationDelay:"1.4s"}}>
            <div className="da-feat-marker"/>
            <div className="da-feat-line"/>
            <div className="da-feat-content">
              <h3>Ergonomic Audit</h3>
              <p>Every dimension checked against role-specific benchmarks. AI assessment of modifications with structural consequence analysis.</p>
            </div>
          </div>

          <div className="da-feat da-feat-6" style={{animationDelay:"1.7s"}}>
            <div className="da-feat-marker"/>
            <div className="da-feat-line"/>
            <div className="da-feat-content">
              <h3>Material Engine</h3>
              <p>Apply leather, fabric, metal, and wood textures directly to mask regions. Multiply-blended over the original sketch lines.</p>
            </div>
          </div>

          {/* App name — bottom left, animated entrance */}
          <div className="da-hero-brand">
            <h1 className="da-hero-title">
              {"DESIGNABLE".split("").map((ch,i)=>(
                <span key={i} className="da-hero-letter" style={{animationDelay:`${0.6+i*0.06}s`}}>{ch}</span>
              ))}
              <span className="da-hero-ai-space"> </span>
              {"AI".split("").map((ch,i)=>(
                <span key={`ai${i}`} className="da-hero-letter da-hero-letter-accent" style={{animationDelay:`${1.3+i*0.06}s`}}>{ch}</span>
              ))}
            </h1>
            <span className="da-hero-sub">sketch → intelligence</span>
          </div>

          {/* Scroll indicator */}
          <div className="da-hero-scroll">
            <span>Scroll to begin</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
        </section>

        {/* ── UPLOAD SECTION ──────────────────────────────────────── */}
        <section className="da-upload-section">
          <div className="da-upload-section-grid"/>
          <div className="da-upload-section-inner">
            <h2 className="da-upload-heading">Begin your <em>analysis</em></h2>
            <p className="da-upload-desc">Choose furniture type, then upload the matching sketch with optional measurement labels.</p>

            <div className="da-type-switch" role="radiogroup" aria-label="Furniture type">
              {FURNITURE_TYPES.map(type=>{
                const active=furnitureType===type;
                return(
                  <button
                    key={type}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    className={`da-type-chip ${active?"active":""}`}
                    onClick={()=>setFurnitureType(type)}
                  >
                    {type[0].toUpperCase()+type.slice(1)}
                  </button>
                );
              })}
            </div>

            <div className={`da-upload-zone ${imgUrl?"has-preview":""}`} onClick={()=>fRef.current?.click()}>
              {imgUrl?(
                <div className="da-upload-preview">
                  <img src={imgUrl} alt="Preview"/>
                  <div className="da-preview-overlay">Click to change</div>
                </div>
              ):(
                <div className="da-upload-inner">
                  <svg className="da-upload-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2"><path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0 0l-4-4m4 4l4-4" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  <span className="da-upload-label">Drop sketch here</span>
                  <span className="da-upload-sub">JPG, PNG — any size</span>
                </div>
              )}
              <input ref={fRef} type="file" accept="image/*" onChange={handleFile} style={{display:"none"}}/>
            </div>

            {imgUrl&&(
              <button className="da-cta" onClick={upload} disabled={loading}>
                {loading?<><span className="da-spin-dark"/>Analysing...</>:<>Analyse sketch <span className="da-cta-arrow">→</span></>}
              </button>
            )}
            {uploadErr&&<div className="da-upload-err">{uploadErr}</div>}

            <div className="da-hints">
              {furnitureType==="chair"?(<>
                <span className="da-hint-chip">Eames</span>
                <span className="da-hint-chip">Wing chair</span>
                <span className="da-hint-chip">Office</span>
                <span className="da-hint-chip">Egg shell</span>
              </>):(<>
                <span className="da-hint-chip">Dining table</span>
                <span className="da-hint-chip">Coffee table</span>
                <span className="da-hint-chip">Round top</span>
                <span className="da-hint-chip">Four-leg base</span>
              </>)}
            </div>
          </div>
        </section>
        
       {/* ── SCULPT STUDIO SECTION ───────────────────────────────── */}
        <section className="da-sculpt-section">
          <div className="da-sculpt-grid"/>
          <div className="da-sculpt-inner">
            <div className="da-sculpt-text">
              <span className="da-sculpt-badge">New</span>
              <h2 className="da-sculpt-title">3D Sculpt <em>Studio</em></h2>
              <p className="da-sculpt-desc">
                Mould digital clay into any chair form. Drag parts from the inventory,
                reshape with push, pull, smooth, and crease tools. Snap parts together
                and send your creation directly to AI analysis.
              </p>
              <div className="da-sculpt-features">
                <div className="da-sculpt-feat">
                  <span className="da-sculpt-feat-icon">◆</span>
                  <div>
                    <strong>Part Inventory</strong>
                    <p>Pre-shaped seats, backrests, armrests, legs — or start from a basic blob</p>
                  </div>
                </div>
                <div className="da-sculpt-feat">
                  <span className="da-sculpt-feat-icon">◆</span>
                  <div>
                    <strong>Sculpting Brushes</strong>
                    <p>Push, pull, smooth, flatten, and crease — full control over every surface</p>
                  </div>
                </div>
                <div className="da-sculpt-feat">
                  <span className="da-sculpt-feat-icon">◆</span>
                  <div>
                    <strong>Magnetic Assembly</strong>
                    <p>Parts snap to correct positions — seat, back, arms, legs align automatically</p>
                  </div>
                </div>
              </div>
              <button className="da-sculpt-cta" onClick={()=>navigate("/sculpt")}>
                Enter Sculpt Studio <span className="da-sculpt-arrow">→</span>
              </button>
            </div>
            <div className="da-sculpt-visual">
              <div className="da-sculpt-orb">
                <div className="da-sculpt-orb-inner"/>
                <div className="da-sculpt-orb-ring"/>
              </div>
            </div>
          </div>
        </section>
 

        {/* ── DRAWING CANVAS TEASER ───────────────────────────────── */}
        <section className="da-canvas-section">
          <div className="da-canvas-inner">
            <span className="da-canvas-badge">Coming soon</span>
            <h2 className="da-canvas-title">Drawing Canvas</h2>
            <p className="da-canvas-desc">Sketch directly in the browser with pressure-sensitive tools, layer management, and real-time AI feedback as you draw.</p>
            <div className="da-canvas-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3">
                <path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          </div>
        </section>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════ */
  /* WORKSPACE                                                            */
  /* ═══════════════════════════════════════════════════════════════════ */
  return(
    <div className="da-workspace">
      <header className="da-ws-header">
        <button className="da-ws-back" onClick={()=>{setResult(null);setImgOk(false);setFile(null);setImgUrl(null);setChat([]);setMods({});setRcGeom({});setAiFb("");setTextures({});setSel(null);setPanelIdx(0);}}>← Back</button>
        <span className="da-ws-logo">Designable<span className="da-dot">.</span></span>
        <div className="da-ws-info">
          <span className="da-ws-type">{result.identified_type}</span>
          {result.is_hybrid&&<span className="da-ws-hybrid">Hybrid</span>}
          {sel&&<span className="da-ws-selected">● {fmt(sel)}</span>}
         
        </div>
        <div className="da-ws-actions">
          <button className={`da-ws-btn ${sharpMode?"active":""}`} onClick={()=>setSharpMode(s=>!s)}>{sharpMode?"● Sharpness":"○ Sharpness"}</button>
          <button className="da-ws-btn" onClick={()=>setTf({x:0,y:0,s:1})}>Fit</button>
          <button className="da-ws-btn accent" onClick={()=>{
  // Strip non-serializable image objects — only pass src strings
  const serializableTextures = Object.fromEntries(
    Object.entries(textures).map(([label, tex]) => [label, { src: tex.src }])
  );
  navigate("/room-preview", { state: { imgUrl, curParts, serializableTextures, imgD } });
}}>⊞ Room Preview</button>
          <button className="da-ws-btn accent" onClick={()=>fRef.current?.click()}>New sketch</button>
          <input ref={fRef} type="file" accept="image/*" onChange={e=>{handleFile(e);setResult(null);setImgOk(false);}} style={{display:"none"}}/>
        </div>
      </header>

      <div className="da-ws-body">
        {/* LEFT: Chat (collapsible) */}
        <aside className={`da-ws-chat ${chatCollapsed?"collapsed":""}`}>
          {chatCollapsed?(
            <button className="da-ws-chat-expand" onClick={()=>setChatCollapsed(false)} title="Expand chat">
              <span className="da-ws-chat-vlabel">Chat</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </button>
          ):(<>
            <div className="da-ws-chat-head">
              <span>Design Assistant</span>
              <button className="da-ws-chat-collapse" onClick={()=>setChatCollapsed(true)} title="Collapse chat">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M15 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </button>
            </div>
            <div className="da-ws-chat-msgs">
              {chat.map((m,i)=>(
                <div key={i} className={`da-ws-msg ${m.role}`}>
                  {m.role==="assistant"?<ReactMarkdown>{m.content}</ReactMarkdown>:m.content}
                </div>
              ))}
              {chatBusy&&<div className="da-ws-msg assistant"><span className="da-spin"/>Thinking...</div>}
              <div ref={chatEnd}/>
            </div>
            <div className="da-ws-chat-in">
              <input value={chatIn} onChange={e=>setChatIn(e.target.value)} placeholder="Ask about your design..."
                onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat();}}}/>
              <button onClick={sendChat} disabled={chatBusy||!chatIn.trim()}>→</button>
            </div>
          </>)}
        </aside>

        {/* CENTER: Canvas */}
        <div className="da-ws-canvas" ref={contRef}
          onMouseMove={onMv} onMouseDown={onDn} onMouseUp={onUp}
          onMouseLeave={()=>{onUp();setTooltip(null);}} onClick={onCk} onWheel={onWh}>
          <canvas ref={canRef}/>
          {tooltip&&hovData&&!sel&&(<HoverTooltip part={hovData} x={tooltip.x} y={tooltip.y}/>)}
        </div>

        {/* RIGHT: Carousel panel */}
        <aside className="da-ws-carousel">
          <CarouselPanel
            panelIdx={panelIdx}
            setPanelIdx={setPanelIdx}
            isTable={result?.furniture_type==="table"}
            selData={selData}
            mods={mods}
            origParts={origParts}
            rcGeom={rcGeom}
            aiFb={aiFb}
            aiFbLoad={aiFbLoad}
            hasMods={hasMods}
            onMod={uMod}
            onRecalc={recalc}
            onGetAi={getAi}
            selLabel={effectiveSel}
            textures={textures}
            onApplyTexture={applyTexture}
            onClearTexture={clearTexture}
          />
        </aside>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* HOVER TOOLTIP                                                           */
/* ═══════════════════════════════════════════════════════════════════════ */

function HoverTooltip({part,x,y}){
  const g=part.geometry;if(!g)return null;
  const shape=g.shape||{};const flags=g.ergonomic_flags||[];
  const sm=shape.contour_smoothness;const cv=shape.curvature;const ps=shape.proportional_size;
  return(
    <div className="da-tooltip" style={{left:x+16,top:y-10}}>
      <div className="da-tooltip-head">{fmt(part.label)}</div>
      {sm&&<div className="da-tooltip-row"><span className="da-tooltip-k">Form</span><span>{sm.label}</span></div>}
      {cv&&<div className="da-tooltip-row"><span className="da-tooltip-k">Surface</span><span>{cv.label}</span></div>}
      {ps&&<div className="da-tooltip-row"><span className="da-tooltip-k">Size</span><span>{ps.label}</span></div>}
      {flags.filter(f=>f.status!=="ok").map((f,i)=>(
        <div key={i} className={`da-tooltip-flag ${f.status}`}>
          {f.status==="critical"?"✕":"⚠"} {f.field}: {f.measured}
        </div>
      ))}
      {flags.length>0&&flags.every(f=>f.status==="ok")&&<div className="da-tooltip-ok">All checks passed</div>}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* CAROUSEL PANEL                                                          */
/* ═══════════════════════════════════════════════════════════════════════ */

function CarouselPanel({panelIdx,setPanelIdx,isTable=false,selData,mods,origParts,rcGeom,aiFb,aiFbLoad,hasMods,onMod,onRecalc,onGetAi,selLabel,textures,onApplyTexture,onClearTexture}){
  const selMod=selLabel?mods[selLabel]:null;
  const [direction,setDirection]=useState("right");
  const [animKey,setAnimKey]=useState(0);
  const visiblePanels=useMemo(()=>isTable?[0,1,3,4]:[0,1,2,3,4],[isTable]);
  const activePanel=visiblePanels.includes(panelIdx)?panelIdx:visiblePanels[0];

  useEffect(()=>{
    if(!visiblePanels.includes(panelIdx))setPanelIdx(visiblePanels[0]);
  },[panelIdx,visiblePanels,setPanelIdx]);

  const handleNext=()=>{
    setDirection("right");
    setAnimKey(k=>k+1);
    const idx=visiblePanels.indexOf(activePanel);
    const next=visiblePanels[(idx+1)%visiblePanels.length];
    setPanelIdx(next);
  };
  const handlePrev=()=>{
    setDirection("left");
    setAnimKey(k=>k+1);
    const idx=visiblePanels.indexOf(activePanel);
    const prev=visiblePanels[(idx-1+visiblePanels.length)%visiblePanels.length];
    setPanelIdx(prev);
  };
  const handleJump=(panel)=>{
    setDirection(panel>activePanel?"right":"left");
    setAnimKey(k=>k+1);
    setPanelIdx(panel);
  };

  const renderPanel=()=>{
    switch(activePanel){
      case 0: return selData
        ? <DimensionsPanel label={selLabel} mod={selMod} onMod={onMod} onRecalc={onRecalc}/>
        : <EmptyState msg="Click a part to adjust its dimensions"/>;
      case 1: return selData
        ? <MeasurementsPanel part={selData}/>
        : <EmptyState msg="Click a part to view measurements"/>;
      case 2: return selData
        ? <ShapePanel part={selData}/>
        : <EmptyState msg="Click a part to view shape analysis"/>;
      case 3: return <ErgoPanel mods={mods} origParts={origParts} rcGeom={rcGeom} aiFb={aiFb} aiFbLoad={aiFbLoad} hasMods={hasMods} onGetAi={onGetAi}/>;
      case 4: return <MaterialPanel
        selLabel={selLabel} selData={selData}
        textures={textures}
        onApply={onApplyTexture} onClear={onClearTexture}/>;
      default: return null;
    }
  };

  return(
    <div className="da-cp-wrap">
      <div className="da-cp-viewport">
        <div key={animKey} className={`da-cp-slide-in ${direction}`}>
          {renderPanel()}
        </div>
      </div>

      {/* Nav */}
      <div className="da-cp-nav">
        <button className="da-cp-arrow" onClick={handlePrev} title="Previous panel" aria-label="Previous">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M15 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
        <div className="da-cp-title-wrap">
          <span key={activePanel} className="da-cp-title">{PANEL_TITLES[activePanel]}</span>
          <div className="da-cp-dots">
            {visiblePanels.map((panel,i)=>(
              <button key={panel} className={`da-cp-dot ${panel===activePanel?"active":""}`} onClick={()=>handleJump(panel)} aria-label={`Panel ${i+1}`}/>
            ))}
          </div>
        </div>
        <button className="da-cp-arrow" onClick={handleNext} title="Next panel" aria-label="Next">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* PANEL 0: DIMENSIONS (2D coordinate UI)                                   */
/* ═══════════════════════════════════════════════════════════════════════ */

function DimensionsPanel({label,mod,onMod,onRecalc}){
  const sx=mod?.sx||1,sy=mod?.sy||1,sl=mod?.sl||0;
  const padRef=useRef(null);
  const [dragging,setDragging]=useState(false);

  // Pad is 160x160. Origin is center (sx=1, sy=1). Range: 0.5x to 2x = -80px to +80px
  const PAD=160;
  const handleX=((sx-1)/1)*80; // range -0.5 → -80px, +1 → +80px
  const handleY=-((sy-1)/1)*80; // inverted: bigger Y = up

  const handleMove=useCallback((clientX,clientY)=>{
    if(!padRef.current)return;
    const r=padRef.current.getBoundingClientRect();
    const cx=r.left+r.width/2,cy=r.top+r.height/2;
    const dx=Math.max(-80,Math.min(80,clientX-cx));
    const dy=Math.max(-80,Math.min(80,clientY-cy));
    // Map back to scale
    const nsx=Math.round((1+(dx/80))*100)/100;
    const nsy=Math.round((1-(dy/80))*100)/100;
    onMod(label,"sx",Math.max(0.5,Math.min(2,nsx)));
    onMod(label,"sy",Math.max(0.5,Math.min(2,nsy)));
  },[label,onMod]);

  const onDown=e=>{
    e.preventDefault();
    setDragging(true);
    handleMove(e.clientX,e.clientY);
    const mv=ev=>handleMove(ev.clientX,ev.clientY);
    const up=()=>{setDragging(false);onRecalc();window.removeEventListener("mousemove",mv);window.removeEventListener("mouseup",up);};
    window.addEventListener("mousemove",mv);
    window.addEventListener("mouseup",up);
  };

  const reset=()=>{onMod(label,"sx",1);onMod(label,"sy",1);onRecalc();};

  return(
    <div className="da-dim-wrap">
      <div className="da-dim-head">
        <span className="da-dim-part">{fmt(label)}</span>
      </div>

      <div className="da-dim-coord-wrap">
        <div className="da-dim-axis-label top">H +</div>
        <div className="da-dim-axis-label bottom">H −</div>
        <div className="da-dim-axis-label left">W −</div>
        <div className="da-dim-axis-label right">W +</div>

        <div ref={padRef} className={`da-dim-pad ${dragging?"dragging":""}`} onMouseDown={onDown}>
          {/* Grid lines */}
          <div className="da-dim-axis-h"/>
          <div className="da-dim-axis-v"/>
          <div className="da-dim-origin"/>
          {/* Handle */}
          <div className="da-dim-handle" style={{left:`calc(50% + ${handleX}px)`,top:`calc(50% + ${handleY}px)`}}/>
        </div>
      </div>

      <div className="da-dim-readout">
        <div className="da-dim-ro-item">
          <span className="da-dim-ro-k">Width</span>
          <span className="da-dim-ro-v">{(sx*100).toFixed(0)}%</span>
        </div>
        <div className="da-dim-ro-item">
          <span className="da-dim-ro-k">Height</span>
          <span className="da-dim-ro-v">{(sy*100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Shape slider (single axis, kept as linear control) */}
      <div className="da-dim-shape">
        <div className="da-dim-shape-label">
          <span>Shape</span>
          <span className="da-dim-shape-val">{sl<0?"Sharper":sl>0?"Smoother":"Original"}</span>
        </div>
        <div className="da-dim-shape-track">
          <div className="da-dim-shape-line"/>
          {[-3,-2,-1,0,1,2,3].map(v=>(
            <button key={v} className={`da-dim-shape-tick ${sl===v?"active":""} ${v===0?"center":""}`}
              onClick={()=>{onMod(label,"sl",v);onRecalc();}}
              style={{left:`${((v+3)/6)*100}%`}}
              title={v===0?"Original":v<0?`Sharpen ${Math.abs(v)}`:`Smooth ${v}`}/>
          ))}
        </div>
        <div className="da-dim-shape-ends"><span>Sharp</span><span>Smooth</span></div>
      </div>

      <div className="da-dim-actions">
        <button className="da-dim-btn ghost" onClick={reset}>Reset</button>
        <button className="da-dim-btn primary" onClick={onRecalc}>Recalculate</button>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* PANEL 1: MEASUREMENTS (2x2 grid)                                         */
/* ═══════════════════════════════════════════════════════════════════════ */

function MeasurementsPanel({part}){
  const g=part.geometry;if(!g)return null;
  const m=g.measurements||{};
  const raw=g._raw||{};
  const items=[];
  if(m.width_mm!=null)items.push({l:"Width",v:`${m.width_mm}`,u:"mm"});
  else if(m.width_px!=null)items.push({l:"Width",v:`${m.width_px}`,u:"px"});
  if(m.height_mm!=null)items.push({l:"Height",v:`${m.height_mm}`,u:"mm"});
  else if(m.height_px!=null)items.push({l:"Height",v:`${m.height_px}`,u:"px"});

  if(m.curvature_radius!=null)items.push({l:"Curve Radius",v:`${m.curvature_radius}`,u:m.curvature_radius_unit||""});
  if(m.compactness!=null)items.push({l:"Compactness",v:m.compactness,u:""});
  if(m.scale_vs_seat!=null)items.push({l:"Scale vs Seat",v:`${m.scale_vs_seat}`,u:"×"});
  if(m.dominant_angle_deg!=null)items.push({l:"Dominant Axis",v:`${m.dominant_angle_deg}`,u:"°"});
  if(m.area_mm2!=null)items.push({l:"Area",v:`${m.area_mm2}`,u:"mm²"});
  else if(m.area_px!=null)items.push({l:"Area",v:`${m.area_px}`,u:"px²"});
  if(raw.solidity!=null)items.push({l:"Solidity",v:raw.solidity,u:""});
  if(raw.aspect_ratio!=null)items.push({l:"Aspect Ratio",v:raw.aspect_ratio,u:""});

  return(
    <div className="da-ms-wrap">
      <div className="da-ms-head">
        <span className="da-ms-part">{fmt(part.label)}</span>
        <span className="da-ms-role" style={{color:rc(part.label).hex}}>{role(part.label)}</span>
      </div>
      <div className="da-ms-grid">
        {items.map((it,i)=>(
          <div key={i} className="da-ms-card">
            <div className="da-ms-k">{it.l}</div>
            <div className="da-ms-v">{it.v}<span className="da-ms-u">{it.u}</span></div>
          </div>
        ))}
      </div>
      {items.length===0&&<div className="da-empty-inner">No measurement data available</div>}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* PANEL 2: SHAPE DESCRIPTORS + FLAGS                                       */
/* ═══════════════════════════════════════════════════════════════════════ */

function ShapePanel({part}){
  const g=part.geometry;if(!g)return null;
  const shape=g.shape||{};
  const flags=g.ergonomic_flags||[];
  const sh=sharp(g);
  const KEYS=["contour_smoothness","curvature","orientation","proportional_size","symmetry","edge_regularity"];

  return(
    <div className="da-sh-wrap">
      <div className="da-sh-head">
        <span className="da-sh-part">{fmt(part.label)}</span>
        <span className="da-sh-role" style={{color:rc(part.label).hex}}>{role(part.label)}</span>
      </div>

      {/* Sharpness bar */}
      <div className="da-sh-sharp">
        <div className="da-sh-sharp-lbl">Edge Sharpness</div>
        <div className="da-sh-sharp-track">
          <div className="da-sh-sharp-bar"/>
          <div className="da-sh-sharp-thumb" style={{left:`${sh*100}%`}}/>
        </div>
        <div className="da-sh-sharp-ends"><span>Soft</span><span>Sharp</span></div>
      </div>

      <div className="da-sh-section-title">Shape Descriptors</div>
      {KEYS.map(k=>{
        const d=shape[k];if(!d)return null;
        return(
          <div key={k} className="da-sh-desc">
            <div className="da-sh-desc-k">{k.replace(/_/g," ")}</div>
            <div className="da-sh-desc-l">{d.label}</div>
            {d.detail&&<div className="da-sh-desc-d">{d.detail}</div>}
            {d.design_interpretation&&<div className="da-sh-interp design"><span className="da-sh-itag">Design</span>{d.design_interpretation}</div>}
            {d.ergonomic_interpretation&&<div className="da-sh-interp ergo"><span className="da-sh-itag">Ergo</span>{d.ergonomic_interpretation}</div>}
            {d.width_note&&<div className="da-sh-interp size"><span className="da-sh-itag">Width</span>{d.width_note}</div>}
            {d.height_note&&<div className="da-sh-interp size"><span className="da-sh-itag">Height</span>{d.height_note}</div>}
          </div>
        );
      })}

      {flags.length>0&&(<>
        <div className="da-sh-section-title">Ergonomic Flags</div>
        {flags.map((f,i)=>(
          <div key={i} className={`da-sh-flag ${f.status}`}>
            <div className="da-sh-flag-top">
              <span className={`da-sh-flag-st ${f.status}`}>{f.status==="ok"?"✓":f.status==="warning"?"⚠":"✕"} {f.status?.toUpperCase()}</span>
              <span className="da-sh-flag-field">{f.field?.toUpperCase()}</span>
            </div>
            <div className="da-sh-flag-vals"><span>Measured: <strong>{f.measured}</strong></span><span>Benchmark: {f.benchmark}</span></div>
            <div className="da-sh-flag-note">{f.note}</div>
          </div>
        ))}
      </>)}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* PANEL 3: ERGONOMICS & AI                                                 */
/* ═══════════════════════════════════════════════════════════════════════ */

function ErgoPanel({mods,origParts,rcGeom,aiFb,aiFbLoad,hasMods,onGetAi}){
  if(!hasMods){
    return(<div className="da-empty-inner">Make adjustments to see ergonomic impact</div>);
  }
  return(
    <div className="da-er-wrap">
      <div className="da-er-head">
        <span>Modification Log</span>
        <button className="da-er-ai-btn" onClick={onGetAi} disabled={aiFbLoad}>
          {aiFbLoad?<><span className="da-spin"/>Analysing</>:"AI Assessment"}
        </button>
      </div>

      <div className="da-er-cards">
        {Object.entries(mods).map(([l,m])=>{
          const o=origParts.find(p=>p.label===l);const r2=rcGeom[l];
          return(
            <div key={l} className="da-er-card">
              <div className="da-er-card-h">
                <span className="da-pdot" style={{background:rc(l).hex}}/>
                <span className="da-er-card-name">{fmt(l)}</span>
                <span className="da-er-delta">
                  {m.sx!==1&&`W:${(m.sx*100).toFixed(0)}%`}
                  {m.sx!==1&&m.sy!==1&&" "}
                  {m.sy!==1&&`H:${(m.sy*100).toFixed(0)}%`}
                  {m.sl!==0&&` ${m.sl<0?"Sharper":"Smoother"}`}
                </span>
              </div>
              {r2?(r2.ergonomic_flags||[]).map((f,i)=>{
                const of2=(o?.geometry?.ergonomic_flags||[])[i];const ch=of2&&of2.status!==f.status;
                return(
                  <div key={i} className={`da-er-flag ${ch?"changed":""}`}>
                    <span className={`da-er-st ${f.status}`}>{f.status==="ok"?"✓":f.status==="warning"?"⚠":"✕"}</span>
                    <span className="da-er-fn">{f.field}</span>
                    <span className="da-er-fv">{f.measured}</span>
                    {ch&&<span className="da-er-was">was {of2.status}</span>}
                  </div>
                );
              }):<div className="da-er-hint">Recalculate to compute new flags</div>}
            </div>
          );
        })}
      </div>

      {aiFb&&(
        <div className="da-er-ai-result">
          <div className="da-er-ai-head">AI Assessment</div>
          <div className="da-er-ai-body"><ReactMarkdown>{aiFb}</ReactMarkdown></div>
        </div>
      )}
      {aiFbLoad&&!aiFb&&<div className="da-er-ai-loading"><span className="da-spin"/>Analysing modifications...</div>}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */
/* PANEL 4: MATERIAL ENGINE                                                 */
/* ═══════════════════════════════════════════════════════════════════════ */

function MaterialPanel({selLabel,selData,textures,onApply,onClear}){
  const [openCat,setOpenCat]=useState(null);
  const activeTex=selLabel?textures[selLabel]:null;

  if(!selData){
    return <EmptyState msg="Click a part to apply materials"/>;
  }

  const categories=Object.keys(MATERIAL_DATA); // leather, fabric, metal, wood

  return(
    <div className="da-mt-wrap">
      <div className="da-mt-head">
        <span className="da-mt-part">{fmt(selLabel)}</span>
        <span className="da-mt-role" style={{color:rc(selLabel).hex}}>{role(selLabel)}</span>
      </div>

      {activeTex&&(
        <div className="da-mt-active">
          <img src={activeTex.src} alt="Active" className="da-mt-active-thumb"/>
          <div className="da-mt-active-info">
            <span className="da-mt-active-label">Applied</span>
            <span className="da-mt-active-src">{activeTex.src.split("/").pop()}</span>
          </div>
          <button className="da-mt-clear" onClick={()=>onClear(selLabel)} title="Remove material">×</button>
        </div>
      )}

      <div className="da-mt-categories">
        {categories.map(cat=>{
          const isOpen=openCat===cat;
          const subCats=MATERIAL_DATA[cat];
          return(
            <div key={cat} className="da-mt-cat">
              <button className={`da-mt-cat-btn ${isOpen?"open":""}`} onClick={()=>setOpenCat(isOpen?null:cat)}>
                <span className="da-mt-cat-name">{cat}</span>
                <svg className={`da-mt-cat-chev ${isOpen?"open":""}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </button>
              {isOpen&&(
                <div className="da-mt-subcats">
                  {Object.entries(subCats).map(([subName,swatches])=>(
                    <div key={subName} className="da-mt-subcat">
                      <div className="da-mt-subcat-name">{subName}</div>
                      <div className="da-mt-swatches">
                        {swatches.map((sw,i)=>{
                          const isActive=activeTex?.src===sw.src;
                          return(
                            <button key={i} className={`da-mt-swatch ${isActive?"active":""}`}
                              onClick={()=>onApply(sw.src)} title={sw.name}>
                              <img src={sw.src} alt={sw.name}/>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════ */

function EmptyState({msg}){
  return(
    <div className="da-empty-inner">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{opacity:0.2,marginBottom:10}}>
        <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01" strokeLinecap="round"/>
      </svg>
      <p>{msg}</p>
    </div>
  );
}