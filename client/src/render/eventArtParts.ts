// 事件插圖用的地面、地物、小圖示（Phase 6C-ART2；移植自 docs/art/sample/explore.js、cloudTiles.js、ashenTiles.js、
// realms.js、hud.js 裡 events.js 用到的函式）。和實地地圖同一套畫法：52 的虛擬格、光從左上、深色外框。
// 只移植事件插圖用得到的部分；荒原的地面與枯木、枯草、木箱直接用遊戲已有的 ASHEN_TERRAIN、ASHEN_OBJECTS（5A-ART6 已移植）。
// 確定性：沒有 Math.random；需要變化的地方用座標當種子（同樣張的兩種種子算法）。
import { ASHEN_OBJECTS } from "./ashenObjects";
import { ASHEN_TERRAIN } from "./ashenTerrain";
import { type Ctx, TAU } from "./artDraw";
import { seeded } from "./artRandom";
import { rgba, shade } from "./color";
import type { ObjectArtSpec } from "./objectArt";
import type { TileArtSpec } from "./terrainArt";

/** 一格（虛擬單位）。 */
export const T = 52;
export const OUT = "#1c1712";

const C = {
  slate: "#7d8c84",
  moss: "#5a8a3a",
  red: "#b8432f",
  redDark: "#8a2f20",
  path: "#b89a62",
  grass: "#689a70",
  rock: "#6e6a62",
};

/** explore.js 的 xorshift（地面、地物用）。 */
function xorshift(seed: number): () => number {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >> 17;
    s ^= s << 5;
    s >>>= 0;
    return (s % 100000) / 100000;
  };
}
const R = (gx: number, gy: number, k: number): (() => number) => xorshift((gx * 73856093) ^ (gy * 19349663) ^ (k * 83492791));
/** realms.js 的種子（mulberry32；石板、竹子用）。 */
const RR = (gx: number, gy: number, k: number): (() => number) => seeded((gx * 73856093) ^ (gy * 19349663) ^ (k * 83492791));

export function rr(ctx: Ctx, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function box(ctx: Ctx, x: number, y: number, w: number, h: number, fill: string, stroke: string | null = OUT, lw = 2, r = 2): void {
  rr(ctx, x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke !== null) {
    ctx.lineWidth = lw;
    ctx.strokeStyle = stroke;
    ctx.stroke();
  }
}

export function dot(ctx: Ctx, x: number, y: number, r: number, fill: string): void {
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}

function shadow(ctx: Ctx, cx: number, cy: number, rx: number, ry: number, a = 0.3): void {
  ctx.fillStyle = `rgba(0,0,0,${a})`;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.fill();
}

/** 放射光暈（events.js 的 `glow`：`c` 是 `rgba(...)`，外圈透明）。 */
export function glow(ctx: Ctx, x: number, y: number, r: number, c: string, a: number): void {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, c);
  g.addColorStop(1, c.replace(/[\d.]+\)$/, "0)"));
  ctx.save();
  ctx.globalAlpha = a;
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  ctx.restore();
}

// ---------------- 地面 ----------------

/** realms.js 的石板（雲嶺青石板）。 */
function slabs(ctx: Ctx, x: number, y: number, gx: number, gy: number): void {
  const r = RR(gx, gy, 1);
  ctx.fillStyle = "#56645c";
  ctx.fillRect(x, y, T, T);
  const split = r() < 0.5;
  const blocks: readonly (readonly [number, number, number, number])[] = split
    ? [[0, 0, 0.55, 0.5], [0.55, 0, 0.45, 0.5], [0, 0.5, 1, 0.5]]
    : [[0, 0, 1, 0.45], [0, 0.45, 0.4, 0.55], [0.4, 0.45, 0.6, 0.55]];
  for (const [bx, by, bw, bh] of blocks) {
    ctx.fillStyle = shade("#7d8c84", 0.92 + r() * 0.16);
    ctx.beginPath();
    ctx.roundRect(x + bx * T + 1.5, y + by * T + 1.5, bw * T - 3, bh * T - 3, 3);
    ctx.fill();
    ctx.fillStyle = rgba("#ffffff", 0.12);
    ctx.fillRect(x + bx * T + 2, y + by * T + 2, bw * T - 4, 2);
  }
  if (r() < 0.45) {
    ctx.fillStyle = rgba("#5a8a3a", 0.75);
    for (let i = 0; i < 4; i++) {
      ctx.beginPath();
      ctx.arc(x + r() * T, y + r() * T, 2 + r() * 3, 0, TAU);
      ctx.fill();
    }
  }
}

/** 雲嶺地面：`g` 草地、`p` 黃土路、`s` 青石板（explore.js 的 `ground`）。 */
export function ground(ctx: Ctx, kind: "g" | "p" | "s", gx: number, gy: number): void {
  const x = gx * T;
  const y = gy * T;
  if (kind === "s") {
    slabs(ctx, x, y, gx, gy);
    return;
  }
  const r = R(gx, gy, 3);
  if (kind === "p") {
    ctx.fillStyle = shade(C.path, 0.95 + r() * 0.1);
    ctx.fillRect(x, y, T, T);
    for (let i = 0; i < 8; i++) {
      ctx.fillStyle = r() < 0.5 ? "rgba(90,70,40,0.4)" : "rgba(255,240,210,0.35)";
      ctx.fillRect(x + r() * T, y + r() * T, 2, 2);
    }
    return;
  }
  ctx.fillStyle = shade(C.grass, 0.95 + r() * 0.1);
  ctx.fillRect(x, y, T, T);
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  for (let i = 0; i < 6; i++) {
    const gx2 = x + 5 + r() * (T - 10);
    const gy2 = y + 8 + r() * (T - 13);
    ctx.strokeStyle = r() < 0.55 ? "#9ccf86" : "#4f8a3a";
    ctx.beginPath();
    ctx.moveTo(gx2, gy2);
    ctx.quadraticCurveTo(gx2 - 1, gy2 - 5, gx2 - 4, gy2 - 8);
    ctx.moveTo(gx2, gy2);
    ctx.quadraticCurveTo(gx2 + 1, gy2 - 5, gx2 + 4, gy2 - 9);
    ctx.stroke();
  }
}

const NO_SIDES = { n: false, s: false, w: false, e: false };

/** 荒原地面（遊戲的荒原地形畫法）：`stone` 焦土、`lava` 岩漿。 */
export function ashTile(ctx: Ctx, terrain: "stone" | "lava", gx: number, gy: number): void {
  const spec: TileArtSpec = {
    region: "ashen_waste",
    look: "",
    terrain,
    x: gx,
    y: gy,
    height: 0,
    surface: "none",
    surfSame: NO_SIDES,
    lip: NO_SIDES,
    wallFace: false,
    blocked: terrain === "lava",
    tint: null,
  };
  ctx.save();
  ctx.translate(gx * T, gy * T);
  ASHEN_TERRAIN[terrain]?.(ctx, spec);
  ctx.restore();
}

/** 荒原物件（遊戲的荒原物件畫法），左上角在 (x, y)。 */
export function ashObj(ctx: Ctx, kind: "dead_tree" | "grass" | "crate", x: number, y: number): void {
  const spec: ObjectArtSpec = {
    region: "ashen_waste",
    look: "",
    kind,
    x: Math.round(x),
    y: Math.round(y),
    joinL: false,
    joinR: false,
    vertical: false,
    flammable: false,
    turnsLeft: null,
    hpStage: 0,
  };
  ctx.save();
  ctx.translate(x, y);
  ASHEN_OBJECTS[kind]?.(ctx, spec);
  ctx.restore();
}

// ---------------- 圖示（小牌、泡泡共用；explore.js 的 ICON＋hud.js 的 notes、warn） ----------------

export type IconId = "coin" | "sword" | "bang" | "ask" | "rest" | "portal" | "scroll" | "notes" | "warn";
/** 第 5 個參數 `ink`：黑色圖示（驚嘆號、問號）改用的顏色；彩色圖示不理它。 */
type IconDraw = (ctx: Ctx, x: number, y: number, s: number, ink?: string) => void;

/** 事件插圖小牌（深底）上黑色圖示改用的淺色（6C-ART3 順手項）。 */
export const BADGE_ICON_INK = "#f2e6c8";

const bang: IconDraw = (ctx, x, y, s, ink = OUT) => {
  ctx.fillStyle = ink;
  ctx.fillRect(x - s * 0.12, y - s * 0.5, s * 0.24, s * 0.65);
  ctx.fillRect(x - s * 0.12, y + s * 0.3, s * 0.24, s * 0.22);
};

export const ICON: Readonly<Record<IconId, IconDraw>> = {
  coin(ctx, x, y, s) {
    dot(ctx, x, y + s * 0.1, s * 0.55, "#e8bb48");
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.beginPath();
    ctx.arc(x, y + s * 0.1, s * 0.55, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = OUT;
    ctx.fillRect(x - s * 0.15, y - s * 0.12, s * 0.3, s * 0.45);
  },
  sword(ctx, x, y, s) {
    ctx.strokeStyle = OUT;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(x - s * 0.5, y + s * 0.5);
    ctx.lineTo(x + s * 0.5, y - s * 0.5);
    ctx.stroke();
    ctx.strokeStyle = "#dfe4ea";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.strokeStyle = "#e8bb48";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(x - s * 0.45, y + s * 0.1);
    ctx.lineTo(x - s * 0.1, y + s * 0.45);
    ctx.stroke();
  },
  bang,
  ask(ctx, x, y, s, ink = OUT) {
    ctx.strokeStyle = ink;
    ctx.lineWidth = s * 0.22;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.arc(x, y - s * 0.18, s * 0.28, Math.PI * 1.05, Math.PI * 0.45);
    ctx.lineTo(x, y + s * 0.18);
    ctx.stroke();
    dot(ctx, x, y + s * 0.45, s * 0.12, ink);
  },
  rest(ctx, x, y, s) {
    ctx.fillStyle = "#ff8a2a";
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.55);
    ctx.quadraticCurveTo(x + s * 0.45, y, x, y + s * 0.4);
    ctx.quadraticCurveTo(x - s * 0.45, y, x, y - s * 0.55);
    ctx.fill();
    ctx.fillStyle = "#ffd23a";
    ctx.beginPath();
    ctx.ellipse(x, y + s * 0.12, s * 0.15, s * 0.25, 0, 0, TAU);
    ctx.fill();
  },
  portal(ctx, x, y, s) {
    ctx.save();
    ctx.shadowColor = "#8fe0ff";
    ctx.shadowBlur = 6;
    ctx.strokeStyle = "#5ac8f0";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, s * 0.45, 0, TAU);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, s * 0.2, 0, TAU);
    ctx.stroke();
    ctx.restore();
  },
  scroll(ctx, x, y, s) {
    box(ctx, x - s * 0.5, y - s * 0.4, s, s * 0.8, "#f2e6c8", OUT, 1.5, 1);
    ctx.fillStyle = C.redDark;
    ctx.fillRect(x - s * 0.6, y - s * 0.5, s * 1.2, s * 0.15);
    ctx.fillRect(x - s * 0.6, y + s * 0.35, s * 1.2, s * 0.15);
    ctx.strokeStyle = "#8a7a5a";
    ctx.lineWidth = 1;
    for (const k of [-0.15, 0, 0.15]) {
      ctx.beginPath();
      ctx.moveTo(x - s * 0.3, y + s * k);
      ctx.lineTo(x + s * 0.3, y + s * k);
      ctx.stroke();
    }
  },
  notes(ctx, x, y, s) {
    box(ctx, x - s * 0.5, y - s * 0.4, s, s * 0.7, "#f2e6c8", OUT, 1.5, 3);
    ctx.fillStyle = "#f2e6c8";
    ctx.beginPath();
    ctx.moveTo(x - s * 0.2, y + s * 0.28);
    ctx.lineTo(x - s * 0.3, y + s * 0.5);
    ctx.lineTo(x, y + s * 0.28);
    ctx.fill();
    ctx.strokeStyle = "#8a7a5a";
    ctx.lineWidth = 1;
    for (const k of [-0.18, 0.02]) {
      ctx.beginPath();
      ctx.moveTo(x - s * 0.3, y + s * k);
      ctx.lineTo(x + s * 0.3, y + s * k);
      ctx.stroke();
    }
  },
  warn(ctx, x, y, s) {
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.5);
    ctx.lineTo(x + s * 0.5, y + s * 0.4);
    ctx.lineTo(x - s * 0.5, y + s * 0.4);
    ctx.closePath();
    ctx.fillStyle = "#ffd23a";
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    bang(ctx, x, y + s * 0.02, s * 0.6);
  },
};

export type BubbleKind = "quest" | "talk" | "danger" | "info";
const BUBBLE_FILL: Readonly<Record<BubbleKind, string>> = { quest: "#ffd23a", talk: "#ffffff", danger: "#ff6a5a", info: "#bfe8ff" };

/** 頭上的泡泡（只放圖示）：quest 黃、talk 白、danger 紅、info 淺藍。 */
export function bubble(ctx: Ctx, x: number, y: number, icon: IconId, kind: BubbleKind): void {
  const fill = BUBBLE_FILL[kind];
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.35)";
  ctx.shadowOffsetY = 2;
  ctx.shadowBlur = 3;
  rr(ctx, x - 13, y - 26, 26, 22, 8);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.restore();
  ctx.beginPath();
  ctx.moveTo(x - 4, y - 5);
  ctx.lineTo(x, y + 2);
  ctx.lineTo(x + 4, y - 5);
  ctx.fillStyle = fill;
  ctx.fill();
  rr(ctx, x - 13, y - 26, 26, 22, 8);
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = fill;
  ctx.fillRect(x - 3, y - 6, 6, 3);
  ICON[icon](ctx, x, y - 15, 13);
}

// ---------------- 地物（座標以格為單位的照 explore.js；以像素為單位的照 cloudTiles.js、ashenTiles.js） ----------------

export function campfire(ctx: Ctx, gx: number, gy: number): void {
  const x = gx * T;
  const y = gy * T;
  const cx = x + T / 2;
  const cy = y + T * 0.6;
  const g = ctx.createRadialGradient(cx, cy, 3, cx, cy, 46);
  g.addColorStop(0, "rgba(255,190,90,0.45)");
  g.addColorStop(1, "rgba(255,190,90,0)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(cx, cy, 46, 0, TAU);
  ctx.fill();
  for (let k = 0; k < 7; k++) {
    const a = (k / 7) * TAU;
    box(ctx, cx + Math.cos(a) * 13 - 4, cy + Math.sin(a) * 7 - 3, 8, 6, "#8a8a84", OUT, 1.2, 3);
  }
  ctx.strokeStyle = "#5a3a20";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(cx - 9, cy + 3);
  ctx.lineTo(cx + 9, cy - 3);
  ctx.moveTo(cx - 9, cy - 3);
  ctx.lineTo(cx + 9, cy + 3);
  ctx.stroke();
  ctx.save();
  ctx.shadowColor = "#ff8a2a";
  ctx.shadowBlur = 12;
  ICON.rest(ctx, cx, cy - 8, 22);
  ctx.restore();
}

function sparkle(ctx: Ctx, x: number, y: number): void {
  ctx.beginPath();
  ctx.moveTo(x, y - 4);
  ctx.lineTo(x + 1.2, y - 1.2);
  ctx.lineTo(x + 4, y);
  ctx.lineTo(x + 1.2, y + 1.2);
  ctx.lineTo(x, y + 4);
  ctx.lineTo(x - 1.2, y + 1.2);
  ctx.lineTo(x - 4, y);
  ctx.lineTo(x - 1.2, y - 1.2);
  ctx.fill();
}

export function chest(ctx: Ctx, gx: number, gy: number): void {
  const x = gx * T;
  const y = gy * T;
  const cx = x + T / 2;
  shadow(ctx, cx + 3, y + T * 0.78, 16, 5);
  box(ctx, cx - 14, y + 22, 28, 18, "#8a5a30", OUT, 2, 2);
  ctx.beginPath();
  ctx.moveTo(cx - 14, y + 24);
  ctx.quadraticCurveTo(cx, y + 8, cx + 14, y + 24);
  ctx.closePath();
  ctx.fillStyle = "#a06a38";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "#e8bb48";
  ctx.fillRect(cx - 15, y + 22, 30, 3);
  box(ctx, cx - 3, y + 24, 6, 7, "#e8bb48", OUT, 1.2, 1);
  ctx.save();
  ctx.globalAlpha = 0.9;
  ctx.fillStyle = "#fff4c0";
  for (const [sx, sy] of [[-16, 8], [15, 12], [4, 2]] as const) sparkle(ctx, cx + sx, y + sy);
  ctx.restore();
}

export function stele(ctx: Ctx, gx: number, gy: number): void {
  const x = gx * T;
  const y = gy * T;
  const cx = x + T / 2;
  shadow(ctx, cx + 4, y + T * 0.85, 16, 5);
  box(ctx, cx - 10, y + 10, 20, 34, "#8a948c", OUT, 2, 6);
  ctx.fillStyle = rgba(C.moss, 0.8);
  ctx.beginPath();
  ctx.arc(cx - 6, y + 40, 5, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#4a524c";
  ctx.lineWidth = 1.2;
  for (const k of [18, 24, 30]) {
    ctx.beginPath();
    ctx.moveTo(cx - 5, y + k);
    ctx.lineTo(cx + 5, y + k);
    ctx.stroke();
  }
}

/** realms.js 的竹子（一叢 4 根）。 */
function bamboo(ctx: Ctx, x: number, y: number): void {
  const r = RR(x, y, 9);
  shadow(ctx, x + T / 2 + 3, y + T * 0.86, 18, 5, 0.35);
  for (let i = 0; i < 4; i++) {
    const bx = x + 10 + i * 10 + r() * 3;
    const top = y + 2 + r() * 8;
    ctx.fillStyle = i % 2 ? "#4f8a3a" : "#6aa84a";
    ctx.fillRect(bx, top, 5, y + T * 0.86 - top);
    ctx.strokeStyle = OUT;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(bx, top, 5, y + T * 0.86 - top);
    ctx.fillStyle = "#2f5a22";
    for (let k = top + 9; k < y + T * 0.8; k += 10) ctx.fillRect(bx - 1, k, 7, 2);
    ctx.fillStyle = "#7cc05a";
    ctx.beginPath();
    ctx.ellipse(bx + 9, top + 6 + r() * 6, 7, 2.5, -0.5, 0, TAU);
    ctx.fill();
  }
}

/** 大片竹林（cloudTiles.js）。 */
export function bambooGrove(ctx: Ctx, x: number, y: number, w: number, h: number): void {
  shadow(ctx, x + (w * T) / 2 + 6, y + h * T - 8, w * T * 0.5, 12, 0.35);
  const r = R(x, y, 81);
  for (let k = 0; k < w * h * 3; k++) bamboo(ctx, x + r() * (w - 1) * T, y + r() * (h - 0.6) * T);
}

/** 枯木林（ashenTiles.js；枯木、枯草用遊戲的荒原物件）。 */
export function deadGrove(ctx: Ctx, x: number, y: number, w: number, h: number): void {
  shadow(ctx, x + (w * T) / 2 + 6, y + h * T - 8, w * T * 0.5, 12, 0.35);
  const r = R(x, y, 61);
  for (let k = 0; k < w * h * 2 + 1; k++) ashObj(ctx, "dead_tree", x + r() * (w - 0.8) * T, y + r() * (h - 0.8) * T);
  for (let k = 0; k < w * h; k++) ashObj(ctx, "grass", x + r() * (w - 1) * T, y + (h - 1) * T * r());
}

export function pine(ctx: Ctx, x: number, y: number): void {
  const cx = x + T / 2;
  shadow(ctx, cx + 4, y + T * 0.9, 20, 6, 0.35);
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 7;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(cx, y + T * 0.92);
  ctx.quadraticCurveTo(cx - 6, y + 24, cx + 4, y + 8);
  ctx.stroke();
  ctx.strokeStyle = "#6a4a30";
  ctx.lineWidth = 4.5;
  ctx.stroke();
  for (const [dx, dy, rw] of [[-14, 10, 16], [12, 4, 15], [-2, -4, 14], [14, 20, 11]] as const) {
    ctx.fillStyle = "#2f5a3a";
    ctx.beginPath();
    ctx.ellipse(cx + dx, y + dy, rw, rw * 0.45, 0, 0, TAU);
    ctx.fill();
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    ctx.fillStyle = "rgba(160,220,140,0.25)";
    ctx.beginPath();
    ctx.ellipse(cx + dx - 3, y + dy - 2, rw * 0.6, rw * 0.2, 0, 0, TAU);
    ctx.fill();
  }
}

export function boulder(ctx: Ctx, x: number, y: number): void {
  shadow(ctx, x + T / 2 + 3, y + T * 0.78, 20, 6);
  ctx.beginPath();
  ctx.moveTo(x + 8, y + 40);
  ctx.lineTo(x + 12, y + 20);
  ctx.lineTo(x + 26, y + 12);
  ctx.lineTo(x + 40, y + 18);
  ctx.lineTo(x + 45, y + 38);
  ctx.closePath();
  ctx.fillStyle = C.rock;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.18)";
  ctx.fillRect(x + 16, y + 18, 12, 3);
  dot(ctx, x + 34, y + 30, 3, rgba(C.moss, 0.8));
}

/** 花草（cloudTiles.js；樣張以像素座標當種子）。 */
export function flowers(ctx: Ctx, x: number, y: number, gx: number, gy: number): void {
  const r = R(gx, gy, 91);
  const colors = ["#f2e6c8", "#e8a0b0", "#ffd23a"] as const;
  for (let k = 0; k < 6; k++) {
    const px = x + 6 + r() * 40;
    const py = y + 10 + r() * 34;
    ctx.strokeStyle = "#4f8a3a";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(px, py + 5);
    ctx.lineTo(px, py);
    ctx.stroke();
    dot(ctx, px, py, 2.2, colors[k % 3]!);
  }
}

/** 飄霧（固定時間 `t`，不動）。 */
export function mistWisp(ctx: Ctx, x: number, y: number, t: number): void {
  for (let k = 0; k < 3; k++) {
    const px = x + 10 + k * 14 + Math.sin(t / 900 + k) * 4;
    const py = y + 20 + k * 6;
    const g = ctx.createRadialGradient(px, py, 1, px, py, 16);
    g.addColorStop(0, "rgba(232,232,224,0.45)");
    g.addColorStop(1, "rgba(232,232,224,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - 10, y, T + 20, T);
  }
}

/** 雲嶺祭壇：石台＋香爐＋煙。 */
export function altar(ctx: Ctx, x: number, y: number): void {
  const cx = x + T / 2;
  shadow(ctx, cx + 3, y + T * 0.84, 22, 6);
  box(ctx, x + 6, y + 26, T - 12, 16, shade(C.slate, 1.1), OUT, 2, 2);
  box(ctx, x + 10, y + 22, T - 20, 6, C.slate, OUT, 1.6, 1);
  ctx.beginPath();
  ctx.ellipse(cx, y + 20, 8, 4, 0, 0, TAU);
  ctx.fillStyle = "#8a6a3a";
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  box(ctx, cx - 7, y + 14, 14, 7, "#a07a40", OUT, 1.6, 2);
  ctx.strokeStyle = "rgba(240,240,235,0.7)";
  ctx.lineWidth = 1.5;
  for (let k = -1; k <= 1; k++) {
    ctx.beginPath();
    ctx.moveTo(cx + k * 3, y + 13);
    ctx.bezierCurveTo(cx + k * 3 - 4, y + 6, cx + k * 3 + 4, y + 2, cx + k * 3, y - 4);
    ctx.stroke();
  }
  dot(ctx, x + 12, y + 30, 2, C.red);
  dot(ctx, x + T - 12, y + 30, 2, C.red);
}

/** 角魔古祭壇（荒原）：黑石台＋兩支彎角＋暗紅符文。 */
export function hornAltar(ctx: Ctx, x: number, y: number): void {
  const cx = x + T / 2;
  shadow(ctx, cx + 3, y + T * 0.86, 22, 6);
  box(ctx, x + 6, y + 28, T - 12, 14, "#2e2622", OUT, 2, 2);
  for (const s of [-1, 1]) {
    ctx.beginPath();
    ctx.moveTo(cx + s * 12, y + 30);
    ctx.quadraticCurveTo(cx + s * 22, y + 8, cx + s * 8, y + 2);
    ctx.quadraticCurveTo(cx + s * 16, y + 12, cx + s * 6, y + 30);
    ctx.closePath();
    ctx.fillStyle = "#bfb0a4";
    ctx.fill();
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
  ctx.save();
  ctx.shadowColor = "#ff3a2a";
  ctx.shadowBlur = 6;
  ctx.strokeStyle = "#c83a2a";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.arc(cx, y + 35, 4, 0, TAU);
  ctx.moveTo(cx - 8, y + 35);
  ctx.lineTo(cx + 8, y + 35);
  ctx.stroke();
  ctx.restore();
}

/** 運輸車：鐵輪木車＋源晶碎片箱。 */
export function cart(ctx: Ctx, x: number, y: number): void {
  shadow(ctx, x + T / 2 + 4, y + T * 0.84, 24, 6);
  box(ctx, x + 4, y + 16, T - 8, 20, "#7a5a38", OUT, 2, 2);
  for (const px of [x + 12, x + T - 12]) {
    ctx.beginPath();
    ctx.arc(px, y + 38, 7, 0, TAU);
    ctx.fillStyle = "#5a5e60";
    ctx.fill();
    ctx.lineWidth = 1.8;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
  box(ctx, x + 14, y + 8, 22, 10, "#5a4030", OUT, 1.4, 1);
  glow(ctx, x + 25, y + 12, 10, "rgba(140,220,255,0.9)", 0.6);
  dot(ctx, x + 25, y + 12, 2.6, "#c8f0ff");
}

/** 石燈籠（realms.js）。 */
export function stoneLantern(ctx: Ctx, x: number, y: number): void {
  shadow(ctx, x + T / 2 + 3, y + T * 0.86, 13, 4, 0.35);
  const g = "#9aa39c";
  const rect = (rx: number, ry: number, w: number, h: number, fill: string, lw = 2, r = 2): void => box(ctx, rx, ry, w, h, fill, OUT, lw, r);
  rect(x + 18, y + 38, 16, 7, shade(g, 0.85));
  rect(x + 23, y + 26, 6, 12, g);
  rect(x + 17, y + 16, 18, 11, g);
  const lg = ctx.createRadialGradient(x + 26, y + 21, 0, x + 26, y + 21, 14);
  lg.addColorStop(0, rgba("#ffcf6a", 0.6));
  lg.addColorStop(1, rgba("#ffcf6a", 0));
  ctx.fillStyle = lg;
  ctx.beginPath();
  ctx.arc(x + 26, y + 21, 14, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "#ffcf6a";
  ctx.fillRect(x + 22, y + 18, 8, 6);
  ctx.beginPath();
  ctx.moveTo(x + 12, y + 16);
  ctx.lineTo(x + 26, y + 6);
  ctx.lineTo(x + 40, y + 16);
  ctx.closePath();
  ctx.fillStyle = shade(g, 0.75);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  rect(x + 24, y + 2, 4, 5, g, 1.5, 1);
}

/** 敵人腳下的紅色環（enemyArt.js 的 `ring`，非精英）。 */
export function enemyRing(ctx: Ctx, rx: number): void {
  ctx.save();
  ctx.globalAlpha = 0.3;
  ctx.fillStyle = "#d24a3a";
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 0.9;
  ctx.strokeStyle = "#d24a3a";
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.restore();
}
