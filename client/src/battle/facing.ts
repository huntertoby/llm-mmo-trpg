// 朝向與背刺（Phase 3D-8d，純函式）：單位圖示上的小箭頭、背後格與文字。
import type { Facing, Pos, UnitView } from "../api/types";
import { DIRECTION_DELTA } from "./targeting";

const FACING_TEXT: Readonly<Record<Facing, string>> = {
  north: "北 ↑",
  east: "東 →",
  south: "南 ↓",
  west: "西 ←",
};

/** 單位資訊的一行：「東 →（背後 (2, 3)）」。 */
export function facingText(u: Pick<UnitView, "facing" | "pos">): string {
  const back = backTile(u.pos, u.facing);
  return `${FACING_TEXT[u.facing]}（背後 (${back.x}, ${back.y})）`;
}

/** 背後格：位置 ＋ 朝向的反方向（只算相鄰的那一格；可能在地圖外）。 */
export function backTile(pos: Pos, facing: Facing): Pos {
  const d = DIRECTION_DELTA[facing];
  return { x: pos.x - d.dx, y: pos.y - d.dy };
}

/**
 * 橢圓底圈外緣的朝向尖角（紙娃娃，Phase 3-16b）：底邊貼著中心 (cx, cy)、半徑 (rx, ry) 的橢圓，
 * 尖端朝 `facing` 往外 `size`；回傳 `[x0, y0, x1, y1, x2, y2]`（第一組為尖端）。
 */
export function ringArrow(facing: Facing, cx: number, cy: number, rx: number, ry: number, size = 6): number[] {
  const d = DIRECTION_DELTA[facing];
  const tip = { x: cx + d.dx * (rx + size), y: cy + d.dy * (ry + size) };
  const bx = cx + d.dx * (rx - 1);
  const by = cy + d.dy * (ry - 1);
  const half = size * 0.9;
  return [tip.x, tip.y, bx - d.dy * half, by + d.dx * half, bx + d.dy * half, by - d.dx * half];
}

/**
 * 單位圖示外緣的小三角形箭頭（相對於格子中心的頂點座標 `[x0, y0, x1, y1, x2, y2]`）：尖端朝向
 * `facing`，底邊貼著半徑 `r` 的圓。
 */
export function facingArrow(facing: Facing, r: number, size = 6): number[] {
  const d = DIRECTION_DELTA[facing];
  const tip = { x: d.dx * (r + size), y: d.dy * (r + size) };
  const base = { x: d.dx * (r - 1), y: d.dy * (r - 1) };
  const side = { x: -d.dy * size, y: d.dx * size }; // 垂直於朝向
  return [tip.x, tip.y, base.x + side.x, base.y + side.y, base.x - side.x, base.y - side.y];
}
