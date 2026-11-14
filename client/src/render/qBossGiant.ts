// GB-4b：灰燼之心 3×3 巨型版（照 docs/art/sample/qBossGiant.js，`2ca9688b5` 之後；移植需求 docs/art/GB巨型頭目-移植需求.md 2～5 節）。
// A1 立繪（三階段 × 熔殼在／不在、熔殼脫落）、地面（3×3 陣營環、第 3 階段坑底紅光）、A2 部位格標示、A4 破壞演出，逐行搬成 TypeScript。
// 和樣張不同的地方（都不改畫法）：
// - 色票、`seedOf` 從遊戲端 import（`qBoss.ts` 的灰燼之心色票、`inkStyle.seedOf`）；殼片名稱和 1 格版 `qBoss.PLATES` 同一組（測試鎖住）。
// - 部位遮罩（滑過亮起、第 1 格白閃）**不用樣張的換色相減**（`partMask` 只是樣張取遮罩的手段，移植需求 3.5 第 4 條、第 7 節第 4 條）：
//   由畫法直接給——照常畫本體，只有那個部位的零件（噴口＝`vent()` 三支、殼縫＝`seam()` 兩條、核心＝`cavity()`＋`core()`）上色，
//   其他零件用 `destination-out` 擦掉（同 PB-1e `partLayer` 的做法），所以被後畫的零件蓋住的地方自然不算；描邊用圓盤膨脹（同 `band()`）。
// - 待機一圈首尾接上：`st.loop` 有值時振盪照整數次（同 `qBoss.ts` 的 `osc`／`cyc`）；樣張沒有這個參數，沒給時和樣張逐式相同。
// - 「破」字記號的放大同 `bossPartArt.popScale`（`minMarkScale(14, 12, 縮放)`，PB-1f；不 import bossPartArt 免得成環）；打不到原因小圓片的圖樣用遊戲端 `qIcon/parts.ts` 的 `glyph`。
// - 沒有 DOM（vitest）時剪影層退回直接平塗（同 `qBoss.ts` 的 `layer`）。
// 座標：模型像素（1 格 48），原點＝錨點＝3×3 南排的南緣中點（中心格中心往南 72）；y 往上是負。確定性：沒有 Math.random，動畫只吃 st.t。
import { TAU, type Ctx } from "./artDraw";
import { darken, lighten, mix } from "./color";
import { seedOf } from "./inkStyle";
import { DOLL_SCALE } from "./paperdoll";
import { drawCreatureFx } from "./qCreatureAnim";
import type { CreatureFx } from "./creaturePose";
import { hasDom, qLayer, QC_OUT, type QLayerOpt } from "./qCreatureLayer";
import { ASH, BOSS_FIELD_SCALE, BOSS_GLOW_A, BOSS_GLOW_W, bossClipOf, bossPlan, cyc, osc } from "./qBoss";
import { MIN_BREAK_POP_FONT_PX, minMarkScale } from "./minMark";
import { blit } from "./qIcon/core";
import { glyph as partGlyph, BOX as PART_BOX } from "./qIcon/parts";

type P2 = readonly [number, number];
type Box = readonly [number, number, number, number];

/** 一格（模型 px，`battle/geometry.ts` TILE_SIZE）。 */
export const GT = 48;
/** qBoss 1 單位在戰場上的模型像素（`(T/52) × DOLL_SCALE × huge`）≈ 1.566；線寬、外框、外光照這個換算（移植需求 2.3）。 */
export const GG = (GT / 52) * DOLL_SCALE * BOSS_FIELD_SCALE;
const OUT = QC_OUT;
const OW = 1.3 * GG;
const GLOW_W = BOSS_GLOW_W * GG;
const GLOW_A = BOSS_GLOW_A;
const GOLD = "#ffbf3a";
/** 圖層範圍（模型 px）。 */
export const GIANT_BOX: Box = [-96, -214, 96, 16];
/** 錨點往南離中心格中心多遠（模型 px）。 */
export const GIANT_ANCHOR_DY = GT * 1.5;
/** 本體含外光的外接框（模型 px，`giant_boss_shots.py --anchor`，六種外觀相同）。 */
export const GIANT_BOUNDS = { x0: -79.3, y0: -159.7, x1: 79.3, y1: 2.5 } as const;

const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
const num = (v: number | undefined, d: number): number => (typeof v === "number" && Number.isFinite(v) ? v : d);
const rnd = (key: string, k = 0): number => (seedOf(`${key}:${k}`) % 10000) / 10000;
const light = lighten;
const dark = darken;

// ---- 色（照 qBoss 灰燼之心；沒有新色票） ----
const { BASALT, BASALT_L, LAVA, LAVA_HOT, CORE, EMBER } = ASH;
const CAVE = mix(BASALT, OUT, 0.55);
const COOL = "#2a221e";
const PLUG = "#3e332e";
const seamOf = (c: string): string => mix(c, OUT, 0.55);
const LW = 0.6 * GG;

/** 部位遮罩模式（`maskPart`）：只有這個部位的零件上色，其他零件擦掉。`null`＝照常畫。 */
let MASK: GiantPart | null = null;
/** 遮罩只要核心的晶體、不含殼窩（GB-4c，美術 GB-4b 可修 2：破壞第 1 格白閃只用 `core()`；滑過亮起照舊含殼窩光）。 */
let MASK_CRYSTAL = false;
/** 畫一個零件前：遮罩模式時，這個部位的零件照常畫，其他零件改成擦掉。`cavity`＝核心的殼窩（`MASK_CRYSTAL` 時也擦掉）。 */
function zone(g: Ctx, part: GiantPart | null, cavity = false): void {
  if (MASK === null) return;
  const on = part === MASK && !(cavity && MASK_CRYSTAL);
  g.globalCompositeOperation = on ? "source-over" : "destination-out";
}

function path(g: Ctx, pts: readonly P2[]): void {
  g.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.closePath();
}
function poly(g: Ctx, pts: readonly P2[], c: string, opt: { line?: boolean; lw?: number } = {}): void {
  path(g, pts);
  g.fillStyle = c;
  g.fill();
  if (opt.line !== false) {
    g.strokeStyle = seamOf(c);
    g.lineWidth = opt.lw ?? LW;
    g.lineJoin = "round";
    g.stroke();
  }
}
function ell(g: Ctx, x: number, y: number, rx: number, ry: number, c: string, opt: { line?: boolean; lw?: number; rot?: number } = {}): void {
  g.beginPath();
  g.ellipse(x, y, rx, ry, opt.rot ?? 0, 0, TAU);
  g.fillStyle = c;
  g.fill();
  if (opt.line !== false) {
    g.strokeStyle = seamOf(c);
    g.lineWidth = opt.lw ?? LW;
    g.stroke();
  }
}
function line(g: Ctx, pts: readonly P2[], w: number, c: string): void {
  g.save();
  g.strokeStyle = c;
  g.lineWidth = w;
  g.lineCap = "round";
  g.lineJoin = "round";
  g.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.stroke();
  g.restore();
}
/** 破壞演出第 2 格「裂開」：部位上的亮金白裂紋。 */
function crackLines(g: Ctx, list: ReadonlyArray<readonly P2[]>, k = 1): void {
  for (const pts of list) {
    line(g, pts, 2.2 * k, "#ffe08a");
    line(g, pts, 0.9 * k, "#ffffff");
  }
}
/** 平塗光暈：3 圈半透明同心橢圓（qBoss flatGlow）。 */
function flatGlow(ctx: Ctx, x: number, y: number, r: number, c: string, a: number, ry = r): void {
  ctx.save();
  ctx.fillStyle = c;
  for (const [k, al] of [[1, 0.16], [0.72, 0.2], [0.46, 0.26]] as const) {
    ctx.globalAlpha = al * a;
    ctx.beginPath();
    ctx.ellipse(x, y, r * k, ry * k, 0, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}
function rrect(ctx: Ctx, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  const q = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.moveTo(x + q, y);
  ctx.arcTo(x + w, y, x + w, y + h, q);
  ctx.arcTo(x + w, y + h, x, y + h, q);
  ctx.arcTo(x, y + h, x, y, q);
  ctx.arcTo(x, y, x + w, y, q);
  ctx.closePath();
}
/** 有 DOM：剪影外框層；沒有（測試）：直接平塗。 */
function layer(ctx: Ctx, box: Box, draw: (g: Ctx) => void, o: QLayerOpt): void {
  if (hasDom() && typeof ctx.getTransform === "function") {
    qLayer(ctx, box, draw, o);
    return;
  }
  ctx.save();
  draw(ctx);
  ctx.restore();
}

// ---- 佔格與部位綁格（PhaseGB 計畫 D15、T11、T20） ----
export type GiantPart = "vent" | "seam" | "core";
export const GIANT_PARTS: readonly GiantPart[] = ["vent", "seam", "core"];
/** 3×3 每一格屬於哪個部位：[列（0 北、1 中、2 南）][欄（0 西、1 中、2 東）]。body＝前殼（本體）。 */
export const TILE_PART: ReadonlyArray<readonly (GiantPart | "body")[]> = [["vent", "vent", "vent"], ["seam", "core", "seam"], ["body", "body", "body"]];
/** 一格的左上角（模型 px、相對錨點）。 */
export const tileXY = (row: number, col: number): P2 => [(col - 1) * GT - GT / 2, -3 * GT + row * GT];
/** 伺服器的部位 ID → 畫法的部位（`content/units/ashen_heart.yaml`）。 */
export const GIANT_PART_OF: Readonly<Record<string, GiantPart>> = { vent: "vent", shell_seam: "seam", core: "core" };

// ---- 噴口（北排） ----
export const VENTS = [
  { x: -46, base: -90, top: -136, bw: 23, tw: 10, tilt: -0.16 },
  { x: 46, base: -90, top: -136, bw: 23, tw: 10, tilt: 0.16 },
  { x: 0, base: -96, top: -148, bw: 25, tw: 11, tilt: 0 },
] as const;
type Vent = (typeof VENTS)[number];
function vent(g: Ctx, v: Vent, S: GiantS): void {
  const h = v.base - v.top;
  const sealed = S.ventSealed;
  g.save();
  g.translate(v.x, v.base);
  g.rotate(v.tilt);
  const bw = v.bw;
  const tw = v.tw;
  const body = (q: Ctx): void => {
    q.beginPath();
    q.moveTo(-bw, 6);
    q.quadraticCurveTo(-tw * 0.95, -h * 0.3, -tw, -h);
    q.lineTo(tw, -h);
    q.quadraticCurveTo(tw * 0.95, -h * 0.3, bw, 6);
    q.closePath();
  };
  body(g);
  g.fillStyle = BASALT;
  g.fill();
  g.strokeStyle = seamOf(BASALT);
  g.lineWidth = LW;
  g.stroke();
  g.save();
  body(g);
  g.clip();
  g.fillStyle = light(BASALT, 0.12);
  g.beginPath();
  g.moveTo(-bw - 2, 6);
  g.quadraticCurveTo(-tw * 1.2, -h * 0.3, -tw + 2, -h);
  g.lineTo(-tw * 0.15, -h);
  g.quadraticCurveTo(-tw * 0.4, -h * 0.4, -bw * 0.3, 6);
  g.closePath();
  g.fill();
  g.restore();
  const wAt = (yy: number): number => {
    const t = Math.min(1, Math.max(0, -yy / h));
    const u = 1 - t;
    return u * u * bw + 2 * u * t * tw * 0.95 + t * t * tw;
  };
  for (const [yy, n] of [[-h * 0.14, 3], [-h * 0.46, 2]] as const) {
    const hw = wAt(yy);
    for (let k = 0; k < n; k++) {
      const x = -hw + (2 * hw * (k + 0.5)) / n;
      const rx = hw / n + 2.2;
      const ry = 5.2 - n * 0.4;
      ell(g, x, yy, rx, ry, BASALT_L);
      g.save();
      g.beginPath();
      g.ellipse(x, yy, rx, ry, 0, 0, TAU);
      g.clip();
      ell(g, x - rx * 0.3, yy - ry * 0.35, rx * 0.36, ry * 0.3, light(BASALT_L, 0.22), { line: false });
      ell(g, x + rx * 0.3, yy + ry * 0.55, rx * 0.6, ry * 0.4, dark(BASALT_L, 0.14), { line: false });
      g.restore();
    }
  }
  ell(g, 0, -h, tw + 2.6, 5.8, BASALT_L);
  for (const [dx, r] of [[-tw - 1, 2.6], [tw + 0.6, 2.2], [-tw * 0.3, 2]] as const) ell(g, dx, -h - 3.6 + Math.abs(dx) * 0.08, r + 0.6, r, BASALT_L);
  if (sealed) {
    // 破＝封住（A4 定稿）：冷殼塞住口、頂出口緣一點，兩道灰裂；口緣溢出的熔岩也冷成黑色的硬流痕
    ell(g, 0, -h + 0.4, tw - 0.6, 3.6, COOL);
    g.fillStyle = PLUG;
    g.beginPath();
    g.moveTo(-tw + 1.2, -h + 0.8);
    g.quadraticCurveTo(-tw * 0.55, -h - 4.6, 0, -h - 4.4);
    g.quadraticCurveTo(tw * 0.6, -h - 4.4, tw - 1.2, -h + 0.8);
    g.closePath();
    g.fill();
    g.strokeStyle = seamOf(PLUG);
    g.lineWidth = LW;
    g.stroke();
    ell(g, -tw * 0.32, -h - 2.4, tw * 0.3, 1.1, "#6e6259", { line: false });
    line(g, [[-tw * 0.55, -h - 0.4], [-tw * 0.15, -h - 2.6], [tw * 0.05, -h - 0.6], [tw * 0.4, -h - 2.8]], 0.9, "#7a706a");
    for (const [dx, len] of [[-tw * 0.55, 7], [tw * 0.35, 10]] as const) {
      g.fillStyle = COOL;
      g.beginPath();
      g.moveTo(dx - 2, -h + 2.5);
      g.quadraticCurveTo(dx - 2.4, -h + 2.5 + len * 0.6, dx, -h + 2.5 + len * 0.85);
      g.quadraticCurveTo(dx + 2.4, -h + 2.5 + len * 0.6, dx + 2, -h + 2.5);
      g.closePath();
      g.fill();
      g.fillStyle = "#5a504a";
      g.fillRect(dx - 0.5, -h + 3, 1, len * 0.45);
    }
  } else {
    const hot = S.ventFlare ? 1 : clamp(0.55 + 0.45 * S.breath * (S.phase === 1 ? 0.6 : 1));
    ell(g, 0, -h + 0.4, tw - 0.6, 3.6, LAVA);
    ell(g, 0, -h + 0.1, tw - 5, 1.8, mix(LAVA, LAVA_HOT, hot), { line: false });
    const L = S.phase === 3 ? 1.9 : 1;
    for (const [dx, len] of [[-tw * 0.55, 7], [tw * 0.35, 10]] as const) {
      g.fillStyle = LAVA;
      g.beginPath();
      g.moveTo(dx - 2, -h + 2.5);
      g.quadraticCurveTo(dx - 2.4, -h + 2.5 + len * L * 0.7, dx, -h + 2.5 + len * L);
      g.quadraticCurveTo(dx + 2.4, -h + 2.5 + len * L * 0.7, dx + 2, -h + 2.5);
      g.closePath();
      g.fill();
      g.fillStyle = LAVA_HOT;
      g.fillRect(dx - 0.5, -h + 3, 1, len * L * 0.55);
    }
  }
  if (!sealed && S.spout > 0) {
    const s = S.spout;
    const H = 26 + 34 * s;
    g.fillStyle = LAVA;
    g.beginPath();
    g.moveTo(-tw + 3, -h);
    g.quadraticCurveTo(-tw - 2, -h - H * 0.6, 0, -h - H);
    g.quadraticCurveTo(tw + 2, -h - H * 0.6, tw - 3, -h);
    g.closePath();
    g.fill();
    ell(g, 0, -h - H * 0.45, 3.4, H * 0.3, LAVA_HOT, { line: false });
  }
  if (S.crackPart === "vent")
    crackLines(g, [
      [[-tw * 0.3, -h + 3], [-tw * 0.75, -h * 0.74], [-tw * 0.2, -h * 0.52], [-bw * 0.4, -h * 0.24]],
      [[tw * 0.45, -h + 3], [tw * 0.8, -h * 0.66], [tw * 0.3, -h * 0.42]],
    ]);
  g.restore();
}

// ---- 背殼（岩丘，本體） ----
const DOME: readonly P2[] = [[-70, -3], [-73, -18], [-69, -36], [-72, -56], [-69, -76], [-60, -94], [-42, -106], [-20, -111], [0, -112], [20, -111], [42, -106], [60, -94], [69, -76], [72, -56], [69, -36], [73, -18], [70, -3]];
function domePath(g: Ctx): void {
  g.beginPath();
  g.moveTo(...DOME[0]!);
  for (let i = 1; i < DOME.length - 1; i++) {
    const [x, y] = DOME[i]!;
    const [nx, ny] = DOME[i + 1]!;
    g.quadraticCurveTo(x, y, (x + nx) / 2, (y + ny) / 2);
  }
  g.lineTo(...DOME[DOME.length - 1]!);
  g.closePath();
}
const DOME_SHELLS: ReadonlyArray<readonly [number, number, number, number, number]> = [[-24, -101, 12, 6.5, -0.3], [24, -101, 12, 6.5, 0.3], [-44, -78, 6.5, 8.5, -0.2], [44, -78, 6.5, 8.5, 0.2]];
function dome(g: Ctx): void {
  domePath(g);
  g.fillStyle = BASALT;
  g.fill();
  g.save();
  domePath(g);
  g.clip();
  ell(g, -30, -100, 36, 12, light(BASALT, 0.12), { rot: -0.22, line: false });
  ell(g, 46, -52, 30, 44, dark(BASALT, 0.16), { rot: 0.1, line: false });
  for (const [x, y, rx, ry, r] of DOME_SHELLS) smallShell(g, x, y, rx, ry, r);
  g.restore();
  for (const s of [-1, 1]) smallShell(g, s * 67, -67, 6, 10, s * -0.12);
}
/** 小甲蟲背（qBoss 底座甲蟲背）：圓背甲＋中線＋左上亮面。 */
function smallShell(g: Ctx, x: number, y: number, rx: number, ry: number, r: number): void {
  ell(g, x, y, rx, ry, BASALT_L, { rot: r });
  g.save();
  g.translate(x, y);
  g.rotate(r);
  line(g, [[0, -ry + 1], [0, ry - 1]], 0.9 * GG * 0.7, OUT);
  ell(g, -rx * 0.35, -ry * 0.35, rx * 0.3, ry * 0.25, light(BASALT_L, 0.22), { line: false });
  g.restore();
}

// ---- 殼縫（中排東西，兩格同一個部位） ----
export const SEAM: readonly P2[] = [[54, -93], [58, -83], [55, -72], [60, -62], [57, -52], [61, -44]];
const SEAM_COLD = ["#1a1310", "#2e2420", "#7a6e66"] as const;
function seam(g: Ctx, s: number, S: GiantS): void {
  const pts: P2[] = SEAM.map(([x, y]) => [s * x, y]);
  const cool = S.seamCool;
  const hot = S.crackPart === "seam";
  const heat = clamp(0.45 + 0.55 * S.breath);
  const oc = cool > 0 ? mix(EMBER, SEAM_COLD[0], cool) : EMBER;
  const ic = hot ? LAVA_HOT : cool > 0 ? mix(LAVA, SEAM_COLD[1], cool) : LAVA;
  if (cool < 1) {
    g.save();
    g.globalAlpha = 0.22 * (1 - cool) * (hot ? 1.8 : 1);
    line(g, pts, hot ? 13 : 10, hot ? LAVA_HOT : LAVA);
    g.restore();
  }
  for (const [a, b] of [[1, [s * 64, -88]], [3, [s * 52, -60]]] as const) {
    line(g, [pts[a]!, b], 3.4, oc);
    line(g, [pts[a]!, b], 1.5, ic);
  }
  line(g, pts, 6.4, oc);
  line(g, pts, 3.8, ic);
  if (cool <= 0) line(g, pts, 1.5, hot ? "#ffffff" : mix(LAVA, LAVA_HOT, heat));
  else if (cool < 1) {
    g.save();
    g.globalAlpha = 1 - cool;
    line(g, pts, 1.5, mix(LAVA, LAVA_HOT, heat));
    g.restore();
  } else {
    // 破掉定稿：縫裡凝成黑殼，受光那側一條灰白的冷殼邊＋兩粒冷渣
    line(g, pts.map(([x, y]) => [x - 1.1, y - 0.4] as const), 0.9, SEAM_COLD[2]);
    for (const [x, y] of [[58, -78], [57, -56]] as const) ell(g, s * x, y, 1.3, 1, SEAM_COLD[2], { line: false });
  }
}

// ---- 殼窩、殼蓋、核心（中心格） ----
const CX = 0;
const CY = -72;
const CAV_RX = 28;
const CAV_RY = 24;
const CORE_PTS: readonly P2[] = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]];
const CK = GG * 1.05;
const CORE_DEAD = "#7a5a46";
function cavity(g: Ctx, S: GiantS): void {
  ell(g, CX, CY, CAV_RX + 3.5, CAV_RY + 3.5, BASALT_L);
  ell(g, CX, CY, CAV_RX, CAV_RY, CAVE);
  g.save();
  g.beginPath();
  g.ellipse(CX, CY, CAV_RX, CAV_RY, 0, 0, TAU);
  g.clip();
  ell(g, CX, CY + 18, 20, 8, mix(CAVE, LAVA, 0.55), { line: false });
  if (S.phase >= 2) flatGlow(g, CX, CY, 28, CORE, (0.55 + 0.45 * S.breath) * (1 - S.die) * S.coreLight);
  if (S.charge > 0) flatGlow(g, CX, CY - 2, 30, LAVA_HOT, 0.7 * S.charge);
  g.restore();
}
function core(g: Ctx, S: GiantS): void {
  const s = (1 + 0.06 * S.breath) * (1 - 0.55 * S.die) * S.coreScale;
  g.save();
  g.translate(CX, CY - S.inhale * 2);
  g.scale(CK * s, CK * s);
  let c = mix(CORE, "#fff4d0", 0.35 * S.breath + 0.4 * S.crack);
  if (S.die > 0) c = mix(c, "#5a4a44", S.die);
  if (S.coreDull > 0) c = mix(c, CORE_DEAD, S.coreDull);
  const lw = LW / CK;
  poly(g, CORE_PTS, c, { lw });
  g.save();
  path(g, CORE_PTS);
  g.clip();
  poly(g, [[0, -15], [-9, -9], [-11, 3], [1, 0]], light(c, 0.35), { line: false });
  poly(g, [[11, 4], [4, 13], [1, 0]], dark(c, 0.12), { line: false });
  g.restore();
  g.fillStyle = S.coreDull > 0 ? mix("#ffffff", light(CORE_DEAD, 0.3), 0.6 * S.coreDull) : "#ffffff";
  g.fillRect(-5, -9, 2.2, 4.4);
  g.fillRect(-2, -10.4, 1.4, 1.4);
  if (S.crackPart === "core")
    crackLines(
      g,
      [
        [[-2, -13], [2, -5], [-1, 2], [3, 10]],
        [[9, -6], [4, -1], [8, 5]],
        [[-9, -2], [-4, 1], [-7, 8]],
      ],
      (0.8 / CK) * GG,
    );
  if (S.coreBroken) {
    for (const pts of [
      [[-2, -12], [2, -4], [-1, 3], [3, 10]],
      [[8, -6], [3, -2], [7, 6]],
      [[-9, -3], [-4, 0], [-6, 7]],
    ] as const)
      line(g, pts, 1.6, "#2a1a14");
    g.fillStyle = LAVA;
    g.fillRect(1.2, -3.6, 1.6, 1.6);
  }
  if (S.crack > 0 && !S.coreBroken) {
    g.save();
    g.globalAlpha = clamp(S.crack);
    line(g, [[-2, -12], [2, -4], [-1, 3], [3, 10]], 1.6 * 0.8, "#ffffff");
    line(g, [[8, -6], [3, -2], [7, 6]], 1.3 * 0.8, "#fff4c0");
    g.restore();
  }
  g.restore();
}
/** 殼蓋：兩片甲蟲殼在殼窩前合起來（第 1 階段），中縫透出核心的光；第 2 階段起往兩側掀開。open 0～1。 */
function lid(g: Ctx, S: GiantS, open: number): void {
  const glow = mix(LAVA, LAVA_HOT, clamp(0.3 + 0.7 * S.breath));
  if (open < 1) {
    g.save();
    g.globalAlpha = 1 - open;
    line(g, [[CX, CY - CAV_RY + 4], [CX - 1.5, CY - 6], [CX + 1.2, CY + 7], [CX, CY + CAV_RY - 5]], 5, glow);
    g.restore();
  }
  for (const s of [-1, 1]) {
    g.save();
    g.translate(CX + s * (CAV_RX + 1), CY);
    g.scale(1 - 0.62 * open, 1);
    g.translate(-s * (CAV_RX + 1), 0);
    const half: P2[] = [];
    for (let i = 0; i <= 12; i++) {
      const a = -Math.PI / 2 + (i / 12) * Math.PI;
      half.push([s * Math.cos(a) * (CAV_RX + 1.5), Math.sin(a) * (CAV_RY + 1.5)]);
    }
    half.push([s * 2.2, CAV_RY - 4], [s * 1.2, 7], [s * 3.2, -6], [s * 2, -CAV_RY + 5]);
    poly(g, half, BASALT_L);
    g.save();
    path(g, half);
    g.clip();
    ell(g, s * 14, -9, 8, 9, s < 0 ? light(BASALT_L, 0.2) : dark(BASALT_L, 0.1), { line: false, rot: s * 0.3 });
    for (const yy of [-8, 7]) line(g, [[s * 4, yy], [s * 25, yy + 3]], 0.9 * GG * 0.7, OUT);
    g.restore();
    g.restore();
  }
}

// ---- 前殼（南排三隻熔岩甲蟲，本體） ----
export const BEETLES = [
  { x: -47, y: -36, rx: 25, ry: 20, rot: -0.1 },
  { x: 47, y: -36, rx: 25, ry: 20, rot: 0.1 },
  { x: 0, y: -35, rx: 27, ry: 21, rot: 0 },
] as const;
function beetle(g: Ctx, b: (typeof BEETLES)[number], S: GiantS): void {
  g.save();
  g.translate(b.x, b.y);
  g.rotate(b.rot);
  ell(g, 0, 0, b.rx, b.ry, BASALT_L);
  g.save();
  g.beginPath();
  g.ellipse(0, 0, b.rx, b.ry, 0, 0, TAU);
  g.clip();
  ell(g, -b.rx * 0.36, -b.ry * 0.4, b.rx * 0.36, b.ry * 0.26, light(BASALT_L, 0.22), { line: false, rot: -0.3 });
  ell(g, b.rx * 0.4, b.ry * 0.45, b.rx * 0.5, b.ry * 0.35, dark(BASALT_L, 0.14), { line: false });
  g.restore();
  line(g, [[0, -b.ry + 1.2], [0, b.ry - 1.2]], 0.9 * GG, OUT);
  const z: P2[] = [[-b.rx * 0.62, 6], [-b.rx * 0.32, 2.5], [-b.rx * 0.08, 7], [b.rx * 0.2, 3], [b.rx * 0.48, 7.5], [b.rx * 0.66, 4]];
  const heat = S.phase === 3 ? 0.6 + 0.4 * S.breath : 0.15 + 0.2 * S.breath;
  line(g, z, 2 * GG, EMBER);
  line(g, z, 1 * GG, mix(LAVA, LAVA_HOT, heat));
  const hy = b.ry + 1;
  for (const s of [-1, 1])
    poly(
      g,
      [
        [s * 4.6, hy + 3.6],
        [s * 9.4, hy + 7.6],
        [s * 6.6, hy + 9],
        [s * 2.8, hy + 5.6],
      ],
      dark(BASALT, 0.1),
    );
  ell(g, 0, hy, 10.5, 6.4, BASALT);
  ell(g, -3.4, hy - 2.6, 3.6, 1.6, light(BASALT, 0.16), { line: false });
  for (const s of [-1, 1]) {
    g.fillStyle = OUT;
    g.fillRect(s * 4.2 - 2, hy - 1.4, 4, 3.6);
    g.fillStyle = mix(LAVA, LAVA_HOT, 0.5 + 0.5 * S.breath);
    g.fillRect(s * 4.2 - 1.3, hy - 0.7, 2.6, 2.4);
  }
  g.restore();
}

// ---- 熔殼殼片（狀態 molten_shell）：名稱和 qBoss.PLATES 同一組（雜湊一樣）；位置放大圍住殼窩 ----
/** [名稱, x, y, 旋轉, 寬, 高]（模型 px）。 */
export const GIANT_PLATES: ReadonlyArray<readonly [string, number, number, number, number, number]> = [
  ["p-back-l", -24, -89, -0.5, 26, 17],
  ["p-back-r", 24, -89, 0.5, 26, 17],
  ["p-top", 0, -92, 0, 28, 16],
  ["p-left", -31, -72, -0.9, 22, 19],
  ["p-right", 31, -72, 0.9, 22, 19],
  ["p-low-l", -20, -54, -0.3, 26, 16],
  ["p-low-r", 20, -54, 0.3, 26, 16],
  ["p-front", 0, -59, 0, 29, 16],
  ["p-mid-l", -13, -79, -0.2, 21, 16],
  ["p-mid-r", 13, -79, 0.2, 21, 16],
];
function plate(g: Ctx, w: number, h: number, heat: number): void {
  ell(g, 0, 0, w / 2, h / 2, BASALT_L);
  g.save();
  g.beginPath();
  g.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU);
  g.clip();
  ell(g, -w * 0.16, -h * 0.18, w * 0.22, h * 0.16, light(BASALT_L, 0.22), { line: false, rot: -0.3 });
  g.restore();
  line(g, [[0, -h / 2 + 1.2], [0, h / 2 - 1.2]], 0.9 * GG, OUT);
  const z: P2[] = [[-w * 0.34, 0.9], [-w * 0.17, -1.8], [0, 1.5], [w * 0.17, -1.5], [w * 0.34, 1.2]];
  line(g, z, 2 * GG, EMBER);
  line(g, z, 1 * GG, mix(LAVA, LAVA_HOT, clamp(heat)));
}
export interface PlateAt {
  x: number;
  y: number;
  r: number;
  a: number;
  s: number;
}
/**
 * 殼片的掛點：熔殼在＝貼著（第 2、3 階段＝往外撐開），隨呼吸張開；不在＝依名稱雜湊往北彈起、飛過噴口落進北邊岩漿，
 * 後 40% 邊縮小邊淡出；脫落完（breakT ≥ 1）回傳 `null`（不畫，南排不留殼片）。
 */
export function giantPlateAnchor(p: (typeof GIANT_PLATES)[number], shell: number, bt: number, breath: number, open = false): PlateAt | null {
  const [key, x, y, r] = p;
  if (shell > 0) {
    const o = 0.6 * breath;
    const k = open ? 1.42 : 1;
    const px = CX + (x - CX) * k;
    const py = CY + (y - CY) * (open ? 1.2 : 1);
    return { x: px * (1 + 0.02 * o), y: py - o * 0.9, r: r * (open ? 1.25 : 1), a: 1, s: 1 };
  }
  if (bt >= 1) return null;
  const dir = Math.sign(x || rnd(key) - 0.5) || 1;
  const spin = (rnd(key, 3) - 0.5) * 6;
  const fx = x * 1.15 + dir * (4 + 14 * rnd(key, 1));
  const fy = -162 - 18 * rnd(key, 4);
  const hop = 22 + 18 * rnd(key, 2);
  const u = clamp(bt);
  const fade = clamp((u - 0.6) / 0.4);
  return { x: x + (fx - x) * u, y: y + (fy - y) * u - hop * Math.sin(Math.PI * u), r: r + spin * u, a: 1 - fade, s: 1 - 0.4 * fade };
}
/** 殼片中心離開佔格（北緣以北、或兩側 |x| > 72）＝不屬本體圖層：自己包黑外框、不吃頭目金外光（A4 可修 B）。 */
export const plateFree = (A: PlateAt): boolean => A.y < -144 || Math.abs(A.x) > 72;
const flyOrder = (bt: number): Array<(typeof GIANT_PLATES)[number]> =>
  [...GIANT_PLATES].sort((a, b) => (giantPlateAnchor(a, 0, bt, 0)?.y ?? 0) - (giantPlateAnchor(b, 0, bt, 0)?.y ?? 0));
function freePlates(ctx: Ctx, S: GiantS): void {
  if (S.shell > 0 || S.bt >= 1) return;
  for (const p of flyOrder(S.bt)) {
    const A = giantPlateAnchor(p, 0, S.bt, 0, false);
    if (A === null || A.a <= 0 || !plateFree(A)) continue;
    layer(
      ctx,
      GIANT_BOX,
      (g) => {
        g.translate(A.x, A.y);
        g.rotate(A.r);
        g.scale(A.s, A.s);
        plate(g, p[4], p[5], 0.12);
      },
      { ow: OW, alpha: A.a },
    );
  }
}

// ---- 狀態 ----
/** 破壞演出的一格（k：0 命中、1 裂開、2 斷開、3 落地、4 定格；side：殼縫被打中的那一側，−1 西、1 東）。 */
export interface GiantFx {
  part: GiantPart;
  k: number;
  side?: number;
}
export interface GiantState {
  phase?: number;
  /** 熔殼在不在（0～1；預設第 1 階段在、其他不在）。 */
  shell?: number;
  /** 熔殼脫落進度（0～1）。 */
  breakT?: number;
  /** 毫秒（呼吸、熔毀裂紋閃爍）。 */
  t?: number;
  /** 待機一圈的進度（0～1）；有值時振盪照整數次（首尾接上）。 */
  loop?: number;
  inhale?: number;
  spout?: number;
  /** 蓄力光（熔心爆蓄力、吸氣中；火焰箭的核心光）。 */
  charge?: number;
  dieT?: number;
  broken?: Partial<Record<GiantPart, boolean>>;
  fx?: GiantFx | null;
}
/** 破壞演出五格的參數（移植需求 5.2；第 5 格＝破壞後定稿）。 */
export const BRK = {
  ms: [80, 80, 160, 160, 0],
  seamCool: [0, 0, 0.6, 1, 1],
  coreScale: [1, 0.88, 0.7, 0.86, 0.92],
  coreDull: [0, 0.15, 0.55, 0.7, 0.7],
  coreLight: [1, 0.7, 0.3, 0.25, 0.25],
  charge: [1, 0.6, 0.15, 0, 0],
  inhale: [1, 0.6, 0, 0, 0],
  /** 第 1 階段殼縫破：熔殼殼片的脫落進度（移植需求 5.2 表：第 3 格 0.35、第 4 格 0.72）。 */
  breakT: [0, 0, 0.35, 0.72, 1],
} as const;
export interface GiantS {
  t: number;
  phase: 1 | 2 | 3;
  shell: number;
  bt: number;
  breath: number;
  crack: number;
  inhale: number;
  spout: number;
  die: number;
  lp: number | undefined;
  broken: Partial<Record<GiantPart, boolean>>;
  fx: Required<GiantFx> | null;
  crackPart: GiantPart | null;
  ventSealed: boolean;
  ventFlare: boolean;
  seamCool: number;
  coreBroken: boolean;
  coreScale: number;
  coreDull: number;
  coreLight: number;
  charge: number;
}
function fxOf(st: GiantState): Required<GiantFx> | null {
  const f = st.fx;
  if (f == null || !["vent", "seam", "core"].includes(f.part)) return null;
  return { part: f.part, k: Math.max(0, Math.min(4, Math.round(num(f.k, 0)))), side: f.side === -1 ? -1 : 1 };
}
/** 狀態 → 畫法參數（樣張 `stateOf`）。 */
export function giantStateOf(st: GiantState = {}): GiantS {
  const t = num(st.t, 0);
  const lp = st.loop;
  const phase: 1 | 2 | 3 = st.phase === 2 || st.phase === 3 ? st.phase : 1;
  const shell = clamp(num(st.shell, phase === 1 ? 1 : 0));
  const bt = clamp(num(st.breakT, shell > 0 ? 0 : 1));
  const broken = st.broken ?? {};
  const fx = fxOf(st);
  const K = fx === null ? 0 : fx.k;
  const is = (p: GiantPart): boolean => fx !== null && fx.part === p;
  const coreTab = (row: readonly number[], done: number, base: number): number => (is("core") ? row[K]! : broken.core === true ? done : base);
  return {
    t,
    phase,
    shell,
    bt,
    lp,
    breath: 0.5 + 0.5 * Math.sin(osc(t, 420, lp)),
    crack: phase === 3 ? 0.6 + 0.4 * Math.sin(osc(t, 160, lp)) : 0,
    inhale: is("core") ? BRK.inhale[K]! : clamp(num(st.inhale, 0)),
    spout: clamp(num(st.spout, 0)),
    die: clamp(num(st.dieT, 0)),
    broken,
    fx,
    crackPart: fx !== null && K === 1 ? fx.part : null,
    ventSealed: broken.vent === true || (is("vent") && K >= 2),
    ventFlare: is("vent") && K === 1,
    seamCool: broken.seam === true ? 1 : is("seam") ? BRK.seamCool[K]! : 0,
    coreBroken: broken.core === true || (is("core") && K >= 3),
    coreScale: coreTab(BRK.coreScale, BRK.coreScale[4], 1),
    coreDull: coreTab(BRK.coreDull, BRK.coreDull[4], 0),
    coreLight: coreTab(BRK.coreLight, BRK.coreLight[4], 1),
    charge: is("core") ? BRK.charge[K]! : clamp(num(st.charge, 0)),
  };
}

/** 本體（全部平塗部件；給剪影層包外框）。遮罩模式時每個零件前切換上色／擦掉（`zone`）。 */
function bodyLayer(g: Ctx, S: GiantS): void {
  zone(g, "vent");
  for (const v of VENTS) vent(g, v, S);
  zone(g, null);
  dome(g);
  zone(g, "seam");
  seam(g, -1, S);
  seam(g, 1, S);
  zone(g, "core", true);
  cavity(g, S);
  zone(g, "core");
  core(g, S);
  zone(g, null);
  lid(g, S, S.phase >= 2 ? 1 : 0);
  for (const b of BEETLES) beetle(g, b, S);
  if (S.phase === 3)
    for (const [x, len, w] of [[-14, 20, 4.2], [3, 27, 5], [17, 16, 3.6]] as const) {
      // 熔毀：熔岩從殼窩下緣漫出、流過中間那隻甲蟲
      const y0 = CY + CAV_RY - 2;
      const L = len * (0.85 + 0.15 * Math.sin(osc(S.t, 300, S.lp) + x));
      g.fillStyle = LAVA;
      g.beginPath();
      g.moveTo(x - w, y0);
      g.quadraticCurveTo(x - w * 0.9, y0 + L * 0.7, x, y0 + L);
      g.quadraticCurveTo(x + w * 0.9, y0 + L * 0.7, x + w, y0);
      g.closePath();
      g.fill();
      g.strokeStyle = EMBER;
      g.lineWidth = LW;
      g.stroke();
      g.fillStyle = LAVA_HOT;
      g.fillRect(x - 0.8, y0 + 1, 1.6, L * 0.6);
    }
  const open = S.phase >= 2;
  const order = S.shell > 0 ? GIANT_PLATES : S.bt >= 1 ? [] : flyOrder(S.bt);
  for (const p of order) {
    const A = giantPlateAnchor(p, S.shell, S.bt, S.breath, open);
    if (A === null || A.a <= 0 || (S.shell <= 0 && plateFree(A))) continue;
    g.save();
    g.globalAlpha = A.a;
    g.translate(A.x, A.y);
    g.rotate(A.r);
    g.scale(A.s, A.s);
    plate(g, p[4], p[5], S.shell > 0 ? S.breath : 0.12);
    g.restore();
  }
  g.globalCompositeOperation = "source-over";
}

/** 地面：3×3 陣營環（提案 A：圓角方框貼佔格內 3）＋精英金框＋南緣中點金菱形＋影子。顏色是陣營環（敵方＝樣張的紅）。 */
export function giantGroundRing(ctx: Ctx, ring: { fill: string; stroke: string } = { fill: "#c63b3b", stroke: "#ffb3a8" }): void {
  ctx.save();
  ctx.fillStyle = "rgba(10,8,14,0.35)";
  ctx.beginPath();
  ctx.ellipse(0, -30, 74, 26, 0, 0, TAU);
  ctx.fill();
  const r = { x: -69, y: -141, w: 138, h: 138 };
  ctx.save();
  rrect(ctx, r.x, r.y, r.w, r.h, 14);
  ctx.clip();
  ctx.fillStyle = ring.fill;
  ctx.globalAlpha = 0.35;
  ctx.fillRect(r.x, r.y, r.w, -96 - r.y);
  ctx.globalAlpha = 0.8;
  ctx.fillRect(r.x, -96, r.w, r.y + r.h + 96);
  ctx.restore();
  rrect(ctx, r.x, r.y, r.w, r.h, 14);
  ctx.lineWidth = 1.5 * 1.6;
  ctx.strokeStyle = ring.stroke;
  ctx.stroke();
  rrect(ctx, r.x - 2.5, r.y - 2.5, r.w + 5, r.h + 5, 16);
  ctx.lineWidth = 3.6;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.lineWidth = 1.8;
  ctx.strokeStyle = GOLD;
  ctx.stroke();
  gem(ctx, 0, -5.5, 1.6);
  ctx.restore();
}
function gem(ctx: Ctx, x: number, y0: number, s: number): void {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(x, y0);
  ctx.lineTo(x + 2.6 * s, y0 + 2.6 * s);
  ctx.lineTo(x, y0 + 5.2 * s);
  ctx.lineTo(x - 2.6 * s, y0 + 2.6 * s);
  ctx.closePath();
  ctx.lineJoin = "round";
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 1.6 * s;
  ctx.stroke();
  ctx.fillStyle = GOLD;
  ctx.fill();
  ctx.fillStyle = "#fff2c0";
  ctx.fillRect(x - 0.5 * s, y0 + 1.2 * s, s, s);
  ctx.restore();
}
/** 陣營環的圖層範圍（模型 px、相對錨點）。 */
export const GIANT_RING_BOX = { x: -80, y: -150, w: 160, h: 158 } as const;

/** 第 3 階段坑底發紅：屬地面層（地格之上、所有單位之前）。原點＝錨點。 */
export function giantGroundGlow(ctx: Ctx, st: GiantState = {}): void {
  const S = giantStateOf(st);
  if (S.phase === 3) flatGlow(ctx, 0, -50, 112, "#ff6e1e", 1 - S.die, 92);
}
/** 坑底紅光的範圍（模型 px、相對錨點）：`flatGlow(0, −50, 112, ry 92)`。 */
export const GIANT_GLOW_BOX = { x: -114, y: -144, w: 228, h: 188 } as const;
export const giantHasGroundGlow = (phase: number): boolean => phase === 3;

export interface GiantDrawOpt {
  /** 頭目外光色（預設傳說金；null＝不畫）。 */
  glow?: string | null;
  /** 受擊白閃 0～1。 */
  flash?: number;
}
/** 畫灰燼之心（3×3；不含地面的環與紅光）。ctx 目前座標＝模型 px、原點＝錨點。 */
export function drawGiantHeart(ctx: Ctx, st: GiantState = {}, opt: GiantDrawOpt = {}): void {
  const S = giantStateOf(st);
  layer(ctx, GIANT_BOX, (g) => bodyLayer(g, S), { ow: OW, glow: opt.glow === null || S.die > 0 ? null : (opt.glow ?? GOLD), glowW: GLOW_W, glowA: GLOW_A, flash: num(opt.flash, 0) });
  freePlates(ctx, S);
  if (S.inhale > 0) {
    const parts: Array<readonly [number, number, number, string]> = [];
    for (let k = 0; k < 16; k++) {
      const a = rnd("in", k) * TAU;
      const d = 96 * (1 - ((cyc(S.t, 600, S.lp) + rnd("in2", k)) % 1));
      parts.push([CX + Math.cos(a) * d, CY + Math.sin(a) * d * 0.6, 2.8, LAVA_HOT]);
    }
    layer(
      ctx,
      GIANT_BOX,
      (g) => {
        for (const [x, y, r, c] of parts) {
          g.fillStyle = c;
          g.beginPath();
          g.arc(x, y, r, 0, TAU);
          g.fill();
        }
      },
      { ow: 0.8 * GG, alpha: S.phase !== 3 ? Math.max(0.3, S.inhale) : 1 },
    );
  }
}

/** 本體填色層（不描外框、不帶外光）：選單「本體」列的頭像用（移植需求 4.2）。`z`＝每模型 px 幾個 canvas px。沒有 DOM 時 `null`。 */
export function giantFill(st: GiantState, z: number): { canvas: HTMLCanvasElement; ox: number; oy: number; z: number } | null {
  if (typeof document === "undefined") return null;
  const S = giantStateOf(st);
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round((GIANT_BOX[2] - GIANT_BOX[0]) * z));
  c.height = Math.max(1, Math.round((GIANT_BOX[3] - GIANT_BOX[1]) * z));
  const g = c.getContext("2d");
  if (g === null) return null;
  g.setTransform(z, 0, 0, z, -GIANT_BOX[0] * z, -GIANT_BOX[1] * z);
  bodyLayer(g, S);
  return { canvas: c, ox: -GIANT_BOX[0] * z, oy: -GIANT_BOX[1] * z, z };
}

// ---------------- 部位遮罩、滑過亮起、白閃 ----------------
/**
 * 部位遮罩：只有那個部位實際露出的像素（不透明），畫在 `GIANT_BOX` 範圍、每模型 px `res` 個 canvas px。
 * 由畫法直接給：照常畫本體，只有那個部位的零件上色，其他零件 `destination-out`（被後畫的零件蓋住的地方自然擦掉）。沒有 DOM 時 `null`。
 * `crystal`：核心只取晶體（`core()`），不含殼窩（`cavity()`）——破壞白閃用（GB-4c）；其他部位不受影響。
 */
export function giantPartMask(st: GiantState, part: GiantPart, res: number, crystal = false): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const S = giantStateOf(st);
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil((GIANT_BOX[2] - GIANT_BOX[0]) * res));
  c.height = Math.max(1, Math.ceil((GIANT_BOX[3] - GIANT_BOX[1]) * res));
  const g = c.getContext("2d");
  if (g === null) return null;
  g.setTransform(res, 0, 0, res, -GIANT_BOX[0] * res, -GIANT_BOX[1] * res);
  MASK = part;
  MASK_CRYSTAL = crystal;
  try {
    bodyLayer(g, S);
  } finally {
    MASK = null;
    MASK_CRYSTAL = false;
  }
  // 半透明的零件（熱光、光暈）照不透明算：遮罩只看有沒有
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, c.width, c.height);
  return c;
}
function tintCanvas(src: HTMLCanvasElement, col: string): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = src.width;
  c.height = src.height;
  const x = c.getContext("2d")!;
  x.drawImage(src, 0, 0);
  x.globalCompositeOperation = "source-in";
  x.fillStyle = col;
  x.fillRect(0, 0, c.width, c.height);
  return c;
}
/** 圓盤膨脹（N 方向 × 3 圈，同 qCreatureLayer）。 */
function dilateCanvas(src: HTMLCanvasElement, r: number, N = 16): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = src.width;
  c.height = src.height;
  const g = c.getContext("2d")!;
  for (const f of [1, 0.66, 0.33])
    for (let i = 0; i < N; i++) {
      const a = (i / N) * TAU;
      g.drawImage(src, Math.cos(a) * r * f, Math.sin(a) * r * f);
    }
  g.drawImage(src, 0, 0);
  return c;
}
/** 亮起：亮青白 #a8f4ff 描邊＋外框色襯邊＋部位上 35% 同色（線寬照模型 px，畫面上描邊 ≥ 1.5 px、襯邊 ≥ 1 px）。 */
export const GIANT_HOVER = { color: "#a8f4ff", ink: OUT, width: 2.0, inkW: 1.3, fill: 0.35, minPx: 1.5 } as const;
/**
 * 滑過部位格時身上那個部位亮起（`GIANT_BOX` 範圍的畫布、每模型 px `res` 個 canvas px）。`screen`＝每模型 px 幾個畫面 px（地圖縮放），
 * 線寬下限照畫面 px 算。沒有 DOM 時 `null`。
 */
export function giantGlowCanvas(st: GiantState, part: GiantPart, res: number, screen: number): HTMLCanvasElement | null {
  const mask = giantPartMask(st, part, res);
  if (mask === null) return null;
  const dpr = screen > 0 ? res / screen : 1;
  const wp = Math.max(GIANT_HOVER.width * res, GIANT_HOVER.minPx * dpr);
  const ip = Math.max(GIANT_HOVER.inkW * res, 1 * dpr);
  const outer = dilateCanvas(mask, wp + ip);
  const mid = dilateCanvas(mask, wp);
  const lay = document.createElement("canvas");
  lay.width = mask.width;
  lay.height = mask.height;
  const l = lay.getContext("2d")!;
  l.drawImage(tintCanvas(outer, GIANT_HOVER.ink), 0, 0);
  l.drawImage(tintCanvas(mid, GIANT_HOVER.color), 0, 0);
  l.globalCompositeOperation = "destination-out";
  l.drawImage(mask, 0, 0);
  l.globalCompositeOperation = "source-over";
  l.globalAlpha = GIANT_HOVER.fill;
  l.drawImage(tintCanvas(mask, GIANT_HOVER.color), 0, 0);
  return lay;
}
/** 破壞第 1 格「命中」：部位整塊白閃（遮罩和滑過亮起同一份，但核心只白晶體、不含殼窩：GB-4c 美術可修 2），a＝0.9（段 1 同值）。 */
export const GIANT_FLASH_A = 0.9;
export function giantFlashCanvas(st: GiantState, part: GiantPart, res: number): HTMLCanvasElement | null {
  const mask = giantPartMask(st, part, res, true);
  if (mask === null) return null;
  const out = tintCanvas(mask, "#ffffff");
  const c = document.createElement("canvas");
  c.width = out.width;
  c.height = out.height;
  const g = c.getContext("2d")!;
  g.globalAlpha = GIANT_FLASH_A;
  g.drawImage(out, 0, 0);
  return c;
}

// ---------------- A4 破壞演出（5 格約 0.6 秒） ----------------
const mouthOf = (v: Vent): P2 => {
  const h = v.base - v.top;
  return [v.x + Math.sin(v.tilt) * h, v.base - Math.cos(v.tilt) * h];
};
/** 「破」字記號的位置（模型 px，相對錨點）。殼縫掛在被打中的那一側（side −1 西、1 東）。噴口 GB-4c 改 (0, −140)（原 −168 蓋頭頂 HUD；移植需求 5.4）。 */
export const POP: Readonly<Record<GiantPart, P2>> = { vent: [0, -140], seam: [57, -106], core: [0, -114] };
export const popAt = (part: GiantPart, side = 1): P2 => {
  const [x, y] = POP[part];
  return [part === "seam" ? side * x : x, y];
};
const POP_STYLE = { r: 10, ring: 1.5, font: 14, bg: "rgba(0,0,0,0.72)", ringC: "#ff5a4a", text: "#ffd23f", ch: "破" } as const;
/** 「破」記號的等比倍率（同 `bossPartArt.popScale`：畫面字 ≥ 12 px，PB-1f）。 */
export const giantPopScale = (boardScale: number): number => minMarkScale(POP_STYLE.font, MIN_BREAK_POP_FONT_PX, boardScale);
const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";
function pop(ctx: Ctx, x: number, y: number, a: number, f: number): void {
  const P = POP_STYLE;
  ctx.save();
  ctx.globalAlpha = a;
  ctx.beginPath();
  ctx.arc(x, y, P.r * f, 0, TAU);
  ctx.fillStyle = P.bg;
  ctx.fill();
  ctx.lineWidth = P.ring * f;
  ctx.strokeStyle = P.ringC;
  ctx.stroke();
  ctx.font = `bold ${P.font * f}px ${FONT}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = P.text;
  ctx.fillText(P.ch, x, y + 0.5 * f);
  ctx.restore();
}
const SMOKE = ["#2c272b", "#5a5357"] as const;
/** 黑煙（噴口封住的專屬特效）：四團平塗煙，整團包細外框、一起淡。 */
function smoke(ctx: Ctx, x: number, y: number, r: number, a: number): void {
  const lobes = [[0, 0, 1], [-0.75, 0.3, 0.72], [0.75, 0.25, 0.78], [0.1, -0.68, 0.8]] as const;
  layer(
    ctx,
    [x - 2.5 * r, y - 2.5 * r, x + 2.5 * r, y + 2.5 * r],
    (g) => {
      g.fillStyle = SMOKE[0];
      for (const [dx, dy, s] of lobes) {
        g.beginPath();
        g.arc(x + dx * r, y + dy * r, s * r, 0, TAU);
        g.fill();
      }
      g.fillStyle = SMOKE[1];
      for (const [dx, dy, s] of [lobes[3], lobes[1]]) {
        g.beginPath();
        g.ellipse(x + (dx - 0.28 * s) * r, y + (dy - 0.3 * s) * r, 0.42 * s * r, 0.28 * s * r, -0.4, 0, TAU);
        g.fill();
      }
    },
    { ow: 0.6 * GG, alpha: a },
  );
}
/** 火星四散（核心破的專屬特效）：12 顆火星從核心往外噴，第 4 格飛遠、往下掉、變小變淡。 */
function sparks(ctx: Ctx, k: number): void {
  const far = k >= 3;
  const list: Array<readonly [number, number, number, number, string]> = [];
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * TAU + (rnd("spk", i) - 0.5) * 0.4;
    const d = far ? 46 + 16 * rnd("spk-d", i) : 22 + 10 * rnd("spk-d", i);
    const fall = far ? 10 + 6 * rnd("spk-f", i) : 0;
    list.push([Math.cos(a), Math.sin(a) * 0.75, d, fall, i % 3 === 2 ? LAVA : LAVA_HOT]);
  }
  layer(
    ctx,
    GIANT_BOX,
    (g) => {
      for (const [cx, cy, d, fall, c] of list) {
        const x = CX + cx * d;
        const y = CY + cy * d + fall;
        const tail = far ? 4 : 7;
        const w = far ? 2 : 2.8;
        line(g, [[x - cx * tail, y - cy * tail - (far ? 3 : 0)], [x, y]], w, c);
        g.fillStyle = "#fff4c0";
        g.beginPath();
        g.arc(x, y, w * 0.32, 0, TAU);
        g.fill();
      }
    },
    { ow: 0.8 * GG, alpha: far ? 0.75 : 1 },
  );
}
/**
 * 破壞演出的特效層（白閃之外的東西）：畫在所有單位與部位格標示之上。ctx 座標＝模型 px、原點＝錨點；
 * `st.fx`＝{ part, k 0～4, side }；`boardScale`＝地圖縮放（「破」字 800 反向放大，`bossPartArt.popScale`）。
 */
export function giantBreakFx(ctx: Ctx, st: GiantState, boardScale = 1): void {
  const S = giantStateOf(st);
  const f = S.fx;
  if (f === null || f.k >= 4) return;
  const k = f.k;
  const D = (x: number, y: number, list: CreatureFx[]): void => {
    ctx.save();
    ctx.translate(x, y);
    drawCreatureFx(ctx, list, undefined, [-40, -40, 40, 40]);
    ctx.restore();
  };
  const burst = (r: number, c = "#ffffff", c2 = "#ffe08a", a = 1): CreatureFx => ({ k: "burst", x: 0, y: 0, r, c, c2, a });
  const shards = (c: string | readonly string[], s = 2.2, list: ReadonlyArray<readonly [number, number, number]> = [[-9, -6, 0.6], [9, -8, -0.8], [6, 6, 2.2]]): CreatureFx[] =>
    list.map(([x, y, rot], i) => ({ k: "shard", x, y, rot, s, c: typeof c === "string" ? c : c[i % c.length]! }));
  const [px, py] = popAt(f.part, f.side);
  if (f.part === "vent") {
    const M = VENTS.map(mouthOf);
    const mid = M[2]!;
    if (k === 0) M.forEach(([x, y], i) => D(x, y, [burst(i === 2 ? 10 : 8)]));
    if (k === 1) {
      D(mid[0], mid[1], [
        burst(7, "#ffe08a", "#ffffff", 0.8),
        ...shards("#9a8a7e", 2.4, [
          [-10, -7, 0.6],
          [10, -10, -0.8],
          [4, -16, 2.2],
        ]),
      ]);
      D(M[0]![0], M[0]![1], [burst(5, "#ffe08a", "#ffffff", 0.8)]);
      D(M[1]![0], M[1]![1], [burst(5, "#ffe08a", "#ffffff", 0.8)]);
    }
    if (k === 2) {
      M.forEach(([x, y], i) => smoke(ctx, x, y - 7, i === 2 ? 9 : 8, 0.95));
      D(mid[0], mid[1], [burst(15, "#ffd23f", "#ffffff"), { k: "ring", x: 0, y: 2, rx: 20, c: "#ffe08a", w: 1.6 }]);
    }
    if (k === 3)
      M.forEach(([x, y], i) => {
        smoke(ctx, x - 2, y - 17, i === 2 ? 10 : 9, 0.9);
        smoke(ctx, x + 3, y - 32, i === 2 ? 12 : 10.5, 0.65);
        D(x, y + 1, [{ k: "dust", x: 0, y: 0, r: 5, c: "#8a807a", a: 0.9 }]);
      });
  } else if (f.part === "seam") {
    const sx = f.side * 57;
    const sy = -68;
    if (k === 0) D(sx, sy, [burst(9)]);
    if (k === 1) D(sx, sy, [burst(6, "#ffe08a", "#ffffff", 0.8), ...shards(["#9a8a7e", LAVA, "#9a8a7e"], 2.4)]);
    if (k === 2) {
      D(sx, sy, [burst(14, "#ffd23f", "#ffffff"), { k: "ring", x: 0, y: 4, rx: 16, c: "#ffe08a", w: 1.6 }]);
      for (const s of [-1, 1])
        D(s * 58, -70, [
          { k: "puff", x: 0, y: -10, r: 5, c: "#d8d0c8" },
          { k: "puff", x: s * 2, y: 10, r: 4.2, c: "#d8d0c8" },
        ]);
    }
    if (k === 3)
      for (const s of [-1, 1])
        D(s * 59, -46, [
          { k: "dust", x: 0, y: 0, r: 5, c: "#8a807a", a: 0.9 },
          { k: "puff", x: -s * 2, y: -34, r: 5.5, c: "#d8d0c8", a: 0.5 },
        ]);
  } else {
    if (k === 0) D(CX, CY, [burst(10)]);
    if (k === 1) D(CX, CY, [burst(7, "#ffe08a", "#ffffff", 0.8), ...shards("#ffd98a", 2.2)]);
    if (k === 2) {
      sparks(ctx, 2);
      D(CX, CY, [burst(15, "#ffd23f", "#ffffff"), { k: "ring", x: 0, y: 6, rx: 22, c: "#ffe08a", w: 1.6 }]);
    }
    if (k === 3) {
      sparks(ctx, 3);
      D(CX, CY, [
        { k: "puff", x: 0, y: -16, r: 5, c: "#6a6064", a: 1 },
        { k: "dust", x: 0, y: 20, r: 5, c: "#8a807a", a: 0.9 },
      ]);
    }
  }
  const pk = giantPopScale(boardScale);
  if (k === 2) pop(ctx, px, py, 1, pk);
  if (k === 3) pop(ctx, px, py - 3, 0.55, pk);
}
/** 破壞演出特效畫布的範圍（模型 px、相對錨點；含「破」字 800 放大與火星）。 */
export const GIANT_FX_BOX = { x: -110, y: -230, w: 220, h: 250 } as const;

// ---------------- A2 部位格標示（3×3 地面格；畫在單位之上） ----------------
export const MARK = {
  cream: "#f2e6c8",
  hover: "#a8f4ff",
  dimLine: "#8a8690",
  broken: "#5a1a1a",
  x: "#ff5a4a",
  body: "#ff4040",
  inset: 7,
  arm: 10,
  w: 2.2,
  inkW: 1.8,
  minW: 1.5,
  xSize: 18,
  xMin: 6,
  chipR: 8,
  chipMin: 7,
} as const;
/** 打不到的原因 → 小圖（`qIcon/parts.ts`）；字照玩法 PM 定稿（移植需求第 9 節）。 */
export const REASON = {
  ranged: { cat: "target", id: "tag_ranged", zh: "要遠程攻擊才打得到" },
  range: { cat: "card", id: "range", zh: "射程不夠" },
  sight: { cat: "status", id: "blinded", zh: "看不到這一格" },
} as const;
export type MarkWhy = keyof typeof REASON;
export const BACK_CHIP = { cat: "condition", id: "from_behind", zh: "近戰打這裡算從背後" } as const;
/** 800 寬的背刺記號環色。 */
export const BACK_RING = "#ffd75e";
/** 一塊標示的狀態：完好、打不到、破掉、未露出。 */
export type MarkState = "ok" | "off" | "broken" | "hidden";
export interface MarkPart {
  state: MarkState;
  why?: MarkWhy | undefined;
}
export interface MarksOpt {
  /** 畫面 px／模型 px（地圖縮放）。 */
  S?: number;
  /** 裝置 px／畫面 px。 */
  res?: number;
  /** 滑過的部位（`body`＝前殼）。 */
  hover?: GiantPart | "body" | null;
  /** 攻擊者是近戰（殼縫畫背刺記號）。 */
  melee?: boolean;
  /** 殼縫算從背後（`PartView.counts_as_behind`）；預設 true。 */
  behind?: boolean;
}
/** 標示的區塊：[部位, 列, 起欄, 欄數, 背刺記號放哪一側]。 */
export const REGIONS: ReadonlyArray<readonly [GiantPart, number, number, number, number]> = [["vent", 0, 0, 3, 0], ["seam", 1, 0, 1, -1], ["core", 1, 1, 1, 0], ["seam", 1, 2, 1, 1]];
/** 窄畫面（800 寬）：一格畫面寬 < 40 px（不畫原因小圓片、背刺記號換 U 形箭頭）。 */
export const marksCompact = (S: number): boolean => GT * S < 40;

/** 每塊的狀態 → 畫標示。ctx 座標＝模型 px、原點＝錨點。 */
export function drawGiantMarks(ctx: Ctx, parts: Partial<Record<GiantPart, MarkPart>>, o: MarksOpt = {}): void {
  const S = o.S ?? 1;
  const res = o.res ?? 1;
  const hover = o.hover ?? null;
  const melee = o.melee !== false && o.behind !== false;
  const W = (w: number, min: number): number => Math.max(w, min / S);
  const compact = marksCompact(S);
  for (const [part, row, c0, n, side] of REGIONS) {
    const st = parts[part] ?? { state: "ok" as const };
    const [x0, y0] = tileXY(row, c0);
    const w = n * GT;
    let state: MarkState | "hover" = st.state;
    if (state === "ok" && hover === part) state = "hover";
    const ins = MARK.inset;
    const inner = [x0 + ins - 1, y0 + ins - 1, w - 2 * ins + 2, GT - 2 * ins + 2] as const;
    ctx.save();
    const skip = compact && part === "seam" && melee ? (side < 0 ? 2 : 3) : -1;
    if (state === "ok") brackets(ctx, x0, y0, w, MARK.cream, W(MARK.w, MARK.minW), W(MARK.inkW, 1), skip);
    else if (state === "hover") {
      const lw = W(2.6, 2);
      ctx.fillStyle = MARK.hover;
      ctx.globalAlpha = 0.14;
      ctx.fillRect(...inner);
      ctx.globalAlpha = 1;
      rrect(ctx, ...inner, 5);
      ctx.lineWidth = lw + 2 * W(MARK.inkW, 1);
      ctx.strokeStyle = OUT;
      ctx.stroke();
      ctx.lineWidth = lw;
      ctx.strokeStyle = MARK.hover;
      ctx.stroke();
    } else if (state === "off") {
      ctx.fillStyle = compact ? "rgba(10,8,14,0.55)" : "rgba(10,8,14,0.34)";
      ctx.fillRect(...inner);
      ctx.globalAlpha = compact ? 1 : 0.75;
      brackets(ctx, x0, y0, w, MARK.dimLine, W(1.8, 1.5), W(1.4, 1));
      ctx.globalAlpha = 1;
      if (!compact) reasonChip(ctx, REASON[st.why ?? "range"], x0 + w / 2, y0 + GT / 2, W(MARK.chipR, MARK.chipMin), S, res);
    } else if (state === "broken") {
      ctx.fillStyle = MARK.broken;
      ctx.globalAlpha = 0.55;
      ctx.fillRect(...inner);
      ctx.globalAlpha = 1;
      const r = W(MARK.xSize, MARK.xMin) / 2;
      const lw = W(3, 1.5);
      ctx.lineCap = "round";
      for (let k = 0; k < n; k++) {
        const cx = x0 + k * GT + GT / 2;
        const cy = y0 + GT / 2;
        for (const [c, lww] of [[OUT, lw + W(2.4, 1.2)], [MARK.x, lw]] as const) {
          ctx.strokeStyle = c;
          ctx.lineWidth = lww;
          ctx.beginPath();
          ctx.moveTo(cx - r, cy - r);
          ctx.lineTo(cx + r, cy + r);
          ctx.moveTo(cx + r, cy - r);
          ctx.lineTo(cx - r, cy + r);
          ctx.stroke();
        }
      }
    } else {
      // 未露出：灰虛線圓角框（線 ≥ 1.5 px、段 ≥ 3 px、不透明，外框色襯邊）
      ctx.setLineDash([W(4, 3.5), W(3, 2.5)]);
      rrect(ctx, ...inner, 5);
      ctx.lineWidth = W(1.6, 1.5) + 2 * W(1, 0.8);
      ctx.strokeStyle = OUT;
      ctx.stroke();
      ctx.lineWidth = W(1.6, 1.5);
      ctx.strokeStyle = MARK.dimLine;
      ctx.stroke();
      ctx.setLineDash([]);
    }
    // 殼縫：近戰時一顆背刺記號（R4 遠程不算，不畫），放「內側」下角（靠核心那側），不蓋住貼外側的熔岩裂縫
    if (part === "seam" && melee && (state === "ok" || state === "hover")) {
      const r = W(MARK.chipR, MARK.chipMin);
      const e = compact ? W(1, 1.5) : W(1, 0.5);
      const cx = side < 0 ? x0 + GT - r - e : x0 + r + e;
      const cy = y0 + GT - r - e;
      if (compact) backMark(ctx, cx, cy, r, S, side);
      else backChip(ctx, cx, cy, r, S, res);
    }
    ctx.restore();
  }
  if (hover === "body") {
    ctx.save();
    const lw = W(2, 1.5);
    ctx.lineWidth = lw + W(1.6, 1);
    ctx.strokeStyle = OUT;
    ctx.strokeRect(-72 + 2, -144 + 2, 140, 140);
    ctx.lineWidth = lw;
    ctx.strokeStyle = MARK.body;
    ctx.strokeRect(-72 + 2, -144 + 2, 140, 140);
    ctx.restore();
  }
}
/** 800 寬的背刺記號：深底圓＋2 px 條件黃環＋米白 U 形迴轉箭頭「∩」（外側腳往上、繞過頂、從內側腳往下，箭頭朝下）。 */
function backMark(ctx: Ctx, x: number, y: number, r: number, S: number, side: number): void {
  const px = 1 / S;
  const ring = 2 * px;
  const a = r * 0.34;
  const lw = Math.max(2 * px, r * 0.24);
  const hw = r * 0.3;
  const sx = -side;
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fillStyle = "rgba(10,12,18,0.92)";
  ctx.fill();
  ctx.lineWidth = ring;
  ctx.strokeStyle = BACK_RING;
  ctx.beginPath();
  ctx.arc(x, y, r - ring / 2, 0, TAU);
  ctx.stroke();
  const top = y - r * 0.06;
  const xo = x - sx * a;
  const xi = x + sx * a;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = MARK.cream;
  ctx.lineWidth = lw;
  ctx.beginPath();
  ctx.moveTo(xo, y + r * 0.46);
  ctx.lineTo(xo, top);
  ctx.arc(x, top, a, sx > 0 ? Math.PI : 0, sx > 0 ? 0 : Math.PI, sx < 0);
  ctx.lineTo(xi, y + r * 0.12);
  ctx.stroke();
  ctx.fillStyle = MARK.cream;
  ctx.beginPath();
  ctx.moveTo(xi - hw, y + r * 0.1);
  ctx.lineTo(xi + hw, y + r * 0.1);
  ctx.lineTo(xi, y + r * 0.58);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
/** 區塊四角的 L 形括號（色＋外框色襯邊）；skip：不畫的角（0 左上、1 右上、2 右下、3 左下）。 */
function brackets(ctx: Ctx, x0: number, y0: number, w: number, col: string, lw: number, ink: number, skip = -1): void {
  const i = MARK.inset;
  const a = MARK.arm;
  const x1 = x0 + w - i;
  const y1 = y0 + GT - i;
  const xa = x0 + i;
  const ya = y0 + i;
  const all: ReadonlyArray<readonly P2[]> = [
    [[xa, ya + a], [xa, ya], [xa + a, ya]],
    [[x1 - a, ya], [x1, ya], [x1, ya + a]],
    [[x1, y1 - a], [x1, y1], [x1 - a, y1]],
    [[xa + a, y1], [xa, y1], [xa, y1 - a]],
  ];
  const segs = all.filter((_, k) => k !== skip);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const [c, ww] of [[OUT, lw + 2 * ink], [col, lw]] as const) {
    ctx.strokeStyle = c;
    ctx.lineWidth = ww;
    for (const sg of segs) {
      ctx.beginPath();
      sg.forEach(([x, y], k) => (k > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.stroke();
    }
  }
}
/** 圖樣貼在小圓片裡（`QIconsParts.chip` 的貼法：圖樣本身＝半徑 × 1.56，貼整數裝置 px）；`gray`＝去色。 */
function chipGlyph(ctx: Ctx, cat: string, id: string, x: number, y: number, r: number, S: number, res: number, gray: boolean): void {
  const cpx = r * 1.56 * S;
  const g = partGlyph(cat, id, cpx, res);
  if (g === null) return;
  let src = g;
  if (gray) {
    const c = document.createElement("canvas");
    c.width = g.width;
    c.height = g.height;
    const gx = c.getContext("2d");
    if (gx === null) return;
    gx.filter = "grayscale(1) brightness(1.05)";
    gx.drawImage(g, 0, 0);
    src = c;
  }
  const a = r * 1.56 * PART_BOX;
  blit(ctx, src, x - a / 2, y - a / 2, a, S * res);
}
function reasonChip(ctx: Ctx, R: { cat: string; id: string }, x: number, y: number, r: number, S: number, res: number): void {
  ctx.save();
  ctx.fillStyle = "rgba(10,12,18,0.88)";
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = Math.max(1 / S, r * 0.12);
  ctx.stroke();
  if (hasDom()) chipGlyph(ctx, R.cat, R.id, x, y, r, S, res, true);
  ctx.restore();
}
/** 1600 的背刺小圓片（`condition:from_behind`；深底、環 `#ffe9a8`）。 */
function backChip(ctx: Ctx, x: number, y: number, r: number, S: number, res: number): void {
  ctx.save();
  ctx.fillStyle = "rgba(10,12,18,0.88)";
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#ffe9a8";
  ctx.lineWidth = Math.max(1 / S, r * 0.12);
  ctx.stroke();
  if (hasDom()) chipGlyph(ctx, BACK_CHIP.cat, BACK_CHIP.id, x, y, r, S, res, false);
  ctx.restore();
}
/** 部位格標示畫布的範圍（模型 px、相對錨點）：佔格四邊各多 4。 */
export const GIANT_MARK_BOX = { x: -76, y: -148, w: 152, h: 152 } as const;

// ---------------- 戰場接點（GB-4b）：外觀旗標、片段 → 狀態、畫一格 ----------------
/** 一格的單位畫布原點（`unitSprite.FEET`＝格子中心往南 T×0.23）到錨點（中心格中心往南 72）的距離（模型 px）。 */
export const GIANT_FEET_TO_ANCHOR = GIANT_ANCHOR_DY - GT * 0.23;
/**
 * 戰場貼圖的畫布（虛擬單位，1 單位＝`GG` 模型 px；`inkCreature.creatureCanvasSize`）：原點（腳底）＝一般單位的腳底（`FEET`），
 * 畫的時候再往南 `GIANT_FEET_TO_ANCHOR` 到錨點，所以頭目的節點、`FEET`、受擊與待機的位移全部沿用一格的規矩。
 * 範圍包住 `GIANT_BOX`（含熔岩柱、飛走的殼片）。`top`＝頭頂（含金外光；HUD 放在它上方，`unitSprite.bossHudDy`）。
 */
export const GIANT_CANVAS: { readonly w: number; readonly h: number; readonly foot: number; readonly top: number } = (() => {
  const foot = Math.ceil((GIANT_FEET_TO_ANCHOR - GIANT_BOX[1]) / GG);
  const below = Math.ceil((GIANT_BOX[3] + GIANT_FEET_TO_ANCHOR) / GG) + 1;
  return { w: Math.ceil((GIANT_BOX[2] - GIANT_BOX[0]) / GG) + 2, h: foot + below, foot, top: (GIANT_BOUNDS.y0 + GIANT_FEET_TO_ANCHOR) / GG };
})();
/** 出手點（虛擬單位、相對腳底）：核心（殼窩中心）。 */
export const GIANT_MOUTH: P2 = [0, (CY + GIANT_FEET_TO_ANCHOR) / GG];

/** 戰場上的外觀（不含片段）：階段、熔殼、破了哪些部位、破壞演出的這一格。 */
export interface GiantLook {
  phase: 1 | 2 | 3;
  /** 熔殼在不在（`molten_shell` 狀態）；演出中殼縫破的前兩格蓋回 1。 */
  shell: 0 | 1;
  /** 熔殼脫落進度（只有殼縫破第 3、4 格有值）。 */
  breakT?: number;
  broken: Partial<Record<GiantPart, boolean>>;
  fx: Required<GiantFx> | null;
}

/** `UnitDraw` 裡用得到的欄位（`battle/partStrip` 的 `PartDraw`／`PartFx` 的結構）。 */
export interface GiantLookInput {
  phase: number | null | undefined;
  statusIds?: readonly string[] | undefined;
  parts?: ReadonlyArray<{ id: string; broken: boolean }> | undefined;
  partFx?: { part: string; frame?: number | undefined; side?: number | undefined; shed?: boolean | undefined } | null | undefined;
}

/** 單位資料 → 外觀。演出中（`partFx.frame` 0～3）那個部位當成還沒破；殼縫第 1 階段破時熔殼前兩格蓋回、第 3、4 格照 `BRK.breakT` 飛走。 */
export function giantLookOf(i: GiantLookInput): GiantLook {
  const phase: 1 | 2 | 3 = i.phase === 2 || i.phase === 3 ? i.phase : 1;
  const broken: Partial<Record<GiantPart, boolean>> = {};
  for (const p of i.parts ?? []) {
    const g = GIANT_PART_OF[p.id];
    if (g !== undefined && p.broken) broken[g] = true;
  }
  let shell: 0 | 1 = (i.statusIds ?? []).includes("molten_shell") ? 1 : 0;
  let breakT: number | undefined;
  const f = i.partFx;
  const part = f == null ? undefined : GIANT_PART_OF[f.part];
  let fx: Required<GiantFx> | null = null;
  if (f != null && part !== undefined && typeof f.frame === "number" && f.frame >= 0 && f.frame <= 3) {
    const k = Math.round(f.frame);
    fx = { part, k, side: f.side === -1 ? -1 : 1 };
    delete broken[part];
    if (part === "seam" && f.shed === true) {
      if (k < 2) shell = 1;
      else {
        shell = 0;
        breakT = BRK.breakT[k];
      }
    }
  }
  return { phase, shell, ...(breakT === undefined ? {} : { breakT }), broken, fx };
}

/** 外觀的快取鍵片段（同外觀同鍵）。 */
export function giantLookKey(l: GiantLook): string {
  const b = GIANT_PARTS.filter((p) => l.broken[p] === true).join("+");
  const f = l.fx === null ? "" : `${l.fx.part}${l.fx.k}${l.fx.side < 0 ? "w" : "e"}`;
  return `G${l.phase}${l.shell}${l.breakT === undefined ? "" : `@${l.breakT}`}|${b}|${f}`;
}

/** 片段的一格（`CreaturePose` 的 clip、u、flash、alpha、reduce）。 */
export interface GiantPose {
  clip?: string | undefined;
  u?: number | undefined;
  flash?: number | undefined;
  alpha?: number | undefined;
  reduce?: boolean | undefined;
}

/**
 * 片段 → `GiantState`（移植需求第 7 節第 1 條）：時間軸沿用 `qBoss.ts` 灰燼之心的 `BOSS_MS`／`bossFrameU`／`bossPlan`，
 * 只取參數：待機的呼吸（`loop` 首尾接上）、熔岩噴發的吸氣與熔岩柱（`spout`，從中間噴口往上）、火焰箭的核心光（`flare`→`charge`）、
 * 受擊整隻白閃、倒下的縮小（`dieT`）。3×3 不位移：衝撞 `ram`、受擊的左右晃（dx、rot）都不用；片段自帶的地上特效也不畫（位置是照 1 格算的）。
 */
export function giantStateFor(look: GiantLook, pose: GiantPose | null): { st: GiantState; flash: number } {
  const base: GiantState = { phase: look.phase, shell: look.shell, ...(look.breakT === undefined ? {} : { breakT: look.breakT }), broken: look.broken, fx: look.fx };
  if (pose === null || pose.clip === undefined) return { st: { ...base, t: 1200 }, flash: clamp(num(pose?.flash, 0)) };
  const clip = bossClipOf({ id: "ah", phase: look.phase }, pose.clip);
  const P = bossPlan("ah", clip, num(pose.u, 0), { phase: look.phase, ...(pose.reduce === true ? { reduce: true } : {}) });
  const s = P.st as { t?: number; loop?: number; inhale?: number; spout?: number; dieT?: number };
  const st: GiantState = { ...base, t: num(s.t, 1200) };
  if (s.loop !== undefined) st.loop = s.loop;
  if (clip === "spout" && pose.reduce !== true) {
    st.inhale = num(s.inhale, 0);
    st.spout = num(s.spout, 0);
  }
  const flare = P.o.flare ?? 0;
  if (flare > 0) st.charge = flare;
  if (clip === "death") st.dieT = num(s.dieT, 0);
  return { st, flash: clamp(Math.max(num(pose.flash, 0), P.o.flash)) };
}

/** ctx 目前每模型 px 幾個 canvas px（有 DOM 時從變換矩陣量；沒有時 1）。 */
function ctxRes(ctx: Ctx): number {
  if (typeof ctx.getTransform !== "function") return 1;
  const m = ctx.getTransform();
  return Math.max(0.25, Math.hypot(m.a, m.b));
}

/**
 * 戰場貼圖的一格（`inkCreature.drawCreature` 的巨型分支）：ctx 原點＝腳底（`FEET`）、單位＝模型 px（呼叫端已 `scale(1/GG)`）。
 * 不鏡像（朝南固定，T8）。`ground === "only"`（影子層）不畫：影子在地面的陣營環裡（`giantGroundRing`）。
 * 破壞演出第 1 格（命中）在部位上疊白閃（`giantFlashCanvas`，遮罩由畫法直接給）。
 */
export function drawGiantFrame(ctx: Ctx, look: GiantLook, pose: GiantPose | null, ground: boolean | "only" = true): void {
  if (ground === "only") return;
  const { st, flash } = giantStateFor(look, pose);
  ctx.save();
  ctx.translate(0, GIANT_FEET_TO_ANCHOR);
  const a = clamp(num(pose?.alpha, 1));
  if (a !== 1) ctx.globalAlpha = (typeof ctx.globalAlpha === "number" ? ctx.globalAlpha : 1) * a;
  drawGiantHeart(ctx, st, { flash });
  if (look.fx !== null && look.fx.k === 0 && hasDom()) {
    const res = ctxRes(ctx);
    const c = giantFlashCanvas(st, look.fx.part, res);
    if (c !== null) ctx.drawImage(c, GIANT_BOX[0], GIANT_BOX[1], c.width / res, c.height / res);
  }
  ctx.restore();
}
