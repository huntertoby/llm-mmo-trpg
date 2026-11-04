// NPC 的小動作（Phase 6N-10；需求 docs/art/動畫移植需求第二批.md 第 9 節、動畫方案 2.7）。
// 接在 6M-4 的 idleClips 上：呼吸照舊（breathScale），小動作換成「每人 3～4 種」，含職業動作（鐵匠搥打、掌櫃擦桌子）。
// 全部是純函式：（場景鍵、單位 ID、身分、待機時鐘毫秒）→ 姿勢。不用 Math.random()、不讀時間。
// - 挑哪一種：探索中沒有戰鬥鍵，照第 0 節第 3 點用「地圖 ID:單位 ID:動作序號」的 FNV-1a（inkStyle.seedOf）；
//   重新整理、重播、換人看都一樣。
// - 間隔、第一次的偏移：照單位 ID 的雜湊錯開（每人 4～7 秒一次）。
// - 職業動作是循環（搥 3 下、擦 2 趟）：在兩個姿勢之間來回，來回量化成 3 級、強度量化成 4 級，貼圖鍵有限（6M-3 快取量化）。
import type { Facing } from "../api/types";
import { breathScale, FIDGET_LEVELS, FIDGETS, idHash, type IdleFrame } from "./idleClips";
import { mixPose, scalePose, type InkPose } from "./inkPose";
import { seedOf } from "./inkStyle";
import { quantizePose } from "./motionClips";

/** NPC 的身分（決定有哪些小動作）：鐵匠、掌櫃（酒館、商店）、一般。從設施位置推（`world/fieldAmbient.ts`），不讀伺服器欄位。 */
export type NpcRole = "smith" | "keeper" | "town";
export const NPC_ROLES: readonly NpcRole[] = ["smith", "keeper", "town"];

export type NpcFidgetId = "glance" | "stretch" | "scratch" | "hammer" | "wipe" | "wipe_brow";

interface FidgetDef {
  ms: number;
  /** 一個姿勢（張望、伸懶腰…）或兩個姿勢來回（`cycles` 趟）。 */
  a: Readonly<InkPose>;
  b?: Readonly<InkPose>;
  cycles?: number;
}

export const NPC_FIDGETS: Readonly<Record<NpcFidgetId, FidgetDef>> = {
  glance: { ms: 1200, a: FIDGETS.glance },
  stretch: { ms: 1200, a: FIDGETS.stretch },
  // 搔頭：一隻手舉到頭邊
  scratch: { ms: 1200, a: Object.freeze({ arm: -2.5, elbow: -1.7, lean: 0.04, armL: -7 }) },
  // 鐵匠搥打：舉高 → 往前下搥，3 下
  hammer: {
    ms: 1800,
    a: Object.freeze({ arm: -2.3, elbow: -0.6, lean: -0.05, armL: -8, bob: -0.4 }),
    b: Object.freeze({ arm: 0.55, elbow: 0.15, lean: 0.14, bob: 0.6, armL: 2.5 }),
    cycles: 3,
  },
  // 掌櫃擦桌子：前傾、手在身前來回，2 趟
  wipe: {
    ms: 1600,
    a: Object.freeze({ arm: 1.0, elbow: -0.35, lean: 0.12, bob: 0.5, armL: -3.5, armR: 1.5 }),
    b: Object.freeze({ arm: 0.35, elbow: -1.05, lean: 0.1, bob: 0.5, armL: 1.5, armR: -3.5 }),
    cycles: 2,
  },
  // 擦汗：手背抹過額頭
  wipe_brow: { ms: 1200, a: Object.freeze({ arm: -2.1, elbow: -2.3, lean: -0.04, armL: -6.5 }) },
};

/**
 * 每種身分的小動作（3～4 種；同一種可以出現兩次＝出現得比較常）。
 * 鐵匠、掌櫃的職業動作佔一半以上，一般 NPC 只有日常的三種。
 */
export const ROLE_FIDGETS: Readonly<Record<NpcRole, readonly NpcFidgetId[]>> = {
  smith: ["hammer", "glance", "hammer", "wipe_brow", "stretch", "hammer"],
  keeper: ["wipe", "glance", "wipe", "stretch", "scratch", "wipe"],
  town: ["glance", "stretch", "scratch"],
};

/** NPC 小動作的間隔：每人 4～7 秒一次（比 6M-4 主角、戰場單位的 7～11 秒勤快，街上看得到）。 */
export const NPC_EVERY_MIN = 4000;
export const NPC_EVERY_SPAN = 3000;
/** 來回的量化級數（0、½、1）。 */
export const SWING_LEVELS = 2;

export function npcSchedule(id: string): { every: number; offset: number } {
  const h = idHash(`npc|${id}`);
  const every = NPC_EVERY_MIN + ((h >>> 10) % NPC_EVERY_SPAN);
  return { every, offset: (h >>> 3) % every };
}

/** 第 `n` 次小動作做哪一種：「場景鍵:單位 ID:序號」的 FNV-1a。 */
export function npcFidgetPick(scene: string, id: string, role: NpcRole, n: number): NpcFidgetId {
  const list = ROLE_FIDGETS[role];
  return list[seedOf(`${scene}:${id}:${n}`) % list.length]!;
}

/** 梯形強度：前後 18% 漸入漸出，中間全強（循環動作大部分時間在全強，貼圖少）。 */
function envelope(u: number): number {
  const edge = 0.18;
  if (u < edge) return u / edge;
  if (u > 1 - edge) return (1 - u) / edge;
  return 1;
}

export interface NpcFidget {
  id: NpcFidgetId;
  /** 強度（已量化，0～1）。 */
  level: number;
  /** 來回（已量化，0 ＝ 姿勢 a、1 ＝ 姿勢 b；單一姿勢的動作一律 0）。 */
  swing: number;
}

/** `ms` 時這個 NPC 在做的小動作（沒有＝`null`）。 */
export function npcFidgetAt(scene: string, id: string, role: NpcRole, ms: number): NpcFidget | null {
  if (!(ms >= 0)) return null;
  const { every, offset } = npcSchedule(id);
  const local = ms + every - offset;
  const n = Math.floor(local / every);
  if (n < 1) return null;
  const which = npcFidgetPick(scene, id, role, n);
  const def = NPC_FIDGETS[which];
  const into = local - n * every;
  if (into >= def.ms) return null;
  const u = into / def.ms;
  const k = def.b === undefined ? Math.sin(u * Math.PI) : envelope(u);
  const level = Math.round(k * FIDGET_LEVELS) / FIDGET_LEVELS;
  if (level <= 0) return null;
  const cycles = def.cycles ?? 0;
  const swing = def.b === undefined ? 0 : Math.round((0.5 - 0.5 * Math.cos(u * cycles * Math.PI * 2)) * SWING_LEVELS) / SWING_LEVELS;
  return { id: which, level, swing };
}

/** 小動作的姿勢（已量化）。 */
export function npcFidgetPose(f: NpcFidget): InkPose {
  const def = NPC_FIDGETS[f.id];
  const base = def.b === undefined ? def.a : mixPose(def.a, def.b, f.swing);
  return quantizePose(scalePose(base, f.level));
}

/** 職業動作（6Q-1）：做的時候轉成側面（側面骨架有完整手臂），做完轉回原本的朝向。日常動作不轉。 */
export const WORK_FIDGETS: readonly NpcFidgetId[] = ["hammer", "wipe"];

export function isWorkFidget(id: NpcFidgetId): boolean {
  return WORK_FIDGETS.includes(id);
}

/**
 * 做職業動作時轉向哪一側（6Q-1）：本來就是側面 ＝ 不轉；有工作設施的方向（`toward`）＝ 朝設施；
 * 都沒有 ＝ 照單位 ID 的雜湊定東或西（確定性，同一個人永遠同一側）。
 */
export function workFacing(id: string, facing: Facing, toward?: "east" | "west"): "east" | "west" {
  if (facing === "east" || facing === "west") return facing;
  if (toward !== undefined) return toward;
  return (idHash(`work|${id}`) & 1) === 0 ? "east" : "west";
}

/** NPC 的待機畫面：多一個 `facing`（做職業動作時的側面；沒有 ＝ 照原本的朝向畫）。 */
export interface NpcIdleFrame extends IdleFrame {
  facing?: Facing;
}

/**
 * NPC 在 `ms` 時的待機畫面（呼吸照 6M-4；鍵以 `n:` 開頭，和 6M-4 的小動作不混）。
 * 給了 `facing`（6Q-1）：職業動作期間轉成 `workFacing` 的側面，鍵帶上朝向；動作結束（強度回到 0）就轉回原本的朝向。
 */
export function npcIdleFrame(scene: string, id: string, role: NpcRole, ms: number, facing?: Facing, toward?: "east" | "west"): NpcIdleFrame {
  const f = npcFidgetAt(scene, id, role, ms);
  const scaleY = breathScale(id, ms);
  if (f === null) return { scaleY, pose: null, key: "" };
  const key = `n:${f.id}:${f.level}:${f.swing}`;
  if (facing === undefined || !isWorkFidget(f.id)) return { scaleY, pose: npcFidgetPose(f), key };
  const side = workFacing(id, facing, toward);
  return { scaleY, pose: npcFidgetPose(f), key: side === facing ? key : `${key}|${side}`, facing: side };
}
