// 刻印的符文（Phase 3-23）：格子上的小紋樣（施放者陣營色外框＋元素色內紋）、資訊卡文字（純函式）。
import type { BattleView, Pos, RuneView } from "../api/types";
import { TEAM_COLORS } from "./glossary";
import { ELEMENT_COLORS } from "../render/palette";
import { hexToNumber } from "./vfxPalette";

/** 標籤符文（不帶元素）的內紋顏色。 */
export const TAG_RUNE_COLOR = 0xd8d0b8;

/** 符文的一個繪製筆畫：位置、陣營色、元素色；同一格有多個符文時各占一個象限（`slot`／`slots`）。 */
export interface RuneDraw {
  id: number;
  x: number;
  y: number;
  /** 外框：刻下符文的施放者的陣營色。 */
  teamColor: number;
  /** 內紋：元素色（標籤符文為 `TAG_RUNE_COLOR`）。 */
  color: number;
  /** 同一格的第幾個符文（依編號）與該格共有幾個。 */
  slot: number;
  slots: number;
  /** 剩 1 輪時畫淡一點，提醒快消失了。 */
  fading: boolean;
}

/** 視圖的符文；舊的錄製回應（3-23 之前）沒有 `runes` 欄位，視為沒有符文。 */
export function runesOf(view: BattleView): readonly RuneView[] {
  return view.runes ?? [];
}

export function runeColor(r: RuneView): number {
  const colors = r.element === null ? undefined : ELEMENT_COLORS[r.element];
  return colors === undefined ? TAG_RUNE_COLOR : hexToNumber(colors.accent);
}

/** 每個符文一筆（依編號）；同一格的符文各占一個象限。 */
export function runeDraws(view: BattleView): RuneDraw[] {
  const runes = [...runesOf(view)].sort((a, b) => a.id - b.id);
  const perCell = new Map<string, number>();
  for (const r of runes) {
    const key = `${r.pos.x},${r.pos.y}`;
    perCell.set(key, (perCell.get(key) ?? 0) + 1);
  }
  const seen = new Map<string, number>();
  return runes.map((r) => {
    const key = `${r.pos.x},${r.pos.y}`;
    const slot = seen.get(key) ?? 0;
    seen.set(key, slot + 1);
    return {
      id: r.id,
      x: r.pos.x,
      y: r.pos.y,
      teamColor: TEAM_COLORS[r.team],
      color: runeColor(r),
      slot,
      slots: perCell.get(key) ?? 1,
      fading: r.remaining <= 1,
    };
  });
}

/** 一個符文的說明：「刻印流英雄的雷紋，剩 2 輪」。 */
export function runeLine(r: RuneView, ownerName: string): string {
  return `${ownerName}的${r.name_zh}，剩 ${r.remaining} 輪`;
}

/** 這一格上的符文（依編號）。 */
export function runesAt(view: BattleView, pos: Pos): RuneView[] {
  return runesOf(view)
    .filter((r) => r.pos.x === pos.x && r.pos.y === pos.y)
    .sort((a, b) => a.id - b.id);
}

export function ownerNameOf(view: BattleView, r: RuneView): string {
  return view.units.find((u) => u.id === r.owner_id)?.name_zh ?? r.owner_id;
}
