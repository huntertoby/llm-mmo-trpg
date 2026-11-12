// 移動片段（Phase 6M-3；需求 docs/archive/art/動畫移植需求.md 第 2、3 節，公式照樣張 docs/art/sample/anim.js 的 walkPose、heightRow）。
// 全部是純函式：時間（或走過的格數）→ 紙娃娃姿勢（inkPose.ts）／異形姿勢（creaturePose.ts）。不用 Math.random()、不讀時間。
// - 走路、跑步、潛行：一個循環 2π ＝ 兩步；走路一步約 0.45 秒，跑步快 1.6 倍，潛行慢到 0.6 倍。
// - 戰場與探索逐格走時，相位跟著走過的格數走（一格一步，腳步不打滑），每格的時間照 6A-4d（`TILE_STEP_MS`）。
// - 高低差（`TILE_SIZE` 48、每級 `RAISE` 6）：差一級用走的（上：前半段抬腳、後半段身體升；下：後半段身體降、落地多起伏 1），
//   差兩級以上用跳的（最高點從起點、落點中較高的一端往上量 14 ＋ 級差 × 6，往下跳 0.7 倍；落地揚塵；6R-1c）。
// - 快取：姿勢量化（相位每 1/16 循環、數值到 0.02）之後才放進貼圖快取鍵（`poseKey`），同一個姿勢共用一張貼圖。
import { RAISE } from "../battle/elevation";
import type { Facing } from "../api/types";
import type { Gait } from "../battle/walkAnim";
import { CREATURE_CLIPS, type CreaturePose } from "./creaturePose";
import { POSE_KEYS, pz, type InkPose } from "./inkPose";

export type { Gait };

export interface GaitSpec {
  /** 一步的時間（毫秒；一個循環兩步）。 */
  stepMs: number;
  /** 側面髖的擺幅（弧度）。 */
  amp: number;
  /** 起伏（虛擬像素）。 */
  bob: number;
  /** 整個人的不透明度（潛行半透明）。 */
  alpha: number;
}

/** 走路一步約 0.45 秒；跑步速度約 1.6 倍；潛行約 0.6 倍、半透明（照隱匿的透明度 0.55）。 */
export const GAITS: Readonly<Record<Gait, GaitSpec>> = {
  walk: { stepMs: 450, amp: 0.5, bob: 1.2, alpha: 1 },
  run: { stepMs: 450 / 1.6, amp: 0.75, bob: 2.2, alpha: 1 },
  sneak: { stepMs: 450 / 0.6, amp: 0.35, bob: 1.2, alpha: 0.55 },
};

const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
const mix = (a: number, b: number, t: number): number => a + (b - a) * t;
const TAU = Math.PI * 2;

/** 緩入緩出（二次；同 walkAnim 的 easeInOut）。 */
export function easeInOut(t: number): number {
  const k = clamp(t);
  return k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
}

/**
 * 走路循環在相位 `phase`（弧度，2π ＝ 兩步）的姿勢。樣張 walkPose：側面髖 ±amp、膝在後擺時彎、手臂反向擺、起伏；
 * 正面、背面左右腳交替抬 3.2、手上下擺 1.6。跑步：前傾 0.2、手肘彎；潛行：蹲低 2.5、前傾 0.3、膝多彎 0.5。
 * 另一隻手（6M-1 新增的 `armF`）和主手反向擺。
 */
export function gaitPose(phase: number, gait: Gait = "walk"): InkPose {
  const g = GAITS[gait];
  const sn = Math.sin(phase);
  const p: InkPose = {
    hipN: g.amp * sn,
    hipF: -g.amp * sn,
    kneeN: 0.9 * Math.max(0, -Math.sin(phase + 0.9)),
    kneeF: 0.9 * Math.max(0, Math.sin(phase + 0.9)),
    arm: -0.35 * sn,
    armF: 0.35 * sn,
    bob: -Math.abs(Math.cos(phase)) * g.bob,
    liftL: 3.2 * Math.max(0, sn),
    liftR: 3.2 * Math.max(0, -sn),
    armL: 1.6 * sn,
    armR: -1.6 * sn,
  };
  if (gait === "run") return { ...p, lean: 0.2, arm: -0.6 * sn - 0.3, elbow: -0.9, armF: 0.6 * sn - 0.3, elbowF: -0.9 };
  if (gait === "sneak") return { ...p, lean: 0.3, bob: pz(p, "bob") + 2.5, kneeN: pz(p, "kneeN") + 0.5, kneeF: pz(p, "kneeF") + 0.5, arm: -0.6, elbow: -0.5 };
  return p;
}

/** 片段播到第 `ms` 毫秒的相位（時間的純函式；每步 `stepMs`）。 */
export function gaitPhaseAt(gait: Gait, ms: number): number {
  return (ms / GAITS[gait].stepMs) * Math.PI;
}

/** 片段播到第 `ms` 毫秒的姿勢（循環：週期 ＝ 兩步）。 */
export function gaitPoseAt(gait: Gait, ms: number): InkPose {
  return gaitPose(gaitPhaseAt(gait, ms), gait);
}

/** 逐格走：第 `tile` 格（0 起）走到 `u`（0～1）時的相位；一格一步。 */
export function tilePhase(tile: number, u: number): number {
  return (tile + clamp(u)) * Math.PI;
}

/** 相位量化的級數（每個循環）：16 ＝ 每步 8 張貼圖。 */
export const PHASE_STEPS = 16;

/** 相位量化到每循環 `PHASE_STEPS` 級（貼圖快取用；動起來看不出差別）。 */
export function quantizePhase(phase: number): number {
  const step = TAU / PHASE_STEPS;
  return Math.round(phase / step) * step;
}

/** 姿勢數值量化的單位（弧度與虛擬像素共用）。 */
export const POSE_QUANT = 0.02;

/** 量化姿勢（每個欄位四捨五入到 `POSE_QUANT`；`wpn` 沒給時維持沒給）。 */
export function quantizePose(p: InkPose): InkPose {
  const out: InkPose = {};
  for (const k of POSE_KEYS) {
    const v = p[k];
    if (typeof v !== "number" || !Number.isFinite(v)) continue;
    const q = Math.round(v / POSE_QUANT) * POSE_QUANT + 0; // +0：不要 -0
    out[k] = Number(q.toFixed(2));
  }
  return out;
}

/** 姿勢的快取鍵（固定欄位順序；值是 0 的欄位不寫）。 */
export function poseKey(p: InkPose): string {
  const q = quantizePose(p);
  return POSE_KEYS.filter((k) => q[k] !== undefined && (k === "wpn" || q[k] !== 0))
    .map((k) => `${k}${q[k]}`)
    .join(",");
}

// ---- 高低差 ------------------------------------------------------------------

/** 跳躍拋物線的基本高度（虛擬像素＝模型像素）。 */
export const JUMP_BASE = 14;
/** 往下跳的弧度倍率。 */
export const JUMP_DOWN = 0.7;
/** 差一級時身體在這一格的後半段才升降（u 從這裡開始）。 */
export const STEP_RISE_FROM = 0.4;
/** 落地揚塵從這裡開始（u）。 */
export const DUST_FROM = 0.85;

/**
 * 跳躍最高點高過「起點、落點中較高的一端」多少模型像素（6R-1c，美術 PM 11-06：代決 #24「14＋級差×6」
 * 從較高的一端往上量；往下跳 0.7 倍）。同高時 ＝ `JUMP_BASE`。
 */
export function jumpRise(fromH: number, toH: number): number {
  const diff = toH - fromH;
  return (JUMP_BASE + Math.abs(diff) * RAISE) * (diff > 0 ? 1 : diff < 0 ? JUMP_DOWN : 1);
}

/**
 * 跳躍在中點時離「直線底線」（起點到落點高度的線性內插）的高度：`rise` ＋ 級差的一半。
 * 中點的底線在兩端中間，補上半個級差，最高點才會量在較高的一端上面（6R-1c）。
 */
export function jumpPeakAir(fromH: number, toH: number, rise = jumpRise(fromH, toH)): number {
  return rise + (Math.abs(toH - fromH) * RAISE) / 2;
}

/**
 * 技能跳躍（獸躍等 `leap_air` 片段）的離地高度倍率（6R-1c）：片段原本中點離地 `flatPeak`（模型像素）；
 * 起訖有高低差時沿用高低差跳躍的弧度（`jumpPeakAir`），兩者取大。同高時 ＝ 1（平地的弧不變）。
 */
export function leapAirScale(fromH: number, toH: number, flatPeak: number): number {
  if (flatPeak <= 0) return 1;
  return Math.max(flatPeak, jumpPeakAir(fromH, toH)) / flatPeak;
}

/** 高低差的走法：同高或差一級用走的，差兩級以上用跳的。 */
export function climbMode(fromH: number, toH: number): "walk" | "jump" {
  return Math.abs(toH - fromH) >= 2 ? "jump" : "walk";
}

/** 跳躍的骨架姿勢（樣張 leap：起跳收腿、空中、落地伸直）。 */
export function leapPose(u: number): InkPose {
  const k = Math.sin(clamp(u) * Math.PI);
  return { hipN: 0.9 * k, kneeN: 1.5 * k, hipF: 0.5 * k, kneeF: 1.7 * k, arm: -0.9 * k, armF: -0.6 * k, liftL: 2.4 * k, liftR: 2.4 * k, armL: -1.2 * k, armR: -1.2 * k };
}

/** 一格移動某一刻的畫面：水平進度、身體抬高（模型像素，含所在格的高度）、離地高度、姿勢與揚塵。 */
export interface LegFrame {
  mode: "walk" | "jump";
  /** 水平進度（0～1，緩入緩出）。 */
  t: number;
  /** 腳底所在的高度（模型像素，＝ 級數 × RAISE，往上為正）。 */
  lift: number;
  /** 跳躍時離地的高度（模型像素，往上為正）。 */
  air: number;
  /** 紙娃娃姿勢（已量化）。 */
  pose: InkPose;
  /** 異形姿勢（走、跳都用異形的走路片段；跳時身體被拉長一點）。 */
  creature: CreaturePose;
  /** 整個人的不透明度（潛行半透明）。 */
  alpha: number;
  /** 落地揚塵的強度（0～1；只有跳躍落地時 > 0）。 */
  dust: number;
}

/**
 * 從高 `fromH` 走到高 `toH` 的一格，播到 `u`（0～1）時的畫面；`tile` ＝ 這是第幾格（相位接續）。
 * 純函式，戰場與探索共用。
 */
export function legFrame(u: number, fromH: number, toH: number, gait: Gait = "walk", tile = 0): LegFrame {
  const k = clamp(u);
  const diff = toH - fromH;
  const g = GAITS[gait];
  if (climbMode(fromH, toH) === "jump") {
    const t = easeInOut(k);
    const air = Math.sin(k * Math.PI) * jumpPeakAir(fromH, toH);
    const dust = k > DUST_FROM ? clamp((1 - k) / (1 - DUST_FROM)) : 0;
    const stretch = Math.sin(k * Math.PI);
    return { mode: "jump", t, lift: mix(fromH, toH, t) * RAISE, air, pose: quantizePose(leapPose(k)), creature: { sx: 1 - 0.06 * stretch, sy: 1 + 0.1 * stretch, rot: 0 }, alpha: g.alpha, dust };
  }
  const phase = quantizePhase(tilePhase(tile, k));
  const pose = { ...gaitPose(phase, gait) };
  // 差一級：上＝前半段抬腳（髖 +0.4、膝 +0.7）；上下都在後半段才升降 6
  const rise = easeInOut(clamp((k - STEP_RISE_FROM) / (1 - STEP_RISE_FROM)));
  if (diff > 0) {
    const s = Math.sin(k * Math.PI);
    pose.hipN = pz(pose, "hipN") + 0.4 * s;
    pose.kneeN = pz(pose, "kneeN") + 0.7 * s;
    pose.liftL = pz(pose, "liftL") + 1.5 * s;
    pose.lean = Math.max(pz(pose, "lean"), 0.1);
  } else if (diff < 0) {
    // 落地時起伏多 1（往下壓一下）
    const land = k > 0.75 ? Math.sin(((k - 0.75) / 0.25) * Math.PI) : 0;
    pose.bob = pz(pose, "bob") + land;
  }
  const creature = CREATURE_CLIPS.walk.pose((((tile + k) / 2) % 1 + 1) % 1);
  return { mode: "walk", t: easeInOut(k), lift: (fromH + diff * rise) * RAISE, air: 0, pose: quantizePose(pose), creature, alpha: g.alpha, dust: 0 };
}

// ---- 倒地（prone 狀態）------------------------------------------------------

/** 倒地時身體轉的角度（弧度；同 walkAnim 的 SLIP_ANGLE）。 */
export const PRONE_ANGLE = 1.35;
/** 倒地時身體往前溜的距離（模型像素）。 */
export const PRONE_SLIDE = 6;

/** 躺著的骨架姿勢：膝蓋微彎、手往頭上攤開（以腳底為軸轉倒之後看起來是仰躺）。 */
export const PRONE_POSE: Readonly<InkPose> = Object.freeze({ hipN: 0.35, kneeN: 0.55, hipF: 0.1, kneeF: 0.3, arm: -1.9, elbow: -0.3, armF: -1.5, liftL: 1.5, armL: -1.2, armR: -1.2 });

/**
 * 倒地的身體（只轉小人本身，底圈、血條不動）：`t` 0～1 ＝ 前 35% 腳往前溜，接著 35% 以腳底為軸倒下，最後躺著。
 * 往東走往西倒、往西走往東倒；南北一律往東側倒。回傳小人貼圖（錨點在腳底）的位移、旋轉與姿勢。
 * `t ＝ 1` 就是倒地狀態下持續躺著的樣子（重畫場景時照這個畫）。
 */
export function proneBody(t: number, facing: Facing, walking: InkPose = {}): { x: number; y: number; rotation: number; pose: InkPose } {
  const k = clamp(t);
  const dx = facing === "east" ? 1 : facing === "west" ? -1 : 0;
  const dy = facing === "south" ? 1 : facing === "north" ? -1 : 0;
  const spin = facing === "east" ? -1 : 1;
  const s = easeInOut(Math.min(1, k / 0.35));
  const fall = easeInOut(clamp((k - 0.35) / 0.35));
  const pose: InkPose = {};
  for (const key of POSE_KEYS) {
    if (key === "wpn") continue;
    const a = pz(walking, key);
    const b = pz(PRONE_POSE, key);
    const v = mix(a, b, fall);
    if (v !== 0) pose[key] = v;
  }
  return { x: dx * PRONE_SLIDE * s, y: dy * PRONE_SLIDE * 0.5 * s, rotation: spin * PRONE_ANGLE * fall, pose: quantizePose(pose) };
}

// ---- 冰面滑倒並滑行（#123，6E-2）-----------------------------------------------------

/** 滑行時身體往後仰的角度（弧度）。 */
export const SKID_LEAN = 0.22;

/** 滑行的骨架姿勢：雙腳一前一後、膝微彎、雙手張開保持平衡（不踏步）。 */
export const SKID_POSE: Readonly<InkPose> = Object.freeze({ hipN: 0.45, kneeN: 0.15, hipF: -0.35, kneeF: 0.35, arm: -1.1, armF: -0.9, elbow: -0.2, liftL: 1.2, armL: -1.4, armR: -1.4 });

/** 滑行時的身體：往面向的反方向仰（同倒地的方向，南北一律往東側），姿勢固定。 */
export function skidBody(facing: Facing): { rotation: number; pose: InkPose } {
  const spin = facing === "east" ? -1 : 1;
  return { rotation: spin * SKID_LEAN, pose: quantizePose({ ...SKID_POSE }) };
}

/** 冰面第一格的踉蹌（`t` 0～1）：左右晃兩下、越晃越小，最後回正（旋轉，弧度）。 */
export function stumbleTilt(t: number): number {
  const k = clamp(t);
  return Math.sin(k * Math.PI * 4) * 0.18 * (1 - k);
}

// ---- 人形受擊（6M-4 併入美術 PM 檢查：和 6M-3 的異形一致，只閃剪影）-----------------

/** 人形受擊片段的長度（毫秒；同樣張 CLIP.hit）。 */
export const HUMAN_HIT_MS = 360;
/** 受擊時往後彈的距離（虛擬像素；樣張 move −7）。 */
export const HIT_KNOCK = 7;

/** 白閃強度量化（0.05 一級；貼圖快取用）。 */
export function quantizeFlash(f: number): number {
  if (!(f > 0)) return 0;
  return Number((Math.round(clamp(f) * 20) / 20).toFixed(2));
}

/** 人形受擊白閃的峰值（OCL-1b：外框閃白 k 的分母，Q6；只用在人形受擊、倒下、被撞倒、疊層白閃）。 */
export const HUMAN_HIT_FLASH = 0.85;

/**
 * 人形受擊（樣張 CLIP.hit）：`t` 0～1 ＝ 仰一下、主手往後甩、往後彈 7，白閃開頭 0.85、播到 1/4 時消失。
 * 回傳的姿勢、白閃都已量化；`knock` 是往後彈的距離（虛擬像素，往面向的反方向）。
 */
export function humanHit(t: number): { pose: InkPose; flash: number; knock: number } {
  const k = clamp(t);
  const pose = quantizePose({ lean: -0.3 * Math.sin(clamp(k * 2) * Math.PI), arm: -0.5 * Math.sin(k * Math.PI) });
  return { pose, flash: quantizeFlash(Math.max(0, 1 - k * 4) * HUMAN_HIT_FLASH), knock: HIT_KNOCK * Math.sin(clamp(k * 1.6) * Math.PI) };
}

/** 往面向的反方向彈 `d`：東西向照原距離，南北向（有透視）只走一半。 */
export function knockOffset(facing: Facing, d: number): { x: number; y: number } {
  if (facing === "east") return { x: -d, y: 0 };
  if (facing === "west") return { x: d, y: 0 };
  return { x: 0, y: facing === "south" ? -d * 0.5 : d * 0.5 };
}
