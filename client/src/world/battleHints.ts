// 戰鬥短提示（Phase 6F-2；09 9.6.9 #99「戰鬥中出現短提示，可以關掉」；玩法 PM 筆記 U1）。
// 伺服器在大世界戰鬥的 `WorldView.battle_hints` 給這場可能出現的提示（新手任務這一步的 `teach` ＋通用的四種）；
// 這裡照戰況判斷哪一則現在該出現。每種提示每個角色只出一次（記在本機 localStorage，鍵含角色 ID）；
// 「不再顯示提示」也記在本機。提示只影響畫面，不改戰鬥結果。
import type { BattleHint, BattleView, UnitView } from "../api/types";

type Store = Pick<Storage, "getItem" | "setItem">;

/** 全部關掉（本機）。 */
export const HINTS_OFF_KEY = "trpg.battleHints.off";
/** 某個角色看過的提示 ID（本機；JSON 陣列）。 */
export function seenKey(characterId: string): string {
  return `trpg.battleHints.seen.${characterId}`;
}

function storage(): Store | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export function readHintsOff(store: Store | null = storage()): boolean {
  try {
    return store?.getItem(HINTS_OFF_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeHintsOff(on: boolean, store: Store | null = storage()): void {
  try {
    store?.setItem(HINTS_OFF_KEY, on ? "1" : "0");
  } catch {
    // 私密視窗或封鎖網站資料：只是不記住
  }
}

export function readSeen(characterId: string, store: Store | null = storage()): Set<string> {
  try {
    const raw = store?.getItem(seenKey(characterId));
    const parsed: unknown = raw == null ? [] : JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : []);
  } catch {
    return new Set();
  }
}

export function writeSeen(characterId: string, seen: ReadonlySet<string>, store: Store | null = storage()): void {
  try {
    store?.setItem(seenKey(characterId), JSON.stringify([...seen].sort()));
  } catch {
    // 同上
  }
}

/** 事件（`StepOut.events` 的元素）裡提示會看的欄位。 */
export interface HintEvent {
  type?: unknown;
  unit_id?: unknown;
  mode?: unknown;
}

function tileAt(view: BattleView, x: number, y: number) {
  return view.tiles.find((t) => t.x === x && t.y === y);
}

function alive(u: UnitView): boolean {
  return u.hp > 0 && u.downed !== true;
}

/** 這則提示的觸發條件現在成立嗎（`view`＝目前畫出來的戰場，`events`＝這次回應的事件）。 */
export function hintFires(hint: BattleHint, view: BattleView, heroId: string, events: readonly HintEvent[]): boolean {
  const hero = view.units.find((u) => u.id === heroId);
  const team = hero?.team ?? "player";
  switch (hint.trigger) {
    case "battle_start":
      return true;
    case "enemy_on_water":
      return view.units.some((u) => u.team !== team && alive(u) && tileAt(view, u.pos.x, u.pos.y)?.surface === "water");
    case "water_present":
      return view.tiles.some((t) => t.surface === "water");
    case "ice_present":
      return view.tiles.some((t) => t.surface === "ice");
    case "trap_present":
      return view.traps.length > 0;
    case "lethal_terrain": {
      const deadly = new Set(hint.terrains ?? []);
      return view.tiles.some((t) => deadly.has(t.terrain));
    }
    case "reaction":
      return (hero?.reaction_rules.length ?? 0) > 0 || events.some((e) => e.type === "reaction_triggered");
    case "pushed": {
      const mine = new Set(view.units.filter((u) => u.team === team).map((u) => u.id));
      return events.some((e) => e.type === "unit_moved" && e.mode === "forced" && typeof e.unit_id === "string" && mine.has(e.unit_id));
    }
    default:
      return false;
  }
}

/** 現在要出的提示：照伺服器給的順序，第一則成立、還沒看過的；全部關掉或沒有時 `null`。 */
export function nextHint(
  hints: readonly BattleHint[],
  view: BattleView,
  heroId: string,
  events: readonly HintEvent[],
  seen: ReadonlySet<string>,
  off: boolean,
): BattleHint | null {
  if (off) return null;
  return hints.find((h) => !seen.has(h.id) && hintFires(h, view, heroId, events)) ?? null;
}
