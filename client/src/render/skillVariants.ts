// 技能變體（Phase 6N-8；方案 docs/art/動畫方案.md 2.11，需求 docs/art/動畫移植需求第二批.md 第 0 節第 3 點、第 7 節）。
// 同一招放幾次，樣子會有點不同：三層（起手、原語、特效）各自照確定性雜湊挑一個變體，組合起來。
// **不變的**：顏色（元素）、範圍與形狀（技能形狀）、落點、命中時間（`hitAt`）、一招 1.8 秒的上限、6N-5 的停頓與強化——
// 衍生片段的長度與命中點照原本（`skillVariantPoses.ts`），特效只換軌跡、爆發的樣子與粒子分布，格子與時間不動。
// 鍵 ＝「戰鬥鍵:事件 seq:施放者 ID:skill:技能 ID」（普攻 ＝ `attack`）；雜湊 ＝ `attackVariants.variantHash`（FNV-1a ＋ fmix32）。
// 三層各取雜湊的不同位元（`LAYER_BITS`）：起手 0～9、原語 10～20、特效 21～31；同一層裡的幾項再用混合進位拆開。
// 全部是資料＋純函式：不用 Math.random()、不讀時鐘。
import { variantHash } from "./attackVariants";
import type { CastMode, ClipId, WeaponClass } from "./skillClips";
import { CAST_OPENERS, CHARGE_POSES, HEAL_STYLES, ORB_CHANTS, STAFF_CHANTS, SUMMON_CIRCLES, type PoseVariant } from "./skillVariantPoses";

export { CAST_OPENERS, CHARGE_POSES, HEAL_STYLES, ORB_CHANTS, STAFF_CHANTS, SUMMON_CIRCLES };

// ---- 變體表 -----------------------------------------------------------------------

export interface Named<I extends string = string> {
  id: I;
  zh: string;
}

export type DashRoute = "straight" | "curve" | "zigzag";
export type LeapArc = "low" | "high" | "flip";
export type Trail = "arc" | "straight" | "spiral";
export type BurstShape = "rays" | "ring" | "star";
export type Spread = "even" | "side" | "center";

/** 原語：衝刺路線（3）。第一個 ＝ 原本的直線。 */
export const DASH_ROUTES: readonly Named<DashRoute>[] = [
  { id: "straight", zh: "直線" },
  { id: "curve", zh: "略彎" },
  { id: "zigzag", zh: "Z 字殘影" },
];
/** 原語：跳躍弧度（3）。 */
export const LEAP_ARCS: readonly Named<LeapArc>[] = [
  { id: "low", zh: "低弧" },
  { id: "high", zh: "高弧" },
  { id: "flip", zh: "空翻" },
];
/** 特效：飛行物軌跡（3，落點固定是目標格）。 */
export const TRAILS: readonly Named<Trail>[] = [
  { id: "arc", zh: "微弧" },
  { id: "straight", zh: "直線" },
  { id: "spiral", zh: "螺旋" },
];
/** 特效：爆發形狀（3）。 */
export const BURST_SHAPES: readonly Named<BurstShape>[] = [
  { id: "rays", zh: "放射" },
  { id: "ring", zh: "圓環" },
  { id: "star", zh: "星形" },
];
/** 特效：粒子分布（3）。 */
export const SPREADS: readonly Named<Spread>[] = [
  { id: "even", zh: "均勻" },
  { id: "side", zh: "偏一側" },
  { id: "center", zh: "從中心噴出" },
];

/** 起手層用哪一組：法器（法杖 `s`、法球 `o`）的詠唱、其他武器的施法起手、近身技能的蓄力。 */
export type OpenerSet = "chant_s" | "chant_o" | "cast" | "charge";
export const OPENER_SETS: Readonly<Record<OpenerSet, readonly PoseVariant[]>> = { chant_s: STAFF_CHANTS, chant_o: ORB_CHANTS, cast: CAST_OPENERS, charge: CHARGE_POSES };

/** 方案 2.11 的變體數（測試鎖住）。 */
export const SKILL_VARIANT_COUNT = {
  chant: 5,
  cast: 3,
  charge: 3,
  dash: 3,
  leap: 3,
  summon: 3,
  heal: 3,
  trail: 3,
  burst: 3,
  spread: 3,
} as const;

// ---- 挑法 -------------------------------------------------------------------------

/** 三層各用雜湊的哪幾個位元（[起, 迄)）。 */
export const LAYER_BITS = { opener: [0, 10], primitive: [10, 21], fx: [21, 32] } as const satisfies Record<string, readonly [number, number]>;
export type SkillLayer = keyof typeof LAYER_BITS;

/** 雜湊的第 [起, 迄) 位元（無號整數）。 */
export function layerField(hash: number, layer: SkillLayer): number {
  const [lo, hi] = LAYER_BITS[layer];
  const width = hi - lo;
  return width >= 32 ? hash >>> 0 : (hash >>> lo) & ((1 << width) - 1);
}

/** 戰鬥中的鍵：「戰鬥鍵:事件 seq:施放者 ID:skill:技能 ID」（普攻的技能 ID 用 `attack`）。 */
export function skillVariantKey(battleKey: string, seq: number, casterId: string, skillId: string | null): string {
  return `${battleKey}:${seq}:${casterId}:skill:${skillId ?? "attack"}`;
}

export interface SkillVariantPick {
  key: string;
  /** 起手層（沒有可換的蓄力時為 `null`）。 */
  opener: { set: OpenerSet; index: number } | null;
  dash: number;
  leap: number;
  summon: number;
  heal: number;
  trail: number;
  burst: number;
  spread: number;
}

/**
 * 起手層用哪一組（不新增欄位，照武器與施放方式）：
 * - 法杖、法球：飛行物、自身、地面 → 詠唱（5）；普攻只有遠程（6N-7 待決 1；近身的杖敲、球推照舊）；
 * - 其他武器：飛行物、自身、地面 → 施法起手（3）；近身技能 → 蓄力（3）；普攻不挑（6N-6／6N-7 的攻擊變體）；
 * - 起手對照表那一格沒有蓄力片段（例如法杖、槍、空手的地面）→ `null`（沒有可換的，照舊）。
 */
export function openerSetOf(weapon: WeaponClass, mode: CastMode, basic: boolean, hasWindup: boolean): OpenerSet | null {
  if (!hasWindup) return null;
  const focus = weapon === "staff" ? "chant_s" : weapon === "orb" ? "chant_o" : null;
  if (basic) return focus !== null && mode === "ranged" ? focus : null;
  if (mode === "melee") return "charge";
  return focus ?? "cast";
}

/** 照鍵挑三層的變體。`opener` 是起手層用哪一組（`openerSetOf`）。 */
export function pickSkillVariant(key: string, opener: OpenerSet | null): SkillVariantPick {
  const h = variantHash(key);
  const o = layerField(h, "opener");
  const p = layerField(h, "primitive");
  const f = layerField(h, "fx");
  return {
    key,
    opener: opener === null ? null : { set: opener, index: o % OPENER_SETS[opener].length },
    dash: p % 3,
    leap: Math.floor(p / 3) % 3,
    summon: Math.floor(p / 9) % 3,
    heal: Math.floor(p / 27) % 3,
    trail: f % 3,
    burst: Math.floor(f / 3) % 3,
    spread: Math.floor(f / 9) % 3,
  };
}

/** 起手層的片段：原本的蓄力或出招 → 衍生片段（第一個詠唱、施法起手 ＝ 原本的，ID 不變）。 */
export function openerClip<C extends ClipId>(base: C, pick: SkillVariantPick | null): C | ClipId {
  const o = pick?.opener ?? null;
  if (o === null) return base;
  const v = OPENER_SETS[o.set][o.index]!;
  if (v.keys === undefined && v.pose === undefined && v.fx === undefined) return base;
  return `${base}~${o.set}${o.index}` as ClipId;
}

/** 原語層的片段：召喚（`summon_press`）換法陣、治療增益（`palm_heal`、`raise_hand`）換光；其他原語照舊。 */
export function primitiveClip<C extends ClipId>(clip: C, pick: SkillVariantPick | null, healOf: (clip: ClipId) => number | null): C | ClipId {
  if (pick === null) return clip;
  if (clip === "summon_press") return pick.summon === 0 ? clip : (`${clip}~summon${pick.summon}` as ClipId);
  if (clip === "palm_heal" || clip === "raise_hand") {
    const own = healOf(clip);
    return own === null || own === pick.heal ? clip : (`${clip}~heal${pick.heal}` as ClipId);
  }
  return clip;
}

/** 這一招的特效變體（飛行物軌跡、爆發形狀、粒子分布）。 */
export interface FxLook {
  trail: Trail;
  burst: BurstShape;
  spread: Spread;
}

export function fxLookOf(pick: SkillVariantPick): FxLook {
  return { trail: TRAILS[pick.trail]!.id, burst: BURST_SHAPES[pick.burst]!.id, spread: SPREADS[pick.spread]!.id };
}

// ---- 幾何（純函式；繪製器照它畫） ----------------------------------------------------

type Pt = { x: number; y: number };

/**
 * 飛行物在時間 `t`（0～1）的位置：微弧（往上拱）、直線、螺旋（繞著直線轉，幅度兩頭為 0）。
 * 不管哪一種，`t = 0` 在起點、`t = 1` **正好在目標格**（偏移量乘上 sin(πt)，兩頭都是 0）。`tile` ＝ 格子大小（像素）。
 */
export function trajectoryPoint(a: Pt, b: Pt, t: number, trail: Trail, tile: number): Pt {
  const k = t <= 0 ? 0 : t >= 1 ? 1 : t;
  const x = a.x + (b.x - a.x) * k;
  const y = a.y + (b.y - a.y) * k;
  if (k === 0 || k === 1 || trail === "straight") return { x, y };
  const env = Math.sin(k * Math.PI);
  if (trail === "arc") return { x, y: y - env * tile * 0.32 };
  const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
  const nx = -(b.y - a.y) / len;
  const ny = (b.x - a.x) / len;
  const w = Math.sin(k * Math.PI * 6) * env * tile * 0.16;
  return { x: x + nx * w, y: y + ny * w };
}

/** 衝刺路線在時間 `t` 往旁邊偏多少（格的倍數，垂直於前進方向）：直線 0、略彎一道弧、Z 字兩個轉角（1/3、2/3）。兩頭都是 0。 */
export function routeOffset(route: DashRoute, t: number): number {
  const k = t <= 0 ? 0 : t >= 1 ? 1 : t;
  if (route === "curve") return 0.28 * Math.sin(k * Math.PI);
  if (route === "zigzag") {
    const A = 0.24;
    if (k < 1 / 3) return A * (k * 3);
    if (k < 2 / 3) return A * (1 - (k - 1 / 3) * 6);
    return -A * (1 - (k - 2 / 3) * 3);
  }
  return 0;
}

/** Z 字的轉角（留殘影的時間點）。 */
export const ZIGZAG_CORNERS: readonly number[] = [0, 1 / 3, 2 / 3];

/** 跳躍：離地高度的倍率與身體轉了幾圈（低弧 ＝ 原本的 `leap_air`；空翻轉一圈；時間 `t` 0～1）。 */
export function leapShape(arc: LeapArc, t: number): { airScale: number; spin: number } {
  const k = t <= 0 ? 0 : t >= 1 ? 1 : t;
  if (arc === "low") return { airScale: 1, spin: 0 };
  if (arc === "high") return { airScale: 1.8, spin: 0 };
  // 空翻：起跳、落地時站直，中段轉一圈（緩入緩出）
  const u = k < 0.15 ? 0 : k > 0.85 ? 1 : (k - 0.15) / 0.7;
  return { airScale: 1.25, spin: Math.PI * 2 * (u * u * (3 - 2 * u)) };
}

/**
 * 爆發粒子的分布：均勻（照原本）、偏一側（往 `side` 那邊噴，`side` ＝ 飛行的水平方向）、從中心噴出（往上噴泉）。
 * 只移粒子的位置；粒子數、大小、顏色、透明度不變。`k` ＝ 爆發的進度、`reach` ＝ 原本的半徑。
 */
export function spreadParticle(p: Pt, spread: Spread, k: number, reach: number, side: 1 | -1): Pt {
  if (spread === "side") return { x: p.x * 0.55 + side * reach * 0.45 * Math.min(1, k * 1.6), y: p.y * 0.8 };
  if (spread === "center") return { x: p.x * 0.45, y: p.y * 0.35 - reach * 0.9 * k * (1 - 0.45 * k) };
  return p;
}
