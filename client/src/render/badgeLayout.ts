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

import { tileLift } from "../battle/elevation";
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
 * 灌注徽章（6F-13，美術 PM 6F-12 檢查第 2 節第 1 點）：「灌」字提到 12px，1040、800 寬還是糊成一塊
 * （`docs/art/6f13_1_glyph12_*`），而且 800 寬時圓的畫面直徑約 18px，和召喚物回合數徽章（約 15px）放不進同一格的上緣。
 * 改成程式繪製的小水滴（沒有黑底圓，深色描邊）：`INFUSED_DROP_H` 高（含尖端）、`INFUSED_DROP_W` 寬（世界座標），
 * `INFUSED_DROP_LINE` 深色描邊（一半在外）。地圖縮小時整顆反向放大，水滴在畫面上至少高 `MIN_INFUSED_ICON_PX`（和狀態圖示一樣 10px）。
 */
export const INFUSED_DROP_H = 12;
export const INFUSED_DROP_W = 8.5;
export const INFUSED_DROP_LINE = 1.5;
export const MIN_INFUSED_ICON_PX = 10;

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
    const k = minMarkScale(INFUSED_DROP_H, MIN_INFUSED_ICON_PX, boardScale);
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

/**
 * 數字放在圓的哪裡（6F-13）：`br` 右下（原位）、`b` 正下方、`bl` 左下。
 * 800 寬一格裡太擠時（蓄力在左、狀態列在中間），右下的數字一定會蓋到狀態列；改放正下方或左下就讓得開
 * （美術 PM 6F-12 檢查：蓄力的「1」蓋住防禦圖示約一半）。照這個順序試，右下放得下就不換。
 */
export type NumCorner = "br" | "b" | "bl";
/** 6F-14（美術 PM 6F-13 檢查：800 寬蓄力的「1」壓到朝向三角形）：右下、左下優先，正下方最後。 */
export const NUM_CORNERS: readonly NumCorner[] = ["br", "bl", "b"];

/** 數字中心相對圓心的位置（徽章節點的本地座標，放大前）。 */
export function numberAt(corner: NumCorner): { x: number; y: number } {
  if (corner === "b") return { x: 0, y: STATUS_BADGE_NUM_AT + 1.5 };
  return { x: corner === "bl" ? -STATUS_BADGE_NUM_AT : STATUS_BADGE_NUM_AT, y: STATUS_BADGE_NUM_AT };
}

/** 一顆徽章畫出來的形狀（世界座標）：外圓（含外框線）＋數字的方框（灌注是水滴的外框）。 */
export function badgeShapes(kind: BadgeKind, at: { x: number; y: number }, sc: BadgeScales, digits = 1, corner: NumCorner = "br"): { circle: Circle; box: Box | null } {
  if (kind === "infused") {
    // 水滴：下半的圓（圓心在中心往下 H/2 − W/2）＋整顆的外框方框（含描邊；尖端的描邊多留一倍）
    const k = sc.ki;
    const e = INFUSED_DROP_LINE / 2;
    const round = INFUSED_DROP_W / 2;
    const circle = { x: at.x, y: at.y + k * (INFUSED_DROP_H / 2 - round), r: k * (round + e) };
    return { circle, box: { l: at.x - k * (round + e), r: at.x + k * (round + e), t: at.y - k * (INFUSED_DROP_H / 2 + 2 * e), b: at.y + k * (INFUSED_DROP_H / 2 + e) } };
  }
  const circle = { ...at, r: sc.ki * (STATUS_BADGE_R + STATUS_BADGE_LINE / 2) };
  const o = numberAt(corner);
  const dx = o.x * sc.ki;
  const dy = o.y * sc.ki;
  const h = numberHalf(digits, sc.kn);
  return { circle, box: { l: at.x + dx - h.w, r: at.x + dx + h.w, t: at.y + dy - h.h, b: at.y + dy + h.h } };
}

const LIM = T / 2 - BADGE_CELL_PAD;

function insideCell(c: Circle, b: Box | null): boolean {
  if (c.x - c.r < -LIM - 1e-9 || c.x + c.r > LIM + 1e-9 || c.y - c.r < -LIM - 1e-9 || c.y + c.r > LIM + 1e-9) return false;
  return b === null || (b.l >= -LIM - 1e-9 && b.r <= LIM + 1e-9 && b.t >= -LIM - 1e-9 && b.b <= LIM + 1e-9);
}

function boxHitsBox(a: Box, b: Box, gap: number): boolean {
  return a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
}

/** 要避開的形狀：一個圓（別的徽章）或一個方框（狀態列的圖示、「+N」字），或兩者（炸彈、蓄力徽章）。 */
export interface Obstacle {
  circle: Circle | null;
  box: Box | null;
  /** 6F-14：只有數字（`badgeShapes` 的方框）要避開，圓可以蓋到（朝向三角形在格子正中間、怎麼放都碰得到時）。 */
  numOnly?: boolean;
  /** 6F-14：「▲N」的數字：圓和數字都一律避開，只有最後一層才放寬（`firm` 放寬成只讓數字避開時也不放寬）。 */
  keep?: boolean;
}

/**
 * 數字的方框和狀態列圖示、「+N」字等方框之間至少留的空隙（6F-14）：數字的方框已經含描邊、字寬也估得寬，
 * 0.5 就不會碰到；用 `BADGE_GAP`（1）的話，800 寬蓄力的數字放在右下時和讓到右邊的防禦圖示差 0.6 放不下。
 */
export const BADGE_NUM_GAP = 0.5;

/** 一顆徽章放在 `at` 時是否合格：整顆在格子裡、不碰臉、不碰 `avoid` 裡的形狀。 */
export function badgeFits(shape: { circle: Circle; box: Box | null }, avoid: readonly Obstacle[]): boolean {
  const { circle, box } = shape;
  if (!insideCell(circle, box)) return false;
  if (circleHitsCircle(circle, FACE, BADGE_GAP) || (box !== null && circleHitsBox(FACE, box, BADGE_GAP))) return false;
  for (const o of avoid) {
    if (o.numOnly !== true && o.circle !== null && circleHitsCircle(circle, o.circle, BADGE_GAP)) return false;
    if (o.numOnly !== true && o.box !== null && circleHitsBox(circle, o.box, BADGE_GAP)) return false;
    if (box !== null && o.circle !== null && circleHitsBox(o.circle, box, BADGE_GAP)) return false;
    if (box !== null && o.box !== null && boxHitsBox(box, o.box, BADGE_NUM_GAP)) return false;
  }
  return true;
}


/** 搜尋的格點間距（世界座標）。 */
const STEP = 0.5;

/**
 * 一顆徽章放好的位置：`tier` 是用到第幾層（0 ＝ 全部避開；越大放寬越多），
 * `faceOk` 是否避開了相鄰格的臉（6F-13；`false` 時徽章畫在那個單位的下層，見 `rowLayers.ts`）。
 */
export interface Placed {
  x: number;
  y: number;
  tier: number;
  faceOk: boolean;
  /** 數字放在圓的哪裡（灌注一律 `br`，沒有數字）。 */
  corner: NumCorner;
}

/** 臉當成要避開的形狀（6F-13：相鄰格的單位）。 */
function faceObstacles(faces: readonly Circle[]): Obstacle[] {
  return faces.map((c) => ({ circle: c, box: null }));
}

/**
 * 徽章的位置（帶層數）：原位 `pref`（相對格子中心的世界座標）合格就不動；不合格時找離原位最近的合格位置（`nearest`）。
 * `tiers` 是一層一層放寬的「要避開的形狀」：第一層放不下就試下一層，最後一層之後只顧臉和格子。
 * `hard` 每一層都要避開（6F-13：灌注徽章不蓋「+N」）。`faces` 是相鄰格單位的臉（6F-13）：
 * 先在每一層都避開它們；全部放不下才不管相鄰的臉（`faceOk` false，畫在那個單位的下層）。
 * 自己的臉一律優先；都不行（手動縮到很小）才只夾在格子裡。
 */
export function placeBadgeTier(
  kind: BadgeKind,
  pref: { x: number; y: number },
  sc: BadgeScales,
  tiers: ReadonlyArray<readonly Obstacle[]> = [],
  digits = 1,
  faces: readonly Circle[] = [],
  hard: readonly Obstacle[] = [],
  firm: readonly Obstacle[] = [],
): Placed {
  const fits = (others: readonly Obstacle[], corner: NumCorner) => (p: { x: number; y: number }) => badgeFits(badgeShapes(kind, p, sc, digits, corner), others);
  const levels: ReadonlyArray<readonly Obstacle[]> = [...tiers, []];
  const passes: Obstacle[][] = faces.length > 0 ? [faceObstacles(faces), []] : [[]];
  // 數字的位置：同一層裡先試右下（任何位置），放不下才換左下、正下方（灌注沒有數字）
  const corners: readonly NumCorner[] = kind === "infused" ? ["br"] : NUM_CORNERS;
  // 6F-14：`firm`（朝向三角形、「▲N」的數字）每一層都避開；全部放不下時三角形先只讓數字避開（圓可以蓋到），
  // 再不管三角形（「▲N」的數字照樣避開），最後才都不管
  const firms: ReadonlyArray<readonly Obstacle[]> =
    firm.length > 0 ? [firm, firm.map((o) => (o.keep === true ? o : { ...o, numOnly: true })), firm.filter((o) => o.keep === true), []] : [[]];
  let tier = 0;
  for (const keep of firms)
    for (const [pi, near] of passes.entries())
      for (const avoid of levels) {
        for (const corner of corners) {
          const best = nearest(pref, fits([...avoid, ...hard, ...keep, ...near], corner));
          if (best !== null) return { ...best, tier, faceOk: pi === 0, corner };
        }
        tier++;
      }
  const c = badgeShapes(kind, pref, sc, digits).circle;
  const clamp = (v: number) => Math.min(Math.max(v, -LIM + c.r), LIM - c.r);
  return { x: clamp(pref.x), y: clamp(pref.y), tier, faceOk: faces.length === 0, corner: "br" };
}

/** 徽章的位置（`placeBadgeTier` 不帶層數；6F-12 的介面）。 */
export function placeBadge(
  kind: BadgeKind,
  pref: { x: number; y: number },
  sc: BadgeScales,
  tiers: ReadonlyArray<readonly Obstacle[]> = [],
  digits = 1,
  faces: readonly Circle[] = [],
): { x: number; y: number } {
  const p = placeBadgeTier(kind, pref, sc, tiers, digits, faces);
  return { x: p.x, y: p.y };
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

/** 6F-13 的排法選項：`faces` 相鄰格單位的臉、`plusBoxes` 狀態列的「+N」字（灌注徽章每一層都避開）。 */
export interface BadgeLayoutOpts {
  faces?: readonly Circle[];
  plusBoxes?: readonly Box[];
  /** 6F-14：每一層都避開、最後才放寬的方框（朝向三角形）。 */
  firmBoxes?: readonly Box[];
  /** 6F-14：比 `firmBoxes` 更晚放寬的方框（同一格「▲N」的數字：徽章可以蓋到「▲」，數字一定要看得到）。 */
  keepBoxes?: readonly Box[];
}

export interface BadgeLayout {
  at: { x: number; y: number };
  sc: BadgeScales;
  tier: number;
  faceOk: boolean;
  corner: NumCorner;
}

/**
 * 一個單位所有徽章的位置（縮放 `boardScale`）：照順序放，回傳和 `reqs` 同順序的圓心、倍率與用到的層數。
 * 避開的順序（放不下時一層一層放寬，`placeBadgeTier`）：
 * ① 前面放好的徽章、`extra`（召喚物回合數徽章）、`rowBoxes`（腳邊狀態列的圖示與「+N」字）；
 * ② 回合數徽章與狀態列（和前面的徽章重疊）；③ 只避開回合數徽章（徽章畫在狀態列上面，數字照樣讀得出來）。
 * 6F-13：每一層都避開相鄰格單位的臉（`opts.faces`），全部放不下才不管；灌注徽章每一層都避開「+N」（`opts.plusBoxes`）。
 */
export function layoutBadges(reqs: BadgeReq[], boardScale: number, extra: Circle[] = [], rowBoxes: readonly Box[] = [], opts: BadgeLayoutOpts = {}): BadgeLayout[] {
  const turns: Obstacle[] = extra.map((c) => ({ circle: c, box: null }));
  const must: Obstacle[] = [...turns, ...rowBoxes.map((b) => ({ circle: null, box: b }))];
  const placed: Obstacle[] = [...must];
  const faces = opts.faces ?? [];
  const plus: Obstacle[] = (opts.plusBoxes ?? []).map((b) => ({ circle: null, box: b }));
  const firm: Obstacle[] = [...(opts.firmBoxes ?? []).map((b) => ({ circle: null, box: b })), ...(opts.keepBoxes ?? []).map((b) => ({ circle: null, box: b, keep: true }))];
  return reqs.map((r) => {
    const sc = badgeScales(r.kind, boardScale);
    const p = placeBadgeTier(r.kind, { x: r.at.x * T, y: r.at.y * T }, sc, [placed, must, turns], r.digits, faces, r.kind === "infused" ? plus : [], firm);
    const at = { x: p.x, y: p.y };
    placed.push(badgeShapes(r.kind, at, sc, r.digits, p.corner));
    return { at, sc, tier: p.tier, faceOk: p.faceOk, corner: p.corner };
  });
}

// ---- 6F-13：擁擠時狀態列讓位、只留「+N」 ----

/**
 * 狀態列的顯示方式（美術 PM 6F-12 檢查第 2 節第 2 點、第 3 節）：
 * - `normal` 照 `rowLayout.ts`；
 * - `shift-r`／`shift-l` 圖示照舊，整排靠右、靠左（讓出另一邊給徽章；召喚物沒有，右上有回合數徽章）；
 * - `plus-c`／`plus-r`／`plus-l` 只顯示「+N」字（N ＝ 全部的狀態數），放在中間、靠右、靠左（只在精簡列）。
 */
export type RowMode = "normal" | "shift-r" | "shift-l" | "plus-c" | "plus-r" | "plus-l";
export const SHIFT_MODES: readonly RowMode[] = ["shift-r", "shift-l"];
export const PLUS_ONLY_MODES: readonly RowMode[] = ["plus-c", "plus-r", "plus-l"];

/** 一種顯示方式畫出來的形狀：`boxes` 全部（圖示、角標、「+N」字），`plus` 其中的「+N」字。 */
export interface RowVariantShapes {
  boxes: Box[];
  plus: Box[];
}

/**
 * 狀態列要用哪一種顯示方式（6F-13；純函式，確定性）。`variants` 裡有的才會選：
 * - 沒有徽章：`normal`；
 * - 精簡列（縮放 ≤ 85%）有灌注徽章：一律只留「+N」（中間 → 靠右 → 靠左，選第一個讓每顆徽章都在第 0 層的；都不行就中間）；
 * - 其他：照 `normal` → 靠右 → 靠左 →（精簡列才有）只留「+N」的順序，選第一個讓每顆徽章都在第 0 層
 *   （不碰臉、狀態列、彼此、回合數徽章）的；都不行時精簡列只留「+N」（中間），否則 `normal`（徽章照舊一層一層放寬）。
 */
export function chooseRowMode(
  reqs: BadgeReq[],
  boardScale: number,
  extra: Circle[],
  variants: Partial<Record<RowMode, RowVariantShapes>>,
  compact: boolean,
  faces: readonly Circle[] = [],
  firmBoxes: readonly Box[] = [],
  keepBoxes: readonly Box[] = [],
): RowMode {
  if (reqs.length === 0) return "normal";
  const strict = (m: RowMode) => {
    const v = variants[m];
    return v !== undefined && layoutBadges(reqs, boardScale, extra, v.boxes, { faces, plusBoxes: v.plus, firmBoxes, keepBoxes }).every((l) => l.tier === 0);
  };
  const plusOk = compact && variants["plus-c"] !== undefined;
  // 6F-14：沒有灌注時，只留「+N」先放在第一顆徽章的另一側（徽章在左就先試靠右），字和徽章的數字不擠在一起
  const away = reqs[0]!.at.x;
  const plusOrder: readonly RowMode[] = away < 0 ? ["plus-r", "plus-l", "plus-c"] : away > 0 ? ["plus-l", "plus-r", "plus-c"] : PLUS_ONLY_MODES;
  const order: RowMode[] = plusOk && reqs.some((r) => r.kind === "infused") ? [...PLUS_ONLY_MODES] : ["normal", ...SHIFT_MODES, ...(plusOk ? plusOrder : [])];
  return order.find(strict) ?? (plusOk ? "plus-c" : "normal");
}
// ---- 6F-13：相鄰格單位的臉 ----

/** 算臉要用的單位資料：格子、所在格的高度、是否倒下（倒下的人躺著，頭不往上伸）。 */
export interface FaceSource {
  x: number;
  y: number;
  height: number;
  downed: boolean;
}

/**
 * 相鄰格的單位伸進這一格的臉（相對這一格中心的世界座標，美術 PM 6F-12 檢查第 2 節第 3 點）：
 * 只有南邊（`y` 較大）的單位頭會往上伸進來；站在較高的格子上時再往上 `tileLift(高度差)`。
 * 臉的大小照標準人形（`FACE`）。整顆在這一格外面的不算。照 y、x 排序（確定性）。
 */
export function neighborFaces(self: { x: number; y: number; height: number }, others: readonly FaceSource[]): Circle[] {
  const out: Circle[] = [];
  for (const o of others) {
    const dx = o.x - self.x;
    const dy = o.y - self.y;
    if (o.downed || dy <= 0 || Math.abs(dx) > 1) continue;
    const c = { x: dx * T + FACE.x, y: dy * T + FACE.y - (tileLift(o.height) - tileLift(self.height)), r: FACE.r };
    if (c.x + c.r <= -T / 2 || c.x - c.r >= T / 2 || c.y + c.r <= -T / 2 || c.y - c.r >= T / 2) continue;
    out.push(c);
  }
  return out.sort((a, b) => a.y - b.y || a.x - b.x);
}

/** 一顆徽章（圓＋數字的方框）是否碰到方框 `b`（6F-14：「▲N」的數字要看得到）。 */
export function shapeHitsBox(shape: { circle: Circle; box: Box | null }, b: Box, gap = 0): boolean {
  return circleHitsBox(shape.circle, b, gap) || (shape.box !== null && boxHitsBox(shape.box, b, gap));
}
