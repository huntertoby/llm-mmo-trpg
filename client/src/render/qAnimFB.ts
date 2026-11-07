// Q 版正面（朝南）、背面（朝北）的五類出招（QK-5；照 docs/art/sample/qAnimFB.js 改寫，需求 docs/art/QK移植需求.md 第 6 節）。
// 樣張是 7 個關鍵幀（0 預備、1 起手、2 蓄力頂點、3 出招中、4 命中／出手、5 收招、6 回位）；遊戲裡用 `fbt`（0～6 的連續值）在相鄰兩幀之間插值：
//   手的目標點、身體起伏、抬腳、杖頭光、武器角度與縮短比例、槍長、弓弦等數值線性內插；兩幀的圖層結構（ops 的種類與層）不同時，過半就換到下一幀的結構。
// 手臂與武器分三層（qDoll.drawBody 依序呼叫）：under＝身體之前（被身體、頭擋住）、over＝身體之後頭之前、top＝頭之後（最靠鏡頭）。
// 背面五類另加身體前傾（美術 PM 建議、使用者「不 照建議」）：起手到命中 0.05→0.12 弧度，收招回正（`lean`，qDoll 的 fbLean）。
// 這裡只放資料與純函式（畫的工具由 qDoll 的 FbApi 給），沒有 Math.random、不讀時間。
import type { Ctx } from "./artDraw";
import { fk, ik, TAU, type P2, type QItem } from "./qCore";
import { BOW_EY, qWeapon, staffOrbColor } from "./qWeapons";

/**
 * 五類（`fbk` 的值 1～5）＋QK-5b 借用的兩組（6、7；美術 PM QK-5 檢查第 2 題「不另出樣張，借最接近的一組」）：
 * `gun`＝弩、火槍借弓那組的舉起與放箭格（不拉弦：第 2～3 格持平，武器畫在持弓手上、指向目標）；
 * `cast`＝法球、自身／地面施放借法杖那組（杖頭往前那兩格改畫手上的武器；沒有主手武器就空手，副手法球照畫）。
 */
export const FB_KINDS = ["sword", "spear", "bow", "staff", "gauntlet", "gun", "cast"] as const;
export type FbKind = (typeof FB_KINDS)[number];
export const fbKindIndex = (k: FbKind): number => FB_KINDS.indexOf(k) + 1;
export const fbKindOfIndex = (i: number): FbKind | null => FB_KINDS[Math.round(i) - 1] ?? null;
export type FbView = "front" | "back";
export type FbLayer = "under" | "over" | "top";
/** 樣張每幀 140ms；7 幀。 */
export const FB_FRAMES = 7;
export const FB_FRAME_MS = 140;
/** 命中（近戰）／出手（弓、杖）那一幀。 */
export const FB_HIT = 4;

type Hand = { h: P2; st?: boolean; out?: number | "down"; f?: number };
interface OpArm {
  t: "arm";
  L: FbLayer;
  who: "m" | "o";
  big?: number;
  clip?: "out";
}
interface OpW {
  t: "w";
  L: FbLayer;
  /** 畫在哪隻手（沒給＝主手；QK-5b 火器畫在副手＝持弓手）。 */
  on?: "o";
  a: number;
  s?: number;
  wd?: number;
  mg?: number;
  wrap?: boolean;
  clip?: "hand";
}
interface OpWrap {
  t: "wrap";
  L: FbLayer;
  a: number | "spA";
  on: "m" | "o";
}
/** 長槍：正面（d 沒給＝後手 → 前手）／背面（d 給定）；hand：只畫在主手拳頭裡（背面補畫握把）。 */
interface OpSpear {
  t: "spear";
  L: FbLayer;
  Lf: number;
  Lb: number;
  hl: number;
  hw: number;
  w0: number;
  w1: number;
  d?: P2;
  hand?: boolean;
}
interface OpStaff {
  t: "staffFS";
  L: FbLayer;
  d: P2;
  Lf: number;
  Lb: number;
  sc: number;
  w0: number;
  w1: number;
}
/** 弓：U＝弓臂方向、F＝弓背方向（沒給＝持弓手 − 拉弦手）；torso：只畫在軀幹範圍內（背面待機）。 */
interface OpBow {
  t: "bow";
  L: FbLayer;
  U: P2;
  pull: number;
  nock: boolean;
  F?: P2;
  torso?: boolean;
}
export type FbOp = OpArm | OpW | OpWrap | OpSpear | OpStaff | OpBow;
export interface FbFrame {
  m: Hand;
  o: Hand;
  bob?: number;
  liftL?: number;
  liftR?: number;
  glow?: number;
  lean?: number;
  ops: readonly FbOp[];
}

// ---------------- 關鍵幀（照 qAnimFB.js 的 C 表，數值不改） ----------------
const arm = (who: "m" | "o", L: FbLayer, x: Partial<OpArm> = {}): OpArm => ({ t: "arm", who, L, ...x });
const wpn = (L: FbLayer, a: number, x: Partial<OpW> = {}): OpW => ({ t: "w", L, a, ...x });
const wrapOp = (L: FbLayer, a: number | "spA", on: "m" | "o" = "m"): OpWrap => ({ t: "wrap", L, a, on });
const IDLE_F = { m: { h: [-11.85, -10.06] as P2, st: true }, o: { h: [11.85, -10.06] as P2, st: true } };
const IDLE_B = { m: { h: [11.85, -10.06] as P2, st: true }, o: { h: [-11.85, -10.06] as P2, st: true } };
const PI = Math.PI;
/** 背面前傾（0 預備 … 4 命中 … 6 回正）。 */
const LEAN = [0, 0.05, 0.08, 0.1, 0.12, 0.05, 0] as const;
const lean = (fr: readonly FbFrame[]): FbFrame[] => fr.map((f, i) => ({ ...f, lean: LEAN[i] ?? 0 }));

const SWORD: Record<FbView, readonly FbFrame[]> = {
  front: [
    { ...IDLE_F, ops: [arm("o", "over"), arm("m", "over"), wpn("over", -0.12, { wrap: true })] },
    { m: { h: [-13, -21.5], out: -1 }, o: { h: [12, -13], st: true }, bob: -0.4, ops: [arm("o", "over"), arm("m", "over"), wpn("over", -0.05, { wrap: true })] },
    { m: { h: [-12, -29.5], out: -1 }, o: { h: [11.5, -15], st: true }, bob: -0.6, ops: [wpn("under", 0.8), arm("o", "over"), arm("m", "over"), wrapOp("over", 0.8)] },
    { m: { h: [-11, -25], out: -1 }, o: { h: [12, -14], st: true }, bob: -0.3, ops: [arm("o", "over"), arm("m", "over"), wpn("top", -0.25, { s: 0.55, wd: 1.1, wrap: true })] },
    { m: { h: [-3, -14], st: true }, o: { h: [12.5, -14], st: true }, ops: [arm("o", "over"), arm("m", "top"), wpn("top", PI - 0.4, { s: 0.75, wd: 1.15, wrap: true })] },
    { m: { h: [-1.5, -13], out: "down" }, o: { h: [12, -12], st: true }, ops: [arm("o", "over"), arm("m", "top"), wpn("top", 2.25, { s: 0.95, wd: 1.05, wrap: true })] },
    { m: { h: [-11, -12], st: true }, o: IDLE_F.o, ops: [arm("o", "over"), arm("m", "over"), wpn("over", -0.5, { wrap: true })] },
  ],
  back: lean([
    { ...IDLE_B, ops: [wpn("under", 0.12), arm("o", "over"), arm("m", "over"), wpn("over", 0.12, { clip: "hand" })] },
    { m: { h: [13, -21.5], out: 1 }, o: { h: [-12, -13], st: true }, bob: -0.4, ops: [arm("o", "over"), arm("m", "over"), wpn("over", 0.05)] },
    { m: { h: [12, -29.5], out: 1 }, o: { h: [-11.5, -15], st: true }, bob: -0.6, ops: [arm("o", "over"), arm("m", "over"), wpn("top", -0.8)] },
    { m: { h: [10.5, -28], out: 1 }, o: { h: [-12, -14], st: true }, bob: -0.3, ops: [arm("o", "over"), wpn("over", 0.1, { s: 0.6 }), arm("m", "over"), wpn("over", 0.1, { s: 0.6, clip: "hand" })] },
    { m: { h: [3, -15], out: 1 }, o: { h: [-12.5, -16], st: true }, ops: [wpn("under", -2.2, { s: 0.8 }), arm("m", "over", { clip: "out" }), arm("o", "over")] },
    { m: { h: [0.5, -14.5], out: 1 }, o: { h: [-12, -15], st: true }, ops: [wpn("under", -2.55, { s: 0.85 }), arm("m", "over", { clip: "out" }), arm("o", "over")] },
    { m: { h: [11, -12], st: true }, o: IDLE_B.o, ops: [wpn("under", 0.4), arm("o", "over"), arm("m", "over"), wpn("over", 0.4, { clip: "hand" })] },
  ]),
};

const SPF = (Lf: number, hl: number, hw: number): FbOp[] => [
  arm("o", "over"),
  arm("m", "over"),
  { t: "spear", L: "over", Lf, Lb: 4, hl, hw, w0: 1.5, w1: 2.1 + hw * 0.06 },
  wrapOp("over", "spA", "m"),
  wrapOp("over", "spA", "o"),
];
const SPB = (Lf: number, Lb: number, d?: P2): FbOp[] => {
  const dd = d === undefined ? {} : { d };
  return [arm("o", "under"), { t: "spear", L: "under", Lf, Lb, hl: 3, hw: 3.4, w0: 2.4, w1: 1.3, ...dd }, arm("m", "over"), { t: "spear", L: "over", Lf, Lb, hl: 3, hw: 3.4, w0: 2.4, w1: 1.3, hand: true, ...dd }];
};
const SPEAR: Record<FbView, readonly FbFrame[]> = {
  front: [
    { m: { h: [-1, -17.5], out: -1 }, o: { h: [1.5, -13.3], out: 1 }, ops: SPF(14, 5, 6.5) },
    { m: { h: [-2.5, -19.5], out: -1 }, o: { h: [0.5, -15.5], out: 1 }, bob: -0.3, ops: SPF(11, 4.5, 6) },
    { m: { h: [-3, -20], out: -1 }, o: { h: [0, -16.3], out: 1 }, bob: -0.5, ops: SPF(10, 4.3, 5.8) },
    { m: { h: [-0.5, -16], st: true }, o: { h: [1.5, -12], st: true }, liftR: 1.5, ops: SPF(18, 6.2, 8.4) },
    { m: { h: [0, -15], st: true }, o: { h: [2, -11.5], st: true }, liftR: 1, ops: SPF(20, 7, 9.6) },
    { m: { h: [-0.3, -15.5], st: true }, o: { h: [1.8, -11.8], st: true }, ops: SPF(18.5, 6.6, 9) },
    { m: { h: [-1, -17.5], out: -1 }, o: { h: [1.5, -13.3], out: 1 }, ops: SPF(14, 5, 6.5) },
  ],
  back: lean([
    { m: { h: [9.3, -12.5], out: 1 }, o: { h: [2, -16.5], out: -1 }, ops: SPB(11, 9) },
    { m: { h: [10.2, -10.5], out: 1 }, o: { h: [0.5, -16.5], out: -1 }, bob: -0.3, ops: SPB(11, 10) },
    { m: { h: [10.4, -10], out: 1 }, o: { h: [0.2, -16.2], out: -1 }, bob: -0.5, ops: SPB(11, 10.5) },
    { m: { h: [8.6, -15], out: 1 }, o: { h: [0, -19], out: -1 }, liftL: 1.5, ops: SPB(22, 8, [-0.33, -0.94]) },
    { m: { h: [8, -16], out: 1 }, o: { h: [-0.5, -19.5], out: -1 }, liftL: 1, ops: SPB(25, 7.5, [-0.34, -0.94]) },
    { m: { h: [8.3, -15.5], out: 1 }, o: { h: [0, -19.2], out: -1 }, ops: SPB(24, 7.8, [-0.34, -0.94]) },
    { m: { h: [9.3, -12.5], out: 1 }, o: { h: [2, -16.5], out: -1 }, ops: SPB(11, 9) },
  ]),
};

const BK = BOW_EY + 9;
const F_FULL: P2 = [(4.5 - -5.5) / BK, (-14.5 - -24) / BK];
const F_FULL_B: P2 = [(-7.3 - 6) / BK, (-29.5 - -24.5) / BK];
const bow = (L: FbLayer, U: P2, pull: number, nock = true, F?: P2, torso = false): OpBow => ({ t: "bow", L, U, pull, nock, ...(F === undefined ? {} : { F }), ...(torso ? { torso } : {}) });
const BF = (U: P2, pull: number, nock = true, F?: P2): FbOp[] => [arm("o", "top"), bow("top", U, pull, nock, F), arm("m", "top")];
const BB = (U: P2, pull: number, nock: boolean, F?: P2, clipM = false): FbOp[] => [bow("under", U, pull, nock, F), arm("o", "over"), arm("m", "over", clipM ? { clip: "out" } : {})];
const BOW: Record<FbView, readonly FbFrame[]> = {
  front: [
    { m: { h: [0, -15], out: -1 }, o: { h: [5, -11.5], st: true }, ops: BF([-0.3, 0.95], 2) },
    { m: { h: [-1, -19], out: -1 }, o: { h: [5.5, -16.5], st: true }, bob: -0.2, ops: BF([-0.4, 0.92], 3) },
    { m: { h: [-3.5, -22], out: -1 }, o: { h: [5, -15.5], st: true }, bob: -0.3, ops: BF([-0.45, 0.89], 6) },
    { m: { h: [-5.5, -24], out: -1 }, o: { h: [4.5, -14.5], st: true }, bob: -0.3, ops: BF([-0.5, 0.87], 9) },
    { m: { h: [-8, -25.5], out: -1 }, o: { h: [4.5, -14.5], st: true }, bob: -0.2, ops: BF([-0.5, 0.87], 0, false, F_FULL) },
    { m: { h: [-7, -21], out: -1 }, o: { h: [4.5, -14], st: true }, ops: BF([-0.5, 0.87], 0, false, F_FULL) },
    { m: IDLE_F.m, o: { h: [5, -12], st: true }, ops: [arm("o", "top"), bow("top", [-0.3, 0.95], 0, false, [0.62, 0.42]), arm("m", "over")] },
  ],
  back: lean([
    { m: { h: [1, -14], out: 1 }, o: { h: [-4, -12], st: true }, ops: [bow("under", [0.3, 0.95], 1.5, true, undefined, true), arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })] },
    { m: { h: [3, -21.5], out: 1 }, o: { h: [-5.5, -24], st: true }, bob: -0.2, ops: BB([0.5, 0.87], 3, false, undefined, true) },
    { m: { h: [5, -23.5], out: 1 }, o: { h: [-6.8, -28], st: true }, bob: -0.3, ops: BB([0.6, 0.8], 6, false) },
    { m: { h: [6, -24.5], out: 1 }, o: { h: [-7.3, -29.5], st: true }, bob: -0.3, ops: BB([0.7, 0.71], 9, false) },
    { m: { h: [11, -24.5], out: 1 }, o: { h: [-7.3, -29.5], st: true }, bob: -0.2, ops: BB([0.7, 0.71], 0, false, F_FULL_B) },
    { m: { h: [10, -21], out: 1 }, o: { h: [-7, -28.5], st: true }, ops: BB([0.7, 0.71], 0, false, F_FULL_B) },
    { m: { h: [1, -14], out: 1 }, o: { h: [-4, -12], st: true }, ops: [bow("under", [0.3, 0.95], 0, false, [-0.5, -0.4], true), arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })] },
  ]),
};

const STF = (a: number, mg = 0): FbOp[] => [arm("o", "over"), arm("m", "over"), wpn("over", a, { mg, wrap: true })];
const STB = (a: number, mg = 0): FbOp[] => [wpn("under", a, { mg }), arm("o", "over"), arm("m", "over")];
const sfs = (L: FbLayer, d: P2, Lf: number, Lb: number, sc: number, w0: number, w1: number): OpStaff => ({ t: "staffFS", L, d, Lf, Lb, sc, w0, w1 });
const STAFF: Record<FbView, readonly FbFrame[]> = {
  front: [
    { ...IDLE_F, ops: STF(0, -1.9) },
    { m: { h: [-12.5, -21], out: -1 }, o: { h: [11.5, -15], st: true }, glow: 0.4, bob: -0.3, ops: STF(0.05) },
    { m: { h: [-11.5, -27], out: -1 }, o: { h: [11, -17], st: true }, glow: 1, bob: -0.5, ops: STF(0.12) },
    { m: { h: [-7, -17], st: true }, o: { h: [11.5, -15], st: true }, glow: 1, ops: [arm("o", "over"), arm("m", "over"), sfs("top", [0.35, 0.94], 12, 4, 1.45, 2.4, 3), wrapOp("top", PI - 0.36)] },
    { m: { h: [-7, -17.5], st: true }, o: { h: [11.5, -15], st: true }, glow: 0.6, ops: [arm("o", "over"), arm("m", "over"), sfs("top", [0.33, 0.94], 11, 4, 1.35, 2.4, 2.9), wrapOp("top", PI - 0.34)] },
    { m: { h: [-10.5, -15], st: true }, o: { h: [11.8, -12], st: true }, glow: 0.3, ops: STF(0, -1) },
    { ...IDLE_F, ops: STF(0, -1.9) },
  ],
  back: lean([
    { ...IDLE_B, ops: STB(0, -1.9) },
    { m: { h: [12.5, -21], out: 1 }, o: { h: [-11.5, -15], st: true }, glow: 0.4, bob: -0.3, ops: STB(-0.05) },
    { m: { h: [11.5, -27], out: 1 }, o: { h: [-11, -17], st: true }, glow: 1, bob: -0.5, ops: STB(-0.12) },
    { m: { h: [9.5, -25], out: 1 }, o: { h: [-11.5, -15], st: true }, glow: 1, ops: [sfs("under", [-0.3, -0.95], 15, 3, 0.8, 2.2, 1.6), arm("o", "over"), arm("m", "over")] },
    { m: { h: [9.5, -25.5], out: 1 }, o: { h: [-11.5, -15], st: true }, glow: 0.6, ops: [sfs("under", [-0.28, -0.96], 14, 3, 0.8, 2.2, 1.6), arm("o", "over"), arm("m", "over")] },
    { m: { h: [11, -15], st: true }, o: { h: [-11.8, -12], st: true }, glow: 0.3, ops: STB(0, -1) },
    { ...IDLE_B, ops: STB(0, -1.9) },
  ]),
};

const GD_F = { m: { h: [-4, -16.5] as P2, out: "down" as const }, o: { h: [4.5, -16] as P2, out: "down" as const } };
const GD_B = { m: { h: [2.5, -15] as P2, out: 1 }, o: { h: [-3, -14.5] as P2, out: -1 } };
const oOut = arm("o", "over", { clip: "out" });
const GAUNTLET: Record<FbView, readonly FbFrame[]> = {
  front: [
    { ...GD_F, ops: [arm("o", "over"), arm("m", "over")] },
    { m: { h: [-9.5, -12.5], out: "down" }, o: GD_F.o, bob: -0.2, ops: [arm("m", "over"), arm("o", "over")] },
    { m: { h: [-7, -15], out: "down" }, o: GD_F.o, bob: -0.3, ops: [arm("m", "over"), arm("o", "over")] },
    { m: { h: [-3.5, -16], st: true }, o: { h: [5, -16.5], out: "down" }, ops: [arm("o", "over"), arm("m", "top", { big: 1.4 })] },
    { m: { h: [-1.5, -13.5], st: true }, o: { h: [5, -16.5], out: "down" }, liftR: 1, ops: [arm("o", "over"), arm("m", "top", { big: 2.0 })] },
    { m: { h: [-2, -14], st: true }, o: { h: [5, -16.5], out: "down" }, ops: [arm("o", "over"), arm("m", "top", { big: 1.75 })] },
    { ...GD_F, ops: [arm("o", "over"), arm("m", "over")] },
  ],
  back: lean([
    { ...GD_B, ops: [oOut, arm("m", "over", { clip: "out" })] },
    { m: { h: [9.8, -12], out: 1 }, o: GD_B.o, bob: -0.2, ops: [oOut, arm("m", "over", { big: 1.1 })] },
    { m: { h: [9, -17], out: 1 }, o: GD_B.o, bob: -0.3, ops: [oOut, arm("m", "over")] },
    { m: { h: [9.3, -27], st: true }, o: { h: [-3, -14.5], out: -1 }, ops: [oOut, arm("m", "over")] },
    { m: { h: [8.9, -29], st: true }, o: { h: [-3, -14.5], out: -1 }, liftL: 1, ops: [oOut, arm("m", "over")] },
    { m: { h: [9, -28.5], st: true }, o: { h: [-3, -14.5], out: -1 }, ops: [oOut, arm("m", "over")] },
    { ...GD_B, ops: [oOut, arm("m", "over", { clip: "out" })] },
  ]),
};

// ---------------- QK-5b：借用的兩組 ----------------
/** 火器在持弓手上的方向與縮短：正面指向鏡頭（往下、縮短），背面指向遠處（往上，被身體擋住只露槍口）。 */
const GUN_A: Record<FbView, number> = { front: PI - 0.55, back: -0.45 };
/** QK-5c（美術 PM QK-5 檢查第 4 節第 2 題）：正面（朝南）火器整把放大 1.3 倍（長 0.55×1.3、寬 ×1.3），讓槍身看得出來。 */
export const GUN_FRONT_ZOOM = 1.3;
const GUN_S: Record<FbView, number> = { front: 0.55 * GUN_FRONT_ZOOM, back: 0.8 };
const GUN_W: Record<FbView, number> = { front: GUN_FRONT_ZOOM, back: 1 };
/** 弓那組換成火器：拉弦的手、弓弦拿掉；第 2～3 格持平（同第 1 格舉起的手），命中、收招、回位照放箭格。 */
function gunOf(view: FbView): readonly FbFrame[] {
  const src = BOW[view];
  const L: FbLayer = view === "front" ? "top" : "under";
  const ops = (i: number): FbOp[] => {
    const g = wpn(L, GUN_A[view], { on: "o", s: i === 0 || i === 6 ? GUN_S[view] * 0.8 : GUN_S[view], wd: GUN_W[view] });
    return view === "front" ? [arm("o", "top"), g, arm("m", i === 6 ? "over" : "top")] : [g, arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })];
  };
  return src.map((f, i) => {
    const hold = i === 2 || i === 3 ? src[1]! : f;
    return { ...f, m: hold.m, o: hold.o, ops: ops(i) };
  });
}
const GUN: Record<FbView, readonly FbFrame[]> = { front: gunOf("front"), back: gunOf("back") };

/** 法杖那組換成手上的武器：杖頭往前（staffFS）那兩格改畫主手武器（同方向、縮短 0.55），其他格照法杖（武器用 w 畫）。 */
function castOf(view: FbView): readonly FbFrame[] {
  return STAFF[view].map((f) => ({
    ...f,
    ops: f.ops.map((o): FbOp => (o.t === "staffFS" ? wpn(o.L, Math.atan2(o.d[0], -o.d[1]), { s: 0.55 }) : o)),
  }));
}
const CAST: Record<FbView, readonly FbFrame[]> = { front: castOf("front"), back: castOf("back") };

export const FB_CLIPS: Readonly<Record<FbKind, Record<FbView, readonly FbFrame[]>>> = { sword: SWORD, spear: SPEAR, bow: BOW, staff: STAFF, gauntlet: GAUNTLET, gun: GUN, cast: CAST };

// ---------------- 插值 ----------------
const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;
const lerpP = (a: P2, b: P2, t: number): P2 => [lerp(a[0], b[0], t), lerp(a[1], b[1], t)];
/** 角度走最短的一邊。 */
const lerpA = (a: number, b: number, t: number): number => {
  let d = (b - a) % TAU;
  if (d > Math.PI) d -= TAU;
  if (d < -Math.PI) d += TAU;
  return a + d * t;
};
const sig = (ops: readonly FbOp[]): string => ops.map((o) => `${o.t}:${o.L}:${"who" in o ? o.who : ""}:${"clip" in o ? (o.clip ?? "") : ""}:${o.t === "spear" ? (o.d ? "d" : "") + (o.hand ? "h" : "") : ""}:${o.t === "bow" ? (o.F ? "F" : "") + (o.torso ? "t" : "") : ""}:${o.t === "wrap" ? String(o.a === "spA") : ""}:${o.t === "w" ? (o.on ?? "") : ""}`).join("|");

function lerpOp(a: FbOp, b: FbOp, t: number): FbOp {
  const out: Record<string, unknown> = { ...(t < 0.5 ? a : b) };
  const A = a as unknown as Record<string, unknown>;
  const B = b as unknown as Record<string, unknown>;
  for (const k of Object.keys(A)) {
    const x = A[k];
    const y = B[k];
    if (typeof x === "number" && typeof y === "number") out[k] = k === "a" ? lerpA(x, y, t) : lerp(x, y, t);
    else if (Array.isArray(x) && Array.isArray(y) && x.length === 2) out[k] = lerpP(x as P2, y as P2, t);
  }
  // 只有一邊有的數值（縮短 s、寬 wd、mg）：沒給＝1（s、wd）或 0（mg）
  for (const k of ["s", "wd", "mg", "big"] as const) {
    const x = A[k];
    const y = B[k];
    if (typeof x === "number" || typeof y === "number") {
      const d = k === "mg" || k === "big" ? (k === "big" ? 1 : 0) : 1;
      out[k] = lerp(typeof x === "number" ? x : d, typeof y === "number" ? y : d, t);
    }
  }
  return out as unknown as FbOp;
}

function lerpHand(a: Hand, b: Hand, t: number): Hand {
  const n = t < 0.5 ? a : b;
  const st = !!a.st === !!b.st ? !!a.st : !!n.st;
  return { h: lerpP(a.h, b.h, t), ...(st ? { st: true } : {}), ...(n.out === undefined ? {} : { out: n.out }), ...(a.f !== undefined || b.f !== undefined ? { f: lerp(a.f ?? 1, b.f ?? 1, t) } : {}) };
}

/** 這一類這一面在 `fbt`（0～6）的一格（相鄰兩幀內插）。 */
export function fbFrameAt(kind: FbKind, view: FbView, fbt: number): FbFrame {
  const fr = FB_CLIPS[kind][view];
  const u = Math.max(0, Math.min(FB_FRAMES - 1, Number.isFinite(fbt) ? fbt : 0));
  const i = Math.min(FB_FRAMES - 2, Math.floor(u));
  const t = u - i;
  const A = fr[i]!;
  const B = fr[i + 1]!;
  if (t <= 1e-6) return A;
  if (t >= 1 - 1e-6) return B;
  const same = sig(A.ops) === sig(B.ops);
  const ops = same ? A.ops.map((o, k) => lerpOp(o, B.ops[k]!, t)) : t < 0.5 ? A.ops : B.ops;
  const num = (k: "bob" | "liftL" | "liftR" | "glow" | "lean"): number => lerp(A[k] ?? 0, B[k] ?? 0, t);
  return { m: lerpHand(A.m, B.m, t), o: lerpHand(A.o, B.o, t), bob: num("bob"), liftL: num("liftL"), liftR: num("liftR"), glow: num("glow"), lean: num("lean"), ops };
}

// ---------------- 解手臂與畫 ----------------
export interface FbArmSol {
  sx: number;
  sA: number;
  eA: number;
  len: readonly number[] | null;
  hand: P2;
}
/** 樣張 solve：打直（st）＝往鏡頭或往遠處時照距離縮短（不拉長）；否則 IK。 */
export function fbSolve(sx: number, s: Hand): FbArmSol {
  const UA = 5;
  const FA = 5.5;
  if (s.st) {
    const dx = s.h[0] - sx;
    const dy = s.h[1] + 20;
    const d = Math.hypot(dx, dy);
    const f = Math.min(1, d / (UA + FA));
    const len = [UA * f, FA * f];
    const sA = Math.atan2(-dx, dy);
    return { sx, sA, eA: 0, len, hand: fk(sx, sA, 0, len) };
  }
  const len = s.f ? [UA * s.f, FA * s.f] : null;
  const r = ik(sx, s.h, s.out ?? Math.sign(sx), len);
  return { sx, sA: r.sA, eA: r.eA, len, hand: fk(sx, r.sA, r.eA, len) };
}
export const fbHands = (fr: FbFrame, view: FbView): { m: FbArmSol; o: FbArmSol } => {
  const ms = view === "front" ? -8.5 : 8.5;
  return { m: fbSolve(ms, fr.m), o: fbSolve(-ms, fr.o) };
};

/** qDoll 給的畫圖工具（樣張 fbApiOf）。 */
export interface FbApi {
  ctx: Ctx;
  view: FbView;
  main: QItem | undefined;
  /** 畫一隻手臂（第 17 版：彎肘兩段描邊、打直一圈）。 */
  arm: (A: FbArmSol) => void;
  /** 主手武器：a＝世界角度，M＝自訂 2×2（縮短、往鏡頭）。 */
  weapon: (hand: P2, a: number, M: readonly number[] | null, mg: number) => void;
  wrap: (hand: P2, a: number) => void;
  bow: (hand: P2, U: P2, F: P2, pull: number, nock: boolean) => void;
  /** 副手物品（盾、書、法球…）畫在副手上；沒有就不畫。 */
  offItem: (hand: P2, layer: FbLayer) => void;
  colors: (it: QItem | undefined) => readonly [string, string];
}

const SHAFT = "#6a4420";
const COLLAR = "#8a6a2a";
const TORSO = [-7.5, -21, 15, 13.5] as const;
const norm = (p: readonly number[]): P2 => {
  const l = Math.hypot(p[0] ?? 0, p[1] ?? 0) || 1;
  return [(p[0] ?? 0) / l, (p[1] ?? 0) / l];
};
const Mof = (a: number, s = 1, wd = 1): number[] | null => (s === 1 && wd === 1 ? null : [Math.cos(a) * wd, Math.sin(a) * wd, -Math.sin(a) * s, Math.cos(a) * s]);

function pole(c: Ctx, R: P2, d: P2, Lf: number, Lb: number, w0: number, w1: number): P2 {
  const n: P2 = [-d[1], d[0]];
  const B: P2 = [R[0] - d[0] * Lb, R[1] - d[1] * Lb];
  const T: P2 = [R[0] + d[0] * Lf, R[1] + d[1] * Lf];
  c.beginPath();
  c.moveTo(B[0] + (n[0] * w0) / 2, B[1] + (n[1] * w0) / 2);
  c.lineTo(T[0] + (n[0] * w1) / 2, T[1] + (n[1] * w1) / 2);
  c.lineTo(T[0] - (n[0] * w1) / 2, T[1] - (n[1] * w1) / 2);
  c.lineTo(B[0] - (n[0] * w0) / 2, B[1] - (n[1] * w0) / 2);
  c.closePath();
  c.fillStyle = SHAFT;
  c.fill();
  return T;
}
function spearHead(c: Ctx, T: P2, d: P2, hl: number, hw: number, steel: string): P2 {
  const n: P2 = [-d[1], d[0]];
  const P: P2 = [T[0] + d[0] * hl, T[1] + d[1] * hl];
  c.fillStyle = steel;
  c.beginPath();
  c.moveTo(P[0], P[1]);
  c.lineTo(T[0] + (n[0] * hw) / 2, T[1] + (n[1] * hw) / 2);
  c.lineTo(T[0] - (n[0] * hw) / 2, T[1] - (n[1] * hw) / 2);
  c.closePath();
  c.fill();
  c.fillStyle = "rgba(255,255,255,0.45)";
  c.beginPath();
  c.moveTo(P[0], P[1]);
  c.lineTo(T[0] + n[0] * hw * 0.12, T[1] + n[1] * hw * 0.12);
  c.lineTo(T[0] + n[0] * hw * 0.3, T[1] + n[1] * hw * 0.3);
  c.closePath();
  c.fill();
  c.fillStyle = COLLAR;
  const cw = hw * 0.62;
  c.beginPath();
  c.moveTo(T[0] + (n[0] * cw) / 2, T[1] + (n[1] * cw) / 2);
  c.lineTo(T[0] - (n[0] * cw) / 2, T[1] - (n[1] * cw) / 2);
  c.lineTo(T[0] - (n[0] * cw) / 2 - d[0] * 1.3, T[1] - (n[1] * cw) / 2 - d[1] * 1.3);
  c.lineTo(T[0] + (n[0] * cw) / 2 - d[0] * 1.3, T[1] + (n[1] * cw) / 2 - d[1] * 1.3);
  c.closePath();
  c.fill();
  return P;
}
function staffHead(c: Ctx, P: P2, sc: number, g: number, orb: string): void {
  c.save();
  c.globalAlpha = 0.35 + 0.35 * g;
  c.fillStyle = orb;
  c.beginPath();
  c.arc(P[0], P[1], 5.2 * sc, 0, TAU);
  c.fill();
  c.restore();
  c.fillStyle = orb;
  c.beginPath();
  c.arc(P[0], P[1], 3.6 * sc, 0, TAU);
  c.fill();
  c.fillStyle = "rgba(255,255,255,0.8)";
  c.beginPath();
  c.arc(P[0] - 1.2 * sc, P[1] - 1.2 * sc, 1.1 * sc, 0, TAU);
  c.fill();
}
const spA = (H: { m: FbArmSol; o: FbArmSol }): number => Math.atan2(H.o.hand[0] - H.m.hand[0], -(H.o.hand[1] - H.m.hand[1]));

/** 這一格的作用端（槍尖、杖頭、劍尖、拳頭；角色座標，bob 前），特效起點用。 */
export function fbTip(kind: FbKind, view: FbView, fr: FbFrame, main: QItem | undefined): P2 {
  const H = fbHands(fr, view);
  if (kind === "bow") return view === "front" ? [5, -12] : [-4, -36]; // 樣張 proj 的 from（背面從頭頂上方飛出）
  if (kind === "gauntlet") return H.m.hand;
  for (const op of fr.ops) {
    if (op.t === "spear" && !op.hand) {
      const R = H.m.hand;
      const d = op.d ? norm(op.d) : norm([H.o.hand[0] - R[0], H.o.hand[1] - R[1]]);
      return [R[0] + d[0] * (op.Lf + op.hl), R[1] + d[1] * (op.Lf + op.hl)];
    }
    if (op.t === "staffFS") {
      const d = norm(op.d);
      return [H.m.hand[0] + d[0] * op.Lf, H.m.hand[1] + d[1] * op.Lf];
    }
  }
  const w = fr.ops.find((o): o is OpW => o.t === "w" && o.clip !== "hand");
  const q = qWeapon(main);
  // 法球（沒有主手武器）的施放：從副手（法球）放出
  if (kind === "cast" && !q) return H.o.hand;
  const len = q?.W.len ?? (kind === "staff" ? 32 : 14);
  if (w === undefined) return H.m.hand;
  const h = w.on === "o" ? H.o.hand : H.m.hand;
  const s = (w.s ?? 1) * len - (w.mg ?? 0);
  return [h[0] + Math.sin(w.a) * s, h[1] - Math.cos(w.a) * s];
}

/** 一層：照 ops 依序畫（qDoll.drawBody 在 under、over、top 三個位置呼叫）。 */
export function drawFbLayer(api: FbApi, fr: FbFrame, layer: FbLayer): void {
  const c = api.ctx;
  const H = fbHands(fr, api.view);
  const steel = api.colors(api.main && api.main.kind === "spear" ? api.main : { slot: "main_hand", kind: "spear", material: "steel" })[0];
  // 副手物品：主手武器沒用到副手時（劍、杖、拳），照副手的位置畫（盾、書）；背面在身體之前、正面在副手臂之後
  const offFree = !fr.ops.some((o) => o.t === "bow" || o.t === "spear" || (o.t === "wrap" && o.on === "o") || (o.t === "w" && o.on === "o"));
  if (offFree && layer === "under" && api.view === "back") api.offItem(H.o.hand, "under");
  for (const op of fr.ops) {
    if (op.L !== layer) continue;
    c.save();
    if ("clip" in op && op.clip === "out") {
      c.beginPath();
      c.rect(-80, -120, 160, 200);
      c.rect(TORSO[0], TORSO[1], TORSO[2], TORSO[3]);
      c.clip("evenodd");
    }
    if (op.t === "w" && op.clip === "hand") {
      const h = H.m.hand;
      c.beginPath();
      c.arc(h[0], h[1], 2.6, 0, TAU);
      c.clip();
    }
    switch (op.t) {
      case "arm": {
        const R = H[op.who];
        api.arm(R);
        if (op.big !== undefined && op.big > 1) {
          // 往鏡頭的拳頭：在手的位置放大重畫一次（只畫拳頭那一圈）
          const [x, y] = R.hand;
          c.save();
          c.beginPath();
          c.arc(x, y, 3.2 * op.big, 0, TAU);
          c.clip();
          c.translate(x, y);
          c.scale(op.big, op.big);
          c.translate(-x, -y);
          api.arm(R);
          c.restore();
        }
        if (op.who === "o" && offFree && api.view === "front") api.offItem(R.hand, layer);
        break;
      }
      case "w": {
        const h = H[op.on ?? "m"].hand;
        api.weapon(h, op.a, Mof(op.a, op.s ?? 1, op.wd ?? 1), op.mg ?? 0);
        if (op.wrap) api.wrap(h, op.a);
        break;
      }
      case "wrap":
        api.wrap(H[op.on].hand, op.a === "spA" ? spA(H) : op.a);
        break;
      case "spear": {
        const R = H.m.hand;
        const d = op.d ? norm(op.d) : norm([H.o.hand[0] - R[0], H.o.hand[1] - R[1]]);
        if (op.hand) {
          c.beginPath();
          c.arc(R[0], R[1], 2.6, 0, TAU);
          c.clip();
          pole(c, R, d, op.Lf, op.Lb, op.w0, op.w1);
        } else spearHead(c, pole(c, R, d, op.Lf, op.Lb, op.w0, op.w1), d, op.hl, op.hw, steel);
        break;
      }
      case "staffFS": {
        const T = pole(c, H.m.hand, norm(op.d), op.Lf, op.Lb, op.w0, op.w1);
        staffHead(c, T, op.sc, 1, staffOrbColor(api.main));
        break;
      }
      case "bow": {
        const G = H.o.hand;
        const N = H.m.hand;
        const k = BOW_EY + op.pull;
        const F: P2 = op.F ?? [(G[0] - N[0]) / k, (G[1] - N[1]) / k];
        if (op.torso) {
          c.beginPath();
          c.rect(TORSO[0], TORSO[1], TORSO[2], TORSO[3]);
          c.clip();
        }
        api.bow(G, op.U, F, op.pull, op.nock);
        break;
      }
    }
    c.restore();
  }
}

// ---------------- 接到戰場的技能片段 ----------------
/**
 * 武器種類（起手對照表的列）＋施放方式 → 正面、背面用哪一類（其他組合照舊的正面、背面畫法）。
 * QK-5b（美術 PM QK-5 檢查第 2 題）：成對、鐮、鞭近戰借劍那組（主手揮；鞭的遠程片段同近戰，一起借）；
 * 弩、火槍遠程借弓那組（`gun`，不拉弦）；法球遠程、自身與地面施放借法杖那組（拿法杖的直接用法杖，其他 `cast`）。
 * QK-5c（美術 PM QK-5 檢查第 4 節第 1 題）：弓、弩、火槍的自身與地面施放不借法杖（舉弓像射天空），照舊上下位移＝null。
 */
const NO_CAST: ReadonlySet<string> = new Set(["bow", "crossbow", "gun"]);
export function fbKindFor(weapon: string, mode: string): FbKind | null {
  if (mode === "self" || mode === "ground") {
    if (NO_CAST.has(weapon)) return null;
    return weapon === "staff" ? "staff" : "cast";
  }
  if (mode === "melee") {
    if (weapon === "blade" || weapon === "arcane" || weapon === "pair" || weapon === "scythe" || weapon === "whip") return "sword";
    if (weapon === "spear") return "spear";
    if (weapon === "fist" || weapon === "bare") return "gauntlet";
    return null;
  }
  if (mode === "ranged") {
    if (weapon === "bow") return "bow";
    if (weapon === "crossbow" || weapon === "gun") return "gun";
    if (weapon === "staff") return "staff";
    if (weapon === "orb") return "cast";
    if (weapon === "whip") return "sword";
  }
  return null;
}

/** 技能時間軸的一列在正面、背面怎麼播：蓄力（幀 0→2）、出招（2→4 命中／出手→6）、收勢（停在 6，過半回站好）。 */
export interface FbPart {
  /** null＝這一組武器、施放方式沒有正面背面五類（只用 part 給側面的 Q 版關鍵姿勢 atk、bowAim）。 */
  kind: FbKind | null;
  part: "windup" | "strike" | "recover";
  /** 出招片段的命中點（0～1）。 */
  hitAt?: number;
}

/** 這一列在片段時間 t（0～1）的關鍵幀時間；收勢過半回 null（站好）。片段時間先量化成 16 格（同 skillClips.CLIP_STEPS）。 */
export function fbTimeOf(p: FbPart, t: number): number | null {
  const q = Math.round(Math.max(0, Math.min(1, t)) * 16) / 16;
  let u: number;
  if (p.part === "windup") u = 2 * q;
  else if (p.part === "recover") return q < 0.5 ? 6 : null;
  else {
    const h = Math.max(0.05, Math.min(0.95, p.hitAt ?? 0.5));
    u = q <= h ? 2 + (2 * q) / h : 4 + (2 * (q - h)) / (1 - h);
  }
  return Math.round(u * 100) / 100;
}

// ---------------- 側面：出招接 Q 版關鍵姿勢（atk、bowAim） ----------------
export type KeyAttackPose = Partial<Record<"bob" | "lean" | "hipN" | "hipF" | "kneeN" | "kneeF" | "atk" | "bowAim" | "pull", number>>;
const ATK_KINDS: ReadonlySet<string> = new Set(["greatsword", "spear", "scythe", "crossbow", "longgun", "pistol", "shotgun"]);
const AIM_FIRST: ReadonlySet<string> = new Set(["crossbow", "longgun", "pistol", "shotgun"]);
/**
 * 側面的雙手劍、長柄（槍、鐮）、弩、火槍：蓄力把 atk 推到「提起／舉起」（雙手劍 0.5＝舉到臉前上方；槍鐮 0.35；弩槍瞄準 1），
 * 出招到命中推到 1（劈下、刺出），之後停在 1，收勢過半回站好。弓：蓄力 bowAim 0→1、拉弦 0→4；命中（放箭）那一刻放開。
 * 姿勢的手臂、武器角度改由關鍵姿勢決定（拿掉片段的 arm、elbow、wpn），身體的前傾、跨步、起伏照片段。主手不是這幾種＝null。
 */
export function qKeyAttackPose(mainKind: string | undefined, p: FbPart, t: number, base: Readonly<Partial<Record<"bob" | "lean" | "hipN" | "hipF" | "kneeN" | "kneeF", number>>>): KeyAttackPose | null {
  if (mainKind === undefined) return null;
  const bow = mainKind === "bow";
  if (!bow && !ATK_KINDS.has(mainKind)) return null;
  const q = Math.round(Math.max(0, Math.min(1, t)) * 16) / 16;
  const body: KeyAttackPose = {};
  for (const k of ["bob", "lean", "hipN", "hipF", "kneeN", "kneeF"] as const) if (typeof base[k] === "number") body[k] = base[k];
  const h = Math.max(0.05, Math.min(0.95, p.hitAt ?? 0.5));
  if (bow) {
    if (p.part === "windup") return { ...body, bowAim: q, pull: 4 * q };
    if (p.part === "strike") return { ...body, bowAim: 1, pull: q < h ? 4 : 0 };
    return q < 0.5 ? { ...body, bowAim: 1, pull: 0 } : null;
  }
  const up = mainKind === "greatsword" ? 0.5 : AIM_FIRST.has(mainKind) ? 1 : 0.35;
  if (p.part === "windup") return { ...body, atk: up * q };
  if (p.part === "strike") return { ...body, atk: q < h ? up + ((1 - up) * q) / h : 1 };
  return q < 0.5 ? { ...body, atk: 1 } : null;
}
