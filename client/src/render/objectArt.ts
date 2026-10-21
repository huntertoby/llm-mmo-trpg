// 場景物件的程式繪製（Phase 3-16a；移植自美術 PM 樣張 procedural.js 的 OBJECT_DRAW）。
// 每個物件畫成一張透明背景的離屏貼圖（座標以 ART_T ＝ 52 的虛擬格為單位）。
// 沒有畫法的新物件：灰色六角形（字 glyph 由繪圖端疊上），不會出錯。
import { PAL, rgba } from "./artPalette";
import { flame, roundRect, shadowEllipse, TAU, type Ctx } from "./artDraw";
import { rng } from "./artRandom";
import { ART_T } from "./terrainArt";

const T = ART_T;

export interface ObjectArtSpec {
  kind: string;
  x: number;
  y: number;
  /** 左右鄰格也是同種物件（矮牆連起來）。 */
  joinL: boolean;
  joinR: boolean;
  /** 橋沿南北方向鋪（上下鄰是橋、左右不是）。 */
  vertical: boolean;
  flammable: boolean;
}

export function objectArtKey(s: ObjectArtSpec): string {
  return [s.kind, s.x, s.y, +s.joinL, +s.joinR, +s.vertical, +s.flammable].join("|");
}

type ObjectDrawer = (ctx: Ctx, s: ObjectArtSpec) => void;

function crate(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * 0.34, T * 0.3);
  const s = T * 0.62;
  const o = (T - s) / 2;
  roundRect(ctx, o, o, s, s, 3);
  ctx.fillStyle = PAL.wood;
  ctx.fill();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = PAL.woodDark;
  ctx.stroke();
  ctx.strokeStyle = PAL.woodMid;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let i = 1; i < 3; i++) {
    ctx.moveTo(o + 2, o + (s * i) / 3);
    ctx.lineTo(o + s - 2, o + (s * i) / 3);
  }
  ctx.stroke();
  ctx.strokeStyle = PAL.woodDark;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(o + 3, o + 3);
  ctx.lineTo(o + s - 3, o + s - 3);
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.18)";
  ctx.fillRect(o + 2, o + 2, s - 4, 3);
}

function oilBarrel(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * 0.3, T * 0.28);
  const c = T / 2;
  const r = T * 0.29;
  ctx.fillStyle = "#4a2a12";
  roundRect(ctx, c - r, c - r + 4, r * 2, r * 2, r);
  ctx.fill();
  ctx.fillStyle = "#8a5228";
  ctx.beginPath();
  ctx.arc(c, c, r, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "rgba(60,32,12,0.55)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let k = -2; k <= 2; k++) {
    const half = Math.sqrt(r * r - (k * r * 0.36) ** 2);
    ctx.moveTo(c + k * r * 0.36, c - half + 1);
    ctx.lineTo(c + k * r * 0.36, c + half - 1);
  }
  ctx.stroke();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "#9aa0a8";
  ctx.beginPath();
  ctx.arc(c, c, r - 1.5, 0, TAU);
  ctx.stroke();
  ctx.save();
  ctx.beginPath();
  ctx.arc(c, c, r * 0.5, 0, TAU);
  ctx.clip();
  ctx.fillStyle = "#f2b33d";
  ctx.fillRect(c - r, c - r, r * 2, r * 2);
  ctx.fillStyle = "#1a120a";
  ctx.beginPath();
  ctx.moveTo(c, c - 5.5);
  ctx.bezierCurveTo(c + 5, c + 0.5, c + 4, c + 5, c, c + 5);
  ctx.bezierCurveTo(c - 4, c + 5, c - 5, c + 0.5, c, c - 5.5);
  ctx.fill();
  ctx.restore();
}

function stonePillar(ctx: Ctx): void {
  const c = T / 2;
  const r = T * 0.3;
  const oct = (cx: number, cy: number, rad: number): void => {
    ctx.beginPath();
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * TAU + Math.PI / 8;
      ctx.lineTo(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad);
    }
    ctx.closePath();
  };
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.moveTo(c - r * 0.7, c + r * 0.7);
  ctx.lineTo(c + r * 0.7, c - r * 0.7);
  ctx.lineTo(c + r * 0.7 + 12, c - r * 0.7 + 12);
  ctx.lineTo(c - r * 0.7 + 12, c + r * 0.7 + 12);
  ctx.fill();
  oct(c + 12, c + 12, r);
  ctx.fill();
  ctx.fillStyle = PAL.rockDark;
  oct(c, c + 5, r);
  ctx.fill();
  ctx.fillRect(c - r * 0.92, c, r * 1.84, 5);
  ctx.fillStyle = PAL.rock;
  oct(c, c, r);
  ctx.fill();
  ctx.fillStyle = "#bdb9af";
  oct(c, c, r * 0.62);
  ctx.fill();
  ctx.strokeStyle = "rgba(80,76,70,0.7)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(c - 3, c - r + 2);
  ctx.lineTo(c + 1, c - 5);
  ctx.lineTo(c - 2, c + 2);
  ctx.stroke();
}

/** 矮牆（美術 PM docs/art/矮牆.md）：暖色石塊——頂面亮、正面錯縫磚、2px 深色外框（相連的一側不畫）、較深的投影。 */
const LOW_WALL = { top: "#d8c7a2", topEdge: "#f2e6c8", face: "#86704f", mortar: "#4c3d2a", outline: "#241c13" } as const;

function lowWall(ctx: Ctx, s: ObjectArtSpec): void {
  const x0 = s.joinL ? 0 : 4;
  const x1 = s.joinR ? T : T - 4;
  const capY = T * 0.3;
  const capH = T * 0.16;
  const faceH = T * 0.26;
  const faceY = capY + capH;
  const w = x1 - x0;
  // 投影（落向右下）
  ctx.fillStyle = "rgba(0,0,0,0.42)";
  ctx.fillRect(x0 + 4, faceY + faceH, w, 7);
  // 正面：兩排錯縫磚
  ctx.fillStyle = LOW_WALL.face;
  ctx.fillRect(x0, faceY, w, faceH);
  ctx.strokeStyle = LOW_WALL.mortar;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const rowH = faceH / 2;
  ctx.moveTo(x0, faceY + rowH);
  ctx.lineTo(x1, faceY + rowH);
  for (let r = 0; r < 2; r++) {
    for (let bx = r ? 8 : 17; bx < x1 - 1; bx += 17) {
      if (bx <= x0 + 1) continue;
      ctx.moveTo(bx, faceY + r * rowH);
      ctx.lineTo(bx, faceY + (r + 1) * rowH);
    }
  }
  ctx.stroke();
  // 壓頂石（頂面）：最上面 2px 亮邊，每 26px 一條縫
  ctx.fillStyle = LOW_WALL.top;
  ctx.fillRect(x0, capY, w, capH);
  ctx.fillStyle = LOW_WALL.topEdge;
  ctx.fillRect(x0, capY, w, 2);
  ctx.strokeStyle = "rgba(76,61,42,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let bx = 13; bx < x1 - 1; bx += 26) {
    if (bx <= x0 + 1) continue;
    ctx.moveTo(bx, capY);
    ctx.lineTo(bx, capY + capH);
  }
  ctx.stroke();
  // 外框：只框外輪廓，相連的那一側不畫；壓頂石與正面之間一條 1px 線
  ctx.strokeStyle = LOW_WALL.outline;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x0, capY);
  ctx.lineTo(x1, capY);
  ctx.moveTo(x0, faceY + faceH);
  ctx.lineTo(x1, faceY + faceH);
  if (!s.joinL) {
    ctx.moveTo(x0, capY);
    ctx.lineTo(x0, faceY + faceH);
  }
  if (!s.joinR) {
    ctx.moveTo(x1, capY);
    ctx.lineTo(x1, faceY + faceH);
  }
  ctx.stroke();
  ctx.strokeStyle = "rgba(36,28,19,0.7)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x0, faceY);
  ctx.lineTo(x1, faceY);
  ctx.stroke();
}

function woodenBridge(ctx: Ctx, s: ObjectArtSpec): void {
  ctx.save();
  if (s.vertical) {
    ctx.translate(T, 0);
    ctx.rotate(Math.PI / 2);
  }
  ctx.fillStyle = "#7a5028";
  ctx.fillRect(0, 7, T, T - 14);
  ctx.strokeStyle = "#4b2f15";
  ctx.lineWidth = 1.5;
  for (let px = 0; px <= T; px += T / 6) {
    ctx.beginPath();
    ctx.moveTo(px, 8);
    ctx.lineTo(px, T - 8);
    ctx.stroke();
  }
  const r = rng(s.x, s.y, 30);
  for (let px = 0; px < T; px += T / 6) {
    ctx.fillStyle = `rgba(255,220,170,${0.05 + r() * 0.12})`;
    ctx.fillRect(px + 1, 8, T / 6 - 2, T - 16);
  }
  ctx.fillStyle = "#4b2f15";
  ctx.fillRect(0, 4, T, 4);
  ctx.fillRect(0, T - 8, T, 4);
  ctx.restore();
}

function fallenLog(ctx: Ctx): void {
  ctx.save();
  ctx.translate(T / 2, T / 2);
  ctx.rotate(-0.5);
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  roundRect(ctx, -T * 0.4 + 3, -7 + 6, T * 0.8, 15, 7);
  ctx.fill();
  ctx.fillStyle = "#7a5130";
  roundRect(ctx, -T * 0.4, -8, T * 0.8, 16, 8);
  ctx.fill();
  ctx.strokeStyle = "#4e3119";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-T * 0.3, -3);
  ctx.lineTo(T * 0.1, -3);
  ctx.moveTo(-T * 0.2, 3);
  ctx.lineTo(T * 0.2, 3);
  ctx.stroke();
  ctx.fillStyle = "#d1a86e";
  ctx.beginPath();
  ctx.ellipse(T * 0.36, 0, 5, 8, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#8a6038";
  ctx.beginPath();
  ctx.ellipse(T * 0.36, 0, 2.5, 4.5, 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
}

function earthWall(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * 0.42, T * 0.3);
  roundRect(ctx, 5, 9, T - 10, T - 16, 10);
  ctx.fillStyle = "#8a6a45";
  ctx.fill();
  ctx.fillStyle = "#a7845a";
  roundRect(ctx, 8, 9, T - 16, T * 0.35, 8);
  ctx.fill();
  ctx.strokeStyle = "#5e4529";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(9, T * 0.58);
  ctx.lineTo(T - 9, T * 0.55);
  ctx.moveTo(10, T * 0.7);
  ctx.lineTo(T - 12, T * 0.72);
  ctx.stroke();
}

function deadTree(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 4, T / 2 + 5, T * 0.36, T * 0.3);
  ctx.strokeStyle = "#4a3624";
  ctx.lineCap = "round";
  const branch = (x: number, y: number, a: number, len: number, w: number, depth: number): void => {
    const x2 = x + Math.cos(a) * len;
    const y2 = y + Math.sin(a) * len;
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    if (depth > 0) {
      branch(x2, y2, a - 0.5, len * 0.6, w * 0.6, depth - 1);
      branch(x2, y2, a + 0.6, len * 0.55, w * 0.6, depth - 1);
    }
  };
  for (let k = 0; k < 5; k++) branch(T / 2, T / 2, (k / 5) * TAU + 0.3, T * 0.2, 4, 1);
  ctx.fillStyle = "#5c4430";
  ctx.beginPath();
  ctx.arc(T / 2, T / 2, 6, 0, TAU);
  ctx.fill();
}

// ---- 樣張沒有的物件：依同一套規則補（影子在右下、深淺兩階、深色外框）----

function iceWall(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * 0.38, T * 0.28);
  roundRect(ctx, 6, 8, T - 12, T - 16, 7);
  ctx.fillStyle = rgba(PAL.iceWall, 0.78);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#5fa8d3";
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.45)";
  roundRect(ctx, 9, 10, T - 18, T * 0.28, 5);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.85)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(14, T - 16);
  ctx.lineTo(22, T - 26);
  ctx.moveTo(T - 20, T - 14);
  ctx.lineTo(T - 15, T - 22);
  ctx.stroke();
}

function thornWall(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 40);
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * 0.4, T * 0.28);
  ctx.fillStyle = "#33521c";
  ctx.beginPath();
  ctx.ellipse(T / 2, T / 2 + 2, T * 0.38, T * 0.3, 0, 0, TAU);
  ctx.fill();
  ctx.lineCap = "round";
  ctx.lineWidth = 3;
  ctx.strokeStyle = PAL.thorn;
  for (let i = 0; i < 4; i++) {
    const y = 12 + i * 9 + r() * 3;
    ctx.beginPath();
    ctx.moveTo(6, y);
    ctx.bezierCurveTo(T * 0.3, y - 8, T * 0.6, y + 8, T - 6, y);
    ctx.stroke();
  }
  ctx.fillStyle = "#d8d2a8";
  for (let i = 0; i < 9; i++) {
    const px = 8 + r() * (T - 16);
    const py = 10 + r() * (T - 20);
    ctx.beginPath();
    ctx.moveTo(px, py - 4);
    ctx.lineTo(px + 2.5, py + 2);
    ctx.lineTo(px - 2.5, py + 2);
    ctx.closePath();
    ctx.fill();
  }
}

function rubble(ctx: Ctx, s: ObjectArtSpec): void {
  // 3–5 塊大石頭，約佔格子 70%；每塊有影子與亮面
  const r = rng(s.x, s.y, 41);
  const n = 3 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * TAU + r() * 0.8;
    const dist = i === 0 ? 0 : 9 + r() * 5;
    const cx = T / 2 + Math.cos(a0) * dist;
    const cy = T / 2 + 2 + Math.sin(a0) * dist * 0.8;
    const rad = 8 + r() * 4;
    shadowEllipse(ctx, cx + 2, cy + rad * 0.6, rad * 1.05, rad * 0.55);
    ctx.fillStyle = i % 2 === 0 ? PAL.rock : PAL.rockDark;
    ctx.beginPath();
    for (let k = 0; k < 7; k++) {
      const a = (k / 7) * TAU;
      const rr = rad * (0.78 + r() * 0.3);
      ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * 0.85);
    }
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.28)";
    ctx.beginPath();
    ctx.ellipse(cx - rad * 0.25, cy - rad * 0.3, rad * 0.45, rad * 0.25, -0.4, 0, TAU);
    ctx.fill();
    ctx.fillStyle = "rgba(0,0,0,0.18)";
    ctx.fillRect(cx - rad * 0.2, cy + rad * 0.25, rad * 0.8, 1.5);
  }
}

function thinIce(ctx: Ctx, s: ObjectArtSpec): void {
  // 不規則的薄冰邊緣＋從一點放射的細裂紋
  const r = rng(s.x, s.y, 42);
  ctx.beginPath();
  const pts = 11;
  for (let k = 0; k < pts; k++) {
    const a = (k / pts) * TAU;
    const rad = T * (0.4 + r() * 0.08);
    ctx.lineTo(T / 2 + Math.cos(a) * rad, T / 2 + Math.sin(a) * rad);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(205,238,255,0.55)";
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = "rgba(255,255,255,0.8)";
  ctx.stroke();
  ctx.strokeStyle = "rgba(90,150,200,0.75)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const cx = T * (0.35 + r() * 0.3);
  const cy = T * (0.35 + r() * 0.3);
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU + r() * 0.5;
    const len = 12 + r() * 10;
    const mx = cx + Math.cos(a) * len * 0.5;
    const my = cy + Math.sin(a) * len * 0.5;
    ctx.moveTo(cx, cy);
    ctx.lineTo(mx, my);
    ctx.lineTo(mx + Math.cos(a + 0.6) * len * 0.5, my + Math.sin(a + 0.6) * len * 0.5);
  }
  ctx.stroke();
}

function grassFloor(ctx: Ctx, s: ObjectArtSpec): void {
  // 一團較高的深色草叢：3–4 簇草葉，約佔格子 70%，下方有淡影子（和地面的短草明顯不同）
  const r = rng(s.x, s.y, 43);
  shadowEllipse(ctx, T / 2 + 2, T * 0.78, T * 0.36, T * 0.12);
  const clumps = 3 + Math.floor(r() * 2);
  for (let i = 0; i < clumps; i++) {
    const bx = T * (0.22 + (0.56 * i) / (clumps - 1)) + (r() - 0.5) * 4;
    const by = T * (0.74 + (i % 2) * 0.04);
    const blades = 6 + Math.floor(r() * 3);
    for (let b = 0; b < blades; b++) {
      const lean = ((b / (blades - 1)) * 2 - 1) * 9 + (r() - 0.5) * 3;
      const h = 20 + r() * 8 - Math.abs(lean) * 0.5;
      ctx.fillStyle = b % 3 === 0 ? PAL.grassLight : PAL.bush;
      ctx.beginPath();
      ctx.moveTo(bx + (b - blades / 2) * 1.1 - 1.6, by);
      ctx.quadraticCurveTo(bx + lean * 0.5, by - h * 0.6, bx + lean, by - h);
      ctx.quadraticCurveTo(bx + lean * 0.5 + 2, by - h * 0.5, bx + (b - blades / 2) * 1.1 + 1.6, by);
      ctx.closePath();
      ctx.fill();
    }
  }
}

export const OBJECT_DRAW: Readonly<Record<string, ObjectDrawer>> = {
  crate,
  oil_barrel: oilBarrel,
  stone_pillar: stonePillar,
  low_wall: lowWall,
  wooden_bridge: woodenBridge,
  fallen_log: fallenLog,
  earth_wall: earthWall,
  dead_tree: deadTree,
  ice_wall: iceWall,
  thorn_wall: thornWall,
  rubble,
  thin_ice: thinIce,
  grass: grassFloor,
};

export function hasObjectArt(kind: string): boolean {
  return kind in OBJECT_DRAW;
}

/** 沒有畫法的新物件：灰色六角形（不會出錯；字由繪圖端疊上）。 */
function drawGenericObject(ctx: Ctx): void {
  ctx.fillStyle = "#888";
  ctx.beginPath();
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * TAU;
    ctx.lineTo(T / 2 + Math.cos(a) * 16, T / 2 + Math.sin(a) * 16);
  }
  ctx.closePath();
  ctx.fill();
}

/** 可燃物右上角的小火苗。 */
function flammableMark(ctx: Ctx): void {
  ctx.save();
  ctx.translate(T - 9, 12);
  ctx.fillStyle = "rgba(20,12,6,0.65)";
  ctx.beginPath();
  ctx.arc(0, -2, 6.5, 0, TAU);
  ctx.fill();
  flame(ctx, 0, 3, 9);
  ctx.restore();
}

export function drawObject(ctx: Ctx, s: ObjectArtSpec): void {
  (OBJECT_DRAW[s.kind] ?? drawGenericObject)(ctx, s);
  if (s.flammable && s.kind !== "wooden_bridge") flammableMark(ctx);
}
