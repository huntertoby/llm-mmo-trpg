// 致命格的標記（Phase 6V-2；docs/art/Fable審查.md 第 2 節 A）：整格大紅 X 改成四角小紅角標；滑過、路徑預覽、
// 選目標時整格疊淡紅。**只是畫法**：致命判定（`TileDraw.deadly`，由名詞表的 `deadly` 標籤來）與路徑預覽的規則都不動。
// 純函式：角標的座標、要疊淡紅的格子都由畫面資料算；Pixi 的畫法分開在 `drawLethalCorners`。
import type { Graphics } from "pixi.js";
import type { Pos } from "../api/types";
import type { DrawModel } from "../battle/drawModel";
import { HIGHLIGHT } from "../battle/glossary";
import type { PathDraw } from "../battle/pathPreview";

/** 角標的邊長（格子像素，48px 格約 6px）與線寬。 */
export const LETHAL_CORNER = 6;
export const LETHAL_CORNER_WIDTH = 1.5;
/** 角標離格緣的內縮。 */
export const LETHAL_CORNER_INSET = 2;
/** 角標的透明度；滑過、預覽、選目標時整格淡紅的透明度（同現在的危險區色）。 */
export const LETHAL_CORNER_ALPHA = 0.85;
export const LETHAL_TINT_ALPHA = 0.22;

/** 一條角標的折線：`[x0, y0, x1, y1, x2, y2]`（先橫再直，從角往內）。 */
export type CornerPath = readonly [number, number, number, number, number, number];

/** 四角角標的折線（格子像素；`t` 是格子邊長）。 */
export function lethalCornerPaths(t: number, size = LETHAL_CORNER, inset = LETHAL_CORNER_INSET): CornerPath[] {
  const a = inset;
  const b = t - inset;
  return [
    [a, a + size, a, a, a + size, a],
    [b - size, a, b, a, b, a + size],
    [b, b - size, b, b, b - size, b],
    [a + size, b, a, b, a, b - size],
  ];
}

/** 畫四角角標到 `g`（格子左上角為原點）。 */
export function drawLethalCorners(g: Graphics, t: number): void {
  for (const [x0, y0, x1, y1, x2, y2] of lethalCornerPaths(t)) g.moveTo(x0, y0).lineTo(x1, y1).lineTo(x2, y2);
  g.stroke({ width: LETHAL_CORNER_WIDTH, color: HIGHLIGHT.deadly, alpha: LETHAL_CORNER_ALPHA, cap: "round", join: "round" });
}

/** 畫面上「正在看」的格子：滑過、路徑預覽經過與停下的格子、預覽範圍、可選目標、已選的格子。 */
export interface LethalFocus {
  hover: Pos | null;
  path?: PathDraw;
  preview: readonly Pos[];
  attacks: readonly Pos[];
  picked: readonly Pos[];
}

const key = (p: Pos): string => `${p.x},${p.y}`;

/** 這些格子裡哪些是致命格（去重、依 (y, x) 排序）；不是致命格的不疊淡紅。 */
export function lethalTintCells(model: DrawModel, focus: LethalFocus): Pos[] {
  const deadly = new Set(model.tiles.filter((t) => t.deadly).map(key));
  const seen = new Map<string, Pos>();
  const add = (p: Pos | null | undefined): void => {
    if (p == null) return;
    const k = key(p);
    if (deadly.has(k) && !seen.has(k)) seen.set(k, { x: p.x, y: p.y });
  };
  add(focus.hover);
  for (const p of focus.preview) add(p);
  for (const p of focus.attacks) add(p);
  for (const p of focus.picked) add(p);
  const path = focus.path;
  if (path !== undefined) {
    for (const d of path.dots) add(d.pos);
    for (const f of path.frames) add(f.pos);
    for (const seg of path.segments) add(seg.to);
    for (const b of path.bangs) add(b);
    for (const s of path.slipStops) {
      add(s.pos);
      for (const p of s.slide) add(p);
    }
    add(path.missEnd);
  }
  return [...seen.values()].sort((a, b) => a.y - b.y || a.x - b.x);
}
