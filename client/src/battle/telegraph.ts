// 環境預告 → 格子標記與側欄文字（純函式）。
// 伺服器回應的 `telegraph` 是「下一次環境回合（本輪結束時）會發生的變化」；這裡整理成
// 格子上的小圖示（每格一個，依優先序）與滑過時的說明。
import type { BattleView, Pos, TelegraphChange, TelegraphOut } from "../api/types";
import { posKey } from "./geometry";

export type MarkKind = TelegraphChange["kind"];

export interface MarkStyle {
  glyph: string;
  color: number;
  /** 數字越大越優先（同一格有多項變化時，圖示取優先序最高的）。 */
  priority: number;
}

/** 預告圖示的樣式（之後換美術只改這裡）。 */
export const MARK_STYLES: Readonly<Record<string, MarkStyle>> = {
  object_exploded: { glyph: "爆", color: 0xff3b30, priority: 8 },
  unit_downed: { glyph: "倒", color: 0xff3b30, priority: 7 },
  unit_damaged: { glyph: "傷", color: 0xff6a3d, priority: 6 },
  object_ignited: { glyph: "燃", color: 0xff9a2e, priority: 5 },
  object_destroyed: { glyph: "毀", color: 0xc0a080, priority: 4 },
  unit_spawned: { glyph: "援", color: 0xb06bff, priority: 4 },
  terrain: { glyph: "地", color: 0xd0a060, priority: 3 },
  surface: { glyph: "面", color: 0x7fe3ff, priority: 2 },
};

const FALLBACK_STYLE: MarkStyle = { glyph: "?", color: 0xffffff, priority: 0 };

export function markStyle(kind: string): MarkStyle {
  return MARK_STYLES[kind] ?? FALLBACK_STYLE;
}

export interface TelegraphMark {
  pos: Pos;
  /** 這一格優先序最高的變化。 */
  kind: string;
  glyph: string;
  color: number;
  /** 這一格所有變化的說明。 */
  texts: string[];
}

function changePos(c: TelegraphChange, view: BattleView): Pos | null {
  if (c.pos != null) return c.pos;
  if (c.unit_id != null) return view.units.find((u) => u.id === c.unit_id)?.pos ?? null;
  return null;
}

/** 每格一個標記（依優先序取圖示，說明合併）。沒有位置也找不到單位的變化不標記（仍會列在側欄）。 */
export function telegraphMarks(t: TelegraphOut, view: BattleView): TelegraphMark[] {
  const byTile = new Map<string, TelegraphMark>();
  for (const c of t.changes) {
    const pos = changePos(c, view);
    if (pos === null) continue;
    const style = markStyle(c.kind);
    const key = posKey(pos);
    const mark = byTile.get(key);
    if (mark === undefined) {
      byTile.set(key, { pos, kind: c.kind, glyph: style.glyph, color: style.color, texts: [c.text] });
      continue;
    }
    mark.texts.push(c.text);
    if (style.priority > markStyle(mark.kind).priority) {
      mark.kind = c.kind;
      mark.glyph = style.glyph;
      mark.color = style.color;
    }
  }
  return [...byTile.values()].sort((a, b) => a.pos.y - b.pos.y || a.pos.x - b.pos.x);
}

/** 滑過格子時要顯示的預告說明（沒有時空陣列）。 */
export function marksTextAt(marks: readonly TelegraphMark[], tile: Pos | null): string[] {
  if (tile === null) return [];
  return marks.find((m) => m.pos.x === tile.x && m.pos.y === tile.y)?.texts ?? [];
}

/** 側欄的文字摘要：變化、還在燃燒的物件、下一輪的地圖事件。 */
export function telegraphLines(t: TelegraphOut): string[] {
  return [...t.changes.map((c) => c.text), ...t.burning.map((b) => b.text), ...t.upcoming.map((u) => u.text)];
}

export function telegraphIsEmpty(t: TelegraphOut): boolean {
  return t.changes.length === 0 && t.burning.length === 0 && t.upcoming.length === 0;
}
