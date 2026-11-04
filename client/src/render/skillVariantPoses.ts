// 技能變體的片段資料（Phase 6N-8；方案 docs/art/動畫方案.md 2.11，需求 docs/art/動畫移植需求第二批.md 第 7 節）。
// 起手層（詠唱、施法起手、蓄力）與原語層（召喚法陣、治療增益）的「衍生片段」：由原本的片段改關鍵姿勢或特效，
// **長度（ms）、命中點（hitAt）、作用端（anchor）、位移、出招命中那一格之後的關鍵姿勢一律照原本**，所以時間軸、
// 飛行物起點、落點都不變。挑哪一個在 `skillVariants.ts`；衍生片段的 ID 是「原本的 ID~標籤」（`clipDef` 照標籤算、快取）。
// 全部是資料＋純函式：不用 Math.random()、不讀時鐘。
// 座標照 skillClips.ts：側面朝東，`arm` 負＝往前上抬；武器絕對角度 ＝ arm ＋ elbow ＋ wpn（0 作用端朝上、π/2 朝前）。
import { mixPose, type InkPose } from "./inkPose";
import type { ClipDef, FxCue, FxKind } from "./skillClips";

type Key = readonly [number, InkPose];
const fx = (kind: FxKind, where: FxCue["where"], from = 0, to = 1): FxCue => ({ kind, where, from, to });

/**
 * 起手層的一個變體：
 * - `replace`：蓄力片段第一格（站好）之後的關鍵姿勢換成 `keys`（每一格先疊在原本蓄力最後的姿勢上）；
 * - `overlay`：原本的每一格都疊上 `pose`（時間 0 不疊、0.6 以後全疊），主手的動作照原本、只改身體或另一隻手；
 * - `keys`／`pose` 都沒有 ＝ 原本的樣子（第一個變體）。
 * `fx` 有給時換掉蓄力片段的特效。出招片段只換第一格（＝蓄力最後一格），命中那一格之後照原本。
 */
export interface PoseVariant {
  id: string;
  zh: string;
  keys?: readonly Key[];
  pose?: InkPose;
  fx?: readonly FxCue[];
}

// ---- 起手：法器的詠唱（5） -------------------------------------------------------

/** 法杖的詠唱（作用端 ＝ 杖頭）。第一個 ＝ 起手對照表原本的「舉杖（腳下法陣）」。 */
export const STAFF_CHANTS: readonly PoseVariant[] = [
  { id: "raise", zh: "舉杖（腳下法陣）" },
  {
    id: "front_circle",
    zh: "身前畫陣",
    keys: [
      [0.35, { arm: -1.0, elbow: -1.1, wpn: 3.5, armF: -1.1, elbowF: -0.9, lean: -0.04 }],
      [0.7, { arm: -1.25, elbow: -0.85, wpn: 3.95, armF: -0.9, elbowF: -1.1, lean: -0.02, bob: -0.4 }],
      [1, { arm: -1.0, elbow: -1.1, wpn: 3.45, armF: -1.1, elbowF: -0.9, lean: -0.04 }],
    ],
    fx: [fx("sigil", "anchor", 0.2, 1)],
  },
  {
    id: "stamp_swirl",
    zh: "頓地捲火",
    keys: [
      [0.35, { arm: -0.5, wpn: 0.5, bob: 1.4, lean: 0.06 }],
      [0.55, { arm: -0.5, wpn: 0.5, bob: 1.0, lean: 0.04 }],
      [1, { arm: -2.4, wpn: 2.6, lean: -0.08, bob: -0.8 }],
    ],
    fx: [fx("quake", "feet", 0.3, 0.7), fx("gust", "feet", 0.4, 1)],
  },
  {
    id: "one_hand_seal",
    zh: "單手結印",
    keys: [
      [0.6, { arm: -0.6, wpn: 1.2, armF: -1.2, elbowF: -1.7, lean: -0.04, bob: -0.6 }],
      [1, { arm: -0.6, wpn: 1.2, armF: -1.25, elbowF: -1.75, lean: -0.04, bob: -0.2 }],
    ],
    fx: [fx("glow", "anchor", 0.3, 1), fx("motesIn", "feet", 0.2, 1)],
  },
  {
    id: "palms",
    zh: "雙手合十",
    keys: [
      [0.6, { arm: -0.9, elbow: -1.3, wpn: 2.2, armF: -0.9, elbowF: -1.3, lean: -0.05, bob: -0.6 }],
      [1, { arm: -0.9, elbow: -1.3, wpn: 2.2, armF: -0.9, elbowF: -1.3, lean: -0.05, bob: -0.3 }],
    ],
    fx: [fx("motesIn", "feet", 0.1, 1), fx("glow", "anchor", 0.5, 1)],
  },
];

/** 法球的詠唱（作用端 ＝ 拿法球的另一隻手）；名稱和法杖同一組。 */
export const ORB_CHANTS: readonly PoseVariant[] = [
  { id: "raise", zh: "舉杖（腳下法陣）" },
  {
    id: "front_circle",
    zh: "身前畫陣",
    keys: [
      [0.35, { armF: -1.2, elbowF: -0.8, arm: -1.0, elbow: -1.0, lean: -0.04 }],
      [0.7, { armF: -1.45, elbowF: -0.5, arm: -0.8, elbow: -1.2, lean: -0.02, bob: -0.4 }],
      [1, { armF: -1.2, elbowF: -0.8, arm: -1.0, elbow: -1.0, lean: -0.04 }],
    ],
    fx: [fx("sigil", "anchor", 0.2, 1)],
  },
  {
    id: "stamp_swirl",
    zh: "頓地捲火",
    keys: [
      [0.35, { armF: -0.4, elbowF: 0, bob: 1.4, lean: 0.08 }],
      [0.55, { armF: -0.4, elbowF: 0, bob: 1.0, lean: 0.05 }],
      [1, { armF: -2.4, elbowF: -0.2, lean: -0.08, bob: -0.8 }],
    ],
    fx: [fx("quake", "feet", 0.3, 0.7), fx("gust", "feet", 0.4, 1)],
  },
  {
    id: "one_hand_seal",
    zh: "單手結印",
    keys: [
      [0.6, { arm: -1.2, elbow: -1.7, armF: -0.8, elbowF: -0.6, lean: -0.04, bob: -0.6 }],
      [1, { arm: -1.25, elbow: -1.75, armF: -0.8, elbowF: -0.6, lean: -0.04, bob: -0.2 }],
    ],
    fx: [fx("glow", "anchor", 0.3, 1), fx("motesIn", "feet", 0.2, 1)],
  },
  {
    id: "palms",
    zh: "雙手合十",
    keys: [
      [0.6, { arm: -0.9, elbow: -1.3, armF: -0.9, elbowF: -1.3, lean: -0.05, bob: -0.6 }],
      [1, { arm: -0.9, elbow: -1.3, armF: -0.9, elbowF: -1.3, lean: -0.05, bob: -0.3 }],
    ],
    fx: [fx("motesIn", "feet", 0.1, 1), fx("glow", "anchor", 0.5, 1)],
  },
];

// ---- 起手：其他武器的施法起手（3）、蓄力姿勢（3） ---------------------------------

/** 非法器的施法起手（飛行物、自身、地面）：主手照起手對照表，只改另一隻手與身體。第一個 ＝ 原本的。 */
export const CAST_OPENERS: readonly PoseVariant[] = [
  { id: "table", zh: "照起手對照表" },
  { id: "off_seal", zh: "副手結印", pose: { armF: -1.3, elbowF: -1.6, lean: -0.06, bob: -0.5 }, fx: [fx("glow", "anchor", 0.3, 1), fx("motesIn", "feet", 0.2, 1)] },
  { id: "side_coil", zh: "側身蓄勢", pose: { lean: -0.18, hipN: -0.2, hipF: 0.3, armF: 0.45, elbowF: -0.4, kneeN: 0.3, bob: 0.8 } },
];

/** 近身技能的蓄力（方案 2.11：收在腰側、舉過頭、壓低前傾）。三個都改主手，所以沒有「原本的」。 */
export const CHARGE_POSES: readonly PoseVariant[] = [
  { id: "waist", zh: "收在腰側", pose: { arm: 0.6, elbow: -0.9, wpn: -2.2, lean: 0.08, kneeN: 0.4, kneeF: 0.3, bob: 1.2 } },
  { id: "overhead", zh: "舉過頭", pose: { arm: -2.7, elbow: -0.2, wpn: 1.7, lean: -0.12, hipN: 0.25, hipF: -0.2, bob: -0.4 } },
  { id: "low_lean", zh: "壓低前傾", pose: { arm: 0.25, elbow: -0.3, wpn: 1.3, lean: 0.24, kneeN: 0.7, kneeF: 0.6, hipN: 0.4, bob: 2.6 } },
];

// ---- 原語：召喚法陣（3）、治療增益（3） ------------------------------------------

/** 召喚法陣：只換特效（身體照原本的雙手下壓）。第一個 ＝ 原本的「地面亮起」。 */
export const SUMMON_CIRCLES: readonly PoseVariant[] = [
  { id: "ground", zh: "地面亮起" },
  { id: "sky", zh: "從天而降", fx: [fx("pillar", "targetFeet", 0.35, 1), fx("motesDown", "targetFeet", 0.4, 1), fx("circle", "targetFeet", 0.7, 1)] },
  { id: "smoke", zh: "從煙霧裡浮現", fx: [fx("smoke", "targetFeet", 0.3, 1), fx("motesUp", "targetFeet", 0.6, 1)] },
];

/** 治療、增益的光：目標身上那一道換成這三種之一（身體照原本）。 */
export const HEAL_STYLES: ReadonlyArray<{ id: string; zh: string; kind: FxKind }> = [
  { id: "motes", zh: "光點上飄", kind: "motesUp" },
  { id: "ring", zh: "光環收束", kind: "ringUp" },
  { id: "petals", zh: "花瓣散落", kind: "petals" },
];
/** 治療、增益片段裡會被換掉的那一道光（目標身上的光點或光環）。 */
const HEAL_CUES: ReadonlySet<FxKind> = new Set<FxKind>(["motesUp", "ringUp", "petals"]);

// ---- 衍生 -------------------------------------------------------------------------

/** 衍生片段的標籤 → 用哪一組。`chant_s` 法杖、`chant_o` 法球。 */
const POSE_SETS: Readonly<Record<string, readonly PoseVariant[]>> = {
  chant_s: STAFF_CHANTS,
  chant_o: ORB_CHANTS,
  cast: CAST_OPENERS,
  charge: CHARGE_POSES,
  summon: SUMMON_CIRCLES,
};

/** 標籤（例如 `chant_s3`）拆成組名與第幾個；不認得回傳 `null`。 */
export function parseTag(tag: string): { set: string; index: number } | null {
  const m = /^([a-z_]+?)(\d+)$/.exec(tag);
  if (m === null) return null;
  const set = m[1]!;
  const index = Number(m[2]);
  if (set === "heal") return index < HEAL_STYLES.length ? { set, index } : null;
  const list = POSE_SETS[set];
  return list === undefined || index >= list.length ? null : { set, index };
}

const lastPose = (keys: readonly Key[]): InkPose => keys[keys.length - 1]![1];

/** 片段第一格之後的每一格都有 `wpn`（武器角度）；有一格沒有 ＝ 那一格是預設握法，衍生時不碰 `wpn`。 */
function keepsWpn(base: ClipDef): boolean {
  return base.keys.slice(1).every(([, p]) => p.wpn !== undefined);
}

function withoutWpn(p: InkPose): InkPose {
  const { wpn: _wpn, ...rest } = p;
  return rest;
}

/** 蓄力片段的衍生（沒有命中點的片段）。 */
function deriveWindup(base: ClipDef, v: PoseVariant): ClipDef {
  const end = lastPose(base.keys);
  const own = keepsWpn(base) ? (p: InkPose) => p : withoutWpn;
  let keys: readonly Key[] = base.keys;
  if (v.keys !== undefined) keys = [[0, base.keys[0]![1]], ...v.keys.map(([t, p]): Key => [t, { ...end, ...own(p) }])];
  else if (v.pose !== undefined) {
    const over = own(v.pose);
    keys = base.keys.map(([t, p]): Key => (t <= 0 ? [t, p] : t >= 0.6 ? [t, { ...p, ...over }] : [t, mixPose(p, { ...p, ...over }, t / 0.6)]));
  }
  return { ...base, keys, ...(v.fx === undefined ? {} : { fx: v.fx }) };
}

/** 出招片段的衍生：只換第一格（接上衍生蓄力的最後一格），命中那一格之後照原本。 */
function deriveStrike(base: ClipDef, v: PoseVariant): ClipDef {
  const first = base.keys[0]![1];
  const joint: InkPose = v.keys !== undefined ? { ...first, ...lastPose(v.keys) } : v.pose !== undefined ? { ...first, ...v.pose } : first;
  // 後面的格子沒給 `wpn`（＝ 預設握法，不是一個固定角度）時，第一格的 `wpn` 照原本，命中那一格的武器角度才和原本一樣
  if (!keepsWpn(base)) {
    if (first.wpn === undefined) delete joint.wpn;
    else joint.wpn = first.wpn;
  }
  return { ...base, keys: [[0, joint], ...base.keys.slice(1)] };
}

/** 治療、增益：目標身上那一道光換成第 `index` 種。 */
function deriveHeal(base: ClipDef, index: number): ClipDef {
  const kind = HEAL_STYLES[index]!.kind;
  return { ...base, fx: (base.fx ?? []).map((c) => (HEAL_CUES.has(c.kind) ? { ...c, kind } : c)) };
}

/**
 * 原本的片段＋標籤 → 衍生片段。蓄力（沒有 `hitAt`）改關鍵姿勢與特效；出招（有 `hitAt`）只換第一格；
 * 召喚只換特效；治療增益只換目標身上那一道光。長度、命中點、作用端、位移一律照原本。不認得的標籤回傳 `null`。
 */
export function deriveClip(base: ClipDef, tag: string): ClipDef | null {
  const t = parseTag(tag);
  if (t === null) return null;
  if (t.set === "heal") return deriveHeal(base, t.index);
  const v = POSE_SETS[t.set]![t.index]!;
  if (t.set === "summon") return v.fx === undefined ? base : { ...base, fx: v.fx };
  return base.hitAt === undefined ? deriveWindup(base, v) : deriveStrike(base, v);
}

/** 治療、增益片段原本用的是第幾種光（沒有可換的光回傳 `null`）。 */
export function healStyleOf(base: ClipDef): number | null {
  const c = (base.fx ?? []).find((x) => HEAL_CUES.has(x.kind));
  return c === undefined ? null : HEAL_STYLES.findIndex((s) => s.kind === c.kind);
}
