// 異形敵人的 4 個通用動畫片段（Phase 6M-2；需求 docs/archive/art/動畫移植需求.md 第 1 節第 5 點、動畫方案.md 第 2.1 節）：走、撲、受擊、倒下。
// 不拆關節：整隻身體以腳底 (0,0) 為準伸縮（sx、sy）、傾斜（rot，順時針為正＝頭往下）、位移（dx、dy，往前＝+x、往上＝-y），
// 再加上透明度 alpha 與受擊白閃 flash（白閃由呼叫端疊，drawCreature 不畫）。地上的影子不跟著動。
// 確定性：每個片段都是時間的純函式（t 0→1，或毫秒），不用 Math.random()。
import type { Ctx } from "./artDraw";
import type { Pt } from "./inkStyle";

/** 一格異形姿勢；每個欄位都可省略（＝不變）。 */
export interface CreaturePose {
  dx?: number;
  dy?: number;
  /** 橫向、縱向伸縮（以腳底為準；1 ＝ 不變）。 */
  sx?: number;
  sy?: number;
  /** 以腳底為軸傾斜（弧度，順時針為正：朝東時頭往下）。 */
  rot?: number;
  /** 不透明度（0～1，乘在現有透明度上）。 */
  alpha?: number;
  /** 受擊白閃強度（0～1）；資料欄位，由戰場在貼圖上疊白色。 */
  flash?: number;
  /**
   * QK-4：Q 版分部件片段（`idle`、`move`、`hit`、`death`、`atk:<id>`；頭目 `boss:<片段>`）。有值時部件依 qCreatureAnim 的掛點動，
   * 上面的整隻欄位（伸縮、傾斜、透明）再疊在外面（跳躍的拉長、壓扁）。
   */
  clip?: string;
  /** 片段的進度（0～1，已量化成格：循環 8 格、單次 12 格／秒）。 */
  u?: number;
  /** 樣張頁用：連飛向目標的特效也畫進貼圖（戰場上由技能特效畫，預設不畫）。 */
  fxAll?: boolean;
  /** QK-4b：鳥起飛／落地過場（移動片段往待機落地姿勢內插；1＝落地、0＝飛行；只有 qCreatureAnim.PERCHERS 用）。 */
  perch?: number;
  /** 樣張頁的減少動態對照（戰場的減少動態由 reducedMotion 跳最後一格）。 */
  reduce?: boolean;
  /** CB-2b：引擎已經把身體位移過去，片段的整隻前衝（root dx）歸零，其餘（蹲伏、騰空、四肢）照播。 */
  inPlace?: boolean;
}

export type CreatureClipId = "walk" | "pounce" | "hit" | "fall";

export interface CreatureClip {
  /** 基本長度（毫秒），之後乘上播放速度。 */
  dur: number;
  /** 循環播放（走）；否則播完停在最後一格。 */
  loop: boolean;
  /** t（0→1）→ 姿勢。 */
  pose: (t: number, opt?: CreatureClipOpt) => CreaturePose;
}

export interface CreatureClipOpt {
  /** 舊參數（6M-2 浮空身形上下飄）；QK-4 起每款身形自己的移動片段已處理，留著相容。 */
  hover?: boolean;
}

const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, Number.isFinite(v) ? v : 0));

/** QK-4 片段的格數（同 qCreatureAnim：循環 8 格；受擊 400 毫秒＝5 格、倒下 1000 毫秒＝12 格、攻擊約 12 格／秒）。 */
const CLIP_FRAMES = { move: 8, hit: 5, death: 12, atk: 12 } as const;
const loopU = (t: number, n: number): number => (((Math.floor(clamp(t) * n) % n) + n) % n) / n;
const onceU = (t: number, n: number): number => Math.round(clamp(t) * (n - 1)) / (n - 1);

/** 攻擊的動作類型（QK-4，qCreatureAnim.AttackType 同一組）：依技能的特效類型挑每款身形的攻擊片段。 */
export type CreatureAttackType = "melee" | "charge" | "breath" | "cast" | "area" | "summon" | "blink";

/** 攻擊片段的這一格：`atk:@<類型>`，畫的時候依身形挑該類型的攻擊（沒有那個類型就退回普攻）。 */
export function creatureStrikePose(type: CreatureAttackType, t: number): CreaturePose {
  return { clip: `atk:@${type}`, u: onceU(t, CLIP_FRAMES.atk) };
}

/**
 * QK-4：4 個通用片段改成 Q 版分部件片段的引用（`clip`＋量化過的 `u`）：走＝每款身形的移動、撲＝普攻、受擊、倒下。
 * 實際的部件動作在 qCreatureAnim（依身形）；這裡只決定片段與格。
 */
export const CREATURE_CLIPS: Readonly<Record<CreatureClipId, CreatureClip>> = {
  walk: { dur: 900, loop: true, pose: (t) => ({ clip: "move", u: loopU(t, CLIP_FRAMES.move) }) },
  pounce: { dur: 760, loop: false, pose: (t) => creatureStrikePose("melee", t) },
  hit: {
    dur: 400,
    loop: false,
    pose: (t) => {
      const u = onceU(t, CLIP_FRAMES.hit);
      return u < 0.2 ? { clip: "hit", u, flash: 0.9 } : { clip: "hit", u }; // 白閃也寫在整隻欄位（同 qCreatureAnim 受擊的前 20%）
    },
  },
  fall: { dur: 1000, loop: false, pose: (t) => ({ clip: "death", u: onceU(t, CLIP_FRAMES.death) }) },
};

export const CREATURE_CLIP_IDS: readonly CreatureClipId[] = ["walk", "pounce", "hit", "fall"];

/** 某片段播到第 `ms` 毫秒的姿勢（循環片段取餘數；其他停在最後一格）。 */
export function creaturePoseAt(id: CreatureClipId, ms: number, opt: CreatureClipOpt = {}): CreaturePose {
  const c = CREATURE_CLIPS[id];
  const t = c.loop ? (((ms % c.dur) + c.dur) % c.dur) / c.dur : clamp(ms / c.dur);
  return c.pose(t, opt);
}

// QK-4b：鳥（qCreatureAnim.PERCHERS）待機落地、移動在空中：起飛／落地過場
/** 過場的長度（毫秒，約 4 格 × 83）。 */
export const PERCH_MS = 333;
/** 移動開頭（elapsed 從起飛算）、結尾（remain 到落地）的落地比例，量化到 4 格（1、0.75、0.5、0.25、0）。 */
export function perchAt(elapsedMs: number, remainMs: number | null): number {
  const a = elapsedMs < PERCH_MS ? 1 - Math.max(0, elapsedMs) / PERCH_MS : 0;
  const b = remainMs !== null && remainMs < PERCH_MS ? 1 - Math.max(0, remainMs) / PERCH_MS : 0;
  return Math.max(0, Math.ceil(Math.max(a, b) * 4 - 1e-9) / 4);
}
/** CB-2c：鳥攻擊前的起飛（`up`）、攻擊後的落地（`down`）過場。 */
export type PerchRow = "up" | "down";
/** 過場這一列播到 `t`（0～1）的落地比例：同移動的 4 格（起飛 1、0.75、0.5、0.25；落地 0.25、0.5、0.75、1）。 */
export function perchRowLevel(kind: PerchRow, t: number): number {
  const ms = clamp(t) * PERCH_MS;
  return kind === "up" ? perchAt(ms, null) : perchAt(PERCH_MS * 9, PERCH_MS - ms);
}
/** 過場這一列的姿勢：起飛接攻擊片段第一格、落地從攻擊片段最後一格開始（銜接處不跳），往待機的落地姿勢內插。 */
export function perchRowPose(kind: PerchRow, type: CreatureAttackType, t: number): CreaturePose {
  return { ...creatureStrikePose(type, kind === "up" ? 0 : 1), perch: perchRowLevel(kind, t) };
}
/** 讀欄位；沒給或不是有限數字 → 預設。 */
type NumKey = "dx" | "dy" | "sx" | "sy" | "rot" | "alpha" | "flash" | "u";
export function cp(p: CreaturePose, k: NumKey): number {
  const v = p[k];
  const def = k === "sx" || k === "sy" || k === "alpha" ? 1 : 0;
  return typeof v === "number" && Number.isFinite(v) ? v : def;
}

/** 套上姿勢（呼叫端已 save）：位移 → 以腳底為軸傾斜 → 伸縮 → 透明度。值是預設時不加指令。 */
export function applyCreaturePose(ctx: Ctx, p: CreaturePose): void {
  const dx = cp(p, "dx");
  const dy = cp(p, "dy");
  if (dx !== 0 || dy !== 0) ctx.translate(dx, dy);
  const rot = cp(p, "rot");
  if (rot !== 0) ctx.rotate(rot);
  const sx = cp(p, "sx");
  const sy = cp(p, "sy");
  if (sx !== 1 || sy !== 1) ctx.scale(sx, sy);
  const a = clamp(cp(p, "alpha"));
  if (a !== 1) ctx.globalAlpha = (typeof ctx.globalAlpha === "number" ? ctx.globalAlpha : 1) * a;
}

const POSE_FIELDS: ReadonlyArray<"dx" | "dy" | "sx" | "sy" | "rot" | "alpha" | "flash"> = ["dx", "dy", "sx", "sy", "rot", "alpha", "flash"];
const q2 = (v: number): number => Number((Math.round(v / 0.02) * 0.02 + 0).toFixed(2));

/** 量化異形姿勢（每個欄位到 0.02；6M-3 貼圖快取用）。 */
export function quantizeCreaturePose(p: CreaturePose): CreaturePose {
  const out: CreaturePose = {};
  for (const k of POSE_FIELDS) if (p[k] !== undefined) out[k] = q2(cp(p, k));
  if (p.clip !== undefined) {
    out.clip = p.clip;
    out.u = cp(p, "u");
  }
  if (p.fxAll === true) out.fxAll = true;
  if (p.reduce === true) out.reduce = true;
  if (p.perch !== undefined && p.perch > 0) out.perch = q2(p.perch);
  if (p.inPlace === true) out.inPlace = true;
  return out;
}

/** 異形姿勢的快取鍵（固定欄位順序、量化到 0.02；預設值不寫）。 */
export function creaturePoseKey(p: CreaturePose): string {
  const out: string[] = [];
  for (const k of POSE_FIELDS) {
    const v = q2(cp(p, k));
    const def = k === "sx" || k === "sy" || k === "alpha" ? 1 : 0;
    if (v !== def) out.push(`${k}${v}`);
  }
  if (p.clip !== undefined) out.push(`${p.clip}@${cp(p, "u").toFixed(4)}`);
  if (p.fxAll === true) out.push("fxall");
  if (p.reduce === true) out.push("reduce");
  if (p.perch !== undefined && p.perch > 0) out.push(`perch${q2(p.perch)}`);
  if (p.inPlace === true) out.push("inplace");
  return out.join(",");
}

/**
 * 6R-F（前端審查第 9 點）：把姿勢的位移拆出來。貼圖只畫伸縮、傾斜、透明度、白閃（鍵不含 dx、dy，同一個伸縮共用一張），
 * 位移由戰場移動小人的節點（`unitSprite.placeCreatureBody`），畫面和原本把位移畫進貼圖一樣。
 */
export function splitCreatureOffset(p: CreaturePose): { pose: CreaturePose; dx: number; dy: number } {
  const { dx: _dx, dy: _dy, ...rest } = p;
  return { pose: rest, dx: cp(p, "dx"), dy: cp(p, "dy") };
}

/**
 * 受擊白閃（6M-3，6M-2 驗收第 3 點）：只閃角色的剪影，不能整格變白。照樣張 `filter: brightness(0) invert(1) opacity(f)`：
 * 把（不含地上影子的）身體像素變成白色、不透明度乘 `flash`（0～1），再疊回角色上。剪影外（透明）的像素維持透明。
 * `data` 是 RGBA（ImageData.data），原地修改。
 */
export function whiteSilhouette(data: Uint8ClampedArray, flash: number): void {
  const f = clamp(flash);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = 255;
    data[i + 1] = 255;
    data[i + 2] = 255;
    data[i + 3] = Math.round(data[i + 3]! * f);
  }
}

// ============================== QK-4：Q 版異形的分部件姿勢（qCreatureAnim.ts 產生、inkCreature.ts 畫） ==============================

/** 一個部件組（或整隻 root）的變換：以支點為準位移、旋轉、斜切、縮放、透明。 */
export interface PartXf {
  rot?: number;
  dx?: number;
  dy?: number;
  kx?: number;
  sx?: number;
  sy?: number;
  a?: number;
  pivot?: readonly [number, number];
}

/** 動畫特效（地面座標，跟著朝向鏡像）：塵土、環、光暈、吐息、飛行物…（qCreatureAnim.drawFx 畫）。 */
export interface CreatureFx {
  k: "dust" | "ring" | "glow" | "cone" | "wave" | "puff" | "orb" | "burst" | "bolt" | "beam" | "slash" | "chomp" | "shard" | "egg" | "flame" | "blob" | "rock";
  x?: number;
  y?: number;
  r?: number;
  rx?: number;
  ry?: number;
  c?: string;
  c2?: string;
  a?: number;
  w?: number;
  tail?: number;
  rot?: number;
  s?: number;
  q?: number;
  len?: number;
  ang?: number;
  max?: number;
  spread?: number;
  t?: number;
  x0?: number;
  y0?: number;
  x1?: number;
  y1?: number;
  amp?: number;
  h?: number;
  crack?: boolean;
  rim?: string;
  /** 飛向目標格（飛行物、命中爆開、射線、雷）：戰場上由技能特效畫，貼圖不畫（樣張頁照畫）。 */
  ranged?: boolean;
  /** CB-2c：蛋（拋物線到指定格）：戰場上由 `eggArc` 畫，貼圖不畫（樣張頁照畫）；不算出手格（`ranged` 會把出手格提早到飛出那一格）。 */
  lobbed?: boolean;
}

/** 一格分部件姿勢（照樣張 qCreatureAnim.js 的 pose 物件）。 */
export interface QPartPose {
  root: PartXf;
  parts: Record<string, PartXf>;
  flash: number;
  flashColor?: string;
  alpha: number;
  shadow: number;
  fx: CreatureFx[];
  limbRim?: boolean;
  softGround?: boolean;
  /** QK-4b：倒下閉眼（眼睛畫成深色 ×；四足獸倒下）。 */
  eyeShut?: boolean;
  /** QK-4b：同一組畫好幾次，每次只畫 clip 多邊形裡的那一塊、各自位移旋轉（傀儡崩塌斷成幾塊）。 */
  split?: Record<string, SplitPiece[]>;
}
/** 斷塊：clip 多邊形（部件座標）、繞 pivot 位移旋轉。 */
export interface SplitPiece {
  clip: readonly Pt[];
  pivot?: Pt;
  dx?: number;
  dy?: number;
  rot?: number;
}

const BASE = (clip: string): string => clip.split("~")[0] ?? clip;
const TYPE_BY_CLIP: ReadonlyArray<readonly [CreatureAttackType, readonly string[]]> = [
  ["charge", ["dash", "charge_through", "leap", "dash_lean", "shoulder_charge", "leap_air", "shoulder_ram"]],
  ["summon", ["summon", "summon_press"]],
  ["blink", ["teleport", "shadowstep", "swap", "swap_any", "teleport_target", "warp_pose", "smoke_step", "swap_pose"]],
  ["area", ["shockwave", "zone", "aura_pulse", "ground_punch", "stab_ground", "stab_ground_in", "stomp", "stomp_raise", "staff_stamp", "palm_ground", "zone_stamp", "butt_stamp", "create_surface"]],
  ["breath", ["blow_surface", "blow_sleeve"]],
];

/**
 * QK-4：技能片段（人形的片段 ID）＋到目標的距離 → 異形攻擊的動作類型。衝鋒、召喚、位移、範圍、吐息照片段；
 * 其他：目標是自己（距離 0）＝範圍、超過 1 格＝遠程施放、相鄰＝普攻。
 */
export function creatureAttackTypeOf(clip: string, dist: number | null): CreatureAttackType {
  const base = BASE(clip);
  for (const [t, ids] of TYPE_BY_CLIP) if (ids.includes(base)) return t;
  if (dist === 0) return "area";
  if (dist !== null && dist > 1) return "cast";
  return "melee";
}
