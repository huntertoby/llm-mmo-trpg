// 場景物件的程式繪製（Phase 3-16a；移植自美術 PM 樣張 procedural.js 的 OBJECT_DRAW）。
// 每個物件畫成一張透明背景的離屏貼圖（座標以 ART_T ＝ 52 的虛擬格為單位）。
// 沒有畫法的新物件：灰色六角形（字 glyph 由繪圖端疊上），不會出錯。
import { PAL, rgba } from "./artPalette";
import { flame, roundRect, shadowEllipse, TAU, type Ctx } from "./artDraw";
import { rng } from "./artRandom";
import { cracks, type HpStage } from "./fieldFx";
import { drawLowWall } from "./lowWallArt";
import { CLOUD_OBJECTS } from "./cloudRidgeObjects";
import { pickThemed, themeKey, type ArtTheme, type LookTable, type RegionTable } from "./regionArt";
import { ART_T } from "./terrainArt";

const T = ART_T;

export interface ObjectArtSpec extends ArtTheme {
  kind: string;
  x: number;
  y: number;
  /** 左右鄰格也是同種物件（矮牆連起來）。 */
  joinL: boolean;
  joinR: boolean;
  /** 橋沿南北方向鋪（上下鄰是橋、左右不是）。 */
  vertical: boolean;
  flammable: boolean;
  /** 暫時物件還剩幾次環境回合（`expiresIn`）；永久物件為 `null`。外觀只分「最後 1 回合」與否（徽章另畫）。 */
  turnsLeft: number | null;
  /** 受損級距（見 `hpStageOf`）：0 ＞ 66%、1 ≤ 66%、2 ≤ 33%；沒有耐久的物件為 0。 */
  hpStage: HpStage;
}

/** 剩餘回合的外觀級距：0＝永久、1＝還有幾回合、2＝最後 1 回合（鍵只用級距，不用原始回合數）。 */
const turnsLevel = (s: ObjectArtSpec): number => (s.turnsLeft === null ? 0 : s.turnsLeft <= 1 ? 2 : 1);

export function objectArtKey(s: ObjectArtSpec): string {
  return [s.kind, s.x, s.y, +s.joinL, +s.joinR, +s.vertical, +s.flammable, turnsLevel(s), s.hpStage, themeKey(s)].join("|");
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

function lowWall(ctx: Ctx, s: ObjectArtSpec): void {
  drawLowWall(ctx, s);
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

// ---- 戰場效果新畫法（Phase 3-36b；移植自 docs/art/sample/fx.js）：冰牆、荊棘叢、倒塌物、薄冰 ----

const lastTurn = (s: ObjectArtSpec): boolean => s.turnsLeft !== null && s.turnsLeft <= 1;

function softShadow(ctx: Ctx, cx: number, cy: number, rx: number, ry: number, a = 0.32): void {
  ctx.fillStyle = `rgba(0,0,0,${a})`;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.fill();
}

/** 冰牆：半透明的冰晶塊（有高度、擋視線）；最後一回合開始融化（滴水、變透明、頂部變圓）。 */
function iceWall(ctx: Ctx, s: ObjectArtSpec): void {
  const melting = lastTurn(s);
  softShadow(ctx, T / 2 + 3, T * 0.82, T * 0.38, T * 0.12, 0.35);
  const a = melting ? 0.62 : 0.85;
  const top = melting ? T * 0.14 : T * 0.04;
  const base = T * 0.84;
  const l = T * 0.12;
  const rr = T * 0.88;
  // 晶體外形：三根高低不一的冰柱連成一塊
  const pts: ReadonlyArray<readonly [number, number]> = melting
    ? [[l, base], [l, top + 16], [l + 8, top + 6], [T * 0.42, top + 2], [T * 0.6, top + 8], [rr - 6, top + 10], [rr, top + 20], [rr, base]]
    : [[l, base], [l, top + 14], [l + 6, top + 4], [T * 0.34, top + 12], [T * 0.5, top], [T * 0.66, top + 10], [rr - 5, top + 6], [rr, top + 16], [rr, base]];
  ctx.save();
  ctx.beginPath();
  pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
  ctx.closePath();
  const g = ctx.createLinearGradient(l, top, rr, base);
  g.addColorStop(0, rgba("#e8fbff", a));
  g.addColorStop(0.5, rgba("#8fd8f0", a));
  g.addColorStop(1, rgba("#3f9cc8", a));
  ctx.fillStyle = g;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#163a52";
  ctx.stroke();
  ctx.clip();
  // 晶面：亮色斜線
  ctx.strokeStyle = rgba("#ffffff", 0.75);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(l + 7, base - 6);
  ctx.lineTo(l + 13, top + 14);
  ctx.moveTo(T * 0.5, base - 4);
  ctx.lineTo(T * 0.47, top + 8);
  ctx.stroke();
  ctx.strokeStyle = rgba("#1d5f86", 0.5);
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(T * 0.34, top + 12);
  ctx.lineTo(T * 0.36, base);
  ctx.moveTo(T * 0.66, top + 10);
  ctx.lineTo(T * 0.64, base);
  ctx.stroke();
  ctx.restore();
  if (melting) {
    // 水滴與底部水窪
    ctx.fillStyle = rgba("#4aa3ff", 0.55);
    ctx.beginPath();
    ctx.ellipse(T / 2, base + 2, T * 0.42, 4, 0, 0, TAU);
    ctx.fill();
    ctx.fillStyle = "#bfefff";
    for (const [dx, dy] of [[0.2, 0.62], [0.55, 0.7], [0.8, 0.58]] as const) {
      ctx.beginPath();
      ctx.ellipse(dx * T, dy * T, 1.6, 2.6, 0, 0, TAU);
      ctx.fill();
    }
  }
}

/** 荊棘叢：一團交纏的藤蔓＋尖刺＋小紅花；最後一回合枯萎（褐色、刺變少、沒有花）。 */
function thornWall(ctx: Ctx, s: ObjectArtSpec): void {
  const dry = lastTurn(s);
  const r = rng(s.x, s.y, 3);
  softShadow(ctx, T / 2 + 2, T * 0.74, T * 0.4, T * 0.14);
  const vine = dry ? "#7a5a30" : "#3f6a26";
  const vineHi = dry ? "#a07a44" : "#6aa040";
  // 底下一團暗色輪廓（讓荊棘從地面分出來）
  ctx.fillStyle = dry ? "#3a2a16" : "#1e3412";
  ctx.beginPath();
  ctx.ellipse(T / 2, T * 0.56, T * 0.42, T * 0.24, 0, 0, TAU);
  ctx.fill();
  ctx.lineCap = "round";
  for (let i = 0; i < 7; i++) {
    const sx = 6 + r() * (T - 12);
    const sy = T * 0.72;
    const ex = 6 + r() * (T - 12);
    const ey = T * 0.3 + r() * 8;
    ctx.strokeStyle = i % 2 ? vine : vineHi;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.quadraticCurveTo(r() * T, T * (0.2 + r() * 0.3), ex, ey);
    ctx.stroke();
    // 尖刺
    const n = dry ? 1 : 3;
    for (let k = 0; k < n; k++) {
      const tt = 0.25 + k * 0.25;
      const px = sx + (ex - sx) * tt;
      const py = sy + (ey - sy) * tt;
      ctx.fillStyle = dry ? "#d8c8a0" : "#f2ecd0";
      ctx.beginPath();
      ctx.moveTo(px - 2, py);
      ctx.lineTo(px, py - 6);
      ctx.lineTo(px + 2, py);
      ctx.fill();
    }
  }
  if (!dry) {
    ctx.fillStyle = "#c84a6a";
    for (let i = 0; i < 2; i++) {
      ctx.beginPath();
      ctx.arc(12 + r() * (T - 24), T * 0.38 + r() * 10, 2.4, 0, TAU);
      ctx.fill();
    }
  }
}

/** 倒塌物：大小石塊堆成的一堆（深色外框＋頂面亮色），一看就是「擋路、可躲」。 */
function rubble(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 5);
  softShadow(ctx, T / 2 + 3, T * 0.74, T * 0.42, T * 0.15, 0.4);
  const rocks = [
    [0.3, 0.62, 11],
    [0.62, 0.64, 12],
    [0.46, 0.46, 12],
    [0.76, 0.5, 8],
    [0.2, 0.46, 8],
    [0.5, 0.7, 7],
  ] as const;
  for (const [rx, ry, size] of rocks) {
    const cx = rx * T;
    const cy = ry * T;
    const n = 5 + Math.floor(r() * 2);
    const pts: Array<[number, number]> = [];
    for (let i = 0; i < n; i++) {
      const ang = (i / n) * TAU + r() * 0.5;
      const rad = size * (0.75 + r() * 0.3);
      pts.push([cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad * 0.8]);
    }
    ctx.beginPath();
    pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
    ctx.closePath();
    ctx.fillStyle = "#8d8376";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#2a241d";
    ctx.stroke();
    // 頂面亮色
    ctx.fillStyle = "#b9ae9c";
    ctx.beginPath();
    ctx.ellipse(cx - size * 0.15, cy - size * 0.3, size * 0.5, size * 0.28, -0.3, 0, TAU);
    ctx.fill();
  }
  // 碎屑
  ctx.fillStyle = "#6e665b";
  for (let i = 0; i < 6; i++) ctx.fillRect(6 + r() * (T - 12), T * 0.72 + r() * 8, 2.5, 2);
}

/** 薄冰：架在冰窟上的冰板；裂痕隨 HP 增加（級距 0／1／2 → 2／4／7 道），最後露出底下的黑水。 */
function thinIce(ctx: Ctx, s: ObjectArtSpec): void {
  const stage = s.hpStage;
  ctx.fillStyle = "#0e2a44";
  ctx.fillRect(0, 0, T, T);
  const r = rng(s.x, s.y, 9);
  ctx.beginPath();
  ctx.roundRect(3, 3, T - 6, T - 6, 8);
  ctx.fillStyle = rgba("#cdeeff", stage === 2 ? 0.62 : 0.85);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#e8fbff";
  ctx.stroke();
  // 冰下的暗影（看得出下面是冰窟）
  ctx.fillStyle = rgba("#0e2a44", 0.25);
  ctx.beginPath();
  ctx.ellipse(T / 2, T / 2, T * 0.26, T * 0.2, 0.3, 0, TAU);
  ctx.fill();
  // 裂痕：從中心放射
  const rays = stage === 0 ? 2 : stage === 1 ? 4 : 7;
  ctx.strokeStyle = stage === 2 ? "#0e2a44" : "#4a7a9a";
  ctx.lineWidth = stage === 2 ? 2 : 1.3;
  ctx.beginPath();
  for (let i = 0; i < rays; i++) {
    const ang = (i / rays) * TAU + r();
    let px = T / 2;
    let py = T / 2;
    ctx.moveTo(px, py);
    for (let k = 0; k < 3; k++) {
      px += Math.cos(ang + (r() - 0.5) * 0.8) * 7;
      py += Math.sin(ang + (r() - 0.5) * 0.8) * 7;
      ctx.lineTo(px, py);
    }
  }
  ctx.stroke();
  if (stage === 2) {
    // 破洞：露出黑水
    ctx.fillStyle = "#081a2c";
    ctx.beginPath();
    ctx.moveTo(T * 0.44, T * 0.42);
    ctx.lineTo(T * 0.58, T * 0.44);
    ctx.lineTo(T * 0.56, T * 0.58);
    ctx.lineTo(T * 0.42, T * 0.55);
    ctx.fill();
  }
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

/** 各區的物件畫法（區域 ID → 物件 ID → 畫法）；預設區不在表內，雲嶺（3-37b）已加入，其他區之後加。 */
export const REGION_OBJECT_DRAW: RegionTable<ObjectDrawer> = { cloud_ridge: CLOUD_OBJECTS };

/** `look` 覆寫的物件畫法（`"鍵=值"` → 物件 ID → 畫法）；目前沒有。 */
export const LOOK_OBJECT_DRAW: LookTable<ObjectDrawer> = {};

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

/** 受損裂痕的顏色與範圍（比例）；沒列的物件用預設。薄冰自己畫裂痕（依級距），不套通用裂痕。 */
const CRACKS: Readonly<Record<string, { color: string; box?: readonly [number, number, number, number] }>> = {
  ice_wall: { color: "#123048", box: [0.2, 0.15, 0.8, 0.8] },
  thorn_wall: { color: "#140c06" },
  rubble: { color: "#1a1612" },
};

export function drawObject(ctx: Ctx, s: ObjectArtSpec): void {
  (pickThemed(s, s.kind, REGION_OBJECT_DRAW, LOOK_OBJECT_DRAW) ?? OBJECT_DRAW[s.kind] ?? drawGenericObject)(ctx, s);
  if (s.hpStage > 0 && s.kind !== "thin_ice") {
    const style = CRACKS[s.kind];
    cracks(ctx, s.hpStage, s.x, s.y, style?.color, style?.box);
  }
  if (s.flammable && s.kind !== "wooden_bridge") flammableMark(ctx);
}
