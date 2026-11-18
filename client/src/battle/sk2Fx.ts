// SK-2 三個新原語的戰鬥演出描述（AR-SK2；純函式）：吸收表面、疾病擴散、鉤。
// 美術：docs/art/SK-2原語-美術.md 第 2 節與「第 2 版」，移植需求 docs/art/SK-2原語-移植需求.md 第 1 節第 2～4 項。
// 只讀這一步的事件、這一步之前（`before`）與之後（`after`）的畫面與技能卡，不讀時鐘、不用亂數，不裁決規則：
// - 吸收表面吃 `surface_absorbed`（施放者、格子、表面、收益）；
// - 疾病擴散吃 `disease_spread`（倒下的人、被傳染的人、狀態）；範圍格照引擎量距離的方式（單位距離，量到最近佔格；
//   `engine/contagion.py`、`rules/footprint.unit_dist`）算，不是樣張畫的上下左右 4 格；
// - 鉤吃「技能卡帶 `hook` 原語的 `skill_used`」之後的強制位移（`unit_moved` mode forced）、推不動（`push_resisted`／`collided` immovable）。
//   拉到一半停下、而且沒有撞擊＝前面是致命地形（引擎 `stop_before_deadly`），演出照「熔岩前煞住」。
// 時間一律是正常速度的毫秒（未縮放），由繪製器乘上播放速度的倍率。
import type { BattleView, EventBase, Pos, UnitView } from "../api/types";
import { asEvent } from "../api/types";
import { nearestTile, unitTiles } from "./footprint";
import type { VfxCards } from "./vfx";

/** 疾病擴散傳給幾格內的同陣營單位（`content/rules/core.yaml` 的 `contagion_radius` 初值；前端沒有規則資料，照抄）。 */
export const CONTAGION_RADIUS = 1;

/** 吸收表面：施放者吸走 `tile` 上的 `surface`，換成 `gain`（`element` 時是 `element`）。 */
export interface Sk2Absorb {
  kind: "absorb";
  casterId: string;
  tile: Pos;
  surface: string;
  gain: string;
  element: string | null;
}

/** 疾病擴散：`fromId` 倒下時把 `statusId` 傳給 `toId`；`range` 是候選範圍格（不含倒下的人自己佔的格），`chosen` 是被傳染的人那一格。 */
export interface Sk2Spread {
  kind: "spread";
  fromId: string;
  toId: string;
  from: Pos;
  to: Pos;
  /** 飛過去的那一團畫哪一種（多種時照事件順序取第一種）。 */
  statusId: string;
  range: Pos[];
  chosen: Pos;
  /** 演出開始（倒下那一刻；未縮放，相對這一步的特效原點）。 */
  atMs: number;
}

/** 鉤的三種演出：一般拉回、拉到一半在致命地形前煞住、拉不動（巨型頭目等）改撞擊。 */
export type HookMode = "pull" | "brake" | "immovable";

/** 鉤：施放者 `casterId`（在 `caster`）鉤住 `targetId`，從 `from` 拉到 `to`。 */
export interface Sk2Hook {
  kind: "hook";
  casterId: string;
  targetId: string;
  caster: Pos;
  from: Pos;
  to: Pos;
  mode: HookMode;
  /** 受鉤的那一格（巨型單位是離施放者最近的佔格）。 */
  hookTile: Pos;
  /** 煞住時前面那一格（致命地形）；其他為 `null`。 */
  hazard: Pos | null;
  /** 這一招的特效（`StepVfx.casts`）裡要換成鎖鏈的那一個（施放者發出的第一個）；沒有為 -1。 */
  castIndex: number;
  /** 拉的位移在這一步特效時鐘上的開始與長度（未縮放；`playback` 照出招後的位移填）。 */
  pullAtMs: number;
  pullMs: number;
}

export type Sk2Fx = Sk2Absorb | Sk2Spread | Sk2Hook;

const str = (v: unknown): string | null => (typeof v === "string" ? v : null);
const posOf = (v: unknown): Pos | null => {
  const p = v as { x?: unknown; y?: unknown } | null;
  return p !== null && typeof p === "object" && typeof p.x === "number" && typeof p.y === "number" ? { x: p.x, y: p.y } : null;
};
const manhattan = (a: Pos, b: Pos): number => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
const sign = (n: number): number => (n > 0 ? 1 : n < 0 ? -1 : 0);

/** 單位 `u` 的佔格到 `t` 的最近曼哈頓距離（同引擎 `dist_to`）。 */
function distTo(u: UnitView, t: Pos): number {
  return Math.min(...unitTiles(u).map((c) => manhattan(c, t)));
}

/**
 * 疾病擴散的候選範圍格：地圖內、離倒下的人最近佔格 1～`radius` 格（曼哈頓）的格子，依 (y, x) 排序。
 * 引擎是「範圍內的同陣營存活單位」挑一個；畫面把範圍整片鋪淡色，被選中那格加亮框。
 */
export function spreadRange(fallen: UnitView, view: Pick<BattleView, "width" | "height">, radius = CONTAGION_RADIUS): Pos[] {
  const out: Pos[] = [];
  for (let y = 0; y < view.height; y++)
    for (let x = 0; x < view.width; x++) {
      const d = distTo(fallen, { x, y });
      if (d >= 1 && d <= radius) out.push({ x, y });
    }
  return out;
}

function unitIn(views: readonly BattleView[], id: string | null): UnitView | undefined {
  if (id === null) return undefined;
  for (const v of views) {
    const u = v.units.find((x) => x.id === id);
    if (u !== undefined) return u;
  }
  return undefined;
}

function absorbOf(e: EventBase): Sk2Absorb | null {
  const casterId = str(e.unit_id);
  const tile = posOf(e.pos);
  if (casterId === null || tile === null) return null;
  return { kind: "absorb", casterId, tile, surface: str(e.surface) ?? "water", gain: str(e.gain) ?? "stack", element: str(e.element) };
}

function spreadOf(e: EventBase, before: BattleView, after: BattleView, downAt: (id: string) => number): Sk2Spread | null {
  const fromId = str(e.from_id);
  const toId = str(e.to_id);
  const fallen = unitIn([after, before], fromId);
  const target = unitIn([after, before], toId);
  const ids = Array.isArray(e.status_ids) ? e.status_ids.filter((s): s is string => typeof s === "string") : [];
  if (fromId === null || toId === null || fallen === undefined || target === undefined) return null;
  return {
    kind: "spread",
    fromId,
    toId,
    from: fallen.pos,
    to: target.pos,
    statusId: ids[0] ?? "burning",
    range: spreadRange(fallen, after),
    chosen: nearestTile(target, fallen.pos),
    atMs: downAt(fromId),
  };
}

/** 從 `skill_used`（索引 `i`）往後找鉤住的人與結果，到下一個 `skill_used` 為止。 */
function hookOf(events: readonly EventBase[], i: number, before: BattleView, after: BattleView): Sk2Hook | null {
  const used = events[i] as EventBase;
  const casterId = str(used.unit_id);
  const casterUnit = unitIn([before, after], casterId);
  if (casterId === null || casterUnit === undefined) return null;
  const caster = casterUnit.pos;
  let targetId: string | null = null;
  let from: Pos | null = null;
  let to: Pos | null = null;
  let immovable = false;
  let collided = false;
  for (let k = i + 1; k < events.length; k++) {
    const e = events[k] as EventBase;
    if (e.type === "skill_used") break;
    if (e.type === "unit_moved" && e.mode === "forced") {
      const id = str(e.unit_id);
      if (targetId !== null && id !== targetId) continue;
      targetId = id;
      from ??= posOf(e.from_pos);
      to = posOf(e.to_pos);
    } else if (e.type === "push_resisted" && targetId === null) {
      targetId = str(e.unit_id);
      immovable = true;
    } else if (e.type === "collided" && (targetId === null || str(e.unit_id) === targetId)) {
      targetId ??= str(e.unit_id);
      collided = true;
      if (e.obstacle === "immovable") immovable = true;
    }
  }
  const target = unitIn([before, after], targetId);
  if (targetId === null || target === undefined) return null;
  const start = from ?? target.pos;
  const end = to ?? start;
  const moved = to !== null;
  const mode: HookMode = !moved && immovable ? "immovable" : moved && !collided && manhattan(end, caster) > 1 ? "brake" : "pull";
  const step = { x: sign(caster.x - end.x), y: sign(caster.y - end.y) };
  const hazard = mode === "brake" ? { x: end.x + (step.x !== 0 ? step.x : 0), y: end.y + (step.x !== 0 ? 0 : step.y) } : null;
  return { kind: "hook", casterId, targetId, caster, from: start, to: end, mode, hookTile: nearestTile(target, caster), hazard, castIndex: -1, pullAtMs: 0, pullMs: 0 };
}

/**
 * 這一步的 SK-2 演出（照事件順序）。`cards`：技能卡（看招有沒有 `hook` 原語）；`downAt(id)`：那個人倒下的那一刻
 * （這一步特效時鐘上、未縮放；沒有倒下片段時呼叫端給 0）。
 */
export function sk2FxOf(raw: readonly Record<string, unknown>[], before: BattleView, after: BattleView, cards: VfxCards, downAt: (id: string) => number = () => 0): Sk2Fx[] {
  const events = raw.map(asEvent);
  const out: Sk2Fx[] = [];
  events.forEach((e, i) => {
    if (e.type === "surface_absorbed") {
      const a = absorbOf(e);
      if (a !== null) out.push(a);
    } else if (e.type === "disease_spread") {
      const s = spreadOf(e, before, after, downAt);
      if (s !== null) out.push(s);
    } else if (e.type === "skill_used") {
      const id = str(e.skill_id);
      const card = id === null ? undefined : cards[id];
      if (card?.effect_ids?.includes("hook") !== true) return;
      const h = hookOf(events, i, before, after);
      if (h !== null) out.push(h);
    }
  });
  return out;
}
