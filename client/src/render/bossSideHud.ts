// BM-1（美術 PM PB-1e 驗收裁定待決 3「800 頭目狀態列移到 HP 條旁」；併 PB-1f 待決 3）：
// 800 寬（地圖縮放 ≤ `COMPACT_ROW_MAX_SCALE`）時，有部位的頭目（1 格的霧鎖真人、3×3 的灰燼之心）的腳邊狀態列
// 不再疊在 HP 條正上方（反向放大後蓋住下腹，滑過三個部位時亮起看不出差別），改放 HP 條（含部位小格）的右邊；
// 炸彈、蓄力、灌注徽章放左邊。站在地圖最右欄時左右對調。1600 寬（縮放 > 0.85）照原本的排法。
//
// 純函式（座標都是未加 `bossHudDy` 的單位本地座標，和 `rowShapes`、`hpBoxOf` 同一套）；`unitSprite.statusRow`／`registerBadges` 呼叫。

import type { UnitDraw } from "../battle/drawModel";
import { HP_H, HP_W, HP_Y, stripLayout } from "../battle/partStrip";
import { badgeScales, badgeShapes, type BadgeLayout, type BadgeReq } from "./badgeLayout";
import { isCompactRow, shapesHitArrow, type Box, type Circle, type MapEdge } from "./rowLayout";

/** HP 條與兩側的狀態列、徽章之間的空隙（畫面 px；換算成世界座標 ÷ 地圖縮放）。 */
export const BOSS_SIDE_GAP_PX = 2;
/** 狀態列碰到朝向三角形（朝東、朝西時在底圈外緣）時，往外讓的步長（世界座標）。 */
const ARROW_STEP = 0.5;
/** 往外讓的上限（世界座標）。 */
const ARROW_MAX = 24;

/** HP 條（含護盾條與部位小格）在這個縮放下的方框；兩側的東西以它的垂直中心對齊。 */
export interface SideBlock {
  l: number;
  r: number;
  t: number;
  b: number;
  /** 狀態列放左邊（站在地圖最右欄）。 */
  rowLeft: boolean;
}

/** 這個單位在這個縮放下要不要用兩側排法：有部位、站著、有 HP 條，而且是 800 寬的精簡縮放。 */
export function bossSideHudOn(u: Pick<UnitDraw, "downed"> & Partial<Pick<UnitDraw, "parts" | "noBar">>, boardScale: number): boolean {
  return u.parts !== undefined && u.parts.length > 0 && !u.downed && u.noBar !== true && isCompactRow(boardScale);
}

/** HP 條＋部位小格在縮放 `boardScale` 下的方框（`SHIELD_OUTLINE` 由呼叫端給：有護盾條時往外 1、往上 3＋1）。 */
export function sideBlock(u: Pick<UnitDraw, "shieldRatio"> & Partial<Pick<UnitDraw, "parts">>, boardScale: number, shieldOutline: number, edge: MapEdge): SideBlock {
  const o = u.shieldRatio > 0 ? shieldOutline : 0;
  const n = u.parts?.length ?? 0;
  const b = n > 0 ? stripLayout(n, boardScale).bottom : HP_Y + HP_H;
  return { l: -HP_W / 2 - o, r: HP_W / 2 + o, t: HP_Y - (u.shieldRatio > 0 ? 3 + o : 0), b, rowLeft: edge.right };
}

function mid(block: SideBlock): number {
  return (block.t + block.b) / 2;
}

function gapOf(boardScale: number): number {
  return boardScale > 0 ? BOSS_SIDE_GAP_PX / boardScale : BOSS_SIDE_GAP_PX;
}

/** 形狀整組平移。 */
export function shiftShapes<T extends { boxes: Box[]; circles: Circle[]; cap: Box | null }>(sh: T, dx: number, dy: number): T {
  const mv = (b: Box): Box => ({ l: b.l + dx, r: b.r + dx, t: b.t + dy, b: b.b + dy });
  const boxes = sh.boxes.map(mv);
  // `cap` 是 `boxes` 裡的同一個物件（`badgeLayout` 用 `Set` 認），平移後也要指向新陣列裡的那一個
  const capIdx = sh.cap === null ? -1 : sh.boxes.indexOf(sh.cap);
  const cap = sh.cap === null ? null : capIdx >= 0 ? boxes[capIdx]! : mv(sh.cap);
  return { ...sh, boxes, circles: sh.circles.map((c) => ({ ...c, x: c.x + dx, y: c.y + dy })), cap };
}

/**
 * 狀態列（照原本排法算好的形狀 `sh`）搬到 HP 條旁邊的位移：垂直置中對齊 HP 條＋部位小格，
 * 水平貼著 HP 條外側（空隙畫面 `BOSS_SIDE_GAP_PX`）；碰到朝向三角形再往外讓。
 */
export function sideRowShift(sh: { boxes: readonly Box[] }, block: SideBlock, boardScale: number, arrow: Box | null): { dx: number; dy: number } {
  if (sh.boxes.length === 0) return { dx: 0, dy: 0 };
  const l = Math.min(...sh.boxes.map((b) => b.l));
  const r = Math.max(...sh.boxes.map((b) => b.r));
  const t = Math.min(...sh.boxes.map((b) => b.t));
  const b = Math.max(...sh.boxes.map((x) => x.b));
  const gap = gapOf(boardScale);
  const dy = mid(block) - (t + b) / 2;
  const at = (extra: number) => (block.rowLeft ? block.l - gap - extra - r : block.r + gap + extra - l);
  let extra = 0;
  const moved = (d: number) => ({ boxes: sh.boxes.map((x) => ({ l: x.l + d, r: x.r + d, t: x.t + dy, b: x.b + dy })), circles: [] });
  while (extra < ARROW_MAX && shapesHitArrow(moved(at(extra)), arrow)) extra += ARROW_STEP;
  return { dx: at(extra), dy };
}

/**
 * 炸彈、蓄力、灌注徽章在 HP 條另一側（預設左邊）的位置：照順序由內往外排，圓心垂直對齊 HP 條＋部位小格的中心，
 * 數字放外側下角（左邊用「左下」、右邊用「右下」），不壓到 HP 條。
 */
export function sideBadgeLayouts(reqs: readonly BadgeReq[], boardScale: number, block: SideBlock): BadgeLayout[] {
  const gap = gapOf(boardScale);
  const left = !block.rowLeft;
  const corner = left ? "bl" : "br";
  const y = mid(block);
  let edge = left ? block.l - gap : block.r + gap;
  return reqs.map((req) => {
    const sc = badgeScales(req.kind, boardScale);
    const sh = badgeShapes(req.kind, { x: 0, y: 0 }, sc, req.digits, corner);
    const ls = [sh.circle.x - sh.circle.r, ...(sh.box === null ? [] : [sh.box.l])];
    const rs = [sh.circle.x + sh.circle.r, ...(sh.box === null ? [] : [sh.box.r])];
    const lo = Math.min(...ls);
    const hi = Math.max(...rs);
    const x = left ? edge - hi : edge - lo;
    edge = left ? x + lo - gap : x + hi + gap;
    return { at: { x, y }, sc, tier: 0, faceOk: true, corner, firm: 0 };
  });
}
