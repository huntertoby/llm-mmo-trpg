// 異形敵人（野獸、熔岩獸、源晶造物、傀儡、石靈、異形召喚物）的 Q 版畫法（QK-4；Phase 5A-ART1／ART2 的 C 墨線改成 Q）。
// 照美術 PM 樣張 docs/art/sample/qCreature.js（需求 docs/art/QK移植需求.md 第 5 節）：身形的點座標、部件順序、特徵、詞綴沿用 5A-ART 那份，
// 只換畫法層：純色平塗（無抖動、無排線）＋部件之間一條細縫線＋整隻剪影粗外框（1.3 單位 #16121a，qCreatureLayer.qLayer）；
// 方眼＋高光、Q 大頭（qHead：頭部部件以頸部為支點放大）、材質平塗紋樣、霧下緣 3 段淡出、頭目外光＝剪影膨脹的平塗光。
// 外觀 ＝ 身形 body × 材質 material × 元素 element × 大小 size × 特徵 traits（＋依狀態的 status_traits）× 精英詞綴 affixes。
// 不認得的值一律退回、不出錯：body → ooze、material → fur、element → 沒有元素、size → 1、trait／affix → 略過（affix 只剩精英金環）。
// 座標：腳底 (0,0)、往上是 -y、朝東（+x 是前方）；朝西左右鏡像；正面、背面沿用側面。
// 動畫（QK-4）：部件依名稱開頭歸到部件組（RIG），姿勢只改每組的變換（qCreatureAnim.ts）；沒有姿勢時指令流和靜態相同。
// 確定性：紋樣抖動用名稱雜湊（禁止 Math.random()）。
import type { Facing } from "../api/types";
import { TAU, type Ctx } from "./artDraw";
import { darken, lighten, mix } from "./color";
import { applyCreaturePose, cp, type CreatureFx, type CreaturePose, type PartXf, type QPartPose, type SplitPiece } from "./creaturePose";
import { turnCreatureFx } from "./creatureFxTurn";
import { CREATURE_ELEM, FIRE } from "./qCreatureElem";
import { Q_HEADS, RIG, type QHeadDef, type RigDef } from "./creatureRig";
import { attackClipFor, BODY_ANIM, creatureFrameU, drawCreatureFx, idHash, PERCHERS, qCreaturePartPose, type AttackType } from "./qCreatureAnim";
import { BOSS_BOX, BOSS_FIELD_SCALE, BOSS_IDLE_N, BOSS_MS, bossOf, bossPoseFx, drawBossFrame, type BossId } from "./qBoss";
import { ellPts, lcg, seedOf, type Pt } from "./inkStyle";
import { hasDom, qLayer, QC_OUT } from "./qCreatureLayer";

export { CREATURE_ELEM };

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
  /** 單位範本 ID（QK-4：頭目 `ashen_heart`、`rift_shard_lord` 改用 qBoss 畫法）。 */
  template?: string | undefined;
  /** 頭目目前的階段（1 起；`UnitView.boss_phase.index`）。 */
  bossPhase?: number | null | undefined;
}

const CRYSTAL = "#9a86ff"; // 源晶藍紫（形態光環、魔導劍同色）
/** Q 版玄武岩（C 的 #3b2c28 提亮一階，黑外框裡才看得出形狀）。 */
export const BASALT = "#4a3631";
// 顏色分開（qCreature.js 11-07）：熔岩聖＝乳白鋸齒＋小十字、金眼；源晶暗＝深靛紫晶
const MAGMA_ELEM: Readonly<Record<string, readonly [string, string]>> = { holy: ["#fff4dc", "#ffbf3a"] };
const MAGMA_CROSS: Readonly<Record<string, string>> = { holy: "#fffbe8" };
const CRYSTAL_SHADOW = "#4e3a8e";
const OUT = QC_OUT;
const INK = OUT;

export const MATERIALS = ["fur", "magma", "crystal", "stone", "wood", "mist"] as const;
export type Material = (typeof MATERIALS)[number];
export const SIZES: Readonly<Record<string, number>> = { tiny: 0.62, small: 0.8, medium: 1, large: 1.25, huge: 1.6 };
/** 戰場上的大小（Phase 5A-ART5，`docs/archive/art/5A-ART檢查.md` 1）：tiny、small 放大，medium 以上不變；樣張頁與其他畫面照 `SIZES`。 */
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
  /** 熔岩聖的小十字亮點色。 */
  cross: string | undefined;
  sharp: boolean;
  alpha: number | undefined;
  /** tiny／small：紋樣只畫 1 筆、背上只有 1 個。 */
  lite: boolean;
}

const isMaterial = (m: string | null | undefined): m is Material => m != null && (MATERIALS as readonly string[]).includes(m);

export function paletteOf(material: Material, element: string | undefined, tint: string | undefined, fur: string, lite = false): Palette {
  const el = element === undefined ? undefined : CREATURE_ELEM[element];
  let base: string;
  let accent: string | null;
  let eye: string;
  if (material === "magma") {
    const me = (element !== undefined ? MAGMA_ELEM[element] : undefined) ?? el;
    base = tint ?? BASALT;
    accent = me?.[0] ?? FIRE[0];
    eye = me?.[1] ?? FIRE[1];
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
    base = element === "shadow" ? CRYSTAL_SHADOW : el !== undefined ? mix(CRYSTAL, el[0], 0.4) : (tint ?? CRYSTAL);
    accent = el?.[1] ?? "#e4dcff";
    eye = "#ffffff";
  } else {
    base = tint ?? fur;
    if (el !== undefined) base = mix(base, el[0], 0.22);
    accent = el?.[0] ?? null;
    eye = el?.[1] ?? "#ffd23a";
  }
  return {
    mat: material,
    base,
    d: darken(base, 0.28),
    l: lighten(base, 0.3),
    accent,
    eye,
    cross: material === "magma" && element !== undefined ? MAGMA_CROSS[element] : undefined,
    sharp: material === "crystal" || material === "stone",
    alpha: material === "mist" ? 0.62 : undefined,
    lite,
  };
}

// ============================== Q 畫法層（部件掛點：姿勢、Q 大頭） ==============================

interface DrawState {
  qhead: QHeadDef | null;
  inHead: boolean;
  headDone: boolean;
  pose: QPartPose | null;
  groups: ReadonlyArray<readonly [string, string]> | null;
  pivots: Readonly<Record<string, Pt>> | null;
  last: string;
  depth: number;
}
const S: DrawState = { qhead: null, inHead: false, headDone: false, pose: null, groups: null, pivots: null, last: "body", depth: 0 };

function headHook(ctx: Ctx, key: string): void {
  const q = S.qhead;
  if (q === null) return;
  const end = q[4];
  if (S.inHead && end !== undefined && key.startsWith(end)) {
    ctx.restore();
    S.inHead = false;
    S.headDone = true;
    return;
  }
  if (S.inHead || S.headDone || !key.startsWith(q[0])) return;
  const [, x, y, s] = q;
  S.inHead = true;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.translate(-x, -y);
}

const UNIVERSAL: ReadonlyArray<readonly [string, string]> = [
  ["tr-scar", "head"],
  ["af-bz", "head"],
];
function groupOf(key: string): string {
  for (const [p, g] of S.groups ?? []) if (key.startsWith(p)) return g;
  for (const [p, g] of UNIVERSAL) if (key.startsWith(p)) return g;
  return "body";
}

/** 套一組的變換（呼叫端 save 過）；沒有這組時回傳 false。 */
export function applyPartXf(ctx: Ctx, f: PartXf | undefined, pivot: Pt): boolean {
  if (f === undefined) return false;
  const [px, py] = f.pivot ?? pivot;
  ctx.save();
  ctx.translate(px + (f.dx ?? 0), py + (f.dy ?? 0));
  if (f.rot) ctx.rotate(f.rot);
  if (f.kx) ctx.transform(1, 0, f.kx, 1, 0, 0);
  ctx.scale(f.sx ?? 1, f.sy ?? 1);
  ctx.translate(-px, -py);
  if (f.a !== undefined) ctx.globalAlpha *= Math.max(0, Math.min(1, f.a));
  return true;
}

/** QK-4b 斷塊：同一組畫好幾次，每次只畫 clip 多邊形裡的那一塊（傀儡崩塌）。 */
function drawSplit(ctx: Ctx, pieces: readonly SplitPiece[], fn: () => void): void {
  for (const q of pieces) {
    ctx.save();
    const [px, py] = q.pivot ?? [0, 0];
    ctx.translate(px + (q.dx ?? 0), py + (q.dy ?? 0));
    if (q.rot) ctx.rotate(q.rot);
    ctx.translate(-px, -py);
    ctx.beginPath();
    q.clip.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
    ctx.clip();
    fn();
    ctx.restore();
  }
}

function inPart(ctx: Ctx, g: string, fn: () => void): void {
  if (S.pose === null || S.depth > 0) {
    fn();
    return;
  }
  S.depth++;
  const on = applyPartXf(ctx, S.pose.parts[g], S.pivots?.[g] ?? [0, 0]);
  try {
    const sp = S.pose.split?.[g];
    if (sp) drawSplit(ctx, sp, fn);
    else fn();
  } finally {
    if (on) ctx.restore();
    S.depth--;
  }
}
function part(ctx: Ctx, key: string, fn: () => void): void {
  headHook(ctx, key);
  if (S.pose === null) {
    fn();
    return;
  }
  S.last = groupOf(key);
  inPart(ctx, S.last, fn);
}
function mark(key: string): void {
  if (S.pose !== null) S.last = groupOf(key);
}

/** 圓潤的部件用「中點二次曲線」（不抖）。 */
function smooth(ctx: Ctx, pts: readonly Pt[], closed = true): void {
  ctx.beginPath();
  const n = pts.length;
  const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  if (!closed) {
    ctx.moveTo(pts[0]![0], pts[0]![1]);
    for (let i = 1; i < n - 1; i++) {
      const m = mid(pts[i]!, pts[i + 1]!);
      ctx.quadraticCurveTo(pts[i]![0], pts[i]![1], m[0], m[1]);
    }
    ctx.lineTo(pts[n - 1]![0], pts[n - 1]![1]);
    return;
  }
  const m0 = mid(pts[n - 1]!, pts[0]!);
  ctx.moveTo(m0[0], m0[1]);
  for (let i = 0; i < n; i++) {
    const p = pts[i]!;
    const m = mid(p, pts[(i + 1) % n]!);
    ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
  }
  ctx.closePath();
}
function outline(ctx: Ctx, pts: readonly Pt[], sharp: boolean | undefined): void {
  if (sharp !== true) {
    smooth(ctx, pts);
    return;
  }
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
}

interface InkOpt {
  sharp?: boolean;
  /** false：不畫縫線。 */
  line?: boolean;
}

/** 平塗一塊；部件之間一條細縫線（本色加深），外輪廓由剪影外框負責。 */
function ink(ctx: Ctx, key: string, pts: readonly Pt[], color: string, opt: InkOpt = {}): void {
  part(ctx, key, () => {
    ctx.save();
    outline(ctx, pts, opt.sharp);
    ctx.fillStyle = color;
    ctx.fill();
    if (opt.line !== false) {
      ctx.strokeStyle = mix(color, OUT, 0.55);
      ctx.lineWidth = 0.55;
      ctx.lineJoin = "round";
      ctx.stroke();
    }
    ctx.restore();
  });
}
function stroke(ctx: Ctx, key: string, pts: readonly Pt[], w = 0.7, color = OUT): void {
  part(ctx, key, () => {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = w;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    smooth(ctx, pts, false);
    ctx.stroke();
    ctx.restore();
  });
}
/** 粗線肢體：縫線色底＋色線；動畫的 limbRim（蜘蛛）改亮邊、加粗。 */
function limb(ctx: Ctx, key: string, pts: readonly Pt[], w: number, color: string): void {
  const rim = S.pose?.limbRim === true;
  stroke(ctx, key, pts, w + 1.1 + (rim ? 0.5 : 0), rim ? lighten(color, 0.38) : mix(color, OUT, 0.55));
  stroke(ctx, key, pts, w + (rim ? 0.7 : 0), color);
}
function dot(ctx: Ctx, x: number, y: number, rx: number, ry: number, c: string): void {
  inPart(ctx, S.last, () => {
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.ellipse(x, y, rx, ry, 0, 0, TAU);
    ctx.fill();
  });
}

// ---- 材質紋樣（平塗線條、色塊；lite＝tiny／small 只畫 1 筆） ----
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
function clipTo(ctx: Ctx, pts: readonly Pt[], P: Palette): void {
  ctx.save();
  outline(ctx, pts, P.sharp);
  ctx.clip();
}
function polyline(ctx: Ctx, pts: readonly Pt[]): void {
  ctx.beginPath();
  pts.forEach(([x, y], j) => (j > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
}

/** 熔岩：一～兩道鋸齒裂縫（暗紅底＋亮色芯）；聖＝裂縫上方的小十字亮點。 */
function cracks(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const r = lcg(seedOf(key));
  const n = !P.lite && b.x1 - b.x0 > 18 ? 2 : 1;
  clipTo(ctx, pts, P);
  for (let i = 0; i < n; i++) {
    const y = b.y0 + (b.y1 - b.y0) * (n === 1 ? 0.5 : 0.35 + 0.3 * i);
    const line: Pt[] = [];
    for (let x = b.x0 + 2; x <= b.x1 - 2; x += 3.6) line.push([x, y + (line.length % 2 ? -1.4 : 1.4) + (r() - 0.5) * 1.2]);
    if (line.length < 2) continue;
    ctx.save();
    ctx.strokeStyle = "#7a2a08";
    ctx.lineWidth = 2;
    ctx.lineJoin = "miter";
    polyline(ctx, line);
    ctx.stroke();
    ctx.strokeStyle = P.accent ?? FIRE[0];
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  }
  if (P.cross !== undefined) {
    const cs: ReadonlyArray<readonly [number, number]> = P.lite ? [[0.4, 0.22]] : [[0.24, 0.22], [0.56, 0.18]];
    for (const [fx, fy] of cs) {
      const x = b.x0 + (b.x1 - b.x0) * fx;
      const y = b.y0 + (b.y1 - b.y0) * fy + 1.2;
      const h = 2.3;
      ctx.save();
      ctx.lineCap = "round";
      for (const [c, w] of [["#7a2a08", 1.9], [P.cross, 0.9]] as const) {
        ctx.strokeStyle = c;
        ctx.lineWidth = w;
        ctx.beginPath();
        ctx.moveTo(x - h, y);
        ctx.lineTo(x + h, y);
        ctx.moveTo(x, y - h);
        ctx.lineTo(x, y + h);
        ctx.stroke();
      }
      ctx.restore();
    }
  }
  ctx.restore();
}
/** 源晶：左上一塊亮面（色塊）＋一條晶面線。 */
function facets(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const w = b.x1 - b.x0;
  const h = b.y1 - b.y0;
  clipTo(ctx, pts, P);
  ctx.fillStyle = lighten(P.base, 0.28);
  ctx.beginPath();
  ctx.moveTo(b.x0 - 1, b.y0 - 1);
  ctx.lineTo(b.x0 + w * 0.5, b.y0 - 1);
  ctx.lineTo(b.x0 + w * 0.22, b.y1 + 1);
  ctx.lineTo(b.x0 - 1, b.y1 + 1);
  ctx.closePath();
  ctx.fill();
  if (!P.lite) stroke(ctx, `${key}-f2`, [[b.x0 + w * 0.6, b.y0], [b.x0 + w * 0.5, b.y0 + h * 0.6], [b.x1, b.y0 + h * 0.7]], 0.7, lighten(P.base, 0.55));
  ctx.restore();
}
/** 青石：發光刻符 ᛉ（平塗兩層線；lite 只畫一豎）。 */
function runes(ctx: Ctx, _key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const cx = (b.x0 + b.x1) / 2;
  const cy = (b.y0 + b.y1) / 2;
  const lines: Pt[][] = P.lite
    ? [[[cx, cy - 3], [cx, cy + 3]]]
    : [
        [[cx, cy - 3.6], [cx, cy + 3.6]],
        [[cx - 2.6, cy - 3], [cx, cy - 0.4], [cx + 2.6, cy - 3]],
      ];
  clipTo(ctx, pts, P);
  for (const l of lines) {
    ctx.save();
    ctx.lineJoin = "miter";
    ctx.lineCap = "round";
    polyline(ctx, l);
    ctx.strokeStyle = darken(P.base, 0.35);
    ctx.lineWidth = 1.8;
    ctx.stroke();
    ctx.strokeStyle = P.accent ?? "#8fe3ff";
    ctx.lineWidth = 0.85;
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
}
/** 木：一～兩道木紋（平塗深色線）。 */
function grain(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  clipTo(ctx, pts, P);
  for (const i of P.lite ? [1.5] : [1, 2]) {
    const y = b.y0 + ((b.y1 - b.y0) * i) / 3;
    stroke(ctx, `${key}-gr${i}`, [[b.x0, y], [(b.x0 + b.x1) / 2, y - 0.8], [b.x1, y + 0.4]], 0.7, P.d);
  }
  ctx.restore();
}
/** 毛皮：肚子下緣一塊亮色（平塗）。 */
function furBelly(ctx: Ctx, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const w = b.x1 - b.x0;
  const h = b.y1 - b.y0;
  if (w < 8 || h < 6) return;
  clipTo(ctx, pts, P);
  ctx.fillStyle = P.l;
  ctx.beginPath();
  ctx.ellipse((b.x0 + b.x1) / 2 + w * 0.08, b.y1 + h * 0.08, w * 0.36, h * 0.32, 0, 0, TAU);
  ctx.fill();
  ctx.restore();
}
/** 霧：一道亮色漩渦線（平塗）。 */
function swirl(ctx: Ctx, pts: readonly Pt[], P: Palette): void {
  const b = bbox(pts);
  const w = b.x1 - b.x0;
  const h = b.y1 - b.y0;
  if (w < 6 || h < 5) return;
  clipTo(ctx, pts, P);
  ctx.save();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 0.9;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.ellipse((b.x0 + b.x1) / 2 - w * 0.05, (b.y0 + b.y1) / 2, w * 0.22, h * 0.2, 0, Math.PI * 0.9, Math.PI * 2.3);
  ctx.stroke();
  ctx.restore();
  ctx.restore();
}

interface MassOpt extends InkOpt {
  color?: string;
  main?: boolean;
}

/** 一塊身體：材質色平塗；`main` ＝ 主要部位，再加材質紋樣（Q 的大頭保持乾淨：頭上只有源晶的亮面）。 */
function mass(ctx: Ctx, key: string, pts: readonly Pt[], P: Palette, opt: MassOpt = {}): void {
  part(ctx, key, () => {
    ink(ctx, key, pts, opt.color ?? P.base, { sharp: opt.sharp ?? P.sharp, ...(opt.line === false ? { line: false } : {}) });
    if (opt.main !== true) return;
    if (/head/.test(key) && P.mat !== "crystal") return;
    if (P.mat === "magma") cracks(ctx, key, pts, P);
    else if (P.mat === "crystal") facets(ctx, key, pts, P);
    else if (P.mat === "stone") runes(ctx, key, pts, P);
    else if (P.mat === "wood") grain(ctx, key, pts, P);
    else if (P.mat === "mist" && !P.lite) swirl(ctx, pts, P);
    else if (P.mat === "fur" && opt.color === undefined && !P.lite && /body|blob|torso|abd/.test(key)) furBelly(ctx, pts, P);
  });
}

/** 背上的小東西：毛（短毛三角）、熔岩（火星方塊）、源晶（晶刺）、青石（苔點）；木頭、霧不加。lite 只畫第一個。 */
function back(ctx: Ctx, key: string, list: readonly Pt[], P: Palette): void {
  list.forEach(([x, y], i) =>
    part(ctx, `${key}-sh${i}`, () => {
      if (P.lite && i > 0) return;
      if (P.mat === "crystal") {
        const h = 5 + (i % 2) * 2.4;
        ink(ctx, `${key}-sh${i}`, [[x - 2, y + 1], [x + 0.6, y - h], [x + 2.4, y + 1]], lighten(P.base, 0.25), { sharp: true });
        stroke(ctx, `${key}-shl${i}`, [[x + 0.2, y - h + 1.6], [x - 0.6, y]], 0.6, "#ffffff");
      } else if (P.mat === "stone") {
        dot(ctx, x, y + 0.6, 1.8, 1, "#6a9a4a");
      } else if (P.mat === "wood" || P.mat === "mist") {
        // 木頭、霧：背上不加東西
      } else if (P.mat === "magma") {
        ctx.fillStyle = P.accent ?? FIRE[0];
        ctx.fillRect(x + 0.2, y - 3.8 - (i % 2) * 2.4, 1.6, 1.6);
      } else {
        ink(ctx, `${key}-tuft${i}`, [[x - 1.8, y + 0.8], [x, y - 2.6], [x + 1.6, y + 0.6]], P.d, { sharp: true, line: false });
      }
    }),
  );
}

/** Q 的眼睛：圓角方眼（眼色）＋方瞳＋一點高光。 */
function eye(ctx: Ctx, x: number, y: number, P: { eye: string }, r = 1): void {
  inPart(ctx, S.last, () => {
    const s = r * 1.25;
    if (S.pose?.eyeShut) {
      // QK-4b：倒下閉眼＝深色 ×（靜態不變）
      ctx.save();
      ctx.strokeStyle = OUT;
      ctx.lineWidth = 0.7 * s;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(x - 1.05 * s, y - 1.05 * s);
      ctx.lineTo(x + 1.05 * s, y + 1.05 * s);
      ctx.moveTo(x + 1.05 * s, y - 1.05 * s);
      ctx.lineTo(x - 1.05 * s, y + 1.05 * s);
      ctx.stroke();
      ctx.restore();
      return;
    }
    ctx.fillStyle = P.eye;
    ctx.beginPath();
    ctx.roundRect(x - 1.15 * s, y - 1.25 * s, 2.3 * s, 2.5 * s, 0.7 * s);
    ctx.fill();
    ctx.fillStyle = OUT;
    ctx.fillRect(x - 0.2 * s, y - 0.95 * s, 1.0 * s, 1.9 * s);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(x + 0.15 * s, y - 0.85 * s, 0.45 * s, 0.45 * s);
  });
}
const fang = (ctx: Ctx, key: string, x: number, y: number, h = 2): void => ink(ctx, key, [[x - 0.8, y], [x, y + h], [x + 0.8, y]], "#f4ecd8", { sharp: true, line: false });

// ============================== 身形 ==============================
/** 每種身形：預設毛色、最高點（top）、頭（詞綴特效）、身長的一半（len）、背上幾個點（sp）、熔核點（core）、浮空、Q 大頭。 */
export interface BodyDef {
  zh: string;
  fur: string;
  top: number;
  head: Pt;
  len: number;
  sp: readonly Pt[];
  core?: Pt;
  hover?: boolean;
  qHead?: QHeadDef;
  qHeadBy?: Readonly<Record<string, QHeadDef>>;
  draw: (ctx: Ctx, P: Palette, variant: string) => void;
}

function drawHound(ctx: Ctx, P: Palette): void {
  for (const x of [-12, 6]) mass(ctx, `hd-lf${x}`, [[x, -12], [x + 4, -12], [x + 4.4, 0], [x - 0.4, 0]], P, { color: P.d });
  mass(ctx, "hd-tail", [[-14, -20], [-22, -25], [-26, -21], [-20, -17], [-13, -15]], P);
  mass(ctx, "hd-body", [[-16, -12], [-17, -20], [-10, -25], [4, -25], [12, -22], [13, -12], [0, -10]], P, { main: true });
  back(ctx, "hd", [[-10, -25], [-4, -25.6], [2, -25.4]], P);
  for (const x of [-9, 8]) mass(ctx, `hd-l${x}`, [[x, -13], [x + 4, -13], [x + 4.6, 0], [x - 0.4, 0]], P);
  mass(ctx, "hd-ear", [[12, -29], [13, -36], [16.4, -30]], P, { color: P.d, sharp: true });
  mass(ctx, "hd-head", [[8, -22], [11, -30], [17, -31], [22, -28], [28, -26], [28, -23], [21, -21], [14, -18]], P, { main: true });
  dot(ctx, 28, -25, 0.9, 0.8, INK);
  eye(ctx, 19, -27.4, P);
  fang(ctx, "hd-fang", 24, -22.2);
}

function drawBoar(ctx: Ctx, P: Palette): void {
  for (const x of [-10, 6]) mass(ctx, `bo-lf${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P, { color: P.d });
  stroke(ctx, "bo-tail", [[-15, -16], [-18, -18], [-17.4, -20]], 0.8);
  mass(ctx, "bo-body", [[-15, -8], [-16, -18], [-8, -24], [4, -25], [12, -20], [13, -9], [0, -7]], P, { main: true });
  [-11, -6, -1, 4].forEach((x, i) => ink(ctx, `bo-br${i}`, [[x - 2, -23 - (x > -8 ? 1 : 0)], [x, -27.4], [x + 2, -24]], P.d, { sharp: true }));
  back(ctx, "bo", [[-8, -24], [6, -23]], P);
  for (const x of [-7, 8]) mass(ctx, `bo-l${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P);
  mass(ctx, "bo-ear", [[11, -21], [12, -26], [15, -21]], P, { color: P.d, sharp: true });
  mass(ctx, "bo-head", [[9, -22], [16, -21], [22, -16], [23, -11], [17, -9], [10, -11]], P, { main: true });
  ink(ctx, "bo-snout", ellPts(22.4, -13.2, 2.2, 2.8, 10), P.l);
  ink(ctx, "bo-tusk", [[18.6, -11.4], [21.4, -17.4], [20.4, -11]], "#f4ecd8", { sharp: true });
  eye(ctx, 16.6, -17.4, P, 0.9);
}

function drawBear(ctx: Ctx, P: Palette): void {
  for (const x of [-11, 6]) mass(ctx, `be-lf${x}`, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], P, { color: P.d });
  mass(ctx, "be-body", [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], P, { main: true });
  back(ctx, "be", [[-10, -28.4], [-3, -29.8], [4, -29.2]], P);
  for (const x of [-6, 11]) mass(ctx, `be-l${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], P);
  mass(ctx, "be-head", [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], P, { main: true });
  mass(ctx, "be-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), P);
  ink(ctx, "be-snout", ellPts(23.4, -22.2, 2.6, 2, 10), P.l);
  dot(ctx, 25.2, -23, 0.9, 0.8, INK);
  eye(ctx, 18.6, -25.6, P, 0.9);
}

function drawBat(ctx: Ctx, P: Palette): void {
  mass(ctx, "fl-bwf", [[-1, -3], [-10, -16], [-20, -14], [-17, -9], [-22, -6], [-15, -3], [-16, 2], [-4, 1]], P, { color: P.d });
  mass(ctx, "fl-bbody", ellPts(0, 0, 6, 7, 16), P, { main: true });
  mass(ctx, "fl-bwn", [[1, -3], [10, -18], [21, -17], [18, -11], [24, -8], [16, -4], [17, 1], [4, 1]], P, { main: true });
  for (const [x, t] of [[3, -14], [7.4, -14.6]] as const) mass(ctx, `fl-be${x}`, [[x - 1.6, -8.4], [x, t], [x + 1.6, -8.4]], P, { sharp: true });
  mass(ctx, "fl-bhead", ellPts(5, -6.4, 4, 3.6, 12), P);
  eye(ctx, 7, -7, P, 0.8);
  fang(ctx, "fl-bfang", 7.6, -3.6, 1.6);
  // Q 版：蝠不畫 back()（背點在翅尖外，晶刺、苔點會浮在半空）
}

function drawBird(ctx: Ctx, P: Palette): void {
  mass(ctx, "fl-wf", [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]], P, { color: P.d, sharp: true });
  mass(ctx, "fl-tail", [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]], P, { color: P.d, sharp: true });
  mass(ctx, "fl-body", ellPts(0, 0, 9, 6, 16), P, { main: true });
  ink(ctx, "fl-belly", ellPts(1.5, 2, 6, 3, 12), P.mat === "fur" ? "#f0e6d0" : P.l);
  mass(ctx, "fl-wn", [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]], P, { main: true, sharp: true });
  mass(ctx, "fl-head", ellPts(9, -4, 4.2, 4.2, 12), P);
  ink(ctx, "fl-beak", [[12.5, -5.2], [17, -3], [12.5, -1]], "#e8bb48", { sharp: true });
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
  const legs: Pt[][] = [
    [[1, -10], [-6, -19], [-13, 0]],
    [[3, -10], [0, -21], [-4, 0]],
    [[5, -10], [9, -21], [8, 0]],
    [[7, -10], [16, -18], [18, 0]],
  ];
  legs.forEach((l, i) => limb(ctx, `sp-lf${i}`, l.map(([x, y]): Pt => [x - 2.2, y - 0.6]), 0.9, P.d));
  mass(ctx, "sp-abd", ellPts(-9, -12, 9, 8, 18), P, { main: true });
  back(ctx, "sp", [[-12, -19.6], [-6, -19.4]], P);
  stroke(ctx, "sp-mark", [[-11, -15], [-8, -11], [-11, -8]], 1.2, P.accent ?? "#c0392b");
  mass(ctx, "sp-head", ellPts(5, -9, 6, 5, 14), P);
  legs.forEach((l, i) => limb(ctx, `sp-l${i}`, l, 1, P.base));
  mark("sp-eyes");
  for (const [x, y] of [[9.4, -11], [10.6, -9.4], [8.6, -9.2]] as const) dot(ctx, x, y, 0.7, 0.7, P.eye);
  fang(ctx, "sp-fang", 10, -6, 2);
}

function drawBeetle(ctx: Ctx, P: Palette): void {
  const legs: Pt[][] = [
    [[-8, -6], [-12, -3], [-13, 0]],
    [[0, -6], [-1, -2], [-2, 0]],
    [[7, -6], [9, -3], [11, 0]],
  ];
  legs.forEach((l, i) => limb(ctx, `bt-lf${i}`, l.map(([x, y]): Pt => [x + 2, y]), 0.8, P.d));
  mass(ctx, "bt-shell", [[-14, -8], [-13, -15], [-6, -20], [4, -20], [11, -15], [12, -8], [0, -6]], P, { main: true });
  stroke(ctx, "bt-seam", [[-13, -10], [-4, -14.6], [8, -16.6]], 0.6);
  back(ctx, "bt", [[-6, -20], [1, -20.4]], P);
  mass(ctx, "bt-head", [[11, -14], [16, -15], [19, -11], [17, -7], [11, -7]], P, { color: P.d });
  mass(ctx, "bt-horn", [[16, -13.4], [23, -18], [19.4, -11]], P, { color: P.l, sharp: true });
  legs.forEach((l, i) => limb(ctx, `bt-l${i}`, l, 0.9, P.base));
  mark("bt-eye");
  eye(ctx, 15.6, -11.6, P, 0.8);
}

function drawLizard(ctx: Ctx, P: Palette): void {
  for (const x of [-6, 9]) mass(ctx, `lz-lf${x}`, [[x - 2, -6], [x + 2, -6], [x + 1, 0], [x - 3, 0]], P, { color: P.d });
  mass(ctx, "lz-tail", [[-8, -10], [-20, -9], [-30, -3], [-32, -1], [-22, -4], [-8, -5]], P, { main: true });
  mass(ctx, "lz-body", [[-10, -5], [-10, -11], [-2, -14], [10, -13], [14, -9], [12, -5], [0, -4]], P, { main: true });
  for (const x of [-6, -1, 4]) ink(ctx, `lz-sp${x}`, [[x - 2, -13.4], [x, -18.4], [x + 2, -13.6]], P.mat === "fur" ? "#c0392b" : P.l, { sharp: true });
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
  const plates: Pt[][] = [
    [[-8, -21], [-9, -7]],
    [[3, -21], [2, -7]],
    [[-14, -12.4], [11.4, -12.4]],
  ];
  plates.forEach((l, i) => stroke(ctx, `sh-plate${i}`, l, 0.6));
  stroke(ctx, "sh-rim", [[-16, -6], [13, -6]], 2.2, INK);
  stroke(ctx, "sh-rim2", [[-16, -6], [13, -6]], 1.2, P.l);
  back(ctx, "sh", [[-9, -21], [-2, -22.6], [5, -21.4]], P);
  for (const x of [-11, 5]) mass(ctx, `sh-l${x}`, [[x, -7], [x + 5, -7], [x + 5.6, 0], [x - 0.4, 0]], P, { color: P.l });
  mass(ctx, "sh-head", [[11, -11], [16, -12], [20, -9], [19, -5], [13, -5]], P, { color: P.l });
  eye(ctx, 17, -9.4, P, 0.8);
}

function drawOoze(ctx: Ctx, P: Palette): void {
  mass(ctx, "oz-blob", [[-13, 0], [-14, -6], [-10, -13], [-3, -17], [5, -16], [11, -11], [13, -4], [12, 0]], P, { main: true });
  for (const [x, y, r] of [[-6, -6, 1.8], [-2, -11, 1.2], [8, -5, 1.4]] as const) ink(ctx, `oz-bub${x}`, ellPts(x, y, r, r, 8), P.l);
  back(ctx, "oz", [[-6, -15], [2, -16.6]], P);
  mark("oz-face");
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
  ink(ctx, "go-eye", [[2.4, -44.6], [6.4, -44.6], [6.4, -43], [2.4, -43]], P.accent ?? "#ffd23a", { sharp: true });
  mass(ctx, "go-arm", [[4, -38], [11, -38], [16, -24], [16, -14], [10, -14], [9, -24]], P, { main: true });
  mass(ctx, "go-fist", ellPts(13, -12, 4, 3.6, 12), P);
}

function drawWisp(ctx: Ctx, P: Palette): void {
  ctx.save();
  ctx.translate(0, -20);
  for (const [i, [x, y, s]] of ([[-11, -5, 2.4], [10, -8, 2], [3, 9, 1.8]] as const).entries()) {
    mass(ctx, `wp-or${i}`, [[x, y - s * 1.6], [x + s, y], [x, y + s * 1.6], [x - s, y]], P, { sharp: true, color: P.l });
  }
  mass(ctx, "wp-core", [[0, -11], [7.4, 0], [0, 11], [-7.4, 0]], P, { main: true, sharp: true });
  ink(ctx, "wp-in", [[0, -5], [3.4, 0], [0, 5], [-3.4, 0]], P.accent ?? P.eye, { sharp: true });
  dot(ctx, 1.2, -0.6, 0.9, 1.3, INK);
  ctx.restore();
}

function drawFeline(ctx: Ctx, P: Palette): void {
  for (const x of [-8, 10]) mass(ctx, `fe-lf${x}`, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], P, { color: P.d });
  mass(ctx, "fe-tail", [[-12, -12.4], [-21, -12], [-26, -7], [-24, -5.4], [-20, -9], [-12, -9]], P);
  mass(ctx, "fe-body", ellPts(0, -11, 14, 5, 20), P, { main: true });
  back(ctx, "fe", [[-6, -15.6], [2, -16]], P);
  for (const x of [-11, 7]) mass(ctx, `fe-l${x}`, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], P);
  for (const x of [13, 17.4]) mass(ctx, `fe-ear${x}`, [[x - 2.2, -16.6], [x, -21.6], [x + 2.2, -16.6]], P, { sharp: true });
  mass(ctx, "fe-head", ellPts(15, -14.5, 5.4, 4.6, 16), P, { main: true });
  ink(ctx, "fe-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), P.l);
  eye(ctx, 17.2, -15.4, P, 0.9);
  dot(ctx, 21, -13.4, 0.6, 0.5, INK);
}

function drawWraith(ctx: Ctx, P: Palette): void {
  ctx.save();
  ctx.translate(0, -4);
  limb(ctx, "wr-arm-l", [[-7, -30], [-12, -22], [-14, -16]], 2.2, P.base);
  mass(ctx, "wr-body", [[-8, -34], [-10, -20], [-7, -8], [-4, -2], [-1, -6], [2, -1], [5, -6], [9, -18], [8, -34]], P, { main: true });
  mass(ctx, "wr-head", ellPts(0, -38, 6, 6.4, 14), P);
  for (const x of [-2.4, 2.4]) {
    // Q：暗色眼窩＋方眼，霧材質、任何元素都看得到
    dot(ctx, x, -38, 1.9, 2.1, darken(P.base, 0.55));
    eye(ctx, x, -38, { eye: lighten(P.eye, 0.4) }, 0.85);
  }
  limb(ctx, "wr-arm-r", [[7, -30], [12, -23], [15, -18]], 2.2, P.base);
  ctx.restore();
}

function drawPylon(ctx: Ctx, P: Palette): void {
  ink(ctx, "py-base", [[-8, 0], [-9, -5], [9, -5], [8, 0]], "#6a645e");
  mass(ctx, "py-ob", [[-5, -5], [-4, -30], [0, -38], [4, -30], [5, -5]], P, { main: true, sharp: true });
  ink(ctx, "py-eye", ellPts(1.6, -22, 1.8, 2.4, 10), P.accent ?? P.eye);
  dot(ctx, 2, -22, 0.5, 1.2, INK);
  ctx.save();
  ctx.globalAlpha = 0.8;
  stroke(ctx, "py-ring", [...ellPts(0, -22, 8.6, 2.4, 20), [8.6, -22]], 0.7, P.accent ?? P.l);
  ctx.restore();
}

export const BODIES: Readonly<Record<string, BodyDef>> = {
  hound: { zh: "犬狼", fur: "#7a7a82", top: -36, head: [20, -28], len: 24, sp: [[-10, -25], [-4, -25.6], [2, -25.4]], qHead: Q_HEADS["hound"]!, draw: drawHound },
  boar: { zh: "野豬", fur: "#6a4a36", top: -28, head: [16, -18], len: 22, sp: [[-8, -24], [-1, -25], [6, -23]], qHead: Q_HEADS["boar"]!, draw: drawBoar },
  bear: { zh: "熊", fur: "#6a4a32", top: -33, head: [18, -26], len: 22, sp: [[-10, -28.4], [-3, -29.8], [4, -29.2]], qHead: Q_HEADS["bear"]!, draw: drawBear },
  flyer: {
    zh: "飛禽",
    fur: "#a07a4a",
    top: -50,
    head: [9, -22],
    len: 20,
    hover: true,
    sp: [[-4, -22], [0, -24], [4, -22]],
    qHeadBy: { bat: ["fl-be", 4, -2, 1.25], bird: ["fl-head", 6, -2, 1.18, "fl-claw"] },
    draw: drawFlyer,
  },
  crawler: { zh: "爬蟲", fur: "#3a3440", top: -24, head: [15, -12], len: 18, sp: [[-8, -20], [-2, -20.4]], draw: (ctx, P, v) => (v === "spider" ? drawSpider(ctx, P) : drawBeetle(ctx, P)) },
  lizard: { zh: "蜥蜴", fur: "#6a7a3a", top: -19, core: [2, -7.4], head: [20, -12], len: 30, sp: [[-6, -13.6], [-1, -14], [4, -13.6]], qHead: Q_HEADS["lizard"]!, draw: drawLizard },
  serpent: { zh: "蛇", fur: "#5a7a3a", top: -30, head: [12, -26], len: 17, sp: [[-10, -7], [-1, -10.4]], qHead: Q_HEADS["serpent"]!, draw: drawSerpent },
  shell: { zh: "龜殼", fur: "#5a6a4a", top: -23, head: [16, -9], len: 20, sp: [[-9, -21], [-2, -22.6], [5, -21.4]], qHead: Q_HEADS["shell"]!, draw: drawShell },
  ooze: { zh: "軟泥", fur: "#6a9a5a", top: -18, head: [6, -10], len: 15, sp: [[-6, -15], [2, -16.6]], draw: drawOoze },
  golem: { zh: "傀儡", fur: "#8a847e", top: -49, core: [-1, -29], head: [2, -44], len: 17, sp: [[-9, -38.4], [-3, -39.6], [3, -40]], qHead: Q_HEADS["golem"]!, draw: drawGolem },
  wisp: { zh: "晶靈", fur: "#9a86ff", top: -34, core: [0, -20], head: [0, -22], len: 12, hover: true, sp: [[0, -31]], draw: drawWisp },
  feline: { zh: "豹", fur: "#c8a060", top: -23, head: [15, -15], len: 22, sp: [[-8, -15], [-2, -16], [4, -15.6]], qHead: Q_HEADS["feline"]!, draw: drawFeline },
  wraith: { zh: "霧魅", fur: "#e6ecef", top: -46, head: [0, -42], len: 12, hover: true, sp: [[-4, -40], [4, -40]], draw: drawWraith },
  pylon: { zh: "晶塔", fur: "#8a847e", top: -40, head: [1, -24], len: 9, sp: [[0, -38]], draw: drawPylon },
};
export const BODY_IDS: readonly string[] = Object.keys(BODIES);
/** 有款式的身形：第一個是預設款。 */
export const BODY_VARIANTS: Readonly<Record<string, readonly string[]>> = { flyer: ["bird", "bat"], crawler: ["beetle", "spider"] };

// 動畫掛點（RIG）與 Q 大頭的支點搬到 creatureRig.ts（qCreatureAnim 也要讀，避免循環匯入）。
export { RIG, type RigDef };
/** 動畫掛點用的身形鍵（飛禽、爬蟲分款式）。 */
export const rigKey = (r: Pick<ResolvedCreature, "body" | "variant">): string => (r.body === "flyer" || r.body === "crawler" ? r.variant : r.body);
/** 16 款（動畫、畫廊的順序）。 */
export const RIG_KEYS: readonly string[] = ["hound", "boar", "bear", "feline", "lizard", "shell", "beetle", "spider", "serpent", "ooze", "golem", "wisp", "wraith", "pylon", "bird", "bat"];

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
  /** 堅甲的鐵片高度（人形：肩胸）。 */
  armorY?: number | undefined;
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
    ink(ctx, `tr-cr${i}`, [q(-4.4, 2.6), q(-3.6, -2.4), q(0, -3.6), q(3.6, -2.4), q(4.4, 2.6), q(0, 3.4)], BASALT);
    stroke(ctx, `tr-crl${i}`, [q(0, -3.2), q(0, 3)], 0.45, "#1c1412");
  });
  ([[-2, -1, 2, -2], [-4, 6, -1, 9], [3, 5, 5, 8]] as const).forEach(([x0, y0, x1, y1], i) => stroke(ctx, `tr-crg${i}`, [[cx + x0, cy + y0], [cx + x1, cy + y1]], 0.9, FIRE[1]));
}

/** 特徵：`soft` ＝ 無外框、半透明，畫在剪影外（霧團、黃煙）；`behind` ＝ 畫在身體後面（霧氣繞身）。 */
export const TRAITS: Readonly<Record<string, { zh: string; soft?: boolean; draw: FxDraw }>> = {
  stone_back: { zh: "背上石板", draw: (ctx, a) => a.sp.forEach(([x, y], i) => ink(ctx, `tr-sb${i}`, [[x - 3, y + 1.4], [x - 1.6, y - 4.4 - (i % 2) * 1.6], [x + 2.6, y - 3.4], [x + 3, y + 1.4]], "#8a8f94", { sharp: true })) },
  volcano: {
    zh: "背上小火山",
    draw: (ctx, a, P) => {
      const [x, y] = a.sp[Math.floor(a.sp.length / 2)] ?? a.head;
      ink(ctx, "tr-vc", [[x - 6, y + 2], [x - 2, y - 6], [x + 2, y - 6], [x + 6, y + 2]], "#4a3a34");
      ink(ctx, "tr-vc-mouth", ellPts(x, y - 6, 2, 0.8, 10), P?.accent ?? FIRE[0]);
      ([[-0.6, -9.6, 1.6], [1.6, -12.4, 1.9]] as const).forEach(([dx, dy, r], i) => ink(ctx, `tr-vc-sm${i}`, ellPts(x + dx, y + dy, r, r, 10), "#9a9490"));
    },
  },
  smoke: {
    zh: "黃煙",
    soft: true,
    // Q：無外框、半透明，從背上往上飄、越高越大越淡
    draw: (ctx, a) =>
      ([[-a.len * 0.25, a.top - 1, 2, 0.6], [-a.len * 0.1, a.top - 5.5, 2.8, 0.45], [a.len * 0.05, a.top - 11, 3.6, 0.3]] as const).forEach(([x, y, r, al], i) => {
        ctx.save();
        ctx.globalAlpha = al;
        ink(ctx, `tr-sk${i}`, ellPts(x, y, r, r * 0.85, 12), "#e8d860", { line: false });
        ctx.restore();
      }),
  },
  mist: {
    zh: "霧氣繞身",
    soft: true,
    draw: (ctx, a) => {
      ctx.save();
      ctx.globalAlpha = 0.55;
      ([[-a.len * 0.7, -2, 3.4], [-a.len * 0.1, -1, 4], [a.len * 0.6, -2.4, 3]] as const).forEach(([x, y, r], i) => ink(ctx, `tr-ms${i}`, ellPts(x, y, r, r * 0.55, 12), "#eef2f4", { line: false }));
      stroke(ctx, "tr-ms-l", [[-a.len, -6], [-a.len * 0.4, -8], [0, -6]], 0.5, "#ffffff");
      ctx.restore();
    },
  },
  core: {
    zh: "熔核",
    draw: (ctx, a, P) => {
      const [x, y] = a.core ?? a.head;
      const c = P?.accent ?? FIRE[0];
      ink(ctx, "tr-core", ellPts(x, y, 3.2, 3.2, 12), c);
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
  brood: { zh: "背負卵囊", draw: (ctx, a, P) => a.sp.forEach(([x, y], i) => ink(ctx, `tr-egg${i}`, ellPts(x, y - 2, 2.4, 3, 10), P?.accent ?? "#ffb23a")) },
  lava_pool: {
    zh: "背負熔岩池",
    draw: (ctx, a, P) => {
      const [x0, y0] = a.sp[0] ?? a.head;
      const x1 = (a.sp[a.sp.length - 1] ?? a.head)[0];
      ink(ctx, "tr-pool-rim", [[x0 - 5, y0 + 1], [x0 - 3, y0 - 3], [x1 + 3, y0 - 4], [x1 + 5, y0], [x1 + 3, y0 + 3], [x0 - 3, y0 + 3]], "#4a3a34");
      ink(ctx, "tr-pool", ellPts((x0 + x1) / 2, y0 - 1.4, (x1 - x0) / 2 + 2, 1.4, 14), P?.accent ?? FIRE[0]);
    },
  },
  spots: {
    zh: "斑紋",
    draw: (ctx, _a, P) => {
      mark("tr-spots"); // CB-3：斑點算身體組（原本跟著最後畫的頭部組轉，上撩爪時會凸出背部）
      ([[-8, -12], [-3, -14], [2, -11.4], [-5, -9.4], [8, -12.4]] as const).forEach(([x, y]) => dot(ctx, x, y, 1.1, 0.8, P?.d ?? "#5a4a3a"));
    },
  },
  sparks: { zh: "電光", draw: (ctx, a) => ([[-a.len * 0.5, a.top * 0.75], [a.len * 0.6, a.top * 0.85]] as const).forEach(([x, y], i) => stroke(ctx, `tr-spk${i}`, [[x, y], [x + 2, y + 2], [x, y + 3], [x + 2.4, y + 5.4]], 0.9, "#fff36b")) },
};

// ============================== 精英詞綴（人形敵人同一套） ==============================
/** 連心的青色（頭上的結與到相鄰同門的虛線；虛線由戰場畫）。 */
export const LINK_COLOR = "#3fd0c0";

export const AFFIX: Readonly<Record<string, { zh: string; soft?: boolean; draw: (ctx: Ctx, a: FxInfo) => void }>> = {
  berserk: {
    zh: "狂暴的",
    draw: (ctx, a) => {
      const [hx, hy] = a.head;
      ([[-3, -6, 1.8], [1, -9, 2.2], [4.6, -6.4, 1.6]] as const).forEach(([dx, dy, r], i) => ink(ctx, `af-bz${i}`, ellPts(hx + dx, hy + dy, r, r, 10), "#ff8a7a"));
      for (const s of [-1, 1]) stroke(ctx, `af-bzv${s}`, [[hx - 1 + s * 1.4, hy - 3.2], [hx + s * 0.6, hy - 2], [hx + 1 + s * 1.4, hy - 3.2]], 0.8, "#e02a2a");
    },
  },
  regen: {
    zh: "再生的",
    draw: (ctx, a) =>
      ([[-a.len * 0.7, a.top * 0.45], [a.len * 0.5, a.top * 0.75], [-a.len * 0.2, a.top * 0.95], [a.len * 0.85, a.top * 0.3]] as const).forEach(([x, y], i) => {
        stroke(ctx, `af-rg${i}a`, [[x - 1.8, y], [x + 1.8, y]], 1.1, "#3f9a4a");
        stroke(ctx, `af-rg${i}b`, [[x, y - 1.8], [x, y + 1.8]], 1.1, "#3f9a4a");
        stroke(ctx, `af-rg${i}c`, [[x - 1.4, y], [x + 1.4, y]], 0.55, "#b6f0a0");
        stroke(ctx, `af-rg${i}d`, [[x, y - 1.4], [x, y + 1.4]], 0.55, "#b6f0a0");
      }),
  },
  armored: {
    zh: "堅甲的",
    draw: (ctx, a) => {
      const y = a.armorY ?? a.top * (a.hover === true ? 0.55 : 0.6);
      [-a.len * 0.35, a.len * 0.1].forEach((x, i) => ink(ctx, `af-ar${i}`, [[x - 4, y - 1.4], [x + 4, y - 2.4], [x + 4.6, y + 3], [x - 3.6, y + 3.6]], "#8d969f"));
      for (const x of [-a.len * 0.35, a.len * 0.1]) dot(ctx, x, y + 0.6, 0.6, 0.6, "#3c4248");
    },
  },
  swift: { zh: "迅捷的", draw: (ctx, a) => [a.top * 0.3, a.top * 0.55, a.top * 0.8].forEach((y, i) => stroke(ctx, `af-sw${i}`, [[-a.len - 3 - i * 2, y], [-a.len - 11 - i * 2, y]], 0.9, "#e8e8ea")) },
  elemental: {
    zh: "元素的",
    draw: (ctx, a) => {
      const c = (a.element !== undefined ? CREATURE_ELEM[a.element] : undefined) ?? FIRE;
      [-a.len * 0.6, a.len * 0.1, a.len * 0.75].forEach((x, i) => {
        ink(ctx, `af-el${i}`, [[x - 2, 0.6], [x - 0.6, -4.4], [x, -2.4], [x + 1, -6.4], [x + 2.2, 0.6]], c[0], { sharp: true });
        dot(ctx, x + 0.2, -1, 0.8, 1, c[1]);
      });
    },
  },
  mist_hidden: {
    zh: "霧隱的",
    soft: true,
    // 邊緣模糊：身邊幾團白霧（本體另外降到 75% 不透明）
    draw: (ctx, a) => {
      ctx.save();
      ctx.globalAlpha = 0.6;
      ([[-a.len * 0.8, a.top * 0.4, 3.6], [a.len * 0.7, a.top * 0.65, 3.2], [-a.len * 0.2, a.top * 0.95, 3], [a.len * 0.2, -1.4, 4]] as const).forEach(([x, y, r], i) => ink(ctx, `af-mh${i}`, ellPts(x, y, r, r * 0.7, 12), "#eef2f4", { line: false }));
      ctx.restore();
    },
  },
  linked: {
    zh: "連心的",
    // 頭上一顆青色連心結；連到相鄰同門的虛線由 BattleRenderer 畫（樣張畫的兩段示意線不畫進貼圖）
    draw: (ctx, a) => {
      const [hx] = a.head;
      const y = a.top - 4;
      for (const s of [-1, 1]) stroke(ctx, `af-lk${s}`, [[hx + s * 1.6, y + 2], [hx + s * 3.4, y - 0.4], [hx + s * 1.6, y - 2.4], [hx, y - 0.6]], 1, LINK_COLOR);
    },
  },
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

/** 人形敵人的詞綴特效位置（Q 版頭：圓心 (0,-29)、頭頂 -38；狂暴的紅霧在頭頂外、堅甲的鐵片在肩胸）。 */
export const HUMANOID_FX: FxInfo = { head: [2, -35], top: -40, len: 10, armorY: -20, sp: [[-4, -20], [3, -20]] };

// ============================== 組合 ==============================
export interface ResolvedCreature {
  body: string;
  variant: string;
  material: Material;
  element: string | undefined;
  tint: string | undefined;
  /** 大小倍率（含精英 ×1.15）。 */
  size: number;
  /** tiny／small（紋樣簡化成 1 筆）。 */
  lite: boolean;
  /** 認得的特徵（含依狀態的 status_traits；去重、保持順序）。 */
  traits: string[];
  affixes: string[];
  /** 頭目外光色；不是頭目為 `undefined`。 */
  glow: string | undefined;
  /** QK-4：有專屬畫法的頭目（qBoss）與目前階段；一般異形為 `undefined`。 */
  boss?: { id: BossId; phase: number } | undefined;
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
  const lite = look.size != null && (SIZES[look.size] ?? 1) < 0.95;
  const traits: string[] = [];
  const add = (t: string): void => {
    if (TRAITS[t] !== undefined && !traits.includes(t)) traits.push(t);
  };
  for (const t of look.traits ?? []) add(t);
  const statuses = input.statusIds ?? [];
  const byStatus = look.status_traits ?? {};
  for (const sid of Object.keys(byStatus).sort()) if (statuses.includes(sid)) for (const t of byStatus[sid] ?? []) add(t);
  const out: ResolvedCreature = { body, variant, material, element, tint, size, lite, traits, affixes: knownAffixes(input.affixes), glow };
  const boss = bossOf(input.template, input.bossPhase, statuses);
  if (boss !== null) out.boss = boss;
  return out;
}

/** 貼圖快取鍵（外觀＋朝向）：status_traits 已解進 `traits`，狀態一變鍵就跟著變。 */
export function creatureKey(r: ResolvedCreature, facing: Facing): string {
  const boss = r.boss === undefined ? "" : `${r.boss.id}${r.boss.phase}`;
  return ["c", r.body, r.variant, r.material, r.element ?? "", r.tint ?? "", r.size.toFixed(3), r.lite ? "l" : "", r.traits.join("+"), r.affixes.join("+"), r.glow ?? "", boss, facing === "west" ? "w" : "e"].join("|");
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

/** 一隻的色票（tiny／small 簡化紋樣）。 */
export function creaturePalette(r: ResolvedCreature): Palette {
  return paletteOf(r.material, r.element, r.tint, BODIES[r.body]!.fur, r.lite);
}

/** 畫身體（平塗部件，不含外框）：特徵（soft、電光除外）畫在身上。`part` 為分部件姿勢。 */
function drawParts(ctx: Ctx, r: ResolvedCreature, P: Palette): void {
  const b = BODIES[r.body]!;
  S.qhead = (b.qHeadBy !== undefined ? b.qHeadBy[r.variant] : b.qHead) ?? null;
  S.inHead = false;
  S.headDone = false;
  S.last = "body";
  S.depth = 0;
  try {
    b.draw(ctx, P, r.variant);
    if (S.inHead) ctx.restore();
    S.qhead = null;
    S.inHead = false;
    S.headDone = false;
    const info = fxInfo(r);
    for (const t of r.traits) if (TRAITS[t]!.soft !== true && t !== "sparks") TRAITS[t]!.draw(ctx, info, P);
  } finally {
    S.qhead = null;
    S.inHead = false;
    S.headDone = false;
    S.depth = 0;
  }
}

/** 分部件姿勢在整隻（身體、特徵、詞綴）畫完之前都有效（同樣張 stamp 的 POSE）。 */
function withPose(r: ResolvedCreature, pose: QPartPose | null, fn: () => void): void {
  const rig = pose === null ? undefined : RIG[rigKey(r)];
  S.pose = pose;
  S.groups = rig?.groups ?? null;
  S.pivots = rig?.pivots ?? null;
  S.last = "body";
  try {
    fn();
  } finally {
    S.pose = null;
    S.groups = null;
    S.pivots = null;
    S.last = "body";
    S.depth = 0;
  }
}

/** 剪影外框層的範圍（單位，同樣張 BOX）。 */
const BOX: readonly [number, number, number, number] = [-62, -84, 62, 18];

/**
 * 異形貼圖畫哪一層（6R-F）：`all` ＝ 影子＋身體（原本）；`body` ＝ 只有身體（姿勢的位移改由戰場移動節點）；
 * `shadow` ＝ 只有地上的影子（身體移開時影子留在原地）。
 */
export type CreatureLayer = "all" | "body" | "shadow";

/** 一層：有 DOM 時用剪影外框層，沒有時（測試）直接平塗。 */
function layered(ctx: Ctx, draw: (g: Ctx) => void, o: Parameters<typeof qLayer>[3]): void {
  if (hasDom() && typeof ctx.getTransform === "function") {
    qLayer(ctx, BOX, draw, o);
    return;
  }
  ctx.save();
  if ((o?.alpha ?? 1) !== 1) ctx.globalAlpha = o?.alpha ?? 1;
  draw(ctx);
  ctx.restore();
}

/** CB-3：熊人立重拍的乳白三爪（照樣張 atk:slam 的 pose.over）：畫在近側前掌的掌端，跟著前腿組的變換；自己一層細外框。 */
function drawClaws(ctx: Ctx, pp: QPartPose, key: string): void {
  const piv = RIG[key]?.pivots["FN"];
  const cw = pp.claws ?? 0;
  if (piv === undefined || cw <= 0) return;
  const fn = pp.parts["FN"] ?? {};
  const draw = (g: Ctx): void => {
    g.translate(piv[0] + (fn.dx ?? 0), piv[1] + (fn.dy ?? 0));
    g.rotate(fn.rot ?? 0);
    g.transform(1, 0, fn.kx ?? 0, 1, 0, 0);
    g.scale(fn.sx ?? 1, fn.sy ?? 1);
    g.fillStyle = "#f4ecd8";
    for (const dx of [-2.6, 0, 2.6]) {
      g.beginPath();
      g.moveTo(dx - 1, 13);
      g.lineTo(dx + 0.6, 13 + 3.4 * cw);
      g.lineTo(dx + 1, 13);
      g.closePath();
      g.fill();
    }
  };
  if (hasDom() && typeof ctx.getTransform === "function") {
    qLayer(ctx, [-70, -90, 74, 18], draw, { ow: 0.5 });
    return;
  }
  ctx.save();
  draw(ctx);
  ctx.restore();
}

/** 片段的分部件姿勢（沒有片段 → `null`）。 */
function partPoseOf(r: ResolvedCreature, P: Palette, pose: CreaturePose | null): QPartPose | null {
  if (pose?.clip === undefined) return null;
  const key = rigKey(r);
  const clip = pose.clip.startsWith("atk:@") ? attackClipFor(key, pose.clip.slice(5) as AttackType) : pose.clip;
  if (clip === null) return null;
  const part = qCreaturePartPose({ key, element: r.element, mat: P.mat, base: P.base, accent: P.accent, traits: r.traits }, clip, pose.u ?? 0, pose.reduce === true, pose.perch ?? 0);
  return part !== null && pose.inPlace === true ? { ...part, root: { ...part.root, dx: 0 } } : part;
}

/**
 * 畫一隻異形（腳底在原點、朝東，已乘上大小；呼叫端鏡像）：影子、分身、本體（霧隱 75%）、軟特效、詞綴特效、動畫特效。地面環由戰場畫。
 * `pose`：片段（`clip`、`u`）＋整隻的伸縮、傾斜、透明（跳躍）；不給或 `null` 時是靜態。
 * `ground`：false ＝ 不畫地上的影子；`"only"` ＝ 只畫影子。
 */
export function drawCreature(ctx: Ctx, r: ResolvedCreature, pose: CreaturePose | null = null, ground: boolean | "only" = true): void {
  if (r.boss !== undefined) {
    drawBossFrame(ctx, r.boss, pose, ground);
    return;
  }
  const b = BODIES[r.body]!;
  const P = creaturePalette(r);
  const info = fxInfo(r);
  const pp = partPoseOf(r, P, pose);
  ctx.save();
  ctx.scale(r.size, r.size);
  const sh = pp?.shadow ?? 1;
  if (ground !== false && sh > 0) {
    ctx.save();
    ctx.fillStyle = "rgba(10,8,14,0.32)";
    ctx.beginPath();
    ctx.ellipse(pp?.root.dx ?? 0, 0.2, Math.max(7, b.len * 0.62) * sh, 2.4 * sh, 0, 0, TAU);
    ctx.fill();
    ctx.restore();
  }
  if (ground === "only") {
    ctx.restore();
    return;
  }
  if (pose !== null) applyCreaturePose(ctx, pose); // 整隻的位移、伸縮、傾斜、透明（戰場上位移已由 splitCreatureOffset 拆給節點）
  const T0 = typeof ctx.getTransform === "function" ? ctx.getTransform() : null;
  const soft = (fn: () => void): void => {
    if (pp?.softGround !== true || T0 === null) {
      fn();
      return;
    }
    ctx.save();
    ctx.setTransform(T0);
    fn();
    ctx.restore();
  };
  const rootOn = pp !== null && applyPartXf(ctx, pp.root, [0, 0]); // applyPartXf 自己 save
  const pa = pp?.alpha ?? 1;
  const flash = Math.max(pp?.flash ?? 0, pose === null ? 0 : cp(pose, "flash"));
  const ow = 1.3 / r.size;
  const mist = P.mat === "mist" ? 0.62 : 1;
  const hid = r.affixes.includes("mist_hidden") ? 0.75 : 1;
  withPose(r, pp, () => {
  if (r.traits.includes("mist")) soft(() => TRAITS["mist"]!.draw(ctx, info, P)); // 霧在身體後面
  const fade: readonly [number, number] | null = P.mat === "mist" ? [1, b.top * 0.3] : null; // 霧材質：下緣 3 段淡出
  if (r.affixes.includes("mirror"))
    layered(
      ctx,
      (g) => {
        g.translate(-9, -1);
        drawParts(g, r, P);
      },
      { ow, alpha: 0.35 * pa, fade },
    );
  layered(ctx, (g) => drawParts(g, r, P), { ow, alpha: mist * hid * pa, glow: r.glow, fade, flash, flashColor: pp?.flashColor });
  if (pp?.claws !== undefined && pp.claws > 0) drawClaws(ctx, pp, rigKey(r));
  for (const t of r.traits) if (TRAITS[t]!.soft === true && t !== "mist") soft(() => TRAITS[t]!.draw(ctx, info, P));
  for (const a of r.affixes) if (AFFIX[a]?.soft === true) soft(() => AFFIX[a]!.draw(ctx, info));
  const fx = r.affixes.filter((a) => AFFIX[a] !== undefined && AFFIX[a].soft !== true);
  const sparks = r.traits.includes("sparks");
  if (fx.length > 0 || sparks)
    layered(
      ctx,
      (g) => {
        if (sparks) TRAITS["sparks"]!.draw(g, info, P);
        for (const a of fx) AFFIX[a]!.draw(g, info);
      },
      pa < 1 ? { ow: 0.8 / r.size, alpha: pa } : { ow: 0.8 / r.size },
    );
  });
  if (rootOn) ctx.restore();
  // CB-3c：目標在正南／正北（`fxTurn`）時特效不畫進身體貼圖，由 `renderCreatureFxCanvas` 另畫、戰場放到目標那一格
  if (pp !== null && pp.fx.length > 0 && pose?.fxTurn === undefined) drawCreatureFx(ctx, creatureFxShown(pp.fx, pose), r.element);
  ctx.restore();
}

/** 貼圖裡要畫的片段特效：樣張頁（`fxAll`）全畫；戰場上飛向目標的與蛋由技能特效畫，不畫進貼圖。 */
function creatureFxShown(fx: readonly CreatureFx[], pose: CreaturePose | null): readonly CreatureFx[] {
  return pose?.fxAll === true ? fx : fx.filter((f) => f.ranged !== true && f.lobbed !== true);
}

/**
 * CB-3c：轉向後的特效畫布（虛擬單位；原點＝「相鄰目標」那一點的地面，放在目標格上）。上下都要放得下一格加特效高度。
 * CB-3c 時寬度同身體畫布 176（同一欄的特效都在中線上）。CB-4：斜向保留橫向 x（u ＝ x − 52），全部身形的攻擊片段 × 精英＋大型 1.4375
 * 最遠到 ±112.9（甲蟲爆裂的光點，含半徑；蹄後的塵土 −94.9），所以加寬到 240（半寬 120）；原點仍在中線，同一欄的畫面不變。
 * 頭目貼圖不含大小（`fxSizeOf` ＝ 1），片段特效的 u 在 −8～−2。都由 `cb4FxAnchor.test.ts` 鎖住。
 */
export const CREATURE_FX_BOX = { w: 240, h: 300, foot: 200 } as const;

/** CB-4：轉向特效貼圖裡的大小（頭目的貼圖不含大小，同 `unitSprite.creatureOffsetPx`）。 */
export function fxSizeOf(r: ResolvedCreature): number {
  return r.boss === undefined ? r.size : 1;
}

/** CB-3c／CB-4：這一格轉向後的片段特效（腳底座標、未乘大小；原點＝「相鄰目標」那一點）。沒有轉向、沒有特效 → 空。頭目照 `bossPoseFx`。 */
export function turnedCreatureFx(r: ResolvedCreature, pose: CreaturePose, c: number): CreatureFx[] {
  if (pose.fxTurn === undefined) return [];
  if (r.boss !== undefined) return turnCreatureFx(bossPoseFx(r.boss, pose), pose.fxTurn, c);
  const pp = partPoseOf(r, creaturePalette(r), pose);
  return pp === null ? [] : turnCreatureFx(creatureFxShown(pp.fx, pose), pose.fxTurn, c);
}

/**
 * CB-3c／CB-4：目標不在同一排時，片段這一格自帶的特效另畫一張（`creatureFxTurn.ts`）：原點在「相鄰目標」那一點、照 `facing` 鏡射。
 * `c`：往前一個虛擬單位轉成幾個虛擬單位往南／往北（`fxTurnScale`）。沒有轉向、這一格沒有特效、沒有 DOM → `null`。
 */
export function renderCreatureFxCanvas(r: ResolvedCreature, facing: Facing, dpr: number, pose: CreaturePose, c: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const fx = turnedCreatureFx(r, pose, c);
  if (fx.length === 0) return null;
  const { w, h, foot } = CREATURE_FX_BOX;
  const off = document.createElement("canvas");
  off.width = w * dpr;
  off.height = h * dpr;
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(w / 2, foot);
  if (facing === "west") o.scale(-1, 1);
  const size = fxSizeOf(r);
  o.scale(size, size);
  const a = pose.alpha;
  if (a !== undefined && a !== 1) o.globalAlpha = Math.max(0, Math.min(1, a));
  drawCreatureFx(o, fx, r.element, [-w / 2 / size, -foot / size, w / 2 / size, (h - foot) / size]);
  return off;
}

/** 人形敵人的詞綴特效與人形特徵（`under` ＝ 身體後面：霧氣繞身；否則畫在身上）。不認得的略過。 */
export function drawHumanoidFx(ctx: Ctx, affixes: readonly string[], traits: readonly string[], under: boolean): void {
  const info = HUMANOID_FX;
  const known = traits.filter((t) => TRAITS[t] !== undefined);
  if (under) {
    if (known.includes("mist")) TRAITS["mist"]!.draw(ctx, { ...info, len: 12 }, null);
    return;
  }
  for (const t of known) if (TRAITS[t]!.soft === true && t !== "mist") TRAITS[t]!.draw(ctx, { ...info, len: 12 }, null);
  const ids = knownAffixes(affixes);
  for (const a of ids) if (AFFIX[a]?.soft === true) AFFIX[a]!.draw(ctx, info);
  const solidT = known.filter((t) => TRAITS[t]!.soft !== true);
  const solidA = ids.filter((a) => AFFIX[a] !== undefined && AFFIX[a].soft !== true);
  if (solidT.length === 0 && solidA.length === 0) return;
  layered(
    ctx,
    (g) => {
      for (const t of solidT) TRAITS[t]!.draw(g, { ...info, len: 12 }, null);
      for (const a of solidA) AFFIX[a]!.draw(g, info);
    },
    { ow: 0.8 },
  );
}

/** 異形貼圖的虛擬畫布（QK-4 放大：動畫的撲擊、震地環、huge 都放得下）：176×136、腳底在下方 24px。 */
export const CREATURE_W = 176;
export const CREATURE_H = 136;
export const CREATURE_FOOT_Y = CREATURE_H - 24;
/** 頭目在戰場上照 huge 畫（QK-4b，取代 5A-ART 的 ×0.9；同樣張 QBoss.stampField）：整隻 ×1.6，腳底在自己那格，可蓋到隔壁格。 */
export const HUGE_FIELD_SCALE = BOSS_FIELD_SCALE;

/** 這隻的貼圖畫布（頭目另有較大的畫布）。 */
export function creatureCanvasSize(r: Pick<ResolvedCreature, "boss">): { w: number; h: number; foot: number } {
  if (r.boss !== undefined) return { w: BOSS_BOX.w, h: BOSS_BOX.h, foot: BOSS_BOX.foot };
  return { w: CREATURE_W, h: CREATURE_H, foot: CREATURE_FOOT_Y };
}

/** 頭頂的高度（虛擬單位、已乘大小；狀態列避開用）。 */
export function creatureTop(r: ResolvedCreature): number {
  if (r.boss !== undefined) return BOSS_BOX.top[r.boss.id];
  return bodyTop(r.body).top * r.size;
}

/**
 * 異形貼圖（朝西鏡像；頭目外光在剪影層裡）；沒有 DOM 時回傳 `null`。
 * `pose`：片段的這一格（`clip`、`u`）＋整隻的伸縮、傾斜、透明；白閃在剪影層裡（只閃剪影）。
 * `layer`（6R-F）：只畫身體或只畫影子（見 `CreatureLayer`）。
 */
export function renderCreatureCanvas(r: ResolvedCreature, facing: Facing, dpr: number, pose: CreaturePose | null = null, layer: CreatureLayer = "all"): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const { w, h, foot } = creatureCanvasSize(r);
  const off = document.createElement("canvas");
  off.width = w * dpr;
  off.height = h * dpr;
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(w / 2, foot);
  if (facing === "west") o.scale(-1, 1);
  drawCreature(o, r, layer === "shadow" ? null : pose, layer === "all" ? true : layer === "shadow" ? "only" : false);
  return off;
}

/** QK-4b：出手點（虛擬單位、未乘大小，朝東；嘴，頭目＝灰燼之心核心、碎晶之主前手晶）：飛行物、射線從這裡發出。 */
export function creatureMouth(r: ResolvedCreature): readonly [number, number] {
  if (r.boss !== undefined) return r.boss.id === "ah" ? [0, -28] : [52, -46];
  return BODY_ANIM[rigKey(r)]?.mouth ?? [10, -16]; // 大小由 creatureOffsetPx 乘
}

/** QK-4b：這隻異形有起飛／落地過場（鳥）。 */
export function creaturePerches(r: ResolvedCreature): boolean {
  return r.boss === undefined && PERCHERS.has(rigKey(r));
}

/** 待機的這一格（QK-4）：異形一圈 8 格、頭目 16 格；相位用單位 id 雜湊（同一隻每次一樣、不同隻錯開）。 */
export function creatureIdlePose(r: ResolvedCreature, clockMs: number, id: string): CreaturePose {
  if (r.boss !== undefined) {
    const ms = BOSS_MS["idle"] ?? 5278;
    const t = clockMs + ((idHash(id) % 1000) / 1000) * ms;
    const f = Math.floor((((t % ms) + ms) % ms) / (ms / BOSS_IDLE_N));
    return { clip: "idle", u: f / BOSS_IDLE_N };
  }
  return { clip: "idle", u: creatureFrameU(rigKey(r), "idle", clockMs, id) ?? 0 };
}
