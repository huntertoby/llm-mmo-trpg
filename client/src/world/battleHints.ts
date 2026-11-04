// 戰鬥短提示（Phase 6F-2；09 9.6.9 #99「戰鬥中出現短提示，可以關掉」；玩法 PM 筆記 U1）。
// 伺服器在大世界戰鬥的 `WorldView.battle_hints` 給這場可能出現的提示（新手任務這一步的 `teach` ＋通用的四種）；
// 這裡照戰況判斷哪一則現在該出現。每種提示每個角色只出一次、「不再顯示提示」——6F-4（6F-2b）起都記在角色身上
// （伺服器的 `WorldView.hints`；出現時送 `hint_seen`、關掉送 `hints_off`，設定裡的「重新顯示提示」送
// `hints_reset`）。開場、教學、升級畫面看過了也記在同一份紀錄。提示只影響畫面，不改戰鬥結果。
import type { BattleHint, BattleView, UnitView, WorldAction, WorldHints } from "../api/types";

/** `hints.seen` 裡「開場看過了」的 ID（6F-4）。 */
export const OPENING_SEEN = "opening";
/** `hints.seen` 裡教學看過了的 ID（`lesson:allocate`、`lesson:flash`、`lesson:reflash`）。 */
export function lessonSeenId(kind: string): string {
  return `lesson:${kind}`;
}

/** 伺服器記的提示紀錄（沒有＝全部沒看過、沒關）。 */
export function hintsOf(hints: WorldHints | null | undefined): { seen: ReadonlySet<string>; off: boolean } {
  return { seen: new Set(hints?.seen ?? []), off: hints?.off ?? false };
}

/** 記下出過的提示、看過的開場與教學（`ids`），或看過的升級畫面（`level`）。 */
export function hintSeenAction(ids: readonly string[], level?: number): WorldAction {
  return level === undefined ? { kind: "hint_seen", ids: [...ids] } : { kind: "hint_seen", ids: [...ids], level };
}

/** 「不再顯示提示」。 */
export const HINTS_OFF_ACTION: WorldAction = { kind: "hints_off", off: true };
/** 設定裡的「重新顯示提示」：清掉出過的提示、教學紀錄與「不再顯示」。 */
export const HINTS_RESET_ACTION: WorldAction = { kind: "hints_reset" };

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
