// Q 版紙娃娃的共用核心（QK-1；照 docs/art/sample/qDoll.js 改寫，需求 docs/art/QK移植需求.md 第 0、2 節）。
// 座標：腳底中心 (0,0)、往上為負；身高約 46（頭正圓 r 8.5 在 y −29）。髖 −9、膝 −5、肩 −20、肘 −15、手 −9.5。
// 這個檔案放：型別、畫一隻時的共用狀態（樣張的模組變數 POSE／WEST／TINT…）、小工具、手臂規則 ARM（ARM_SPREAD_SET.E）、骨架 fk／ik。
// 畫法只換、不改規則：外觀資料照 `DollSpec`（appearance.ts），顏色由呼叫端的 hooks 決定（遊戲用 itemColors，畫廊對樣張時用樣張色）。
import type { Ctx } from "./artDraw";

export const TAU = Math.PI * 2;
/** 剪影外框色（樣張 OUT）。 */
export const Q_OUT = "#16121a";

/** Q 版的一件裝備（`GearItem` 的超集：樣張另有紋章 crest、背帶 strap）。 */
export interface QItem {
  kind: string;
  slot?: string;
  material?: string;
  color?: string;
  element?: string;
  form?: string;
  trim?: string;
  hilt?: string;
  crest?: string;
  strap?: string;
  glow?: string;
  /** 盾心紋樣（RG-4，DollGear.emblem）：目前只認 `peak`（雲紋碑盾的三峰山），不認得就不畫。 */
  emblem?: string;
  /** PB-1e 頭目部位破了（`render/bossPartArt.ts`）：拂塵剪短（只剩柄、金箍、三撮短毛）。 */
  cut?: boolean;
  /** PB-1e：劍斷（刃畫到鋸齒斷口為止）；`"side"`＝側面（斷口往刃尖移，鋸齒露在身體輪廓外）。 */
  broken?: boolean | "side";
}

/** Q 版外觀（`Look` 的超集：#137 的可選外觀、獸耳四種）。不認得的值當作沒有。 */
export interface QLook {
  skin: string;
  hair?: string;
  hairColor?: string;
  bunBand?: string;
  pants?: string;
  trim?: string;
  skull?: boolean;
  eyes?: string;
  build?: string;
  ears?: string;
  horns?: string;
  tail?: string;
  hornColor?: string;
  tailColor?: string;
  scaleColor?: string;
  pattern?: string;
  markColor?: string;
  beard?: boolean;
  tusks?: boolean;
  slitEyes?: boolean;
  ridge?: boolean;
  spines?: boolean;
  wings?: boolean;
  beastEars?: string;
  earColor?: string;
  face?: string;
  eyeStyle?: string;
  lashes?: boolean;
  beardStyle?: string;
  frame?: string;
  belt?: string;
}

export type QSlot = "head" | "body" | "hands" | "feet" | "cloak" | "main_hand" | "off_hand" | "neck" | "back" | "waist";
export type QGear = Partial<Record<QSlot, QItem>>;
export interface QUnit {
  look: QLook;
  gear: QGear;
  /** PB-1e：氣海（霧鎖真人）。`qi`＝露出時腹前的淡青氣旋、`crack`＝破了（三道裂痕＋淡霧）；都不描外框、排在主手武器之下。 */
  dantian?: "qi" | "crack";
}
export type QView = "front" | "back" | "side";

/** 畫布座標的一點。 */
export type P2 = [number, number];

/** 2D 變換矩陣（DOMMatrix 的 a～f）。 */
export interface M6 {
  a: number;
  b: number;
  c: number;
  d: number;
  e: number;
  f: number;
}

/** 武器回報（自測用）：握把、作用端、副手握點（畫布座標）、武器座標 → 畫布的矩陣、武器表 QW 的鍵（拄劍用短劍）。 */
export type QProbe = (kind: string, hand: P2, tip: P2, view: string, off: P2 | null, m: M6, wkey: string) => void;

/**
 * 姿勢（樣張 POSE）：inkPose 的欄位（bob、lean、hipN/F、kneeN/F、arm、wpn、armL/R、liftL/R、pull），
 * 加上 Q 版關鍵姿勢與待機的欄位（atk 雙手出招 0→1、bowAim 拉弓、nock 搭箭、dw 武器多轉、glow、orbY、lash、shieldUp）。
 * hands／layers／probe／tintOff 只給自測用。
 */
export interface QPose {
  bob?: number;
  lean?: number;
  hipN?: number;
  hipF?: number;
  kneeN?: number;
  kneeF?: number;
  arm?: number;
  /** 6N 片段的另一隻手（遠側）繞肩（掌心放出等手勢）；Q 版只在另一隻手空著時照用。 */
  armF?: number;
  /** QK-5：側面空著的主手、另一隻手的臂長加量（0＝原長，0.3＝長 1.3 倍；開場醒來半坐起撐地那一格用）。 */
  reach?: number;
  reachF?: number;
  wpn?: number | undefined;
  armL?: number;
  armR?: number;
  liftL?: number;
  liftR?: number;
  pull?: number;
  atk?: number;
  bowAim?: number;
  nock?: number;
  dw?: number;
  glow?: number;
  orbY?: number;
  lash?: number;
  shieldUp?: number;
  idle?: number;
  /** QK-7：1 ＝ 杖頭光暈由疊加層畫（貼圖裡不畫光暈）。 */
  glowLayer?: number;
  /** QK-5：正面、背面五類出招（qAnimFB.ts）：類別 1～5（劍、長槍、弓、法杖、拳）與關鍵幀時間 0～6；側面不吃。 */
  fbk?: number;
  fbt?: number;
  tintOff?: string;
  probe?: QProbe;
  hands?: Record<string, P2 | boolean>;
  layers?: string[];
}

type NumKey = "reach" | "reachF" | "bob" | "lean" | "hipN" | "hipF" | "kneeN" | "kneeF" | "arm" | "armF" | "armL" | "armR" | "liftL" | "liftR" | "pull" | "atk" | "bowAim" | "nock" | "dw" | "glow" | "orbY" | "lash" | "shieldUp" | "glowLayer";

/** 顏色掛勾：裝備的 [主色, 暗色]、元素色。 */
export interface QHooks {
  colors: (it: QItem) => readonly [string, string];
  tint: (element: string | undefined) => string | undefined;
}

/** 畫一隻時的共用狀態（樣張的模組變數）；每次 draw 開始時設好、結束時歸零。 */
export const S = {
  POSE: null as QPose | null,
  WEST: false,
  TINT: null as string | null,
  NOPAD: false,
  FAR: 0,
  FARH: 0,
  SEAM: false,
  NOBUCKLE: false,
  SEAMIN: false,
  SHEDGE: false,
  FILLARM: false,
  FREEARM: false,
  EBOFF: false,
  BOWP: null as { pull?: number | null; nock?: boolean; noArrow?: boolean } | null,
  BOWM: null as M6 | null,
  CTX: null as Ctx | null,
  hooks: null as QHooks | null,
  /** PB-1e：正在畫的手持物 kind（`mainWeapon` 畫 `W.draw` 的期間；部位圖層、遮罩用，見 `render/bossPartArt.ts`）。 */
  PAINT: null as string | null,
};

/** 讀姿勢欄位；沒給或不是有限數字 → 0。 */
export function pz(k: NumKey): number {
  const v = S.POSE?.[k];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

export function rotAt(ctx: Ctx, x: number, y: number, a: number): void {
  if (!a) return;
  ctx.translate(x, y);
  ctx.rotate(a);
  ctx.translate(-x, -y);
}
export function rr(ctx: Ctx, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}
export function fill(ctx: Ctx, c: string, path: () => void): void {
  ctx.beginPath();
  ctx.fillStyle = c;
  path();
  ctx.fill();
}
/** 兩色混合（樣張 mix；只認 #rrggbb）。 */
export function mix(a: string, b: string, t: number): string {
  const p = (h: string): number[] => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const A = p(a);
  const B = p(b);
  return "#" + A.map((v, i) => Math.round(v + ((B[i] ?? 0) - v) * t).toString(16).padStart(2, "0")).join("");
}
/** 一件裝備的 [主色, 暗色]；沒有裝備＝預設布衣色。 */
export function colors(it: QItem | null | undefined): readonly [string, string] {
  return it ? S.hooks!.colors(it) : ["#d8cdb4", "#a89c80"];
}
/** 武器顏色：有指定顏色或材質就照它，否則用預設材質（帶元素）。 */
export function wc(it: QItem | null | undefined, def: string): readonly [string, string] {
  return it && (it.color || it.material) ? colors(it) : S.hooks!.colors({ kind: it?.kind ?? "", material: def, ...(it?.element ? { element: it.element } : {}) });
}

const ID: M6 = { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
/** 目前的變換矩陣（測試用的假畫布沒有 getTransform 時當作單位矩陣）。 */
export function getM(ctx: Ctx): M6 {
  const m = (ctx as { getTransform?: () => unknown }).getTransform?.() as M6 | undefined;
  return m && typeof m.a === "number" ? { a: m.a, b: m.b, c: m.c, d: m.d, e: m.e, f: m.f } : { ...ID };
}
export const tp = (m: M6, x: number, y: number): P2 => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
export function invM(m: M6): M6 {
  const det = m.a * m.d - m.b * m.c || 1;
  return { a: m.d / det, b: -m.b / det, c: -m.c / det, d: m.a / det, e: (m.c * m.f - m.d * m.e) / det, f: (m.b * m.e - m.a * m.f) / det };
}
export function setM(ctx: Ctx, m: M6): void {
  ctx.setTransform(m.a, m.b, m.c, m.d, m.e, m.f);
}

// ---------- 手臂規則（ARM_SPREAD_SET.E，2026-11-06 使用者定案）----------
/** E：手臂微微離開（a 0.325）、sw 1、bk −1、shf、po 0、shA 0.2、ea 0.09、edge inner 0.9／0.45 ＋ fist ring 0.9／0.45、sideOne。 */
export interface ArmSpread {
  a: number;
  dx: number;
  tilt: number;
  robe: number;
  hold: number;
  sw: number;
  swa: number;
  bk?: number;
  shf?: boolean;
  po?: number;
  shA?: number;
  ea?: number;
  edge?: { mode: "ring" | "inner"; w: number; k: number; fist?: { mode: "ring" | "seam"; w: number; k: number } };
  sideOne?: boolean;
}
export const ARM_SPREAD_SET: Readonly<Record<"A" | "E", ArmSpread>> = {
  A: { a: 0.7, dx: 0, tilt: 0, robe: 0, hold: 0, sw: 0, swa: 0 },
  E: { a: 0.325, dx: 0, tilt: 0, robe: 0, hold: 0, sw: 1, swa: 0, bk: -1, shf: true, po: 0, shA: 0.2, ea: 0.09, edge: { mode: "inner", w: 0.9, k: 0.45, fist: { mode: "ring", w: 0.9, k: 0.45 } }, sideOne: true },
};
/** 目前的手臂規則（預設 E；自測比較第 16 版寬度時暫時換成 A）。 */
export const ARMS = { cur: ARM_SPREAD_SET.E };
export const ARM = (): ArmSpread => ARMS.cur;
/** 不是 A（第 16 版）時，正面、背面的袖子也描內框（樣張 SEAMF）。 */
export const SEAMF = (): boolean => ARMS.cur !== ARM_SPREAD_SET.A;

// ---------- 骨架：肩 (x,−20) → 肘（+5）→ 手（+5.5）----------
export const UA = 5;
export const FA = 5.5;
export const rot = (a: number, [x, y]: readonly [number, number]): P2 => [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)];
export const SHX = (): number => 8.5 + ARM().dx;
export const OUTA = (): number => ARM().a;

/** 肩角 sA、肘角 eA → 手的位置。 */
export function fk(x: number, sA: number, eA: number, len: readonly number[] | null = null): P2 {
  const ua = len ? (len[0] ?? UA) : UA;
  const fa = len ? (len[1] ?? FA) : FA;
  const e: P2 = [x - ua * Math.sin(sA), -20 + ua * Math.cos(sA)];
  return [e[0] - fa * Math.sin(sA + eA), e[1] + fa * Math.cos(sA + eA)];
}

/** 反解：手掌目標 t → 關節角度；out＝手肘往哪邊（+1 往 +x、−1、"down"）。 */
export function ik(x: number, t: readonly number[], out: number | "down", len: readonly number[] | null = null): { sA: number; eA: number; ok: boolean } {
  const ua = len ? (len[0] ?? 5) : 5;
  const fa = len ? (len[1] ?? 5.5) : 5.5;
  const reach = ua + fa - 0.1;
  const dx = (t[0] ?? 0) - x;
  const dy = (t[1] ?? 0) + 20;
  const r0 = Math.hypot(dx, dy);
  const r = Math.min(Math.max(r0, Math.abs(ua - fa) + 0.05), reach);
  const phi = Math.atan2(-dx, dy);
  const al = Math.acos((ua * ua + r * r - fa * fa) / (2 * ua * r));
  const be = Math.acos((ua * ua + fa * fa - r * r) / (2 * ua * fa));
  let best: { sA: number; eA: number; sc: number } | null = null;
  for (const sg of [1, -1]) {
    const sA = phi + sg * al;
    const eA = -sg * (Math.PI - be);
    const sc = out === "down" ? -20 + ua * Math.cos(sA) : (x - ua * Math.sin(sA)) * out;
    if (!best || sc > best.sc) best = { sA, eA, sc };
  }
  return { sA: best!.sA, eA: best!.eA, ok: r0 <= reach };
}

/** 指定手肘方向（dir：肩 → 手肘），前臂再指向目標 t。 */
export function elbowTo(x: number, dir: readonly number[], t: readonly number[], len: readonly number[] | null = null): { sA: number; eA: number; ok: boolean; h: P2 } {
  const ua = len ? (len[0] ?? UA) : UA;
  const fa = len ? (len[1] ?? FA) : FA;
  const d0 = dir[0] ?? 0;
  const d1 = dir[1] ?? 0;
  const l = Math.hypot(d0, d1);
  const e: P2 = [x + (ua * d0) / l, -20 + (ua * d1) / l];
  const sA = Math.atan2(-d0 / l, d1 / l);
  const fx = (t[0] ?? 0) - e[0];
  const fy = (t[1] ?? 0) - e[1];
  const fl = Math.hypot(fx, fy) || 1;
  const eA = Math.atan2(-fx / fl, fy / fl) - sA;
  return { sA, eA, ok: true, h: [e[0] + (fa * fx) / fl, e[1] + (fa * fy) / fl] };
}

/** 記下手的位置（自測用：POSE.hands）。 */
export const rec = (who: string): ((hand: P2, ctx: Ctx) => void) | null => {
  const hs = S.POSE?.hands;
  return hs ? (hand: P2, ctx: Ctx): void => void (hs[who] = tp(getM(ctx), hand[0], hand[1])) : null;
};
export const mark = (n: string): void => void S.POSE?.layers?.push(n);
export const clamp01 = (t: number): number => Math.max(0, Math.min(1, t));
export const isShield = (it: QItem | null | undefined): boolean => !!it && String(it.kind).startsWith("shield");
/** 塔盾一類（RG-4，docs/art/RG樣張.md 9.8 第 1 條；RG-5 加熔殼塔盾 10.5 第 2 條）：塔盾、雲紋碑盾 `sect_great`、熔殼塔盾 `molten_shell` 共用握法、位移、圖層。 */
export const isTowerLike = (it: QItem | null | undefined): boolean =>
  !!it && it.kind === "shield_kite" && (it.form === "tower" || it.form === "sect_great" || it.form === "molten_shell");
