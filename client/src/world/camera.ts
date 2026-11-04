// 實地地圖的鏡頭（Phase 6B-6；純函式）：格子大小照戰鬥繪製器的預設縮放（`BattleRenderer` 的 scale＝1，每格
// `TILE_SIZE` 個 CSS 像素），地圖不再整張塞進畫面。地圖比可視區大時鏡頭跟著主角（主角在畫面中央），到地圖邊緣停住；
// 比可視區小時置中（兩個方向各自判斷）。`frameCamera` 給 6C-2 就地開打時框住整個戰場用。
//
// 6F-3（巡檢 bug 3）：HUD 疊在舞台上（左上主角卡、底部快捷列、右側小地圖與任務追蹤），鏡頭跟隨時以「扣掉 HUD 的
// 安全區」（`ViewInsets`）的中心為準；地圖邊緣可以捲到 HUD 外面（邊緣停在安全區的邊上），主角和出口不會躲在 HUD 底下。
//
// 座標：「畫布座標」＝縮放後畫布左上角為原點的 CSS 像素（含上方的抬高預留 `topReserve`）。
// 鏡頭 `{ x, y }`＝可視區左上角對到的畫布座標；畫布在可視區裡平移 `(-x, -y)`。地圖比可視區小時 x、y 是負的（置中）。
import type { FieldView, Pos } from "../api/types";
import { stagePixels, topReserve, type HeightGrid } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import { clientToTile, scaledSize, type ClientRect, type Size } from "../battle/stageLayout";
import type { Rect } from "./hud";

/** 實地地圖的縮放：照戰鬥繪製器的預設（`BattleRenderer` 一開始 scale＝1，每格 48 CSS 像素）。 */
export const FIELD_SCALE = 1;
/** `frameCamera` 的縮放下限（同戰鬥自動填滿的下限 `MIN_SCALE`）。 */
export const FRAME_MIN_SCALE = 0.5;

export interface Camera {
  /** 可視區左上角對到的畫布座標（CSS 像素）。 */
  x: number;
  y: number;
  scale: number;
}

/** 格子範圍（格子座標；`width`、`height` 是格數）。 */
export interface TileRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** 縮放後畫布的大小（同 `BattleCanvas` 的實際大小）。 */
export function canvasSize(grid: HeightGrid, scale: number): Size {
  return scaledSize(grid, scale);
}

/** 格子中心的畫布座標（不算格子本身的抬高；鏡頭用，不必那麼準）。 */
export function tileCenter(grid: HeightGrid, p: { x: number; y: number }, scale: number): { x: number; y: number } {
  return { x: (p.x + 0.5) * TILE_SIZE * scale, y: (topReserve(grid) + (p.y + 0.5) * TILE_SIZE) * scale };
}

/** HUD 在可視區四邊佔掉的寬度（CSS 像素）；鏡頭以扣掉這些的安全區為準（6F-3）。 */
export interface ViewInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export const NO_INSETS: ViewInsets = { top: 0, right: 0, bottom: 0, left: 0 };

/**
 * 一個方向：`lo`、`hi`＝可視區兩端被 HUD 佔掉的寬度（安全區＝`view − lo − hi`）。
 * 內容比安全區小＝在安全區裡置中；否則以 `center` 為安全區的中心，夾在 [−lo, 內容−可視區＋hi]
 *（地圖邊緣最多捲到安全區的邊上，不會躲在 HUD 底下）。`lo`＝`hi`＝0 時同 6B-6：比可視區小置中、否則夾在 [0, 內容−可視區]。
 */
export function clampAxis(view: number, content: number, center: number, lo = 0, hi = 0): number {
  if (!(view > 0)) return 0;
  const safe = view - lo - hi;
  if (!(safe > 0)) return clampAxis(view, content, center); // HUD 比畫面還大（極小視窗）：不扣
  if (content <= safe) return -(lo + (safe - content) / 2);
  // RT-3b（6F-7 檢查小修：窄視窗的室內地圖，出口「出」格子蓋在工具列上）：比安全區大、但扣掉 `hi`（下方工具列）
  // 還放得下時，整張貼齊 `hi` 那一邊（例如房間下緣貼在工具列上方，往上對齊），不再跟著主角捲到工具列底下。
  // 這時 `lo` 那一邊（左上主角卡）會蓋到地圖的一角：主角卡只在左邊，蓋到的是邊角而不是出口。
  if (hi > 0 && content <= view - hi) {
    const y = content - view + hi;
    return y === 0 ? 0 : y;
  }
  const x = Math.max(-lo, Math.min(content - view + hi, center - lo - safe / 2));
  return x === 0 ? 0 : x; // 不回 −0

}

/** 跟著 `focus`（格子，可為補間中的小數）的鏡頭；`insets`＝HUD 佔掉的四邊（主角放在安全區中央）。 */
export function followCamera(
  view: Size,
  grid: HeightGrid,
  focus: { x: number; y: number },
  scale = FIELD_SCALE,
  insets: ViewInsets = NO_INSETS,
): Camera {
  const size = canvasSize(grid, scale);
  const c = tileCenter(grid, focus, scale);
  return {
    x: clampAxis(view.width, size.width, c.x, insets.left, insets.right),
    y: clampAxis(view.height, size.height, c.y, insets.top, insets.bottom),
    scale,
  };
}

/**
 * 框住指定的格子範圍（6C-2：就地開打時框住 12×12 戰場）：縮放取「範圍＋邊距放得進可視區」，最大不超過 `maxScale`
 *（預設＝實地地圖的縮放，不放大）、最小 `FRAME_MIN_SCALE`；鏡頭以範圍中心為準，照樣夾在地圖邊界內。
 * `margin`＝範圍四周各留幾格。
 */
export function frameCamera(
  view: Size,
  grid: HeightGrid,
  rect: TileRect,
  opts: { margin?: number; maxScale?: number; minScale?: number } = {},
): Camera {
  const margin = opts.margin ?? 0.5;
  const maxScale = opts.maxScale ?? FIELD_SCALE;
  const minScale = opts.minScale ?? FRAME_MIN_SCALE;
  const w = (rect.width + margin * 2) * TILE_SIZE;
  const h = (rect.height + margin * 2) * TILE_SIZE + topReserve(grid);
  let scale = maxScale;
  if (w > 0 && h > 0 && view.width > 0 && view.height > 0) scale = Math.min(view.width / w, view.height / h);
  scale = Math.max(minScale, Math.min(maxScale, scale));
  const center = { x: rect.x + rect.width / 2 - 0.5, y: rect.y + rect.height / 2 - 0.5 };
  return followCamera(view, grid, center, scale);
}

/** 兩個鏡頭一樣（差不到 0.5 像素）。 */
export function sameCamera(a: Camera, b: Camera): boolean {
  return Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5 && a.scale === b.scale;
}

/** 畫布在可視區裡的平移（CSS `translate`）。 */
export function cameraTransform(cam: Camera): string {
  return `translate(${-cam.x}px, ${-cam.y}px)`;
}

/** 畫布在畫面上的矩形（可視區左上角在 `viewLeft`、`viewTop`）：給點擊換算用，和 `getBoundingClientRect()` 一致。 */
export function canvasRect(grid: HeightGrid, cam: Camera, viewLeft = 0, viewTop = 0): ClientRect {
  const size = canvasSize(grid, cam.scale);
  return { left: viewLeft - cam.x, top: viewTop - cam.y, width: size.width, height: size.height };
}

/** 可視區裡的點（相對可視區左上角）→ 格子；考慮鏡頭位移。在地圖外回傳 `null`。 */
export function viewToTile(px: number, py: number, grid: HeightGrid, cam: Camera): Pos | null {
  return clientToTile(px, py, canvasRect(grid, cam), grid);
}

/** 一格在可視區裡的矩形（相對可視區左上角；不算抬高）。 */
export function tileViewRect(grid: HeightGrid, p: Pos, cam: Camera): Rect {
  const cell = TILE_SIZE * cam.scale;
  return { left: p.x * cell - cam.x, top: (topReserve(grid) + p.y * TILE_SIZE) * cam.scale - cam.y, width: cell, height: cell };
}

/**
 * 出口格在可視區（舞台）裡的矩形，給 HUD 的出口半透明判斷（以畫面上的位置為準）。
 * 給了 `view` 時只留畫面上看得到的出口格（在畫面外的不必讓 HUD 變半透明）。
 */
export function exitViewRects(field: FieldView, cam: Camera, view?: Size): Rect[] {
  const rects = field.exits.flatMap((e) => e.cells.map(([x, y]) => tileViewRect(field, { x, y }, cam)));
  if (view === undefined) return rects;
  return rects.filter((r) => r.left < view.width && r.left + r.width > 0 && r.top < view.height && r.top + r.height > 0);
}

/** 鏡頭目前看得到的格子範圍（給小地圖畫框；夾在地圖內，格子座標可為小數）。 */
export function visibleTiles(view: Size, grid: HeightGrid, cam: Camera): TileRect {
  const cell = TILE_SIZE * cam.scale;
  const reserve = topReserve(grid) * cam.scale;
  const x0 = Math.max(0, cam.x / cell);
  const y0 = Math.max(0, (cam.y - reserve) / cell);
  const x1 = Math.min(grid.width, (cam.x + view.width) / cell);
  const y1 = Math.min(grid.height, (cam.y + view.height - reserve) / cell);
  return { x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0) };
}

/** 整張地圖都在畫面裡（兩個方向都不用跟）。 */
export function fitsInView(view: Size, grid: HeightGrid, scale = FIELD_SCALE): boolean {
  const px = stagePixels(grid);
  return px.width * scale <= view.width && px.height * scale <= view.height;
}
