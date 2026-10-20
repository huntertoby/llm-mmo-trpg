// 複合技能（位移 → 動作，Phase 3F-3b）的兩段選取（純函式）。
// 伺服器的合法動作已經是「位移段選取 × 動作段選取」：`target_pos`／`target_id` 是位移段，
// `followup_target`（方向、單位、物件，或 null＝以落點為中心的形狀）是動作段。這裡把它們分成：
// 第 1 段＝位移段（點落點格，或衝鋒／瞬步點目標單位）、第 2 段＝動作段（點方向、點目標，或確認施放）。
import type { Action, BattleView, Direction, Pos } from "../api/types";
import { posKey, samePos } from "./geometry";

const DELTA: Readonly<Record<Direction, { dx: number; dy: number }>> = {
  north: { dx: 0, dy: -1 },
  east: { dx: 1, dy: 0 },
  south: { dx: 0, dy: 1 },
  west: { dx: -1, dy: 0 },
};
const ORDER: readonly Direction[] = ["north", "east", "south", "west"];
const DIRECTION_NAME: Readonly<Record<Direction, string>> = { north: "北", east: "東", south: "南", west: "西" };
const ARROW: Readonly<Record<Direction, string>> = { north: "↑", east: "→", south: "↓", west: "←" };

type UseSkillAction = Extract<Action, { type: "use_skill" }>;

/** 動作段的一個選取。 */
export interface CompositeSecond {
  /** `d:<方向>`、`u:<單位>`、`o:<物件>`，或 `c`（以落點為中心，不用選）。 */
  key: string;
  kind: "direction" | "unit" | "object" | "center";
  direction: Direction | null;
  targetId: string | null;
  action: UseSkillAction;
}

/** 位移段的一個選取（落點格或目標單位）與它之後能接的動作段選取。 */
export interface CompositeFirst {
  /** `p:<x>,<y>`（位移到這一格）或 `u:<單位>`（衝向／瞬步到這個單位）。 */
  key: string;
  pos: Pos | null;
  unitId: string | null;
  seconds: CompositeSecond[];
}

export type CompositeSet = Map<string, CompositeFirst>;

function secondOf(action: UseSkillAction): CompositeSecond {
  const f = action.followup_target ?? null;
  if (f?.direction != null) {
    return { key: `d:${f.direction}`, kind: "direction", direction: f.direction, targetId: null, action };
  }
  if (f?.target_id != null) return { key: `u:${f.target_id}`, kind: "unit", direction: null, targetId: f.target_id, action };
  if (f?.target_object_id != null) {
    return { key: `o:${f.target_object_id}`, kind: "object", direction: null, targetId: f.target_object_id, action };
  }
  return { key: "c", kind: "center", direction: null, targetId: null, action };
}

/** 複合技能的合法動作 → 位移段選取（依出現順序）各自能接的動作段選取。 */
export function buildComposite(actions: readonly Action[]): CompositeSet {
  const out: CompositeSet = new Map();
  for (const a of actions) {
    if (a.type !== "use_skill") continue;
    const pos = a.target_pos ?? null;
    const key = pos !== null ? `p:${posKey(pos)}` : a.target_id != null ? `u:${a.target_id}` : null;
    if (key === null) continue;
    let first = out.get(key);
    if (first === undefined) {
      first = { key, pos, unitId: pos === null ? (a.target_id ?? null) : null, seconds: [] };
      out.set(key, first);
    }
    const second = secondOf(a);
    if (!first.seconds.some((s) => s.key === second.key)) first.seconds.push(second);
  }
  return out;
}

/** 這個位移段選取只剩「以落點為中心」一種動作段：點一下就能施放（不必再選）。 */
export function soleCenter(first: CompositeFirst): CompositeSecond | null {
  const only = first.seconds.length === 1 ? first.seconds[0] : undefined;
  return only !== undefined && only.kind === "center" ? only : null;
}

function unitsAt(view: BattleView, tile: Pos): string[] {
  return view.units.filter((u) => !u.escaped && !u.dismissed && samePos(u.pos, tile)).map((u) => u.id);
}

/** 位移段：`tile` 上可以選的落點格或目標單位的鍵（沒有時 `null`）。 */
export function firstKeyAt(set: CompositeSet, view: BattleView, tile: Pos): string | null {
  const byPos = set.get(`p:${posKey(tile)}`);
  if (byPos !== undefined) return byPos.key;
  for (const id of unitsAt(view, tile)) {
    if (set.has(`u:${id}`)) return `u:${id}`;
  }
  return null;
}

/** 位移段選取在戰場上的位置（落點格，或目標單位目前所在的格子）。 */
export function firstPos(first: CompositeFirst, view: BattleView): Pos | null {
  if (first.pos !== null) return first.pos;
  return view.units.find((u) => u.id === first.unitId)?.pos ?? null;
}

/** 動作段：選了位移段 `first` 之後，戰場上點 `tile` 對應的選取。方向型點落點旁邊的格子，單體點目標，
 * 以落點為中心的形狀點落點本身；落點未知（衝向單位）時方向與中心只能用面板按鈕。 */
export function secondAt(first: CompositeFirst, view: BattleView, tile: Pos): CompositeSecond | null {
  for (const s of first.seconds) {
    if (s.kind === "unit" && s.targetId !== null && unitsAt(view, tile).includes(s.targetId)) return s;
    if (s.kind === "object" && s.targetId !== null) {
      const obj = view.objects.find((o) => o.id === s.targetId);
      if (obj !== undefined && samePos(obj.pos, tile)) return s;
    }
  }
  const landing = first.pos;
  if (landing === null) return null;
  for (const s of first.seconds) {
    if (s.kind !== "direction" || s.direction === null) continue;
    const d = DELTA[s.direction];
    if (landing.x + d.dx === tile.x && landing.y + d.dy === tile.y) return s;
  }
  if (samePos(landing, tile)) return first.seconds.find((s) => s.kind === "center") ?? null;
  return null;
}

/** 動作段在戰場上可以點的格子（紅框／方向箭頭）。 */
export function secondTiles(first: CompositeFirst, view: BattleView): { targets: Pos[]; directions: { pos: Pos; direction: Direction }[] } {
  const targets: Pos[] = [];
  const directions: { pos: Pos; direction: Direction }[] = [];
  for (const s of first.seconds) {
    if (s.kind === "unit") {
      const at = view.units.find((u) => u.id === s.targetId)?.pos;
      if (at !== undefined) targets.push(at);
    } else if (s.kind === "object") {
      const at = view.objects.find((o) => o.id === s.targetId)?.pos;
      if (at !== undefined) targets.push(at);
    } else if (s.kind === "direction" && s.direction !== null && first.pos !== null) {
      const d = DELTA[s.direction];
      directions.push({ pos: { x: first.pos.x + d.dx, y: first.pos.y + d.dy }, direction: s.direction });
    } else if (s.kind === "center" && first.pos !== null) {
      targets.push(first.pos);
    }
  }
  return { targets, directions };
}

/** 動作段的選項（面板按鈕）：依 北東南西、單位、物件、中心 排序，附中文標籤。 */
export function secondChoices(first: CompositeFirst, view: BattleView): { second: CompositeSecond; label: string }[] {
  const rank = (s: CompositeSecond): number =>
    s.kind === "direction" ? ORDER.indexOf(s.direction ?? "north") : s.kind === "unit" ? 10 : s.kind === "object" ? 20 : 30;
  return [...first.seconds]
    .sort((a, b) => rank(a) - rank(b) || a.key.localeCompare(b.key))
    .map((second) => {
      switch (second.kind) {
        case "direction":
          return { second, label: `${ARROW[second.direction ?? "north"]} 向${DIRECTION_NAME[second.direction ?? "north"]}` };
        case "unit":
          return { second, label: `攻擊 ${view.units.find((u) => u.id === second.targetId)?.name_zh ?? second.targetId}` };
        case "object":
          return { second, label: `攻擊物件 ${second.targetId ?? ""}` };
        case "center":
          return { second, label: "以落點為中心施放" };
      }
    });
}

/** 兩段選取的提示文字。 */
export function compositePrompt(first: CompositeFirst | null, count: number): string {
  if (first === null) {
    return `第 1 段（位移）：點選落點或目標（紅框 ${count} 個）。只有「以落點為中心」的技能點一下就會施放。Esc／右鍵取消。`;
  }
  const where = first.pos !== null ? `落點 (${first.pos.x}, ${first.pos.y})` : "目標";
  return `第 2 段（動作）：已選定${where}，點方向箭頭或目標，或用下方按鈕；紫色格子是第二段的範圍。再點其他落點可改選。`;
}
