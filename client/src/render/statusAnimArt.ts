// 狀態動作與地表動態的小貼圖（Phase 6N-9）：固定一小組（狀態 14 張、地表 3 張），全場共用，
// 動畫時只換位置、縮放、透明度、旋轉與染色，不會再產生新的貼圖。沒有 DOM 時回傳 `null`（測試環境）。
import { Texture } from "pixi.js";
import type { ParticleTex } from "./statusAnim";
import type { ShimmerTex } from "./surfaceAnim";

type Ctx = CanvasRenderingContext2D;
const TAU = Math.PI * 2;
const DPR = 2;

interface Spec {
  w: number;
  h: number;
  /** 錨點（0～1）：粒子的位置對到貼圖的這一點。 */
  ax: number;
  ay: number;
  draw: (c: Ctx) => void;
}

function flameShape(c: Ctx, k: number): void {
  // 4 個形狀：火舌往左、右擺，高低不同
  const lean = [-1.2, 0.6, 1.4, -0.4][k]!;
  const tall = [11, 12.5, 10.5, 13][k]!;
  c.fillStyle = "#ff8a1e";
  c.strokeStyle = "#3a1404";
  c.lineWidth = 1;
  c.beginPath();
  c.moveTo(6, 15);
  c.quadraticCurveTo(0.5, 10, 4 + lean, 15 - tall);
  c.quadraticCurveTo(11.5, 9, 6, 15);
  c.fill();
  c.stroke();
  c.fillStyle = "#ffe27a";
  c.beginPath();
  c.moveTo(6, 14.5);
  c.quadraticCurveTo(3.8, 11.5, 5 + lean * 0.5, 15 - tall * 0.55);
  c.quadraticCurveTo(8.6, 11.5, 6, 14.5);
  c.fill();
}

const SPECS: Readonly<Record<ParticleTex, Spec>> = {
  flame0: { w: 12, h: 16, ax: 0.5, ay: 0.94, draw: (c) => flameShape(c, 0) },
  flame1: { w: 12, h: 16, ax: 0.5, ay: 0.94, draw: (c) => flameShape(c, 1) },
  flame2: { w: 12, h: 16, ax: 0.5, ay: 0.94, draw: (c) => flameShape(c, 2) },
  flame3: { w: 12, h: 16, ax: 0.5, ay: 0.94, draw: (c) => flameShape(c, 3) },
  smoke: {
    w: 14,
    h: 12,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      c.fillStyle = "rgba(90,86,84,0.85)";
      for (const [x, y, r] of [
        [5, 7, 3.6],
        [8.5, 5.5, 3.8],
        [9, 8, 3],
      ] as const) {
        c.beginPath();
        c.arc(x, y, r, 0, TAU);
        c.fill();
      }
    },
  },
  bubble: {
    w: 8,
    h: 8,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      c.fillStyle = "rgba(120,210,80,0.75)";
      c.strokeStyle = "#1d4a12";
      c.lineWidth = 0.9;
      c.beginPath();
      c.arc(4, 4, 3, 0, TAU);
      c.fill();
      c.stroke();
      c.fillStyle = "rgba(255,255,255,0.8)";
      c.beginPath();
      c.arc(3, 3, 0.9, 0, TAU);
      c.fill();
    },
  },
  star: {
    w: 10,
    h: 10,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      c.fillStyle = "#ffd84a";
      c.strokeStyle = "#5a4000";
      c.lineWidth = 0.8;
      c.beginPath();
      for (let i = 0; i < 10; i++) {
        const r = i % 2 === 0 ? 4 : 1.7;
        const a = -Math.PI / 2 + (i * Math.PI) / 5;
        const x = 5 + Math.cos(a) * r;
        const y = 5 + Math.sin(a) * r;
        if (i === 0) c.moveTo(x, y);
        else c.lineTo(x, y);
      }
      c.closePath();
      c.fill();
      c.stroke();
    },
  },
  ring: {
    w: 32,
    h: 10,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      c.strokeStyle = "rgba(255,216,74,0.8)";
      c.lineWidth = 1.2;
      c.beginPath();
      c.ellipse(16, 5, 14, 4, 0, 0, TAU);
      c.stroke();
    },
  },
  glint: {
    w: 6,
    h: 22,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const g = c.createLinearGradient(0, 0, 6, 0);
      g.addColorStop(0, "rgba(255,255,255,0)");
      g.addColorStop(0.5, "rgba(255,255,255,0.95)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = g;
      c.fillRect(0, 0, 6, 22);
    },
  },
  vine: {
    w: 10,
    h: 16,
    ax: 0.3,
    ay: 1,
    draw: (c) => {
      c.strokeStyle = "#3d8a2a";
      c.lineWidth = 2;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(3, 16);
      c.bezierCurveTo(1, 11, 8, 9, 5, 3);
      c.stroke();
      c.fillStyle = "#5cb83c";
      c.beginPath();
      c.ellipse(6.5, 6.5, 2.2, 1.2, -0.6, 0, TAU);
      c.fill();
    },
  },
  drop: {
    w: 6,
    h: 8,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      c.fillStyle = "#6ab8ff";
      c.strokeStyle = "#163a66";
      c.lineWidth = 0.8;
      c.beginPath();
      c.moveTo(3, 0.6);
      c.quadraticCurveTo(5.6, 4.6, 3, 7.2);
      c.quadraticCurveTo(0.4, 4.6, 3, 0.6);
      c.fill();
      c.stroke();
    },
  },
  arc0: { w: 16, h: 12, ax: 0.5, ay: 0.5, draw: (c) => arcShape(c, 0) },
  arc1: { w: 16, h: 12, ax: 0.5, ay: 0.5, draw: (c) => arcShape(c, 1) },
  arc2: { w: 16, h: 12, ax: 0.5, ay: 0.5, draw: (c) => arcShape(c, 2) },
};

const ARC_PATHS: ReadonlyArray<ReadonlyArray<readonly [number, number]>> = [
  [
    [1, 7],
    [5, 3],
    [7, 8],
    [11, 4],
    [15, 6],
  ],
  [
    [2, 2],
    [6, 6],
    [4, 9],
    [10, 7],
    [14, 11],
  ],
  [
    [1, 10],
    [4, 5],
    [8, 7],
    [9, 2],
    [15, 3],
  ],
];

function arcShape(c: Ctx, k: number): void {
  const pts = ARC_PATHS[k]!;
  for (const [w, color] of [
    [2.6, "rgba(140,200,255,0.55)"],
    [1.1, "#fffbe0"],
  ] as const) {
    c.strokeStyle = color;
    c.lineWidth = w;
    c.lineJoin = "round";
    c.beginPath();
    pts.forEach(([x, y], i) => (i === 0 ? c.moveTo(x, y) : c.lineTo(x, y)));
    c.stroke();
  }
}

const SHIMMER_SPECS: Readonly<Record<ShimmerTex, Spec>> = {
  streak: {
    w: 22,
    h: 4,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const g = c.createLinearGradient(0, 0, 22, 0);
      g.addColorStop(0, "rgba(255,255,255,0)");
      g.addColorStop(0.5, "rgba(255,255,255,1)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(11, 2, 11, 1.2, 0, 0, TAU);
      c.fill();
    },
  },
  sheen: {
    w: 34,
    h: 22,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const g = c.createRadialGradient(17, 11, 1, 17, 11, 16);
      g.addColorStop(0, "rgba(255,255,255,0.9)");
      g.addColorStop(0.55, "rgba(255,255,255,0.45)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(17, 11, 16, 10, 0, 0, TAU);
      c.fill();
    },
  },
  glow: {
    w: 44,
    h: 40,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const g = c.createRadialGradient(22, 20, 2, 22, 20, 21);
      g.addColorStop(0, "rgba(255,255,255,1)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = g;
      c.fillRect(0, 0, 44, 40);
    },
  },
  // 6V-2：熔岩上漂的岩殼塊（不透光深色、邊緣裂紋；sprite 用 normal 混色）
  crust: {
    w: 20,
    h: 14,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const pts: ReadonlyArray<readonly [number, number]> = [
        [2, 7],
        [5, 2],
        [12, 1],
        [18, 4],
        [19, 9],
        [14, 13],
        [6, 12],
      ];
      c.beginPath();
      pts.forEach(([x, y], i) => (i === 0 ? c.moveTo(x, y) : c.lineTo(x, y)));
      c.closePath();
      c.fillStyle = "rgba(42,22,16,0.92)";
      c.fill();
      c.strokeStyle = "rgba(20,10,6,0.95)";
      c.lineWidth = 1.2;
      c.lineJoin = "round";
      c.stroke();
      c.strokeStyle = "rgba(255,211,107,0.35)";
      c.lineWidth = 0.8;
      c.beginPath();
      c.moveTo(6, 6);
      c.lineTo(11, 8);
      c.lineTo(14, 5);
      c.stroke();
    },
  },
  // 6V-2b：深水上慢慢飄的大波紋（一道很淡的寬弧；add 混色、染灰藍）
  swell: {
    w: 46,
    h: 10,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const g = c.createLinearGradient(0, 0, 46, 0);
      g.addColorStop(0, "rgba(255,255,255,0)");
      g.addColorStop(0.5, "rgba(255,255,255,1)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      c.strokeStyle = g;
      c.lineWidth = 1.6;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(2, 7);
      c.quadraticCurveTo(23, 1, 44, 7);
      c.stroke();
    },
  },
  // 6V-2：熔岩上漂的熱光（add 混色、染橘）
  ember: {
    w: 36,
    h: 30,
    ax: 0.5,
    ay: 0.5,
    draw: (c) => {
      const g = c.createRadialGradient(18, 15, 1, 18, 15, 17);
      g.addColorStop(0, "rgba(255,255,255,1)");
      g.addColorStop(0.5, "rgba(255,255,255,0.4)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(18, 15, 17, 13, 0, 0, TAU);
      c.fill();
    },
  },
};

const cache = new Map<string, Texture>();

function textureOf(key: string, spec: Spec): Texture | null {
  if (typeof document === "undefined") return null;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = spec.w * DPR;
  canvas.height = spec.h * DPR;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(DPR, DPR);
  spec.draw(ctx);
  const tex = Texture.from(canvas);
  cache.set(key, tex);
  return tex;
}

export interface AnimTex {
  texture: Texture;
  /** 虛擬單位（52 ＝ 一格）的寬高與錨點。 */
  w: number;
  h: number;
  ax: number;
  ay: number;
}

export function particleTexture(tex: ParticleTex): AnimTex | null {
  const spec = SPECS[tex];
  const texture = textureOf(`p|${tex}`, spec);
  return texture === null ? null : { texture, w: spec.w, h: spec.h, ax: spec.ax, ay: spec.ay };
}

export function shimmerTexture(tex: ShimmerTex): AnimTex | null {
  const spec = SHIMMER_SPECS[tex];
  const texture = textureOf(`s|${tex}`, spec);
  return texture === null ? null : { texture, w: spec.w, h: spec.h, ax: spec.ax, ay: spec.ay };
}

/** 目前產生過的動畫小貼圖數（效能量測用；上限 19，6V-2 加了岩殼與熱光）。 */
export const animTextureCount = (): number => cache.size;
