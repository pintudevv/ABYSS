"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import {
  motion,
  useInView,
  AnimatePresence,
  useScroll,
  useTransform,
  useSpring,
} from "framer-motion";
import { useRouter } from "next/navigation";
import { uploadFile, getStatus, formatFileSize, TaskStatus, TelemetryLog } from "@/lib/api";
import FileUpload from "@/components/FileUpload";
import ProgressPipeline from "@/components/ProgressPipeline";
import { Shield, AlertTriangle, Terminal, ArrowUpRight, ArrowRight } from "lucide-react";

/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   DESIGN TOKENS  (color-expert: OKLCH semantic token architecture)
   Reference -> Semantic -> Component
   All values verified sRGB in-gamut.
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
const C = {
  n50:  "#070709",
  n100: "#0D0D12",
  n200: "#13131A",
  n300: "#71717A",
  n400: "#A1A1AA",
  n600: "#D4D4D8",
  n900: "#F4F4F6",
  a500: "#FF2E55",
  a400: "#FF4D6D",
  a100: "rgba(255, 46, 85, 0.12)",
  bg:        "#070709",
  card:      "rgba(13, 13, 18, 0.85)",
  border:    "rgba(255, 255, 255, 0.08)",
  borderDim: "rgba(255, 255, 255, 0.04)",
  text:      "#F4F4F6",
  muted:     "#A1A1AA",
  accent:    "#FF2E55",
  accentRed: "#FF2E55",
  accentMid: "#C0392B",
  dark:      "#070709",
  darkBorder:"rgba(255, 255, 255, 0.12)",
  darkMuted: "#71717A",
};

/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   GLOBAL CSS  (modern-web-design: fluid type scale, keyframes, grain)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300..900;1,14..32,300..900&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --step--2: clamp(0.65rem,  0.62rem + 0.15vw, 0.78rem);
  --step--1: clamp(0.78rem,  0.74rem + 0.20vw, 0.9rem);
  --step-0:  clamp(0.9rem,   0.84rem + 0.30vw, 1.1rem);
  --step-1:  clamp(1.1rem,   0.98rem + 0.60vw, 1.5rem);
  --step-2:  clamp(1.4rem,   1.15rem + 1.25vw, 2.2rem);
  --step-3:  clamp(1.9rem,   1.45rem + 2.25vw, 3.4rem);
  --step-4:  clamp(2.6rem,   1.8rem  + 4.00vw, 5.4rem);
  --step-5:  clamp(3.8rem,   2.4rem  + 7.00vw, 8.5rem);
}

html { scroll-behavior: smooth; }
body {
  background: ${C.bg};
  color: ${C.text};
  font-family: 'Inter', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}

/* Grain noise texture overlay */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: 0.028;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 180px 180px;
}



/* Marquee */
.marquee-track {
  display: flex;
  gap: 0;
  animation: marquee 28s linear infinite;
  white-space: nowrap;
}
@keyframes marquee {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

/* 3D scene */
.scene { perspective: 1200px; perspective-origin: 50% 42%; }
@keyframes floatCard {
  0%,100% { transform: rotateX(8deg) rotateY(-14deg) translateY(0px); }
  50%      { transform: rotateX(10deg) rotateY(-17deg) translateY(-10px); }
}
@keyframes spin1 { to { transform: rotate(360deg); } }
@keyframes glowPulse {
  0%,100% { opacity: 0.18; }
  50%      { opacity: 0.55; }
}
.float-card { animation: floatCard 7s ease-in-out infinite; transform-style: preserve-3d; }
.glow  { animation: glowPulse 3s ease-in-out infinite; }
.three-canvas { position: fixed; inset: 0; width: 100vw !important; height: 100vh !important; display: block; pointer-events: none; z-index: 0; }
@keyframes shimmer {
  0%   { transform: translateX(-100%) skewX(-12deg); }
  100% { transform: translateX(220%) skewX(-12deg); }
}
.glass-shimmer { overflow: hidden; }
.glass-shimmer::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, transparent 0%, oklch(100% 0 0 / 0.05) 50%, transparent 100%);
  animation: shimmer 5s ease-in-out infinite;
  pointer-events: none;
  z-index: 10;
}

/* Radar sweep */
@keyframes radarSweep {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.radar-sweep { animation: radarSweep 4s linear infinite; }

/* Node pulse */
@keyframes nodePulse {
  0%,100% { r: 2.5; opacity: 0.6; }
  50%      { r: 4;   opacity: 1; }
}
.node-pulse { animation: nodePulse 2.5s ease-in-out infinite; }

/* Clip-path reveal */
.clip-reveal { clip-path: inset(0 0 100% 0); }
.clip-visible { clip-path: inset(0 0 0% 0); transition: clip-path 0.8s cubic-bezier(0.22,1,0.36,1); }

/* Hover line underline */
.hover-line {
  position: relative;
  display: inline-block;
}
.hover-line::after {
  content: '';
  position: absolute;
  bottom: -2px; left: 0;
  width: 0; height: 1.5px;
  background: currentColor;
  transition: width 0.3s cubic-bezier(0.22,1,0.36,1);
}
.hover-line:hover::after { width: 100%; }

/* Card lift */
.card-lift {
  transition: transform 0.35s cubic-bezier(0.22,1,0.36,1), box-shadow 0.35s;
}
.card-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 48px oklch(16% 0.012 285 / 0.08);
}

@keyframes floatParticle {
  0% { transform: translateY(0px) scale(0.9); opacity: 0.2; }
  50% { transform: translateY(-40px) scale(1.1); opacity: 0.7; }
  100% { transform: translateY(-80px) scale(0.9); opacity: 0.2; }
}

@keyframes scanline {
  0% { transform: translateY(-100vh); }
  100% { transform: translateY(100vh); }
}

.cyber-scanline {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  background: linear-gradient(to bottom, transparent 95%, rgba(255,46,85,0.08) 98%, transparent 100%);
  animation: scanline 8s linear infinite;
}
`;



/* ─────────────────────────────────────────────────────────────────────────────
   HERO VISUAL — PE entropy heatmap (what real malware analysis tools show)
/* ─────────────────────────────────────────────────────────────────────────────
   THREE.JS THREAT NETWORK — animated 3D node graph for the hero background
───────────────────────────────────────────────────────────────────────────── */
function ThreeScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const W = canvas.offsetWidth  || 1280;
    const H = canvas.offsetHeight || 860;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setClearColor(0x000000, 0);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(52, W / H, 0.1, 2000);
    camera.position.set(0, 0, 430);

    const NODE_COUNT   = 120;
    const THREAT_COUNT = 8;
    const positions: THREE.Vector3[] = [];
    const group = new THREE.Group();

    const sphereGeo  = new THREE.SphereGeometry(2.4, 10, 10);
    const normalMat  = new THREE.MeshBasicMaterial({ color: 0x2A2D3E, transparent: true, opacity: 0.6 });
    const accentMat  = new THREE.MeshBasicMaterial({ color: 0x00D2FF, transparent: true, opacity: 0.8 });
    const threatMat  = new THREE.MeshBasicMaterial({ color: 0xFF2E55 });

    for (let i = 0; i < NODE_COUNT; i++) {
      const theta = Math.acos(2 * Math.random() - 1);
      const phi   = 2 * Math.PI * Math.random();
      const r     = 130 + Math.random() * 140;
      const pos   = new THREE.Vector3(
        r * Math.sin(theta) * Math.cos(phi),
        r * Math.sin(theta) * Math.sin(phi) * 0.55,
        r * Math.cos(theta),
      );
      positions.push(pos);
      const mat  = i < THREAT_COUNT ? threatMat : (i < 25 ? accentMat : normalMat);
      const mesh = new THREE.Mesh(sphereGeo, mat);
      mesh.position.copy(pos);
      group.add(mesh);
    }

    // Threat rings (red halo around threat nodes)
    const ringGeo = new THREE.RingGeometry(4.5, 6.2, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xFF2E55, transparent: true, opacity: 0.45, side: THREE.DoubleSide });
    for (let i = 0; i < THREAT_COUNT; i++) {
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(positions[i]);
      ring.lookAt(camera.position);
      group.add(ring);
    }

    // Edges
    const edgePts: number[] = [];
    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        if (positions[i].distanceTo(positions[j]) < 145) {
          edgePts.push(...positions[i].toArray(), ...positions[j].toArray());
        }
      }
    }
    const edgeGeo = new THREE.BufferGeometry();
    edgeGeo.setAttribute("position", new THREE.Float32BufferAttribute(edgePts, 3));
    const edgeMat  = new THREE.LineBasicMaterial({ color: 0x1A1D2B, transparent: true, opacity: 0.5 });
    const edges    = new THREE.LineSegments(edgeGeo, edgeMat);

    scene.add(group);
    scene.add(edges);

    let frameId: number;
    let mx = 0, my = 0;
    const onMouse = (e: MouseEvent) => {
      mx = (e.clientX / window.innerWidth  - 0.5) * 0.35;
      my = (e.clientY / window.innerHeight - 0.5) * 0.22;
    };
    window.addEventListener("mousemove", onMouse);

    const animate = () => {
      frameId = requestAnimationFrame(animate);
      group.rotation.y += 0.0011;
      group.rotation.x += 0.0003;
      edges.rotation.copy(group.rotation);
      camera.position.x += (mx * 45 - camera.position.x) * 0.04;
      camera.position.y += (-my * 32 - camera.position.y) * 0.04;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      const w = canvas.offsetWidth, h = canvas.offsetHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("mousemove", onMouse);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
    };
  }, []);

  return <canvas ref={canvasRef} className="three-canvas" />;
}

/* ─────────────────────────────────────────────────────────────────────────────
   HERO VISUAL — PE entropy heatmap (what real malware analysis tools show)
   Cells reveal L→R coloured by entropy, then threat verdict overlays in.
───────────────────────────────────────────────────────────────────────────── */
type HeroPhase = "idle" | "scanning" | "verdict";


// Deterministic entropy map for a realistic malicious PE file
// Rows: DOS hdr | PE hdr | .text | .text | .rdata | .data | UPX0 | UPX1
const COLS = 22, ROWS = 8;
const SECTIONS = ["DOS Hdr","PE Hdr",".text",".text",".rdata",".data","UPX0","UPX1"];
const SECTION_COLORS = [
  /* DOS  */ "oklch(58% 0.16 240)",
  /* PE   */ "oklch(54% 0.14 230)",
  /* .txt */ "oklch(58% 0.16 145)",
  /* .txt */ "oklch(56% 0.15 145)",
  /* .rd  */ "oklch(66% 0.16 80)",
  /* .dat */ "oklch(70% 0.14 70)",
  /* UPX0 */ "oklch(56% 0.22 22)",
  /* UPX1 */ "oklch(50% 0.24 22)",
];
// entropy per row (0–1)
const ROW_ENTROPY = [0.12, 0.18, 0.46, 0.51, 0.62, 0.38, 0.89, 0.94];

function makeCell(row: number, col: number) {
  const base = ROW_ENTROPY[row];
  const jitter = (Math.sin(row * 31 + col * 17) * 0.5 + 0.5) * 0.14;
  return Math.min(1, Math.max(0, base + jitter - 0.07));
}

function entropyColor(e: number) {
  if (e < 0.25) return "oklch(58% 0.16 240)";   // cool blue – very low
  if (e < 0.45) return "oklch(58% 0.18 145)";   // green
  if (e < 0.60) return "oklch(68% 0.16 80)";    // yellow
  if (e < 0.78) return "oklch(64% 0.20 50)";    // orange
  return "oklch(52% 0.24 22)";                   // hot red
}

function HeroVisual() {
  const [phase, setPhase] = useState<HeroPhase>("idle");
  const [revealed, setRevealed] = useState(0); // how many cells are visible
  const totalCells = COLS * ROWS;

  useEffect(() => {
    let t: ReturnType<typeof setTimeout>;
    let iv: ReturnType<typeof setInterval>;

    const cycle = () => {
      setPhase("idle");
      setRevealed(0);

      t = setTimeout(() => {
        setPhase("scanning");
        let n = 0;
        iv = setInterval(() => {
          n = Math.min(n + 4, totalCells);
          setRevealed(n);
          if (n >= totalCells) {
            clearInterval(iv);
            t = setTimeout(() => {
              setPhase("verdict");
              t = setTimeout(cycle, 3800);
            }, 350);
          }
        }, 35);
      }, 700);
    };

    cycle();
    return () => { clearTimeout(t); clearInterval(iv); };
  }, []);

  const scanPct = phase === "idle" ? 0 : phase === "verdict" ? 100 : Math.round((revealed / totalCells) * 100);

  return (
    <div className="scene" style={{ width: 420, height: 480, position: "relative", flexShrink: 0 }}>
      {/* ambient glow – very subtle on light bg */}
      <div className="glow" style={{
        position: "absolute", inset: "12%", borderRadius: "50%",
        background: "radial-gradient(ellipse, oklch(52% 0.22 22 / 0.07) 0%, transparent 70%)",
        filter: "blur(48px)", zIndex: 0,
      }} />

      <div className="float-card" style={{ width: "100%", height: "100%", position: "relative" }}>
        <div style={{
          position: "absolute", inset: 0,
          background: C.card,
          border: `1px solid ${C.border}`,
          boxShadow: `0 1px 3px oklch(0% 0 0 / 0.04), 0 12px 40px oklch(0% 0 0 / 0.09)`,
          overflow: "hidden", zIndex: 1,
          display: "flex", flexDirection: "column",
        }}>

          {/* ── Chrome bar ── */}
          <div style={{
            padding: "10px 14px",
            borderBottom: `1px solid ${C.border}`,
            background: C.bg,
            display: "flex", alignItems: "center", gap: 8,
            flexShrink: 0,
          }}>
            <div style={{ display: "flex", gap: 5 }}>
              {["oklch(52% 0.22 22)","oklch(68% 0.18 80)","oklch(58% 0.16 145)"].map((bg,i) => (
                <div key={i} style={{ width: 8, height: 8, borderRadius: "50%", background: bg, opacity: 0.8 }} />
              ))}
            </div>
            <div style={{
              flex: 1, height: 20,
              border: `1px solid ${C.border}`,
              background: C.card,
              display: "flex", alignItems: "center", paddingLeft: 8, gap: 5,
            }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: C.n300 }} />
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7.5, color: C.muted }}>
                abyss / entropy-analysis
              </span>
            </div>
          </div>

          {/* ── File info row ── */}
          <div style={{
            padding: "10px 14px",
            borderBottom: `1px solid ${C.border}`,
            display: "flex", alignItems: "center", justifyContent: "space-between",
            flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <div style={{ width: 26, height: 26, background: "#FF2E55", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Terminal size={12} color="white" />
              </div>
              <div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: C.text, fontWeight: 600 }}>
                  sample.exe
                </div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7.5, color: C.muted, marginTop: 1 }}>
                  2.4 MB &nbsp;·&nbsp; PE32+ &nbsp;·&nbsp; 8 sections
                </div>
              </div>
            </div>
            {/* live scan % */}
            <div style={{ textAlign: "right" }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: C.accent, fontWeight: 700 }}>
                {scanPct}%
              </div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7, color: C.n300, marginTop: 1, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {phase === "idle" ? "ready" : phase === "verdict" ? "complete" : "scanning"}
              </div>
            </div>
          </div>

          {/* ── Heatmap area ── */}
          <div style={{ flex: 1, padding: "12px 14px 8px", display: "flex", flexDirection: "column", gap: 8, position: "relative", overflow: "hidden" }}>

            {/* Section labels + rows */}
            <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
              {Array.from({ length: ROWS }).map((_, row) => (
                <div key={row} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {/* section label */}
                  <div style={{
                    width: 40, flexShrink: 0,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 7, color: SECTION_COLORS[row],
                    textAlign: "right", letterSpacing: "0.04em",
                  }}>
                    {SECTIONS[row]}
                  </div>
                  {/* cells */}
                  <div style={{ display: "flex", gap: 2, flex: 1 }}>
                    {Array.from({ length: COLS }).map((_, col) => {
                      const idx = row * COLS + col;
                      const e = makeCell(row, col);
                      const visible = idx < revealed;
                      return (
                        <div key={col} style={{
                          flex: 1,
                          height: 18,
                          background: visible ? entropyColor(e) : C.n200,
                          opacity: visible ? (0.7 + e * 0.3) : 0.35,
                          transition: "background 0.15s, opacity 0.15s",
                        }} />
                      );
                    })}
                  </div>
                  {/* entropy bar */}
                  <div style={{ width: 28, flexShrink: 0 }}>
                    <div style={{ height: 3, background: C.n200, overflow: "hidden" }}>
                      <div style={{
                        height: "100%",
                        width: revealed > row * COLS ? `${Math.round(ROW_ENTROPY[row] * 100)}%` : "0%",
                        background: SECTION_COLORS[row],
                        transition: "width 0.4s ease",
                      }} />
                    </div>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 6.5, color: C.n400, marginTop: 2, textAlign: "right" }}>
                      {revealed > row * COLS ? (ROW_ENTROPY[row] * 8).toFixed(1) : "—"}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Legend */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, paddingTop: 4, borderTop: `1px solid ${C.border}` }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7, color: C.n300, textTransform: "uppercase", letterSpacing: "0.1em" }}>Entropy</span>
              {[
                { label: "Low", color: "oklch(58% 0.16 240)" },
                { label: "Med", color: "oklch(68% 0.16 80)" },
                { label: "High", color: "oklch(64% 0.20 50)" },
                { label: "Max", color: "oklch(52% 0.24 22)" },
              ].map(({ label, color }) => (
                <div key={label} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                  <div style={{ width: 8, height: 8, background: color, opacity: 0.85 }} />
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7, color: C.muted }}>{label}</span>
                </div>
              ))}
            </div>

            {/* ── Verdict overlay — slides up when complete ── */}
            <AnimatePresence>
              {phase === "verdict" && (
                <motion.div
                  key="verdict-overlay"
                  initial={{ y: "100%" }}
                  animate={{ y: 0 }}
                  exit={{ y: "100%" }}
                  transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
                  style={{
                    position: "absolute", left: 0, right: 0, bottom: 0,
                    background: C.card,
                    borderTop: `2px solid ${C.accent}`,
                    padding: "14px 14px 12px",
                    display: "flex", flexDirection: "column", gap: 10,
                  }}
                >
                  {/* Main verdict */}
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 36, height: 36, background: C.accent, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <AlertTriangle size={18} color="white" />
                    </div>
                    <div>
                      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 800, color: C.accent, textTransform: "uppercase", letterSpacing: "0.08em", lineHeight: 1 }}>
                        Threat Detected
                      </div>
                      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: C.muted, marginTop: 3 }}>
                        Ransomware · UPX-packed · High entropy sections
                      </div>
                    </div>
                    {/* Confidence pill */}
                    <div style={{ marginLeft: "auto", textAlign: "right" }}>
                      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 900, color: C.text, lineHeight: 1 }}>94%</div>
                      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7, color: C.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>confidence</div>
                    </div>
                  </div>

                  {/* 3 stat chips */}
                  <div style={{ display: "flex", gap: 6 }}>
                    {[
                      { label: "Entropy", value: "7.9 / 8.0", accent: true },
                      { label: "Packed Sections", value: "2", accent: true },
                      { label: "Risk", value: "CRITICAL", accent: true },
                    ].map(({ label, value, accent }) => (
                      <div key={label} style={{
                        flex: 1, padding: "7px 8px",
                        background: C.bg,
                        border: `1px solid ${C.border}`,
                      }}>
                        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7, color: C.n300, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
                        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, fontWeight: 700, color: C.accent, marginTop: 3 }}>{value}</div>
                      </div>
                    ))}
                  </div>

                  {/* CTA */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7.5, color: C.n300 }}>forensic_report.json ready</span>
                    <div style={{
                      padding: "6px 16px",
                      background: C.text,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 8, fontWeight: 700, color: "white",
                      letterSpacing: "0.08em", textTransform: "uppercase",
                    }}>
                      View Report
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

          </div>
        </div>
      </div>
    </div>
  );
}








/* -----------------------------------------------------------------------
   MARQUEE STRIP
----------------------------------------------------------------------- */
const MARQUEE_ITEMS = [
  "Static Analysis", "PE Header Inspection", "Section Entropy",
  "XGBoost / RF / LightGBM", "Frida API Hooks", "Zero-Day Detection",
  "FakeNet Sinkhole", "Forensic Report", "98.4% Accuracy",
  "Static Analysis", "PE Header Inspection", "Section Entropy",
  "XGBoost / RF / LightGBM", "Frida API Hooks", "Zero-Day Detection",
  "FakeNet Sinkhole", "Forensic Report", "98.4% Accuracy",
];

function Marquee() {
  return (
    <div style={{
      borderTop: `1px solid ${C.border}`,
      borderBottom: `1px solid ${C.border}`,
      background: C.card,
      overflow: "hidden",
      padding: "13px 0",
    }}>
      <div className="marquee-track">
        {MARQUEE_ITEMS.map((t, i) => (
          <span key={i} style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "var(--step--2)",
            color: i % 9 === 8 ? C.accent : C.muted,
            fontWeight: i % 9 === 8 ? 700 : 400,
            padding: "0 40px",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
          }}>
            {t}{i % 9 !== 8 && <span style={{ color: C.n300, marginLeft: 40 }}>|</span>}
          </span>
        ))}
      </div>
    </div>
  );
}


/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   MOVEABLE & FLOATING CARDS (Interactive framer-motion drag & floating physics)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
function MoveableReportCard({ n, label, desc, index }: { n: string; label: string; desc: string; index: number }) {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <Reveal delay={index * 0.06}>
      <motion.div
        drag
        dragConstraints={{ left: -180, right: 180, top: -120, bottom: 120 }}
        dragElastic={0.25}
        dragTransition={{ bounceStiffness: 300, bounceDamping: 20 }}
        onDragStart={() => setIsDragging(true)}
        onDragEnd={() => setIsDragging(false)}
        animate={isDragging ? undefined : {
          y: [0, index % 2 === 0 ? -10 : 10, 0, index % 2 === 0 ? 10 : -10, 0],
          rotate: [0, index % 2 === 0 ? 1.5 : -1.5, 0, index % 2 === 0 ? -1.5 : 1.5, 0],
        }}
        transition={isDragging ? undefined : {
          duration: 4.5 + (index % 3) * 0.8,
          repeat: Infinity,
          ease: "easeInOut",
          delay: index * 0.2,
        }}
        whileHover={{
          scale: 1.05,
          zIndex: 40,
          borderColor: "rgba(255, 46, 85, 0.5)",
          boxShadow: "0 25px 50px rgba(0,0,0,0.7), 0 0 35px rgba(255,46,85,0.25)",
        }}
        whileTap={{ scale: 0.98 }}
        style={{
          padding: "clamp(1.5rem, 3vw, 2.5rem)",
          background: "rgba(13, 13, 18, 0.88)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          borderRadius: 18,
          height: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 14,
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: "none",
          position: "relative",
          boxShadow: "0 12px 35px rgba(0,0,0,0.5)",
          touchAction: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", color: "#FF2E55", fontWeight: 800 }}>
            {n}
          </span>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "9px",
              color: isDragging ? "#FF2E55" : "rgba(255,255,255,0.5)",
              background: isDragging ? "rgba(255,46,85,0.2)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${isDragging ? "rgba(255,46,85,0.5)" : "rgba(255,255,255,0.12)"}`,
              padding: "3px 10px",
              borderRadius: 6,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              fontWeight: 700,
            }}
          >
            {isDragging ? "DRAGGING..." : "MOVEABLE ✥"}
          </span>
        </div>

        <span style={{ fontSize: "var(--step-1)", fontWeight: 800, color: "#F4F4F6", letterSpacing: "-0.02em" }}>
          {label}
        </span>
        <span style={{ fontSize: "var(--step-0)", color: "#A1A1AA", lineHeight: 1.7 }}>
          {desc}
        </span>
      </motion.div>
    </Reveal>
  );
}

function MoveableLayerCard({ card, index }: { card: { n: string; title: string; tag: string; tagColor: string; body: string; detail: string[] }; index: number }) {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <Reveal delay={index * 0.08}>
      <motion.div
        drag
        dragConstraints={{ left: -160, right: 160, top: -100, bottom: 100 }}
        dragElastic={0.25}
        dragTransition={{ bounceStiffness: 300, bounceDamping: 20 }}
        onDragStart={() => setIsDragging(true)}
        onDragEnd={() => setIsDragging(false)}
        animate={isDragging ? undefined : {
          y: [0, index % 2 === 0 ? -12 : 12, 0, index % 2 === 0 ? 12 : -12, 0],
          rotate: [0, index % 2 === 0 ? 1.5 : -1.5, 0, index % 2 === 0 ? -1.5 : 1.5, 0],
        }}
        transition={isDragging ? undefined : {
          duration: 5 + index * 0.7,
          repeat: Infinity,
          ease: "easeInOut",
          delay: index * 0.3,
        }}
        whileHover={{
          scale: 1.04,
          zIndex: 40,
          borderColor: "rgba(255,46,85,0.4)",
          boxShadow: "0 25px 50px rgba(0,0,0,0.7), 0 0 35px rgba(255,46,85,0.2)",
        }}
        whileTap={{ scale: 0.98 }}
        style={{
          padding: "clamp(2rem, 4vw, 3rem)",
          background: "rgba(13, 13, 18, 0.88)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          borderRadius: 20,
          display: "flex",
          flexDirection: "column",
          gap: 24,
          height: "100%",
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: "none",
          position: "relative",
          boxShadow: "0 12px 35px rgba(0,0,0,0.5)",
          touchAction: "none",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "var(--step-4)", fontWeight: 900, color: "rgba(255,255,255,0.15)", lineHeight: 1 }}>
            {card.n}
          </span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
              color: card.tagColor, border: `1px solid ${card.tagColor}`,
              padding: "4px 12px", borderRadius: 6, textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700,
            }}>{card.tag}</span>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
              color: isDragging ? "#FF2E55" : "rgba(255,255,255,0.4)",
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
              padding: "4px 10px", borderRadius: 6, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700,
            }}>MOVEABLE ✥</span>
          </div>
        </div>
        <div>
          <h3 style={{ fontSize: "var(--step-2)", fontWeight: 800, letterSpacing: "-0.025em", marginBottom: 12, lineHeight: 1.1, color: "#F4F4F6" }}>{card.title}</h3>
          <p style={{ fontSize: "var(--step-0)", color: "#A1A1AA", lineHeight: 1.75 }}>{card.body}</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: "auto", paddingTop: 20, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
          {card.detail.map(d => (
            <div key={d} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "var(--step--1)", color: "#A1A1AA", fontFamily: "'JetBrains Mono', monospace" }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#FF2E55", flexShrink: 0 }} />
              {d}
            </div>
          ))}
        </div>
      </motion.div>
    </Reveal>
  );
}



/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   GLOBAL BACKGROUND ANIMATION SYSTEM (3D WebGL Matrix + Scanlines + Radial Glows + Floating Telemetry across ALL sections)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
function GlobalBackgroundAnimation() {
  return (
    <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
      {/* 3D WebGL Node Canvas */}
      {/* Global 3D scene renders via GlobalBackgroundAnimation */}

      {/* Vertical Cyber Scanline Sweep */}
      <div className="cyber-scanline" />

      {/* Multi-layered Pulsing Radial Glow Spotlights */}
      <div style={{
        position: "absolute", top: "5%", left: "15%", width: "55vw", height: "55vh",
        background: "radial-gradient(circle, rgba(255, 46, 85, 0.08) 0%, transparent 70%)",
        animation: "pulseGlow 10s ease-in-out infinite", filter: "blur(60px)"
      }} />
      <div style={{
        position: "absolute", top: "40%", right: "10%", width: "50vw", height: "50vh",
        background: "radial-gradient(circle, rgba(0, 210, 255, 0.07) 0%, transparent 70%)",
        animation: "pulseGlow 12s ease-in-out infinite 2s", filter: "blur(70px)"
      }} />
      <div style={{
        position: "absolute", bottom: "15%", left: "25%", width: "60vw", height: "60vh",
        background: "radial-gradient(circle, rgba(0, 229, 153, 0.06) 0%, transparent 70%)",
        animation: "pulseGlow 14s ease-in-out infinite 4s", filter: "blur(70px)"
      }} />

      {/* Floating Telemetry Code Particles across all sections */}
      <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
        {[
          "0x7F90_PE_HEADER", "ENTROPY_CRITICAL:7.92", "HOOK_CREATE_REMOTE_THREAD",
          "SINKHOLE_ACTIVE_NET", "01001101_INSTRUMENTED", "ZERO_DAY_ANOMALY_99%",
          "FRIDA_HOOK_SUCCESS", "AES_DECEPTION_ACTIVE", "VIRTUAL_ALLOC_EX_INTERCEPT"
        ].map((text, idx) => (
          <span
            key={idx}
            style={{
              position: "absolute",
              left: `${(idx * 11 + 4) % 88}%`,
              top: `${(idx * 13 + 8) % 88}%`,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "10px",
              fontWeight: 700,
              color: idx % 3 === 0 ? "rgba(255,46,85,0.25)" : (idx % 3 === 1 ? "rgba(0,210,255,0.25)" : "rgba(0,229,153,0.25)"),
              animation: `floatParticle ${10 + (idx % 4) * 3}s linear infinite`,
              animationDelay: `${idx * 1.2}s`,
              pointerEvents: "none",
              userSelect: "none"
            }}
          >
            {text}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   INFINITE MOVING MARQUEE TRACK (Cards moving continuously left to right + interactively moveable/draggable)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
function MovingMarqueeCards() {
  const [isPaused, setIsPaused] = useState(false);
  const [direction, setDirection] = useState<"left-to-right" | "right-to-left">("left-to-right");

  const cardsData = [
    { n: "01", label: "Executive Verdict",  desc: "Threat type, confidence score, risk level, and zero-day flag - one summary panel." },
    { n: "02", label: "SHAP Importance",    desc: "Top-10 features driving the ML verdict, shown as a ranked animated bar chart." },
    { n: "03", label: "Attack Timeline",    desc: "Every API call, file write, and socket in chronological order with severity tags." },
    { n: "04", label: "Exfil Endpoints",    desc: "Contacted IPs and domains, blocked or sinkholed, with country hints and protocol details." },
    { n: "05", label: "Mock Data Served",   desc: "Exactly what the payload received - honey passwords, fake registry keys, dummy files." },
    { n: "06", label: "PDF Export",         desc: "One-click forensic PDF for your SOC, legal team, or incident response report." },
  ];

  const duplicatedCards = [...cardsData, ...cardsData, ...cardsData];

  const xAnimation = direction === "left-to-right" 
    ? ["-50%", "0%"]
    : ["0%", "-50%"];

  return (
    <div style={{ position: "relative", width: "100%", overflow: "hidden", paddingTop: 10, paddingBottom: 20 }}>
      {/* Interactive Controls Bar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 20, flexWrap: "wrap", gap: 12
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: isPaused ? "#FFB000" : "#00E599",
            boxShadow: isPaused ? "0 0 12px #FFB000" : "0 0 12px #00E599",
          }} />
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#A1A1AA", fontWeight: 700, letterSpacing: "0.08em" }}>
            CONTINUOUS MOTION · {direction === "left-to-right" ? "SLIDING LEFT → RIGHT" : "SLIDING RIGHT → LEFT"}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={() => setDirection(d => d === "left-to-right" ? "right-to-left" : "left-to-right")}
            style={{
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
              color: "#F4F4F6", fontSize: "11px", fontFamily: "'JetBrains Mono', monospace",
              padding: "6px 14px", borderRadius: 8, cursor: "pointer", fontWeight: 700,
              transition: "all 0.2s ease"
            }}
          >
            {direction === "left-to-right" ? "◀ REVERSE DIRECTION" : "▶ SLIDE LEFT TO RIGHT"}
          </button>
          <button
            type="button"
            onClick={() => setIsPaused(p => !p)}
            style={{
              background: isPaused ? "rgba(255,46,85,0.2)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${isPaused ? "#FF2E55" : "rgba(255,255,255,0.12)"}`,
              color: isPaused ? "#FF2E55" : "#F4F4F6",
              fontSize: "11px", fontFamily: "'JetBrains Mono', monospace",
              padding: "6px 14px", borderRadius: 8, cursor: "pointer", fontWeight: 700,
              transition: "all 0.2s ease"
            }}
          >
            {isPaused ? "▶ RESUME MOTION" : "⏸ PAUSE TRACK"}
          </button>
        </div>
      </div>

      {/* Infinite Horizontal Motion Track */}
      <div style={{
        overflow: "hidden", width: "100%", position: "relative",
        maskImage: "linear-gradient(to right, transparent, black 3%, black 97%, transparent)",
        WebkitMaskImage: "linear-gradient(to right, transparent, black 3%, black 97%, transparent)"
      }}>
        <motion.div
          animate={isPaused ? undefined : { x: xAnimation }}
          transition={isPaused ? undefined : {
            x: {
              repeat: Infinity,
              repeatType: "loop",
              duration: 32,
              ease: "linear",
            }
          }}
          style={{ display: "flex", gap: 24, width: "max-content", padding: "12px 0" }}
        >
          {duplicatedCards.map((item, idx) => (
            <div key={idx} style={{ width: 380, flexShrink: 0 }}>
              <MoveableReportCard n={item.n} label={item.label} desc={item.desc} index={idx} />
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   REVEAL WRAPPER  (motion-framer: useInView stagger pattern)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
function Reveal({ children, delay = 0, y = 32, className = "" }: {
  children: React.ReactNode; delay?: number; y?: number; className?: string;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  return (
    <motion.div ref={ref} className={className}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: "var(--step--2)",
      color: C.muted,
      textTransform: "uppercase",
      letterSpacing: "0.14em",
    }}>
      {children}
    </span>
  );
}

/* ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   MAIN PAGE
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- */
export default function UploadPage() {
  const router   = useRouter();
  const uploadRef = useRef<HTMLDivElement>(null);
  const heroRef   = useRef<HTMLElement>(null);

  // Scroll-linked header blur
  const { scrollY } = useScroll();
  const headerBg = useTransform(scrollY, [0, 60], ["rgba(7,7,9,0)", "rgba(7,7,9,0.88)"]);
  const headerBorder = useTransform(scrollY, [0, 60], ["rgba(255,255,255,0)", "rgba(255,255,255,0.08)"]);

  // Parallax on hero visual
  const heroVisualY = useTransform(scrollY, [0, 500], [0, -60]);
  const springY     = useSpring(heroVisualY, { stiffness: 60, damping: 20 });

  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [stage, setStage] = useState<TaskStatus>("pending");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [telemetryLogs, setTelemetryLogs] = useState<TelemetryLog[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    let active = true;
    const iv = setInterval(async () => {
      try {
        const res = await getStatus(taskId);
        if (!active) return;
        setStage(res.status); setProgress(res.progress); setStatusMessage(res.message);
        if (res.telemetry_logs) setTelemetryLogs(res.telemetry_logs);
        if (res.status === "complete" || res.progress === 100) {
          clearInterval(iv);
          setTimeout(() => router.push(`/report?task=${taskId}`), 1200);
        } else if (res.status === "failed") {
          clearInterval(iv); setError(res.message || "Pipeline failed");
        }
      } catch (e) { setError(e instanceof Error ? e.message : "Status check failed"); }
    }, 2000);
    return () => { active = false; clearInterval(iv); };
  }, [taskId, router]);

  const handleFile = async (f: File) => {
    setFile(f); setError(null); setProgress(0); setStage("pending"); setStatusMessage("Uploading...");
    try { const r = await uploadFile(f); setTaskId(r.task_id); }
    catch (e) { setError(e instanceof Error ? e.message : "Upload failed"); setFile(null); }
  };

  const scrollToUpload = () => uploadRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: CSS }} />

      {/* ------ HEADER --------------------------------------------------------------------------------------------------------------------------------------------------------- */}
      <motion.header style={{
        background: headerBg,
        borderBottom: `1px solid`,
        borderColor: headerBorder as any,
        backdropFilter: "blur(20px)",
        position: "fixed", top: 0, left: 0, right: 0,
        zIndex: 1000,
        padding: "0 clamp(1.5rem, 5vw, 4rem)",
        height: 58,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          style={{ display: "flex", alignItems: "center", gap: 10 }}
        >
          <div style={{ width: 30, height: 30, background: "#FF2E55", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Shield size={14} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 900, fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase", lineHeight: 1, color: "#F4F4F6" }}>ABYSS</div>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 7, color: "#A1A1AA", letterSpacing: "0.08em", textTransform: "uppercase", marginTop: 1 }}>Threat Intelligence</div>
          </div>
        </motion.div>

        <motion.nav
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          style={{ display: "flex", gap: "clamp(1.5rem, 3vw, 2.5rem)", alignItems: "center" }}
        >
          {[["How It Works", "#how-it-works"], ["ML Stack", "#architecture"], ["Report", "#report"]].map(([label, href]) => (
            <a key={label} href={href} className="hover-line"
              style={{ fontSize: "var(--step--1)", color: "#A1A1AA", textDecoration: "none", fontWeight: 500 }}>
              {label}
            </a>
          ))}
          <motion.button
            onClick={scrollToUpload}
            whileHover={{ scale: 1.04, y: -1 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: "spring", stiffness: 400, damping: 18 }}
            style={{
              padding: "8px 20px",
              background: C.accent, color: "white", border: "none",
              fontFamily: "'Inter', sans-serif", fontWeight: 700,
              fontSize: "var(--step--1)", letterSpacing: "0.05em",
              textTransform: "uppercase", cursor: "pointer",
            }}
          >
            Analyze
          </motion.button>
        </motion.nav>
      </motion.header>

      <main style={{ paddingTop: 58 }}>

        {/* ------ HERO — dark 3D section ----------------------------------------------------------------------------------------------- */}
        <div style={{ position: "relative", background: "#070709", overflow: "hidden" }}>
          {/* Three.js canvas fills the entire hero area */}
          {/* Global 3D scene renders via GlobalBackgroundAnimation */}
          {/* Edge vignette so nodes fade out toward borders */}
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none", zIndex: 0,
            background: "radial-gradient(ellipse 90% 90% at 50% 50%, transparent 20%, rgba(7,7,9,0.85) 100%)",
          }} />
          {/* Bottom fade into the next section */}
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0, height: "180px",
            background: "linear-gradient(to bottom, transparent, #070709)",
            pointerEvents: "none", zIndex: 0,
          }} />

        <section ref={heroRef} style={{
          minHeight: "96vh",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "clamp(2rem, 4vw, 5rem)",
          alignItems: "center",
          padding: "clamp(4rem, 9vw, 8rem) clamp(1.5rem, 5vw, 4rem) clamp(5rem, 8vw, 7rem)",
          maxWidth: 1280, margin: "0 auto",
          position: "relative", zIndex: 1,
        }}>

          {/* Left column */}
          <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: "clamp(1.25rem, 2.5vw, 2rem)" }}>


            {/* Live indicator */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              style={{ display: "flex", alignItems: "center", gap: 8, width: "fit-content" }}
            >
              <div style={{ position: "relative", width: 8, height: 8 }}>
                <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: C.accent, animation: "glowPulse 1.5s ease-in-out infinite" }} />
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.accent }} />
              </div>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "var(--step--2)", color: "#00E599", textTransform: "uppercase", letterSpacing: "0.14em" }}>System online | Zero-Data Retention & Continuous Model Learning Active</span>
            </motion.div>

            {/* Headline */}
            <div style={{ overflow: "hidden" }}>
              <motion.h1
                initial={{ y: "110%" }}
                animate={{ y: 0 }}
                transition={{ duration: 0.75, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
                style={{
                  fontSize: "var(--step-5)",
                  fontWeight: 900,
                  lineHeight: 0.96,
                  letterSpacing: "-0.04em",
                  color: "#F4F4F6",
                }}
              >
                Every<br />
                file.
              </motion.h1>
            </div>
            <div style={{ overflow: "hidden" }}>
              <motion.div
                initial={{ y: "110%" }}
                animate={{ y: 0 }}
                transition={{ duration: 0.75, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
                style={{
                  fontSize: "var(--step-5)",
                  fontWeight: 300,
                  fontStyle: "italic",
                  lineHeight: 0.96,
                  letterSpacing: "-0.04em",
                  color: "#FF2E55",
                }}
              >
                Exposed.
              </motion.div>
            </div>

            {/* Body */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
              style={{
                fontSize: "var(--step-1)",
                color: "#A1A1AA",
                lineHeight: 1.75,
                maxWidth: 440,
                marginTop: "0.5rem",
              }}
            >
              ABYSS detonates suspicious files in isolated hypervisor environments,
              intercepts API calls through Frida instrumentation, and runs a
              stacked ML ensemble to classify threats — in under two seconds.
            </motion.p>

            {/* CTA row */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}
            >
              <motion.button
                onClick={scrollToUpload}
                whileHover={{ scale: 1.04, y: -3 }}
                whileTap={{ scale: 0.96 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
                style={{
                  padding: "16px 32px",
                  background: C.accent, color: "white", border: "none",
                  fontFamily: "'Inter', sans-serif", fontWeight: 800,
                  fontSize: "var(--step-0)", letterSpacing: "0.03em",
                  textTransform: "uppercase", cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 10,
                  boxShadow: "0 8px 24px rgba(20,20,19,0.12)",
                }}
              >
                Analyze a file <ArrowUpRight size={16} />
              </motion.button>
              <motion.a
                href="#how-it-works"
                whileHover={{ x: 4 }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
                style={{
                  fontSize: "var(--step-0)", color: "#A1A1AA",
                  display: "flex", alignItems: "center", gap: 6,
                  textDecoration: "none", fontWeight: 500,
                }}
              >
                See how it works <ArrowRight size={14} />
              </motion.a>
            </motion.div>

            {/* Metrics strip */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              style={{
                display: "flex", gap: "2rem",
                paddingTop: "1.75rem",
                borderTop: "1px solid oklch(100% 0 0 / 0.1)",
                marginTop: "0.5rem",
              }}
            >
              {[
                { v: "98.4%", l: "Detection accuracy" },
                { v: "3",     l: "Defence layers" },
                { v: "<2s",   l: "Time to verdict" },
              ].map(({ v, l }) => (
                <div key={l}>
                  <div style={{ fontSize: "var(--step-3)", fontWeight: 900, letterSpacing: "-0.03em", lineHeight: 1, color: "#F4F4F6" }}>{v}</div>
                  <div style={{ fontSize: "var(--step--1)", color: "#A1A1AA", marginTop: 4 }}>{l}</div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right: 3D visual with parallax */}
          <motion.div
            style={{ y: springY, display: "flex", justifyContent: "center", position: "relative", zIndex: 1 }}
            initial={{ opacity: 0, x: 48 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.85, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
          >
            <HeroVisual />
          </motion.div>
        </section>
        </div>{/* /hero dark */}

        {/* ------ MARQUEE ------------------------------------------------------------------------------------------------------------------------------------------------------ */}
        <Marquee />

        {/* ------ UPLOAD --------------------------------------------------------------------------------------------------------------------------------------------------------- */}
        <section id="upload" ref={uploadRef} style={{
          padding: "clamp(5rem, 9vw, 8rem) clamp(1.5rem, 5vw, 4rem)",
          background: C.card,
          borderBottom: `1px solid ${C.border}`,
        }}>
          <div style={{ maxWidth: 640, margin: "0 auto" }}>
            <Reveal>
              <Tag>01 - Upload target</Tag>
              <h2 style={{ fontSize: "var(--step-4)", fontWeight: 900, letterSpacing: "-0.035em", lineHeight: 1.0, marginTop: 14, marginBottom: 16 }}>
                Drop your file.
              </h2>
              <p style={{ fontSize: "var(--step-0)", color: C.muted, lineHeight: 1.75, marginBottom: 36 }}>
                Supports EXE, DLL, ZIP, PDF, DOCX — up to 200 MB.
                The full analysis pipeline runs automatically.
              </p>
            </Reveal>

            <AnimatePresence mode="wait">
              {!file ? (
                <motion.div key="drop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div style={{ border: `1px solid ${C.border}`, background: C.bg }}>
                    <FileUpload onFileSelected={handleFile} />
                  </div>
                </motion.div>
              ) : (
                  <motion.div key="progress" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    {/* File info bar */}
                    <div style={{
                      padding: "14px 18px", border: `1px solid ${C.border}`, background: C.bg,
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
                        <div style={{ width: 36, height: 36, background: "#FF2E55", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          <Terminal size={15} color="white" />
                        </div>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 600, fontSize: "var(--step-0)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 280 }}>{file.name}</div>
                          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "var(--step--2)", color: C.muted, marginTop: 2 }}>{formatFileSize(file.size)}</div>
                        </div>
                      </div>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted, border: `1px solid ${C.border}`, padding: "3px 10px" }}>{stage}</span>
                    </div>

                    {error && (
                      <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                        style={{ padding: "14px 18px", border: `1px solid ${C.accent}`, background: C.a100, display: "flex", alignItems: "center", gap: 12, fontSize: "var(--step--1)", color: C.accent }}>
                        <AlertTriangle size={15} style={{ flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>Error</div>
                          <div style={{ opacity: 0.8 }}>{error}</div>
                        </div>
                        <button onClick={() => setFile(null)} style={{ background: "none", border: "none", cursor: "pointer", fontFamily: "'JetBrains Mono', monospace", fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: C.muted, textDecoration: "underline" }}>Reset</button>
                      </motion.div>
                    )}

                    {!error && (
                      <div style={{ padding: "20px 22px", border: `1px solid ${C.border}`, background: C.bg }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                          <Tag>Pipeline</Tag>
                          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 700 }}>{progress}%</span>
                        </div>
                        <ProgressPipeline status={stage} progress={progress} message={statusMessage} telemetryLogs={telemetryLogs} />
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
          </div>
        </section>

        {/* ------ HOW IT WORKS --------------------------------------------------------------------------------------------------------------------------------------- */}
        <section id="how-it-works" style={{
          padding: "clamp(5rem, 10vw, 9rem) clamp(1.5rem, 5vw, 4rem)",
          maxWidth: 1280, margin: "0 auto",
        }}>
          <Reveal>
            <Tag>02 - Protection layers</Tag>
            <h2 style={{ fontSize: "var(--step-4)", fontWeight: 900, letterSpacing: "-0.04em", lineHeight: 1.0, marginTop: 14, marginBottom: "clamp(3rem, 6vw, 5rem)", maxWidth: 500 }}>
              Three layers.<br />Zero escape.
            </h2>
          </Reveal>

          {/* Full-bleed grid — 3 cols separated by 1px borders */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, background: C.border }}>
            {[
              { n: "01", title: "Static Heuristics", tag: "< 80 ms", tagColor: C.muted,
                body: "PE header inspection, section entropy calculation, import hash fingerprinting, packer and cryptor detection — before a single instruction executes.",
                detail: ["Entropy threshold: 7.0", "Import hash matching", "TLS callback detection", "Overlay analysis"] },
              { n: "02", title: "Sandbox Profiling", tag: "Isolated VM", tagColor: C.muted,
                body: "Executes the binary inside an instrumented hypervisor. Full process tree tracing, registry mutation logs, filesystem write interception, and outbound socket mapping.",
                detail: ["Process tree capture", "Registry key tracing", "Socket interception", "File write logging"] },
              { n: "03", title: "Active Deception", tag: "Frida + FakeNet", tagColor: C.accent,
                body: "When the ML ensemble flags a threat, Frida API hooks serve the payload realistic honey-data. All outbound connections are sinkholed. The threat runs, learns nothing, and is fully mapped.",
                detail: ["API call interception", "Honey-data injection", "Network sinkholing", "Full call log export"] },
            ].map((card, i) => (
              <Reveal key={card.n} delay={i * 0.08}>
                <motion.div
                  whileHover={{ background: C.bg }}
                  transition={{ duration: 0.2 }}
                  style={{
                    padding: "clamp(2rem, 4vw, 3rem)",
                    background: C.card,
                    display: "flex", flexDirection: "column", gap: 24, height: "100%",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "var(--step-4)", fontWeight: 900, color: C.borderDim, lineHeight: 1 }}>{card.n}</span>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: 8,
                      color: card.tagColor, border: `1px solid ${card.tagColor}`,
                      padding: "3px 10px", textTransform: "uppercase", letterSpacing: "0.1em",
                    }}>{card.tag}</span>
                  </div>
                  <div>
                    <h3 style={{ fontSize: "var(--step-2)", fontWeight: 800, letterSpacing: "-0.025em", marginBottom: 12, lineHeight: 1.1 }}>{card.title}</h3>
                    <p style={{ fontSize: "var(--step-0)", color: C.muted, lineHeight: 1.75 }}>{card.body}</p>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: "auto", paddingTop: 20, borderTop: `1px solid ${C.border}` }}>
                    {card.detail.map(d => (
                      <div key={d} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "var(--step--1)", color: C.muted }}>
                        <div style={{ width: 4, height: 4, background: C.n300, flexShrink: 0 }} />
                        {d}
                      </div>
                    ))}
                  </div>
                </motion.div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ------ DARK ML SECTION ------------------------------------------------------------------------------------------------------------------------------ */}
        <section id="architecture" style={{
          background: C.dark, color: "white",
          padding: "clamp(5rem, 10vw, 9rem) clamp(1.5rem, 5vw, 4rem)",
          borderTop: `1px solid ${C.darkBorder}`,
        }}>
          <div style={{ maxWidth: 1280, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "clamp(3rem, 7vw, 7rem)", alignItems: "start" }}>

            {/* Left copy */}
            <Reveal>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "var(--step--2)", color: C.darkMuted, textTransform: "uppercase", letterSpacing: "0.14em" }}>
                03 - ML stack
              </span>
              <h2 style={{ fontSize: "var(--step-4)", fontWeight: 900, letterSpacing: "-0.04em", lineHeight: 1.0, marginTop: 14 }}>
                An ensemble<br />
                <span style={{ color: C.accentMid }}>that doesn't miss.</span>
              </h2>
              <p style={{ fontSize: "var(--step-0)", color: C.darkMuted, lineHeight: 1.75, marginTop: 20, maxWidth: 400 }}>
                Three base classifiers vote. A meta-learner fuses probabilities.
                A PyTorch autoencoder flags zero-days by reconstruction loss.
                Static heuristics hard-override the ensemble if risk is 50% or higher.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: C.darkBorder, marginTop: 40 }}>
                {[
                  { l: "XGBoost",      d: "Gradient boosted trees" },
                  { l: "Random Forest",d: "Bagged decision ensemble" },
                  { l: "LightGBM",    d: "Leaf-wise boosting" },
                  { l: "Autoencoder", d: "PyTorch zero-day detection" },
                ].map(({ l, d }) => (
                  <div key={l} style={{
                    padding: "16px 18px",
                    background: C.dark,
                    display: "flex", flexDirection: "column", gap: 5,
                  }}>
                    <span style={{ fontWeight: 700, fontSize: "var(--step-0)" }}>{l}</span>
                    <span style={{ fontSize: "var(--step--1)", color: C.darkMuted }}>{d}</span>
                  </div>
                ))}
              </div>
            </Reveal>

            {/* Code block */}
            <Reveal delay={0.15}>
              <div style={{
                background: "oklch(11% 0.012 285)",
                border: `1px solid ${C.darkBorder}`,
                padding: "0",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "clamp(8px, 1.1vw, 11px)",
                lineHeight: 1.8,
                overflow: "hidden",
              }}>
                {/* Code header bar */}
                <div style={{
                  padding: "12px 18px",
                  borderBottom: `1px solid ${C.darkBorder}`,
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  background: "oklch(13% 0.012 285)",
                }}>
                  <div style={{ display: "flex", gap: 7 }}>
                    {["oklch(52% 0.22 22)", "oklch(72% 0.18 80)", "oklch(62% 0.18 145)"].map(c => (
                      <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: 0.9 }} />
                    ))}
                  </div>
                  <span style={{ color: C.darkMuted, fontSize: 9 }}>classifier_ensemble.py</span>
                </div>
                {/* Code body */}
                <pre style={{ padding: "22px 22px 28px", color: "oklch(78% 0.008 285)", whiteSpace: "pre-wrap", margin: 0 }}>{
`def ensemble_predict(static_vec, behavior_vec):
    # Base classifier probabilities
    probs = {
        "xgb": xgb.predict_proba(static_vec),
        "rf":  rf.predict_proba(static_vec),
        "lgb": lgb.predict_proba(static_vec),
    }

    # Meta-learner fusion
    meta  = np.column_stack(list(probs.values()))
    score = meta_learner.predict(meta)[0]

    # Zero-day: autoencoder reconstruction loss
    loss     = autoencoder.loss(static_vec)
    zero_day = loss > ZERO_DAY_THRESHOLD

    # Heuristic hard-override (score >= 50)
    if zero_day or static_heuristics.score >= 50:
        return "malicious", max(score, 0.98), zero_day

    threat = classify_type(behavior_vec, score)
    return threat, score, False`}
                </pre>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ------ REPORT SECTION --------------------------------------------------------------------------------------------------------------------------------- */}
        <section id="report" style={{
          padding: "clamp(5rem, 10vw, 9rem) clamp(1.5rem, 5vw, 4rem)",
          borderBottom: `1px solid ${C.border}`,
        }}>
          <div style={{ maxWidth: 1280, margin: "0 auto" }}>
            <Reveal>
              <Tag>04 - Forensic report</Tag>
              <h2 style={{ fontSize: "var(--step-4)", fontWeight: 900, letterSpacing: "-0.04em", lineHeight: 1.0, marginTop: 14, marginBottom: "clamp(3rem, 6vw, 5rem)", maxWidth: 520 }}>
                A verdict.<br />Not a guess.
              </h2>
            </Reveal>

            {/* Infinite Horizontal Moving Marquee Track (Left to Right + Draggable) */}
            <MovingMarqueeCards />
          </div>
        </section>

        {/* ------ BOTTOM CTA --------------------------------------------------------------------------------------------------------------------------------------------- */}
        <section style={{
          padding: "clamp(6rem, 12vw, 10rem) clamp(1.5rem, 5vw, 4rem)",
          display: "flex", flexDirection: "column", alignItems: "center",
          textAlign: "center", gap: "clamp(1.5rem, 3vw, 2.5rem)",
          position: "relative", overflow: "hidden",
        }}>
          {/* Ambient glow */}
          <div style={{
            position: "absolute", top: "30%", left: "50%",
            transform: "translateX(-50%)",
            width: "60%", height: "50%",
            background: `radial-gradient(ellipse, ${C.a100} 0%, transparent 70%)`,
            pointerEvents: "none",
          }} />

          <Reveal>
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "var(--step--2)", color: C.muted, textTransform: "uppercase", letterSpacing: "0.14em", marginBottom: 8 }}>
              Ready?
            </p>
            <h2 style={{ fontSize: "var(--step-5)", fontWeight: 900, letterSpacing: "-0.05em", lineHeight: 0.95 }}>
              Know what's<br />
              <em style={{ color: C.accent, fontStyle: "italic", fontWeight: 300 }}>inside.</em>
            </h2>
            <p style={{ fontSize: "var(--step-1)", color: C.muted, marginTop: 24, lineHeight: 1.7 }}>
              Drop a file. Full forensic verdict in under two seconds.
            </p>
            <motion.button
              onClick={scrollToUpload}
              whileHover={{ scale: 1.05, y: -4 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 360, damping: 16 }}
              style={{
                marginTop: 36,
                padding: "20px 48px",
                background: "linear-gradient(135deg, #FF2E55, #C0392B)",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "12px",
                boxShadow: "0 0 35px rgba(255, 46, 85, 0.4)",
                fontFamily: "'Inter', sans-serif",
                fontWeight: 800,
                fontSize: "var(--step-1)",
                letterSpacing: "0.02em",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              Analyze now <ArrowUpRight size={20} />
            </motion.button>
          </Reveal>
        </section>

        {/* ------ FOOTER --------------------------------------------------------------------------------------------------------------------------------------------------------- */}
        <footer style={{
          borderTop: `1px solid ${C.border}`,
          padding: "1.75rem clamp(1.5rem, 5vw, 4rem)",
          display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 22, height: 22, background: "#FF2E55", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Shield size={11} color="white" />
            </div>
            <span style={{ fontWeight: 900, fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase" }}>ABYSS</span>
          </div>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: C.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            v2.1.0 | local-only | all data stays on device
          </span>
        </footer>
      </main>
    </>
  );
}
