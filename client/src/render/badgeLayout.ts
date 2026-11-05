// 炸彈、蓄力、灌注徽章的大小與位置（純函式；6F-12，美術 PM 6F-11 檢查「下一段」）。
//
// 和召喚物回合數徽章（6F-11）一樣：
// - 數字（灌注是「灌」字）在畫面上至少 `MIN_BADGE_FONT_PX`（10px），地圖縮小時反向放大；
// - 整顆（含外框線與數字的描邊）留在格子裡，離格子邊緣 `BADGE_CELL_PAD`；
// - 不蓋到臉和眼睛（`FACE`，標準人形的頭）。
//
// 炸彈、蓄力徽章是「圖示圓 ＋ 右下角數字」：圓和圖示照狀態圖示的規則（圖示畫面上至少 10px，`ki`），
// 數字另外放大到畫面上至少 10px（`kn`）。整顆一起放大的話，800 寬時圓的直徑約 22px（格子才 31px），一定會蓋到臉。
// 灌注徽章是「圓裡一個字」，和回合數徽章一樣整顆放大。
//
// 座標：世界座標、相對格子中心（往下為正）。

import { TILE_SIZE } from "../battle/geometry";
import { MIN_BADGE_FONT_PX, MIN_STATUS_GLYPH_PX, minMarkScale } from "./minMark";
import { BADGE_CELL_PAD, circleHitsBox, circleHitsCircle, type Box, type Circle } from "./rowLayout";

const T = TILE_SIZE;

/** 炸彈、蓄力徽章的圓半徑（外框線另外 1）與圖示邊長（世界座標，1600 寬的原尺寸）。 */
export const STATUS_BADGE_R = 10;
export const STATUS_BADGE_LINE = 2;
export const STATUS_BADGE_ICON = 16;
/** 炸彈、蓄力徽章的數字字級、描邊、相對圓心的位置（圖示右下）。 */
export const STATUS_BADGE_FONT = 10;
export const STATUS_BADGE_STROKE = 3;
export const STATUS_BADGE_NUM_AT = 8;
/**
 * 灌注徽章的圓半徑、外框線、字級。6F-12：圓從 9 縮到 7.5（外框 2 → 1.5），和召喚物回合數徽章（半徑 7、字 10）一樣的比例；
 * 800 寬整顆放大 1.41 倍時，畫面直徑約 15px，才放得進格子又不蓋到臉。
 */
export const INFUSED_R = 7.5;
export const INFUSED_LINE = 1.5;
export const INFUSED_FONT = 11;

/** 徽章和臉、和別的徽章之間至少留的空隙（世界座標）。 */
export const BADGE_GAP = 1;

/**
 * 標準人形的頭（世界座標）：`inkDoll` 的頭是腳底往上 42 的橢圓（半徑 9.2 × 8.6，虛擬單位），
 * 眼睛在腳底往上 41；換算 ＝ `T / 52 × DOLL_SCALE`（0.92），腳底 ＝ `T × 0.23`（`unitSprite.FEET`）。
 * 用一個圓包住整個頭（半徑取較大的 9.2 再加 0.3），不碰到這個圓就不會蓋到臉和眼睛。
 */
const DOLL_PX = (T / 52) * 0.92;
export const FACE: Circle = { x: 0, y: T * 0.23 - 42 * DOLL_PX, r: 9.5 * DOLL_PX };
/** 眼睛（測試對照用）：左右各一，`inkDoll` 的 (±3.2, −41)。 */
export const EYES: Circle[] = [-3.2, 3.2].map((x) => ({ x: x * DOLL_PX, y: T * 0.23 - 41 * DOLL_PX, r: 2.2 * DOLL_PX }));

export type BadgeKind = "bomb" | "charge" | "infused";

/** 徽章的倍率：`ki` 圓與圖示（灌注是整顆）、`kn` 數字。 */
export interface BadgeScales {
  ki: number;
  kn: number;
}

export function badgeScales(kind: BadgeKind, boardScale: number): BadgeScales {
  if (kind === "infused") {
    const k = minMarkScale(INFUSED_FONT, MIN_BADGE_FONT_PX, boardScale);
    return { ki: k, kn: k };
  }
  return { ki: minMarkScale(STATUS_BADGE_ICON, MIN_STATUS_GLYPH_PX, boardScale), kn: minMarkScale(STATUS_BADGE_FONT, MIN_BADGE_FONT_PX, boardScale) };
}

/** 數字的筆畫範圍估計（世界座標的半寬、半高，含描邊）：一個數字約字級 0.6 寬、0.72 高。 */
export function numberHalf(digits: number, kn: number): { w: number; h: number } {
  const s = STATUS_BADGE_STROKE / 2;
  return { w: kn * ((STATUS_BADGE_FONT * 0.6 * digits) / 2 + s), h: kn * ((STATUS_BADGE_FONT * 0.72) / 2 + s) };
}

/** 數字中心相對圓心的位置（世界座標）：圖示右下，跟著圓放大。 */
export function numberOffset(sc: BadgeScales): number {
  return STATUS_BADGE_NUM_AT * sc.ki;
}

/** 一顆徽章畫出來的形狀（世界座標）：外圓（含外框線）＋數字的方框（灌注沒有）。 */
export function badgeShapes(kind: BadgeKind, at: { x: number; y: number }, sc: BadgeScales, digits = 1): { circle: Circle; box: Box | null } {
  if (kind === "infused") return { circle: { ...at, r: sc.ki * (INFUSED_R + INFUSED_LINE / 2) }, box: null };
  const circle = { ...at, r: sc.ki * (STATUS_BADGE_R + STATUS_BADGE_LINE / 2) };
  const d = numberOffset(sc);
  const h = numberHalf(digits, sc.kn);
  return { circle, box: { l: at.x + d - h.w, r: at.x + d + h.w, t: at.y + d - h.h, b: at.y + d + h.h } };
}

const LIM = T / 2 - BADGE_CELL_PAD;

function insideCell(c: Circle, b: Box | null): boolean {
  if (c.x - c.r < -LIM - 1e-9 || c.x + c.r > LIM + 1e-9 || c.y - c.r < -LIM - 1e-9 || c.y + c.r > LIM + 1e-9) return false;
  return b === null || (b.l >= -LIM - 1e-9 && b.r <= LIM + 1e-9 && b.t >= -LIM - 1e-9 && b.b <= LIM + 1e-9);
}

function boxHitsBox(a: Box, b: Box, gap: number): boolean {
  return a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
}

/** 一顆徽章放在 `at` 時是否合格：整顆在格子裡、不碰臉、不碰 `avoid` 裡的形狀。 */
export function badgeFits(shape: { circle: Circle; box: Box | null }, avoid: Array<{ circle: Circle; box: Box | null }>): boolean {
  const { circle, box } = shape;
  if (!insideCell(circle, box)) return false;
  if (circleHitsCircle(circle, FACE, BADGE_GAP) || (box !== null && circleHitsBox(FACE, box, BADGE_GAP))) return false;
  for (const o of avoid) {
    if (circleHitsCircle(circle, o.circle, BADGE_GAP)) return false;
    if (o.box !== null && circleHitsBox(circle, o.box, BADGE_GAP)) return false;
    if (box !== null && circleHitsBox(o.circle, box, BADGE_GAP)) return false;
    if (box !== null && o.box !== null && boxHitsBox(box, o.box, BADGE_GAP)) return false;
  }
  return true;
}

/** 搜尋的格點間距（世界座標）。 */
const STEP = 0.5;

/**
 * 徽章的位置：原位 `pref`（相對格子中心的世界座標）合格就不動；不合格時找離原位最近的合格位置
 * （`nearest`）。`must` 是 `avoid` 裡最要避開的（召喚物回合數徽章）。
 */
export function placeBadge(
  kind: BadgeKind,
  pref: { x: number; y: number },
  sc: BadgeScales,
  avoid: Array<{ circle: Circle; box: Box | null }> = [],
  digits = 1,
  must: Array<{ circle: Circle; box: Box | null }> = [],
): { x: number; y: number } {
  const fits = (others: typeof avoid) => (p: { x: number; y: number }) => badgeFits(badgeShapes(kind, p, sc, digits), others);
  // 先避開所有別的徽章；放不下（800 寬一格裡有兩、三顆）時只避開 `must`、允許和前面的徽章重疊；
  // 再放不下只顧臉和格子；都不行（手動縮到很小）才只夾在格子裡。臉一律優先。
  const best = nearest(pref, fits(avoid)) ?? (must.length > 0 ? nearest(pref, fits(must)) : null) ?? nearest(pref, fits([]));
  if (best !== null) return best;
  const c = badgeShapes(kind, pref, sc, digits).circle;
  const clamp = (v: number) => Math.min(Math.max(v, -LIM + c.r), LIM - c.r);
  return { x: clamp(pref.x), y: clamp(pref.y) };
}

/** 離 `pref` 最近的合格位置（原位合格就是原位；格點 `STEP`，一樣近時先上後下、先左後右）；沒有就 `null`。 */
function nearest(pref: { x: number; y: number }, ok: (p: { x: number; y: number }) => boolean): { x: number; y: number } | null {
  if (ok(pref)) return { ...pref };
  let best: { x: number; y: number } | null = null;
  let bestD = Infinity;
  const n = Math.round(LIM / STEP);
  for (let iy = -n; iy <= n; iy++)
    for (let ix = -n; ix <= n; ix++) {
      const p = { x: ix * STEP, y: iy * STEP };
      const d = (p.x - pref.x) ** 2 + (p.y - pref.y) ** 2;
      if (d < bestD - 1e-9 && ok(p)) {
        best = p;
        bestD = d;
      }
    }
  return best;
}

/** 一個單位身上的徽章（照畫的順序，前面的先放、後面的避開前面的）。 */
export interface BadgeReq {
  kind: BadgeKind;
  /** 原位（相對格子中心的比例，乘上格子大小）。 */
  at: { x: number; y: number };
  /** 數字的位數（灌注不用）。 */
  digits: number;
}

/**
 * 一個單位所有徽章的位置（縮放 `boardScale`）：照順序放，後面的避開前面的和 `extra`（召喚物回合數徽章）。
 * 回傳和 `reqs` 同順序的圓心與倍率。
 */
export function layoutBadges(reqs: BadgeReq[], boardScale: number, extra: Circle[] = []): Array<{ at: { x: number; y: number }; sc: BadgeScales }> {
  const must: Array<{ circle: Circle; box: Box | null }> = extra.map((c) => ({ circle: c, box: null }));
  const placed = [...must];
  return reqs.map((r) => {
    const sc = badgeScales(r.kind, boardScale);
    const at = placeBadge(r.kind, { x: r.at.x * T, y: r.at.y * T }, sc, placed, r.digits, must);
    placed.push(badgeShapes(r.kind, at, sc, r.digits));
    return { at, sc };
  });
}
