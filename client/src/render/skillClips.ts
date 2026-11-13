// 技能片段（Phase 6N-1；需求 docs/art/動畫移植需求第二批.md 第 2、3 節，方案 docs/art/動畫方案.md 2.3）。
// 全部是資料＋純函式：片段 ＝ 幾個關鍵姿勢（時間 0～1 → 姿勢，段間緩入緩出），加上命中點 `hitAt`、特效起點 `anchor`、
// 往前的位移 `move`、離地高度 `air` 與特效提示 `fx`。不用 Math.random()、不讀時鐘；同一個時間永遠得到同一個姿勢。
// - 起手對照表 `OPENER_TABLE`：武器種類（13 列）× 施放方式（4 欄）→ 起手片段＋出招片段（方案 2.3 (1-1)）；
// - 原語片段 `PRIMITIVE_CLIPS`：方案 2.3 (1) 的表，6N-2 上半＋6N-3 下半（`skill_primitives.yaml` 每個原語都有）；之後新增而沒有片段的原語回傳 `null`，播放時退回「起手＋現有特效」；
// - 目標片段：被推、被拉、被撞倒（6N-4 會沿用）。
// 角度、座標照 inkPose.ts：側面朝東，畫布旋轉順時針為正；`arm` 負＝往前上抬（−π/2 水平往前）；
// 武器絕對角度 ＝ arm ＋ elbow ＋ wpn，0 ＝ 作用端朝上、π/2 朝前（inkWeaponFrame.ts 的統一座標）。
import type { Facing } from "../api/types";
import type { GearItem } from "./appearance";
import { mixPose, pz, type InkPose } from "./inkPose";
import { DOLL_JOINTS } from "./inkDoll";
import { dollSkin } from "./inkStyle";
import { easeInOut, quantizePose } from "./motionClips";
import { VARIANT_CLIPS, type VariantClipId } from "./attackVariants";
import { deriveClip } from "./skillVariantPoses";

// ---- 武器種類與施放方式 -------------------------------------------------------

/** 起手對照表的 13 列（方案 2.3 (1-1)）。`blade` ＝ 劍、刀；`arcane` ＝ 魔導劍；`pair` ＝ 成對武器；`bare` ＝ 空手、不認得的武器。 */
export type WeaponClass = "blade" | "arcane" | "pair" | "spear" | "scythe" | "whip" | "fist" | "staff" | "orb" | "bow" | "crossbow" | "gun" | "bare";
export const WEAPON_CLASSES: readonly WeaponClass[] = ["blade", "arcane", "pair", "spear", "scythe", "whip", "fist", "staff", "orb", "bow", "crossbow", "gun", "bare"];

/** 施放方式（由形狀與射程判斷，不新增欄位）：近身接觸、飛行物／遠程、自身／範圍、地面。 */
export type CastMode = "melee" | "ranged" | "self" | "ground";
export const CAST_MODES: readonly CastMode[] = ["melee", "ranged", "self", "ground"];

/** 紙娃娃主手 kind → 武器種類。表上沒有的 kind（拂塵、符紙、傀儡線）照規則退回空手；斧、錘、大劍、匕首見報告待決。 */
const KIND_CLASS: Readonly<Record<string, WeaponClass>> = {
  sword: "blade",
  greatsword: "blade",
  dagger: "blade",
  axe: "blade",
  hammer: "blade",
  spear: "spear",
  scythe: "scythe",
  whip: "whip",
  fist: "fist",
  staff: "staff",
  bow: "bow",
  crossbow: "crossbow",
  longgun: "gun",
  pistol: "gun",
  shotgun: "gun",
};

/** 紙娃娃的主手、副手 → 武器種類：魔導劍 ＝ 劍＋`arcane` 形制；主副手同種 ＝ 成對；只有副手法球 ＝ 法球。 */
export function weaponClassOf(main: GearItem | undefined, off: GearItem | undefined): WeaponClass {
  if (main === undefined) return off?.kind === "orb" ? "orb" : "bare";
  const base = KIND_CLASS[main.kind] ?? "bare";
  if (main.kind === "sword" && main.form === "arcane") return "arcane";
  if (base !== "bare" && off !== undefined && off.kind === main.kind && (base === "blade" || base === "fist")) return base === "fist" ? "fist" : "pair";
  if (base === "bare" && off?.kind === "orb") return "orb";
  return base;
}

// ---- 片段 ---------------------------------------------------------------------

/** 特效起點（由當下姿勢算出的位置）：作用端、主手、另一隻手、腳底、胸口、頭頂。 */
export type Anchor = "tip" | "hand" | "offhand" | "feet" | "chest" | "head";

/** 片段附帶的特效提示（BattleRenderer 照它畫；位置：`anchor` 片段的起點、`feet` 施放者腳下、`target` 目標身上、`targetFeet`、`targetHead`、`link` 目標→施放者）。 */
export type FxKind =
  | "glow"
  | "sigil"
  | "circle"
  | "muzzle"
  | "ring"
  | "ringUp"
  | "motesUp"
  | "motesDown"
  | "motesIn"
  | "shards"
  | "link"
  | "mark"
  | "pillar"
  | "wind"
  | "smoke"
  | "quake"
  // 6N-3
  | "spread"
  | "shrink"
  | "gust"
  | "zoneRing"
  | "rise"
  | "dust"
  | "arc"
  | "trap"
  | "runeFall"
  | "burst"
  | "formIn"
  | "formOut"
  | "guard"
  | "goldFlash"
  | "scan"
  | "orbFly"
  | "iconFly"
  | "rewind"
  | "stack"
  | "coin"
  | "snap"
  | "wound"
  // 6N-8 技能變體（治療增益的「花瓣散落」）
  | "petals";
/** `head` 施放者頭頂；`link` 目標 → 施放者；`linkOut` 施放者 → 目標（6N-3）。 */
export type FxWhere = "anchor" | "feet" | "head" | "target" | "targetFeet" | "targetHead" | "link" | "linkOut";
export interface FxCue {
  kind: FxKind;
  where: FxWhere;
  /** 片段內的起訖（0～1）。 */
  from: number;
  to: number;
}

type Key = readonly [number, InkPose];

export interface ClipDef {
  /** 基本長度（毫秒，正常速度）。 */
  ms: number;
  /** 關鍵姿勢（時間 0～1 遞增；段間緩入緩出）。 */
  keys: readonly Key[];
  /** 命中（或放出）的時間點（0～1）；傷害數字、受擊、特效爆發都從這一刻開始。沒有＝這個片段不命中。 */
  hitAt?: number;
  /** 特效起點。 */
  anchor: Anchor;
  /** 往面向方向的位移（虛擬像素）關鍵點。 */
  move?: readonly (readonly [number, number])[];
  /** 離地高度（虛擬像素，sin 拋物線的頂點）。 */
  air?: number;
  /** 沒有身體動作（不佔時間，和前一個片段同時播；6N-3 的退還、層數類原語）：姿勢不套到小人身上，只播特效。 */
  still?: boolean;
  fx?: readonly FxCue[];
}

const REST: InkPose = { arm: 0, wpn: 0.75 };
const fx = (kind: FxKind, where: FxWhere, from = 0, to = 1): FxCue => ({ kind, where, from, to });

// 揮砍（劍、刀、魔導劍；樣張 CLIP.windup／slash）
const WIND_HI: InkPose = { arm: -2.5, wpn: 1.7, lean: -0.1, hipN: 0.25, hipF: -0.2 };
// 收手（拳、空手）
const FIST_IN: InkPose = { arm: 0.4, elbow: -1.6, lean: -0.1, hipN: 0.2 };
// 劍往前一指（作用端朝前）
const POINT: InkPose = { arm: -1.45, wpn: 3.02, lean: -0.04 };
// 舉高（作用端朝上）
const RAISE: InkPose = { arm: -2.9, wpn: 2.9, lean: -0.06, bob: -0.6 };
// 射擊瞄準
const AIM: InkPose = { arm: -1.3, wpn: 2.87, lean: -0.05 };

/**
 * 起手片段（方案 2.3 (1-1)）。命名：`*_in`／`windup` 類是蓄力（沒有 `hitAt`），其餘是出招（有 `hitAt`）。
 * 時間取樣張的 200～520 毫秒。
 */
export const OPENER_CLIPS = {
  // 近身接觸
  windup: { ms: 260, anchor: "tip", keys: [[0, REST], [1, WIND_HI]] },
  slash: { ms: 220, anchor: "tip", hitAt: 0.62, keys: [[0, WIND_HI], [0.62, { arm: -0.5, wpn: 1.8, lean: 0.15, hipN: 0.45, hipF: -0.3 }], [1, { arm: 0.15, wpn: 1.85, lean: 0.18, hipN: 0.45, hipF: -0.3 }]] },
  arcane_windup: { ms: 280, anchor: "tip", keys: [[0, REST], [1, WIND_HI]], fx: [fx("glow", "anchor", 0.3, 1)] },
  x_windup: { ms: 260, anchor: "tip", keys: [[0, REST], [1, { arm: -2.3, wpn: 1.6, armF: -2.0, elbowF: -0.2, lean: -0.12, hipN: 0.25 }]] },
  twin_slash: { ms: 280, anchor: "tip", hitAt: 0.45, keys: [[0, { arm: -2.3, wpn: 1.6, armF: -2.0, elbowF: -0.2, lean: -0.12, hipN: 0.25 }], [0.45, { arm: 0.1, wpn: 1.85, armF: -1.6, lean: 0.15, hipN: 0.45, hipF: -0.3 }], [1, { arm: 0.2, wpn: 1.85, armF: 0.2, lean: 0.2, hipN: 0.45, hipF: -0.3 }]] },
  thrust_in: { ms: 220, anchor: "tip", keys: [[0, REST], [1, { arm: 0.5, wpn: 0.9, lean: -0.08 }]] },
  thrust: { ms: 200, anchor: "tip", hitAt: 0.7, keys: [[0, { arm: 0.5, wpn: 0.9, lean: -0.08 }], [0.7, { arm: -1.0, wpn: 2.57, lean: 0.2, hipN: 0.5, hipF: -0.35 }], [1, { arm: -1.0, wpn: 2.57, lean: 0.2, hipN: 0.5, hipF: -0.35 }]], move: [[0, 0], [0.7, 8], [1, 8]] },
  sweep_in: { ms: 260, anchor: "tip", keys: [[0, REST], [1, { arm: -1.2, wpn: -0.4, lean: -0.12, hipN: 0.2 }]] },
  sweep: { ms: 240, anchor: "tip", hitAt: 0.6, keys: [[0, { arm: -1.2, wpn: -0.4, lean: -0.12, hipN: 0.2 }], [0.6, { arm: -1.2, wpn: -2.6, lean: 0.12, hipN: 0.45, hipF: -0.3 }], [1, { arm: -1.1, wpn: -3.5, lean: 0.18, hipN: 0.45, hipF: -0.3 }]] },
  whip_in: { ms: 240, anchor: "tip", keys: [[0, REST], [1, { arm: -2.6, wpn: 0.4, lean: -0.15 }]] },
  whip_lash: { ms: 240, anchor: "tip", hitAt: 0.7, keys: [[0, { arm: -2.6, wpn: 0.4, lean: -0.15 }], [0.4, { arm: -1.6, wpn: 1.2, lean: 0.05 }], [0.7, { arm: -1.2, wpn: 2.75, lean: 0.15 }], [1, { arm: -1.0, wpn: 2.6, lean: 0.12 }]] },
  fist_in: { ms: 200, anchor: "hand", keys: [[0, REST], [1, FIST_IN]] },
  punch: { ms: 180, anchor: "hand", hitAt: 0.6, keys: [[0, FIST_IN], [0.6, { arm: -1.55, elbow: 0, lean: 0.22, hipN: 0.5, hipF: -0.35 }], [1, { arm: -1.5, elbow: -0.1, lean: 0.2, hipN: 0.5, hipF: -0.35 }]], move: [[0, 0], [0.6, 6], [1, 6]] },
  staff_raise: { ms: 240, anchor: "tip", keys: [[0, REST], [1, { arm: -2.2, wpn: 1.4, lean: -0.1 }]] },
  staff_tap: { ms: 200, anchor: "tip", hitAt: 0.6, keys: [[0, { arm: -2.2, wpn: 1.4, lean: -0.1 }], [0.6, { arm: -0.9, wpn: 2.7, lean: 0.18, hipN: 0.35 }], [1, { arm: -0.8, wpn: 2.7, lean: 0.15, hipN: 0.35 }]] },
  orb_in: { ms: 220, anchor: "offhand", keys: [[0, REST], [1, { armF: 0.4, elbowF: -1.4, lean: -0.08 }]] },
  orb_push: { ms: 200, anchor: "offhand", hitAt: 0.6, keys: [[0, { armF: 0.4, elbowF: -1.4, lean: -0.08 }], [0.6, { armF: -1.55, elbowF: 0, lean: 0.18, hipN: 0.4 }], [1, { armF: -1.5, lean: 0.15, hipN: 0.4 }]] },
  bash_in: { ms: 220, anchor: "tip", keys: [[0, REST], [1, { arm: 0.35, wpn: 0.2, lean: -0.12 }]] },
  bash: { ms: 200, anchor: "tip", hitAt: 0.6, keys: [[0, { arm: 0.35, wpn: 0.2, lean: -0.12 }], [0.6, { arm: -1.2, wpn: 0.9, lean: 0.25, hipN: 0.5, hipF: -0.3 }], [1, { arm: -1.1, wpn: 0.9, lean: 0.2, hipN: 0.5, hipF: -0.3 }]], move: [[0, 0], [0.6, 5], [1, 5]] },
  // 飛行物、遠程
  point: { ms: 260, anchor: "tip", keys: [[0, REST], [1, { ...POINT, armF: -0.3 }]] },
  palm_release: { ms: 240, anchor: "offhand", hitAt: 0.55, keys: [[0, { ...POINT, armF: -0.3 }], [0.55, { ...POINT, armF: -1.55, elbowF: 0, lean: 0.12 }], [1, { ...POINT, armF: -1.5, lean: 0.08 }]] },
  cross_point: { ms: 260, anchor: "tip", keys: [[0, REST], [1, { ...POINT, armF: -1.3, elbowF: -0.2 }]] },
  mudra: { ms: 300, anchor: "hand", keys: [[0, REST], [1, { arm: -0.8, elbow: -1.8, armF: -0.8, elbowF: -1.8, lean: -0.05 }]], fx: [fx("glow", "anchor", 0.4, 1)] },
  bare_release: { ms: 240, anchor: "offhand", hitAt: 0.55, keys: [[0, { arm: -0.8, elbow: -1.8, armF: -0.8, elbowF: -1.8, lean: -0.05 }], [0.55, { arm: -0.3, elbow: -0.6, armF: -1.55, elbowF: 0, lean: 0.12 }], [1, { arm: -0.2, armF: -1.5, lean: 0.08 }]] },
  sigil: { ms: 480, anchor: "tip", keys: [[0, REST], [0.5, { arm: -1.25, wpn: 2.82, lean: -0.04 }], [1, { arm: -1.25, wpn: 2.82, lean: -0.04 }]], fx: [fx("sigil", "anchor", 0.35, 1)] },
  sigil_cast: { ms: 380, anchor: "tip", hitAt: 0.3, keys: [[0, { arm: -1.25, wpn: 2.82, lean: -0.04 }], [0.3, { arm: -1.4, wpn: 2.82, lean: 0.08 }], [1, { arm: -1.25, wpn: 2.82, lean: 0.08 }]], fx: [fx("sigil", "anchor", 0, 0.5)] },
  tip_point: { ms: 260, anchor: "tip", keys: [[0, REST], [1, { arm: -1.2, wpn: 2.77, lean: -0.06 }]] },
  tip_shot: { ms: 220, anchor: "tip", hitAt: 0.5, keys: [[0, { arm: -1.2, wpn: 2.77, lean: -0.06 }], [0.5, { arm: -1.45, wpn: 2.95, lean: 0.12, hipN: 0.3 }], [1, { arm: -1.4, wpn: 2.9, lean: 0.1, hipN: 0.3 }]], move: [[0, 0], [0.5, 3], [1, 3]] },
  scythe_flick: { ms: 240, anchor: "tip", hitAt: 0.55, keys: [[0, { arm: -1.2, wpn: -0.4, lean: -0.12, hipN: 0.2 }], [0.55, { arm: -1.3, wpn: -3.3, lean: 0.12, hipN: 0.4 }], [1, { arm: -1.3, wpn: -3.5, lean: 0.12, hipN: 0.4 }]] },
  fist_shot: { ms: 200, anchor: "hand", hitAt: 0.55, keys: [[0, FIST_IN], [0.55, { arm: -1.57, elbow: 0, lean: 0.15, hipN: 0.35 }], [1, { arm: -1.55, lean: 0.12, hipN: 0.35 }]] },
  channel: { ms: 520, anchor: "tip", keys: [[0, REST], [0.6, { arm: -2.5, wpn: 2.7, lean: -0.06, bob: -1.2 }], [1, { arm: -2.5, wpn: 2.7, lean: -0.06, bob: -0.4 }]], fx: [fx("circle", "feet", 0.1, 1)] },
  cast: { ms: 420, anchor: "tip", hitAt: 0.3, keys: [[0, { arm: -2.5, wpn: 2.7, lean: -0.06 }], [0.3, { arm: -1.2, wpn: 2.4, lean: 0.12 }], [1, { arm: -1.2, wpn: 2.4, lean: 0.12 }]], fx: [fx("circle", "feet", 0, 0.4)] },
  orb_channel: { ms: 520, anchor: "offhand", keys: [[0, REST], [0.6, { armF: -2.5, elbowF: -0.2, lean: -0.06, bob: -1.2 }], [1, { armF: -2.5, elbowF: -0.2, lean: -0.06, bob: -0.4 }]], fx: [fx("circle", "feet", 0.1, 1), fx("glow", "anchor", 0.3, 1)] },
  orb_cast: { ms: 400, anchor: "offhand", hitAt: 0.3, keys: [[0, { armF: -2.5, elbowF: -0.2, lean: -0.06 }], [0.3, { armF: -1.55, elbowF: 0, lean: 0.12 }], [1, { armF: -1.5, lean: 0.1 }]] },
  aim: { ms: 360, anchor: "tip", keys: [[0, REST], [0.6, AIM], [1, { ...AIM, pull: 6 }]] },
  release: { ms: 300, anchor: "tip", hitAt: 0.15, keys: [[0, { ...AIM, pull: 6 }], [0.15, { arm: -1.45, wpn: 2.77, lean: -0.08, pull: 0 }], [1, { ...AIM, pull: 0 }]] },
  aim_gun: { ms: 340, anchor: "tip", keys: [[0, REST], [0.7, AIM], [1, AIM]] },
  fire: { ms: 260, anchor: "tip", hitAt: 0.15, keys: [[0, AIM], [0.15, { arm: -1.6, wpn: 2.77, lean: -0.12 }], [1, AIM]], fx: [fx("muzzle", "anchor", 0.1, 0.45)] },
  // 自身、範圍
  raise: { ms: 280, anchor: "tip", keys: [[0, REST], [1, RAISE]] },
  raise_glow: { ms: 300, anchor: "tip", keys: [[0, REST], [1, RAISE]], fx: [fx("sigil", "anchor", 0.4, 1)] },
  cross_chest: { ms: 280, anchor: "chest", keys: [[0, REST], [1, { arm: -0.9, elbow: -1.2, wpn: 1.4, armF: -0.9, elbowF: -1.2, lean: -0.06 }]] },
  plant: { ms: 260, anchor: "tip", keys: [[0, REST], [0.7, { arm: -0.6, wpn: 0.6, bob: -1 }], [1, { arm: -0.5, wpn: 0.5, bob: 0.6 }]] },
  whip_circle: { ms: 360, anchor: "tip", keys: [[0, REST], [0.33, { arm: -2.6, wpn: 0.8 }], [0.66, { arm: -2.2, wpn: 3.6 }], [1, { arm: -2.8, wpn: 6.1 }]] },
  fist_clash: { ms: 260, anchor: "chest", keys: [[0, REST], [0.6, { arm: -0.6, elbow: -1.7, armF: -0.6, elbowF: -1.7, lean: -0.05 }], [1, { arm: -0.8, elbow: -1.5, armF: -0.8, elbowF: -1.5, bob: 0.6 }]] },
  orb_raise: { ms: 280, anchor: "offhand", keys: [[0, REST], [1, { armF: -2.9, elbowF: 0, lean: -0.06, bob: -0.6 }]] },
  palms_together: { ms: 300, anchor: "chest", keys: [[0, REST], [1, { arm: -0.9, elbow: -1.3, armF: -0.9, elbowF: -1.3, lean: -0.05 }]] },
  aura_pulse: { ms: 260, anchor: "feet", hitAt: 0.3, keys: [[0, {}], [0.3, { bob: -1.4 }], [1, {}]], fx: [fx("ringUp", "feet", 0.2, 1)] },
  // 地面
  tip_down_in: { ms: 240, anchor: "tip", keys: [[0, REST], [1, { arm: -1.7, wpn: 2.0, lean: -0.08 }]] },
  tip_down: { ms: 220, anchor: "tip", hitAt: 0.6, keys: [[0, { arm: -1.7, wpn: 2.0, lean: -0.08 }], [0.6, { arm: -0.6, wpn: 3.3, lean: 0.2, hipN: 0.35, bob: 1 }], [1, { arm: -0.6, wpn: 3.3, lean: 0.18, hipN: 0.35, bob: 1 }]] },
  stab_ground_in: { ms: 260, anchor: "tip", keys: [[0, REST], [1, { arm: -2.7, wpn: 3.0, lean: -0.1 }]], fx: [fx("glow", "anchor", 0.4, 1)] },
  stab_ground: { ms: 240, anchor: "tip", hitAt: 0.55, keys: [[0, { arm: -2.7, wpn: 3.0, lean: -0.1 }], [0.55, { arm: -0.4, wpn: 3.5, lean: 0.25, kneeN: 0.6, kneeF: 0.6, bob: 2.2 }], [1, { arm: -0.4, wpn: 3.5, lean: 0.22, kneeN: 0.6, kneeF: 0.6, bob: 2.2 }]], fx: [fx("sigil", "feet", 0.55, 1)] },
  pair_down: { ms: 240, anchor: "tip", hitAt: 0.6, keys: [[0, { ...POINT, armF: -1.3 }], [0.6, { arm: -0.6, wpn: 3.3, armF: -0.6, lean: 0.2, bob: 1.2 }], [1, { arm: -0.6, wpn: 3.3, armF: -0.6, lean: 0.18, bob: 1.2 }]] },
  butt_stamp: { ms: 240, anchor: "feet", hitAt: 0.55, keys: [[0, REST], [0.35, { arm: -0.8, wpn: 0.3, bob: -1.5 }], [0.55, { arm: -0.4, wpn: 0.1, bob: 0.8 }], [1, { arm: -0.4, wpn: 0.1 }]] },
  scythe_drag: { ms: 260, anchor: "tip", hitAt: 0.6, keys: [[0, { arm: -1.2, wpn: -0.4, lean: -0.12 }], [0.6, { arm: -0.5, wpn: -2.9, lean: 0.25, hipN: 0.4, bob: 1 }], [1, { arm: -0.4, wpn: -3.1, lean: 0.25, hipN: 0.4, bob: 1 }]] },
  whip_ground: { ms: 240, anchor: "tip", hitAt: 0.65, keys: [[0, { arm: -2.6, wpn: 0.4, lean: -0.15 }], [0.65, { arm: -0.6, wpn: 3.1, lean: 0.2 }], [1, { arm: -0.5, wpn: 3.1, lean: 0.18 }]] },
  ground_punch: { ms: 240, anchor: "hand", hitAt: 0.6, keys: [[0, FIST_IN], [0.6, { arm: -0.3, elbow: 0, lean: 0.35, kneeN: 1.0, kneeF: 1.0, hipN: 0.5, bob: 3.2 }], [1, { arm: -0.3, lean: 0.3, kneeN: 1.0, kneeF: 1.0, hipN: 0.5, bob: 3.2 }]] },
  staff_stamp: { ms: 240, anchor: "feet", hitAt: 0.55, keys: [[0, { arm: -1.6, wpn: 1.6, bob: -1.2 }], [0.55, { arm: -0.5, wpn: 0.5, bob: 0.8 }], [1, { arm: -0.5, wpn: 0.5 }]], fx: [fx("circle", "feet", 0.5, 1)] },
  orb_press: { ms: 240, anchor: "offhand", hitAt: 0.6, keys: [[0, { armF: -2.5, elbowF: -0.2 }], [0.6, { armF: -0.6, elbowF: 0, lean: 0.2, bob: 1.5 }], [1, { armF: -0.6, lean: 0.18, bob: 1.5 }]] },
  lob_aim: { ms: 360, anchor: "tip", keys: [[0, REST], [0.6, { arm: -2.3, wpn: 2.1, lean: -0.2 }], [1, { arm: -2.3, wpn: 2.1, lean: -0.2, pull: 6 }]] },
  lob: { ms: 280, anchor: "tip", hitAt: 0.15, keys: [[0, { arm: -2.3, wpn: 2.1, lean: -0.2, pull: 6 }], [0.15, { arm: -2.4, wpn: 2.1, lean: -0.24, pull: 0 }], [1, { arm: -2.2, wpn: 2.1, lean: -0.15, pull: 0 }]] },
  aim_down: { ms: 320, anchor: "tip", keys: [[0, REST], [1, { arm: -0.9, wpn: 2.9, lean: 0.08 }]] },
  fire_down: { ms: 240, anchor: "tip", hitAt: 0.15, keys: [[0, { arm: -0.9, wpn: 2.9, lean: 0.08 }], [0.15, { arm: -1.2, wpn: 2.9, lean: -0.02 }], [1, { arm: -0.9, wpn: 2.9, lean: 0.08 }]], fx: [fx("muzzle", "anchor", 0.1, 0.45)] },
  palm_ground: { ms: 260, anchor: "hand", hitAt: 0.6, keys: [[0, REST], [0.6, { arm: -0.2, elbow: 0, armF: -0.3, lean: 0.35, kneeN: 1.0, kneeF: 1.0, hipN: 0.5, bob: 3.2 }], [1, { arm: -0.2, armF: -0.3, lean: 0.3, kneeN: 1.0, kneeF: 1.0, hipN: 0.5, bob: 3.2 }]], fx: [fx("circle", "feet", 0.5, 1)] },
} as const satisfies Record<string, ClipDef>;

export type OpenerClipId = keyof typeof OPENER_CLIPS;

/** 一個起手：先播 `windup`（蓄力，可為 `null`＝直接出招），再播 `strike`（出招，有 `hitAt`）。 */
export interface Opener {
  windup: OpenerClipId | null;
  strike: OpenerClipId;
}
const op = (windup: OpenerClipId | null, strike: OpenerClipId): Opener => ({ windup, strike });

/** 起手對照表（方案 2.3 (1-1)，13 列 × 4 欄）。魔導劍飛行物照選項 A「劍指畫符」（代決）。 */
export const OPENER_TABLE: Readonly<Record<WeaponClass, Readonly<Record<CastMode, Opener>>>> = {
  blade: { melee: op("windup", "slash"), ranged: op("point", "palm_release"), self: op("raise", "aura_pulse"), ground: op("tip_down_in", "tip_down") },
  arcane: { melee: op("arcane_windup", "slash"), ranged: op("sigil", "sigil_cast"), self: op("raise_glow", "aura_pulse"), ground: op("stab_ground_in", "stab_ground") },
  pair: { melee: op("x_windup", "twin_slash"), ranged: op("cross_point", "palm_release"), self: op("cross_chest", "aura_pulse"), ground: op("cross_point", "pair_down") },
  spear: { melee: op("thrust_in", "thrust"), ranged: op("tip_point", "tip_shot"), self: op("plant", "aura_pulse"), ground: op(null, "butt_stamp") },
  scythe: { melee: op("windup", "sweep"), ranged: op("sweep_in", "scythe_flick"), self: op("raise", "aura_pulse"), ground: op("sweep_in", "scythe_drag") },
  whip: { melee: op("whip_in", "whip_lash"), ranged: op("whip_in", "whip_lash"), self: op("whip_circle", "aura_pulse"), ground: op("whip_in", "whip_ground") },
  fist: { melee: op("fist_in", "punch"), ranged: op("fist_in", "fist_shot"), self: op("fist_clash", "aura_pulse"), ground: op("fist_in", "ground_punch") },
  staff: { melee: op("staff_raise", "staff_tap"), ranged: op("channel", "cast"), self: op("raise", "aura_pulse"), ground: op(null, "staff_stamp") },
  orb: { melee: op("orb_in", "orb_push"), ranged: op("orb_channel", "orb_cast"), self: op("orb_raise", "aura_pulse"), ground: op("orb_raise", "orb_press") },
  bow: { melee: op("bash_in", "bash"), ranged: op("aim", "release"), self: op("raise", "aura_pulse"), ground: op("lob_aim", "lob") },
  crossbow: { melee: op("bash_in", "bash"), ranged: op("aim_gun", "fire"), self: op("raise", "aura_pulse"), ground: op("aim_down", "fire_down") },
  gun: { melee: op("bash_in", "bash"), ranged: op("aim_gun", "fire"), self: op("raise", "aura_pulse"), ground: op("aim_down", "fire_down") },
  bare: { melee: op("fist_in", "punch"), ranged: op("mudra", "bare_release"), self: op("palms_together", "aura_pulse"), ground: op(null, "palm_ground") },
};

/** 起手（表上沒有的組合退回空手那一列）。 */
export function openerFor(weapon: WeaponClass, mode: CastMode): Opener {
  return OPENER_TABLE[weapon]?.[mode] ?? OPENER_TABLE.bare[mode];
}

// ---- 原語片段（6N-2 上半、6N-3 下半） ------------------------------------------

/**
 * 施放者身上的原語片段（方案 2.3 (1) 的表）。`damage` 的片段就是起手決定的出招（不另外佔時間）；
 * `damage_multiplier` 是出招前的「加力」；位移類（dash…swap）是位移途中的姿勢（BattleRenderer.moveOne 用）。
 */
export const PRIMITIVE_CLIPS = {
  empower: { ms: 180, anchor: "tip", keys: [[0, {}], [0.5, { elbow: -0.35, bob: 0.8, lean: -0.05 }], [1, { elbow: -0.2, bob: 0.4 }]], fx: [fx("glow", "anchor", 0.1, 1)] },
  mark_recover: { ms: 260, anchor: "hand", keys: [[0, {}], [1, { arm: -0.3, wpn: 0.6, lean: -0.04 }]], fx: [fx("mark", "targetHead", 0.1, 1)] },
  palm_heal: { ms: 300, anchor: "offhand", keys: [[0, {}], [0.45, { armF: -1.55, elbowF: 0, lean: 0.05 }], [1, { armF: -1.5, elbowF: 0, lean: 0.05 }]], fx: [fx("glow", "anchor", 0.3, 0.9), fx("motesUp", "target", 0.3, 1)] },
  arm_guard: { ms: 260, anchor: "hand", keys: [[0, {}], [0.5, { arm: -1.3, elbow: -1.2, armF: -1.1, elbowF: -1.0, lean: 0.06 }], [1, { arm: -1.2, elbow: -1.1, armF: -1.0, elbowF: -0.9 }]], fx: [fx("ring", "target", 0.35, 1)] },
  sweep_down: { ms: 280, anchor: "offhand", keys: [[0, {}], [0.35, { armF: -2.4, elbowF: -0.2 }], [1, { armF: 0.2, elbowF: 0, lean: 0.06 }]], fx: [fx("motesDown", "target", 0.3, 1)] },
  kneel_lift: { ms: 420, anchor: "hand", keys: [[0, {}], [0.35, { kneeN: 1.6, hipN: 1.0, kneeF: 0.4, bob: 5, lean: 0.15 }], [1, { kneeN: 1.6, hipN: 1.0, kneeF: 0.4, bob: 5, lean: 0, arm: -2.6, elbow: -0.3, armF: -2.6, elbowF: -0.3 }]], fx: [fx("pillar", "target", 0.4, 1)] },
  fist_chest: { ms: 260, anchor: "chest", keys: [[0, {}], [0.6, { arm: -0.7, elbow: -2.0, lean: -0.04 }], [1, { arm: -0.7, elbow: -2.0, bob: 0.4 }]], fx: [fx("motesIn", "feet", 0.2, 1)] },
  raise_hand: { ms: 260, anchor: "offhand", keys: [[0, {}], [0.5, { armF: -2.8, elbowF: 0 }], [1, { armF: -2.8, elbowF: 0, bob: -0.4 }]], fx: [fx("ringUp", "targetFeet", 0.35, 1)] },
  point_at: { ms: 240, anchor: "offhand", keys: [[0, {}], [0.5, { armF: -1.57, elbowF: 0, lean: 0.06 }], [1, { armF: -1.55, elbowF: 0, lean: 0.06 }]], fx: [fx("glow", "target", 0.4, 1)] },
  palm_push: { ms: 240, anchor: "offhand", keys: [[0, { armF: -0.6, elbowF: -1.2 }], [0.5, { armF: -1.6, elbowF: 0, lean: 0.15 }], [1, { armF: -1.55, elbowF: 0, lean: 0.12 }]], move: [[0, 0], [0.5, 2], [1, 2]], fx: [fx("shards", "target", 0.45, 1)] },
  grab_back: { ms: 300, anchor: "offhand", keys: [[0, {}], [0.35, { armF: -1.6, elbowF: 0, lean: 0.1 }], [1, { armF: -0.6, elbowF: -1.6, lean: -0.1 }]], fx: [fx("link", "link", 0.35, 1)] },
  point_tap: { ms: 240, anchor: "offhand", keys: [[0, {}], [0.5, { armF: -1.65, elbowF: 0 }], [1, { armF: -1.5, elbowF: -0.2 }]], fx: [fx("glow", "anchor", 0.4, 0.9)] },
  palm_shove: { ms: 220, anchor: "offhand", keys: [[0, { armF: -0.5, elbowF: -1.4, arm: -0.4, elbow: -1.2 }], [0.45, { armF: -1.6, elbowF: 0, arm: -1.45, elbow: 0, lean: 0.22, hipN: 0.45, hipF: -0.3 }], [1, { armF: -1.55, arm: -1.4, lean: 0.18, hipN: 0.45, hipF: -0.3 }]], move: [[0, 0], [0.45, 3], [1, 3]] },
  yank: { ms: 260, anchor: "offhand", keys: [[0, {}], [0.3, { armF: -1.6, elbowF: 0, lean: 0.12 }], [1, { armF: -0.4, elbowF: -1.5, lean: -0.18, hipN: -0.2, hipF: 0.3 }]], move: [[0, 0], [1, -2]] },
  sweep_low: { ms: 280, anchor: "feet", keys: [[0, {}], [0.3, { kneeF: 1.2, hipF: 0.2, bob: 2.4, lean: -0.1 }], [0.65, { hipN: 1.1, kneeN: 0.1, kneeF: 1.3, bob: 3, lean: -0.2 }], [1, { hipN: 0.3, kneeF: 0.6, bob: 1.2, lean: -0.05 }]] },
  stomp: { ms: 300, anchor: "feet", hitAt: 0.6, keys: [[0, {}], [0.45, { hipN: 0.9, kneeN: 1.2, liftL: 4, bob: -1, arm: -0.6, armF: -0.6 }], [0.6, { hipN: 0.1, kneeN: 0.2, liftL: 0, bob: 1.6, kneeF: 0.4 }], [1, { bob: 0.5 }]], fx: [fx("quake", "feet", 0.55, 1)] },
  // 位移途中的姿勢
  dash_lean: { ms: 260, anchor: "feet", keys: [[0, { lean: 0.35, hipN: 0.8, hipF: -0.7, kneeF: 0.9, arm: 0.6, armF: 0.5 }], [1, { lean: 0.35, hipN: 0.8, hipF: -0.7, kneeF: 0.9, arm: 0.6, armF: 0.5 }]], fx: [fx("wind", "feet", 0, 1)] },
  shoulder_charge: { ms: 260, anchor: "chest", keys: [[0, { lean: 0.45, hipN: 0.8, hipF: -0.7, kneeF: 0.9, arm: 0.3, elbow: -1.4, armF: 0.4 }], [1, { lean: 0.5, hipN: 0.8, hipF: -0.7, kneeF: 0.9, arm: 0.3, elbow: -1.4, armF: 0.4 }]], fx: [fx("wind", "feet", 0, 1)] },
  leap_air: { ms: 420, anchor: "feet", air: 18, keys: [[0, { kneeN: 0.8, kneeF: 0.8, bob: 2 }], [0.5, { hipN: 0.9, kneeN: 1.5, hipF: 0.5, kneeF: 1.7, arm: -0.9, armF: -0.7 }], [1, { kneeN: 0.6, kneeF: 0.6, bob: 1.5 }]] },
  warp_pose: { ms: 260, anchor: "chest", keys: [[0, {}], [0.5, { armF: -1.0, arm: -0.5, bob: -0.6 }], [1, {}]] },
  smoke_step: { ms: 200, anchor: "chest", keys: [[0, { lean: 0.3, kneeN: 0.6, kneeF: 0.6, bob: 2 }], [1, { lean: 0.2, kneeN: 0.4, kneeF: 0.4, bob: 1 }]], fx: [fx("smoke", "feet", 0, 1)] },
  swap_pose: { ms: 260, anchor: "chest", keys: [[0, {}], [0.5, { armF: -0.9, arm: -0.4 }], [1, {}]], fx: [fx("link", "link", 0, 1)] },
  // ---- 6N-3 下半 ----
  // 召喚
  summon_press: { ms: 380, anchor: "hand", keys: [[0, {}], [0.4, { arm: -2.4, armF: -2.4, bob: -0.6 }], [0.75, { arm: -0.6, elbow: -0.2, armF: -0.6, elbowF: -0.2, lean: 0.15, kneeN: 0.5, kneeF: 0.5, bob: 1.6 }], [1, { arm: -0.6, elbow: -0.2, armF: -0.6, elbowF: -0.2, lean: 0.12, kneeN: 0.5, kneeF: 0.5, bob: 1.4 }]], fx: [fx("circle", "targetFeet", 0.4, 1), fx("motesUp", "targetFeet", 0.6, 1)] },
  sacrifice_grip: { ms: 340, anchor: "offhand", keys: [[0, {}], [0.35, { armF: -1.6, elbowF: 0, lean: 0.08 }], [0.6, { armF: -1.55, elbowF: -0.9, lean: 0.04 }], [1, { armF: -1.2, elbowF: -1.2, lean: -0.06 }]], fx: [fx("orbFly", "link", 0.4, 1)] },
  // 地表、地形
  scatter: { ms: 300, anchor: "offhand", keys: [[0, { armF: 0.3, elbowF: -0.8 }], [0.3, { armF: -0.4, elbowF: -1.4, lean: -0.05 }], [0.65, { armF: -1.9, elbowF: 0, lean: 0.12 }], [1, { armF: -1.7, elbowF: 0, lean: 0.1 }]], fx: [fx("spread", "targetFeet", 0.5, 1)] },
  zone_stamp: { ms: 320, anchor: "tip", keys: [[0, {}], [0.35, { arm: -1.6, wpn: 1.6, bob: -1 }], [0.55, { arm: -0.5, wpn: 0.4, bob: 0.8, lean: 0.08 }], [1, { arm: -0.5, wpn: 0.4, bob: 0.3 }]], fx: [fx("zoneRing", "targetFeet", 0.5, 1)] },
  blow_sleeve: { ms: 320, anchor: "offhand", keys: [[0, {}], [0.3, { armF: -2.2, elbowF: -0.5, lean: -0.08 }], [0.7, { armF: -1.0, elbowF: 0, lean: 0.18, hipN: 0.3 }], [1, { armF: -0.9, elbowF: 0, lean: 0.12, hipN: 0.3 }]], fx: [fx("gust", "target", 0.35, 1)] },
  press_clear: { ms: 300, anchor: "offhand", keys: [[0, {}], [0.4, { armF: -1.9, elbowF: -0.4 }], [1, { armF: -0.9, elbowF: 0, lean: 0.12, bob: 0.8 }]], fx: [fx("shrink", "targetFeet", 0.4, 1)] },
  raise_both: { ms: 340, anchor: "hand", keys: [[0, { arm: -0.3, armF: -0.3, bob: 0.6 }], [0.6, { arm: -2.8, elbow: 0, armF: -2.8, elbowF: 0, bob: -1 }], [1, { arm: -2.9, elbow: 0, armF: -2.9, elbowF: 0, bob: -1.2 }]], fx: [fx("rise", "target", 0.45, 1)] },
  // 升降地形：動作不同；特效共用現有的升降補間（vfx 的 terrain_changed），所以片段本身不帶特效
  stomp_raise: { ms: 320, anchor: "feet", keys: [[0, {}], [0.45, { hipN: 1.1, kneeN: 1.4, liftL: 5, bob: -1.4, arm: -1.6, armF: -1.6 }], [0.62, { hipN: 0.1, kneeN: 0.3, liftL: 0, bob: 1.8, arm: -0.4, armF: -0.4, kneeF: 0.5 }], [1, { bob: 0.4 }]] },
  press_lower: { ms: 340, anchor: "hand", keys: [[0, {}], [0.35, { arm: -2.0, armF: -2.0 }], [0.8, { arm: -0.5, elbow: 0, armF: -0.5, elbowF: 0, kneeN: 0.9, kneeF: 0.9, bob: 3, lean: 0.2 }], [1, { arm: -0.5, elbow: 0, armF: -0.5, elbowF: 0, kneeN: 0.9, kneeF: 0.9, bob: 3, lean: 0.2 }]] },
  // 物件、符文
  shoulder_ram: { ms: 300, anchor: "chest", keys: [[0, { lean: -0.1 }], [0.4, { lean: 0.5, hipN: 0.7, hipF: -0.5, arm: 0.3, elbow: -1.4, kneeF: 0.6 }], [1, { lean: 0.3, hipN: 0.4, hipF: -0.3, arm: 0.2, elbow: -1.2 }]], move: [[0, 0], [0.4, 7], [1, 4]], fx: [fx("dust", "targetFeet", 0.4, 1)] },
  lift_throw: { ms: 440, anchor: "hand", keys: [[0, { kneeN: 0.6, kneeF: 0.6, bob: 2 }], [0.4, { arm: -2.9, elbow: -0.3, armF: -2.9, elbowF: -0.3, bob: -0.8, lean: -0.15 }], [0.7, { arm: -1.4, elbow: 0, armF: -1.4, elbowF: 0, lean: 0.2, hipN: 0.4 }], [1, { arm: -1.2, armF: -1.2, lean: 0.15, hipN: 0.4 }]], fx: [fx("arc", "linkOut", 0.6, 1)] },
  crouch_place: { ms: 380, anchor: "hand", keys: [[0, {}], [0.5, { kneeN: 1.6, hipN: 1.0, kneeF: 1.2, bob: 5, lean: 0.25, arm: -0.4, elbow: -0.3 }], [1, { kneeN: 1.6, hipN: 1.0, kneeF: 1.2, bob: 5, lean: 0.25, arm: -0.4, elbow: -0.3 }]], fx: [fx("trap", "targetFeet", 0.5, 1)] },
  air_write: { ms: 420, anchor: "offhand", keys: [[0, {}], [0.25, { armF: -2.0, elbowF: -0.2 }], [0.5, { armF: -1.4, elbowF: -0.4 }], [0.75, { armF: -1.9, elbowF: -0.1 }], [1, { armF: -1.5, elbowF: -0.3 }]], fx: [fx("sigil", "anchor", 0.1, 0.8), fx("runeFall", "targetFeet", 0.6, 1)] },
  fist_clench: { ms: 280, anchor: "offhand", keys: [[0, {}], [0.4, { armF: -1.6, elbowF: 0, lean: 0.05 }], [0.6, { armF: -1.7, elbowF: -0.5, bob: 0.5 }], [1, { armF: -1.5, elbowF: -0.6 }]], fx: [fx("burst", "target", 0.55, 1)] },
  smash_down: { ms: 320, anchor: "tip", keys: [[0, {}], [0.4, { arm: -2.6, wpn: 1.8, lean: -0.1 }], [0.7, { arm: -0.4, wpn: 2.2, lean: 0.25, hipN: 0.4, bob: 1 }], [1, { arm: -0.4, wpn: 2.2, lean: 0.2, hipN: 0.4, bob: 0.8 }]], fx: [fx("shards", "target", 0.65, 1)] },
  // 形態
  form_gather: { ms: 400, anchor: "chest", keys: [[0, {}], [0.5, { arm: -2.4, armF: -2.4, bob: -0.8 }], [1, { arm: -0.6, elbow: -1.6, armF: -0.6, elbowF: -1.6, bob: 0.6 }]], fx: [fx("formIn", "feet", 0, 0.95)] },
  form_release: { ms: 380, anchor: "chest", keys: [[0, { arm: -0.6, elbow: -1.6, armF: -0.6, elbowF: -1.6, bob: 0.6 }], [0.5, { arm: -2.4, elbow: 0, armF: -2.4, elbowF: 0, bob: -0.8 }], [1, {}]], fx: [fx("formOut", "feet", 0.3, 1)] },
  // 防護與其他
  side_guard: { ms: 320, anchor: "chest", keys: [[0, {}], [0.45, { lean: 0.15, hipN: 0.6, hipF: -0.4, arm: -1.3, elbow: -1.1, armF: -1.6, elbowF: 0 }], [1, { lean: 0.1, hipN: 0.5, hipF: -0.35, arm: -1.2, elbow: -1.0, armF: -1.5, elbowF: 0 }]], move: [[0, 0], [0.45, 5], [1, 5]], fx: [fx("guard", "link", 0.35, 1)] },
  rally_up: { ms: 460, anchor: "chest", keys: [[0, { kneeN: 1.4, kneeF: 0.8, bob: 5, lean: 0.35, arm: 0.4, armF: 0.4 }], [0.45, { kneeN: 1.6, kneeF: 1.0, bob: 5.5, lean: 0.4, armF: -0.6, elbowF: -0.2 }], [1, { arm: -0.3 }]], fx: [fx("goldFlash", "feet", 0.5, 1)] },
  shade_look: { ms: 380, anchor: "head", keys: [[0, {}], [0.4, { armF: -2.6, elbowF: -2.0, lean: -0.06 }], [1, { armF: -2.6, elbowF: -2.0, lean: -0.06, bob: -0.3 }]], fx: [fx("scan", "feet", 0.3, 1)] },
  snatch: { ms: 320, anchor: "hand", keys: [[0, {}], [0.35, { arm: -1.6, elbow: 0, lean: 0.12 }], [1, { arm: -0.5, elbow: -1.7, lean: -0.08 }]], fx: [fx("iconFly", "link", 0.35, 1)] },
  // 給予（共用：靠飛過去的圖示分辨）
  shoulder_tap: { ms: 320, anchor: "offhand", keys: [[0, {}], [0.45, { armF: -1.7, elbowF: -0.1, lean: 0.1 }], [0.7, { armF: -1.5, elbowF: -0.3, lean: 0.1 }], [1, { armF: -1.6, elbowF: -0.1, lean: 0.08 }]], fx: [fx("iconFly", "linkOut", 0.4, 1)] },
  // 退還、層數（共用；沒有身體動作）
  rewind_still: { ms: 420, anchor: "head", still: true, keys: [[0, {}], [1, {}]], fx: [fx("rewind", "head", 0, 1)] },
  stack_still: { ms: 360, anchor: "head", still: true, keys: [[0, {}], [1, {}]], fx: [fx("stack", "head", 0, 1)] },
  // 規則類
  coin_flip: { ms: 420, anchor: "offhand", keys: [[0, {}], [0.3, { armF: -1.0, elbowF: -1.4 }], [0.45, { armF: -1.6, elbowF: -0.6, bob: -0.3 }], [1, { armF: -1.0, elbowF: -1.4 }]], fx: [fx("coin", "head", 0.4, 1)] },
  finger_snap: { ms: 300, anchor: "offhand", keys: [[0, {}], [0.5, { armF: -2.0, elbowF: -1.0 }], [0.6, { armF: -2.1, elbowF: -1.1, bob: 0.4 }], [1, { armF: -1.9, elbowF: -1.0 }]], fx: [fx("snap", "head", 0.5, 1)] },
  clutch_wound: { ms: 340, anchor: "chest", keys: [[0, {}], [0.4, { armF: -0.7, elbowF: -1.9, lean: 0.2, kneeN: 0.4, bob: 1 }], [1, { armF: -0.7, elbowF: -1.9, lean: 0.15, kneeN: 0.3, bob: 0.6 }]], fx: [fx("wound", "anchor", 0.3, 0.9)] },
  // 目標片段（6N-4 會沿用）
  pushed: { ms: 200, anchor: "chest", keys: [[0, { lean: -0.3, hipN: -0.3, hipF: 0.35, kneeN: 0.2, arm: 0.5, armF: 0.6 }], [1, { lean: -0.25, hipN: -0.25, hipF: 0.3, kneeN: 0.15, arm: 0.4, armF: 0.5 }]] },
  pulled: { ms: 200, anchor: "chest", keys: [[0, { lean: 0.3, hipN: 0.35, hipF: -0.4, kneeF: 0.3, arm: -0.8, armF: -0.9 }], [1, { lean: 0.25, hipN: 0.3, hipF: -0.35, kneeF: 0.25, arm: -0.7, armF: -0.8 }]] },
  knocked_down: { ms: 320, anchor: "chest", keys: [[0, {}], [1, {}]] },
} as const satisfies Record<string, ClipDef>;

export type PrimitiveClipId = keyof typeof PRIMITIVE_CLIPS;
/** 6N-8 技能變體的衍生片段：「原本的 ID~標籤」（`skillVariantPoses.deriveClip`；例如 `channel~chant_s1`）。 */
export type DerivedClipId = `${OpenerClipId | PrimitiveClipId}~${string}`;
/** 片段 ID：起手、原語、6N-6 的攻擊變體（`attackVariants.ts`），以及 6N-8 的衍生片段。 */
export type ClipId = OpenerClipId | PrimitiveClipId | VariantClipId | DerivedClipId;

function staticClip(id: string): ClipDef | undefined {
  return (OPENER_CLIPS as Record<string, ClipDef>)[id] ?? (PRIMITIVE_CLIPS as Record<string, ClipDef>)[id] ?? (VARIANT_CLIPS as Record<string, ClipDef>)[id];
}

const DERIVED = new Map<string, ClipDef>();

/** 衍生片段的原本 ID（不是衍生片段就是自己）。 */
export function baseClipOf(id: ClipId): OpenerClipId | PrimitiveClipId | VariantClipId {
  const i = id.indexOf("~");
  return (i < 0 ? id : id.slice(0, i)) as OpenerClipId | PrimitiveClipId | VariantClipId;
}

/** 片段定義（起手、原語、攻擊變體或衍生片段；衍生片段算一次後快取）。不認得的衍生標籤退回原本的片段。 */
export function clipDef(id: ClipId): ClipDef {
  const hit = staticClip(id);
  if (hit !== undefined) return hit;
  const cached = DERIVED.get(id);
  if (cached !== undefined) return cached;
  const i = id.indexOf("~");
  const base = staticClip(id.slice(0, i)) as ClipDef;
  const def = deriveClip(base, id.slice(i + 1)) ?? base;
  DERIVED.set(id, def);
  return def;
}

/** 原語在播放中的角色：`strike` ＝ 起手的出招；`pre` 出招前；`post` 出招後；`move` 位移途中（BattleRenderer.moveOne）。 */
export type PrimitiveRole = "strike" | "pre" | "post" | "move";

export interface PrimitivePlay {
  role: PrimitiveRole;
  /** 施放者的片段；`strike` 為 `null`（用起手的出招）。 */
  clip: PrimitiveClipId | null;
  /** 共用片段用來分辨的小圖示（給予：`skill`／`ap`／`reaction`；退還：`ap`／`cooldown`／`reset`；層數：`+1`／`-1`）。 */
  icon?: string;
}

/**
 * 原語 → 片段（方案 2.3 (1)）。`apply_status` 分增益、減益兩種（由事件的目標陣營判斷）。
 * 共用只有表上標明的幾組：`swap`／`swap_any`；`intercept`／`redirect_damage`；`grant_skill`／`grant_ap`／`extra_reaction`（靠 `icon` 分辨）；`refund_*`／`reset_cooldown`；`add_stack`／`consume_*`。升降地形動作不同、特效共用現有的升降補間。不在表上的原語 → `null`。
 */
export const PRIMITIVE_PLAYS: Readonly<Record<string, PrimitivePlay>> = {
  damage: { role: "strike", clip: null },
  damage_multiplier: { role: "pre", clip: "empower" },
  delayed_damage: { role: "post", clip: "mark_recover" },
  heal: { role: "post", clip: "palm_heal" },
  shield: { role: "post", clip: "arm_guard" },
  cleanse: { role: "post", clip: "sweep_down" },
  revive: { role: "post", clip: "kneel_lift" },
  restore_resource: { role: "post", clip: "fist_chest" },
  "apply_status:buff": { role: "post", clip: "raise_hand" },
  "apply_status:debuff": { role: "post", clip: "point_at" },
  dispel: { role: "post", clip: "palm_push" },
  steal_buff: { role: "post", clip: "grab_back" },
  dash: { role: "move", clip: "dash_lean" },
  charge_through: { role: "move", clip: "shoulder_charge" },
  leap: { role: "move", clip: "leap_air" },
  teleport: { role: "move", clip: "warp_pose" },
  shadowstep: { role: "move", clip: "smoke_step" },
  swap: { role: "move", clip: "swap_pose" },
  swap_any: { role: "move", clip: "swap_pose" },
  teleport_target: { role: "post", clip: "point_tap" },
  push: { role: "post", clip: "palm_shove" },
  pull: { role: "post", clip: "yank" },
  knock_prone: { role: "post", clip: "sweep_low" },
  shockwave: { role: "post", clip: "stomp" },
  // 6N-3 下半
  summon: { role: "post", clip: "summon_press" },
  summon_beside: { role: "post", clip: "summon_press" }, // TF-1：伴生、護主（被動、反應）暫借召喚的動作
  sacrifice_summon: { role: "post", clip: "sacrifice_grip" },
  create_surface: { role: "post", clip: "scatter" },
  zone: { role: "post", clip: "zone_stamp" },
  blow_surface: { role: "post", clip: "blow_sleeve" },
  clear_surface: { role: "post", clip: "press_clear" },
  create_obstacle: { role: "post", clip: "raise_both" },
  raise_terrain: { role: "post", clip: "stomp_raise" },
  lower_terrain: { role: "post", clip: "press_lower" },
  topple: { role: "post", clip: "shoulder_ram" },
  hurl_object: { role: "post", clip: "lift_throw" },
  place_trap: { role: "post", clip: "crouch_place" },
  inscribe: { role: "post", clip: "air_write" },
  detonate_runes: { role: "post", clip: "fist_clench" },
  destroy_object: { role: "post", clip: "smash_down" },
  enter_form: { role: "post", clip: "form_gather" },
  leave_form: { role: "post", clip: "form_release" },
  intercept: { role: "post", clip: "side_guard" },
  redirect_damage: { role: "post", clip: "side_guard" },
  cheat_death: { role: "post", clip: "rally_up" },
  reveal: { role: "post", clip: "shade_look" },
  copy_skill: { role: "post", clip: "snatch" },
  grant_skill: { role: "post", clip: "shoulder_tap", icon: "skill" },
  grant_ap: { role: "post", clip: "shoulder_tap", icon: "ap" },
  extra_reaction: { role: "post", clip: "shoulder_tap", icon: "reaction" },
  refund_ap: { role: "post", clip: "rewind_still", icon: "ap" },
  refund_cooldown: { role: "post", clip: "rewind_still", icon: "cooldown" },
  reset_cooldown: { role: "post", clip: "rewind_still", icon: "reset" },
  add_stack: { role: "post", clip: "stack_still", icon: "+1" },
  consume_stack: { role: "post", clip: "stack_still", icon: "-1" },
  consume_status: { role: "post", clip: "stack_still", icon: "-1" },
  gamble: { role: "post", clip: "coin_flip" },
  rule_change: { role: "post", clip: "finger_snap" },
  self_damage_of_hit: { role: "post", clip: "clutch_wound" },
};

/** 原語（`apply_status` 要帶增益／減益）→ 播法；沒有片段的原語回傳 `null`。 */
export function primitivePlay(primitive: string, polarity: "buff" | "debuff" = "debuff"): PrimitivePlay | null {
  const key = primitive === "apply_status" ? `apply_status:${polarity}` : primitive;
  return PRIMITIVE_PLAYS[key] ?? null;
}

// ---- 求值 ---------------------------------------------------------------------

const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));

/** 片段時間量化：每個片段 16 格（加上量化後的姿勢，同一個片段的貼圖最多 17 張）。 */
export const CLIP_STEPS = 16;

function keyedValue(keys: readonly (readonly [number, number])[], t: number): number {
  const first = keys[0];
  if (first === undefined) return 0;
  if (t <= first[0]) return first[1];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1]!;
    const b = keys[i]!;
    if (t <= b[0]) return a[1] + (b[1] - a[1]) * easeInOut((t - a[0]) / Math.max(1e-6, b[0] - a[0]));
  }
  return keys[keys.length - 1]![1];
}

/** 片段在時間 `t`（0～1）的姿勢（未量化）。 */
export function clipPoseRaw(id: ClipId, t: number): InkPose {
  const keys = clipDef(id).keys;
  const k = clamp(t);
  const first = keys[0]!;
  if (k <= first[0]) return { ...first[1] };
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1]!;
    const b = keys[i]!;
    if (k <= b[0]) return mixPose(a[1], b[1], easeInOut((k - a[0]) / Math.max(1e-6, b[0] - a[0])));
  }
  return { ...keys[keys.length - 1]![1] };
}

export interface ClipFrame {
  pose: InkPose;
  /** 往面向方向的位移（虛擬像素）。 */
  forward: number;
  /** 離地高度（虛擬像素）。 */
  air: number;
}

/** 片段在時間 `t` 的畫面（時間先量化成 `CLIP_STEPS` 格，姿勢再量化，貼圖快取共用）。 */
export function clipFrame(id: ClipId, t: number): ClipFrame {
  const def = clipDef(id);
  const q = Math.round(clamp(t) * CLIP_STEPS) / CLIP_STEPS;
  return {
    pose: quantizePose(frontize(clipPoseRaw(id, q))),
    forward: def.move === undefined ? 0 : keyedValue(def.move, q),
    air: def.air === undefined ? 0 : def.air * Math.sin(q * Math.PI),
  };
}

/**
 * 命中（放出）那一刻的畫面：時間不量化、正好在 `hitAt`（沒有 `hitAt` 用 0.5）。飛行物、光束的起點用它算（6N-8：
 * 技能變體只換出招的第一格，命中那一格以後照原本，所以同一招不管挑到哪個起手，起點都一樣）。
 */
export function clipHitFrame(id: ClipId): ClipFrame {
  const def = clipDef(id);
  const h = def.hitAt ?? 0.5;
  // 命中點正好是關鍵格時用那一格的值（不經過內插的浮點誤差）
  const key = def.keys.find(([t]) => t === h);
  const raw = clipPoseRaw(id, h);
  return {
    pose: quantizePose(frontize(key === undefined ? raw : { ...raw, ...key[1] })),
    forward: def.move === undefined ? 0 : keyedValue(def.move, h),
    air: def.air === undefined ? 0 : def.air * Math.sin(h * Math.PI),
  };
}

/** 收勢：從 `from` 片段最後的姿勢回到站好（`t` 0～1）。 */
export function recoverFrame(from: ClipId, t: number): ClipFrame {
  const q = Math.round(clamp(t) * CLIP_STEPS) / CLIP_STEPS;
  const end = clipPoseRaw(from, 1);
  const def = clipDef(from);
  const fwd = def.move === undefined ? 0 : keyedValue(def.move, 1);
  return { pose: quantizePose(frontize(mixPose(end, {}, easeInOut(q)))), forward: fwd * (1 - easeInOut(q)), air: 0 };
}

/**
 * 正面、背面（只吃 `armL`／`armR`）也看得出動作：主手、另一隻手往前上抬多少，換成手臂往上移多少（已有的值不覆蓋）。
 */
export function frontize(p: InkPose): InkPose {
  const out = { ...p };
  if (out.armL === undefined && p.arm !== undefined) out.armL = -3 * (1 - Math.cos(pz(p, "arm") + pz(p, "elbow") * 0.5));
  if (out.armR === undefined && p.armF !== undefined) out.armR = -3 * (1 - Math.cos(pz(p, "armF") + pz(p, "elbowF") * 0.5));
  return out;
}

// ---- 特效起點（由姿勢算出位置） ----------------------------------------------------

type P2 = readonly [number, number];
const rot = (p: P2, c: P2, a: number): [number, number] => {
  const dx = p[0] - c[0];
  const dy = p[1] - c[1];
  const cs = Math.cos(a);
  const sn = Math.sin(a);
  return [c[0] + dx * cs - dy * sn, c[1] + dx * sn + dy * cs];
};
const add = (a: P2, b: P2): [number, number] => [a[0] + b[0], a[1] + b[1]];
/** 前臂：從（已轉好的）手肘 `at` 出發，把靜止時「手肘 → 手」的向量轉 `a`。 */
const limb = (at: P2, hand: P2, elbow: P2, a: number): [number, number] => add(at, rot([hand[0] - elbow[0], hand[1] - elbow[1]], [0, 0], a));

// 關節位置照 inkDoll.ts（側面朝東；腳底 (0,0)）
const HIP: P2 = [0, -15];
const SHOULDER: P2 = [0, -31.6];
const ELBOW: P2 = [1.9, -28];
const HAND: P2 = [4.6, -24];
const SHOULDER_F: P2 = [0.6, -32.2];
const ELBOW_F: P2 = [3.2, -29.4];
const HAND_F: P2 = [5.6, -27];
const HAND_FRONT: P2 = [-9, -23.2];
/** 沒給 `wpn` 時的預設握法（側面劍；只用在算起點）。 */
const DEFAULT_WPN = 0.75;

/**
 * 姿勢下的特效起點（紙娃娃座標：腳底 (0,0)、虛擬像素；朝西已左右翻）。`len` ＝ 武器握把到作用端的距離
 * （`inkWeaponFrame.weaponFrame(...).len`；沒有武器時 0 ＝ 用手掌）。
 * 側面：髖為軸前傾 `lean`，肩→手肘→手→作用端照 `arm`、`elbow`、`wpn` 轉；正面、背面：手在 (∓9,-23.2)＋`armL`。
 */
export function anchorPoint(pose: InkPose, anchor: Anchor, facing: Facing, len: number): { x: number; y: number } {
  if (dollSkin() === "q") return anchorPointQ(pose, anchor, facing, len);
  const bob = pz(pose, "bob");
  if (anchor === "feet") return { x: 0, y: 0 };
  if (facing === "north" || facing === "south") {
    const hx = facing === "south" ? HAND_FRONT[0] : -HAND_FRONT[0];
    const main: P2 = [hx, HAND_FRONT[1] + pz(pose, "armL") + bob];
    switch (anchor) {
      case "tip":
        return { x: main[0], y: main[1] - len * 0.8 };
      case "hand":
        return { x: main[0], y: main[1] };
      case "offhand":
        return { x: -main[0], y: HAND_FRONT[1] + pz(pose, "armR") + bob };
      case "chest":
        return { x: 0, y: -27 + bob };
      case "head":
        return { x: 0, y: -48 + bob };
    }
  }
  const arm = pz(pose, "arm");
  const elbow = pz(pose, "elbow");
  const wpn = pose.wpn ?? DEFAULT_WPN;
  let p: [number, number];
  switch (anchor) {
    case "tip":
    case "hand": {
      const e = rot(ELBOW, SHOULDER, arm);
      const h = limb(e, HAND, ELBOW, arm + elbow);
      p = anchor === "hand" || len <= 0 ? h : add(h, rot([0, -len], [0, 0], arm + elbow + wpn));
      break;
    }
    case "offhand": {
      const armF = pz(pose, "armF");
      const e = rot(ELBOW_F, SHOULDER_F, armF);
      p = limb(e, HAND_F, ELBOW_F, armF + pz(pose, "elbowF"));
      break;
    }
    case "chest":
      p = [2, -27];
      break;
    case "head":
      p = [0, -48];
      break;
  }
  const leaned = rot(p, HIP, pz(pose, "lean"));
  const sx = facing === "west" ? -1 : 1;
  return { x: leaned[0] * sx, y: leaned[1] + bob };
}

/** 肩 (x,−20) 往下：肩角 sA、肘角 eA → 手（Q 版骨架，同 qCore.fk）。 */
function fkQ(x: number, sA: number, eA: number): [number, number] {
  const J = DOLL_JOINTS;
  const e: [number, number] = [x - J.upperArm * Math.sin(sA), J.shoulderSide[1] + J.upperArm * Math.cos(sA)];
  return [e[0] - J.foreArm * Math.sin(sA + eA), e[1] + J.foreArm * Math.cos(sA + eA)];
}

/**
 * Q 版的特效起點（QK-1；關節照 inkDoll.DOLL_JOINTS）：側面主手肩在肩線 (2,−20)，肩角 `arm`、肘角 min(0, arm×0.35)（同 qDoll 的 6M／6N 片段），
 * 武器角度＝ arm＋wpn；正面、背面持武器的手打直往外 armOut。上半身以髖 (0,−9) 前傾 `lean`。
 */
function anchorPointQ(pose: InkPose, anchor: Anchor, facing: Facing, len: number): { x: number; y: number } {
  const J = DOLL_JOINTS;
  const bob = pz(pose, "bob");
  if (anchor === "feet") return { x: 0, y: 0 };
  if (facing === "north" || facing === "south") {
    const s = facing === "south" ? -1 : 1;
    const h = fkQ(s * J.shoulderFront, -s * J.armOut, 0);
    const main: P2 = [h[0], h[1] + pz(pose, "armL") + bob];
    switch (anchor) {
      case "tip":
        return { x: main[0], y: main[1] - len * 0.8 };
      case "hand":
        return { x: main[0], y: main[1] };
      case "offhand":
        return { x: -main[0], y: h[1] + pz(pose, "armR") + bob };
      case "chest":
        return { x: 0, y: J.chest + bob };
      case "head":
        return { x: 0, y: J.head[1] + bob };
    }
  }
  const arm = pz(pose, "arm");
  const wpn = pose.wpn ?? DEFAULT_WPN;
  let p: [number, number];
  switch (anchor) {
    case "tip":
    case "hand": {
      const h = fkQ(J.shoulderSide[0], arm, Math.min(0, arm * 0.35));
      p = anchor === "hand" || len <= 0 ? h : add(h, rot([0, -len], [0, 0], arm + wpn));
      break;
    }
    case "offhand": {
      const armF = pz(pose, "armF");
      p = fkQ(J.shoulderSide[0], armF, Math.min(0, armF * 0.35));
      break;
    }
    case "chest":
      p = [J.shoulderSide[0], J.chest];
      break;
    case "head":
      p = [J.head[0], J.head[1]];
      break;
  }
  const leaned = rot(p, J.hip, pz(pose, "lean"));
  const sx = facing === "west" ? -1 : 1;
  return { x: leaned[0] * sx, y: leaned[1] + bob };
}
