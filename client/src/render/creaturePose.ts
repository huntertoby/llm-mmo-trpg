// 異形敵人的 4 個通用動畫片段（Phase 6M-2；需求 docs/art/動畫移植需求.md 第 1 節第 5 點、動畫方案.md 第 2.1 節）：走、撲、受擊、倒下。
// 不拆關節：整隻身體以腳底 (0,0) 為準伸縮（sx、sy）、傾斜（rot，順時針為正＝頭往下）、位移（dx、dy，往前＝+x、往上＝-y），
// 再加上透明度 alpha 與受擊白閃 flash（白閃由呼叫端疊，drawCreature 不畫）。地上的影子不跟著動。
// 確定性：每個片段都是時間的純函式（t 0→1，或毫秒），不用 Math.random()。
import type { Ctx } from "./artDraw";

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
  /** 浮空的身形（蝙蝠、鬼火、幽魂…，`bodyTop().hover`）：走路改成上下飄，不踩步。 */
  hover?: boolean;
}

const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
const easeOut = (t: number): number => 1 - (1 - t) * (1 - t);
const easeIn = (t: number): number => t * t;
const TAU = Math.PI * 2;

/** 走：一個循環兩步（0.9 秒），每步身體被腳撐起一下、落地時壓扁一點、前後微微搖。 */
function walk(t: number, opt: CreatureClipOpt = {}): CreaturePose {
  const ph = clamp(t) * TAU;
  if (opt.hover === true) return { dy: -1.6 * Math.sin(ph) - 2, rot: 0.05 * Math.sin(ph), sx: 1, sy: 1 };
  const step = Math.abs(Math.sin(ph)); // 兩步：每半個循環一步
  return { dy: -1.4 * step, sx: 1 + 0.035 * (1 - step), sy: 1 - 0.04 * (1 - step), rot: 0.045 * Math.sin(ph), dx: 0 };
}

/** 撲：蓄力（壓低、往後縮）→ 撲出（拉長、往前上）→ 落地壓扁 → 退回原位（位移由引擎事件決定時，呼叫端另加）。 */
function pounce(t: number): CreaturePose {
  const k = clamp(t);
  if (k < 0.35) {
    const e = easeOut(k / 0.35);
    return { dx: -2.5 * e, dy: 0, sx: 1 + 0.12 * e, sy: 1 - 0.16 * e, rot: -0.08 * e };
  }
  if (k < 0.7) {
    const u = (k - 0.35) / 0.35;
    const e = easeOut(u);
    return { dx: -2.5 + 15.5 * e, dy: -9 * Math.sin(u * Math.PI), sx: 1.12 + 0.06 * Math.sin(u * Math.PI), sy: 0.84 + 0.08 * u, rot: -0.08 + 0.24 * e };
  }
  const v = (k - 0.7) / 0.3;
  const back = easeOut(v);
  const land = Math.sin(clamp(v * 2) * Math.PI) * (1 - v); // 前半段落地壓扁
  return { dx: 13 * (1 - easeIn(v)), dy: 0, sx: 1.12 - 0.12 * back + 0.05 * land, sy: 0.92 + 0.08 * back - 0.08 * land, rot: 0.16 * (1 - back) };
}

/** 受擊：往後彈、頭往後仰、身體被打扁一點，開頭白閃。 */
function hit(t: number): CreaturePose {
  const k = clamp(t);
  const s = Math.sin(clamp(k * 1.6) * Math.PI);
  const r = Math.sin(clamp(k * 2) * Math.PI);
  return { dx: -6 * s, dy: 0, sx: 1 - 0.07 * r, sy: 1 + 0.06 * r, rot: -0.22 * r, flash: Math.max(0, 1 - k * 4) * 0.85 };
}

/** 倒下：往後倒、身體塌扁、變淡；播完停在最後一格。 */
function fall(t: number): CreaturePose {
  const k = clamp(t);
  const e = easeIn(k);
  const bounce = k > 0.8 ? 0.04 * Math.sin(((k - 0.8) / 0.2) * Math.PI) : 0; // 落地時彈一下
  return { dx: -4 * e, dy: 0, sx: 1 + 0.25 * e, sy: 1 - 0.55 * e + bounce, rot: -0.35 * e, alpha: 1 - 0.45 * e };
}

export const CREATURE_CLIPS: Readonly<Record<CreatureClipId, CreatureClip>> = {
  walk: { dur: 900, loop: true, pose: walk },
  pounce: { dur: 520, loop: false, pose: (t) => pounce(t) },
  hit: { dur: 360, loop: false, pose: (t) => hit(t) },
  fall: { dur: 600, loop: false, pose: (t) => fall(t) },
};

export const CREATURE_CLIP_IDS: readonly CreatureClipId[] = ["walk", "pounce", "hit", "fall"];

/** 某片段播到第 `ms` 毫秒的姿勢（循環片段取餘數；其他停在最後一格）。 */
export function creaturePoseAt(id: CreatureClipId, ms: number, opt: CreatureClipOpt = {}): CreaturePose {
  const c = CREATURE_CLIPS[id];
  const t = c.loop ? (((ms % c.dur) + c.dur) % c.dur) / c.dur : clamp(ms / c.dur);
  return c.pose(t, opt);
}

/** 讀欄位；沒給或不是有限數字 → 預設。 */
export function cp(p: CreaturePose, k: keyof CreaturePose): number {
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

const POSE_FIELDS: ReadonlyArray<keyof CreaturePose> = ["dx", "dy", "sx", "sy", "rot", "alpha", "flash"];
const q2 = (v: number): number => Number((Math.round(v / 0.02) * 0.02 + 0).toFixed(2));

/** 量化異形姿勢（每個欄位到 0.02；6M-3 貼圖快取用）。 */
export function quantizeCreaturePose(p: CreaturePose): CreaturePose {
  const out: CreaturePose = {};
  for (const k of POSE_FIELDS) if (p[k] !== undefined) out[k] = q2(cp(p, k));
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
  return out.join(",");
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
