// 腳邊狀態列與召喚物回合數徽章的排法（純函式；6F-11 從 `unitSprite.ts` 抽出）。
//
// 座標：世界座標、相對格子中心（往下為正）。狀態列節點的原點是第一排圖示的中心線、下緣在 `bottom`，
// 整排放大 `k` 倍（`minMark.ts`，地圖縮小時反向放大）；排內的「本地座標」是放大前的大小。
//
// 6F-11（美術 PM 6F-10b 檢查「下一段要修」）：
// - 地圖縮放 ≤ 70%（800 寬）時狀態列只顯示 1 個圖示，後面接一般大小的「+N」字（不縮成角標、不蓋圖示）。
// - 一般單位在 1600、1040 寬時「+N」改成角標（和召喚物同一個角標，6F-10b）。
// - 召喚物回合數徽章的數字在畫面上至少 10px（`summonBadgeScale`），畫面上的半徑因此至少 7px；
//   放不下原位時放在格子右上角、整顆留在格子裡（`summonBadgeCorner`）。

import { TILE_SIZE } from "../battle/geometry";
import { MIN_BADGE_FONT_PX, minMarkScale } from "./minMark";
import { SUMMON_BADGE_FONT, SUMMON_BADGE_RADIUS } from "./unitLook";

const T = TILE_SIZE;

/** 腳邊狀態列的圖示邊長（3U-2b；舊 14，約 60～80%：48px 格 11、88px 格約 20px）。 */
export const ROW_ICON_FEET = 11;
/** 字母標記圓（左下）的右緣 x；狀態列左緣至少離它 1px。 */
export const MARKER_RIGHT = -T * 0.37 + 8;
/** 圖示最小間距（px）：召喚物回合數徽章擠壓時才會小於 `ROW_ICON_FEET + 1`。 */
export const ROW_MIN_PITCH = 6;
/** 狀態列左右不超出格子：格子左右緣（相對格子中心）往內 1px。 */
export const ROW_EDGE = T / 2 - 1;
/** 「+N」小圓（含白邊）比第 2 個圖示右緣多出去的寬度、比圖示上緣多出去的高度。 */
export const ROW_MORE_OUT = 3;
/** 狀態列和回合數徽章之間至少留的空隙（含徽章的外框線）。 */
export const ROW_BADGE_GAP = 2;

// ---- 6F-10b：「+N」角標（6F-11 起一般單位在 1600、1040 寬也用） ----

/** 「+N」角標的半徑（白邊另外 0.5）。 */
export const SUMMON_MORE_R = 4;
/**
 * 「+N」角標的圓心：第 2 個圖示右上角往右 `dx`、往下 `dy`。`dx` 照空間決定（`fitRow`）：
 * 放得下時往右到完全不蓋到圖示（`SUMMON_MORE_DX_MAX`），擠的時候至少 `dx`（只蓋到圖示的一個小角，不蓋到圖案中間）。
 */
export const SUMMON_MORE_AT = { dx: 1, dy: 1.5 };
/** 角標圓（含白邊）的左緣剛好貼著第 2 個圖示的右緣：完全不重疊。 */
export const SUMMON_MORE_DX_MAX = SUMMON_MORE_R + 0.5;
/** 手動把地圖縮到很小、角標放不下時，角標圓心最多往左到圖示右上角往左 2px（舊的一般單位「+N」的位置）。 */
export const SUMMON_MORE_SQUEEZE_DX = -2;
/** 「+N」角標（含白邊）比圖示上緣多出去的高度。 */
export const SUMMON_MORE_OUT_Y = SUMMON_MORE_R + 0.5 - SUMMON_MORE_AT.dy;
/** 6F-10b 的徽章靠右緣位置（壓出格子 3px）；6F-11 起不再使用，留著給舊測試對照。 */
export const SUMMON_BADGE_EDGE_X = T / 2 + 3 - SUMMON_BADGE_RADIUS;
/** 人形（含召喚物的骷髏、石像）往右伸的手臂、武器最遠到格子中心右邊幾 px（世界座標；量 6F-10 的骷髏戰士）。 */
export const HUMANOID_ARM_REACH = 12;

/** 「+N」角標的圓心（`lastX` ＝ 第 2 個圖示的中心 x，本地座標）。 */
export function summonMoreAt(lastX: number, dx: number = SUMMON_MORE_AT.dx): { x: number; y: number } {
  return { x: lastX + ROW_ICON_FEET / 2 + dx, y: -ROW_ICON_FEET / 2 + SUMMON_MORE_AT.dy };
}

// ---- 6F-11：精簡狀態列（地圖縮放 ≤ 70%） ----

/** 地圖縮放 ≤ 這個值（800 寬約 65%）時狀態列只顯示 1 個圖示＋「+N」字。 */
export const COMPACT_ROW_MAX_SCALE = 0.7;
/** 精簡狀態列的「+N」字級（本地座標；整排放大後畫面上 ＝ 9 × k × 縮放 ≥ 10px，和圖示的圖案一樣大）。 */
export const ROW_PLUS_FONT = 9;
/** 精簡狀態列：圖示右緣和「+N」字左緣的空隙（本地座標）。 */
export const ROW_PLUS_GAP = 1.5;
/** 「+N」字的筆畫高度（數字與「+」約字級的 0.72）。 */
export const ROW_PLUS_INK_H = ROW_PLUS_FONT * 0.72;
/** 「+N」字的深色描邊寬度（本地座標；一半在筆畫外）。 */
export const ROW_PLUS_STROKE = 2;
/**
 * 「+N」字的筆畫下緣比圖示下緣低多少（本地座標）：讓出上方給右上角的回合數徽章（召喚物）；
 * 含描邊的下緣仍在 HP 條上緣之上（`ROW_GAP_HP` 4px 內）。
 */
export const ROW_PLUS_DROP = 0.9;

export function isCompactRow(boardScale: number): boolean {
  return boardScale > 0 && boardScale <= COMPACT_ROW_MAX_SCALE + 1e-9;
}

/** 精簡狀態列「+N」的 N：總共的狀態數 − 1（只顯示 1 個圖示）；只有 1 個狀態時 0（不顯示）。 */
export function compactPlusCount(total: number): number {
  return Math.max(0, total - 1);
}

/** 「+N」字的寬度估計（本地座標；實際畫的時候用 Text 量到的寬度）。 */
export function plusTextWidth(count: number): number {
  return ROW_PLUS_FONT * 0.62 * (1 + String(count).length);
}

// ---- 6F-11：召喚物回合數徽章 ----

/** 徽章整顆（含外框線）離格子邊緣至少幾 px（世界座標）：不壓格線、不跨進隔壁格。 */
export const BADGE_CELL_PAD = 1.5;

/** 徽章的反向放大倍率：數字在畫面上至少 `MIN_BADGE_FONT_PX`（徽章半徑跟著放大，畫面上至少 7px）。 */
export function summonBadgeScale(boardScale: number): number {
  return minMarkScale(SUMMON_BADGE_FONT, MIN_BADGE_FONT_PX, boardScale);
}

/** 徽章放大 `kb` 倍後的外緣半徑（含外框線 0.5）。 */
export function badgeOuterR(kb: number): number {
  return kb * (SUMMON_BADGE_RADIUS + 0.5);
}

/** 放不下原位時徽章的圓心：格子右上角，整顆留在格子裡（離格子邊緣 `BADGE_CELL_PAD`）。 */
export function summonBadgeCorner(kb: number): { x: number; y: number } {
  const r = badgeOuterR(kb);
  return { x: T / 2 - BADGE_CELL_PAD - r, y: -T / 2 + BADGE_CELL_PAD + r };
}

/** 沒有狀態列時徽章的圓心：沒放大（1600 寬）照原位，放大了就放到右上角（原位會超出格子）。 */
export function summonBadgeAlone(at: { x: number; y: number }, kb: number, compact: boolean): { x: number; y: number } {
  return compact || kb > 1 + 1e-9 ? summonBadgeCorner(kb) : { ...at };
}

// ---- 幾何 ----

export interface Box {
  l: number;
  r: number;
  t: number;
  b: number;
}
export interface Circle {
  x: number;
  y: number;
  r: number;
}

export function circleHitsBox(c: Circle, b: Box, gap = 0): boolean {
  const dx = Math.max(b.l - c.x, 0, c.x - b.r);
  const dy = Math.max(b.t - c.y, 0, c.y - b.b);
  return dx * dx + dy * dy < (c.r + gap) ** 2 - 1e-9;
}

export function circleHitsCircle(a: Circle, b: Circle, gap = 0): boolean {
  return Math.hypot(a.x - b.x, a.y - b.y) < a.r + b.r + gap - 1e-9;
}

/** 狀態列的排法：`shift` 整排的 x、`pitch` 圖示間距、`moreDx` 角標位置、`compact` 是否只顯示 1 個圖示＋「+N」字。 */
export interface RowPlan {
  shift: number;
  pitch: number;
  moreDx: number;
  compact: boolean;
}

/** 召喚物的狀態列與回合數徽章的排法：`badge` 徽章圓心。 */
export interface SummonRowLayout extends RowPlan {
  badge: { x: number; y: number };
}

/**
 * 一排畫出來的形狀（世界座標）：圖示是方框，角標是圓，精簡列的「+N」字是筆畫範圍的方框。
 * `n` 個圖示（精簡列只畫第 1 個）、`extra` 有沒有角標、`plusW` 精簡列「+N」字的寬度（本地座標，0 ＝ 沒有字）。
 */
export function rowShapes(plan: RowPlan, n: number, k: number, bottom: number, extra: boolean, plusW = 0): { boxes: Box[]; circles: Circle[] } {
  const half = ROW_ICON_FEET / 2;
  const X = (lx: number) => plan.shift + k * lx;
  const Y = (ly: number) => bottom + k * (ly - half);
  const boxes: Box[] = [];
  const circles: Circle[] = [];
  if (plan.compact) {
    boxes.push({ l: X(-half), r: X(half), t: Y(-half), b: Y(half) });
    // 「+N」字：筆畫範圍加上描邊（左右的描邊已含在 Text 量到的寬度裡）
    const s = ROW_PLUS_STROKE / 2;
    if (plusW > 0) boxes.push({ l: X(half + ROW_PLUS_GAP), r: X(half + ROW_PLUS_GAP + plusW), t: Y(half + ROW_PLUS_DROP - ROW_PLUS_INK_H - s), b: Y(half + ROW_PLUS_DROP + s) });
    return { boxes, circles };
  }
  const x0 = -((n - 1) * plan.pitch) / 2;
  for (let i = 0; i < n; i++) boxes.push({ l: X(x0 + i * plan.pitch - half), r: X(x0 + i * plan.pitch + half), t: Y(-half), b: Y(half) });
  if (extra) {
    const m = summonMoreAt(x0 + (n - 1) * plan.pitch, plan.moreDx);
    circles.push({ x: X(m.x), y: Y(m.y), r: k * (SUMMON_MORE_R + 0.5) });
  }
  return { boxes, circles };
}

/** 一排的左右範圍（世界座標）。 */
export function rowSpan(plan: RowPlan, n: number, k: number, extra: boolean, plusW = 0): { l: number; r: number } {
  const half = ROW_ICON_FEET / 2;
  if (plan.compact) return { l: plan.shift - k * half, r: plan.shift + k * (half + (plusW > 0 ? ROW_PLUS_GAP + plusW : 0)) };
  const w = ((n - 1) * plan.pitch) / 2 + half;
  return { l: plan.shift - k * w, r: plan.shift + k * (w + (extra ? plan.moreDx + SUMMON_MORE_R + 0.5 : 0)) };
}

/**
 * 狀態列（`n` 個圖示、`extra` 是否有角標、放大 `k` 倍）夾在 `left`～`right` 之間的排法（6F-10b 的讓步順序）；放不下 `null`。
 * 照順序讓步，放得下就停（`avail` ＝ 可用寬度 ÷ 倍率）：
 * ① 原間距，角標盡量往右（最多完全不蓋到圖示 `SUMMON_MORE_DX_MAX`，至少 `SUMMON_MORE_AT.dx`）；
 * ② 角標停在 `SUMMON_MORE_AT.dx`，縮間距到圖示剛好相貼；③ 圖示相貼，角標往左縮（最多到 `SUMMON_MORE_SQUEEZE_DX`）；
 * ④ 角標停在最左，再縮間距（最小 `ROW_MIN_PITCH`，圖示輕微重疊）。整排盡量置中（原點 0），超出才往內推。
 */
export function fitRow(n: number, k: number, left: number, right: number, extra: boolean): RowPlan | null {
  const half = ROW_ICON_FEET / 2;
  const outOf = (dx: number) => (extra ? dx + SUMMON_MORE_R + 0.5 : 0);
  const place = (pitch: number, dx: number): RowPlan => {
    const l = k * (((n - 1) * pitch) / 2 + half);
    const r = k * (((n - 1) * pitch) / 2 + half + outOf(dx));
    return { shift: Math.min(Math.max(0, left + l), right - r), pitch, moreDx: dx, compact: false };
  };
  const avail = (right - left) / k;
  const EPS = 1e-9;
  const gaps = n - 1;
  const tag = (pitch: number) => avail - gaps * pitch - ROW_ICON_FEET - (extra ? SUMMON_MORE_R + 0.5 : 0); // 角標可用的 dx
  const loose = ROW_ICON_FEET + 1;
  if (!extra) {
    const pitch = gaps === 0 ? loose : Math.min(loose, (avail - ROW_ICON_FEET) / gaps);
    return pitch >= ROW_MIN_PITCH - EPS && avail >= ROW_ICON_FEET - EPS ? place(Math.max(ROW_MIN_PITCH, pitch), 0) : null;
  }
  if (tag(loose) >= SUMMON_MORE_AT.dx - EPS) return place(loose, Math.min(SUMMON_MORE_DX_MAX, tag(loose)));
  if (gaps > 0 && tag(ROW_ICON_FEET) >= SUMMON_MORE_AT.dx - EPS) return place((avail - ROW_ICON_FEET - outOf(SUMMON_MORE_AT.dx)) / gaps, SUMMON_MORE_AT.dx);
  const touch = gaps > 0 ? ROW_ICON_FEET : loose;
  if (tag(touch) >= SUMMON_MORE_SQUEEZE_DX - EPS) return place(touch, Math.min(SUMMON_MORE_AT.dx, tag(touch)));
  if (gaps > 0 && tag(ROW_MIN_PITCH) >= SUMMON_MORE_SQUEEZE_DX - EPS) return place((avail - ROW_ICON_FEET - outOf(SUMMON_MORE_SQUEEZE_DX)) / gaps, SUMMON_MORE_SQUEEZE_DX);
  return null;
}

/** 精簡狀態列（1 個圖示＋「+N」字）：`flushLeft` 靠左（召喚物，讓出右上角給徽章），否則置中；超出 `left`～`right` 往內推。 */
export function compactRow(k: number, left: number, right: number, plusW: number, flushLeft: boolean): RowPlan {
  const half = ROW_ICON_FEET / 2;
  const w = plusW > 0 ? ROW_PLUS_GAP + plusW : 0;
  const lo = left + k * half;
  const hi = right - k * (half + w);
  const want = flushLeft ? lo : (-k * w) / 2;
  return { shift: Math.min(Math.max(want, lo), hi), pitch: ROW_ICON_FEET + 1, moreDx: 0, compact: true };
}

function leftLimit(hasMarker: boolean): number {
  return hasMarker ? MARKER_RIGHT + 1 : -ROW_EDGE;
}

/**
 * 一般單位（沒有回合數徽章）的狀態列排法（6F-11）：
 * - 縮放 ≤ 70%：只顯示 1 個圖示，後面接「+N」字（`plusW` 是它的寬度），整組置中；
 * - 其他：最多 2 個圖示＋「+N」角標（6F-10b 召喚物的角標），夾在格子裡（`fitRow`）。
 */
export function unitRowLayout(n: number, k: number, extra: boolean, hasMarker: boolean, boardScale: number, plusW: number): RowPlan {
  const left = leftLimit(hasMarker);
  if (isCompactRow(boardScale)) return compactRow(k, left, ROW_EDGE, plusW, false);
  return fitRow(n, k, left, ROW_EDGE, extra) ?? { shift: 0, pitch: ROW_MIN_PITCH, moreDx: SUMMON_MORE_SQUEEZE_DX, compact: false };
}

function clearOf(badge: Circle, shapes: { boxes: Box[]; circles: Circle[] }, gap: number): boolean {
  return shapes.boxes.every((b) => !circleHitsBox(badge, b, gap)) && shapes.circles.every((c) => !circleHitsCircle(badge, c, gap));
}

/** 狀態列和右上角徽章至少留的空隙（世界座標）。 */
export const ROW_CORNER_GAP = 1;

/**
 * 召喚物的狀態列與回合數徽章（預設圓心 `at`、放大 `kb` 倍）的排法（6F-10 → 6F-10b → 6F-11）：
 * 1. 不是精簡列、徽章沒放大（1600 寬）時，徽章不動、狀態列夾在左限和徽章左緣 −`ROW_BADGE_GAP` 之間（`fitRow`，和 6F-10b 一樣）；
 * 2. 放不下時徽章放到格子右上角（`summonBadgeCorner`，整顆在格子裡），狀態列靠左排在徽章下面：
 *    先試 2 個圖示（圖示不重疊、角標最多蓋到一小角），和徽章至少留 `ROW_CORNER_GAP`；
 * 3. 還是放不下、或縮放 ≤ 70%（`compact`）時，只顯示 1 個圖示＋「+N」字（`plusW` 是字寬，本地座標）。
 * 「+N」字的 N 由呼叫端算（`compactPlusCount`）；`plusW` 為 0 表示只有 1 個狀態。
 */
export function summonRowLayout(
  n: number,
  k: number,
  at: { x: number; y: number },
  bottom: number,
  extra: boolean,
  hasMarker: boolean,
  kb = 1,
  compact = false,
  plusW = n > 1 || extra ? plusTextWidth(n - 1 + (extra ? 1 : 0)) : 0,
): SummonRowLayout {
  const left = leftLimit(hasMarker);
  // 徽章放大了（1040、800 寬）原位會超出格子，一律放右上角
  if (!compact && kb <= 1 + 1e-9) {
    const beside = fitRow(n, k, left, at.x - SUMMON_BADGE_RADIUS - ROW_BADGE_GAP, extra);
    if (beside !== null) return { ...beside, badge: { ...at } };
  }
  const badge = summonBadgeCorner(kb);
  const bc: Circle = { ...badge, r: badgeOuterR(kb) };
  if (!compact) {
    const half = ROW_ICON_FEET / 2;
    const pitches = n > 1 ? [ROW_ICON_FEET + 1, ROW_ICON_FEET] : [ROW_ICON_FEET + 1];
    const dxs = extra ? [SUMMON_MORE_DX_MAX, (SUMMON_MORE_DX_MAX + SUMMON_MORE_AT.dx) / 2, SUMMON_MORE_AT.dx] : [0];
    for (const pitch of pitches)
      for (const dx of dxs) {
        const out = extra ? dx + SUMMON_MORE_R + 0.5 : 0;
        const w = ((n - 1) * pitch) / 2 + half;
        const lo = left + k * w;
        const hi = ROW_EDGE - k * (w + out);
        if (hi < lo - 1e-9) continue;
        for (const shift of [Math.min(Math.max(0, lo), hi), lo]) {
          const plan: RowPlan = { shift, pitch, moreDx: dx, compact: false };
          if (clearOf(bc, rowShapes(plan, n, k, bottom, extra), ROW_CORNER_GAP)) return { ...plan, badge };
        }
      }
  }
  return { ...compactRow(k, left, ROW_EDGE, plusW, true), badge };
}
