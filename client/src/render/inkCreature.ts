// 異形敵人（野獸、熔岩獸、源晶造物、傀儡、石靈、異形召喚物）的 C 手繪墨線畫法（Phase 5A-ART1／ART2）。
// 移植自美術 PM 樣張 docs/art/sample/enemyArt.js（需求 docs/art/敵人外觀.md 第 3 節）。
// 外觀 ＝ 身形 body × 材質 material × 元素 element × 大小 size × 特徵 traits（＋依狀態的 status_traits）× 精英詞綴 affixes。
// 不認得的值一律退回、不出錯：body → ooze、material → fur、element → 沒有元素、size → 1、trait／affix → 略過（affix 只剩精英金環）。
// 座標：腳底 (0,0)、往上是 -y、朝東（+x 是前方）；朝西左右鏡像；正面、背面沿用側面（同形態、野獸召喚物）。
// 確定性：抖動全部用 inkStyle 的 key 雜湊（禁止 Math.random()）。
import type { Facing } from "../api/types";
import { TAU, type Ctx } from "./artDraw";
import { darken, lighten, mix } from "./color";
import { dot, ellPts, ink, INK, shadow, stroke, withShadeDir, lcg, seedOf, type InkOpt, type Pt } from "./inkStyle";

/** 後端 `DollLook.creature`（字串都可能是前端不認得的新值）。 */
export interface CreatureLookDraw {
  body: string;
  variant?: string | null;
  material?: string | null;
  element?: string | null;
  size?: string | null;
  tint?: string | null;
  traits?: readonly string[] | null;
  status_traits?: Readonly<Record<string, readonly string[]>> | null;
}

/** 畫一隻異形需要的全部輸入。 */
export interface CreatureInput {
  look: CreatureLookDraw;
  /** 身上的狀態 ID（`status_traits` 用）。 */
  statusIds?: readonly string[] | undefined;
  /** 精英（`elite` 標籤）：大小 ×1.15（頭目除外）。 */
  elite?: boolean | undefined;
  /** 精英詞綴的外觀 id（`DollLook.affixes`；內容詞綴 ID 也認得）。 */
  affixes?: readonly string[] | undefined;
  /** 頭目外光（`DollLook.rarity`）。 */
  rarity?: string | null | undefined;
  /** 戰場上（Phase 5A-ART5）：大小查 `FIELD_SIZES`，精英倍率照乘。 */
  field?: boolean | undefined;
}

// 元素色（palette.ts 同一份元素主色；第二色是亮色，眼睛與晶光用）
export const CREATURE_ELEM: Readonly<Record<string, readonly [string, string]>> = {
  fire: ["#ff6a1a", "#ffd04a"],
  ice: ["#8fe3ff", "#e8fbff"],
  lightning: ["#fff36b", "#fff7c0"],
  poison: ["#7ddc3a", "#d6f59a"],
  wind: ["#c8ffe8", "#effff8"],
  earth: ["#b0814a", "#e6c89a"],
  holy: ["#fff2b0", "#fffbe0"],
  shadow: ["#9a6ad8", "#c8a8f0"],
  water: ["#3a7bd5", "#d8f0ff"],
};
const FIRE = CREATURE_ELEM["fire"]!;
const CRYSTAL = "#9a86ff"; // 源晶藍紫（形態光環、魔導劍同色）
const BASALT = "#3b2c28";

export const MATERIALS = ["fur", "magma", "crystal", "stone", "wood", "mist"] as const;
export type Material = (typeof MATERIALS)[number];
export const SIZES: Readonly<Record<string, number>> = { tiny: 0.62, small: 0.8, medium: 1, large: 1.25, huge: 1.6 };
/** 戰場上的大小（Phase 5A-ART5，`docs/art/5A-ART檢查.md` 1）：tiny、small 放大，medium 以上不變；樣張頁與其他畫面照 `SIZES`。 */
export const FIELD_SIZES: Readonly<Record<string, number>> = { ...SIZES, tiny: 0.8, small: 0.9 };
/** 精英的大小倍率（頭目不乘）。 */
export const ELITE_SCALE = 1.15;
/** 頭目外光色（同紙娃娃 `RARITY_GLOW`）。 */
export const CREATURE_GLOW: Readonly<Record<string, string>> = { epic: "#b06cff", legendary: "#ffbf3a" };

/** 材質解出來的色票。 */
export interface Palette {
  mat: Material;
  base: string;
  d: string;
  l: string;
  accent: string | null;
  eye: string;
  sharp: boolean;
  alpha: number | undefined;
}

const isMaterial = (m: string | null | undefined): m is Material => m != null && (MATERIALS as readonly string[]).includes(m);

function paletteOf(material: Material, element: string | undefined, tint: string | undefined, fur: string): Palette {
  const el = element === undefined ? undefined : CREATURE_ELEM[element];
  let base: string;
  let accent: string | null;
  let eye: string;
  if (material === "magma") {
    base = tint ?? BASALT;
    accent = el?.[0] ?? FIRE[0];
    eye = el?.[1] ?? FIRE[1];
  } else if (material === "stone") {
    base = tint ?? "#7f8f94";
    accent = el?.[0] ?? "#8fe3ff";
    eye = el?.[1] ?? "#e8fbff";
  } else if (material === "wood") {
    base = tint ?? "#a8763e";
    accent = el?.[0] ?? null;
    eye = "#2b1e16";
  } else if (material === "mist") {
    base = tint ?? (el !== undefined ? mix("#e6ecef", el[0], 0.45) : "#e6ecef");
    accent = el?.[0] ?? "#b8c4cc";
    eye = el?.[1] ?? "#5a6a7a";
  } else if (material === "crystal") {
    base = el !== undefined ? mix(CRYSTAL, el[0], 0.4) : (tint ?? CRYSTAL);
    accent = el?.[1] ?? "#e4dcff";
    eye = "#ffffff";
  } else {
    base = tint ?? fur;
    if (el !== undefined) base = mix(base, el[0], 0.22);
    accent = el?.[0] ?? null;
    eye = el?.[1] ?? "#ffd23a";
  }
  return { mat: material, base, d: darken(base, 0.28), l: lighten(base, 0.3), accent, eye, sharp: material === "crystal" || material === "stone", alpha: material === "mist" ? 0.62 : undefined };
}

// ---- 小工具 ----
function bbox(pts: readonly Pt[]): { x0: number; x1: number; y0: number; y1: number } {
  let x0 = Infinity;
  let x1 = -Infinity;
  let y0 = Infinity;
  let y1 = -Infinity;
  for (const [x, y] of pts) {
    x0 = Math.min(x0, x);
    x1 = Math.max(x1, x);
    y0 = Math.min(y0, y);
    y1 = Math.max(y1, y);
  }
  return { x0, x1, y0, y1 };
}

function clipTo(ctx: Ctx, pts: readonly Pt[]): void {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
  ctx.clip();
}

/** 粗線肢體：墨線底＋色線。 */
function limb(ctx: Ctx, key: string, pts: readonly Pt[], w: number, color: string): void {
  stroke(ctx, key, pts, w + 1.4, INK);
  stroke(ctx, key, pts, w, color);
}

// ---- 材質表面 ----
function cracks(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const r = lcg(seedOf(key));
  const n = b.x1 - b.x0 > 18 ? 2 : 1;
  ctx.save();
  clipTo(ctx, pts);
  for (let i = 0; i < n; i++) {
    const y = b.y0 + (b.y1 - b.y0) * (0.35 + 0.3 * i);
    const line: Pt[] = [];
    for (let x = b.x0 + 2; x <= b.x1 - 2; x += 3.2) line.push([x, y + (r() - 0.5) * 4]);
    if (line.length < 2) continue;
    stroke(ctx, `${key}-ck${i}a`, line, 1.7, "#7a2a08");
    stroke(ctx, `${key}-ck${i}b`, line, 0.8, P.accent ?? FIRE[0]);
  }
  ctx.restore();
}

function facets(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const w = b.x1 - b.x0;
  const h = b.y1 - b.y0;
  ctx.save();
  clipTo(ctx, pts);
  stroke(ctx, `${key}-f1`, [[b.x0 + w * 0.25, b.y0], [b.x0 + w * 0.45, b.y1]], 0.6, lighten(P.base, 0.5));
  stroke(ctx, `${key}-f2`, [[b.x0 + w * 0.6, b.y0], [b.x0 + w * 0.5, b.y0 + h * 0.6], [b.x1, b.y0 + h * 0.7]], 0.6, lighten(P.base, 0.5));
  ctx.restore();
}

function runes(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const cx = (b.x0 + b.x1) / 2;
  const cy = (b.y0 + b.y1) / 2;
  const rune: Pt[] = [[cx - 3, cy - 3], [cx, cy - 4.4], [cx + 3, cy - 3], [cx, cy], [cx - 2.4, cy + 2.6], [cx + 2.4, cy + 2.6]];
  ctx.save();
  clipTo(ctx, pts);
  stroke(ctx, `${key}-rn1`, rune, 1.4, darken(P.base, 0.35));
  stroke(ctx, `${key}-rn2`, rune, 0.7, P.accent ?? "#8fe3ff");
  ctx.restore();
}

function grain(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  ctx.save();
  clipTo(ctx, pts);
  for (let i = 1; i <= 2; i++) {
    const y = b.y0 + ((b.y1 - b.y0) * i) / 3;
    stroke(ctx, `${key}-gr${i}`, [[b.x0, y], [(b.x0 + b.x1) / 2, y - 0.8], [b.x1, y + 0.4]], 0.45, P.d);
  }
  ctx.restore();
}

interface MassOpt extends InkOpt {
  color?: string;
  main?: boolean;
}

/** 一塊身體：材質色填色；`main` ＝ 主要部位，再加材質表面（裂縫、切面、刻符、木紋）。 */
function mass(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette, opt: MassOpt = {}): void {
  const { color, main, ...rest } = opt;
  ink(ctx, key, pts, color ?? P.base, { sharp: P.sharp, ...(P.alpha !== undefined ? { alpha: P.alpha } : {}), ...rest });
  if (main !== true) return;
  if (P.mat === "magma") cracks(ctx, key, pts, P);
  else if (P.mat === "crystal") facets(ctx, key, pts, P);
  else if (P.mat === "stone") runes(ctx, key, pts, P);
  else if (P.mat === "wood") grain(ctx, key, pts, P);
}

/** 背上的小東西：毛（短毛）、熔岩（火星）、源晶（晶刺）、青石（苔點）；木頭、霧不加。 */
function back(ctx: Ctx, key: string, list: readonly Pt[], P: Palette): void {
  list.forEach(([x, y], i) => {
    if (P.mat === "crystal") {
      const h = 5 + (i % 2) * 2.4;
      ink(ctx, `${key}-sh${i}`, [[x - 2, y + 1], [x + 0.6, y - h], [x + 2.4, y + 1]], lighten(P.base, 0.25), { sharp: true, shade: false, w: 0.6 });
      stroke(ctx, `${key}-shl${i}`, [[x + 0.2, y - h + 1.4], [x - 0.6, y]], 0.5, "#ffffff");
    } else if (P.mat === "stone") {
      dot(ctx, x, y + 0.6, 1.6, 0.8, "#6a8a4a");
    } else if (P.mat === "magma") {
      dot(ctx, x + 1, y - 3 - (i % 2) * 2.4, 0.7, 0.7, P.accent ?? FIRE[0]);
    } else if (P.mat === "fur") {
      stroke(ctx, `${key}-tuft${i}`, [[x - 1.6, y + 0.6], [x, y - 2.4], [x + 1.2, y + 0.4]], 0.6, P.d);
    }
  });
}

const eye = (ctx: Ctx, x: number, y: number, P: Palette, r = 1): void => {
  dot(ctx, x, y, 1.15 * r, 0.9 * r, P.eye);
  dot(ctx, x + 0.2, y, 0.32 * r, 0.75 * r, INK);
};
const fang = (ctx: Ctx, key: string, x: number, y: number, h = 2): void => ink(ctx, key, [[x - 0.7, y], [x, y + h], [x + 0.7, y]], "#f4ecd8", { shade: false, w: 0.35, sharp: true });

// ============================== 身形 ==============================
/** 每種身形：預設毛色、最高點（top）、頭（詞綴特效）、身長的一半（len）、背上幾個點（sp）、熔核點（core）、浮空。 */
export interface BodyDef {
  zh: string;
  fur: string;
  top: number;
  head: Pt;
  len: number;
  sp: readonly Pt[];
  core?: Pt;
  hover?: boolean;
  draw: (ctx: Ctx, P: Palette, variant: string) => void;
}

function drawHound(ctx: Ctx, P: Palette): void {
  for (const x of [-12, 6]) mass(ctx, `hd-lf${x}`, [[x, -12], [x + 4, -12], [x + 4.4, 0], [x - 0.4, 0]], P, { color: P.d });
  mass(ctx, "hd-tail", [[-14, -20], [-22, -25], [-26, -21], [-20, -17], [-13, -15]], P);
  mass(ctx, "hd-body", [[-16, -12], [-17, -20], [-10, -25], [4, -25], [12, -22], [13, -12], [0, -10]], P, { main: true });
  back(ctx, "hd", [[-10, -25], [-4, -25.6], [2, -25.4]], P);
  for (const x of [-9, 8]) mass(ctx, `hd-l${x}`, [[x, -13], [x + 4, -13], [x + 4.6, 0], [x - 0.4, 0]], P);
  mass(ctx, "hd-ear", [[12, -29], [13, -36], [16.4, -30]], P, { color: P.d, w: 0.7, sharp: true });
  mass(ctx, "hd-head", [[8, -22], [11, -30], [17, -31], [22, -28], [28, -26], [28, -23], [21, -21], [14, -18]], P, { main: true });
  dot(ctx, 28, -25, 0.9, 0.8, INK);
  eye(ctx, 19, -27.4, P);
  fang(ctx, "hd-fang", 24, -22.2);
}

function drawBoar(ctx: Ctx, P: Palette): void {
  for (const x of [-10, 6]) mass(ctx, `bo-lf${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P, { color: P.d });
  stroke(ctx, "bo-tail", [[-15, -16], [-18, -18], [-17.4, -20]], 0.8);
  mass(ctx, "bo-body", [[-15, -8], [-16, -18], [-8, -24], [4, -25], [12, -20], [13, -9], [0, -7]], P, { main: true });
  [-11, -6, -1, 4].forEach((x, i) => ink(ctx, `bo-br${i}`, [[x - 2, -23 - (x > -8 ? 1 : 0)], [x, -27.4], [x + 2, -24]], P.d, { sharp: true, shade: false, w: 0.5 }));
  back(ctx, "bo", [[-8, -24], [6, -23]], P);
  for (const x of [-7, 8]) mass(ctx, `bo-l${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P);
  mass(ctx, "bo-ear", [[11, -21], [12, -26], [15, -21]], P, { color: P.d, w: 0.6, sharp: true });
  mass(ctx, "bo-head", [[9, -22], [16, -21], [22, -16], [23, -11], [17, -9], [10, -11]], P, { main: true });
  ink(ctx, "bo-snout", ellPts(22.4, -13.2, 2.2, 2.8, 10), P.l, { shade: false, w: 0.6 });
  ink(ctx, "bo-tusk", [[18.6, -11.4], [21.4, -17.4], [20.4, -11]], "#f4ecd8", { sharp: true, shade: false, w: 0.45 });
  eye(ctx, 16.6, -17.4, P, 0.9);
}

function drawBear(ctx: Ctx, P: Palette): void {
  for (const x of [-11, 6]) mass(ctx, `be-lf${x}`, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], P, { color: P.d });
  mass(ctx, "be-body", [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], P, { main: true });
  back(ctx, "be", [[-10, -28.4], [-3, -29.8], [4, -29.2]], P);
  for (const x of [-6, 11]) mass(ctx, `be-l${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], P);
  mass(ctx, "be-head", [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], P, { main: true });
  mass(ctx, "be-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), P, { shade: false, w: 0.7 });
  ink(ctx, "be-snout", ellPts(23.4, -22.2, 2.6, 2, 10), P.l, { shade: false, w: 0.6 });
  dot(ctx, 25.2, -23, 0.9, 0.8, INK);
  eye(ctx, 18.6, -25.6, P, 0.9);
}

function drawBat(ctx: Ctx, P: Palette): void {
  mass(ctx, "fl-bwf", [[-1, -3], [-10, -16], [-20, -14], [-17, -9], [-22, -6], [-15, -3], [-16, 2], [-4, 1]], P, { color: P.d });
  mass(ctx, "fl-bbody", ellPts(0, 0, 6, 7, 16), P, { main: true });
  mass(ctx, "fl-bwn", [[1, -3], [10, -18], [21, -17], [18, -11], [24, -8], [16, -4], [17, 1], [4, 1]], P, { main: true });
  for (const [x, t] of [[3, -14], [7.4, -14.6]] as const) mass(ctx, `fl-be${x}`, [[x - 1.6, -8.4], [x, t], [x + 1.6, -8.4]], P, { sharp: true, w: 0.6 });
  mass(ctx, "fl-bhead", ellPts(5, -6.4, 4, 3.6, 12), P);
  eye(ctx, 7, -7, P, 0.8);
  fang(ctx, "fl-bfang", 7.6, -3.6, 1.6);
  back(ctx, "fl-b", [[10, -18], [-10, -16]], P);
}

function drawBird(ctx: Ctx, P: Palette): void {
  mass(ctx, "fl-wf", [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]], P, { color: P.d, sharp: true });
  mass(ctx, "fl-tail", [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]], P, { color: P.d, sharp: true, shade: false, w: 0.6 });
  mass(ctx, "fl-body", ellPts(0, 0, 9, 6, 16), P, { main: true });
  ink(ctx, "fl-belly", ellPts(1.5, 2, 6, 3, 12), P.mat === "fur" ? "#f0e6d0" : P.l, { shade: false, w: 0.5 });
  mass(ctx, "fl-wn", [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]], P, { main: true, sharp: true });
  mass(ctx, "fl-head", ellPts(9, -4, 4.2, 4.2, 12), P);
  ink(ctx, "fl-beak", [[12.5, -5.2], [17, -3], [12.5, -1]], "#e8bb48", { sharp: true, shade: false, w: 0.5 });
  eye(ctx, 10.6, -5, P, 0.8);
  for (const x of [-2, 3]) stroke(ctx, `fl-claw${x}`, [[x, 5], [x, 9]], 1.4, "#e8bb48");
  back(ctx, "fl", [[10, -28], [18, -34]], P);
}

function drawFlyer(ctx: Ctx, P: Palette, v: string): void {
  ctx.save();
  ctx.translate(0, -18);
  if (v === "bat") drawBat(ctx, P);
  else drawBird(ctx, P);
  ctx.restore();
}

function drawSpider(ctx: Ctx, P: Palette): void {
  const legs: Pt[][] = [[[1, -10], [-6, -19], [-13, 0]], [[3, -10], [0, -21], [-4, 0]], [[5, -10], [9, -21], [8, 0]], [[7, -10], [16, -18], [18, 0]]];
  legs.forEach((l, i) => limb(ctx, `sp-lf${i}`, l.map(([x, y]): Pt => [x - 2.2, y - 0.6]), 0.9, P.d));
  mass(ctx, "sp-abd", ellPts(-9, -12, 9, 8, 18), P, { main: true });
  back(ctx, "sp", [[-12, -19.6], [-6, -19.4]], P);
  stroke(ctx, "sp-mark", [[-11, -15], [-8, -11], [-11, -8]], 1.2, P.accent ?? "#c0392b");
  mass(ctx, "sp-head", ellPts(5, -9, 6, 5, 14), P);
  legs.forEach((l, i) => limb(ctx, `sp-l${i}`, l, 1, P.base));
  for (const [x, y] of [[9.4, -11], [10.6, -9.4], [8.6, -9.2]] as const) dot(ctx, x, y, 0.7, 0.7, P.eye);
  fang(ctx, "sp-fang", 10, -6, 2);
}

function drawBeetle(ctx: Ctx, P: Palette): void {
  const legs: Pt[][] = [[[-8, -6], [-12, -3], [-13, 0]], [[0, -6], [-1, -2], [-2, 0]], [[7, -6], [9, -3], [11, 0]]];
  legs.forEach((l, i) => limb(ctx, `bt-lf${i}`, l.map(([x, y]): Pt => [x + 2, y]), 0.8, P.d));
  mass(ctx, "bt-shell", [[-14, -8], [-13, -15], [-6, -20], [4, -20], [11, -15], [12, -8], [0, -6]], P, { main: true });
  stroke(ctx, "bt-seam", [[-13, -10], [-4, -14.6], [8, -16.6]], 0.6);
  back(ctx, "bt", [[-6, -20], [1, -20.4]], P);
  mass(ctx, "bt-head", [[11, -14], [16, -15], [19, -11], [17, -7], [11, -7]], P, { color: P.d });
  mass(ctx, "bt-horn", [[16, -13.4], [23, -18], [19.4, -11]], P, { color: P.l, sharp: true, shade: false, w: 0.6 });
  legs.forEach((l, i) => limb(ctx, `bt-l${i}`, l, 0.9, P.base));
  eye(ctx, 15.6, -11.6, P, 0.8);
}

function drawLizard(ctx: Ctx, P: Palette): void {
  for (const x of [-6, 9]) mass(ctx, `lz-lf${x}`, [[x - 2, -6], [x + 2, -6], [x + 1, 0], [x - 3, 0]], P, { color: P.d });
  mass(ctx, "lz-tail", [[-8, -10], [-20, -9], [-30, -3], [-32, -1], [-22, -4], [-8, -5]], P, { main: true });
  mass(ctx, "lz-body", [[-10, -5], [-10, -11], [-2, -14], [10, -13], [14, -9], [12, -5], [0, -4]], P, { main: true });
  for (const x of [-6, -1, 4]) ink(ctx, `lz-sp${x}`, [[x - 2, -13.4], [x, -18.4], [x + 2, -13.6]], P.mat === "fur" ? "#c0392b" : P.l, { sharp: true, shade: false, w: 0.5 });
  back(ctx, "lz", [[-14, -9], [8, -13]], P);
  for (const x of [-7, 10]) mass(ctx, `lz-l${x}`, [[x - 2, -7], [x + 2, -7], [x + 3, 0], [x - 2.6, 0]], P);
  mass(ctx, "lz-head", [[12, -12], [16, -15], [23, -14], [27, -11], [26, -9], [18, -8], [13, -8]], P, { main: true });
  eye(ctx, 19, -12.4, P, 0.85);
}

function drawSerpent(ctx: Ctx, P: Palette): void {
  mass(ctx, "sn-coil", ellPts(-4, -3.6, 13, 4.2, 20), P, { main: true });
  mass(ctx, "sn-coil2", ellPts(-2, -7.4, 8.4, 3.2, 16), P, { color: P.d });
  mass(ctx, "sn-neck", [[1, -6], [8, -6], [10, -16], [9, -24], [4, -24], [5, -16]], P, { main: true });
  stroke(ctx, "sn-belly", [[8.6, -7], [9.4, -16], [8.4, -23]], 1.4, P.mat === "fur" ? "#e8dca0" : P.l);
  back(ctx, "sn", [[-10, -7], [-1, -10.4]], P);
  mass(ctx, "sn-head", [[3, -25], [8, -29.4], [15, -28.4], [18.4, -25], [14, -22], [6, -22]], P, { main: true });
  stroke(ctx, "sn-tongue", [[18.4, -24.6], [21.6, -24.6], [23, -26]], 0.5, "#d23c3c");
  stroke(ctx, "sn-tongue2", [[21.6, -24.6], [23, -23.4]], 0.5, "#d23c3c");
  eye(ctx, 12, -26.4, P, 0.85);
}

function drawShell(ctx: Ctx, P: Palette): void {
  for (const x of [-9, 6]) mass(ctx, `sh-lf${x}`, [[x - 3, -7], [x + 2, -7], [x + 2, 0], [x - 3.4, 0]], P, { color: P.d });
  mass(ctx, "sh-dome", [[-15, -6], [-14, -15], [-7, -22], [4, -22], [11, -16], [12, -6], [0, -5]], P, { main: true });
  const plates: Pt[][] = [[[-8, -21], [-9, -7]], [[3, -21], [2, -7]], [[-14, -12.4], [11.4, -12.4]]];
  plates.forEach((l, i) => stroke(ctx, `sh-plate${i}`, l, 0.6));
  stroke(ctx, "sh-rim", [[-16, -6], [13, -6]], 2.2, INK);
  stroke(ctx, "sh-rim2", [[-16, -6], [13, -6]], 1.2, P.l);
  back(ctx, "sh", [[-9, -21], [-2, -22.6], [5, -21.4]], P);
  for (const x of [-11, 5]) mass(ctx, `sh-l${x}`, [[x, -7], [x + 5, -7], [x + 5.6, 0], [x - 0.4, 0]], P, { color: P.l });
  mass(ctx, "sh-head", [[11, -11], [16, -12], [20, -9], [19, -5], [13, -5]], P, { color: P.l });
  eye(ctx, 17, -9.4, P, 0.8);
}

function drawOoze(ctx: Ctx, P: Palette): void {
  ctx.save();
  ctx.globalAlpha = 0.4;
  ctx.fillStyle = P.d;
  ctx.beginPath();
  ctx.ellipse(0, 0.4, 16, 2.6, 0, 0, TAU);
  ctx.fill();
  ctx.restore();
  mass(ctx, "oz-blob", [[-13, 0], [-14, -6], [-10, -13], [-3, -17], [5, -16], [11, -11], [13, -4], [12, 0]], P, { main: true, alpha: 0.9 });
  for (const [x, y, r] of [[-6, -6, 1.8], [-2, -11, 1.2], [8, -5, 1.4]] as const) ink(ctx, `oz-bub${x}`, ellPts(x, y, r, r, 8), P.l, { shade: false, w: 0.4 });
  back(ctx, "oz", [[-6, -15], [2, -16.6]], P);
  eye(ctx, 4.6, -10, P, 0.9);
  eye(ctx, 8.4, -10.2, P, 0.8);
}

function drawGolem(ctx: Ctx, P: Palette): void {
  mass(ctx, "go-legf", [[-7, -16], [-1, -16], [-1.6, 0], [-8, 0]], P, { color: P.d });
  mass(ctx, "go-armf", [[-10, -37], [-15, -34], [-17, -18], [-12, -17], [-11, -30]], P, { color: P.d });
  mass(ctx, "go-legn", [[0, -16], [6, -16], [6.6, 0], [-0.4, 0]], P);
  mass(ctx, "go-torso", [[-11, -38], [8, -40], [12, -30], [9, -16], [-9, -16], [-12, -28]], P, { main: true });
  back(ctx, "go", [[-9, -38.4], [-3, -39.6]], P);
  mass(ctx, "go-head", [[-4, -40], [-3, -47], [4, -48], [7, -43], [5, -39]], P);
  ink(ctx, "go-eye", [[2.4, -44.6], [6.4, -44.6], [6.4, -43], [2.4, -43]], P.accent ?? "#ffd23a", { shade: false, w: 0.4, sharp: true });
  mass(ctx, "go-arm", [[4, -38], [11, -38], [16, -24], [16, -14], [10, -14], [9, -24]], P, { main: true });
  mass(ctx, "go-fist", ellPts(13, -12, 4, 3.6, 12), P);
}

function drawWisp(ctx: Ctx, P: Palette): void {
  ctx.save();
  ctx.translate(0, -20);
  for (const [i, [x, y, s]] of ([[-11, -5, 2.4], [10, -8, 2], [3, 9, 1.8]] as const).entries()) {
    mass(ctx, `wp-or${i}`, [[x, y - s * 1.6], [x + s, y], [x, y + s * 1.6], [x - s, y]], P, { sharp: true, shade: false, w: 0.5, color: P.l });
  }
  mass(ctx, "wp-core", [[0, -11], [7.4, 0], [0, 11], [-7.4, 0]], P, { main: true, sharp: true });
  ink(ctx, "wp-in", [[0, -5], [3.4, 0], [0, 5], [-3.4, 0]], P.accent ?? P.eye, { sharp: true, shade: false, w: 0.4 });
  dot(ctx, 1.2, -0.6, 0.9, 1.3, INK);
  ctx.restore();
}

function drawFeline(ctx: Ctx, P: Palette): void {
  for (const x of [-8, 10]) mass(ctx, `fe-lf${x}`, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], P, { color: P.d, shade: false, w: 0.6 });
  mass(ctx, "fe-tail", [[-12, -12.4], [-21, -12], [-26, -7], [-24, -5.4], [-20, -9], [-12, -9]], P);
  mass(ctx, "fe-body", ellPts(0, -11, 14, 5, 20), P, { main: true });
  back(ctx, "fe", [[-6, -15.6], [2, -16]], P);
  for (const x of [-11, 7]) mass(ctx, `fe-l${x}`, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], P, { shade: false, w: 0.6 });
  for (const x of [13, 17.4]) mass(ctx, `fe-ear${x}`, [[x - 2.2, -16.6], [x, -21.6], [x + 2.2, -16.6]], P, { w: 0.6, sharp: true });
  mass(ctx, "fe-head", ellPts(15, -14.5, 5.4, 4.6, 16), P, { main: true });
  ink(ctx, "fe-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), P.l, { shade: false, w: 0.5 });
  eye(ctx, 17.2, -15.4, P, 0.9);
  dot(ctx, 21, -13.4, 0.6, 0.5, INK);
}

function drawWraith(ctx: Ctx, P: Palette): void {
  ctx.save();
  ctx.translate(0, -4);
  limb(ctx, "wr-arm-l", [[-7, -30], [-12, -22], [-14, -16]], 2.2, P.base);
  mass(ctx, "wr-body", [[-8, -34], [-10, -20], [-7, -8], [-4, -2], [-1, -6], [2, -1], [5, -6], [9, -18], [8, -34]], P, { main: true });
  mass(ctx, "wr-head", ellPts(0, -38, 6, 6.4, 14), P);
  for (const x of [-2.2, 2.2]) dot(ctx, x, -38, 1.3, 0.9, P.eye);
  limb(ctx, "wr-arm-r", [[7, -30], [12, -23], [15, -18]], 2.2, P.base);
  ctx.restore();
}

function drawPylon(ctx: Ctx, P: Palette): void {
  ink(ctx, "py-base", [[-8, 0], [-9, -5], [9, -5], [8, 0]], "#6a645e", { w: 0.7 });
  mass(ctx, "py-ob", [[-5, -5], [-4, -30], [0, -38], [4, -30], [5, -5]], P, { main: true, sharp: true });
  ink(ctx, "py-eye", ellPts(1.6, -22, 1.8, 2.4, 10), P.accent ?? P.eye, { shade: false, w: 0.4 });
  dot(ctx, 2, -22, 0.5, 1.2, INK);
  ctx.save();
  ctx.globalAlpha = 0.8;
  stroke(ctx, "py-ring", [...ellPts(0, -22, 8.6, 2.4, 20), [8.6, -22]], 0.7, P.accent ?? P.l);
  ctx.restore();
}

export const BODIES: Readonly<Record<string, BodyDef>> = {
  hound: { zh: "犬狼", fur: "#7a7a82", top: -36, head: [20, -28], len: 24, sp: [[-10, -25], [-4, -25.6], [2, -25.4]], draw: drawHound },
  boar: { zh: "野豬", fur: "#6a4a36", top: -28, head: [16, -18], len: 22, sp: [[-8, -24], [-1, -25], [6, -23]], draw: drawBoar },
  bear: { zh: "熊", fur: "#6a4a32", top: -33, head: [18, -26], len: 22, sp: [[-10, -28.4], [-3, -29.8], [4, -29.2]], draw: drawBear },
  flyer: { zh: "飛禽", fur: "#a07a4a", top: -50, head: [9, -22], len: 20, hover: true, sp: [[-4, -22], [0, -24], [4, -22]], draw: drawFlyer },
  crawler: { zh: "爬蟲", fur: "#3a3440", top: -24, head: [15, -12], len: 18, sp: [[-8, -20], [-2, -20.4]], draw: (ctx, P, v) => (v === "spider" ? drawSpider(ctx, P) : drawBeetle(ctx, P)) },
  lizard: { zh: "蜥蜴", fur: "#6a7a3a", top: -19, core: [2, -7.4], head: [20, -12], len: 30, sp: [[-6, -13.6], [-1, -14], [4, -13.6]], draw: drawLizard },
  serpent: { zh: "蛇", fur: "#5a7a3a", top: -30, head: [12, -26], len: 17, sp: [[-10, -7], [-1, -10.4]], draw: drawSerpent },
  shell: { zh: "龜殼", fur: "#5a6a4a", top: -23, head: [16, -9], len: 20, sp: [[-9, -21], [-2, -22.6], [5, -21.4]], draw: drawShell },
  ooze: { zh: "軟泥", fur: "#6a9a5a", top: -18, head: [6, -10], len: 15, sp: [[-6, -15], [2, -16.6]], draw: drawOoze },
  golem: { zh: "傀儡", fur: "#8a847e", top: -49, core: [-1, -29], head: [2, -44], len: 17, sp: [[-9, -38.4], [-3, -39.6], [3, -40]], draw: drawGolem },
  wisp: { zh: "晶靈", fur: "#9a86ff", top: -34, core: [0, -20], head: [0, -22], len: 12, hover: true, sp: [[0, -31]], draw: drawWisp },
  feline: { zh: "豹", fur: "#c8a060", top: -23, head: [15, -15], len: 22, sp: [[-8, -15], [-2, -16], [4, -15.6]], draw: drawFeline },
  wraith: { zh: "霧魅", fur: "#e6ecef", top: -46, head: [0, -42], len: 12, hover: true, sp: [[-4, -40], [4, -40]], draw: drawWraith },
  pylon: { zh: "晶塔", fur: "#8a847e", top: -40, head: [1, -24], len: 9, sp: [[0, -38]], draw: drawPylon },
};
export const BODY_IDS: readonly string[] = Object.keys(BODIES);
/** 有款式的身形：第一個是預設款。 */
export const BODY_VARIANTS: Readonly<Record<string, readonly string[]>> = { flyer: ["bird", "bat"], crawler: ["beetle", "spider"] };

// ============================== 特徵 traits ==============================
/** 特徵／詞綴繪製用的身形資訊。 */
export interface FxInfo {
  head: Pt;
  top: number;
  len: number;
  sp: readonly Pt[];
  core?: Pt | undefined;
  hover?: boolean | undefined;
  element?: string | undefined;
}

type FxDraw = (ctx: Ctx, a: FxInfo, P: Palette | null) => void;

function crust(ctx: Ctx, a: FxInfo): void {
  // 灰燼之心第 1 階段：熔岩甲蟲背殼一片片疊成外殼，殼縫透出火光；殼裂開（移除熔殼）後就不畫
  const [cx, cy] = a.core ?? a.head;
  const plates = [[-7, 3, -0.5], [6.6, 3.4, 0.5], [-8.6, -5, -1.1], [8, -5.6, 1.1], [-3.4, -10.6, -0.3], [3.8, -10.4, 0.35], [0, 6.6, 0]] as const;
  plates.forEach(([dx, dy, rot], i) => {
    const x = cx + dx;
    const y = cy + dy;
    const c = Math.cos(rot);
    const sn = Math.sin(rot);
    const q = (u: number, v: number): Pt => [x + u * c - v * sn, y + u * sn + v * c];
    ink(ctx, `tr-cr${i}`, [q(-4.4, 2.6), q(-3.6, -2.4), q(0, -3.6), q(3.6, -2.4), q(4.4, 2.6), q(0, 3.4)], BASALT, { w: 0.7 });
    stroke(ctx, `tr-crl${i}`, [q(0, -3.2), q(0, 3)], 0.45, "#1c1412");
  });
  ([[-2, -1, 2, -2], [-4, 6, -1, 9], [3, 5, 5, 8]] as const).forEach(([x0, y0, x1, y1], i) => stroke(ctx, `tr-crg${i}`, [[cx + x0, cy + y0], [cx + x1, cy + y1]], 0.9, FIRE[1]));
}

export const TRAITS: Readonly<Record<string, { zh: string; draw: FxDraw }>> = {
  stone_back: { zh: "背上石板", draw: (ctx, a) => a.sp.forEach(([x, y], i) => ink(ctx, `tr-sb${i}`, [[x - 3, y + 1.4], [x - 1.6, y - 4.4 - (i % 2) * 1.6], [x + 2.6, y - 3.4], [x + 3, y + 1.4]], "#8a8f94", { sharp: true, w: 0.7 })) },
  volcano: {
    zh: "背上小火山",
    draw: (ctx, a, P) => {
      const [x, y] = a.sp[Math.floor(a.sp.length / 2)] ?? a.head;
      ink(ctx, "tr-vc", [[x - 6, y + 2], [x - 2, y - 6], [x + 2, y - 6], [x + 6, y + 2]], "#4a3a34", { w: 0.7 });
      ink(ctx, "tr-vc-mouth", ellPts(x, y - 6, 2, 0.8, 10), P?.accent ?? FIRE[0], { shade: false, w: 0.4 });
      ([[-0.6, -9.6, 1.6], [1.6, -12.4, 1.9]] as const).forEach(([dx, dy, r], i) => ink(ctx, `tr-vc-sm${i}`, ellPts(x + dx, y + dy, r, r, 10), "#9a9490", { shade: false, w: 0.4, alpha: 0.75 }));
    },
  },
  smoke: {
    zh: "黃煙",
    draw: (ctx, a) => ([[-a.len * 0.6, a.top * 0.7, 2.6], [a.len * 0.2, a.top * 1.05, 3], [a.len * 0.7, a.top * 0.5, 2.2]] as const).forEach(([x, y, r], i) => ink(ctx, `tr-sk${i}`, ellPts(x, y, r, r * 0.8, 12), "#e8d860", { shade: false, w: 0.4, alpha: 0.55 })),
  },
  mist: {
    zh: "霧氣繞身",
    draw: (ctx, a) => {
      ctx.save();
      ctx.globalAlpha = 0.55;
      ([[-a.len * 0.7, -2, 3.4], [-a.len * 0.1, -1, 4], [a.len * 0.6, -2.4, 3]] as const).forEach(([x, y, r], i) => ink(ctx, `tr-ms${i}`, ellPts(x, y, r, r * 0.55, 12), "#eef2f4", { shade: false, line: false }));
      stroke(ctx, "tr-ms-l", [[-a.len, -6], [-a.len * 0.4, -8], [0, -6]], 0.5, "#ffffff");
      ctx.restore();
    },
  },
  core: {
    zh: "熔核",
    draw: (ctx, a, P) => {
      const [x, y] = a.core ?? a.head;
      const c = P?.accent ?? FIRE[0];
      ink(ctx, "tr-core", ellPts(x, y, 3.2, 3.2, 12), c, { shade: false, w: 0.6 });
      dot(ctx, x - 0.6, y - 0.8, 1.2, 1.2, lighten(c, 0.6));
    },
  },
  crust: { zh: "甲蟲殼堆（熔殼）", draw: crust },
  scar: {
    zh: "疤",
    draw: (ctx, a) => {
      const [x, y] = a.head;
      stroke(ctx, "tr-scar1", [[x - 3, y - 3], [x + 1, y + 2]], 0.8, "#5a2a22");
      stroke(ctx, "tr-scar2", [[x - 1.6, y - 1.2], [x - 3, y]], 0.6, "#5a2a22");
    },
  },
  brood: { zh: "背負卵囊", draw: (ctx, a, P) => a.sp.forEach(([x, y], i) => ink(ctx, `tr-egg${i}`, ellPts(x, y - 2, 2.4, 3, 10), P?.accent ?? "#ffb23a", { shade: false, w: 0.5 })) },
  lava_pool: {
    zh: "背負熔岩池",
    draw: (ctx, a, P) => {
      const first = a.sp[0] ?? a.head;
      const last = a.sp[a.sp.length - 1] ?? a.head;
      const [x0, y0] = first;
      const x1 = last[0];
      ink(ctx, "tr-pool-rim", [[x0 - 5, y0 + 1], [x0 - 3, y0 - 3], [x1 + 3, y0 - 4], [x1 + 5, y0], [x1 + 3, y0 + 3], [x0 - 3, y0 + 3]], "#4a3a34", { w: 0.7 });
      ink(ctx, "tr-pool", ellPts((x0 + x1) / 2, y0 - 1.4, (x1 - x0) / 2 + 2, 1.4, 14), P?.accent ?? FIRE[0], { shade: false, w: 0.4 });
    },
  },
  spots: { zh: "斑紋", draw: (ctx, _a, P) => ([[-8, -12], [-3, -14], [2, -11.4], [-5, -9.4], [8, -12.4]] as const).forEach(([x, y]) => dot(ctx, x, y, 1.1, 0.8, P?.d ?? "#5a4a3a")) },
  sparks: { zh: "電光", draw: (ctx, a) => ([[-a.len * 0.5, a.top * 0.75], [a.len * 0.6, a.top * 0.85]] as const).forEach(([x, y], i) => stroke(ctx, `tr-spk${i}`, [[x, y], [x + 2, y + 2], [x, y + 3], [x + 2.4, y + 5.4]], 0.9, "#fff36b")) },
};
/** 畫在身體後面的特徵。 */
const BEHIND = new Set(["mist"]);

// ============================== 精英詞綴（人形敵人同一套） ==============================
function regen(ctx: Ctx, a: FxInfo): void {
  ([[-a.len * 0.7, a.top * 0.45], [a.len * 0.5, a.top * 0.75], [-a.len * 0.2, a.top * 0.95], [a.len * 0.85, a.top * 0.3]] as const).forEach(([x, y], i) => {
    stroke(ctx, `af-rg${i}a`, [[x - 1.8, y], [x + 1.8, y]], 1.1, "#3f9a4a");
    stroke(ctx, `af-rg${i}b`, [[x, y - 1.8], [x, y + 1.8]], 1.1, "#3f9a4a");
    stroke(ctx, `af-rg${i}c`, [[x - 1.4, y], [x + 1.4, y]], 0.55, "#b6f0a0");
    stroke(ctx, `af-rg${i}d`, [[x, y - 1.4], [x, y + 1.4]], 0.55, "#b6f0a0");
  });
}

function linked(ctx: Ctx, a: FxInfo): void {
  // 頭上一顆青色連心結；連到相鄰同門的虛線由 BattleRenderer 畫
  const [hx] = a.head;
  const y = a.top - 4;
  for (const s of [-1, 1]) stroke(ctx, `af-lk${s}`, [[hx + s * 1.6, y + 2], [hx + s * 3.4, y - 0.4], [hx + s * 1.6, y - 2.4], [hx, y - 0.6]], 1, LINK_COLOR);
}

export const AFFIX: Readonly<Record<string, { zh: string; draw: (ctx: Ctx, a: FxInfo) => void }>> = {
  berserk: {
    zh: "狂暴的",
    draw: (ctx, a) => {
      const [hx, hy] = a.head;
      ([[-3, -6, 1.8], [1, -9, 2.2], [4.6, -6.4, 1.6]] as const).forEach(([dx, dy, r], i) => ink(ctx, `af-bz${i}`, ellPts(hx + dx, hy + dy, r, r, 10), "#ff8a7a", { shade: false, w: 0.45, alpha: 0.8 }));
      for (const s of [-1, 1]) stroke(ctx, `af-bzv${s}`, [[hx - 1 + s * 1.4, hy - 3.2], [hx + s * 0.6, hy - 2], [hx + 1 + s * 1.4, hy - 3.2]], 0.8, "#e02a2a");
    },
  },
  regen: { zh: "再生的", draw: regen },
  armored: {
    zh: "堅甲的",
    draw: (ctx, a) => {
      const y = a.top * (a.hover === true ? 0.55 : 0.6);
      [-a.len * 0.35, a.len * 0.1].forEach((x, i) => ink(ctx, `af-ar${i}`, [[x - 4, y - 1.4], [x + 4, y - 2.4], [x + 4.6, y + 3], [x - 3.6, y + 3.6]], "#8d969f", { w: 0.7 }));
      for (const x of [-a.len * 0.35, a.len * 0.1]) dot(ctx, x, y + 0.6, 0.6, 0.6, "#3c4248");
    },
  },
  swift: { zh: "迅捷的", draw: (ctx, a) => [a.top * 0.3, a.top * 0.55, a.top * 0.8].forEach((y, i) => stroke(ctx, `af-sw${i}`, [[-a.len - 3 - i * 2, y], [-a.len - 11 - i * 2, y]], 0.9, "#e8e8ea")) },
  elemental: {
    zh: "元素的",
    draw: (ctx, a) => {
      const c = (a.element !== undefined ? CREATURE_ELEM[a.element] : undefined) ?? FIRE;
      [-a.len * 0.6, a.len * 0.1, a.len * 0.75].forEach((x, i) => {
        ink(ctx, `af-el${i}`, [[x - 2, 0.6], [x - 0.6, -4.4], [x, -2.4], [x + 1, -6.4], [x + 2.2, 0.6]], c[0], { sharp: true, shade: false, w: 0.45, alpha: 0.9 });
        dot(ctx, x + 0.2, -1, 0.8, 1, c[1]);
      });
    },
  },
  mist_hidden: {
    zh: "霧隱的",
    draw: (ctx, a) => {
      ctx.save();
      ctx.globalAlpha = 0.6;
      ([[-a.len * 0.8, a.top * 0.4, 3.6], [a.len * 0.7, a.top * 0.65, 3.2], [-a.len * 0.2, a.top * 0.95, 3], [a.len * 0.2, -1.4, 4]] as const).forEach(([x, y, r], i) => ink(ctx, `af-mh${i}`, ellPts(x, y, r, r * 0.7, 12), "#eef2f4", { shade: false, line: false }));
      ctx.restore();
    },
  },
  linked: { zh: "連心的", draw: linked },
  blazing: { zh: "熾熱的", draw: (ctx, a) => [-a.len * 0.5, 0, a.len * 0.5].forEach((x, i) => stroke(ctx, `af-bl${i}`, [[x, a.top - 1], [x + 1.4, a.top - 3.4], [x - 0.4, a.top - 5.8], [x + 1, a.top - 8]], 0.8, "#ffb23a")) },
  hardshell: {
    zh: "硬殼的",
    draw: (ctx, a) => {
      a.sp.forEach(([x, y], i) => {
        if (i < 2) stroke(ctx, `af-hs${i}`, [[x - 2.4, y + 2], [x + 1.6, y + 0.6]], 1.1, "#ffffff");
      });
      const s0 = a.sp[0] ?? a.head;
      dot(ctx, s0[0] + 3, s0[1] - 1, 0.9, 0.9, "#ffffff");
    },
  },
  // mirror（分身的）在本體裡畫：身後錯開一個 35% 半透明的分身
};
/** 連心的青色（頭上的結與到相鄰同門的虛線）。 */
export const LINK_COLOR = "#3fd0c0";
/** 內容詞綴 ID（`content/world/enemies.yaml`）→ 美術特效 id；資料有寫 `look` 時不會用到。 */
export const AFFIX_ALIAS: Readonly<Record<string, string>> = { regenerating: "regen", mist_veiled: "mist_hidden", heart_linked: "linked", hard_shelled: "hardshell" };

/** 詞綴清單 → 認得的特效 id（含 mirror；去重、保持順序）；不認得的略過（只剩精英金環）。 */
export function knownAffixes(list: readonly string[] | null | undefined): string[] {
  const out: string[] = [];
  for (const raw of list ?? []) {
    const id = AFFIX_ALIAS[raw] ?? raw;
    if ((AFFIX[id] !== undefined || id === "mirror") && !out.includes(id)) out.push(id);
  }
  return out;
}

/** 人形敵人的詞綴特效位置（頭 (2,-44)、最高 -55、半身長 10）。 */
export const HUMANOID_FX: FxInfo = { head: [2, -44], top: -55, len: 10, sp: [[-4, -33], [3, -33]] };

// ============================== 組合 ==============================
export interface ResolvedCreature {
  body: string;
  variant: string;
  material: Material;
  element: string | undefined;
  tint: string | undefined;
  /** 大小倍率（含精英 ×1.15）。 */
  size: number;
  /** 認得的特徵（含依狀態的 status_traits；去重、保持順序）。 */
  traits: string[];
  affixes: string[];
  /** 頭目外光色；不是頭目為 `undefined`。 */
  glow: string | undefined;
}

const HEX = /^#[0-9a-f]{6}$/i;

/** 驗證並補預設：永遠回傳畫得出來的外觀。 */
export function resolveCreature(input: CreatureInput): ResolvedCreature {
  const look = input.look;
  const body = BODIES[look.body] !== undefined ? look.body : "ooze";
  const variants = BODY_VARIANTS[body] ?? [""];
  const variant = variants.find((v) => v === look.variant) ?? variants[0] ?? "";
  const material: Material = isMaterial(look.material) ? look.material : "fur";
  const element = look.element != null && CREATURE_ELEM[look.element] !== undefined ? look.element : undefined;
  const tint = look.tint != null && HEX.test(look.tint) ? look.tint : undefined;
  const glow = input.rarity != null ? CREATURE_GLOW[input.rarity] : undefined;
  const elite = input.elite === true && glow === undefined; // 頭目不再放大
  const table = input.field === true ? FIELD_SIZES : SIZES;
  const size = (look.size != null ? (table[look.size] ?? 1) : 1) * (elite ? ELITE_SCALE : 1);
  const traits: string[] = [];
  const add = (t: string): void => {
    if (TRAITS[t] !== undefined && !traits.includes(t)) traits.push(t);
  };
  for (const t of look.traits ?? []) add(t);
  const statuses = input.statusIds ?? [];
  const byStatus = look.status_traits ?? {};
  for (const sid of Object.keys(byStatus).sort()) if (statuses.includes(sid)) for (const t of byStatus[sid] ?? []) add(t);
  return { body, variant, material, element, tint, size, traits, affixes: knownAffixes(input.affixes), glow };
}

/** 貼圖快取鍵（外觀＋朝向）：status_traits 已解進 `traits`，狀態一變鍵就跟著變。 */
export function creatureKey(r: ResolvedCreature, facing: Facing): string {
  return ["c", r.body, r.variant, r.material, r.element ?? "", r.tint ?? "", r.size.toFixed(3), r.traits.join("+"), r.affixes.join("+"), r.glow ?? "", facing === "west" ? "w" : "e"].join("|");
}

/** 身形的最高點（虛擬單位，往上是負值，未乘大小）與是否浮空；不認得的身形退回軟泥。 */
export function bodyTop(body: string): { top: number; hover: boolean } {
  const b = BODIES[body] ?? BODIES["ooze"]!;
  return { top: b.top, hover: b.hover === true };
}

function fxInfo(r: ResolvedCreature): FxInfo {
  const b = BODIES[r.body]!;
  return { head: b.head, top: b.top, len: b.len, sp: b.sp, core: b.core, hover: b.hover, element: r.element };
}

function drawBody(ctx: Ctx, r: ResolvedCreature): void {
  const b = BODIES[r.body]!;
  const P = paletteOf(r.material, r.element, r.tint, b.fur);
  const info = fxInfo(r);
  shadow(ctx, b.len * 0.6);
  for (const t of r.traits) if (BEHIND.has(t)) TRAITS[t]!.draw(ctx, info, P); // 霧在身體後面
  b.draw(ctx, P, r.variant);
  for (const t of r.traits) if (!BEHIND.has(t)) TRAITS[t]!.draw(ctx, info, P);
}

/** 畫一隻異形（腳底在原點、朝東，已乘上大小）：分身、本體（霧隱 75%）、詞綴特效。地面環由戰場畫。 */
export function drawCreature(ctx: Ctx, r: ResolvedCreature): void {
  withShadeDir(ctx, -1, () => {
    ctx.save();
    ctx.scale(r.size, r.size);
    if (r.affixes.includes("mirror")) {
      ctx.save();
      ctx.globalAlpha = 0.35;
      ctx.translate(-9, -1);
      drawBody(ctx, r);
      ctx.restore();
    }
    ctx.save();
    if (r.affixes.includes("mist_hidden")) ctx.globalAlpha = 0.75;
    drawBody(ctx, r);
    ctx.restore();
    const info = fxInfo(r);
    for (const a of r.affixes) AFFIX[a]?.draw(ctx, info);
    ctx.restore();
  });
}

/** 人形敵人的詞綴特效與人形特徵（`under` ＝ 身體後面：霧氣繞身；否則畫在身上）。不認得的略過。 */
export function drawHumanoidFx(ctx: Ctx, affixes: readonly string[], traits: readonly string[], under: boolean): void {
  const info = HUMANOID_FX;
  for (const t of traits) {
    const def = TRAITS[t];
    if (def !== undefined && BEHIND.has(t) === under) def.draw(ctx, { ...info, len: 12 }, null);
  }
  if (under) return;
  for (const a of knownAffixes(affixes)) AFFIX[a]?.draw(ctx, info);
}

/** 異形貼圖的虛擬畫布（放得下 huge）：96×96、腳底在下方 12px。 */
export const CREATURE_W = 96;
export const CREATURE_H = 96;
export const CREATURE_FOOT_Y = CREATURE_H - 12;
/** 頭目（huge）在戰場上再縮一點，免得蓋滿三格（樣張「戰場大小」0.7／0.78）。 */
export const HUGE_FIELD_SCALE = 0.9;

function makeCanvas(dpr: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = CREATURE_W * dpr;
  c.height = CREATURE_H * dpr;
  return c;
}

/** 異形貼圖（朝西鏡像；頭目加外光：剪影染色往 12 個方向錯開 2.6px、50%，同 `renderFigureCanvas`）；沒有 DOM 時回傳 `null`。 */
export function renderCreatureCanvas(r: ResolvedCreature, facing: Facing, dpr: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const off = makeCanvas(dpr);
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(CREATURE_W / 2, CREATURE_FOOT_Y);
  if (facing === "west") o.scale(-1, 1);
  drawCreature(o, r);
  if (r.glow === undefined) return off;
  const glow = makeCanvas(dpr);
  const g = glow.getContext("2d");
  const out = makeCanvas(dpr);
  const ctx = out.getContext("2d");
  if (g === null || ctx === null) return off;
  g.drawImage(off, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = r.glow;
  g.fillRect(0, 0, glow.width, glow.height);
  ctx.save();
  ctx.globalAlpha = 0.5;
  for (let a = 0; a < 12; a++) {
    const ang = (a / 12) * TAU;
    ctx.drawImage(glow, Math.cos(ang) * 2.6 * dpr, Math.sin(ang) * 2.6 * dpr);
  }
  ctx.restore();
  ctx.drawImage(off, 0, 0);
  return out;
}
