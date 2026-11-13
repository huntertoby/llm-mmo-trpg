// RG-3（#162）戰場標記的純函式：瞄準預告（準星、瞄準線、被擋的斷點）、盾兵連結、看一眼的時間軸。
// 規格是 `docs/art/RG樣張.md` 第 2 節（第 2 版）＋第 8 節；數值照樣張 `docs/art/sample/rgMarks.js` 搬。
// 座標一律模型像素（一格 TILE_SIZE 48）；「k」＝地圖縮小時的反向放大（`minMark.minMarkScale`）。
// 不讀時鐘：時間由呼叫端傳入（毫秒）；判斷誰被擋一律讀伺服器的欄位（`ChargeOut.lock_blocker_id`），前端不裁決。
import type { BattleView, Pos, PreviewOut, TelegraphOut } from "../api/types";
import { TILE_SIZE } from "./geometry";
import { isAlive } from "./units";

const T = TILE_SIZE;

/** 強招紫（同「蓄」`telegraph.ts` 的 0xb06bff；美術 PM 決定 A）。 */
export const AIM_COLOR = 0xb06bff;
/** 被擋之後的那一段、被擋時的準星：zone_neutral 灰。 */
export const AIM_BLOCKED_COLOR = 0xb0b8c4;
/** Q 版外框色。 */
export const RG_INK = 0x16121a;

export const RG_TIMING = {
  /** 準星一個週期：亮 520 ms ＋ 收 380 ms。 */
  blinkMs: 900,
  blinkOnMs: 520,
  /** 瞄準線流速：每秒往目標走 24 模型像素。 */
  flowPxPerS: 24,
  /** 看一眼整段。 */
  glanceMs: 600,
} as const;

/** 畫面下限（`registerMark` 的下限；樣張第 5 節）與世界大小：準星 20→16、小盾 14→11、看一眼 14→12、「？」12→9、線寬 2→2。 */
export const RG_MIN = {
  reticle: { base: 20, min: 16 },
  chip: { base: 14, min: 11 },
  glance: { base: 14, min: 12 },
  question: { base: 12, min: 9 },
  line: { base: 2, min: 2 },
} as const;

/** 準星圓心到三角外框下緣（13.6）；頭頂到三角的空隙 4。 */
export const RETICLE_BELOW = 13.6;
export const RETICLE_GAP = 4;
/** 小盾中心到下緣外框（7.85）；空隙 2。 */
export const CHIP_BELOW = 7.85;
export const CHIP_GAP = 2;
/** 看一眼的泡泡中心到尾巴尖外框（8）；空隙 2。 */
export const GLANCE_BELOW = 8;
export const GLANCE_GAP = 2;

/** 胸口（格子中心往上 0.3 格）：瞄準線起點、盾兵連結起點。 */
export const CHEST_DY = -0.3 * T;
/** 弓手的蓄力徽章（避開用）：圓心＝格子中心＋(−0.37T, −0.2T)，半徑 10＋2。 */
export const BADGE_AVOID = { dx: -0.37 * T, dy: -0.2 * T, r: 12 } as const;

/** 準星的狀態：0＝亮、1＝收。減少動態時固定亮。 */
export function blinkPhase(ms: number, reduced = false): 0 | 1 {
  if (reduced) return 0;
  const m = ((ms % RG_TIMING.blinkMs) + RG_TIMING.blinkMs) % RG_TIMING.blinkMs;
  return m < RG_TIMING.blinkOnMs ? 0 : 1;
}

/** 頭頂（含頭飾，世界 y）→ 準星、小盾、看一眼的中心 y。 */
export const reticleY = (headTop: number, k: number): number => headTop - RETICLE_GAP - RETICLE_BELOW * k;
export const chipY = (headTop: number, k: number): number => headTop - CHIP_GAP - CHIP_BELOW * k;
export const glanceY = (headTop: number, k: number): number => headTop - GLANCE_GAP - GLANCE_BELOW * k;

// ---------------------------------------------------------------------------
// 誰瞄準誰（讀伺服器的預告）
// ---------------------------------------------------------------------------

export interface AimDraw {
  casterId: string;
  targetId: string;
  caster: Pos;
  target: Pos;
  /** 現在射出會擋下這一擊的目標隊友（伺服器 `lock_blocker_id`）；沒有時 null。 */
  blockerId: string | null;
  blocker: Pos | null;
}

/**
 * 預告裡的瞄準（`ChargeOut.lock_target_id`）→ 要畫的線。弓手或目標不在畫面資料裡（隱蔽看不到、倒下、離場）時不畫：
 * 準星與線不能洩漏看不到的人的位置。
 */
export function aimDraws(t: TelegraphOut | null | undefined, view: BattleView): AimDraw[] {
  const live = new Map(view.units.filter(isAlive).map((u) => [u.id, u.pos]));
  const out: AimDraw[] = [];
  for (const c of t?.charges ?? []) {
    const targetId = c.lock_target_id;
    if (targetId == null) continue;
    const caster = live.get(c.unit_id);
    const target = live.get(targetId);
    if (caster === undefined || target === undefined) continue;
    const blockerId = c.lock_blocker_id ?? null;
    const blocker = blockerId === null ? null : (live.get(blockerId) ?? null);
    out.push({ casterId: c.unit_id, targetId, caster, target, blockerId: blocker === null ? null : blockerId, blocker });
  }
  return out.sort((a, b) => (a.casterId < b.casterId ? -1 : a.casterId > b.casterId ? 1 : 0));
}

export interface ReticleDraw {
  targetId: string;
  pos: Pos;
  /** 每一條都被擋才變灰、不閃（樣張 2.1：兩人瞄準同一人時只要有一條沒被擋就照常紫色閃）。 */
  blocked: boolean;
}

/** 準星：每個目標只畫一個。 */
export function reticleDraws(aims: readonly AimDraw[]): ReticleDraw[] {
  const by = new Map<string, ReticleDraw>();
  for (const a of aims) {
    const r = by.get(a.targetId);
    const blocked = a.blocker !== null;
    if (r === undefined) by.set(a.targetId, { targetId: a.targetId, pos: a.target, blocked });
    else r.blocked = r.blocked && blocked;
  }
  return [...by.values()];
}

// ---------------------------------------------------------------------------
// 瞄準線的幾何
// ---------------------------------------------------------------------------

export interface Pt {
  x: number;
  y: number;
}

export interface LineGeom {
  a: Pt;
  ux: number;
  uy: number;
  len: number;
  /** 本色段的起點、終點（沿線長度）。 */
  start: number;
  end: number;
  /** 被擋的斷點（沿線長度）；沒被擋時 null。 */
  cut: number | null;
}

/**
 * `a`＝弓手胸口、`b`＝準星圓心、`badge`＝弓手蓄力徽章的圓心（避開）、`blocker`＝擋住的人的胸口（沒有＝null）。
 * 起點：往目標 0.4 格；還在徽章圓（半徑 12）裡就沿線往前推到圓外。終點：準星圓心前 11×`rk`。
 * 斷點：擋住的人在線上的位置往弓手那邊退 0.22 格。
 */
export function lineGeom(a: Pt, b: Pt, rk: number, badge: Pt | null, blocker: Pt | null): LineGeom | null {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  if (len < 1) return null;
  const ux = dx / len;
  const uy = dy / len;
  const end = len - 11 * rk;
  let start = 0.4 * T;
  if (badge !== null) while (start < end && Math.hypot(a.x + ux * start - badge.x, a.y + uy * start - badge.y) < BADGE_AVOID.r) start += 0.5;
  if (start >= end) return null;
  let cut: number | null = null;
  if (blocker !== null) {
    const along = (blocker.x - a.x) * ux + (blocker.y - a.y) * uy;
    cut = Math.max(start, Math.min(end, along - 0.22 * T));
  }
  return { a, ux, uy, len, start, end, cut };
}

/** 沿線長度 `s` 的點。 */
export function pointAt(g: LineGeom, s: number): Pt {
  return { x: g.a.x + g.ux * s, y: g.a.y + g.uy * s };
}

/**
 * 虛線的實線段（沿線長度的區間）：照 canvas `setLineDash([dash, gap])` 的樣子，花紋以「從 a 量起的長度 ＋ `offset`」對齊
 * （`offset` 為負＝往終點流動）。只回傳 [s0, s1] 之內的部分。
 */
export function dashes(s0: number, s1: number, dash: number, gap: number, offset: number): Array<[number, number]> {
  const per = dash + gap;
  if (!(per > 0) || s1 <= s0) return [];
  const out: Array<[number, number]> = [];
  let n = Math.floor((s0 + offset) / per);
  for (;;) {
    const from = n * per - offset;
    if (from >= s1) break;
    const lo = Math.max(s0, from);
    const hi = Math.min(s1, from + dash);
    if (hi > lo) out.push([lo, hi]);
    n += 1;
  }
  return out;
}

/** 流動的位移：每秒往目標 24 模型 px（×k）；減少動態時不動。 */
export function flowOffset(ms: number, k: number, reduced = false): number {
  return reduced ? 0 : -((ms / 1000) * RG_TIMING.flowPxPerS) * k;
}

/**
 * 一段沿線區間照「所在的排」切開（瞄準線照排放進每排的 `frames` 那一級，樣張 2.2 圖層）：
 * 用未抬高的格子座標算排（`ya`、`yb`＝兩端未抬高的 y），回傳每一塊的區間與排號。
 */
export function splitRows(s0: number, s1: number, len: number, ya: number, yb: number, rows: number): Array<{ s0: number; s1: number; row: number }> {
  const yAt = (s: number) => ya + ((yb - ya) * s) / len;
  const rowOf = (y: number) => Math.max(0, Math.min(rows - 1, Math.floor(y / T)));
  const out: Array<{ s0: number; s1: number; row: number }> = [];
  let a = s0;
  while (a < s1 - 1e-9) {
    const row = rowOf(yAt(a) + (yb > ya ? 1e-6 : -1e-6));
    let b = s1;
    if (yb !== ya) {
      const edge = yb > ya ? (row + 1) * T : row * T;
      const sEdge = ((edge - ya) * len) / (yb - ya);
      if (sEdge > a + 1e-9 && sEdge < s1) b = sEdge;
    }
    out.push({ s0: a, s1: b, row });
    a = b;
  }
  return out;
}

// ---------------------------------------------------------------------------
// 盾兵連結
// ---------------------------------------------------------------------------

export interface GuardDraw {
  /** 被保護者（玩家選的目標）。 */
  wardId: string;
  ward: Pos;
  /** 盾兵。 */
  guardId: string;
  guard: Pos;
}

/**
 * 滑過目標的預覽有盾兵掩護（`cover.kind` ＝ `shield_guard`、`cover.unit_id`）時畫小盾與連結（樣張 2.4「何時出現」）；
 * 其他（沒有掩護、物件掩護、塔盾、目標或盾兵不在畫面資料裡）null。
 */
export function guardDraw(p: PreviewOut | null | undefined, view: BattleView): GuardDraw | null {
  const cover = p?.cover;
  if (p == null || cover == null || cover.kind !== "shield_guard" || cover.unit_id == null) return null;
  const targetId = "target_id" in p.action && typeof p.action.target_id === "string" ? p.action.target_id : null;
  if (targetId === null) return null;
  const live = new Map(view.units.filter(isAlive).map((u) => [u.id, u.pos]));
  const ward = live.get(targetId);
  const guard = live.get(cover.unit_id);
  if (ward === undefined || guard === undefined) return null;
  return { wardId: targetId, ward, guardId: cover.unit_id, guard };
}

export interface LinkDot {
  x: number;
  y: number;
  r: number;
}

/**
 * 小盾中心（樣張 2.4 ＋ 第 8 節第 2 條）：一般在頭頂正上方；盾兵在被保護者正北（同一直行、在上）時改放在頭的右上側
 * （避開西邊的蓄力徽章、不疊在盾兵腳邊）。`cx`＝被保護者格子中心 x、`headTop`＝含頭飾的頭頂。
 */
export function chipCenter(guard: Pos, ward: Pos, cx: number, headTop: number, k: number): Pt {
  const north = guard.x === ward.x && guard.y < ward.y;
  if (!north) return { x: cx, y: chipY(headTop, k) };
  return { x: cx + NORTH_CHIP_DX * k, y: headTop + NORTH_CHIP_DY };
}

/** 盾兵在正北時小盾的位置：頭頂往右 14×k、中心和頭頂同高往下 4（頭的右上側）。 */
export const NORTH_CHIP_DX = 14;
export const NORTH_CHIP_DY = 4;

/**
 * 盾兵 → 小盾的點線（樣張 `coverLink` 第 2 版）：`a`＝盾兵格子中心、`b`＝被保護者格子中心、`chip`＝小盾中心。
 * 二次曲線、不穿過被保護者的身體；米白小點等距（點距約 4.5k），兩端大一點。
 */
export function linkDots(a: Pt, b: Pt, chip: Pt, k: number): LinkDot[] {
  const same = Math.abs(a.x - b.x) < 1;
  const side = same ? 1 : Math.sign(a.x - b.x);
  const y0 = CHEST_DY;
  let A: Pt;
  if (same) A = { x: a.x + side * 0.46 * T, y: a.y + y0 };
  else {
    const d = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    A = { x: a.x + ((b.x - a.x) / d) * 0.25 * T, y: a.y + y0 + ((b.y - a.y) / d) * 0.25 * T };
  }
  const E = { x: chip.x + side * 8.1 * k, y: chip.y - 2.5 * k };
  const C = same && a.y < b.y ? { x: b.x + side * 0.75 * T, y: (A.y + E.y) / 2 } : { x: b.x + side * Math.max(T, Math.abs(A.x - b.x)), y: E.y };
  const at = (t: number): Pt => ({
    x: (1 - t) * (1 - t) * A.x + 2 * t * (1 - t) * C.x + t * t * E.x,
    y: (1 - t) * (1 - t) * A.y + 2 * t * (1 - t) * C.y + t * t * E.y,
  });
  const N = 96;
  const acc = [0];
  let prev = at(0);
  for (let i = 1; i <= N; i++) {
    const q = at(i / N);
    acc.push((acc[i - 1] as number) + Math.hypot(q.x - prev.x, q.y - prev.y));
    prev = q;
  }
  const len = acc[N] as number;
  const n = Math.max(2, Math.round(len / (4.5 * k)));
  const byLen = (L: number): Pt => {
    let i = 1;
    while (i < N && (acc[i] as number) < L) i++;
    const lo = acc[i - 1] as number;
    const f = (L - lo) / Math.max(1e-6, (acc[i] as number) - lo);
    return at((i - 1 + f) / N);
  };
  const out: LinkDot[] = [];
  for (let i = 0; i <= n; i++) {
    const q = byLen((len * i) / n);
    out.push({ x: q.x, y: q.y, r: (i === 0 || i === n ? 2.1 : 1.3) * k });
  }
  return out;
}

// ---------------------------------------------------------------------------
// 看一眼
// ---------------------------------------------------------------------------

export interface GlanceFrame {
  scale: number;
  alpha: number;
  /** 瞳孔轉過去 0～1。 */
  look: number;
  /** 視線冒出 0～1。 */
  sight: number;
}

/** 0～600 ms 的樣子（樣張 `glanceFrame` 第 2 版）。減少動態：不彈，瞳孔與視線直接到位，最後一刻才消失。 */
export function glanceFrame(ms: number, reduced = false): GlanceFrame {
  const t = Math.max(0, Math.min(RG_TIMING.glanceMs, ms));
  if (reduced) return { scale: 1, alpha: t >= RG_TIMING.glanceMs ? 0 : 1, look: 1, sight: 1 };
  const scale = t < 90 ? 0.6 + 0.5 * (t / 90) : t < 150 ? 1.1 - 0.1 * ((t - 90) / 60) : 1;
  const look = t < 60 ? 0 : t < 150 ? (t - 60) / 90 : 1;
  const sight = t < 150 ? 0 : t < 240 ? (t - 150) / 90 : 1;
  const alpha = t < 480 ? 1 : 1 - (t - 480) / 120;
  return { scale, alpha, look, sight };
}

/** 放置者 → 陷阱格的單位向量（同一格時朝下）。 */
export function glanceDir(from: Pos, to: Pos): Pt {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const d = Math.hypot(dx, dy);
  return d === 0 ? { x: 0, y: 1 } : { x: dx / d, y: dy / d };
}
