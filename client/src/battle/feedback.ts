// 地圖上的戰鬥回饋（Phase 3-9a，純函式）：一步的事件 → 回饋項目（浮動數字、字樣、行動連線、狀態彈出）。
// 畫布（`render/BattleRenderer.ts`）只負責把項目畫出來；位置一律由該步的 `view` 取得單位所在格。
// 位移（推、拉、衝鋒、跳躍、傳送、交換）不在這裡，見 `animation.ts`。
import { asEvent, type BattleView, type EventBase, type Pos } from "../api/types";
import { posKey, samePos } from "./geometry";
import { statusName } from "./glossary";

/** 浮動文字的語氣（決定顏色）：傷害紅、治療綠、護盾淺藍、字樣白、壞字樣橘、好字樣黃。 */
export type FloatTone = "damage" | "heal" | "shield" | "text" | "bad" | "good";

export interface FloatItem {
  kind: "float";
  pos: Pos;
  text: string;
  tone: FloatTone;
  /** 暴擊等要放大的數字。 */
  big: boolean;
  /** 同一格同一步的第幾個（0 起）；畫布依序往上錯開並延後出現，避免重疊。 */
  slot: number;
}

export interface LineItem {
  kind: "line";
  from: Pos;
  to: Pos;
}

export interface StatusItem {
  kind: "status";
  pos: Pos;
  /** 狀態的中文名稱。 */
  text: string;
  slot: number;
}

export type FeedbackItem = FloatItem | LineItem | StatusItem;

/** 事件型別 → 固定字樣（對照表放這一處；有條件的字樣在 `textFor` 內判斷）。 */
export const EVENT_WORDS: Readonly<Record<string, { text: string; tone: FloatTone }>> = {
  collided: { text: "撞擊！", tone: "bad" },
  unit_fell: { text: "墜落", tone: "bad" },
  entered_deadly_terrain: { text: "致命地形", tone: "bad" },
  status_resisted: { text: "抵抗", tone: "text" },
  push_resisted: { text: "抵抗", tone: "text" },
  unit_downed: { text: "擊倒", tone: "bad" },
  death_cheated: { text: "死裡逃生", tone: "good" },
  unit_revived: { text: "復活", tone: "good" },
  turn_skipped: { text: "無法行動", tone: "bad" },
  attack_intercepted: { text: "攔截", tone: "good" },
};

interface Spot {
  pos: Pos | null;
  text: string;
  tone: FloatTone;
  big?: boolean;
}

type Locate = (id: unknown) => Pos | null;

const num = (v: unknown): number => (typeof v === "number" ? v : 0);

function posOf(v: unknown): Pos | null {
  if (typeof v === "object" && v !== null && "x" in v && "y" in v) return v as Pos;
  return null;
}

function attackSpots(e: EventBase, at: Locate): Spot[] {
  const target = at(e.target_id);
  if (e.hit !== true) return [{ pos: target, text: "失手", tone: "text" }];
  const spots: Spot[] = [];
  if (num(e.backstab) > 0) spots.push({ pos: target, text: "背刺！", tone: "good", big: true });
  if (num(e.ambush) > 0) spots.push({ pos: target, text: "伏擊！", tone: "good", big: true });
  return spots;
}

/** 一個事件 → 要在地圖上顯示的浮動文字（沒有對應回饋回傳空陣列）。 */
function textFor(e: EventBase, at: Locate): Spot[] {
  const amount = num(e.amount);
  switch (e.type) {
    case "attack_rolled":
      return attackSpots(e, at);
    case "damage_dealt":
      return amount > 0 ? [{ pos: at(e.target_id), text: `−${amount}`, tone: "damage", big: e.crit === true }] : [];
    case "damage_redirected":
      return amount > 0 ? [{ pos: at(e.to_id), text: `−${amount}`, tone: "damage" }] : [];
    case "healed":
      return amount > 0 ? [{ pos: at(e.target_id), text: `＋${amount}`, tone: "heal" }] : [];
    case "shield_gained":
      return amount > 0 ? [{ pos: at(e.unit_id), text: `＋${amount}盾`, tone: "shield" }] : [];
    case "shield_absorbed":
      return num(e.absorbed) > 0 ? [{ pos: at(e.unit_id), text: `吸收 ${num(e.absorbed)}`, tone: "shield" }] : [];
    case "object_damaged":
      return amount > 0 ? [{ pos: posOf(e.pos), text: `−${amount}`, tone: "damage" }] : [];
    case "maneuver_rolled":
      return e.success === true ? [] : [{ pos: at(e.target_id), text: "抵抗", tone: "text" }];
    case "reaction_triggered":
      return e.reaction === "block" ? [{ pos: at(e.unit_id), text: "格擋", tone: "good" }] : [];
    default: {
      const word = EVENT_WORDS[e.type];
      if (word === undefined) return [];
      return [{ pos: at(e.unit_id ?? e.target_id) ?? posOf(e.pos), ...word, big: e.type === "collided" }];
    }
  }
}

/** 範圍的中心格：各格座標的平均，取範圍內最靠近平均的一格。 */
export function areaCenter(tiles: readonly Pos[]): Pos {
  const n = tiles.length;
  const cx = tiles.reduce((s, p) => s + p.x, 0) / n;
  const cy = tiles.reduce((s, p) => s + p.y, 0) / n;
  let best = tiles[0] as Pos;
  let bestD = Infinity;
  for (const p of tiles) {
    const d = (p.x - cx) ** 2 + (p.y - cy) ** 2;
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  return best;
}

/** 行動連線：攻擊者 → 單體目標；範圍技能 → 範圍的中心格。 */
function linesFor(e: EventBase, at: Locate): Array<{ from: Pos; to: Pos }> {
  if (e.type === "attack_rolled") {
    const from = at(e.attacker_id);
    const to = at(e.target_id);
    return from !== null && to !== null ? [{ from, to }] : [];
  }
  if (e.type === "skill_used" && Array.isArray(e.tiles)) {
    const tiles = e.tiles.map(posOf).filter((p): p is Pos => p !== null);
    const from = at(e.unit_id);
    if (from === null || tiles.length === 0) return [];
    const to = areaCenter(tiles);
    return samePos(from, to) ? [] : [{ from, to }];
  }
  return [];
}

/** 一步的事件 → 回饋項目（依事件順序；重複的連線只留一條）。 */
export function feedbackFor(events: readonly Record<string, unknown>[], view: BattleView): FeedbackItem[] {
  const positions = new Map(view.units.map((u) => [u.id, u.pos]));
  const at: Locate = (id) => (typeof id === "string" ? (positions.get(id) ?? null) : null);
  const items: FeedbackItem[] = [];
  const slots = new Map<string, number>();
  const nextSlot = (pos: Pos): number => {
    const k = posKey(pos);
    const n = slots.get(k) ?? 0;
    slots.set(k, n + 1);
    return n;
  };
  const lineKeys = new Set<string>();
  for (const raw of events) {
    const e = asEvent(raw);
    for (const line of linesFor(e, at)) {
      const k = `${posKey(line.from)}>${posKey(line.to)}`;
      if (lineKeys.has(k)) continue;
      lineKeys.add(k);
      items.push({ kind: "line", ...line });
    }
    for (const s of textFor(e, at)) {
      if (s.pos === null) continue;
      items.push({ kind: "float", pos: s.pos, text: s.text, tone: s.tone, big: s.big === true, slot: nextSlot(s.pos) });
    }
    if (e.type === "status_applied") {
      const pos = at(e.target_id);
      if (pos !== null) items.push({ kind: "status", pos, text: statusName(String(e.status_id)), slot: nextSlot(pos) });
    }
  }
  return items;
}
