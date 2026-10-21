// 高度「整格抬高」（Phase 3-19，美術定案 B：docs/art/3-18倒地與高度.md 第 5 節；純函式）。
// 高 h 的格子頂面往上移 `tileLift(h)` 模型像素，頂面底緣到地面畫崖面；畫布上方預留最高格的抬高量。
// 座標系：「世界座標」＝ 未抬高的格子座標（`tileOrigin`），畫布座標 ＝ 世界座標往下移 `topReserve`。
// 位移一律由 `tileLift` 提供，繪圖、點選、預覽、特效都不自己乘 RAISE。
import type { Pos } from "../api/types";
import { TILE_SIZE, type GridSize } from "./geometry";

/** 每一階高度的抬高量（模型像素）。 */
export const RAISE = 6;

/** 升降動畫的時間（一般速度，毫秒）。 */
export const LIFT_MS = 300;

/** 帶有格子高度的地圖（`DrawModel` 符合）；沒有 `tiles` 時視為平地。 */
export interface HeightGrid extends GridSize {
  tiles?: ReadonlyArray<{ height: number }>;
}

/** 高 h（可為補間中的小數）的格子往上抬多少模型像素；負值視為 0。 */
export function tileLift(h: number): number {
  return Math.max(0, h) * RAISE;
}

/** 格子高度；地圖外或沒有高度資料時為 0。 */
export function heightAt(grid: HeightGrid, p: Pos): number {
  if (p.x < 0 || p.y < 0 || p.x >= grid.width || p.y >= grid.height) return 0;
  return grid.tiles?.[p.y * grid.width + p.x]?.height ?? 0;
}

/** 地圖上最高的高度（平地 0）。 */
export function maxHeight(grid: HeightGrid): number {
  let m = 0;
  for (const t of grid.tiles ?? []) m = Math.max(m, t.height);
  return m;
}

/** 畫布上方預留的高度（模型像素）＝ 最高格的抬高量。 */
export function topReserve(grid: HeightGrid): number {
  return tileLift(maxHeight(grid));
}

/** 畫布的模型像素大小（含上方預留）。 */
export function stagePixels(grid: HeightGrid, tile = TILE_SIZE): { width: number; height: number } {
  return { width: grid.width * tile, height: grid.height * tile + topReserve(grid) };
}

/** 抬高後格子頂面的左上角（世界座標）。 */
export function liftedOrigin(p: Pos, h: number, tile = TILE_SIZE): { x: number; y: number } {
  return { x: p.x * tile, y: p.y * tile - tileLift(h) };
}

/** 抬高後格子頂面的中心（世界座標）。 */
export function liftedCenter(p: Pos, h: number, tile = TILE_SIZE): { x: number; y: number } {
  return { x: p.x * tile + tile / 2, y: p.y * tile + tile / 2 - tileLift(h) };
}

/**
 * 世界座標的點 → 格子：由南往北、同一排由左往右檢查，點在某格「頂面＋崖面」（`[y·T − lift, y·T + T)`）
 * 的範圍內就選那格；南邊的高格蓋住北邊一排時，前排優先。範圍外回傳 `null`。
 */
export function pickTile(px: number, py: number, grid: HeightGrid, tile = TILE_SIZE): Pos | null {
  if (!(px >= 0) || px >= grid.width * tile) return null;
  const x = Math.floor(px / tile);
  for (let y = grid.height - 1; y >= 0; y -= 1) {
    const bottom = (y + 1) * tile;
    const top = y * tile - tileLift(heightAt(grid, { x, y }));
    if (py >= top && py < bottom) return { x, y };
  }
  return null;
}

/** 依繪製順序（由北到南一排一排，同排由左到右）分好的東西。 */
export interface DrawRow<T> {
  y: number;
  items: T[];
}

/** 把有座標的東西依「北 → 南、同排西 → 東」分排（每一排都有，空排的 `items` 為空）。 */
export function drawRows<T extends Pos>(items: readonly T[], rows: number): DrawRow<T>[] {
  const out: DrawRow<T>[] = Array.from({ length: Math.max(0, rows) }, (_, y) => ({ y, items: [] }));
  for (const it of items) out[it.y]?.items.push(it);
  for (const r of out) r.items.sort((a, b) => a.x - b.x);
  return out;
}

/** 單位被南鄰格擋住：南鄰 `(x, y+1)` 在地圖內且比自己高（要在最上層畫剪影）。 */
export function occluded(grid: HeightGrid, p: Pos): boolean {
  if (p.y + 1 >= grid.height) return false;
  return heightAt(grid, { x: p.x, y: p.y + 1 }) > heightAt(grid, p);
}

/** 高格四邊的描線：東、西鄰較低畫外側暗線，北鄰較低畫北緣亮邊，南鄰較低畫崖頂亮唇。地圖外不畫。 */
export interface EdgeMarks {
  east: boolean;
  west: boolean;
  north: boolean;
  south: boolean;
}

export function edgeMarks(grid: HeightGrid, p: Pos): EdgeMarks {
  const h = heightAt(grid, p);
  const lower = (dx: number, dy: number): boolean => {
    const q = { x: p.x + dx, y: p.y + dy };
    if (q.x < 0 || q.y < 0 || q.x >= grid.width || q.y >= grid.height) return false;
    return heightAt(grid, q) < h;
  };
  return { east: lower(1, 0), west: lower(-1, 0), north: lower(0, -1), south: lower(0, 1) };
}

// ---- 升降動畫 ----------------------------------------------------------------

/** ease-out（三次）：開始快、結束慢。 */
export function easeOut(t: number): number {
  const k = Math.max(0, Math.min(1, t));
  return 1 - (1 - k) ** 3;
}

/** 補間中的高度：`elapsed` 毫秒時從 `from` 往 `to` 走到哪裡；時間 ≤ 0 直接是結果。 */
export function liftHeightAt(from: number, to: number, elapsed: number, durationMs: number): number {
  if (!(durationMs > 0) || elapsed >= durationMs) return to;
  return from + (to - from) * easeOut(elapsed / durationMs);
}

/** 一格的高度變化。 */
export interface HeightShift {
  pos: Pos;
  from: number;
  to: number;
}

/**
 * 從一步的事件找出高度改變的格子（`terrain_changed` 且前後高度不同）；同一格多次改變時合併成
 * 「最早的前值 → 最後的後值」，前後相同的略過。依事件出現順序。
 */
export function heightShifts(events: readonly Record<string, unknown>[]): HeightShift[] {
  const byKey = new Map<string, HeightShift>();
  for (const e of events) {
    if (e.type !== "terrain_changed") continue;
    const pos = e.pos;
    const before = e.height_before;
    const after = e.height_after;
    if (typeof pos !== "object" || pos === null || !("x" in pos) || !("y" in pos)) continue;
    if (typeof before !== "number" || typeof after !== "number" || before === after) continue;
    const p = { x: Number(pos.x), y: Number(pos.y) };
    const key = `${p.x},${p.y}`;
    const prev = byKey.get(key);
    byKey.set(key, { pos: p, from: prev?.from ?? before, to: after });
  }
  return [...byKey.values()].filter((s) => s.from !== s.to);
}
