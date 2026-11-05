// 實地地圖上「要看得到的東西」避開 HUD（Phase RT-5b；docs/art/RT-5檢查.md 必修 1、2、5）的純函式。
// `hudInsets`（6F-3）把 HUD 簡化成四邊的寬度，夠讓主角留在安全區中央，但地圖邊上的石碑、站在主角旁邊的人仍可能被
// 右上的小地圖、金幣欄、底部的技能列或說明列蓋住。這裡用 HUD 各塊的實際矩形：
// - `nudgeCamera`：鏡頭在原本的跟隨位置附近（最多 `NUDGE_MAX` 像素、照樣夾在地圖邊界內、主角不能被蓋住）找一個
//   讓「已經露出一部分的重要東西」（開場說話的人、主線給任務的人、橋頭石碑與小牌）整個露出來的位置；
// - `placeTag`：鏡頭移不動時，石碑小牌換到石碑的左、右或下方，不壓在 HUD 上。
// 座標：HUD 矩形是舞台座標（可視區左上角為原點）；目標與小牌是畫布座標（同 camera.ts）；舞台＝畫布 − 鏡頭。
// 確定性：候選位置固定順序、同分取第一個，沒有亂數。
import { heightAt, tileLift, topReserve, type HeightGrid } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import type { Camera, ViewInsets } from "./camera";
import { headAnchor } from "./fieldPeople";
import { hudInsets, type HudLayout, type Rect } from "./hud";

/** 鏡頭最多偏離跟隨位置幾像素（約 2 格）。 */
export const NUDGE_MAX = 96;
/** 試的步距。 */
const NUDGE_STEP = 8;
/** 地圖下緣捲到說明列上面時，和說明列之間留的距離。 */
const REACH_GAP = 8;
/** 離畫面邊緣至少留幾像素才算「露出來」。 */
const EDGE = 4;

/** 說明列（「點格子走過去……」；CSS `.world-field.hud .world-field-bar`）：疊在功能列上方中央、最寬 46%。 */
export function captionRect(stage: { width: number; height: number }, scale: number): Rect {
  const width = stage.width * 0.46;
  const height = 24 * scale;
  return { left: (stage.width - width) / 2, top: stage.height - 70 * scale - height, width, height };
}

/** 鏡頭要避開的 HUD 各塊（舞台座標）：主角卡、隊友卡、影子鈕、地名、小地圖、時間天氣鈕、金幣欄、任務欄、功能列，加上說明列。通知（toasts）一下就收，不算。 */
export function hudAvoidRects(layout: HudLayout, stage: { width: number; height: number }): Rect[] {
  const b = layout.blocks;
  const ids = ["hero", "mates", "shadow", "place", "minimap", "clock", "wallet", "tracker", "bar"] as const;
  const out = ids.map((id) => b[id]).filter((r) => r.width > 0 && r.height > 0);
  if (b.bar.width > 0 && b.bar.height > 0) out.push(captionRect(stage, layout.scale));
  return out;
}

function hits(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width && b.left < a.left + a.width && a.top < b.top + b.height && b.top < a.top + a.height;
}

/**
 * 鏡頭微調時地圖邊緣最多捲到哪（同 `hudInsets`，但下方算到說明列的上緣）：地圖最下排（南邊的浮橋）可以捲到
 * 說明列上面，不會被說明列壓住（RT-5 檢查小修 8）。
 */
export function hudReach(layout: HudLayout, stage: { width: number; height: number }): ViewInsets {
  const base = hudInsets(layout, stage);
  if (!(layout.blocks.bar.width > 0 && layout.blocks.bar.height > 0)) return base;
  return { ...base, bottom: Math.max(base.bottom, stage.height - captionRect(stage, layout.scale).top + REACH_GAP * layout.scale) };
}

/** 畫布座標的矩形在鏡頭 `cam` 下整個露出來：在舞台內（留 `EDGE`）、不壓到任何 HUD。 */
export function clearOfHud(r: Rect, cam: { x: number; y: number }, view: { width: number; height: number }, avoid: readonly Rect[]): boolean {
  const s = { left: r.left - cam.x, top: r.top - cam.y, width: r.width, height: r.height };
  if (s.left < EDGE || s.top < EDGE || s.left + s.width > view.width - EDGE || s.top + s.height > view.height - EDGE) return false;
  return !avoid.some((h) => hits(s, h));
}

/** 畫布座標的矩形在舞台上露出一部分（整個在畫面外的不拉鏡頭）。 */
function onStage(r: Rect, cam: { x: number; y: number }, view: { width: number; height: number }): boolean {
  const s = { left: r.left - cam.x, top: r.top - cam.y, width: r.width, height: r.height };
  return hits(s, { left: 0, top: 0, width: view.width, height: view.height });
}

/** 一個方向鏡頭能動的範圍（同 `clampAxis`：內容比安全區小＝置中不動；否則夾在 [−lo, 內容−可視區＋hi]，含目前位置）。 */
function axisRange(cur: number, view: number, content: number, lo: number, hi: number): [number, number] {
  const safe = view - lo - hi;
  if (!(safe > 0) || content <= safe) return [cur, cur];
  return [Math.min(-lo, cur), Math.max(content - view + hi, cur)];
}

export interface NudgeInput {
  /** 跟隨主角的鏡頭（`followCamera` 的結果）。 */
  cam: Camera;
  view: { width: number; height: number };
  /** 畫布大小。 */
  content: { width: number; height: number };
  insets: ViewInsets;
  /** 微調時地圖邊緣最多捲到哪（`hudReach`；省略＝`insets`）。 */
  reach?: ViewInsets;
  /** HUD 各塊（舞台座標）。 */
  avoid: readonly Rect[];
  /** 主角（畫布座標）：鏡頭移了之後主角也不能被蓋住。 */
  hero: Rect;
  /** 要露出來的東西（畫布座標，依重要程度排）；只算目前已經露出一部分的。 */
  targets: readonly Rect[];
}

/**
 * 鏡頭在跟隨位置附近微調，讓已經露出一部分的目標整個露出來（看得到的目標越多越好，同樣多時移得越少越好，
 * 再同樣時先試的優先：水平、垂直各自由近到遠）。主角被蓋住的位置不選；沒有更好的就不動。
 */
export function nudgeCamera(input: NudgeInput): Camera {
  const { cam, view, content, insets, avoid, hero } = input;
  if (avoid.length === 0) return cam;
  const targets = input.targets.filter((t) => onStage(t, cam, view));
  if (targets.length === 0) return cam;
  const r = input.reach ?? insets;
  const [x0, x1] = axisRange(cam.x, view.width, content.width, r.left, r.right);
  const [y0, y1] = axisRange(cam.y, view.height, content.height, r.top, r.bottom);
  const shown = (c: { x: number; y: number }) => targets.filter((t) => clearOfHud(t, c, view, avoid)).length;
  const base = shown(cam);
  if (base === targets.length) return cam;
  const xs = offsets(cam.x, x0, x1);
  const ys = offsets(cam.y, y0, y1);
  let best = { x: cam.x, y: cam.y, score: base, cost: 0 };
  for (const x of xs) {
    const dx = x - cam.x;
    for (const y of ys) {
      const dy = y - cam.y;
      const cost = Math.abs(dx) + Math.abs(dy);
      if (cost === 0) continue;
      const c = { x, y };
      const score = shown(c);
      const better = score > best.score || (score === best.score && cost < best.cost);
      if (!better || !clearOfHud(hero, c, view, avoid)) continue;
      best = { x, y, score, cost };
    }
  }
  return best.cost === 0 ? cam : { ...cam, x: best.x, y: best.y };
}

/** 一個方向要試的鏡頭位置：由近到遠每 `NUDGE_STEP`（正的先），最多 `NUDGE_MAX`，夾在 [lo, hi]；兩端（地圖邊緣停住的位置）也試。 */
function offsets(cur: number, lo: number, hi: number): number[] {
  const out: number[] = [cur];
  for (let d = NUDGE_STEP; d <= NUDGE_MAX; d += NUDGE_STEP) for (const v of [cur + d, cur - d]) if (v >= lo && v <= hi) out.push(v);
  for (const v of [hi, lo]) if (Math.abs(v - cur) <= NUDGE_MAX && !out.includes(v)) out.push(v);
  return out;
}

/** 小牌放在石碑的哪一邊：`n`＝上方（預設）、`w`／`e`＝左右、`s`＝下方、`lift`＝石碑被下方的 HUD 蓋住時抬到那塊 HUD 上面、
 * `hidden`＝哪裡都放不下、預設位置又壓到 HUD（先不畫）。 */
export type TagSide = "n" | "w" | "e" | "s" | "lift" | "hidden";

/**
 * 石碑小牌的位置（左上角，畫布座標）：預設在石碑上方置中；壓到 HUD 或出了畫面時，依序試上方往內推、左邊、右邊、
 * 下方，取第一個整個露出來的；都不行就照預設（石碑本身也看不到的情況）。
 * `stele`＝石碑（畫布座標，含碑身）；`size`＝小牌大小。`cam`、`view`、`avoid` 為 `null`＝沒有 HUD，照預設。
 */
export function placeTag(
  stele: Rect,
  size: { width: number; height: number },
  cam: { x: number; y: number } | null,
  view: { width: number; height: number } | null,
  avoid: readonly Rect[],
): { left: number; top: number; side: TagSide } {
  const cx = stele.left + stele.width / 2;
  const gap = 4;
  const above = { left: cx - size.width / 2, top: stele.top - gap - size.height, side: "n" as TagSide };
  if (cam === null || view === null || avoid.length === 0) return above;
  const midY = stele.top + stele.height / 2 - size.height / 2;
  const candidates: { left: number; top: number; side: TagSide }[] = [
    above,
    { left: stele.left + stele.width - size.width, top: above.top, side: "n" },
    { left: stele.left, top: above.top, side: "n" },
    { left: stele.left - gap - size.width, top: midY, side: "w" },
    { left: stele.left + stele.width + gap, top: midY, side: "e" },
    { left: cx - size.width / 2, top: stele.top + stele.height + gap, side: "s" },
  ];
  const clear = (c: { left: number; top: number }) => clearOfHud({ left: c.left, top: c.top, width: size.width, height: size.height }, cam, view, avoid);
  for (const c of candidates) if (clear(c)) return c;
  // 石碑本身壓在下方的 HUD（功能列、說明列）底下：小牌往上抬到那塊 HUD 的上面（最多抬 `NUDGE_MAX`，再遠就不像這座石碑的了）
  let top = above.top;
  for (let i = 0; i < 4; i++) {
    const s = { left: above.left - cam.x, top: top - cam.y, width: size.width, height: size.height };
    const over = avoid.filter((r) => hits(s, r));
    if (over.length === 0) break;
    top = Math.min(...over.map((r) => r.top + cam.y)) - gap - size.height;
  }
  const lifted = { left: above.left, top, side: "lift" as TagSide };
  if (above.top - top <= NUDGE_MAX && clear(lifted)) return lifted;
  // 哪裡都放不下：預設位置只是出了畫面邊（沒壓到 HUD）就照預設，跟著鏡頭自然移出去；壓到 HUD 就先不畫（不蓋在 HUD 上）
  const shown = { left: above.left - cam.x, top: above.top - cam.y, width: size.width, height: size.height };
  return avoid.some((r) => hits(shown, r)) ? { ...above, side: "hidden" } : above;
}

/** 小牌的大小（估的；CSS `.field-stele-tag`：字 11.5px、第二行 10.5px 加鎖頭、左右各 8px）。 */
export function tagSize(name: string, sub: string): { width: number; height: number } {
  const nameW = [...name].length * 11.5;
  const subW = sub === "" ? 0 : [...sub].length * 10.5 + 12;
  return { width: Math.ceil(Math.max(nameW, subW) + 18), height: sub === "" ? 23 : 37 };
}

// ---------------- 目標的矩形（畫布座標） ----------------

/** 一格的左右、上下緣（畫布座標，含抬高）。 */
function tileBox(grid: HeightGrid, p: { x: number; y: number }, scale: number): { left: number; width: number; top: number; bottom: number } {
  const lift = tileLift(heightAt(grid, p));
  const top = (topReserve(grid) + p.y * TILE_SIZE - lift) * scale;
  return { left: p.x * TILE_SIZE * scale, width: TILE_SIZE * scale, top, bottom: top + TILE_SIZE * scale };
}

/** 頭上的「！」佔的高度（頭頂往上）。 */
export const ALERT_H = 24;

/** 站著的人（紙娃娃＋頭上的「！」）。 */
export function personRect(grid: HeightGrid, p: { x: number; y: number }, scale: number): Rect {
  const t = tileBox(grid, p, scale);
  const top = headAnchor(grid, p, scale).top - ALERT_H;
  return { left: t.left, top, width: t.width, height: t.bottom - top };
}

/** 石碑的碑身（`drawStele`：碑頂在格子上緣往上約 18 像素，左右各留約 8 像素）。 */
export function steleRect(grid: HeightGrid, p: { x: number; y: number }, scale: number): Rect {
  const t = tileBox(grid, p, scale);
  const top = t.top - 18 * scale;
  return { left: t.left + 8 * scale, top, width: t.width - 16 * scale, height: t.bottom - top };
}

/** 兩個矩形的外框。 */
export function unionRect(a: Rect, b: Rect): Rect {
  const left = Math.min(a.left, b.left);
  const top = Math.min(a.top, b.top);
  return { left, top, width: Math.max(a.left + a.width, b.left + b.width) - left, height: Math.max(a.top + a.height, b.top + b.height) - top };
}
