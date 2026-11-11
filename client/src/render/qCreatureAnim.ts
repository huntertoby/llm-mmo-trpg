// QK-4：Q 版異形的動畫片段（照 docs/art/sample/qCreatureAnim.js）：16 款 × 待機、移動、受擊、倒下，加 35 個攻擊片段（依動作類型）。
// 做法：inkCreature 的部件名稱 → 部件組（RIG：腿、翅、尾、頭、身體、手臂…，各有支點），這裡只算每個組的變換（旋轉、位移、斜切、縮放、透明）
// ＋整隻的變換（root）＋白閃、透明度、影子；特效（飛行物、吐息、震地環…）畫在地面座標。不碰畫法，沒有姿勢時靜態畫面不變。
// 確定性：全部是 u（0～1）的純函式，不用 Math.random；循環片段的相位用 id 的 FNV-1a 雜湊（同 idleClips）。
// 量化：循環片段（待機、移動）一圈 8 格；攻擊、受擊、倒下 12 格／秒（83 毫秒一格），倒下停在最後一格。
// 減少動態（reduce）：待機、移動站好不動；攻擊只往前推 2 單位再回來（特效照放）；受擊只白閃；倒下直接最後一格。
// 戰場上飛向目標格的特效（飛行物、命中爆開、射線）標 `ranged`，由技能特效畫，貼圖不畫（樣張頁照畫）。
import { TAU, type Ctx } from "./artDraw";
import { lighten } from "./color";
import type { CreatureFx, PartXf, QPartPose, SplitPiece } from "./creaturePose";
import { Q_HEADS, RIG } from "./creatureRig";
import { CREATURE_ELEM, elemOr } from "./qCreatureElem";
import { hasDom, qLayer, QC_OUT } from "./qCreatureLayer";

const OUT = QC_OUT;
const ELEM = {
  fire: CREATURE_ELEM["fire"]!,
  ice: CREATURE_ELEM["ice"]!,
  lightning: CREATURE_ELEM["lightning"]!,
  poison: CREATURE_ELEM["poison"]!,
  shadow: CREATURE_ELEM["shadow"]!,
};
const cl = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
const seg = (u: number, a: number, b: number): number => cl((u - a) / (b - a));
const sm = (x: number): number => x * x * (3 - 2 * x);
const bump = (u: number, a: number, b: number): number => Math.sin(Math.PI * seg(u, a, b));
const S = (u: number, n = 1, ph = 0): number => Math.sin(TAU * (u * n + ph));
const Cn = (u: number, n = 1, ph = 0): number => Math.cos(TAU * (u * n + ph));
type KF = ReadonlyArray<readonly [number, number]>;
/** 關鍵格內插：兩格之間用 smoothstep。 */
export function kf(u: number, pts: KF): number {
  const first = pts[0]!;
  if (u <= first[0]) return first[1];
  for (let i = 1; i < pts.length; i++) {
    const [b, vb] = pts[i]!;
    if (u <= b) {
      const [a, va] = pts[i - 1]!;
      return va + (vb - va) * sm((u - a) / (b - a || 1));
    }
  }
  return pts[pts.length - 1]![1];
}
/** id 的 FNV-1a 雜湊（循環片段的相位；同 idleClips.idHash）。 */
export function idHash(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return h >>> 0;
}

/** 動畫要知道的外觀（身形鍵、元素、材質色）。 */
export interface AnimSubject {
  key: string;
  element: string | undefined;
  mat: string;
  base: string;
  accent: string | null;
  /** CB-3：外觀的特徵（熊人立時背上石板往身體壓；沒給＝沒有）。 */
  traits?: readonly string[];
}
type E = { r: AnimSubject };

const MUL = new Set(["sx", "sy", "a"]);
function newPose(): QPartPose {
  return { root: {}, parts: {}, flash: 0, alpha: 1, shadow: 1, fx: [] };
}
function merge(o: PartXf, f: PartXf): void {
  const rec = o as Record<string, unknown>;
  for (const [k, v] of Object.entries(f)) {
    if (k === "pivot") o.pivot = f.pivot;
    else if (MUL.has(k)) rec[k] = ((rec[k] as number | undefined) ?? 1) * (v as number);
    else rec[k] = ((rec[k] as number | undefined) ?? 0) + (v as number);
  }
}
const A = (p: QPartPose, g: string, f: PartXf): void => merge(p.parts[g] ?? (p.parts[g] = {}), f);
const R = (p: QPartPose, f: PartXf): void => merge(p.root, f);
const FX = (p: QPartPose, f: CreatureFx): void => void p.fx.push(f);
/** 飛行物：u 在 [a, b] 從 (x0,y0) 飛到 (x1,y1)，拱高 h；回傳 null＝還沒出手／已到。 */
function proj(u: number, a: number, b: number, x0: number, y0: number, x1: number, y1: number, h = 0): readonly [number, number] | null {
  if (u < a || u > b) return null;
  const q = seg(u, a, b);
  return [x0 + (x1 - x0) * q, y0 + (y1 - y0) * q - h * Math.sin(Math.PI * q)];
}
const TGT = 52; // 目標（相鄰格）的 x
/** CB-2c：產卵片段的蛋：從這一格（u）離開身體；起點（腳底座標，朝東）；大小。戰場的拋物線（eggArc）用同一組。 */
export const EGG_FROM_U = 0.42;
export const EGG_START: readonly [number, number] = [-6, -16];
export const EGG_SCALE = 1.3;
const elc = (r: AnimSubject, d: readonly [string, string]): readonly [string, string] => elemOr(r.element, d);
/** CB-2c：蛋與孵化爆開的顏色（同產卵片段：沒有元素＝火）。 */
export const eggColors = (element: string | undefined): readonly [string, string] => elemOr(element, CREATURE_ELEM["fire"]!);

// ============================== 共用骨架 ==============================
const LEGS4: ReadonlyArray<readonly [string, number]> = [["FN", 0], ["BF", 0], ["FF", 0.5], ["BN", 0.5]];
function breathe(p: QPartPose, u: number, amt = 0.025): void {
  R(p, { sy: 1 + amt * (0.5 - 0.5 * Cn(u)) });
}
interface QuadC {
  amp: number;
  lift: number;
  bob: number;
  nod: number;
  tail?: number;
}
/** 四足對角步：腳底前後＝斜切 kx（往前擺時抬腳＝sy 縮短）；身體一步一顛。 */
function quadWalk(p: QPartPose, u: number, c: QuadC): void {
  for (const [g, ph] of LEGS4) {
    const sw = S(u, 1, ph);
    const lift = Math.max(0, Cn(u, 1, ph));
    A(p, g, { kx: -c.amp * sw, sy: 1 - c.lift * lift });
  }
  R(p, { dy: -c.bob * (0.5 - 0.5 * Cn(u, 2)) });
  A(p, "head", { rot: c.nod * S(u, 2, 0.15) });
  if (c.tail) A(p, "tail", { rot: c.tail * S(u, 1, 0.25) });
}
/** 六腳三腳架步：一組同相。 */
function hexWalk(p: QPartPose, u: number, groups: ReadonlyArray<readonly string[]>, c: { amp: number; lift: number; bob: number; rot?: boolean }): void {
  groups.forEach((gs, i) =>
    gs.forEach((g) => {
      const sw = S(u, 1, i * 0.5);
      const lift = Math.max(0, Cn(u, 1, i * 0.5));
      A(p, g, c.rot === true ? { rot: c.amp * sw, dy: -c.lift * lift } : { kx: -c.amp * sw, sy: 1 - c.lift * lift });
    }),
  );
  R(p, { dy: -c.bob * (0.5 - 0.5 * Cn(u, 2)) });
}
/** 拍翅：翅膀 sy 從上舉到下壓；下拍快（前 40%）、上收慢；下拍時身體往上。 */
function flap(p: QPartPose, u: number, c: { up?: number; dn?: number; bob?: number; base?: number } = {}): number {
  const q = u < 0.4 ? sm(u / 0.4) : 1 - sm((u - 0.4) / 0.6);
  const up = c.up ?? 1.05;
  const dn = c.dn ?? -0.55;
  A(p, "wingN", { sy: up + (dn - up) * q, rot: 0.12 * q });
  A(p, "wingF", { sy: up + (dn - up) * cl(q * 0.92), rot: 0.1 * q });
  R(p, { dy: -(c.bob ?? 1.6) * Math.sin(Math.PI * q) + (c.base ?? 0) });
  return q;
}
/** 翻面的 sy：跳過 0 附近（不會出現「一條線」的那格）。 */
const flipSy = (f: number): number => {
  const c = Math.cos(Math.PI * f);
  return Math.abs(c) < 0.5 ? (f < 0.5 ? 0.5 : -0.5) : c;
};
function quadLegsTuck(p: QPartPose, k: number): void {
  for (const [g] of LEGS4) A(p, g, { sy: 1 - k });
}
// ---- CB-3：第二種近戰片段的輔助（照樣張 qCreatureAnim.js） ----
/** 以 N 為分母的關鍵格（格號 → u＝格號／N），命中格落在量化格上。 */
const kfN = (u: number, N: number, pts: KF): number => kf(u, pts.map(([f, v]) => [f / N, v] as const));
type Foot = readonly [g: string, off?: number, lift?: number];
/**
 * 腳踩地：腳底留在「靜止位置＋off」、離地 lift，由髖的實際位置反推腿的斜切與長度，不穿地、不打滑；抵消 root 的旋轉。
 * 髖抬太高時腿最多拉到 maxS 倍，再高就自然離地。root 要先設好。
 */
function plant(p: QPartPose, e: E, feet: readonly Foot[], maxS = 1.12): void {
  const piv = RIG[e.r.key]?.pivots ?? {};
  const o = p.root;
  const [rx, ry] = o.pivot ?? [0, 0];
  const th = o.rot ?? 0;
  const c = Math.cos(th);
  const s = Math.sin(th);
  for (const [g, off = 0, lift0 = 0] of feet) {
    const [px, py] = piv[g] ?? [0, 0];
    const a = px - rx;
    const b = py - ry;
    const X = rx + (o.dx ?? 0) + a * c - b * s;
    const Y = ry + (o.dy ?? 0) + a * s + b * c;
    const L = -py;
    const lift = Math.max(lift0, -Y - L * maxS);
    const h = Math.max(1, -Y - lift);
    A(p, g, { rot: -th, kx: (px + off - X) / h, sy: h / L });
  }
}
/** 部件上的一點（靜態座標）算到地面座標：套部件變換、大頭倍率、root。特效要從部件出發時用（pose 先設好）。 */
function ptOf(p: QPartPose, e: E, g: string, x: number, y: number): readonly [number, number] {
  const f = p.parts[g] ?? {};
  const [px, py] = f.pivot ?? RIG[e.r.key]?.pivots[g] ?? [0, 0];
  const o = p.root;
  const [rx, ry] = o.pivot ?? [0, 0];
  let a = (x - px) * (f.sx ?? 1);
  const b = (y - py) * (f.sy ?? 1);
  a += (f.kx ?? 0) * b;
  const r = f.rot ?? 0;
  let X = px + (f.dx ?? 0) + a * Math.cos(r) - b * Math.sin(r);
  let Y = py + (f.dy ?? 0) + a * Math.sin(r) + b * Math.cos(r);
  const qh = g === "head" ? Q_HEADS[e.r.key] : undefined;
  if (qh !== undefined) {
    const [, hx, hy, hs] = qh;
    X = hx + (X - hx) * hs;
    Y = hy + (Y - hy) * hs;
  }
  const th = o.rot ?? 0;
  const c = Math.cos(th);
  const s = Math.sin(th);
  const A0 = X - rx;
  const B0 = Y - ry;
  return [rx + (o.dx ?? 0) + A0 * c - B0 * s, ry + (o.dy ?? 0) + A0 * s + B0 * c];
}

// ---- 受擊、倒下（依類別） ----
function hitCommon(p: QPartPose, u: number, back = 3, tilt = 0.08): void {
  p.flash = u < 0.2 ? 0.9 : 0;
  R(p, { dx: -kf(u, [[0, 0], [0.18, back], [1, 0]]), rot: -tilt * kf(u, [[0, 0], [0.18, 1], [1, 0]]) });
}
type Fn = (p: QPartPose, u: number, e: E) => void;
const HIT: Readonly<Record<string, Fn>> = {
  quad(p, u) {
    hitCommon(p, u);
    A(p, "head", { rot: -0.28 * kf(u, [[0, 0], [0.18, 1], [1, 0]]) });
    A(p, "tail", { rot: 0.2 * bump(u, 0, 0.6) });
    for (const g of ["FN", "FF"]) A(p, g, { kx: 0.18 * bump(u, 0, 0.7) });
  },
  flyer(p, u) {
    hitCommon(p, u, 4, 0.22);
    R(p, { dy: -3 * bump(u, 0, 0.8) });
    for (const g of ["wingN", "wingF"]) A(p, g, { sy: 1 + 0.25 * bump(u, 0, 0.5) });
    A(p, "head", { rot: -0.3 * bump(u, 0, 0.7) });
  },
  crawler(p, u) {
    hitCommon(p, u, 2.5, 0.1);
    A(p, "head", { rot: -0.25 * bump(u, 0, 0.7) });
    for (const g of ["N0", "N1", "N2", "N3", "F0", "F1", "F2", "F3"]) A(p, g, { kx: 0.12 * bump(u, 0, 0.6) });
  },
  serpent(p, u) {
    hitCommon(p, u, 2, 0.04);
    const k = kf(u, [[0, 0], [0.18, 1], [1, 0]]);
    A(p, "neck", { kx: 0.32 * k });
    A(p, "head", { dx: -5.5 * k, rot: -0.35 * k });
  },
  shell(p, u) {
    hitCommon(p, u, 2, 0.05);
    const k = kf(u, [[0, 0], [0.15, 1], [0.7, 1], [1, 0]]);
    A(p, "head", { dx: -3.5 * k, sx: 1 - 0.3 * k });
    quadLegsTuck(p, 0.45 * k);
    R(p, { dy: 3 * 0.45 * k * 0.8 });
  },
  ooze(p, u) {
    p.flash = u < 0.2 ? 0.9 : 0;
    const k = kf(u, [[0, 0], [0.15, 1], [1, 0]]);
    const w = Math.sin(u * 14) * (1 - u);
    R(p, { dx: -2.5 * k, sx: 1 + 0.2 * k + 0.06 * w, sy: 1 - 0.2 * k - 0.06 * w, kx: -0.12 * k });
    A(p, "face", { dx: -1.5 * k, dy: 1.5 * k });
  },
  golem(p, u) {
    hitCommon(p, u, 1.5, 0.05);
    A(p, "head", { rot: -0.18 * bump(u, 0, 0.6) });
    A(p, "armN", { rot: 0.25 * bump(u, 0, 0.6) });
    A(p, "armF", { rot: 0.2 * bump(u, 0, 0.6) });
  },
  wisp(p, u) {
    p.flash = u < 0.2 ? 0.9 : 0;
    const k = kf(u, [[0, 0], [0.15, 1], [1, 0]]);
    R(p, { dx: -3 * k + (u < 0.6 ? 0.8 * Math.sign(Math.sin(u * 40)) * (1 - u) : 0) });
    A(p, "core", { sx: 1 - 0.15 * k, sy: 1 - 0.15 * k });
    ([[-1, -0.6], [1, -1], [0.3, 1]] as const).forEach(([x, y], i) => A(p, `orb${i}`, { dx: 4 * x * k, dy: 4 * y * k }));
  },
  wraith(p, u) {
    hitCommon(p, u, 3, 0.06);
    const k = bump(u, 0, 0.8);
    A(p, "body", { kx: -0.25 * k });
    A(p, "head", { dx: -2 * k });
    A(p, "armN", { rot: 0.5 * k });
    A(p, "armB", { rot: 0.4 * k });
    p.alpha = 1 - 0.3 * k;
  },
  pylon(p, u) {
    p.flash = u < 0.2 ? 0.9 : 0;
    const j = u < 0.55 ? Math.sign(Math.sin(u * 46)) * (1 - u / 0.55) : 0;
    A(p, "ob", { dx: -1.2 * j, rot: -0.03 * j });
    A(p, "eye", { dx: -1.2 * j, sy: 1 - 0.6 * bump(u, 0, 0.5) });
    A(p, "ring", { dx: -1.2 * j, dy: 2 * bump(u, 0, 0.6) });
  },
};
function deathQuad(p: QPartPose, u: number, legH: number, c: { headRot?: number; headDy?: number } = {}): void {
  p.flash = u < 0.12 ? 0.7 : 0;
  const st = bump(u, 0, 0.35);
  const k = sm(seg(u, 0.25, 0.75));
  R(p, { dx: -2 * st - 1.5 * k, rot: -0.07 * st + 0.04 * k, dy: legH * 0.62 * k });
  quadLegsTuck(p, 0.7 * k);
  A(p, "head", { rot: -0.25 * st + (c.headRot ?? 0.4) * sm(seg(u, 0.45, 0.9)), dy: (c.headDy ?? 3) * sm(seg(u, 0.45, 0.9)) });
  A(p, "tail", { rot: -0.35 * k });
  if (u >= 0.6) p.eyeShut = true; // QK-4b：四足獸倒下都閉眼 ×（犬狼、豹、蜥蜴照熊的做法）
  p.shadow = 1 - 0.15 * k;
}
/** 側倒（熊、野豬；QK-4b）：晃一下 → 身體落地、四腳伸直往前後攤開、頭垂到地上、最後閉眼（×）。legH＝腳長。 */
function deathSide(p: QPartPose, u: number, legH: number, c: { headRot?: number; headDy?: number; drop?: number; legRot?: number } = {}): void {
  p.flash = u < 0.12 ? 0.7 : 0;
  const st = bump(u, 0, 0.35);
  const k = sm(seg(u, 0.25, 0.75));
  const hk = sm(seg(u, 0.4, 0.85));
  R(p, { dx: -2 * st - 1 * k, rot: -0.07 * st + 0.05 * k, dy: legH * (c.drop ?? 0.6) * k });
  for (const [g, sgn, f] of [["FN", -1, 1], ["FF", -1, 0.75], ["BN", 1, 1], ["BF", 1, 0.75]] as const) A(p, g, { rot: sgn * (c.legRot ?? 1.2) * f * k, sy: 1 - 0.08 * k });
  A(p, "head", { rot: -0.25 * st + (c.headRot ?? 0.5) * hk, dy: (c.headDy ?? 3) * hk });
  A(p, "tail", { rot: 0.5 * k });
  if (u >= 0.6) p.eyeShut = true;
  if (u > 0.55 && u < 0.9) FX(p, { k: "dust", x: 0, y: -1, r: 4, a: 1 - seg(u, 0.55, 0.9) });
  p.shadow = 1 - 0.1 * k;
}

// ============================== 特效 ==============================
/** 一顆飛行物（出手 → 命中爆開）；飛行與命中標 `ranged`。 */
function shot(p: QPartPose, u: number, a: number, b: number, from: readonly [number, number], c: readonly [string, string], o: { x1?: number; y1?: number; h?: number; r?: number; kind?: "shard" } = {}): void {
  const q = proj(u, a, b, from[0], from[1], o.x1 ?? TGT, o.y1 ?? -12, o.h ?? 0);
  if (q !== null) FX(p, { k: o.kind ?? "orb", x: q[0], y: q[1], r: o.r ?? 2.6, c: c[0], c2: c[1], ...(o.kind === undefined ? { tail: 1 } : {}), rot: u * 20, ranged: true });
  if (u > b) {
    const k = seg(u, b, Math.min(1, b + 0.25));
    if (k < 1) {
      FX(p, { k: "glow", x: o.x1 ?? TGT, y: o.y1 ?? -12, r: 10 + 6 * k, c: c[0], a: 1 - k, ranged: true });
      FX(p, { k: "burst", x: o.x1 ?? TGT, y: o.y1 ?? -12, r: 4 + 4 * k, c: c[0], c2: c[1], a: 1 - k * 0.8, ranged: true });
    }
  }
}
/** 蓄力：在 at 聚一顆光。 */
function charge(p: QPartPose, u: number, a: number, b: number, at: readonly [number, number], c: readonly [string, string], r = 2.6): void {
  if (u >= a && u <= b) {
    const k = seg(u, a, b);
    FX(p, { k: "glow", x: at[0], y: at[1], r: 4 + 6 * k, c: c[0], a: 0.4 + 0.6 * k });
    FX(p, { k: "orb", x: at[0], y: at[1], r: r * (0.4 + 0.6 * k), c: c[0], c2: c[1] });
  }
}
const QUAKE = "#ffe9a8"; // 震地環：亮色（深色地面、晶傀儡旁都看得到）
function quakeFx(p: QPartPose, u: number, a: number, x: number, c = QUAKE): void {
  if (u < a) return;
  const k = seg(u, a, 1);
  FX(p, { k: "ring", x, rx: 8 + 34 * k, c, a: 1 - k, w: 1.8 });
  FX(p, { k: "ring", x, rx: 4 + 18 * k, c, a: (1 - k) * 0.9, w: 1.8 });
  FX(p, { k: "glow", x, y: -2, r: 10 * (1 - k) + 4, c, a: 0.6 * (1 - k) });
  FX(p, { k: "dust", x: x - 6 - 8 * k, y: -1, r: 3 + 3 * k, a: 1 - k });
  FX(p, { k: "dust", x: x + 6 + 8 * k, y: -1, r: 3 + 3 * k, a: 1 - k });
  for (let i = 0; i < 3; i++) FX(p, { k: "rock", x: x - 8 + i * 8 + (i - 1) * 6 * k, y: -1 - 8 * Math.sin(Math.PI * cl(k * 1.6 - i * 0.1)), s: 1.6, a: 1 - k });
}
const chompFx = (p: QPartPose, u: number, a: number, b: number, x: number, y: number): void => {
  if (u >= a && u <= b) FX(p, { k: "chomp", x, y, q: seg(u, a, b), a: 1 - 0.5 * seg(u, a, b) });
};
const slashFx = (p: QPartPose, u: number, a: number, b: number, x: number, y: number, c: string, r = 6): void => {
  if (u >= a && u <= b) FX(p, { k: "slash", x, y, r, c, a: 1 - seg(u, a, b) * 0.7, len: 0.5 + seg(u, a, b) });
};

/** 畫特效（地面座標，跟著呼叫端的縮放、鏡像；實體特效有細外框）。 */
export function drawCreatureFx(ctx: Ctx, fxs: readonly CreatureFx[], _element: string | undefined, box: readonly [number, number, number, number] = [-70, -90, 74, 18]): void {
  const solid: CreatureFx[] = [];
  for (const f of fxs) {
    const a = f.a ?? 1;
    const x = f.x ?? 0;
    const y = f.y ?? 0;
    const r = f.r ?? 1;
    if (f.k === "dust") {
      ctx.save();
      ctx.fillStyle = f.c ?? "#b8a890";
      for (const [dx, dy, s] of [[-1, 0, 1], [0.2, -0.5, 1.25], [1.2, 0.1, 0.9]] as const) {
        ctx.globalAlpha = 0.55 * a;
        ctx.beginPath();
        ctx.ellipse(x + dx * r, y + dy * r * 0.6, r * 0.7 * s, r * 0.5 * s, 0, 0, TAU);
        ctx.fill();
      }
      ctx.restore();
    } else if (f.k === "ring") {
      const w = f.w ?? 1.4;
      const rx = f.rx ?? 1;
      ctx.save();
      ctx.globalAlpha = a;
      ctx.strokeStyle = OUT;
      ctx.lineWidth = w + 1.2;
      ctx.beginPath();
      ctx.ellipse(x, y, rx, rx * 0.3, 0, 0, TAU);
      ctx.stroke();
      ctx.strokeStyle = f.c ?? "#ffffff";
      ctx.lineWidth = w;
      ctx.stroke();
      ctx.restore();
    } else if (f.k === "glow") {
      ctx.save();
      ctx.fillStyle = f.c ?? "#ffffff";
      for (const [s, al] of [[1, 0.18], [0.65, 0.26], [0.35, 0.4]] as const) {
        ctx.globalAlpha = al * a;
        ctx.beginPath();
        ctx.arc(x, y, r * s, 0, TAU);
        ctx.fill();
      }
      ctx.restore();
    } else if (f.k === "cone") {
      // 吐息：一串越遠越大越淡的團（平塗）
      ctx.save();
      const n = 5;
      for (let i = 0; i < n; i++) {
        const q = (i + 0.5) / n;
        if (q > (f.len ?? 1)) continue;
        const d = q * (f.max ?? 30);
        const rr = 2.2 + q * (f.spread ?? 6);
        const ang = f.ang ?? 0;
        const cx = x + Math.cos(ang) * d;
        const cy = y + Math.sin(ang) * d + Math.sin(i * 2.1 + (f.t ?? 0)) * 1.2;
        ctx.globalAlpha = a * (0.75 - 0.4 * q);
        ctx.fillStyle = f.c ?? "#ffffff";
        ctx.beginPath();
        ctx.arc(cx, cy, rr, 0, TAU);
        ctx.fill();
        ctx.globalAlpha = a * (0.8 - 0.5 * q);
        ctx.fillStyle = f.c2 ?? "#ffffff";
        ctx.beginPath();
        ctx.arc(cx - rr * 0.2, cy - rr * 0.2, rr * 0.45, 0, TAU);
        ctx.fill();
      }
      ctx.restore();
    } else if (f.k === "wave") {
      ctx.save();
      ctx.globalAlpha = a;
      for (const [w, c] of [[2.4, OUT], [1.2, f.c ?? "#ffffff"]] as const) {
        ctx.strokeStyle = c;
        ctx.lineWidth = w;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.arc(x, y, r, -0.7, 0.7);
        ctx.stroke();
      }
      ctx.restore();
    } else if (f.k === "puff") {
      ctx.save();
      ctx.globalAlpha = 0.5 * a;
      ctx.fillStyle = f.c ?? "#eef2f4";
      ctx.beginPath();
      ctx.ellipse(x, y, r, r * 0.7, 0, 0, TAU);
      ctx.fill();
      ctx.restore();
    } else solid.push(f);
  }
  if (solid.length === 0) return;
  const draw = (g: Ctx): void => {
    for (const f of solid) drawSolid(g, f);
  };
  if (hasDom() && typeof ctx.getTransform === "function") qLayer(ctx, box, draw, { ow: 0.8 });
  else draw(ctx);
}

function drawSolid(g: Ctx, f: CreatureFx): void {
  const x = f.x ?? 0;
  const y = f.y ?? 0;
  const r = f.r ?? 1;
  const c = f.c ?? "#ffffff";
  g.save();
  g.globalAlpha = f.a ?? 1;
  if (f.k === "orb") {
    g.fillStyle = c;
    g.beginPath();
    g.arc(x, y, r, 0, TAU);
    g.fill();
    g.fillStyle = f.c2 ?? "#ffffff";
    g.beginPath();
    g.arc(x - r * 0.15, y - r * 0.15, r * 0.5, 0, TAU);
    g.fill();
    if (f.tail) {
      g.globalAlpha *= 0.6;
      g.fillStyle = c;
      g.beginPath();
      g.ellipse(x - r * 1.6 * f.tail, y, r * 1.3 * f.tail, r * 0.55, 0, 0, TAU);
      g.fill();
    }
  } else if (f.k === "burst") {
    const n = 7;
    g.fillStyle = c;
    g.beginPath();
    for (let i = 0; i < n * 2; i++) {
      const an = (i / (n * 2)) * TAU + 0.2;
      const d = i % 2 ? r * 0.45 : r;
      if (i > 0) g.lineTo(x + Math.cos(an) * d, y + Math.sin(an) * d);
      else g.moveTo(x + Math.cos(an) * d, y + Math.sin(an) * d);
    }
    g.closePath();
    g.fill();
    g.fillStyle = f.c2 ?? "#ffffff";
    g.beginPath();
    g.arc(x, y, r * 0.32, 0, TAU);
    g.fill();
  } else if (f.k === "bolt") {
    const x0 = f.x0 ?? 0;
    const y0 = f.y0 ?? 0;
    const x1 = f.x1 ?? 0;
    const y1 = f.y1 ?? 0;
    const pts: Array<readonly [number, number]> = [[x0, y0]];
    const n = 5;
    for (let i = 1; i < n; i++) {
      const q = i / n;
      pts.push([x0 + (x1 - x0) * q, y0 + (y1 - y0) * q + (i % 2 ? -2.6 : 2.6) * (f.amp ?? 1)]);
    }
    pts.push([x1, y1]);
    for (const [w, cc] of [[2.2, c], [0.8, "#ffffff"]] as const) {
      g.strokeStyle = cc;
      g.lineWidth = w;
      g.lineJoin = "miter";
      g.lineCap = "round";
      g.beginPath();
      pts.forEach(([px, py], i) => (i > 0 ? g.lineTo(px, py) : g.moveTo(px, py)));
      g.stroke();
    }
  } else if (f.k === "beam") {
    g.lineCap = "round";
    const w0 = f.w ?? 2;
    for (const [w, cc] of [[w0, c], [w0 * 0.4, "#ffffff"]] as const) {
      g.strokeStyle = cc;
      g.lineWidth = w;
      g.beginPath();
      g.moveTo(f.x0 ?? 0, f.y0 ?? 0);
      g.lineTo(f.x1 ?? 0, f.y1 ?? 0);
      g.stroke();
    }
  } else if (f.k === "slash") {
    g.lineCap = "round";
    for (let i = 0; i < 3; i++) {
      g.strokeStyle = c;
      g.lineWidth = 1.1;
      g.beginPath();
      g.arc(x + i * 2.2 - 2.2, y + i * 1.2, r, (f.ang ?? -0.3) - 0.9 * (f.len ?? 1), (f.ang ?? -0.3) + 0.5);
      g.stroke();
    }
  } else if (f.k === "chomp") {
    const o = (1 - (f.q ?? 0)) * 3.2 + 0.6;
    g.fillStyle = "#ffffff";
    for (const sgn of [-1, 1]) {
      g.beginPath();
      g.moveTo(x - 4, y + sgn * o);
      g.quadraticCurveTo(x, y + sgn * (o + 3), x + 4, y + sgn * o);
      for (let i = 3; i >= 0; i--) {
        const xx = x - 3 + i * 2;
        g.lineTo(xx + 1, y + sgn * (o - 1.6));
        g.lineTo(xx, y + sgn * o);
      }
      g.closePath();
      g.fill();
    }
  } else if (f.k === "shard") {
    g.translate(x, y);
    g.rotate(f.rot ?? 0);
    const s = f.s ?? 2.4;
    g.fillStyle = c;
    g.beginPath();
    g.moveTo(0, -s * 1.5);
    g.lineTo(s * 0.7, 0);
    g.lineTo(0, s * 1.2);
    g.lineTo(-s * 0.7, 0);
    g.closePath();
    g.fill();
    g.fillStyle = "#ffffff";
    g.fillRect(-s * 0.2, -s * 0.8, s * 0.3, s * 0.7);
  } else if (f.k === "egg") {
    const s = f.s ?? 1;
    g.translate(x, y);
    g.rotate(f.rot ?? 0);
    g.fillStyle = f.c ?? "#ffb23a";
    g.beginPath();
    g.ellipse(0, -3.2 * s, 2.6 * s, 3.3 * s, 0, 0, TAU);
    g.fill();
    g.fillStyle = "#ffe08a";
    g.beginPath();
    g.ellipse(-0.8 * s, -4.4 * s, 0.8 * s, 1.1 * s, 0, 0, TAU);
    g.fill();
    if (f.crack === true) {
      g.strokeStyle = OUT;
      g.lineWidth = 0.6;
      g.beginPath();
      g.moveTo(-2.4 * s, -3.6 * s);
      g.lineTo(-1, -2.4 * s);
      g.lineTo(0.4, -3.8 * s);
      g.lineTo(2.4 * s, -2.8 * s);
      g.stroke();
    }
  } else if (f.k === "flame") {
    const h = f.h ?? 6;
    g.fillStyle = c;
    g.beginPath();
    g.moveTo(x - 2.6, y);
    g.quadraticCurveTo(x - 2.8, y - h * 0.5, x, y - h);
    g.quadraticCurveTo(x + 2.8, y - h * 0.5, x + 2.6, y);
    g.closePath();
    g.fill();
    g.fillStyle = f.c2 ?? "#ffd04a";
    g.beginPath();
    g.ellipse(x, y - h * 0.3, 1.2, h * 0.28, 0, 0, TAU);
    g.fill();
  } else if (f.k === "blob") {
    const rx = f.rx ?? r;
    const ry = f.ry ?? r;
    g.fillStyle = c;
    g.beginPath();
    g.ellipse(x, y, rx, ry, 0, 0, TAU);
    g.fill();
    if (f.rim !== undefined) {
      g.strokeStyle = f.rim;
      g.lineWidth = 0.7;
      g.stroke();
    }
    g.fillStyle = "#ffffff";
    g.globalAlpha *= 0.6;
    g.beginPath();
    g.arc(x - rx * 0.35, y - ry * 0.35, Math.min(rx, ry) * 0.25, 0, TAU);
    g.fill();
  } else if (f.k === "sweep") {
    // CB-3 白弧：外緣是圓弧，內緣往圓心縮（中段偏後最寬），兩端收尖
    const n = 18;
    const w = f.w ?? 3;
    const a0 = f.a0 ?? 0;
    const a1 = f.a1 ?? 0;
    const at = (q: number, rr: number): readonly [number, number] => [x + Math.cos(a0 + (a1 - a0) * q) * rr, y + Math.sin(a0 + (a1 - a0) * q) * rr];
    g.fillStyle = c;
    g.beginPath();
    for (let i = 0; i <= n; i++) {
      const [px, py] = at(i / n, r);
      if (i > 0) g.lineTo(px, py);
      else g.moveTo(px, py);
    }
    for (let i = n; i >= 0; i--) {
      const q = i / n;
      const [px, py] = at(q, r - w * Math.sin(Math.PI * Math.pow(q, 1.7)));
      g.lineTo(px, py);
    }
    g.closePath();
    g.fill();
  } else if (f.k === "rock") {
    const s = f.s ?? 1;
    g.fillStyle = f.c ?? "#7f8f94";
    g.beginPath();
    g.moveTo(x - s, y);
    g.lineTo(x - s * 0.6, y - s * 1.2);
    g.lineTo(x + s * 0.5, y - s * 1.5);
    g.lineTo(x + s, y);
    g.closePath();
    g.fill();
  }
  g.restore();
}

// ============================== 身形 ==============================
/** 攻擊的動作類型：melee 普攻、melee2 第二種近戰（CB-3：單體近戰技能）、charge 衝鋒／撲擊、breath 吐息／噴吐、cast 遠程施放、area 範圍震地／爆發、summon 召喚、blink 位移。 */
export type AttackType = "melee" | "melee2" | "charge" | "breath" | "cast" | "area" | "summon" | "blink";
export const ATTACK_TYPE_ZH: Readonly<Record<AttackType, string>> = { melee: "普攻", melee2: "第二種近戰（單體近戰技能）", charge: "衝鋒／撲擊", breath: "吐息／噴吐", cast: "遠程施放", area: "範圍震地／爆發", summon: "召喚", blink: "位移" };

interface Attack {
  zh: string;
  type: AttackType;
  ms: number;
  fn: Fn;
  /**
   * CB-3（第二種近戰）：命中格的格號。有值＝這個片段在戰場上照自己的格數播（12 格／秒，第 f 格在 f × 83.33 ms，同樣張 frameOf），
   * 命中時間＝hitF × 83.33 ms；沒有＝照舊（戰場量化成 12 格、出手格由特效推）。
   */
  hitF?: number;
}
interface BodyAnim {
  kind: string;
  mouth: readonly [number, number];
  units: string;
  idle: Fn;
  move: Fn;
  attacks: Readonly<Record<string, Attack>>;
  death: Fn;
}

const BT_TRI = [["N0", "N2", "F1"], ["F0", "F2", "N1"]] as const;
const SP_TETRA = [["N0", "F1", "N2", "F3"], ["F0", "N1", "F2", "N3"]] as const;
const ORB_HOME: ReadonlyArray<readonly [number, number]> = [[-11, -5], [10, -8], [3, 9]];
function neck(p: QPartPose, kx: number, rot = 0, extra = 0): void {
  A(p, "neck", { kx });
  A(p, "head", { dx: -18 * kx + extra, rot });
}

// QK-4b 傀儡崩塌的裂縫（軀幹 y −40～−16）：上塊＝肩與背刺；下面左右兩塊
const GOLEM_TOP: ReadonlyArray<readonly [number, number]> = [[-30, -70], [30, -70], [30, -31], [7, -33], [2, -29.5], [-4, -32.5], [-30, -30]];
const GOLEM_LEFT: ReadonlyArray<readonly [number, number]> = [[-30, -30], [-4, -32.5], [2, -29.5], [0.5, -24], [-2.5, -20], [-0.5, -8], [-30, -8]];
const GOLEM_RIGHT: ReadonlyArray<readonly [number, number]> = [[2, -29.5], [7, -33], [30, -31], [30, -8], [-0.5, -8], [-2.5, -20], [0.5, -24]];
// CB-3 蜥蜴掄尾砸擊每格一列：[整隻角度（度，正＝前翻）, 尾根相對角度, 尾巴第 1～4 節各自再彎的角度（正＝往背側翹；null＝不彎）, 頭相對角度,
//   錨點（c 身體中心、s 肩、t 尾尖）, 錨點要到的地面座標 x, y, 四肢]
// 四肢：["p", 位移, 離地]＝四腳踩地；["f", 後腿角度, 後腿長度]＝前腳踩地、後腿離地；["h", 位移, 前腿角度, 前腿長度]＝後腳踩地、前腿離地；["a", 前腿角度, 後腿角度, 長度]＝四腳離地
type TailLegs = readonly ["p", number?, number?] | readonly ["f", number, number] | readonly ["h", number, number, number] | readonly ["a", number, number, number];
type TailRow = readonly [deg: number, tr: number, bd: readonly [number, number, number, number] | null, hr: number, an: "c" | "s" | "t", wx: number, wy: number, lg: TailLegs];
const TAILOVER: readonly TailRow[] = [
  [0, 0, null, 0, "c", 2, -8, ["p"]],
  [3, 0.3, [0.04, 0.05, 0.06, 0.06], -0.05, "c", 2, -6.6, ["p"]],
  [8, 0.55, [0.1, 0.14, 0.16, 0.14], -0.12, "c", 1, -5.6, ["p"]],
  [45, 0.3, [-0.1, -0.16, -0.2, -0.2], -0.6, "s", 12, -7, ["f", 0.5, 1]],
  [100, 0.05, [-0.2, -0.3, -0.36, -0.34], 0.35, "c", 13, -34, ["a", -0.5, 0.6, 0.9]],
  [165, 0.2, [-0.3, -0.4, -0.44, -0.4], 0.2, "c", 17, -26, ["a", 0.3, -0.4, 0.9]],
  [198, 0.16, [0.1, 0.08, 0.05, 0], -0.15, "t", 47, -1.2, ["a", -0.2, 0.3, 0.95]],
  [186, 0.63, [0.03, 0, -0.03, 0], -0.3, "t", 47, -1.2, ["a", 0.5, -0.5, 1]],
  [255, -0.6, [-0.25, -0.25, -0.2, -0.15], 0.3, "c", 15, -20, ["a", -0.4, 0.5, 1]],
  [318, 0.7, [-0.12, -0.17, -0.17, -0.17], 0.15, "c", 13, -24.5, ["a", -0.3, 0.2, 1]],
  [345, 0.5, [0.1, 0.1, 0.1, 0.1], 0.2, "c", 12, -10, ["h", 10, -0.5, 1]],
  [362, 0.18, [-0.05, -0.05, 0, 0.05], 0.1, "c", 13, -6, ["p", 10]],
  [-8, 0.45, [0.04, 0.05, 0.05, 0.04], -0.05, "c", 7, -12.5, ["p", 4.5, 3.5]],
  [3, 0.25, [0.06, 0.08, 0.08, 0.06], 0, "c", 2, -6.4, ["p"]],
  [0, 0, null, 0, "c", 2, -8, ["p"]],
];
// 蜥蜴尾巴的分段（尾巴組內的座標）：尾根、3 個中間關節、尾尖前一節的起點，都在尾巴中線上
const LZ_TAIL: ReadonlyArray<readonly [number, number]> = [[-8, -7.5], [-13, -7.2], [-18, -6.7], [-23, -5.5], [-27.5, -3.4]];
const LZ_TIP: readonly [number, number] = [-32, -1];
/**
 * 分段彎尾巴：把尾巴組切成 5 段（pose.split），第 i 段繞自己的關節多轉 bends[i-1]、接在上一段的末端；每段是原圖的一塊，花紋跟著彎、沿線長度不變。
 * 相鄰兩段在關節處重疊 1.5 單位（彎的外側不會裂開）。回傳尾尖在尾巴組內的座標。
 */
function bendTail(p: QPartPose, bends: readonly [number, number, number, number]): readonly [number, number] {
  const box = (x0: number, x1: number): Array<readonly [number, number]> => [[x0, -40], [x1, -40], [x1, 30], [x0, 30]];
  const pieces: SplitPiece[] = [{ clip: box(-13, -3) }];
  let c = 0;
  let P: readonly [number, number] = LZ_TAIL[1]!;
  for (let i = 1; i <= 4; i++) {
    c += bends[i - 1]!;
    const J = LZ_TAIL[i]!;
    const N = i < 4 ? LZ_TAIL[i + 1]! : LZ_TIP;
    const a = N[0] - J[0];
    const b = N[1] - J[1];
    pieces.push({ pivot: J, dx: P[0] - J[0], dy: P[1] - J[1], rot: c, clip: box(i < 4 ? N[0] : -45, J[0] + 1.5) });
    P = [P[0] + a * Math.cos(c) - b * Math.sin(c), P[1] + a * Math.sin(c) + b * Math.cos(c)];
  }
  p.split = { ...(p.split ?? {}), tail: pieces };
  return P;
}
/** QK-4b 鳥待機落地：比飛行低 9（起飛／落地過場見 birdPerchBlend）。 */
export const BIRD_PERCH_DY = 9;
export const BODY_ANIM: Readonly<Record<string, BodyAnim>> = {
  hound: {
    kind: "quad",
    mouth: [29, -24],
    units: "灰燼犬、霧狼",
    idle(p, u) {
      breathe(p, u);
      A(p, "tail", { rot: 0.2 * S(u, 2) });
      A(p, "head", { rot: -0.05 * S(u, 1, 0.1) });
    },
    move(p, u) {
      quadWalk(p, u, { amp: 0.3, lift: 0.32, bob: 0.9, nod: 0.06, tail: 0.18 });
    },
    attacks: {
      bite: {
        zh: "雙咬（fangs／雙牙）",
        type: "melee",
        ms: 760,
        fn(p, u) {
          const lunge = kf(u, [[0, 0], [0.18, -2], [0.32, 6], [0.42, 4], [0.55, 7], [0.7, 6], [1, 0]]);
          R(p, { dx: lunge, rot: kf(u, [[0, 0], [0.18, -0.07], [0.32, 0.06], [0.45, -0.02], [0.55, 0.07], [1, 0]]), pivot: [-10, 0] });
          A(p, "head", { rot: kf(u, [[0, 0], [0.18, -0.35], [0.3, 0.22], [0.42, -0.3], [0.55, 0.26], [0.7, 0.1], [1, 0]]) });
          for (const g of ["FN", "FF"]) A(p, g, { kx: -0.25 * bump(u, 0.2, 0.75) });
          for (const g of ["BN", "BF"]) A(p, g, { kx: 0.2 * bump(u, 0.2, 0.75) });
          chompFx(p, u, 0.28, 0.42, 37, -23);
          chompFx(p, u, 0.5, 0.66, 38, -21);
        },
      },
      maul: {
        zh: "撲咬拉扯（咬住後身體後坐、往後拉扯）",
        type: "melee2",
        ms: 1100,
        hitF: 4,
        fn(p, u, e) {
          const k = (pts: KF): number => kfN(u, 12, pts);
          const f = Math.round(u * 12);
          // 拉扯：pull 的格（5、7、9）整隻後坐、臀部下沉、四腳釘在原地斜撐（拔河），頭跟著身體往後、嘴咬緊；s＜0 的格被扯回，頭前伸
          const pull = f === 5 || f === 7 ? 1 : f === 9 ? 1.15 : 0;
          const s = k([[0, 0], [4, 0], [5, 1], [6, -0.45], [7, 1], [8, -0.45], [9, 1.15], [10, 0], [12, 0]]);
          const dx = k([[0, 0], [1, -1.5], [2, -3.5], [3, 6], [4, 13], [5, 9.5], [9, 9.5], [10, 4], [11, 0], [12, 0]]) + (pull ? -4.2 * pull : 2.4 * s);
          const rot = k([[0, 0], [1, 0.05], [2, 0.09], [3, -0.17], [4, 0.08], [5, -0.1], [9, -0.1], [10, -0.08], [11, 0.05], [12, 0]]) + (pull ? -0.1 * pull : 0.08 * s);
          R(p, { dx, dy: k([[0, 0], [1, 1.5], [2, 3], [3, -6], [4, 0.6], [5, 1.6], [9, 1.6], [10, -6], [11, 2], [12, 0]]) + 2.2 * pull, rot, pivot: [0, -12] });
          A(p, "head", { rot: k([[0, 0], [1, 0.08], [2, 0.16], [3, -0.42], [4, 0], [5, 0.04], [9, 0.04], [10, 0.1], [12, 0]]) + (pull ? 0.16 : -0.34 * s), dx: pull ? -1.5 * pull : -4.2 * s, dy: pull ? 0 : 0.6 * s });
          const ff = k([[0, 0], [2, 0], [3, 9], [4, 15], [9, 15], [10, 6], [11, 0], [12, 0]]);
          const bf = k([[0, 0], [2, 0], [3, -3], [4, 12], [9, 12], [10, 3], [11, 0], [12, 0]]);
          const lf = k([[2, 0], [3, 5], [4, 0], [9, 0], [10, 4], [11, 0]]);
          const lb = k([[2, 0], [3, 3], [4, 0], [9, 0], [10, 4], [11, 0]]);
          plant(p, e, [["FN", ff, lf], ["FF", ff, lf], ["BN", bf, lb], ["BF", bf, lb]]);
          A(p, "tail", { rot: k([[0, 0], [2, 0.4], [3, -0.25], [4, 0.1], [9, 0.1], [10, -0.3], [11, 0.25], [12, 0]]) + (pull ? 0.5 : 0.75 * s) });
          if (f >= 4 && f <= 9) {
            const [mx, my] = ptOf(p, e, "head", 28, -23.4);
            FX(p, { k: "chomp", x: mx + 0.5, y: my, q: f === 4 ? 0.3 : pull ? 1 : 0.72 });
            if (f === 4) FX(p, { k: "burst", x: mx + 6.5, y: my, r: 7, c: "#ffffff", c2: "#ffe9a8" });
          }
        },
      },
      cast: {
        zh: "火種爆燃（口中引爆）",
        type: "cast",
        ms: 900,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.fire);
          R(p, { rot: kf(u, [[0, 0], [0.35, -0.1], [0.48, 0.05], [1, 0]]), pivot: [-10, 0], dx: kf(u, [[0, 0], [0.35, -1.5], [0.48, 2], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.35, -0.45], [0.48, 0.18], [1, 0]]) });
          charge(p, u, 0.08, 0.42, [29, -27], c);
          shot(p, u, 0.44, 0.62, [31, -25], c, { r: 2.2 });
        },
      },
    },
    death(p, u) {
      deathQuad(p, u, 15, { headRot: 0.45, headDy: 6 });
    },
  },
  boar: {
    kind: "quad",
    mouth: [24, -13],
    units: "硫煙獸",
    idle(p, u) {
      breathe(p, u, 0.03);
      A(p, "head", { rot: 0.05 * S(u, 2) });
      A(p, "tail", { rot: 0.4 * Math.max(0, S(u, 2, 0.2)) });
    },
    move(p, u) {
      quadWalk(p, u, { amp: 0.32, lift: 0.3, bob: 0.7, nod: 0.08, tail: 0.3 });
    },
    attacks: {
      gore: {
        zh: "獠牙撞（fangs）",
        type: "melee",
        ms: 820,
        fn(p, u) {
          A(p, "FN", { kx: u < 0.32 ? 0.35 * S(u / 0.32, 2) : 0, sy: u < 0.32 ? 1 - 0.2 * Math.max(0, Cn(u / 0.32, 2)) : 1 });
          R(p, { dx: kf(u, [[0, 0], [0.3, -1.5], [0.5, 9], [0.62, 8], [1, 0]]), rot: kf(u, [[0, 0], [0.3, 0.06], [0.5, 0.04], [0.6, -0.1], [0.75, 0], [1, 0]]), pivot: [-8, 0] });
          A(p, "head", { rot: kf(u, [[0, 0], [0.3, 0.32], [0.5, 0.25], [0.6, -0.5], [0.78, 0], [1, 0]]) });
          for (const [g, ph] of LEGS4) A(p, g, { kx: u > 0.3 && u < 0.52 ? -0.35 * S(seg(u, 0.3, 0.52), 1, ph) : 0 });
          if (u > 0.3 && u < 0.5) FX(p, { k: "dust", x: -14, y: -1, r: 3, a: 1 - seg(u, 0.3, 0.5) });
          slashFx(p, u, 0.55, 0.7, 34, -18, "#ffffff", 5);
        },
      },
      uptusk: {
        zh: "獠牙上挑（低頭貼地、猛然上挑）",
        type: "melee2",
        ms: 1000,
        hitF: 5,
        fn(p, u, e) {
          const k = (pts: KF): number => kfN(u, 11, pts);
          const f = Math.round(u * 11);
          const rot = k([[0, 0], [1, 0.05], [2, 0.09], [3, 0.11], [4, 0.11], [5, -0.24], [6, -0.44], [7, -0.3], [8, -0.08], [9, -0.02], [11, 0]]);
          R(p, { dx: k([[0, 0], [3, -1], [4, -1.2], [5, 2], [6, 2.4], [8, 1], [11, 0]]), rot, pivot: [-6.5, -12] });
          plant(p, e, [["FN"], ["FF"], ["BN"], ["BF"]]);
          A(p, "head", { rot: k([[0, 0], [1, 0.16], [2, 0.26], [3, 0.31], [4, 0.33], [5, 0.34], [6, 0.34], [7, 0.3], [8, 0.14], [9, 0.04], [11, 0]]) });
          A(p, "tail", { rot: k([[0, 0], [3, 0.6], [4, 0.6], [6, -0.3], [11, 0]]) });
          if (f >= 2 && f <= 4) FX(p, { k: "dust", x: 30, y: -1, r: 3.5, a: f === 4 ? 0.6 : 1 });
          if (f >= 5 && f <= 8) {
            const [tx, ty] = ptOf(p, e, "head", 21.4, -17.4);
            const [bx, by] = ptOf(p, e, "head", 20, -11);
            const d = Math.hypot(tx - bx, ty - by);
            const dirx = (tx - bx) / d;
            const diry = (ty - by) / d;
            const [a0, a1] = ([[0.42, -0.35], [0.22, -0.82], [-0.25, -0.6]] as const)[Math.min(f - 5, 2)]!;
            if (f <= 7) FX(p, { k: "sweep", x: 15, y: -11, r: 21, a0, a1, w: f === 7 ? 1.6 : 3.4 });
            if (f <= 6) {
              FX(p, { k: "burst", x: tx + dirx * 5.5 + 1.5, y: ty + diry * 5.5, r: f === 5 ? 6 : 5, c: "#ffffff", c2: "#ffe9a8" });
              for (let i = 0; i < 3; i++) FX(p, { k: "rock", x: 39 + i * 5 + (f - 5) * 2, y: -2 - (f === 5 ? 9 : 15) * (1 + i * 0.22), s: 1.6 * (f === 5 ? 1 : 0.8) });
            }
          }
        },
      },
      breath: {
        zh: "硫煙吐息（錐形）",
        type: "breath",
        ms: 1000,
        fn(p, u, e) {
          breathe(p, cl(u / 0.3) * 0.5, 0.06 * (u < 0.3 ? 1 : 0));
          R(p, { dx: kf(u, [[0, 0], [0.28, -1.5], [0.4, 0.5], [0.85, 0.5], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.28, -0.3], [0.4, 0.12], [0.85, 0.1], [1, 0]]) });
          if (u > 0.36 && u < 0.92) FX(p, { k: "cone", x: 25, y: -12, max: 36, spread: 9, len: seg(u, 0.36, 0.6), c: e.r.element === "poison" || e.r.element === undefined ? "#c8d040" : elc(e.r, ELEM.poison)[0], c2: "#f2f0b0", a: 1 - seg(u, 0.8, 0.92), t: u * 12 });
        },
      },
    },
    death(p, u) {
      deathSide(p, u, 9, { headRot: 0.35, headDy: 2.5 });
    },
  },
  bear: {
    kind: "quad",
    mouth: [26, -23],
    units: "石背熊",
    idle(p, u) {
      breathe(p, u, 0.03);
      A(p, "head", { rot: 0.06 * S(u, 1) });
      R(p, { kx: 0.015 * S(u, 1, 0.25) });
    },
    move(p, u) {
      quadWalk(p, u, { amp: 0.24, lift: 0.3, bob: 0.6, nod: 0.05 });
      R(p, { rot: 0.025 * S(u, 2) });
    },
    attacks: {
      swipe: {
        zh: "熊掌拍（talons）",
        type: "melee",
        ms: 820,
        fn(p, u) {
          R(p, { rot: kf(u, [[0, 0], [0.35, -0.3], [0.5, 0.07], [0.65, 0.04], [1, 0]]), pivot: [-8, 0], dx: kf(u, [[0, 0], [0.35, -1], [0.5, 3], [1, 0]]) });
          A(p, "FN", { rot: kf(u, [[0, 0], [0.35, -1.25], [0.5, 0.35], [0.65, 0.1], [1, 0]]) });
          A(p, "FF", { rot: kf(u, [[0, 0], [0.38, -0.7], [0.55, 0.1], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.35, -0.15], [0.5, 0.2], [1, 0]]) });
          slashFx(p, u, 0.45, 0.62, 31, -9, "#ffffff", 7);
        },
      },
      slam: {
        zh: "人立重拍（人立舉掌、單掌拍地）",
        type: "melee2",
        ms: 1100,
        hitF: 7,
        fn(p, u, e) {
          const k = (pts: KF): number => kfN(u, 12, pts);
          const f = Math.round(u * 12);
          const rot = k([[0, 0], [1, -0.26], [2, -0.52], [3, -0.68], [4, -0.74], [5, -0.74], [6, -0.42], [7, 0.13], [8, 0.13], [9, 0.09], [10, -0.05], [11, 0.03], [12, 0]]);
          R(p, {
            rot,
            dx: k([[0, 0], [2, -1], [5, -1.5], [6, 5], [7, 13], [8, 13], [9, 11], [10, 5], [11, 0], [12, 0]]),
            dy: k([[0, 0], [5, 0], [6, -2], [7, 1.5], [8, 1.5], [9, 1], [10, -4], [11, 1.5], [12, 0]]),
            pivot: [-8.5, -15],
          });
          // 跳步：出手時後腳跟著往前落、收招時四腳離地跳回原位，腳踩地時不滑動
          const hb = k([[0, 0], [5, 0], [6, 5], [7, 9], [9, 9], [10, 4], [11, 0], [12, 0]]);
          const hl = k([[5, 0], [6, 5], [7, 0], [9, 0], [10, 2.5], [11, 0]]);
          plant(p, e, [["BN", hb, hl], ["BF", hb, hl]]);
          // 頭讓開：世界座標往後上，換算回頭部組（在大頭倍率內）
          const hw = k([[0, 0], [1, -3], [2, -6.5], [3, -7.5], [5, -8], [6, -5], [7, 0], [12, 0]]);
          const hv = k([[0, 0], [2, -1.5], [3, -5], [5, -5.5], [6, -1], [7, -3], [8, -3], [9, -1.5], [10, 0], [12, 0]]);
          const c = Math.cos(rot);
          const s = Math.sin(rot);
          A(p, "head", { rot: k([[0, 0], [1, -0.12], [2, -0.34], [3, -0.68], [5, -0.74], [6, -0.3], [7, 0.3], [8, 0.3], [9, 0.2], [10, 0.08], [12, 0]]) - rot, dx: (hw * c + hv * s) / 1.3, dy: (-hw * s + hv * c) / 1.3 });
          if (f >= 1 && f <= 6) {
            A(p, "FN", { rot: k([[1, -0.9], [2, -1.75], [3, -2.32], [4, -2.5], [5, -2.5], [6, -1.5]]) - rot, sy: 1.08, sx: 1.06, dx: k([[1, 0.5], [3, 1.6], [6, 1.6]]), dy: k([[1, 0], [3, 1], [6, 1]]) });
            A(p, "FF", { rot: k([[1, -0.5], [3, -0.9], [5, -0.9], [6, -0.5]]) - rot, sy: 0.85 });
          } else if (f >= 7) {
            // 重拍：手臂用旋轉（不用斜切，粗細不變），掌底剛好到地面
            if (f <= 9) A(p, "FN", { rot: k([[7, -1.05], [8, -1.05], [9, -1.25]]) - rot, sy: 1.08, sx: 1.06 });
            else plant(p, e, [["FN", k([[10, 6], [11, 0], [12, 0]]), k([[10, 2.5], [11, 0]])]]);
            plant(p, e, [["FF", k([[7, 15], [9, 15], [10, 6], [11, 0], [12, 0]]), k([[9, 0], [10, 2.5], [11, 0]])]]);
          }
          // 人立時背上石板往身體壓一點（石板底邊和身體圓弧本來只有角接觸）：把身體上緣這一帶切開往內移
          if (f >= 1 && f <= 6 && e.r.traits?.includes("stone_back") === true) {
            const ins = 2 * cl(-rot / 0.5);
            p.split = { body: [{ clip: [[-40, -60], [40, -60], [40, -26.2], [-40, -26.2]], dy: ins }, { clip: [[-40, -26.2], [40, -26.2], [40, 20], [-40, 20]] }] };
          }
          // 爪：抬手時伸出（第 1、2 格還短）、拍完抬手時縮回（第 9 格剩一半），跳回的格不畫
          const cw = [0, 0.4, 0.75, 1, 1, 1, 1, 1, 1, 0.5][f] ?? 0;
          if (cw > 0) p.claws = cw;
          if (f >= 7 && f <= 10) {
            const q = (f - 7) / 3;
            const px = f <= 8 ? ptOf(p, e, "FN", 11, -1)[0] : 36;
            FX(p, { k: "dust", x: px + 8 + 6 * q, y: -1, r: 3.2 + 3 * q, a: 1 - q * 0.8 });
            if (f <= 8) FX(p, { k: "dust", x: px - 9 - 5 * q, y: -1, r: 2.6 + 2 * q, a: 1 - q * 0.8 });
            if (f === 7) FX(p, { k: "burst", x: px + 13, y: -7, r: 6.5, c: "#ffffff", c2: "#ffe9a8" });
            if (f <= 8) FX(p, { k: "sweep", x: px - 1, y: -18, r: 17, a0: f === 7 ? -0.6 : 0.5, a1: 1.35, w: f === 7 ? 3.2 : 1.8 });
          }
        },
      },
      quake: {
        zh: "雙掌震地（震地推倒）",
        type: "area",
        ms: 1050,
        fn(p, u) {
          const rise = kf(u, [[0, 0], [0.4, -0.5], [0.52, 0.09], [0.62, 0.05], [1, 0]]);
          R(p, { rot: rise, pivot: [-9, 0], dy: u > 0.5 && u < 0.6 ? 0.6 * Math.sign(Math.sin(u * 90)) : 0 });
          for (const g of ["FN", "FF"]) A(p, g, { rot: kf(u, [[0, 0], [0.4, -1.1], [0.52, 0.15], [0.7, 0], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.4, -0.25], [0.52, 0.25], [1, 0]]) });
          quakeFx(p, u, 0.5, 24);
        },
      },
    },
    death(p, u) {
      deathSide(p, u, 12, { headRot: 0.45, headDy: 4 });
    },
  },
  feline: {
    kind: "quad",
    mouth: [21, -14],
    units: "山豹",
    idle(p, u) {
      breathe(p, u);
      A(p, "tail", { rot: 0.14 * S(u, 1), kx: 0.1 * S(u, 1, 0.2) });
      A(p, "head", { rot: 0.04 * S(u, 1, 0.4) });
    },
    move(p, u) {
      R(p, { sy: 0.96 });
      quadWalk(p, u, { amp: 0.34, lift: 0.32, bob: 0.45, nod: 0.03, tail: 0.12 });
    },
    attacks: {
      claw: {
        zh: "爪擊（talons）",
        type: "melee",
        ms: 640,
        fn(p, u) {
          R(p, { dx: kf(u, [[0, 0], [0.25, -1.5], [0.45, 4], [0.6, 3], [1, 0]]), sy: kf(u, [[0, 1], [0.25, 0.92], [0.45, 1.03], [1, 1]]) });
          A(p, "FN", { rot: kf(u, [[0, 0], [0.28, -1.3], [0.45, 0.35], [0.6, 0.1], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.25, -0.15], [0.45, 0.15], [1, 0]]) });
          A(p, "tail", { rot: 0.3 * bump(u, 0.1, 0.7) });
          slashFx(p, u, 0.4, 0.58, 29, -12, "#ffffff", 6);
        },
      },
      upcut: {
        zh: "反手上撩爪（壓低身體、前爪由下往上）",
        type: "melee2",
        ms: 1000,
        hitF: 6,
        fn(p, u, e) {
          const k = (pts: KF): number => kfN(u, 11, pts);
          const f = Math.round(u * 11);
          const rot = k([[0, 0], [1, 0.05], [2, 0.09], [3, 0.1], [4, 0.1], [5, -0.24], [6, -0.56], [7, -0.5], [8, -0.22], [9, -0.07], [10, -0.01], [11, 0]]);
          R(p, {
            rot,
            dx: k([[0, 0], [2, -1], [3, -1.5], [4, -1.5], [5, 2], [6, 5], [7, 5], [8, 3], [9, 1], [10, 0.3], [11, 0]]),
            dy: k([[0, 0], [1, 2.4], [2, 3.6], [3, 4.2], [4, 4.2], [5, 1.5], [6, -0.5], [7, -0.3], [8, 0], [11, 0]]),
            pivot: [-9.5, -12],
          });
          plant(p, e, [["FF"], ["BN"], ["BF"]]);
          if (f <= 4 || f >= 10) plant(p, e, [["FN"]]);
          else A(p, "FN", { rot: k([[5, -1.15], [6, -1.4], [7, -1.62], [8, -1.15], [9, -0.45]]) - rot, sy: 1.12, sx: 1.08 });
          A(p, "head", { rot: k([[0, 0], [2, 0.12], [3, 0.14], [4, 0.14], [5, 0.12], [6, 0.38], [7, 0.24], [8, 0.02], [10, 0], [11, 0]]), dy: k([[4, 0], [6, -1.5], [7, -1.5], [8, -0.4], [9, 0]]) });
          A(p, "tail", { rot: k([[0, 0], [3, -0.25], [4, -0.3], [6, 0.55], [11, 0]]) });
          // 白弧：以肩為圓心、半徑到爪尖外一點，前端跟著爪尖、尾端拖在爪走過的下方；尾端不低於地面上 2 單位
          if (f >= 5 && f <= 7) {
            const [sx, sy] = ptOf(p, e, "FN", 7, -12);
            const [px, py] = ptOf(p, e, "FN", 7.6, 0);
            const r = Math.hypot(px - sx, py - sy) + 5;
            const a1 = Math.atan2(py - sy, px - sx) - 0.12;
            const a0 = Math.min(a1 + [0.9, 1.15, 0.55][f - 5]!, Math.asin(cl((-2 - sy) / r, -1, 1)));
            FX(p, { k: "sweep", x: sx, y: sy, r, a0, a1, w: f === 7 ? 1.6 : 3 });
          }
        },
      },
      pounce: {
        zh: "衝鋒撲擊（衝鋒撞擊）",
        type: "charge",
        ms: 860,
        fn(p, u) {
          const air = seg(u, 0.3, 0.66);
          R(p, {
            dx: kf(u, [[0, 0], [0.3, -2], [0.66, 14], [0.76, 15], [1, 0]]),
            dy: u > 0.3 && u < 0.66 ? -9 * Math.sin(Math.PI * air) : 0,
            rot: kf(u, [[0, 0], [0.3, 0.04], [0.42, -0.2], [0.6, 0.18], [0.7, 0], [1, 0]]),
            sy: kf(u, [[0, 1], [0.3, 0.86], [0.38, 1.05], [0.66, 1], [0.72, 0.9], [0.8, 1]]),
            pivot: [0, -6],
          });
          for (const g of ["FN", "FF"]) A(p, g, { rot: -1.0 * bump(u, 0.32, 0.68) });
          for (const g of ["BN", "BF"]) A(p, g, { rot: 0.8 * bump(u, 0.3, 0.66) });
          A(p, "tail", { rot: -0.3 * bump(u, 0.3, 0.7) });
          if (u > 0.66 && u < 0.86) FX(p, { k: "dust", x: 18, y: -1, r: 3.5, a: 1 - seg(u, 0.66, 0.86) });
          p.shadow = 1 - 0.3 * Math.sin(Math.PI * air);
        },
      },
    },
    death(p, u) {
      deathQuad(p, u, 11, { headRot: 0.3, headDy: 2.5 });
    },
  },
  lizard: {
    kind: "quad",
    mouth: [27, -11],
    units: "餘燼蜥、寒燼蜥、殼縫餘燼蜥、熔爐母獸",
    idle(p, u) {
      breathe(p, u, 0.03);
      A(p, "tail", { rot: 0.1 * S(u, 1) });
      R(p, { dy: -0.8 * Math.max(0, S(u, 2, 0.1)) });
      A(p, "head", { rot: -0.06 * Math.max(0, S(u, 2, 0.1)) });
    },
    move(p, u) {
      quadWalk(p, u, { amp: 0.5, lift: 0.35, bob: 0.3, nod: 0 });
      A(p, "body", { rot: 0.05 * S(u, 1) });
      A(p, "tail", { rot: -0.18 * S(u, 1, 0.1) });
      A(p, "head", { rot: -0.06 * S(u, 1) });
    },
    attacks: {
      bite: {
        zh: "咬（fangs／餘燼啃咬）",
        type: "melee",
        ms: 660,
        fn(p, u, e) {
          R(p, { dx: kf(u, [[0, 0], [0.28, -2], [0.45, 7], [0.6, 6], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.28, -0.38], [0.42, 0.22], [0.6, 0.1], [1, 0]]) });
          A(p, "tail", { rot: kf(u, [[0, 0], [0.28, 0.2], [0.45, -0.15], [1, 0]]) });
          for (const g of ["FN", "FF"]) A(p, g, { kx: -0.35 * bump(u, 0.25, 0.7) });
          if (e.r.mat === "magma" && u > 0.42 && u < 0.62) {
            const c = elc(e.r, ELEM.fire);
            FX(p, { k: "burst", x: 36, y: -10, r: 3 + 3 * seg(u, 0.42, 0.62), c: c[0], c2: c[1], a: 1 - seg(u, 0.42, 0.62) });
          }
          chompFx(p, u, 0.4, 0.58, 36, -11);
        },
      },
      tailover: {
        zh: "掄尾砸擊（前翻掄尾砸在身前，翻完一圈落地再跳回）",
        type: "melee2",
        ms: 1250,
        hitF: 6,
        fn(p, u, e) {
          // 整隻前翻把臀部帶到身前上方，尾巴跟著臀部從上方掄下來（尾根不離開臀部、尾巴不拉長）；尾巴分段彎；
          // 砸完順著同一方向翻完一圈、四腳落在落點後方，再跳一步回原位。
          const f = Math.round(u * 14);
          const c0: readonly [number, number] = [2, -8];
          const [deg, tr, bd, hr, an, wx, wy, lg] = TAILOVER[f]!;
          const th = (deg * Math.PI) / 180;
          A(p, "tail", { rot: tr });
          A(p, "head", { rot: hr });
          const tipL = bd !== null ? bendTail(p, bd) : LZ_TIP;
          const ta = tipL[0] + 8;
          const tb = tipL[1] + 7.5;
          const loc: readonly [number, number] = an === "s" ? [10, -8] : an === "t" ? [-8 + ta * Math.cos(tr) - tb * Math.sin(tr), -7.5 + ta * Math.sin(tr) + tb * Math.cos(tr)] : c0;
          const a = loc[0] - c0[0];
          const b = loc[1] - c0[1];
          const cs = Math.cos(th);
          const sn = Math.sin(th);
          R(p, { rot: th, dx: wx - c0[0] - (a * cs - b * sn), dy: wy - c0[1] - (a * sn + b * cs), pivot: c0 });
          const FR = ["FN", "FF"] as const;
          const HI = ["BN", "BF"] as const;
          const air = (gs: readonly string[], rot: number, sy: number): void => gs.forEach((g, i) => A(p, g, { rot: rot * (i > 0 ? 0.7 : 1), sy }));
          if (lg[0] === "p") plant(p, e, [...FR, ...HI].map((g) => [g, lg[1] ?? 0, lg[2] ?? 0] as const));
          else if (lg[0] === "f") {
            plant(p, e, FR.map((g) => [g] as const));
            air(HI, lg[1], lg[2]);
          } else if (lg[0] === "h") {
            plant(p, e, HI.map((g) => [g, lg[1], 0] as const));
            air(FR, lg[2], lg[3]);
          } else {
            air(FR, lg[1], lg[3]);
            air(HI, lg[2], lg[3]);
          }
          p.shadow = 1 - 0.3 * cl(-(p.root.dy ?? 0) / 18);
          if (f >= 5 && f <= 8) {
            const [tx, ty] = ptOf(p, e, "tail", tipL[0], tipL[1]);
            const c = elc(e.r, ELEM.fire);
            const HX = 47;
            if (f <= 6) {
              const [cx, cy] = ptOf(p, e, "tail", -8, -7.5);
              const a1 = Math.atan2(ty - cy, tx - cx);
              FX(p, { k: "sweep", x: cx, y: cy, r: Math.hypot(tx - cx, ty - cy), a0: a1 - 1.25, a1, w: 2.8 });
            }
            if (f >= 6) {
              const q = (f - 6) / 2;
              FX(p, { k: "dust", x: HX + 7 + 3 * q, y: -1, r: 3 + 2 * q, a: 1 - 0.7 * q });
              FX(p, { k: "dust", x: HX + 13 + 4 * q, y: -1, r: 2.2 + 1.6 * q, a: 1 - 0.7 * q });
            }
            if (f === 6) FX(p, { k: "burst", x: tx + 4, y: Math.min(ty - 2, -7), r: 6.5, c: e.r.mat === "magma" ? c[0] : "#ffffff", c2: e.r.mat === "magma" ? c[1] : "#ffe9a8" });
          }
        },
      },
      cast: {
        zh: "寒霜（口吐冰彈）",
        type: "cast",
        ms: 860,
        fn(p, u, e) {
          // 投射物顏色：有元素用元素色；沒元素依材質（熔岩＝火、其他＝冰）；冰是冰晶、其他是火球
          const c = e.r.element !== undefined ? elc(e.r, ELEM.ice) : e.r.mat === "magma" ? ELEM.fire : ELEM.ice;
          const ice = c === ELEM.ice;
          R(p, { dx: kf(u, [[0, 0], [0.4, -1.5], [0.5, 1.5], [1, 0]]), rot: kf(u, [[0, 0], [0.4, -0.08], [0.5, 0.03], [1, 0]]), pivot: [-6, 0] });
          A(p, "head", { rot: kf(u, [[0, 0], [0.4, -0.35], [0.5, 0.15], [1, 0]]) });
          charge(p, u, 0.1, 0.45, [28, -13], c);
          shot(p, u, 0.46, 0.66, [30, -11], c, ice ? { kind: "shard", r: 2.4 } : { r: 2.4 });
        },
      },
      summon: {
        zh: "產下幼蜥（召喚）",
        type: "summon",
        ms: 1150,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.fire);
          R(p, { sy: kf(u, [[0, 1], [0.35, 0.9], [0.45, 1.06], [0.6, 1], [1, 1]]), rot: kf(u, [[0, 0], [0.35, 0.05], [0.45, -0.06], [0.6, 0], [1, 0]]), pivot: [0, 0] });
          A(p, "tail", { rot: kf(u, [[0, 0], [0.35, 0.45], [0.5, -0.1], [0.7, 0], [1, 0]]) });
          // CB-2c：蛋、孵化的爆開都標 lobbed：戰場上由 eggArc 拋到指定格，這裡只留給樣張頁（出手格仍由 burst 決定）
          const q = proj(u, EGG_FROM_U, 0.68, EGG_START[0], EGG_START[1], 34, 0, 18);
          if (q !== null) FX(p, { k: "egg", x: q[0], y: q[1], s: EGG_SCALE, c: c[0], rot: u * 8, lobbed: true });
          if (u >= 0.68) {
            const wob = u < 0.85 ? 0.25 * Math.sin(u * 70) : 0;
            FX(p, { k: "egg", x: 34, y: 0, s: EGG_SCALE, c: c[0], rot: wob, crack: u > 0.8, lobbed: true });
            if (u > 0.86) {
              FX(p, { k: "glow", x: 34, y: -4, r: 10, c: c[1], a: 1 - seg(u, 0.86, 1), lobbed: true });
              FX(p, { k: "burst", x: 34, y: -4, r: 5, c: c[0], c2: c[1], a: 1 - seg(u, 0.86, 1), lobbed: true });
            }
          }
        },
      },
    },
    death(p, u) {
      deathQuad(p, u, 8, { headRot: 0.3, headDy: 3 });
      const k = sm(seg(u, 0.3, 0.8));
      A(p, "tail", { rot: 0.4 * k });
      for (const g of ["FN", "FF"]) A(p, g, { kx: -0.9 * k, sy: 1.5 });
      for (const g of ["BN", "BF"]) A(p, g, { kx: 0.9 * k, sy: 1.5 });
      A(p, "body", { sy: 1 - 0.12 * k });
    },
  },
  shell: {
    kind: "shell",
    mouth: [21, -8],
    units: "噴岩龜",
    idle(p, u) {
      breathe(p, u, 0.02);
      A(p, "head", { dx: -0.8 * (0.5 - 0.5 * Cn(u, 1)), rot: 0.06 * S(u, 2) });
    },
    move(p, u) {
      quadWalk(p, u, { amp: 0.28, lift: 0.3, bob: 0.4, nod: 0.04 });
      R(p, { rot: 0.02 * S(u, 2) });
    },
    attacks: {
      lob: {
        zh: "背火山拋射（fire_staff）",
        type: "cast",
        ms: 950,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.fire);
          R(p, { sy: kf(u, [[0, 1], [0.3, 0.93], [0.4, 1.05], [0.55, 1], [1, 1]]) });
          A(p, "head", { dx: kf(u, [[0, 0], [0.3, -2], [0.6, 0], [1, 0]]) });
          quadLegsTuck(p, 0.2 * bump(u, 0, 0.45));
          if (u > 0.36 && u < 0.5) FX(p, { k: "burst", x: -2, y: -30, r: 4 + 3 * seg(u, 0.36, 0.5), c: c[0], c2: c[1], a: 1 - seg(u, 0.36, 0.5) });
          shot(p, u, 0.38, 0.78, [-2, -30], c, { h: 26, y1: -2, r: 3 });
        },
      },
      breath: {
        zh: "火牆（噴吐）",
        type: "breath",
        ms: 1050,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.fire);
          A(p, "head", { dx: kf(u, [[0, 0], [0.25, -1.5], [0.35, 2], [0.85, 2], [1, 0]]), rot: kf(u, [[0, 0], [0.25, -0.2], [0.35, 0.1], [0.85, 0.1], [1, 0]]) });
          R(p, { dx: kf(u, [[0, 0], [0.35, -1], [0.85, -1], [1, 0]]) });
          if (u > 0.32 && u < 0.7) FX(p, { k: "cone", x: 22, y: -7, max: 22, spread: 5, len: seg(u, 0.32, 0.5), c: c[0], c2: c[1], a: 1 - seg(u, 0.6, 0.7), t: u * 12 });
          if (u > 0.5)
            for (let i = 0; i < 4; i++) {
              const k = seg(u, 0.5 + i * 0.05, 0.62 + i * 0.05);
              if (k > 0) FX(p, { k: "flame", x: 34 + i * 6, y: 0, h: (9 + 3 * Math.sin(u * 30 + i)) * k * (1 - seg(u, 0.88, 1)), c: c[0], c2: c[1] });
            }
        },
      },
    },
    death(p, u) {
      p.flash = u < 0.12 ? 0.7 : 0;
      const k = sm(seg(u, 0.15, 0.6));
      A(p, "head", { dx: -3 * k, sx: 1 - 0.5 * k, rot: 0.3 * k });
      quadLegsTuck(p, 0.75 * k);
      R(p, { dy: 6.5 * k, rot: 0.08 * sm(seg(u, 0.55, 0.9)), pivot: [10, 0] });
      p.shadow = 1 - 0.2 * k;
    },
  },
  beetle: {
    kind: "crawler",
    mouth: [22, -14],
    units: "熔岩甲蟲、熔核領主",
    idle(p, u) {
      breathe(p, u, 0.02);
      A(p, "head", { rot: 0.06 * S(u, 2) });
      A(p, "N2", { kx: -0.2 * Math.max(0, S(u, 1, 0.3)) });
    },
    move(p, u) {
      hexWalk(p, u, BT_TRI, { amp: 0.5, lift: 0.35, bob: 0.4 });
      A(p, "head", { rot: 0.04 * S(u, 2) });
    },
    attacks: {
      horn: {
        zh: "角頂（stone_fist）",
        type: "melee",
        ms: 680,
        fn(p, u) {
          R(p, { dx: kf(u, [[0, 0], [0.3, -1], [0.48, 5], [0.62, 4], [1, 0]]), rot: kf(u, [[0, 0], [0.3, 0.1], [0.48, 0.06], [0.58, -0.14], [0.75, 0], [1, 0]]), pivot: [14, 0] });
          A(p, "head", { rot: kf(u, [[0, 0], [0.3, 0.28], [0.48, 0.15], [0.58, -0.55], [0.8, 0], [1, 0]]) });
          slashFx(p, u, 0.52, 0.68, 30, -20, "#ffffff", 5);
        },
      },
      ram: {
        zh: "破城衝撞（衝鋒）",
        type: "charge",
        ms: 880,
        fn(p, u) {
          R(p, { dx: kf(u, [[0, 0], [0.3, -3], [0.55, 14], [0.62, 12.5], [1, 0]]), rot: kf(u, [[0, 0], [0.3, 0.05], [0.55, 0.08], [0.62, -0.06], [0.8, 0], [1, 0]]), pivot: [12, 0] });
          A(p, "head", { rot: kf(u, [[0, 0], [0.3, 0.2], [0.55, 0.2], [0.62, -0.25], [0.85, 0], [1, 0]]) });
          if (u < 0.6) hexWalk(p, (u * 3) % 1, BT_TRI, { amp: 0.5, lift: 0.35, bob: 0 });
          if (u > 0.5 && u < 0.75) {
            FX(p, { k: "burst", x: 40, y: -10, r: 5 + 3 * seg(u, 0.5, 0.75), c: "#ffffff", c2: "#ffe08a", a: 1 - seg(u, 0.55, 0.75) });
            FX(p, { k: "dust", x: 4, y: -1, r: 3.5, a: 1 - seg(u, 0.5, 0.75) });
          }
        },
      },
      burst: {
        zh: "熔流潰堤（殼爆發）",
        type: "area",
        ms: 950,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.fire);
          R(p, { sy: kf(u, [[0, 1], [0.35, 0.88], [0.45, 1.08], [0.6, 1], [1, 1]]), sx: kf(u, [[0, 1], [0.35, 1.04], [0.45, 1.06], [0.6, 1], [1, 1]]), dy: u < 0.35 ? 0.4 * Math.sign(Math.sin(u * 80)) * seg(u, 0.1, 0.35) : 0 });
          quadLegsTuck(p, 0);
          for (const g of ["N0", "N1", "N2", "F0", "F1", "F2"]) A(p, g, { sy: 1 - 0.3 * bump(u, 0.1, 0.5) });
          p.flash = u > 0.2 && u < 0.42 ? 0.35 : 0;
          p.flashColor = c[0];
          if (u > 0.4) {
            const k = seg(u, 0.4, 1);
            FX(p, { k: "ring", x: 0, rx: 10 + 26 * k, c: c[0], a: 1 - k });
            FX(p, { k: "glow", x: 0, y: -12, r: 18 + 8 * k, c: c[0], a: (1 - k) * 0.8 });
            for (let i = 0; i < 5; i++) {
              const an = -Math.PI * (0.15 + 0.7 * (i / 4));
              const d = 8 + 20 * k;
              FX(p, { k: "orb", x: Math.cos(an) * d, y: -12 + Math.sin(an) * d * 0.8 + 18 * k * k, r: 1.6, c: c[0], c2: c[1], a: 1 - k });
            }
          }
        },
      },
    },
    death(p, u) {
      // 翻肚：彈起沿長軸翻面，腳朝上亂踢後停
      p.flash = u < 0.12 ? 0.7 : 0;
      const f = sm(seg(u, 0.15, 0.55));
      R(p, { sy: flipSy(f), dy: -7 * Math.sin(Math.PI * seg(u, 0.15, 0.55)), pivot: [0, -10] });
      A(p, "spikes", { sy: 1 - 0.85 * f });
      const kick = u > 0.55 ? Math.sin(u * 46) * (1 - seg(u, 0.55, 0.92)) : 0;
      ["N0", "N1", "N2", "F0", "F1", "F2"].forEach((g, i) => A(p, g, { kx: 0.4 * kick * (i % 2 ? 1 : -1), sy: 1 - 0.25 * f }));
      A(p, "head", { rot: 0.2 * f });
      p.shadow = 1 - 0.1 * f;
    },
  },
  spider: {
    kind: "crawler",
    mouth: [11, -6],
    units: "（目前沒有單位）",
    idle(p, u) {
      A(p, "abd", { sy: 1 + 0.04 * S(u, 1), sx: 1 + 0.02 * S(u, 1) });
      ["N0", "N1", "N2", "N3"].forEach((g, i) => A(p, g, { rot: 0.05 * S(u, 1, i * 0.25) }));
      A(p, "head", { rot: 0.04 * S(u, 2) });
    },
    move(p, u) {
      hexWalk(p, u, SP_TETRA, { amp: 0.32, lift: 2.2, bob: 0.6, rot: true });
      A(p, "abd", { rot: 0.05 * S(u, 2) });
    },
    attacks: {
      bite: {
        zh: "毒咬（前腳舉起撲咬）",
        type: "melee",
        ms: 720,
        fn(p, u) {
          R(p, { rot: kf(u, [[0, 0], [0.35, -0.22], [0.5, 0.1], [0.65, 0.05], [1, 0]]), pivot: [-14, 0], dx: kf(u, [[0, 0], [0.35, -1], [0.5, 6], [0.62, 5], [1, 0]]) });
          for (const g of ["N3", "F3"]) A(p, g, { rot: kf(u, [[0, 0], [0.35, -0.9], [0.5, 0.25], [1, 0]]) });
          for (const g of ["N2", "F2"]) A(p, g, { rot: kf(u, [[0, 0], [0.35, -0.5], [0.5, 0.15], [1, 0]]) });
          A(p, "head", { dx: 2 * bump(u, 0.4, 0.65), rot: 0.15 * bump(u, 0.4, 0.65) });
          if (u > 0.45 && u < 0.7) FX(p, { k: "burst", x: 20, y: -6, r: 3 + 2 * seg(u, 0.45, 0.7), c: "#7ddc3a", c2: "#d6f59a", a: 1 - seg(u, 0.45, 0.7) });
        },
      },
    },
    death(p, u) {
      p.flash = u < 0.12 ? 0.7 : 0;
      const f = sm(seg(u, 0.15, 0.5));
      const c = sm(seg(u, 0.45, 0.9));
      R(p, { sy: flipSy(f), dy: -6 * Math.sin(Math.PI * seg(u, 0.15, 0.5)), pivot: [-2, -10.5] });
      A(p, "spikes", { sy: 1 - 0.85 * f });
      ["N0", "N1", "N2", "N3"].forEach((g) => A(p, g, { rot: -0.7 * c, sy: 1 - 0.3 * c }));
      ["F0", "F1", "F2", "F3"].forEach((g) => A(p, g, { rot: 0.7 * c, sy: 1 - 0.3 * c }));
    },
  },
  serpent: {
    kind: "serpent",
    mouth: [19, -25],
    units: "（目前沒有單位）",
    idle(p, u) {
      neck(p, 0.07 * S(u, 1), -0.05 * S(u, 1));
      A(p, "coil", { sy: 1 + 0.03 * S(u, 1, 0.25) });
    },
    move(p, u) {
      A(p, "coil", { kx: 0.18 * S(u, 1), sx: 1 + 0.06 * S(u, 2) });
      neck(p, -0.1 * S(u, 1, 0.2), 0.05 * S(u, 1, 0.4));
      R(p, { dx: 0.8 * S(u, 2) });
    },
    attacks: {
      strike: {
        zh: "突咬",
        type: "melee",
        ms: 620,
        fn(p, u) {
          const k = kf(u, [[0, 0], [0.3, 0.32], [0.45, -0.48], [0.58, -0.42], [1, 0]]);
          neck(p, k, kf(u, [[0, 0], [0.3, -0.3], [0.45, 0.2], [1, 0]]));
          A(p, "coil", { kx: 0.1 * bump(u, 0.35, 0.7) });
          R(p, { dx: 2 * bump(u, 0.35, 0.7) });
          chompFx(p, u, 0.4, 0.58, 34, -24);
        },
      },
    },
    death(p, u) {
      p.flash = u < 0.12 ? 0.7 : 0;
      const k = sm(seg(u, 0.2, 0.8));
      A(p, "neck", { sy: 1 - 0.75 * k, kx: -0.3 * k });
      A(p, "head", { dx: 6 * k, dy: 16 * k, rot: 0.25 * k });
      A(p, "coil", { sy: 1 - 0.15 * k });
    },
  },
  ooze: {
    kind: "ooze",
    mouth: [8, -10],
    units: "熔核蛞蝓",
    idle(p, u) {
      R(p, { sx: 1 + 0.04 * S(u, 1), sy: 1 - 0.04 * S(u, 1), kx: 0.04 * S(u, 1, 0.25) });
      A(p, "face", { dy: 0.5 * S(u, 1) });
    },
    move(p, u) {
      R(p, { kx: 0.12 * S(u, 1), sx: 1 + 0.1 * S(u, 1, 0.25), sy: 1 - 0.09 * S(u, 1, 0.25), dx: 1.2 * S(u, 1, 0.1) });
      A(p, "face", { dx: 0.8 * S(u, 1) });
    },
    attacks: {
      slam: {
        zh: "彈跳壓（stone_fist）",
        type: "melee",
        ms: 820,
        fn(p, u, e) {
          const air = seg(u, 0.3, 0.56);
          R(p, {
            sy: kf(u, [[0, 1], [0.28, 0.7], [0.36, 1.25], [0.55, 1.1], [0.62, 0.6], [0.78, 1.08], [0.9, 0.97], [1, 1]]),
            sx: kf(u, [[0, 1], [0.28, 1.25], [0.36, 0.85], [0.55, 0.92], [0.62, 1.4], [0.78, 0.95], [1, 1]]),
            dx: kf(u, [[0, 0], [0.3, 0], [0.58, 8], [0.75, 8], [1, 0]]),
            dy: u > 0.3 && u < 0.58 ? -12 * Math.sin(Math.PI * seg(u, 0.3, 0.58)) : 0,
          });
          A(p, "face", { dy: kf(u, [[0, 0], [0.28, 2], [0.36, -2], [0.62, 3], [1, 0]]) });
          if (u > 0.58 && u < 0.85) {
            const k = seg(u, 0.58, 0.85);
            FX(p, { k: "blob", x: 8 - 16 - 4 * k, y: -1, rx: 2.4, ry: 1.4, c: e.r.base, a: 1 - k });
            FX(p, { k: "blob", x: 8 + 16 + 4 * k, y: -1, rx: 2.4, ry: 1.4, c: e.r.base, a: 1 - k });
            FX(p, { k: "dust", x: 8, y: -1, r: 5, a: 1 - k });
          }
          p.shadow = 1 - 0.35 * Math.sin(Math.PI * air);
        },
      },
      spit: {
        zh: "燈油瓶（拋吐油團）",
        type: "cast",
        ms: 900,
        fn(p, u, e) {
          R(p, { sy: kf(u, [[0, 1], [0.32, 0.8], [0.42, 1.18], [0.55, 0.96], [0.7, 1], [1, 1]]), sx: kf(u, [[0, 1], [0.32, 1.15], [0.42, 0.88], [0.55, 1.03], [1, 1]]), kx: kf(u, [[0, 0], [0.32, -0.08], [0.42, 0.12], [0.6, 0], [1, 0]]) });
          A(p, "face", { dy: kf(u, [[0, 0], [0.32, 1.5], [0.42, -2], [0.7, 0], [1, 0]]) });
          // 油團亮一階＋亮邊；落地爆開濺油、油灘亮邊；有元素時換元素色
          const oc = e.r.element !== undefined ? elc(e.r, ELEM.fire)[0] : "#6a5640";
          const rim = e.r.element !== undefined ? elc(e.r, ELEM.fire)[1] : "#d8c08a";
          const q = proj(u, 0.4, 0.74, 8, -16, 46, -2, 22);
          if (q !== null) FX(p, { k: "blob", x: q[0], y: q[1], r: 3.8, c: oc, rim, ranged: true });
          if (u > 0.74) {
            const k = seg(u, 0.74, 1);
            FX(p, { k: "blob", x: 46, y: 0, rx: 5 + 7 * k, ry: 1.6 + 0.6 * k, c: oc, rim, a: 1 - 0.2 * k, ranged: true });
            if (k < 0.7) FX(p, { k: "burst", x: 46, y: -3, r: 4 + 4 * k, c: oc, c2: rim, a: 1 - k / 0.7, ranged: true });
            for (let i = 0; i < 4; i++) {
              const dx = [-1, -0.4, 0.5, 1][i]!;
              FX(p, { k: "blob", x: 46 + dx * (4 + 9 * k), y: Math.min(-0.5, -2 - (7 - 2 * Math.abs(dx)) * Math.sin(Math.PI * k)), r: 1.3, c: oc, rim, a: 1 - 0.6 * k, ranged: true });
            }
          }
        },
      },
    },
    death(p, u) {
      p.flash = u < 0.12 ? 0.7 : 0;
      const k = sm(seg(u, 0.1, 0.8));
      R(p, { sy: 1 - 0.68 * k + 0.08 * Math.sin(u * 30) * (1 - k), sx: 1 + 0.55 * k });
      A(p, "face", { dy: 5 * k, a: 1 - 0.7 * k });
      p.alpha = 1 - 0.3 * sm(seg(u, 0.5, 1));
    },
  },
  golem: {
    kind: "golem",
    mouth: [-1, -29],
    units: "晶傀儡、碎晶傀儡、焦岩巨像",
    idle(p, u) {
      breathe(p, u, 0.015);
      A(p, "armN", { rot: -0.04 * S(u, 1) });
      A(p, "armF", { rot: 0.04 * S(u, 1) });
      A(p, "head", { rot: 0.04 * S(u, 1, 0.3) });
    },
    move(p, u) {
      ([["legN", 0], ["legF", 0.5]] as const).forEach(([g, ph]) => A(p, g, { kx: -0.28 * S(u, 1, ph), sy: 1 - 0.18 * Math.max(0, Cn(u, 1, ph)) }));
      R(p, { dy: -0.9 * Math.abs(Cn(u, 1, 0.25)), rot: 0.03 * S(u, 1) }); // 每步落地「咚」
      A(p, "armN", { rot: 0.22 * S(u, 1, 0.5) });
      A(p, "armF", { rot: 0.22 * S(u, 1) });
      A(p, "head", { rot: 0.03 * S(u, 2) });
    },
    attacks: {
      smash: {
        zh: "拳砸（stone_fist／碎岩擊）",
        type: "melee",
        ms: 920,
        fn(p, u) {
          A(p, "armN", { rot: kf(u, [[0, 0], [0.4, -2.7], [0.55, -0.75], [0.7, -0.7], [1, 0]]) });
          A(p, "armF", { rot: kf(u, [[0, 0], [0.4, 0.4], [0.55, -0.2], [1, 0]]) });
          R(p, { rot: kf(u, [[0, 0], [0.4, -0.09], [0.55, 0.13], [0.7, 0.1], [1, 0]]), pivot: [-3, 0], dx: kf(u, [[0, 0], [0.4, -1], [0.55, 3], [1, 0]]), dy: u > 0.55 && u < 0.65 ? 0.6 * Math.sign(Math.sin(u * 120)) : 0 });
          A(p, "head", { rot: kf(u, [[0, 0], [0.4, -0.12], [0.55, 0.15], [1, 0]]) });
          if (u > 0.53) {
            const k = seg(u, 0.53, 0.85);
            if (k < 1) {
              FX(p, { k: "burst", x: 27, y: -4, r: 4 + 3 * k, c: "#ffffff", c2: "#e8dcc8", a: 1 - k });
              FX(p, { k: "dust", x: 27, y: -1, r: 4 + 2 * k, a: 1 - k });
            }
          }
        },
      },
      quake: {
        zh: "雙拳震地（震地波）",
        type: "area",
        ms: 1100,
        fn(p, u, e) {
          // 雙臂一起舉過頭、一起砸地
          A(p, "armN", { rot: kf(u, [[0, 0], [0.42, -3.05], [0.55, -0.95], [0.75, -0.9], [1, 0]]) });
          // 遠側手臂：舉起時支點留在肩膀；砸下時肩膀往前滑進軀幹裡，拳頭落在近側拳頭左下方
          A(p, "armF", { rot: kf(u, [[0, 0], [0.42, -3.3], [0.55, -0.85], [0.75, -0.8], [1, 0]]), dx: kf(u, [[0, 0], [0.42, 0], [0.55, 16], [0.75, 16], [1, 0]]) });
          R(p, { rot: kf(u, [[0, 0], [0.42, -0.14], [0.55, 0.2], [0.75, 0.16], [1, 0]]), pivot: [-3, 0], dy: kf(u, [[0, 0], [0.42, -2.5], [0.55, 1], [0.75, 0.6], [1, 0]]) + (u > 0.55 && u < 0.68 ? 0.7 * Math.sign(Math.sin(u * 120)) : 0) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.42, -0.15], [0.55, 0.2], [1, 0]]) });
          if (u > 0.55) {
            const k = seg(u, 0.55, 1);
            for (let i = 0; i < 4; i++) {
              const q = cl(k * 1.6 - i * 0.18);
              if (q > 0 && q < 1) FX(p, { k: "rock", x: 24 + i * 10, y: 0, s: 2.6 * Math.sin(Math.PI * q) + 0.5, c: e.r.mat === "crystal" ? "#b8a8ff" : "#8a847e" });
            }
            FX(p, { k: "dust", x: 24 + 30 * k, y: -1, r: 3 + 2 * k, a: 1 - k });
          }
          quakeFx(p, u, 0.55, 22);
        },
      },
      cast: {
        zh: "核心聚雷（從胸口放出）",
        type: "cast",
        ms: 920,
        fn(p, u, e) {
          const c = e.r.element !== undefined ? elc(e.r, ELEM.lightning) : ELEM.lightning;
          A(p, "armN", { rot: kf(u, [[0, 0], [0.4, 0.7], [0.55, -0.9], [0.8, -0.6], [1, 0]]) });
          A(p, "armF", { rot: kf(u, [[0, 0], [0.4, 0.6], [0.55, -0.3], [1, 0]]) });
          R(p, { rot: kf(u, [[0, 0], [0.4, -0.06], [0.55, 0.04], [1, 0]]), pivot: [0, 0] });
          charge(p, u, 0.1, 0.46, [1, -29], c, 3.2);
          if (u > 0.48 && u < 0.72) {
            FX(p, { k: "bolt", x0: 3, y0: -29, x1: TGT, y1: -14, c: c[0], amp: 1 + 0.6 * Math.sin(u * 60), ranged: true });
            FX(p, { k: "glow", x: TGT, y: -14, r: 10, c: c[0], a: 1 - seg(u, 0.48, 0.72) * 0.6, ranged: true });
          }
        },
      },
    },
    death(p, u) {
      // 崩塌（QK-4b）：晃 → 軀幹沿裂縫斷成 3 塊落地、頭往後滾到一旁、兩隻手臂散落、腿垮成殘樁
      p.flash = u < 0.12 ? 0.7 : 0;
      const sh = u < 0.25 ? 0.6 * Math.sign(Math.sin(u * 120)) : 0;
      const k = sm(seg(u, 0.22, 0.72));
      const k2 = sm(seg(u, 0.3, 0.8));
      R(p, { dx: sh });
      p.split = {
        body: [
          { clip: GOLEM_LEFT, pivot: [-6, -16], dx: -3 * k, dy: 13 * k, rot: -0.35 * k },
          { clip: GOLEM_RIGHT, pivot: [6, -16], dx: 5 * k, dy: 13 * k, rot: 0.5 * k },
          { clip: GOLEM_TOP, pivot: [-2, -31], dx: -1 * k2 + 0.5 * bump(u, 0.7, 0.85), dy: 24 * k2 - 2 * bump(u, 0.78, 0.9), rot: -0.25 * k2 },
        ],
      };
      const roll = sm(seg(u, 0.25, 0.95));
      A(p, "head", { dy: 27 * sm(seg(u, 0.25, 0.6)) - 4 * bump(u, 0.6, 0.75), dx: -15 * roll, rot: -(1.6 + TAU) * roll });
      A(p, "armN", { dy: 30 * sm(seg(u, 0.3, 0.7)), dx: 0, rot: -1.5 * sm(seg(u, 0.3, 0.78)) });
      A(p, "armF", { dy: 17 * sm(seg(u, 0.28, 0.68)), dx: -3 * k, rot: 0.55 * k });
      for (const g of ["legN", "legF"]) A(p, g, { sy: 1 - 0.6 * k });
      A(p, "legN", { rot: 0.25 * k });
      A(p, "legF", { rot: -0.25 * k });
      if (u > 0.62 && u < 1) {
        FX(p, { k: "dust", x: -2, y: -1, r: 6, a: 1 - seg(u, 0.62, 1) });
        FX(p, { k: "dust", x: 24, y: -1, r: 3.5, a: 1 - seg(u, 0.7, 1) });
      }
    },
  },
  wisp: {
    kind: "wisp",
    mouth: [0, -20],
    units: "（灰燼之心另有頭目畫法）",
    idle(p, u) {
      R(p, { dy: -2 * S(u, 1) });
      A(p, "core", { sx: 1 + 0.04 * S(u, 2), sy: 1 + 0.04 * S(u, 2) });
      ORB_HOME.forEach((_, i) => A(p, `orb${i}`, { dx: 2 * Cn(u, 1, i / 3), dy: 1.4 * S(u, 1, i / 3) }));
    },
    move(p, u) {
      R(p, { dy: -1.5 - 1.5 * S(u, 1), rot: 0.1 });
      ORB_HOME.forEach((_, i) => A(p, `orb${i}`, { dx: -2.5 + 1.5 * Cn(u, 1, i / 3), dy: 1.2 * S(u, 1, i / 3) }));
    },
    attacks: {
      shards: {
        zh: "晶刺射出（從核心）",
        type: "cast",
        ms: 880,
        fn(p, u, e) {
          R(p, { dy: -1.5 * S(u, 1) });
          ORB_HOME.forEach(([hx, hy], i) => {
            const fx = 13 - hx;
            const fy = -3 + (i - 1) * 4 - hy;
            const g = seg(u, 0.05 + i * 0.05, 0.35 + i * 0.05);
            const fly = seg(u, 0.42 + i * 0.06, 0.62 + i * 0.06);
            const back = seg(u, 0.78, 1);
            if (fly >= 1) A(p, `orb${i}`, { a: back, sx: 0.4 + 0.6 * back, sy: 0.4 + 0.6 * back }); // 命中後回到原位重新長出來
            else A(p, `orb${i}`, { dx: fx * sm(g) + (TGT - 13) * fly, dy: fy * sm(g), rot: 0.6 * g + 0.97 * (fly > 0 ? 1 : 0) });
            if (u > 0.62 + i * 0.06 && u < 0.78 + i * 0.06) FX(p, { k: "burst", x: TGT, y: -20 + (i - 1) * 4, r: 4, c: e.r.base, c2: "#ffffff", a: 1 - seg(u, 0.62 + i * 0.06, 0.78 + i * 0.06), ranged: true });
          });
          A(p, "core", { sx: 1 + 0.15 * bump(u, 0.3, 0.55), sy: 1 + 0.15 * bump(u, 0.3, 0.55) });
        },
      },
      pulse: {
        zh: "晶脈衝（範圍爆發）",
        type: "area",
        ms: 940,
        fn(p, u, e) {
          const k = kf(u, [[0, 0], [0.35, -0.25], [0.48, 0.3], [0.7, 0.05], [1, 0]]);
          A(p, "core", { sx: 1 + k, sy: 1 + k });
          ORB_HOME.forEach(([hx, hy], i) => A(p, `orb${i}`, { dx: hx * k * 2.2, dy: hy * k * 2.2 }));
          R(p, { dy: -1 * S(u, 1) });
          p.flash = u > 0.42 && u < 0.52 ? 0.5 : 0;
          p.flashColor = e.r.accent ?? "#ffffff";
          if (u > 0.45) {
            const q = seg(u, 0.45, 1);
            FX(p, { k: "ring", x: 0, rx: 8 + 30 * q, c: e.r.base, a: 1 - q });
            FX(p, { k: "glow", x: 0, y: -20, r: 16 + 10 * q, c: e.r.base, a: 1 - q });
          }
        },
      },
    },
    death(p, u, e) {
      // 碎裂：閃白、核心縮掉，晶片往外噴再落地
      p.flash = u < 0.2 ? 0.9 : 0;
      const k = seg(u, 0.18, 0.4);
      A(p, "core", { sx: 1 - 0.85 * sm(k), sy: 1 - 0.85 * sm(k), a: 1 - sm(k), rot: 0.6 * k });
      ORB_HOME.forEach(([hx, hy], i) => {
        const f = seg(u, 0.2, 0.75);
        A(p, `orb${i}`, { dx: hx * 0.8 * f, dy: (20 - hy - 2.4) * f * f - 8 * Math.sin(Math.PI * f) * (1 - f), rot: (i - 1) * 2 * f + 1.57 * sm(f) });
      });
      R(p, { dy: 0 });
      p.shadow = 1 - 0.6 * sm(seg(u, 0.2, 0.6));
      if (u > 0.2)
        for (let i = 0; i < 6; i++) {
          const an = -Math.PI * (0.1 + 0.8 * (i / 5));
          const f = seg(u, 0.2, 0.8);
          const d = 4 + 16 * f;
          FX(p, { k: "shard", x: Math.cos(an) * d * (i % 2 ? 1 : 0.7), y: Math.min(-1.5, -20 + Math.sin(an) * d * 0.6 + 26 * f * f), rot: an + f * 4 * (i % 2 ? 1 : -1), s: 1.8, c: lighten(e.r.base, 0.2) });
        }
    },
  },
  wraith: {
    kind: "wraith",
    mouth: [2, -42],
    units: "霧魅、熔晶魅",
    idle(p, u) {
      R(p, { dy: -1.5 * S(u, 1) });
      A(p, "body", { kx: 0.06 * S(u, 1, 0.2) });
      A(p, "armN", { rot: 0.1 * S(u, 1, 0.1) });
      A(p, "armB", { rot: 0.1 * S(u, 1, 0.35) });
      A(p, "head", { rot: 0.05 * S(u, 1, 0.5) });
    },
    move(p, u) {
      R(p, { dy: -1.5 - 1 * S(u, 2), rot: 0.08 });
      A(p, "body", { kx: 0.12 + 0.05 * S(u, 1) });
      A(p, "armN", { rot: 0.35 + 0.08 * S(u, 1) });
      A(p, "armB", { rot: 0.4 + 0.08 * S(u, 1, 0.3) });
    },
    attacks: {
      claw: {
        zh: "影刃爪（shade_blades）",
        type: "melee",
        ms: 680,
        fn(p, u, e) {
          R(p, { dx: kf(u, [[0, 0], [0.3, -2], [0.5, 7], [0.65, 6], [1, 0]]), rot: kf(u, [[0, 0], [0.3, -0.06], [0.5, 0.14], [1, 0]]), pivot: [0, -20] });
          A(p, "armN", { rot: kf(u, [[0, 0], [0.3, 1.0], [0.5, -1.5], [0.65, -1.2], [1, 0]]) });
          A(p, "armB", { rot: kf(u, [[0, 0], [0.35, 0.9], [0.58, -1.2], [0.72, -1], [1, 0]]) });
          A(p, "body", { kx: kf(u, [[0, 0], [0.3, -0.1], [0.5, 0.2], [1, 0]]) });
          slashFx(p, u, 0.45, 0.65, 30, -26, e.r.element !== undefined ? elc(e.r, ELEM.shadow)[0] : "#c8a8f0", 7);
        },
      },
      blink: {
        zh: "閃現（淡出→淡入）",
        type: "blink",
        ms: 900,
        fn(p, u, e) {
          const out = sm(seg(u, 0.05, 0.38));
          const inn = sm(seg(u, 0.58, 0.9));
          const v = out * (1 - inn);
          R(p, { sx: 1 - 0.6 * v, sy: 1 + 0.35 * v, dy: -4 * v });
          p.alpha = 1 - v;
          for (let i = 0; i < 4; i++) {
            const an = (i / 4) * TAU + u * 6;
            const q = u < 0.5 ? seg(u, 0.1, 0.45) : seg(u, 0.55, 0.9);
            FX(p, { k: "puff", x: Math.cos(an) * (6 + 6 * q), y: -20 + Math.sin(an) * 9, r: 3.6 * (1 - q * 0.5), c: e.r.base, a: Math.sin(Math.PI * q) });
          }
        },
      },
      gaze: {
        zh: "威懾凝視（眼放恐懼波）",
        type: "cast",
        ms: 900,
        fn(p, u, e) {
          const c = e.r.element !== undefined ? elc(e.r, ELEM.shadow) : ELEM.shadow;
          R(p, { dx: kf(u, [[0, 0], [0.35, 2], [0.8, 2], [1, 0]]), rot: kf(u, [[0, 0], [0.35, 0.06], [0.8, 0.06], [1, 0]]), pivot: [0, -20] });
          A(p, "head", { dx: kf(u, [[0, 0], [0.35, 1.5], [0.8, 1.5], [1, 0]]), sx: 1 + 0.12 * bump(u, 0.3, 0.8), sy: 1 + 0.12 * bump(u, 0.3, 0.8) });
          A(p, "armN", { rot: kf(u, [[0, 0], [0.35, -0.6], [0.8, -0.5], [1, 0]]) });
          A(p, "armB", { rot: kf(u, [[0, 0], [0.35, 0.6], [0.8, 0.5], [1, 0]]) });
          if (u > 0.3 && u < 0.5) FX(p, { k: "glow", x: 3, y: -42, r: 8, c: c[1], a: bump(u, 0.3, 0.5) });
          for (let i = 0; i < 3; i++) {
            const q = seg(u, 0.38 + i * 0.1, 0.72 + i * 0.1);
            if (q > 0 && q < 1) FX(p, { k: "wave", x: 6 + (TGT - 6) * q, y: -42 + 26 * q, r: 3 + 5 * q, c: c[0], a: 1 - q * 0.6, ranged: true });
          }
        },
      },
    },
    death(p, u, e) {
      p.flash = u < 0.15 ? 0.8 : 0;
      const k = sm(seg(u, 0.1, 0.9));
      R(p, { dy: -7 * k, sx: 1 - 0.45 * k, sy: 1 + 0.4 * k });
      A(p, "body", { kx: 0.2 * Math.sin(u * 14) * k });
      A(p, "armN", { rot: 0.8 * k });
      A(p, "armB", { rot: 0.7 * k });
      p.alpha = 1 - k;
      p.shadow = 1 - k;
      for (let i = 0; i < 5; i++) {
        const q = seg(u, 0.15 + i * 0.08, 0.75 + i * 0.05);
        if (q > 0 && q < 1) FX(p, { k: "puff", x: (i - 2) * 5, y: -12 - i * 6 - 12 * q, r: 3 + 2 * q, c: e.r.base, a: 1 - q });
      }
    },
  },
  pylon: {
    kind: "pylon",
    mouth: [2, -22],
    units: "火／霧／雷之源晶柱、陣眼石靈",
    idle(p, u) {
      A(p, "ring", { dy: 1.2 * S(u, 1), sx: 1 + 0.05 * S(u, 2) });
      A(p, "eye", { sy: u > 0.82 && u < 0.92 ? 0.25 : 1 });
      A(p, "ob", { sy: 1 + 0.01 * S(u, 1) });
    },
    move(p, u) {
      const lift = -2.5 - 0.8 * S(u, 1);
      for (const g of ["ob", "eye", "ring"]) A(p, g, { dy: lift, rot: 0.05 * S(u, 1, 0.25), pivot: [0, -5] });
      A(p, "ring", { sx: 1 + 0.06 * S(u, 2) });
      p.shadow = 0.85;
    },
    attacks: {
      beam: {
        zh: "晶射線（fist 普攻）",
        type: "cast",
        ms: 920,
        fn(p, u, e) {
          const c: readonly [string, string] = e.r.element !== undefined ? elc(e.r, ELEM.lightning) : [e.r.accent ?? "#e4dcff", "#ffffff"];
          A(p, "ring", { sx: kf(u, [[0, 1], [0.38, 0.6], [0.5, 1.2], [0.8, 1.1], [1, 1]]), dy: kf(u, [[0, 0], [0.38, -3], [0.5, 1], [1, 0]]) });
          A(p, "eye", { sx: 1 + 0.4 * bump(u, 0.1, 0.8), sy: 1 + 0.4 * bump(u, 0.1, 0.8) });
          for (const g of ["ob", "eye", "ring"]) A(p, g, { dx: u > 0.45 && u < 0.75 ? -0.8 : 0 });
          charge(p, u, 0.1, 0.42, [3, -22], c, 2.6);
          if (u > 0.44 && u < 0.78) {
            const w = 3.2 * (1 - 0.6 * seg(u, 0.65, 0.78));
            FX(p, { k: "beam", x0: 4, y0: -22, x1: TGT, y1: -16, w, c: c[0], ranged: true });
            FX(p, { k: "glow", x: TGT, y: -16, r: 9, c: c[0], a: 0.8, ranged: true });
          }
        },
      },
      pulse: {
        zh: "晶脈衝（自身範圍）",
        type: "area",
        ms: 960,
        fn(p, u, e) {
          const c: readonly [string, string] = e.r.element !== undefined ? elc(e.r, ELEM.fire) : [e.r.base, "#ffffff"];
          A(p, "ring", { sx: kf(u, [[0, 1], [0.35, 0.7], [0.5, 1.9], [0.75, 1.3], [1, 1]]), a: kf(u, [[0, 1], [0.5, 0.6], [0.75, 0.3], [1, 1]]), dy: kf(u, [[0, 0], [0.35, -4], [0.5, 0], [1, 0]]) });
          p.flash = u > 0.4 && u < 0.52 ? 0.5 : 0;
          p.flashColor = c[0];
          if (u > 0.45)
            for (const d of [0, 0.15]) {
              const q = seg(u, 0.45 + d, 1);
              if (q > 0 && q < 1) FX(p, { k: "ring", x: 0, rx: 10 + 30 * q, c: c[0], a: 1 - q });
            }
          if (u > 0.4 && u < 0.7) FX(p, { k: "glow", x: 0, y: -22, r: 16, c: c[0], a: bump(u, 0.4, 0.7) });
        },
      },
    },
    death(p, u, e) {
      // 龜裂、往前倒、晶片散落（整隻繞底座右上角倒下，底座反向轉回原位不動）
      p.flash = u < 0.2 ? 0.8 : 0;
      const j = u < 0.28 ? 0.7 * Math.sign(Math.sin(u * 100)) : 0;
      const f = sm(seg(u, 0.25, 0.68)) - 0.06 * bump(u, 0.68, 0.8);
      R(p, { dx: j, rot: 1.42 * f, pivot: [5, -5] });
      A(p, "base", { dx: -j, rot: -1.42 * f, pivot: [5, -5] });
      A(p, "eye", { a: 1 - 0.7 * seg(u, 0.3, 0.7) });
      A(p, "ring", { a: 1 - seg(u, 0.25, 0.5) });
      if (u > 0.66) {
        const k = seg(u, 0.66, 1);
        FX(p, { k: "dust", x: 22, y: -1, r: 5, a: 1 - k });
        for (let i = 0; i < 4; i++) FX(p, { k: "shard", x: 14 + i * 7 + 4 * k * (i - 1.5), y: Math.min(-1.5, -6 - 6 * Math.sin(Math.PI * k) + i), rot: i + 3 * k, s: 1.6, c: lighten(e.r.base, 0.2) });
      }
    },
  },
  bird: {
    kind: "flyer",
    mouth: [17, -21],
    units: "雷羽鷹",
    // 待機（QK-4b）：落地收翅站著（翅膀往後下貼著身體）；一圈抖一次翅膀（半開、收回，兩下）；頭左右看、尾巴輕擺
    idle(p, u) {
      R(p, { dy: BIRD_PERCH_DY });
      p.shadow = 1;
      const sh = u >= 0.55 && u < 0.8 ? Math.abs(Math.sin(TAU * seg(u, 0.55, 0.8))) : 0;
      A(p, "wingN", { sy: -0.42 - 0.2 * sh, rot: 2.1 + 0.75 * sh });
      A(p, "wingF", { sy: -0.38 - 0.2 * sh, rot: 0.3 + 0.5 * sh });
      R(p, { dy: -0.6 * sh });
      A(p, "head", { rot: 0.07 * S(u, 1, 0.3) });
      A(p, "tail", { rot: 0.06 * S(u, 1) + 0.1 * sh });
    },
    move(p, u) {
      flap(p, u, { bob: 2.2, dn: -0.6, base: -6 }); // 飛高一點、下拍收小：翅尖不穿地
      R(p, { rot: 0.08 });
      A(p, "tail", { rot: 0.08 * S(u, 1) });
      A(p, "legs", { rot: 0.5 });
    },
    attacks: {
      rake: {
        zh: "爪擊（talons）",
        type: "melee",
        ms: 700,
        fn(p, u) {
          R(p, { dx: kf(u, [[0, 0], [0.3, -2], [0.52, 8], [0.68, 6], [1, 0]]), dy: kf(u, [[0, 0], [0.3, -6], [0.52, 3], [0.68, 1], [1, 0]]), rot: kf(u, [[0, 0], [0.3, -0.15], [0.52, -0.3], [1, 0]]) });
          const w = kf(u, [[0, 1], [0.3, 1.15], [0.52, -0.3], [0.7, 0.4], [1, 1]]);
          A(p, "wingN", { sy: w });
          A(p, "wingF", { sy: w });
          A(p, "legs", { rot: kf(u, [[0, 0], [0.3, -0.4], [0.5, -1.35], [0.68, -0.8], [1, 0]]) });
          A(p, "head", { rot: kf(u, [[0, 0], [0.5, 0.2], [1, 0]]) });
          slashFx(p, u, 0.48, 0.65, 26, -10, "#ffffff", 6);
        },
      },
      dive: {
        zh: "俯衝斬（衝鋒）",
        type: "charge",
        ms: 920,
        fn(p, u) {
          R(p, { dx: kf(u, [[0, 0], [0.35, -5], [0.58, 15], [0.7, 14], [1, 0]]), dy: kf(u, [[0, 0], [0.35, -14], [0.58, 6], [0.7, 4], [1, 0]]), rot: kf(u, [[0, 0], [0.35, -0.25], [0.45, 0.55], [0.58, 0.45], [0.72, -0.2], [1, 0]]) });
          const w = u < 0.35 ? 1.05 - 1.6 * Math.max(0, S(u / 0.35, 2)) : kf(u, [[0.35, 1], [0.42, 0.25], [0.58, 0.25], [0.7, -0.25], [0.85, 1], [1, 1]]);
          A(p, "wingN", { sy: w, rot: u > 0.38 && u < 0.6 ? 0.5 : 0 });
          A(p, "wingF", { sy: w, rot: u > 0.38 && u < 0.6 ? 0.5 : 0 });
          A(p, "legs", { rot: kf(u, [[0, 0], [0.45, 0.4], [0.56, -1.2], [0.72, -0.5], [1, 0]]) });
          slashFx(p, u, 0.55, 0.72, 33, -6, "#ffffff", 7);
          if (u > 0.55 && u < 0.8) FX(p, { k: "dust", x: 30, y: -1, r: 3.5, a: 1 - seg(u, 0.55, 0.8) });
          p.shadow = 1 - 0.3 * bump(u, 0.1, 0.45);
        },
      },
      cast: {
        zh: "靜電掌（翅尖放電）",
        type: "cast",
        ms: 880,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.lightning);
          const w = kf(u, [[0, 1], [0.38, 1.25], [0.52, -0.55], [0.7, -0.3], [1, 1]]);
          A(p, "wingN", { sy: w });
          A(p, "wingF", { sy: w });
          R(p, { dy: kf(u, [[0, 0], [0.38, 2], [0.52, -4], [1, 0]]), rot: kf(u, [[0, 0], [0.38, -0.1], [0.52, 0.12], [1, 0]]) });
          if (u > 0.1 && u < 0.5) for (const [x, y] of [[17, -51], [-19, -47]] as const) FX(p, { k: "bolt", x0: x - 2, y0: y, x1: x + 2, y1: y + 5, c: c[0], amp: 0.5 * Math.sin(u * 50) });
          if (u > 0.5 && u < 0.72) {
            FX(p, { k: "bolt", x0: 12, y0: -22, x1: TGT - 16, y1: -14, c: c[0], amp: 1 + 0.5 * Math.sin(u * 70), ranged: true });
            FX(p, { k: "glow", x: TGT - 16, y: -14, r: 10, c: c[0], a: 1 - seg(u, 0.5, 0.72) * 0.5, ranged: true });
          }
        },
      },
    },
    death(p, u) {
      p.flash = u < 0.15 ? 0.8 : 0;
      const fall = sm(seg(u, 0.2, 0.7));
      const j = bump(u, 0, 0.25);
      R(p, { dy: -3 * j + 11 * fall - 1.2 * bump(u, 0.7, 0.82), rot: -0.2 * j + 0.22 * fall, dx: 3 * fall, pivot: [0, -18] });
      p.softGround = true;
      const w = 1 - 0.75 * fall;
      A(p, "wingN", { sy: w, rot: 0.3 * fall });
      A(p, "wingF", { sy: w * 0.8, rot: 0.2 * fall });
      A(p, "head", { rot: 0.5 * sm(seg(u, 0.6, 0.95)) });
      A(p, "legs", { rot: -0.8 * fall });
      p.shadow = 1;
      if (u > 0.68 && u < 0.95) FX(p, { k: "dust", x: 4, y: -1, r: 4, a: 1 - seg(u, 0.68, 0.95) });
    },
  },
  bat: {
    kind: "flyer",
    mouth: [8, -21],
    units: "火塵蝠",
    idle(p, u) {
      R(p, { dy: -1.6 * S(u, 2) });
      flap(p, (u * 2) % 1, { up: 1, dn: 0.55, bob: 0.6 });
      A(p, "head", { rot: 0.06 * S(u, 1) });
    },
    move(p, u) {
      flap(p, u, { bob: 2, dn: -0.7 });
      R(p, { rot: 0.1 });
    },
    attacks: {
      fire: {
        zh: "火焰箭（fire_staff 普攻＋技能，口吐）",
        type: "cast",
        ms: 800,
        fn(p, u, e) {
          const c = elc(e.r, ELEM.fire);
          R(p, { dx: kf(u, [[0, 0], [0.35, -3], [0.48, 2], [1, 0]]), dy: kf(u, [[0, 0], [0.35, -3], [0.48, 0], [1, 0]]), rot: kf(u, [[0, 0], [0.35, -0.2], [0.48, 0.15], [1, 0]]) });
          flap(p, (u * 2) % 1, { bob: 0.8 });
          A(p, "head", { rot: kf(u, [[0, 0], [0.35, -0.35], [0.48, 0.25], [1, 0]]) });
          charge(p, u, 0.08, 0.42, [10, -24], c, 2.2);
          shot(p, u, 0.44, 0.66, [12, -22], c, { r: 2.4, y1: -16 });
        },
      },
      bite: {
        zh: "撲咬",
        type: "melee",
        ms: 660,
        fn(p, u) {
          R(p, { dx: kf(u, [[0, 0], [0.25, -3], [0.5, 10], [0.65, 9], [1, 0]]), dy: kf(u, [[0, 0], [0.25, -4], [0.5, 3], [1, 0]]), rot: kf(u, [[0, 0], [0.25, -0.15], [0.5, 0.3], [1, 0]]) });
          const w = kf(u, [[0, 1], [0.25, 1.1], [0.45, 0.35], [0.6, -0.5], [0.8, 1], [1, 1]]);
          A(p, "wingN", { sy: w });
          A(p, "wingF", { sy: w });
          A(p, "head", { rot: kf(u, [[0, 0], [0.3, -0.3], [0.5, 0.3], [1, 0]]) });
          chompFx(p, u, 0.42, 0.62, 25, -20);
        },
      },
    },
    death(p, u) {
      p.flash = u < 0.15 ? 0.8 : 0;
      const fall = sm(seg(u, 0.18, 0.65));
      R(p, { dy: -2 * bump(u, 0, 0.2) + 7.6 * fall - 1 * bump(u, 0.65, 0.78), rot: 0.4 * fall, pivot: [0, -18] });
      p.softGround = true;
      A(p, "wingN", { sy: 1 - 0.7 * fall, rot: 0.35 * fall });
      A(p, "wingF", { sy: 1 - 0.6 * fall });
      A(p, "head", { rot: 0.4 * fall });
      if (u > 0.64 && u < 0.92) FX(p, { k: "dust", x: 0, y: -1, r: 3.5, a: 1 - seg(u, 0.64, 0.92) });
    },
  },
};

// ============================== 片段表、量化、對外 ==============================
export const IDLE_MS: Readonly<Record<string, number>> = { hound: 2200, boar: 2000, bear: 2400, feline: 2200, lizard: 2200, shell: 2400, beetle: 2000, spider: 2000, serpent: 2200, ooze: 2000, golem: 2400, wisp: 2000, wraith: 2400, pylon: 2400, bird: 2000, bat: 2000 };
export const MOVE_MS: Readonly<Record<string, number>> = { hound: 640, boar: 560, bear: 820, feline: 640, lizard: 560, shell: 960, beetle: 520, spider: 480, serpent: 720, ooze: 760, golem: 960, wisp: 800, wraith: 900, pylon: 1000, bird: 520, bat: 360 };
export const HIT_MS = 400;
export const DEATH_MS = 1000;
const FPS_MS = 1000 / 12;
/** 格邊界的浮點誤差：t 剛好在格邊界（例如第 7 格的 583.33…）時商會略小於整數、取到前一格，先加一點再取整（同樣張 frameOf 的 EPS）。 */
const EPS = 1e-6;
export const LOOP_N = 8;

export interface ClipInfo {
  ms: number;
  loop: boolean;
  zh: string;
  type?: AttackType;
  /** 單次片段的格數（12 格／秒；循環 8）。 */
  n: number;
}

/** 這款身形的片段清單：["idle", "move", "atk:<id>"…, "hit", "death"]。 */
export function creatureClips(key: string): string[] {
  const B = BODY_ANIM[key];
  if (B === undefined) return [];
  return ["idle", "move", ...Object.keys(B.attacks).map((a) => `atk:${a}`), "hit", "death"];
}

export function creatureClipInfo(key: string, clip: string): ClipInfo | null {
  const B = BODY_ANIM[key];
  if (B === undefined) return null;
  const single = (ms: number): number => Math.max(2, Math.round(ms / FPS_MS));
  if (clip === "idle") return { ms: IDLE_MS[key] ?? 2000, loop: true, zh: "待機", n: LOOP_N };
  if (clip === "move") return { ms: MOVE_MS[key] ?? 700, loop: true, zh: "移動", n: LOOP_N };
  if (clip === "hit") return { ms: HIT_MS, loop: false, zh: "受擊", n: single(HIT_MS) };
  if (clip === "death") return { ms: DEATH_MS, loop: false, zh: "倒下", n: single(DEATH_MS) };
  const a = clip.startsWith("atk:") ? B.attacks[clip.slice(4)] : undefined;
  return a === undefined ? null : { ms: a.ms, loop: false, zh: a.zh, type: a.type, n: single(a.ms) };
}

/**
 * 片段在 t 毫秒的 u（0～1，已量化成格）。循環：一圈 8 格，相位由 id 雜湊決定；單次：12 格／秒，最後一格 u＝1。
 * 不認得的片段 → null。
 */
export function creatureFrameU(key: string, clip: string, t: number, id?: string): number | null {
  const info = creatureClipInfo(key, clip);
  if (info === null) return null;
  const tt = Math.max(0, Number.isFinite(t) ? t : 0);
  if (info.loop) {
    const step = info.ms / LOOP_N;
    const ph = id !== undefined ? (idHash(id) % 1000) / 1000 : 0;
    const w = (((tt + ph * info.ms) % info.ms) + info.ms) % info.ms;
    return Math.min(LOOP_N - 1, Math.floor(w / step + EPS)) / LOOP_N;
  }
  const f = Math.min(info.n - 1, Math.floor(tt / FPS_MS + EPS));
  return f / (info.n - 1);
}

/** 進度 k（0～1）→ 量化過的 u（循環 8 格；單次照 12 格／秒的格數，最後一格 1）。 */
export function quantizeClipU(key: string, clip: string, k: number): number {
  const info = creatureClipInfo(key, clip);
  const c = cl(Number.isFinite(k) ? k : 0);
  if (info === null) return c;
  if (info.loop) return (Math.floor(c * LOOP_N) % LOOP_N) / LOOP_N;
  return Math.round(c * (info.n - 1)) / (info.n - 1);
}

/** 這款身形中某個動作類型的攻擊片段（沒有那個類型 → 依序退回普攻、第一個攻擊）。 */
export function attackClipFor(key: string, type: AttackType): string | null {
  const B = BODY_ANIM[key];
  if (B === undefined) return null;
  const list = Object.entries(B.attacks);
  const fallback: Readonly<Record<AttackType, readonly AttackType[]>> = {
    melee: ["melee", "charge"],
    melee2: ["melee2", "melee", "charge"],
    charge: ["charge", "melee"],
    breath: ["breath", "cast", "area"],
    cast: ["cast", "breath", "melee"],
    area: ["area", "cast", "melee"],
    summon: ["summon", "cast", "area"],
    blink: ["blink", "melee"],
  };
  for (const t of fallback[type]) {
    const hit = list.find(([, a]) => a.type === t);
    if (hit !== undefined) return `atk:${hit[0]}`;
  }
  return list[0] === undefined ? null : `atk:${list[0][0]}`;
}

/**
 * CB-3：照自己格數播的攻擊片段（第二種近戰）：格數 n、長度 ms、命中格 hitF（12 格／秒，第 f 格在 f × 83.33 ms）。
 * 其他片段＝null（戰場照舊量化成 12 格）。`clip` 是實際片段（`atk:<id>`）。
 */
export function creatureOwnFrames(key: string, clip: string): { n: number; ms: number; hitF: number } | null {
  const a = clip.startsWith("atk:") ? BODY_ANIM[key]?.attacks[clip.slice(4)] : undefined;
  if (a?.hitF === undefined) return null;
  return { n: Math.max(2, Math.round(a.ms / FPS_MS)), ms: a.ms, hitF: a.hitF };
}

/** CB-3：照自己格數播的片段在進度 k（0～1，佔片段長度的比例）的 u：第 f 格從 f × 83.33 ms 起，最後一格停到片段結束。 */
export function ownFrameU(own: { n: number; ms: number }, k: number): number {
  const t = cl(Number.isFinite(k) ? k : 0) * own.ms;
  return Math.min(own.n - 1, Math.floor(t / FPS_MS + EPS)) / (own.n - 1);
}

// ============================== QK-4b：鳥的起飛／落地過場 ==============================
/** 待機落地（比飛行低）、移動在空中的身形：移動開頭與結尾約 4 格從落地姿勢過渡（perch 1＝落地、0＝飛行）。 */
export const PERCHERS: ReadonlySet<string> = new Set(["bird"]);
/** 鳥待機抖翅張最開的那一刻（idle 的 u；過場的半開翅膀用）。 */
const PERCH_SPREAD_U = 0.6125;
const XF_KEYS = ["rot", "dx", "dy", "kx", "sx", "sy", "a"] as const;
function blendXf(a: PartXf | undefined, b: PartXf | undefined, k: number): PartXf {
  const out: PartXf = {};
  for (const key of XF_KEYS) {
    const d = key === "sx" || key === "sy" || key === "a" ? 1 : 0;
    const va = a?.[key] ?? d;
    const vb = b?.[key] ?? d;
    if (va !== d || vb !== d) out[key] = va + (vb - va) * k;
  }
  const pv = (k < 0.5 ? a?.pivot : b?.pivot) ?? a?.pivot ?? b?.pivot;
  if (pv !== undefined) out.pivot = pv;
  return out;
}
/** 兩個姿勢逐欄內插（k 0＝a、1＝b）；特效取 a。 */
function blendPose(a: QPartPose, b: QPartPose, k: number): QPartPose {
  const parts: Record<string, PartXf> = {};
  for (const g of [...new Set([...Object.keys(a.parts), ...Object.keys(b.parts)])].sort()) parts[g] = blendXf(a.parts[g], b.parts[g], k);
  return { ...a, root: blendXf(a.root, b.root, k), parts, shadow: a.shadow + (b.shadow - a.shadow) * k };
}

/** 片段在 u 的分部件姿勢。reduce：減少動態（待機、移動 → null；受擊只白閃；倒下最後一格；攻擊只往前推 2）。不認得 → null。 */
export function qCreaturePartPose(r: AnimSubject, clip: string, u0: number, reduce = false, perch = 0): QPartPose | null {
  const strike = clip.startsWith("atk:");
  if ((clip === "move" || strike) && perch > 0 && !reduce && PERCHERS.has(r.key)) {
    const fly = qCreaturePartPose(r, clip, u0);
    const sit = qCreaturePartPose(r, "idle", 0);
    if (fly === null || sit === null) return fly;
    const k = cl(perch);
    const out = blendPose(fly, sit, k);
    // 翅膀不內插（收翅與拍翅的 sy 正負相反，中間會變成一條線）：落地＝收翅、快落地／剛起飛＝抖翅那格的半開、其他＝拍翅
    // CB-2c：攻擊前後的過場也是收翅 → 半開 → 拍翅（攻擊片段的第一格、最後一格翅膀是靜止的，拍翅借移動片段）
    const wings = k >= 1 ? sit : k >= 0.75 ? qCreaturePartPose(r, "idle", PERCH_SPREAD_U) : strike ? qCreaturePartPose(r, "move", 1 - k) : fly;
    for (const g of ["wingN", "wingF"]) {
      const w = wings?.parts[g];
      if (w !== undefined) out.parts[g] = { ...w };
    }
    if (strike) out.fx = []; // 過場本身沒有攻擊特效
    return out;
  }
  const B = BODY_ANIM[r.key];
  const info = creatureClipInfo(r.key, clip);
  if (B === undefined || info === null) return null;
  const u = cl(u0);
  const p = newPose();
  const e: E = { r };
  if (r.key === "spider") p.limbRim = true; // 蜘蛛的細腳加亮邊
  if (reduce) {
    if (clip === "idle" || clip === "move") return null;
    if (clip === "hit") {
      p.flash = u < 0.2 ? 0.9 : 0;
      return p;
    }
    if (clip === "death") {
      B.death(p, 1, e);
      p.fx = [];
      return p;
    }
    B.attacks[clip.slice(4)]!.fn(p, u, e);
    const q = newPose();
    q.fx = p.fx;
    R(q, { dx: 2 * Math.sin(Math.PI * u) });
    return q;
  }
  if (clip === "idle") B.idle(p, u, e);
  else if (clip === "move") B.move(p, u, e);
  else if (clip === "hit") HIT[B.kind]!(p, u, e);
  else if (clip === "death") B.death(p, u, e);
  else B.attacks[clip.slice(4)]!.fn(p, u, e);
  return p;
}

// ============================== QK-5：攻擊片段的出手格（命中對齊） ==============================
/** 出手那一刻的特效：揮爪、咬合、震地環、爆開、雷、射線、吐息、衝擊波、火焰、碎晶、落石，或任何飛向目標的特效（ranged）。蓄力光、塵土不算。 */
const IMPACT_FX: ReadonlySet<string> = new Set(["slash", "chomp", "ring", "burst", "bolt", "beam", "cone", "wave", "flame", "shard", "rock"]);
const HIT_U = new Map<string, number>();
/** 戰場的攻擊片段格數（creaturePose 的 CLIP_FRAMES.atk）。 */
const ATK_FRAMES = 12;
/**
 * 攻擊片段的出手格（0～1）：照戰場的量化（creaturePose 的攻擊 12 格，u＝f/11）逐格看，第一個出現出手特效的那一格；
 * 整段都沒有出手特效時取整隻往前推最遠的那一格（撲、衝撞）；都沒有＝0.5。純函式、有快取（同一款身形同一個片段只算一次）。
 */
export function creatureAttackHitU(key: string, clip: string): number {
  const ck = `${key}|${clip}`;
  const hit = HIT_U.get(ck);
  if (hit !== undefined) return hit;
  // CB-3：第二種近戰的命中時間照表（命中格 × 83.33 ms ÷ 片段長度）
  const own = creatureOwnFrames(key, clip);
  if (own !== null) {
    const at = (own.hitF * FPS_MS) / own.ms;
    HIT_U.set(ck, at);
    return at;
  }
  const r: AnimSubject = { key, element: undefined, mat: "flesh", base: "#888888", accent: null };
  let found: number | null = null;
  let best = 0.5;
  let far = 0;
  for (let i = 1; i <= ATK_FRAMES - 1 && found === null; i++) {
    const u = i / (ATK_FRAMES - 1);
    const p = qCreaturePartPose(r, clip, u);
    if (p === null) break;
    if (p.fx.some((f) => f.ranged === true || IMPACT_FX.has(f.k))) found = u;
    const dx = p.root?.dx ?? 0;
    if (dx > far + 1e-6) {
      far = dx;
      best = u;
    }
  }
  const out = found ?? best;
  HIT_U.set(ck, out);
  return out;
}
