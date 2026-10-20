// 環境預告 → 格子標記與側欄文字（純函式）。
// 伺服器回應的 `telegraph` 是「下一次環境回合（本輪結束時）會發生的變化」；這裡整理成
// 格子上的小圖示（每格一個，依優先序）與滑過時的說明。
import type { BattleView, Pos, TelegraphChange, TelegraphOut } from "../api/types";
import { posKey } from "./geometry";

type BombOut = NonNullable<TelegraphOut["bombs"]>[number];

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
  zone_moved: { glyph: "域", color: 0xff8a5c, priority: 3 },
  zone_expired: { glyph: "散", color: 0xc0c0c0, priority: 1 },
  // 定時炸彈（Phase 3D-8b）：爆炸的格子、帶著炸彈的單位（標倒數）、炸彈目前的波及範圍
  bomb_exploded: { glyph: "炸", color: 0xff3b30, priority: 8 },
  bomb: { glyph: "炸", color: 0xff7a1a, priority: 9 },
  bomb_area: { glyph: "炸", color: 0xff7a1a, priority: 1 },
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

function changePositions(c: TelegraphChange, view: BattleView): Pos[] {
  // 持續區域（Phase 3D-5）的預告帶著整個區域的格子：每格都標記
  if (c.tiles !== undefined && c.tiles.length > 0) return [...c.tiles];
  const pos = changePos(c, view);
  return pos === null ? [] : [pos];
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
    for (const pos of changePositions(c, view)) addMark(byTile, c, pos);
  }
  for (const b of t.bombs ?? []) {
    const text = bombChange(t, b)?.text ?? b.text; // 下一次就爆炸的炸彈已有變化那一行，不重複
    for (const pos of b.tiles) addBombMark(byTile, "bomb_area", pos, text, "炸");
    addBombMark(byTile, "bomb", b.pos, text, String(b.remaining));
  }
  return [...byTile.values()].sort((a, b) => a.pos.y - b.pos.y || a.pos.x - b.pos.x);
}

function addBombMark(byTile: Map<string, TelegraphMark>, kind: string, pos: Pos, text: string, glyph: string): void {
  const style = markStyle(kind);
  const key = posKey(pos);
  const mark = byTile.get(key);
  if (mark === undefined) {
    byTile.set(key, { pos, kind, glyph, color: style.color, texts: [text] });
    return;
  }
  if (!mark.texts.includes(text)) mark.texts.push(text);
  if (style.priority > markStyle(mark.kind).priority) {
    mark.kind = kind;
    mark.glyph = glyph;
    mark.color = style.color;
  }
}

function addMark(byTile: Map<string, TelegraphMark>, c: TelegraphChange, pos: Pos): void {
  const style = markStyle(c.kind);
  const key = posKey(pos);
  const mark = byTile.get(key);
  if (mark === undefined) {
    byTile.set(key, { pos, kind: c.kind, glyph: style.glyph, color: style.color, texts: [c.text] });
    return;
  }
  mark.texts.push(c.text);
  if (style.priority > markStyle(mark.kind).priority) {
    mark.kind = c.kind;
    mark.glyph = style.glyph;
    mark.color = style.color;
  }
}

/** 滑過格子時要顯示的預告說明（沒有時空陣列）。 */
export function marksTextAt(marks: readonly TelegraphMark[], tile: Pos | null): string[] {
  if (tile === null) return [];
  return marks.find((m) => m.pos.x === tile.x && m.pos.y === tile.y)?.texts ?? [];
}

/** 下一次環境回合就會爆炸的炸彈，預告的「變化」裡已經有一行（同一個攜帶者）。 */
function bombChange(t: TelegraphOut, b: BombOut): TelegraphChange | undefined {
  if (!b.explodes) return undefined;
  return t.changes.find((c) => c.kind === "bomb_exploded" && c.unit_id === b.unit_id);
}

/** 側欄的文字摘要：變化、還在燃燒的物件、下一輪的地圖事件。 */
export function telegraphLines(t: TelegraphOut): string[] {
  return [
    ...t.changes.map((c) => c.text),
    ...(t.bombs ?? []).filter((b) => bombChange(t, b) === undefined).map((b) => b.text),
    ...t.burning.map((b) => b.text),
    ...t.upcoming.map((u) => u.text),
  ];
}

export function telegraphIsEmpty(t: TelegraphOut): boolean {
  return t.changes.length === 0 && (t.bombs ?? []).length === 0 && t.burning.length === 0 && t.upcoming.length === 0;
}
