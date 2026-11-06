// 戰鬥版 HUD 的半透明避讓（Phase 6A-4g；docs/archive/art/6A-4d至6M-3六段檢查.md 第 7 節第 3 項）：地圖鋪滿整個舞台、HUD 疊在上面，
// 沿用 6B-5 出口的規則——HUD 塊底下（含半格緩衝）有單位或可點的格子時，那一塊變半透明（0.38，CSS），滑上去恢復。
// 純函式：格子 → 畫面矩形、要避讓的格子、哪些塊要變半透明。量 DOM 的部分在 `screens/battle/useHudFade.ts`。
import type { Pos } from "../api/types";
import type { Highlights } from "../render/BattleRenderer";
import type { DrawModel } from "./drawModel";
import { heightAt, stagePixels, tileLift, topReserve, type HeightGrid } from "./elevation";
import { TILE_SIZE } from "./geometry";
import type { ClientRect } from "./stageLayout";

/** 會疊在地圖上的 HUD 塊（底部技能列與回合操作在地圖可用區域外，不列）。 */
// 6F-7（美術 PM：選取說明框改成不透明）：選取面板不再變淡；自動填滿時地圖本來就讓開左欄（`stageLayout.hudSideInsets`）
export const FADE_BLOCKS = ["hero", "order", "corner", "telegraph", "summon", "pin", "log"] as const;
export type FadeBlockId = (typeof FADE_BLOCKS)[number];

/** 各塊的選擇器（在 `.battle-screen.hud-a` 裡找）。 */
export const FADE_SELECTORS: Readonly<Record<FadeBlockId, string>> = {
  hero: ".bhud-hero",
  order: ".bhud-top .turn-bar",
  corner: ".bhud-corner",
  telegraph: ".bhud-telegraph",
  summon: ".bhud-right > .summon-panel",
  pin: ".bhud-right > .unit-pin-dock",
  log: ".log-dock",
};

/** 半透明的不透明度（同 6B-5 出口，CSS 在 battle-hud.css）。 */
export const FADE_OPACITY = 0.38;

/** 格子（抬高後的頂面）在畫面上的矩形；`canvas` 是畫布元素的實際矩形（縮放由實際寬高 ÷ 模型像素算）。 */
export function tileClientRect(p: Pos, grid: HeightGrid, canvas: ClientRect, tile = TILE_SIZE): ClientRect {
  const px = stagePixels(grid, tile);
  const sx = px.width > 0 ? canvas.width / px.width : 0;
  const sy = px.height > 0 ? canvas.height / px.height : 0;
  const top = topReserve(grid) + p.y * tile - tileLift(heightAt(grid, p));
  return { left: canvas.left + p.x * tile * sx, top: canvas.top + top * sy, width: tile * sx, height: tile * sy };
}

const posKey = (p: Pos): string => `${p.x},${p.y}`;

/** HUD 要讓開的格子：場上的單位，以及現在可以點的格子（移動、攻擊／目標、方向、攀跳落點）。去重、依座標排序。 */
export function fadeCells(model: Pick<DrawModel, "units">, h: Pick<Highlights, "moves" | "attacks" | "directions" | "vaults">): Pos[] {
  const out = new Map<string, Pos>();
  const add = (p: Pos) => out.set(posKey(p), { x: p.x, y: p.y });
  for (const u of model.units) add({ x: u.x, y: u.y });
  for (const p of h.moves) add(p);
  for (const p of h.attacks) add(p);
  for (const d of h.directions) add(d.pos);
  for (const v of h.vaults ?? []) add(v.pos);
  return [...out.values()].sort((a, b) => a.y - b.y || a.x - b.x);
}

function overlaps(a: ClientRect, b: ClientRect, pad: number): boolean {
  return a.left - pad < b.left + b.width && b.left < a.left + a.width + pad && a.top - pad < b.top + b.height && b.top < a.top + a.height + pad;
}

/** 底下（含半格緩衝）有 `cells` 的 HUD 塊，依 `FADE_BLOCKS` 的順序；量不到（`null`）或大小為 0 的塊不算。 */
export function fadedHudBlocks(blocks: Partial<Record<FadeBlockId, ClientRect | null>>, cells: readonly ClientRect[]): FadeBlockId[] {
  return FADE_BLOCKS.filter((id) => {
    const r = blocks[id];
    if (r == null || r.width <= 0 || r.height <= 0) return false;
    return cells.some((c) => overlaps(r, c, c.width / 2));
  });
}
