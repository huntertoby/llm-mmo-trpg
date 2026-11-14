// 巨型單位的佔格與點格選部位（GB-4a；`docs/phases/PhaseGB計畫.md` 8.1、T12；05 5.12.4 第 3 點）。純函式。
//
// - 伺服器給巨型單位 `UnitView.footprint`／`tiles`（佔的格子，依 (y, x)）；一格的單位兩者都是 null，
//   這裡的函式對它們一律退化成「只看 `pos`」，所以 1 格單位的行為和改前相同。
// - 「哪一格上有誰」一律走 `unitsOnTile`／`unitAtTile`；「單位 ID → 演出位置」走 `hitLocator`
//   （命中判定帶 `hit_tile` 時以那一格為準，GB-1b 待決 4）。
// - 點巨型頭目的某一格：`giantAim` 由 `PartView.tiles` 推出 `target_part`，不跳選單；點前殼、已破、
//   還沒露出的部位格＝本體；打不到的部位格不送出、回原因。標示（GB-4b）也照同一份 tiles（`giantPartStates`）。
import { isAttackRolled, type Action, type EventBase, type PartOption, type PartView, type Pos, type UnitView } from "../api/types";
import { samePos } from "./geometry";

/** 只看位置與佔格的單位（`UnitView` 或測試用的精簡物件）。 */
export interface Footed {
  pos: Pos;
  footprint?: number | null;
  tiles?: readonly Pos[] | null;
}

/** 佔不只一格的單位（不動巨型頭目）。 */
export function isGiant(u: Pick<Footed, "footprint" | "tiles">): boolean {
  return (u.footprint ?? 1) > 1 && (u.tiles?.length ?? 0) > 1;
}

/** 單位佔的格子（一格的單位＝`[pos]`）。 */
export function unitTiles(u: Footed): Pos[] {
  return isGiant(u) && u.tiles != null ? u.tiles.map((t) => ({ x: t.x, y: t.y })) : [u.pos];
}

/** `tile` 是 `u` 佔的格子。 */
export function occupies(u: Footed, tile: Pos): boolean {
  if (!isGiant(u) || u.tiles == null) return samePos(u.pos, tile);
  return u.tiles.some((t) => samePos(t, tile));
}

/** 佔著 `tile` 的單位（照 `units` 的順序；不篩倒下、撤離）。 */
export function unitsOnTile<U extends Footed>(units: readonly U[], tile: Pos): U[] {
  return units.filter((u) => occupies(u, tile));
}

type Present = Footed & { downed: boolean; escaped: boolean; dismissed: boolean };

/** `tile` 上還在場的單位（不含撤離、消失的召喚物）：站著的優先，其次倒下的；沒有為 `undefined`。 */
export function unitAtTile<U extends Present>(units: readonly U[], tile: Pos | null): U | undefined {
  if (tile === null) return undefined;
  const here = unitsOnTile(units, tile).filter((u) => !u.escaped && !u.dismissed);
  return here.find((u) => !u.downed) ?? here[0];
}

/** `tile` 上站著的單位（不含倒下、撤離、消失）。 */
export function standingAtTile<U extends Present>(units: readonly U[], tile: Pos): U | undefined {
  return unitsOnTile(units, tile).find((u) => !u.downed && !u.escaped && !u.dismissed);
}

/** `u` 佔的格子裡離 `from` 最近（曼哈頓）的那一格；同距離 (y, x) 小（佔格是方塊，夾進方塊就是唯一最近）。 */
export function nearestTile(u: Footed, from: Pos): Pos {
  if (!isGiant(u)) return u.pos;
  let best = u.pos;
  let bestD = Infinity;
  for (const t of unitTiles(u)) {
    const d = Math.abs(t.x - from.x) + Math.abs(t.y - from.y);
    if (d < bestD || (d === bestD && (t.y < best.y || (t.y === best.y && t.x < best.x)))) {
      best = t;
      bestD = d;
    }
  }
  return best;
}

/** 部位綁格裡有 `tile` 的部位（一格的頭目、前殼為 `null`）。 */
export function partAtTile(u: Pick<UnitView, "parts">, tile: Pos): PartView | null {
  return (u.parts ?? []).find((p) => (p.tiles ?? []).some((t) => samePos(t, tile))) ?? null;
}

/** 命中判定的「打中的那一格」（`attack_rolled.hit_tile`，GB-1b；一格的目標沒有）。 */
export function hitTileOf(e: EventBase): Pos | null {
  if (!isAttackRolled(e)) return null;
  const v = e.hit_tile;
  return v != null && typeof v.x === "number" && typeof v.y === "number" ? v : null;
}

/** 單位 ID → 演出位置（找不到為 `null`）。 */
export type Locate = (id: unknown) => Pos | null;

/**
 * 一步事件的「單位 ID → 位置」：預設是視圖的 `pos`（巨型單位＝中心格）；依序 `note` 事件後，
 * 被帶 `hit_tile` 的命中判定打到的單位改成那一格（演出落在打中的那一格，8.1 第 2 點）。
 * 下一個打同一個目標、但沒有 `hit_tile` 的命中判定把它還原（例：一格的目標不會有）。
 */
export function hitLocator(units: readonly (Footed & { id: string })[]): { at: Locate; note(e: EventBase): void } {
  const byId = new Map(units.map((u) => [u.id, u] as const));
  const aimed = new Map<string, Pos>();
  const at: Locate = (id) => (typeof id === "string" ? (aimed.get(id) ?? byId.get(id)?.pos ?? null) : null);
  return {
    at,
    note(e) {
      if (typeof e.target_id !== "string") return;
      if (e.type === "attack_rolled") {
        const hit = hitTileOf(e);
        if (hit === null) aimed.delete(e.target_id);
        else aimed.set(e.target_id, hit);
        return;
      }
      // 沒有命中判定的傷害（例：技能的追加傷害）打到巨型單位：落在離來源最近的佔格
      const target = byId.get(e.target_id);
      if (e.type !== "damage_dealt" || target === undefined || !isGiant(target) || aimed.has(e.target_id)) return;
      const from = at(e.source_id);
      if (from !== null) aimed.set(e.target_id, nearestTile(target, from));
    },
  };
}

/** 動作加上 `target_part`（`null`＝本體，照原樣）。 */
export function withPart(action: Action, part: string | null): Action {
  return part === null ? action : ({ ...action, target_part: part } as Action);
}

/** 點（或滑過）巨型頭目某一格的結果。 */
export type GiantAim =
  /** 打本體：前殼、已破、還沒露出的部位格（`part`、`note` 給說明用）。 */
  | { kind: "body"; action: Action; part: PartView | null; note: string | null }
  /** 打這個部位（已加 `target_part`）。 */
  | { kind: "part"; action: Action; part: PartView }
  /** 這個部位現在打不到：不送出，`reason` 是伺服器的 `reason_zh`。 */
  | { kind: "blocked"; part: PartView; reason: string };

/** 前殼的名字（美術移植需求第 9 節）。 */
export const FRONT_SHELL_ZH = "前殼（本體）";

/**
 * 點巨型頭目 `tile` 時要做的事（T12）：`action` 是不帶部位的動作、`options` 是伺服器對這個動作給的部位選項。
 * 部位格打得到＝帶 `target_part`；打不到＝不送出；前殼、已破、未露出＝本體。
 */
export function giantAim(boss: Pick<UnitView, "parts">, options: readonly PartOption[], action: Action, tile: Pos): GiantAim {
  const part = partAtTile(boss, tile);
  if (part === null) return { kind: "body", action, part: null, note: null };
  const option = options.find((o) => o.part_id === part.id);
  if (part.broken) return { kind: "body", action, part, note: "已經破了" };
  if (!part.exposed) return { kind: "body", action, part, note: option?.reason_zh ?? null };
  if (option === undefined) return { kind: "body", action, part, note: null };
  if (option.ok) return { kind: "part", action: withPart(action, part.id), part };
  return { kind: "blocked", part, reason: option.reason_zh ?? "現在打不到" };
}

/** 滑過巨型頭目一格時資訊卡的一行（說明這一格會打到什麼）。 */
export function giantAimLine(aim: GiantAim): string {
  switch (aim.kind) {
    case "part":
      return `部位：${aim.part.name_zh}（點這一格打${aim.part.name_zh}）`;
    case "blocked":
      return `部位：${aim.part.name_zh}・打不到：${aim.reason}`;
    case "body":
      if (aim.part === null) return `${FRONT_SHELL_ZH}：點這一格打本體`;
      return `部位：${aim.part.name_zh}${aim.note === null ? "" : `・${aim.note}`}（點這一格＝打本體）`;
  }
}

/** 一個部位在選目標時的狀態（GB-4b 部位格標示用，和點擊判定同一份 tiles）。 */
export interface GiantPartState {
  id: string;
  name: string;
  tiles: Pos[];
  /** `ok` 打得到；`blocked` 打不到（灰掉）；`broken` 已破；`hidden` 還沒露出。 */
  state: "ok" | "blocked" | "broken" | "hidden";
  /** `blocked`、`hidden` 的原因（伺服器的 `reason_zh`）；其他為 `null`。 */
  reason: string | null;
}

/** 巨型頭目每個綁格部位的狀態；`options` 為 `null`（不是在選打它的動作）時只看破了沒、露出沒。 */
export function giantPartStates(boss: Pick<UnitView, "parts">, options: readonly PartOption[] | null): GiantPartState[] {
  return (boss.parts ?? [])
    .filter((p) => (p.tiles ?? []).length > 0)
    .map((p): GiantPartState => {
      const tiles = (p.tiles ?? []).map((t) => ({ x: t.x, y: t.y }));
      const option = options?.find((o) => o.part_id === p.id);
      if (p.broken) return { id: p.id, name: p.name_zh, tiles, state: "broken", reason: null };
      if (!p.exposed) return { id: p.id, name: p.name_zh, tiles, state: "hidden", reason: option?.reason_zh ?? null };
      if (option !== undefined && !option.ok) return { id: p.id, name: p.name_zh, tiles, state: "blocked", reason: option.reason_zh ?? null };
      return { id: p.id, name: p.name_zh, tiles, state: "ok", reason: null };
    });
}
