// 攻擊變體（Phase 6N-6 近戰；需求 docs/art/動畫移植需求第二批.md 第 0 節第 3 點、第 6 節，方案 docs/art/動畫方案.md 2.10）。
// 同一種武器的普攻有幾種樣子，播放時照確定性雜湊挑一種。變體只改關節角度與弧光方向：
// 同一種武器的所有變體，蓄力片段一樣長、出招片段一樣長、命中點 `hitAt` 一樣（測試鎖住），所以串接器排出來的時間軸完全相同。
// 全部是資料＋純函式：不用 Math.random()、不讀時鐘；挑法用 `inkStyle.seedOf`（FNV-1a）。
// 6N-7：加上遠程（弓、弩、火槍：只換拉弓、上弩、舉槍的姿勢與後座，飛行物、落點、時間不變；沒有弧光）與拳套空手；
// 受擊、閃避的變體在 reactClips.ts（同一套挑法 `variantHash`）。挑法在 `seedOf` 之後多一道 murmur3 fmix32（只在挑變體時用）。
// 角度、座標照 skillClips.ts：側面朝東，`arm` 負＝往前上抬；武器絕對角度 ＝ arm ＋ elbow ＋ wpn（0 作用端朝上、π/2 朝前）。
import type { GearItem } from "./appearance";
import type { InkPose } from "./inkPose";
import { seedOf } from "./inkStyle";
import type { ClipDef, ClipId, FxCue } from "./skillClips";

// ---- 武器（變體表的列） ---------------------------------------------------------

/** 變體表的列（方案 2.10 第 5 點）。6N-6：近戰 8 列；6N-7：拳套空手、弓、弩、火槍。 */
export type AttackFamily = "sword" | "saber" | "arcane" | "heavy" | "pair" | "spear" | "scythe" | "whip" | "fist" | "bow" | "crossbow" | "gun";
export const ATTACK_FAMILIES: readonly AttackFamily[] = ["sword", "saber", "arcane", "heavy", "pair", "spear", "scythe", "whip", "fist", "bow", "crossbow", "gun"];
/** 遠程的列：只有遠程普攻（距離 > 1）挑變體；其餘的列只有近身普攻挑。 */
export const RANGED_FAMILIES: readonly AttackFamily[] = ["bow", "crossbow", "gun"];
/** 這一列在這種施放方式下挑不挑變體（弓在近身時照舊「用弓身敲」、拳套的遠程照舊「拳風」，都不挑）。 */
export function familyApplies(family: AttackFamily, mode: "melee" | "ranged" | "self" | "ground"): boolean {
  return RANGED_FAMILIES.includes(family) ? mode === "ranged" : mode === "melee";
}

/** 表上的名稱。 */
export const FAMILY_ZH: Readonly<Record<AttackFamily, string>> = {
  sword: "劍",
  saber: "刀",
  arcane: "魔導劍",
  heavy: "斧、錘、雙手武器",
  pair: "成對武器",
  spear: "槍（長兵）",
  scythe: "鐮",
  whip: "鞭",
  fist: "拳套、空手",
  bow: "弓",
  crossbow: "弩",
  gun: "火槍",
};

/** 方案 2.10 第 5 點的變體數（測試鎖住）。 */
export const VARIANT_COUNT: Readonly<Record<AttackFamily, number>> = { sword: 5, saber: 5, arcane: 4, heavy: 3, pair: 4, spear: 4, scythe: 3, whip: 3, fist: 5, bow: 4, crossbow: 3, gun: 3 };

/** 起手對照表上有的主手 kind（skillClips 的 `KIND_CLASS`）；不在這裡的（符紙、拂塵、傀儡線）＝ 空手。 */
const KNOWN_KINDS: ReadonlySet<string> = new Set(["sword", "greatsword", "dagger", "axe", "hammer", "spear", "scythe", "whip", "fist", "staff", "bow", "crossbow", "longgun", "pistol", "shotgun"]);

/**
 * 紙娃娃主手、副手 → 變體表的列；法杖、法球回傳 `null`（照起手對照表、不挑變體；施法的變體是 6N-8 的技能變體）。
 * - 魔導劍 ＝ 劍＋`arcane` 形制；刀 ＝ 彎刀（劍的 `curved` 形制）與彎匕（匕首的 `kris` 形制）；
 * - 成對 ＝ 主副手同種的劍、匕首；斧、錘、大劍（含斬馬刀）＝ 斧錘雙手；其餘劍、匕首 ＝ 劍；
 * - 6N-7：拳套與空手（沒有主手、或主手是表上沒有的符紙、拂塵、傀儡線，且副手不是法球）＝ 拳套空手；
 *   弓 ＝ 弓；弩 ＝ 弩；長槍、手槍、霰彈槍 ＝ 火槍。
 */
export function attackFamilyOf(main: GearItem | undefined, off: GearItem | undefined): AttackFamily | null {
  if (main === undefined || !KNOWN_KINDS.has(main.kind)) return off?.kind === "orb" ? null : "fist";
  const k = main.kind;
  if (k === "fist" || k === "bow" || k === "crossbow") return k;
  if (k === "longgun" || k === "pistol" || k === "shotgun") return "gun";
  if (k === "sword" && main.form === "arcane") return "arcane";
  if ((k === "sword" || k === "dagger") && off !== undefined && off.kind === k) return "pair";
  if (k === "sword") return main.form === "curved" ? "saber" : "sword";
  if (k === "dagger") return main.form === "kris" ? "saber" : "sword";
  if (k === "axe" || k === "hammer" || k === "greatsword") return "heavy";
  if (k === "spear" || k === "scythe" || k === "whip") return k;
  return null;
}

// ---- 弧光 -----------------------------------------------------------------------

/**
 * 弧光的形狀（在目標身上；本地座標：朝東、x ＝ 往前、y ＝ 往下，單位 ＝ 半徑；朝西時左右鏡像）：
 * - `arc`：從角度 `from` 掃過 `sweep`（弧度，0 ＝ 往前、−π/2 ＝ 上方；正＝順時針）；`squash` 把弧壓扁（橫掃）；
 * - `line`：一道直線（突刺），方向 `angle`；
 * - `cross`：兩道交叉的直線（交叉斬），方向 `angle` 與 `angle2`；
 * - `ring`：一整圈（迴旋），從 `from` 掃 `sweep`（±2π），`squash` 壓扁。
 */
export type ArcSpec =
  | { kind: "arc"; from: number; sweep: number; squash?: number }
  | { kind: "line"; angle: number }
  | { kind: "cross"; angle: number; angle2: number }
  | { kind: "ring"; from: number; sweep: number; squash: number };

const PI = Math.PI;
/** 由上往下（6N-5 以前唯一的弧光）。 */
export const ARC_DOWN: ArcSpec = { kind: "arc", from: -0.45 * PI, sweep: 0.9 * PI };
const ARC_UP: ArcSpec = { kind: "arc", from: 0.45 * PI, sweep: -0.9 * PI };
const ARC_ACROSS: ArcSpec = { kind: "arc", from: 0.95 * PI, sweep: -0.9 * PI, squash: 0.42 };
const ARC_RING: ArcSpec = { kind: "ring", from: 0.5 * PI, sweep: -2 * PI, squash: 0.5 };
const line = (angle: number): ArcSpec => ({ kind: "line", angle });

/** 弧光取樣的點數（一道弧）。 */
export const ARC_SAMPLES = 18;

type P2 = readonly [number, number];

/** 弧光的每一道筆畫（本地座標的點列，依揮的先後排；`grow` 0～1 ＝ 畫到哪裡）。 */
export function arcStrokes(spec: ArcSpec, grow = 1): P2[][] {
  const g = Math.max(0, Math.min(1, grow));
  switch (spec.kind) {
    case "arc":
    case "ring": {
      const sq = spec.squash ?? 1;
      const n = Math.max(2, Math.round(ARC_SAMPLES * (spec.kind === "ring" ? 2 : 1) * g));
      const pts: P2[] = [];
      for (let i = 0; i <= n; i++) {
        const a = spec.from + spec.sweep * g * (i / n);
        pts.push([Math.cos(a), Math.sin(a) * sq + (sq < 1 ? (1 - sq) * 0.6 : 0)]);
      }
      return [pts];
    }
    case "line":
      return [lineStroke(spec.angle, g)];
    case "cross":
      // 兩道各佔一半時間：先畫第一道，再畫第二道
      return [lineStroke(spec.angle, Math.min(1, g * 2)), ...(g > 0.5 ? [lineStroke(spec.angle2, (g - 0.5) * 2)] : [])];
  }
}

function lineStroke(angle: number, g: number): P2[] {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  const t0 = -1.1;
  const t1 = t0 + 2.2 * g;
  return [
    [c * t0, s * t0],
    [c * t1, s * t1],
  ];
}

/** 弧光從頭到尾的方向（本地座標；`ring` 為 0）：測試「弧光方向和揮的方向一致」用。 */
export function arcTravel(spec: ArcSpec): { dx: number; dy: number } {
  if (spec.kind === "ring") return { dx: 0, dy: 0 };
  let dx = 0;
  let dy = 0;
  for (const s of arcStrokes(spec, 1)) {
    const a = s[0]!;
    const b = s[s.length - 1]!;
    dx += b[0] - a[0];
    dy += b[1] - a[1];
  }
  return { dx, dy };
}

// ---- 變體 -----------------------------------------------------------------------

/** 揮的方向（樣張的分法）：由上往下、由下往上、橫掃（由後往前）、突刺（往前）、迴旋（轉一圈）。 */
export type Swing = "down" | "up" | "across" | "thrust" | "spin" | "shoot";

export interface AttackVariant {
  id: string;
  /** 表上的例子名稱。 */
  zh: string;
  /** 蓄力片段（`VARIANT_CLIPS` 或 `OPENER_CLIPS` 的 ID）；同一列的變體一樣長。 */
  windup: ClipId;
  /** 出招片段（有 `hitAt`）；同一列的變體一樣長、`hitAt` 一樣。 */
  strike: ClipId;
  swing: Swing;
  /** 弧光；遠程沒有（`null`，照舊只畫飛行物）。 */
  arc: ArcSpec | null;
}

const REST: InkPose = { arm: 0, wpn: 0.75 };
const fx = (kind: FxCue["kind"], where: FxCue["where"], from = 0, to = 1): FxCue => ({ kind, where, from, to });
const STANCE = { hipN: 0.45, hipF: -0.3 } as const;

// 蓄力姿勢（出招的第一格 ＝ 蓄力的最後一格）
const LO: InkPose = { arm: 0.9, wpn: -3.3, lean: -0.1, hipN: 0.25, hipF: -0.2, bob: 1.5 };
const SIDE: InkPose = { arm: -1.2, wpn: -0.4, lean: -0.12, hipN: 0.2 };
const THRUST_BACK: InkPose = { arm: 0.4, elbow: -1.2, wpn: 2.4, lean: -0.08, hipN: 0.2 };
const HOP_IN: InkPose = { arm: -2.7, wpn: 1.6, lean: -0.05, kneeN: 0.7, kneeF: 0.7, bob: 2.5 };
const DRAW_IN: InkPose = { arm: 0.6, elbow: -0.9, wpn: -2.2, lean: 0.1, kneeN: 0.5, kneeF: 0.3, bob: 1.5 };
const TWIST: InkPose = { arm: -1.0, wpn: -0.4, lean: -0.2, hipN: -0.2, hipF: 0.3 };
const RUNE_UP: InkPose = { arm: -2.9, wpn: 2.9, lean: -0.06, bob: -0.6 };
const CLEAVE_IN: InkPose = { arm: -2.9, elbow: -0.2, wpn: 2.4, armF: -2.6, lean: -0.18, hipN: 0.3, hipF: -0.25, bob: -0.5 };
const HEAVY_SIDE: InkPose = { arm: -1.0, wpn: -0.5, armF: -1.0, lean: -0.2, hipN: -0.1, hipF: 0.25 };
const WHIRL_IN: InkPose = { arm: -0.2, wpn: -1.8, armF: -0.2, lean: -0.15, kneeN: 0.4, bob: 1 };
const STAB_IN: InkPose = { arm: 0.4, elbow: -1.3, wpn: 2.4, armF: 0.3, elbowF: -1.3, lean: -0.08 };
const PAIR_TWIST: InkPose = { arm: -0.9, wpn: -0.5, armF: -0.6, lean: -0.2, hipN: -0.2, hipF: 0.3 };
const BACKHAND_IN: InkPose = { arm: -2.6, elbow: -0.4, wpn: 6.0, armF: -1.2, lean: -0.1 };
const LOW_IN: InkPose = { arm: 0.6, wpn: 1.3, lean: 0.05, kneeN: 0.6, kneeF: 0.5, bob: 2 };
const SPEAR_SIDE: InkPose = { arm: -1.3, wpn: -0.3, lean: -0.15, hipN: 0.2 };
const LEAP_IN: InkPose = { arm: -2.2, wpn: 3.0, lean: -0.05, kneeN: 0.8, kneeF: 0.8, bob: 2.5 };
const SCY_LIFT_IN: InkPose = { arm: 0.6, wpn: -2.8, lean: -0.1, kneeN: 0.4, bob: 1.2 };
const WHIP_UP_IN: InkPose = { arm: 0.5, wpn: -2.4, lean: -0.1, kneeN: 0.3, bob: 1 };
const WHIP_IN: InkPose = { arm: -2.6, wpn: 0.4, lean: -0.15 };
const WRAP_IN: InkPose = { arm: -2.0, wpn: -0.6, lean: -0.1 };

const wind = (ms: number, to: InkPose, extra: Partial<ClipDef> = {}): ClipDef => ({ ms, anchor: "tip", keys: [[0, REST], [1, to]], ...extra });

// 6N-7 拳套、空手的蓄力姿勢
const HOOK_IN: InkPose = { arm: 0.1, elbow: -1.9, lean: -0.15, hipN: -0.15, hipF: 0.25 };
const UPPER_IN: InkPose = { arm: 0.7, elbow: -1.5, lean: 0.08, kneeN: 0.5, kneeF: 0.4, bob: 2.2 };
const KNEE_IN: InkPose = { arm: -0.7, elbow: -1.5, armF: -0.7, elbowF: -1.5, lean: -0.05 };
const KICK_IN: InkPose = { arm: -0.6, elbow: -1.4, armF: 0.3, lean: -0.25, hipN: -0.2, hipF: 0.3 };

// 6N-7 遠程：起手對照表的瞄準姿勢（skillClips 的 AIM；這裡另寫一份，因為 skillClips 匯入本檔，初始化時還拿不到它的常數）
const AIM: InkPose = { arm: -1.3, wpn: 2.87, lean: -0.05 };
/** 半蹲射：膝蓋彎、身體往下沉。 */
const BOW_CROUCH: InkPose = { kneeN: 0.9, kneeF: 0.7, hipN: 0.45, hipF: 0.1, bob: 4, lean: 0.06 };
/** 側身射：上半身往後仰、轉開。 */
const BOW_SIDE: InkPose = { lean: -0.14, hipN: -0.25, hipF: 0.35, arm: 0.05 };
/** 拋射：弓往上抬約 45 度（武器絕對角度 ≈ π/4）。 */
const BOW_LOB: InkPose = { arm: -0.6, wpn: -0.2, lean: -0.15 };
/** 腰射：手放低、手肘彎，槍身仍水平（arm＋elbow＋wpn 不變）。 */
const GUN_HIP: InkPose = { arm: 0.8, elbow: -0.85, wpn: 0.05, lean: 0.05 };
/** 單膝射：前腳跪下。 */
const GUN_KNEEL: InkPose = { kneeN: 1.6, hipN: 1.0, kneeF: 0.4, bob: 5, lean: 0.05 };

/** 姿勢逐欄相加（遠程變體 ＝ 原本的瞄準、放箭姿勢 ＋ 一組差值，後座的形狀跟著原本的）。 */
function plus(p: InkPose, d: InkPose): InkPose {
  const out: InkPose = { ...p };
  for (const [k, v] of Object.entries(d) as Array<[keyof InkPose, number]>) out[k] = (p[k] ?? 0) + v;
  return out;
}

/**
 * 遠程變體的蓄力＋出招：照起手對照表的弓（aim／release）或弩、火槍（aim_gun／fire）的關鍵點，每個姿勢加上 `delta`
 * （開頭的站好不加），後座那一格（0.15）再加 `kick`。長度、`hitAt`、特效（火槍的槍口火光）都和原本的一樣。
 */
function rangedPair<N extends string>(name: N, base: "bow" | "gun", delta: InkPose, kick: InkPose): Record<N | `${N}_in`, ClipDef> {
  const a = plus(AIM, delta);
  const windup: ClipDef =
    base === "bow"
      ? { ms: 360, anchor: "tip", keys: [[0, REST], [0.6, a], [1, { ...a, pull: 6 }]] }
      : { ms: 340, anchor: "tip", keys: [[0, REST], [0.7, a], [1, a]] };
  const strike: ClipDef =
    base === "bow"
      ? { ms: 300, anchor: "tip", hitAt: 0.15, keys: [[0, { ...a, pull: 6 }], [0.15, plus(plus({ arm: -1.45, wpn: 2.77, lean: -0.08, pull: 0 }, delta), kick)], [1, { ...a, pull: 0 }]] }
      : { ms: 260, anchor: "tip", hitAt: 0.15, keys: [[0, a], [0.15, plus(plus({ arm: -1.6, wpn: 2.77, lean: -0.12 }, delta), kick)], [1, a]], fx: [fx("muzzle", "anchor", 0.1, 0.45)] };
  return { [`${name}_in`]: windup, [name]: strike } as Record<N | `${N}_in`, ClipDef>;
}

/**
 * 變體的片段（不在 `OPENER_CLIPS` 的那些）。同一列的出招片段 `ms`、`hitAt` 和該列原本的出招一樣：
 * 劍、刀、魔導劍、斧錘 220／0.62；成對 280／0.45；槍 200／0.7；鐮 240／0.6；鞭 240／0.7。
 */
export const VARIANT_CLIPS = {
  // 劍、刀
  windup_lo: wind(260, LO),
  slash_lo: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, LO], [0.62, { arm: -1.3, wpn: 2.3, lean: 0.12, ...STANCE }], [1, { arm: -1.7, wpn: 2.5, lean: 0.15, ...STANCE }]] },
  windup_side: wind(260, SIDE),
  slash_side: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, SIDE], [0.62, { arm: -1.2, wpn: -3.1, lean: 0.12, ...STANCE }], [1, { arm: -1.1, wpn: -3.5, lean: 0.18, ...STANCE }]] },
  sword_thrust_in: wind(260, THRUST_BACK),
  sword_thrust: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, THRUST_BACK], [0.62, { arm: -1.45, elbow: 0, wpn: 3.0, lean: 0.22, hipN: 0.5, hipF: -0.35 }], [1, { arm: -1.4, elbow: 0, wpn: 3.0, lean: 0.2, hipN: 0.5, hipF: -0.35 }]], move: [[0, 0], [0.62, 7], [1, 7]] },
  hop_in: wind(260, HOP_IN),
  hop_slash: { ms: 220, anchor: "tip", hitAt: 0.62, air: 7, keys: [[0, HOP_IN], [0.62, { arm: -0.4, wpn: 1.9, lean: 0.25, hipN: 0.6, hipF: -0.3, kneeN: 0.4 }], [1, { arm: 0.1, wpn: 1.9, lean: 0.2, kneeN: 0.5, kneeF: 0.5, bob: 1.5 }]], move: [[0, 0], [0.62, 5], [1, 5]] },
  draw_in: wind(260, DRAW_IN),
  draw_slash: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, DRAW_IN], [0.62, { arm: -1.6, elbow: 0, wpn: 2.0, lean: 0.3, hipN: 0.55, hipF: -0.4 }], [1, { arm: -2.0, elbow: 0, wpn: 2.1, lean: 0.25, hipN: 0.55, hipF: -0.4 }]], move: [[0, 0], [0.62, 9], [1, 9]] },
  spin_in: wind(260, TWIST),
  spin_slash: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, TWIST], [0.35, { arm: -1.2, wpn: -2.2, lean: 0.05, hipN: 0.1, hipF: 0 }], [0.62, { arm: -1.3, wpn: -3.4, lean: 0.18, ...STANCE }], [1, { arm: -1.2, wpn: -3.8, lean: 0.15, ...STANCE }]] },
  // 魔導劍（蓄力 280，劍身發光）
  arcane_side_in: wind(280, SIDE, { fx: [fx("glow", "anchor", 0.3, 1)] }),
  arcane_thrust_in: wind(280, THRUST_BACK, { fx: [fx("glow", "anchor", 0.3, 1)] }),
  rune_in: wind(280, RUNE_UP, { fx: [fx("glow", "anchor", 0.2, 1), fx("sigil", "anchor", 0.45, 1)] }),
  rune_slash: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, RUNE_UP], [0.62, { arm: -0.7, wpn: 2.2, lean: 0.2, ...STANCE }], [1, { arm: -0.3, wpn: 2.2, lean: 0.2, ...STANCE }]], fx: [fx("glow", "anchor", 0, 0.62)] },
  // 斧、錘、雙手武器
  cleave_in: wind(260, CLEAVE_IN),
  cleave: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, CLEAVE_IN], [0.62, { arm: -0.3, wpn: 2.3, armF: -0.4, lean: 0.32, hipN: 0.55, hipF: -0.35, bob: 1.5 }], [1, { arm: -0.1, wpn: 2.3, armF: -0.2, lean: 0.3, hipN: 0.55, hipF: -0.35, bob: 1.5 }]] },
  heavy_side_in: wind(260, HEAVY_SIDE),
  heavy_sweep: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, HEAVY_SIDE], [0.62, { arm: -1.3, wpn: -3.0, armF: -1.3, lean: 0.2, ...STANCE }], [1, { arm: -1.2, wpn: -3.5, armF: -1.2, lean: 0.22, ...STANCE }]] },
  whirl_in: wind(260, WHIRL_IN),
  whirl: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, WHIRL_IN], [0.3, { arm: -2.6, wpn: 1.4, armF: -2.4, lean: -0.1, bob: -0.5 }], [0.62, { arm: -1.2, wpn: 2.9, armF: -1.2, lean: 0.28, ...STANCE, bob: 1 }], [1, { arm: -0.6, wpn: 2.6, armF: -0.6, lean: 0.25, ...STANCE, bob: 1 }]] },
  // 成對武器（蓄力 260，出招 280／0.45）
  pair_stab_in: wind(260, STAB_IN),
  pair_stab: { ms: 280, anchor: "tip", hitAt: 0.45, keys: [[0, STAB_IN], [0.2, { arm: 0.3, elbow: -1.3, wpn: 2.4, armF: -1.45, elbowF: 0, lean: 0.12, hipN: 0.3 }], [0.45, { arm: -1.45, elbow: 0, wpn: 3.0, armF: 0.2, elbowF: -1.2, lean: 0.22, ...STANCE }], [1, { arm: -1.4, elbow: 0, wpn: 3.0, armF: 0.2, elbowF: -1.2, lean: 0.2, ...STANCE }]], move: [[0, 0], [0.45, 6], [1, 6]] },
  pair_spin_in: wind(260, PAIR_TWIST),
  pair_spin: { ms: 280, anchor: "tip", hitAt: 0.45, keys: [[0, PAIR_TWIST], [0.2, { arm: -1.2, wpn: -1.6, armF: -1.4, lean: 0.05 }], [0.45, { arm: -1.3, wpn: -3.3, armF: -2.0, lean: 0.18, ...STANCE }], [1, { arm: -1.2, wpn: -3.6, armF: -1.5, lean: 0.15, ...STANCE }]] },
  backhand_in: wind(260, BACKHAND_IN),
  backhand_stab: { ms: 280, anchor: "tip", hitAt: 0.45, keys: [[0, BACKHAND_IN], [0.45, { arm: -0.9, elbow: -0.2, wpn: 4.2, armF: -0.6, lean: 0.25, ...STANCE, bob: 1 }], [1, { arm: -0.8, elbow: -0.2, wpn: 4.2, armF: -0.4, lean: 0.22, ...STANCE, bob: 1 }]] },
  // 槍（蓄力 220，出招 200／0.7）
  low_thrust_in: wind(220, LOW_IN),
  low_thrust: { ms: 200, anchor: "tip", hitAt: 0.7, keys: [[0, LOW_IN], [0.7, { arm: -0.6, wpn: 2.6, lean: 0.3, hipN: 0.55, hipF: -0.35, kneeN: 0.6, kneeF: 0.5, bob: 2 }], [1, { arm: -0.6, wpn: 2.6, lean: 0.28, hipN: 0.55, hipF: -0.35, kneeN: 0.6, kneeF: 0.5, bob: 2 }]], move: [[0, 0], [0.7, 8], [1, 8]] },
  spear_side_in: wind(220, SPEAR_SIDE),
  spear_sweep: { ms: 200, anchor: "tip", hitAt: 0.7, keys: [[0, SPEAR_SIDE], [0.7, { arm: -1.2, wpn: -3.1, lean: 0.15, ...STANCE }], [1, { arm: -1.1, wpn: -3.4, lean: 0.18, ...STANCE }]] },
  leap_thrust_in: wind(220, LEAP_IN),
  leap_thrust: { ms: 200, anchor: "tip", hitAt: 0.7, air: 8, keys: [[0, LEAP_IN], [0.7, { arm: -0.9, wpn: 3.1, lean: 0.3, hipN: 0.5, hipF: -0.3 }], [1, { arm: -0.9, wpn: 3.1, lean: 0.25, hipN: 0.5, hipF: -0.3, kneeN: 0.5, kneeF: 0.5, bob: 1.5 }]], move: [[0, 0], [0.7, 9], [1, 9]] },
  // 鐮（蓄力 260，出招 240／0.6）
  scythe_side_in: wind(260, SIDE),
  scythe_lift_in: wind(260, SCY_LIFT_IN),
  scythe_lift: { ms: 240, anchor: "tip", hitAt: 0.6, keys: [[0, SCY_LIFT_IN], [0.6, { arm: -1.8, wpn: -4.0, lean: 0.1, hipN: 0.4, hipF: -0.3 }], [1, { arm: -2.2, wpn: -3.8, lean: 0.08, hipN: 0.4, hipF: -0.3 }]] },
  scythe_spin_in: wind(260, TWIST),
  scythe_spin: { ms: 240, anchor: "tip", hitAt: 0.6, keys: [[0, TWIST], [0.3, { arm: -1.2, wpn: -2.1, lean: 0.05 }], [0.6, { arm: -1.3, wpn: -3.5, lean: 0.18, ...STANCE }], [1, { arm: -1.2, wpn: -4.0, lean: 0.15, ...STANCE }]] },
  // 鞭（蓄力 240，出招 240／0.7）
  whip_up_in: wind(240, WHIP_UP_IN),
  whip_up: { ms: 240, anchor: "tip", hitAt: 0.7, keys: [[0, WHIP_UP_IN], [0.4, { arm: -1.0, wpn: 0.4, lean: 0 }], [0.7, { arm: -2.2, wpn: 2.6, lean: 0.1 }], [1, { arm: -2.0, wpn: 2.4, lean: 0.08 }]] },
  whip_side_in: wind(240, WHIP_IN),
  whip_wrap_in: wind(240, WRAP_IN),
  whip_wrap: { ms: 240, anchor: "tip", hitAt: 0.7, keys: [[0, WRAP_IN], [0.35, { arm: -2.6, wpn: 2.0, lean: 0 }], [0.7, { arm: -1.5, wpn: 3.4, lean: 0.12 }], [1, { arm: -0.5, elbow: -1.5, wpn: 2.0, lean: -0.2, hipN: -0.2, hipF: 0.3 }]], move: [[0, 0], [0.7, 0], [1, -2]] },
  // ---- 6N-7 拳套、空手（蓄力 200，出招 180／0.6，同起手對照表的 fist_in／punch） ----
  hook_in: wind(200, HOOK_IN, { anchor: "hand" }),
  hook: { ms: 180, anchor: "hand", hitAt: 0.6, keys: [[0, HOOK_IN], [0.6, { arm: -1.35, elbow: -1.2, lean: 0.22, ...STANCE }], [1, { arm: -1.2, elbow: -1.3, lean: 0.18, ...STANCE }]], move: [[0, 0], [0.6, 4], [1, 4]] },
  upper_in: wind(200, UPPER_IN, { anchor: "hand" }),
  uppercut: { ms: 180, anchor: "hand", hitAt: 0.6, keys: [[0, UPPER_IN], [0.6, { arm: -2.6, elbow: -1.1, lean: -0.1, hipN: 0.3, bob: -0.6 }], [1, { arm: -2.7, elbow: -0.9, lean: -0.08, hipN: 0.3, bob: -0.3 }]], move: [[0, 0], [0.6, 3], [1, 3]] },
  knee_in: wind(200, KNEE_IN, { anchor: "chest" }),
  knee_strike: { ms: 180, anchor: "chest", hitAt: 0.6, keys: [[0, KNEE_IN], [0.6, { arm: -0.4, elbow: -1.8, armF: -0.4, elbowF: -1.8, lean: 0.25, hipN: 1.5, kneeN: 1.9, bob: -1 }], [1, { arm: -0.4, elbow: -1.8, armF: -0.4, elbowF: -1.8, lean: 0.2, hipN: 1.2, kneeN: 1.7, bob: -0.6 }]], move: [[0, 0], [0.6, 5], [1, 5]] },
  kick_in: wind(200, KICK_IN, { anchor: "feet" }),
  spin_kick: { ms: 180, anchor: "feet", hitAt: 0.6, keys: [[0, KICK_IN], [0.35, { arm: -0.8, elbow: -1.2, lean: -0.35, hipN: 0.6, kneeN: 1.2, hipF: 0.2 }], [0.6, { arm: 0.2, elbow: -1.2, armF: -0.6, lean: -0.4, hipN: 1.7, kneeN: 0.2, hipF: -0.1 }], [1, { arm: 0.1, elbow: -1.3, armF: -0.4, lean: -0.3, hipN: 1.4, kneeN: 0.4 }]] },
  // ---- 6N-7 遠程：只換姿勢與後座；長度、`hitAt`、特效照起手對照表（弓 aim 360／release 300、0.15；弩、火槍 aim_gun 340／fire 260、0.15） ----
  ...rangedPair("bow_crouch", "bow", BOW_CROUCH, {}),
  ...rangedPair("bow_side", "bow", BOW_SIDE, { lean: -0.03 }),
  ...rangedPair("bow_lob", "bow", BOW_LOB, { arm: -0.05 }),
  ...rangedPair("gun_hip", "gun", GUN_HIP, { elbow: -0.15 }),
  ...rangedPair("gun_kneel", "gun", GUN_KNEEL, { lean: -0.04 }),
} as const satisfies Record<string, ClipDef>;

export type VariantClipId = keyof typeof VARIANT_CLIPS;

const v = (id: string, zh: string, windup: ClipId, strike: ClipId, swing: Swing, arc: ArcSpec | null): AttackVariant => ({ id, zh, windup, strike, swing, arc });

/**
 * 變體表（方案 2.10 第 5 點的例子）。每列第一個 ＝ 6N-6 以前的普攻（起手對照表的近身那一欄），弧光照舊由上往下或照揮的方向。
 */
const MELEE_VARIANTS: Readonly<Record<Exclude<AttackFamily, "fist" | "bow" | "crossbow" | "gun">, readonly AttackVariant[]>> = {
  sword: [
    v("sword_down", "由上往下", "windup", "slash", "down", ARC_DOWN),
    v("sword_up", "由下往上", "windup_lo", "slash_lo", "up", ARC_UP),
    v("sword_across", "橫掃", "windup_side", "slash_side", "across", ARC_ACROSS),
    v("sword_thrust", "突刺", "sword_thrust_in", "sword_thrust", "thrust", line(0)),
    v("sword_hop", "小跳斬", "hop_in", "hop_slash", "down", { kind: "arc", from: -0.55 * PI, sweep: 0.8 * PI }),
  ],
  saber: [
    v("saber_down", "由上往下", "windup", "slash", "down", ARC_DOWN),
    v("saber_up", "由下往上", "windup_lo", "slash_lo", "up", ARC_UP),
    v("saber_across", "橫掃", "windup_side", "slash_side", "across", ARC_ACROSS),
    v("saber_draw", "拔刀斬", "draw_in", "draw_slash", "up", { kind: "arc", from: 0.6 * PI, sweep: -0.75 * PI }),
    v("saber_spin", "迴身斬", "spin_in", "spin_slash", "spin", ARC_RING),
  ],
  arcane: [
    v("arcane_down", "由上往下", "arcane_windup", "slash", "down", ARC_DOWN),
    v("arcane_across", "橫掃", "arcane_side_in", "slash_side", "across", ARC_ACROSS),
    v("arcane_thrust", "突刺", "arcane_thrust_in", "sword_thrust", "thrust", line(0)),
    v("arcane_rune", "符文一亮再斬", "rune_in", "rune_slash", "down", { kind: "arc", from: -0.5 * PI, sweep: 0.75 * PI }),
  ],
  heavy: [
    v("heavy_cleave", "劈", "cleave_in", "cleave", "down", { kind: "arc", from: -0.55 * PI, sweep: 0.85 * PI }),
    v("heavy_across", "橫掃", "heavy_side_in", "heavy_sweep", "across", ARC_ACROSS),
    v("heavy_whirl", "掄一圈", "whirl_in", "whirl", "spin", { kind: "ring", from: PI, sweep: 2 * PI, squash: 1 }),
  ],
  pair: [
    v("pair_cross", "交叉斬", "x_windup", "twin_slash", "down", { kind: "cross", angle: 0.3 * PI, angle2: 0.7 * PI }),
    v("pair_stab", "連刺", "pair_stab_in", "pair_stab", "thrust", line(0)),
    v("pair_spin", "迴旋", "pair_spin_in", "pair_spin", "spin", ARC_RING),
    v("pair_backhand", "反手刺", "backhand_in", "backhand_stab", "down", line(0.4 * PI)),
  ],
  spear: [
    v("spear_thrust", "直刺", "thrust_in", "thrust", "thrust", line(0)),
    v("spear_low", "下段刺", "low_thrust_in", "low_thrust", "thrust", line(0.15 * PI)),
    v("spear_across", "橫掃", "spear_side_in", "spear_sweep", "across", ARC_ACROSS),
    v("spear_leap", "跳刺", "leap_thrust_in", "leap_thrust", "thrust", line(0.3 * PI)),
  ],
  scythe: [
    v("scythe_across", "橫掃", "scythe_side_in", "sweep", "across", ARC_ACROSS),
    v("scythe_lift", "上挑", "scythe_lift_in", "scythe_lift", "up", ARC_UP),
    v("scythe_spin", "迴旋", "scythe_spin_in", "scythe_spin", "spin", ARC_RING),
  ],
  whip: [
    v("whip_up", "上甩", "whip_up_in", "whip_up", "up", ARC_UP),
    v("whip_side", "側甩", "whip_side_in", "whip_lash", "across", ARC_ACROSS),
    v("whip_wrap", "纏繞拉扯", "whip_wrap_in", "whip_wrap", "spin", ARC_RING),
  ],
};

/** 6N-7 的列（每列第一個 ＝ 6N-7 以前的普攻：拳套空手照近身那一欄，弓、弩、火槍照遠程那一欄）。 */
const MORE_VARIANTS: Readonly<Record<"fist" | "bow" | "crossbow" | "gun", readonly AttackVariant[]>> = {
  fist: [
    v("fist_jab", "直拳", "fist_in", "punch", "thrust", line(0)),
    v("fist_hook", "勾拳", "hook_in", "hook", "across", ARC_ACROSS),
    v("fist_upper", "上勾拳", "upper_in", "uppercut", "up", ARC_UP),
    v("fist_knee", "膝撞", "knee_in", "knee_strike", "up", line(-0.3 * PI)),
    v("fist_kick", "迴旋踢", "kick_in", "spin_kick", "spin", ARC_RING),
  ],
  bow: [
    v("bow_stand", "站射", "aim", "release", "shoot", null),
    v("bow_crouch", "半蹲射", "bow_crouch_in", "bow_crouch", "shoot", null),
    v("bow_side", "側身射", "bow_side_in", "bow_side", "shoot", null),
    v("bow_lob", "拋射", "bow_lob_in", "bow_lob", "shoot", null),
  ],
  crossbow: [
    v("crossbow_shoulder", "抵肩射", "aim_gun", "fire", "shoot", null),
    v("crossbow_hip", "腰射", "gun_hip_in", "gun_hip", "shoot", null),
    v("crossbow_kneel", "單膝射", "gun_kneel_in", "gun_kneel", "shoot", null),
  ],
  gun: [
    v("gun_shoulder", "抵肩射", "aim_gun", "fire", "shoot", null),
    v("gun_hip", "腰射", "gun_hip_in", "gun_hip", "shoot", null),
    v("gun_kneel", "單膝射", "gun_kneel_in", "gun_kneel", "shoot", null),
  ],
};

/** 變體表（6N-6 近戰 8 列＋6N-7 的 4 列）。 */
export const ATTACK_VARIANTS: Readonly<Record<AttackFamily, readonly AttackVariant[]>> = { ...MELEE_VARIANTS, ...MORE_VARIANTS };

// ---- 挑法 -----------------------------------------------------------------------

/** 戰鬥中的鍵：「戰鬥鍵:事件 seq:施放者 ID:片段名」（片段名 ＝ `attack_<列>`）。 */
export function battleVariantKey(battleKey: string, seq: number, casterId: string, family: AttackFamily): string {
  return `${battleKey}:${seq}:${casterId}:attack_${family}`;
}

/** 探索中（沒有戰鬥鍵）：「地圖 ID:單位 ID:動作序號」。 */
export function exploreVariantKey(mapId: string, unitId: string, actionNo: number): string {
  return `${mapId}:${unitId}:${actionNo}`;
}

/**
 * murmur3 的 fmix32（avalanche finalizer）：把 32 位元整數的每一位元打散到所有位元（6N-7，6N-6 待決第 1 點）。
 * FNV-1a 的低位元混合得差：鍵只差最後一個字元（連續的 seq）時，`% 4` 會規律地 0,1,2,3 輪替；先過這一道再取餘數就不會。
 * 純整數運算、確定性。只在挑變體時用；`seedOf` 本身不改（墨線抖動等其他地方照舊）。
 */
export function fmix32(h: number): number {
  let x = h >>> 0;
  x ^= x >>> 16;
  x = Math.imul(x, 0x85ebca6b);
  x ^= x >>> 13;
  x = Math.imul(x, 0xc2b2ae35);
  x ^= x >>> 16;
  return x >>> 0;
}

/** 挑變體用的雜湊：`fmix32(seedOf(鍵))`。攻擊、受擊、閃避的變體都用它。 */
export function variantHash(key: string): number {
  return fmix32(seedOf(key));
}

/** 照鍵挑變體：`variantHash` ÷ 變體數取餘數（重播、觀戰、重新整理都一樣）。 */
export function variantIndex(family: AttackFamily, key: string): number {
  return variantHash(key) % ATTACK_VARIANTS[family].length;
}

export function pickVariant(family: AttackFamily, key: string): AttackVariant {
  return ATTACK_VARIANTS[family][variantIndex(family, key)]!;
}

// ---- 弧光畫到畫面上 ------------------------------------------------------------------

/**
 * 本地座標 → 畫面方向：朝東照原樣；往西打（水平分量為主）左右鏡像；往南、往北打照朝東畫
 * （正面、背面看不出左右，弧光的上下仍和揮的方向一致）。
 */
export function arcMirror(dx: number, dy: number): 1 | -1 {
  return dx < 0 && Math.abs(dx) >= Math.abs(dy) ? -1 : 1;
}
