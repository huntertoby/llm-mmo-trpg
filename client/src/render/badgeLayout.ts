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
/**
 * 6F-18：徽章放不好（放不下、蓋到「+N」或回合數徽章、數字碰到朝向三角形或 HP 條）。
 * 6F-17 這時把數字放進圓裡（`NUM_CENTER`）；美術 PM 6F-17 檢查：蓄力的靶心被數字蓋住，改回 6F-16 的圓外（拿掉）。
 * 現在只給 `chooseRowLayout` 判斷要不要讓狀態列只留「+N」。
 */
export function placedPoorly(p: Pick<Placed, "firm" | "level">): boolean {
  if (p.firm >= FIRM_STEPS.length || (p.level ?? 0) >= 2) return true;
  const step = FIRM_STEPS[p.firm]!;
  return step.arrow === "off" || step.hp !== "full";
}

/** 數字中心相對圓心的位置（徽章節點的本地座標，放大前）。 */
export function numberAt(corner: NumCorner): { x: number; y: number } {
  const a = STATUS_BADGE_NUM_AT;
  if (corner === "b") return { x: 0, y: a + 1.5 };
  return { x: corner === "bl" ? -a : a, y: a };
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
  /** 6F-15：`firm` 裡的角色（預設 `arrow` 朝向三角形；`hp` HP 條），照 `FIRM_STEPS` 一步一步放寬。 */
  role?: FirmRole;
  /** 6F-15：三角形的三個頂點（`[x0, y0, x1, y1, x2, y2]`）；`maxCover` 時用它算圓蓋到多少。 */
  poly?: readonly number[];
  /** 6F-15：圓可以蓋到，但最多蓋到三角形面積的這個比例（`numOnly` 時才看；數字照樣不碰）。 */
  maxCover?: number;
}

/** 數字的方框 `box` 是否碰到 `o`。 */
function numHits(box: Box, o: Obstacle): boolean {
  if (o.circle !== null && circleHitsBox(o.circle, box, BADGE_GAP)) return true;
  return o.box !== null && boxHitsBox(box, o.box, BADGE_NUM_GAP);
}

/** 6F-15：`firm` 方框的角色：朝向三角形、HP 條（6F-18：有人站的格子不畫「▲N」，6F-14～6F-16 的「▲N」數字拿掉）。 */
export type FirmRole = "arrow" | "hp";
type FirmMode = "full" | "partial" | "num" | "off";

/**
 * `firm` 一步一步放寬的順序（6F-15，美術 PM 6F-14 檢查）：
 * ① 全部避開；② 三角形：圓最多蓋到 `ARROW_MAX_COVER`（數字不碰）；③ 三角形：只有數字避開（朝北，美術 PM 照收）；
 * ④ HP 條：只有數字避開（數字型徽章一律不壓在 HP 條上）；⑤ 不管三角形；⑥ 不管 HP 條（最後）。
 */
export const FIRM_STEPS: ReadonlyArray<Readonly<Record<FirmRole, FirmMode>>> = [
  { arrow: "full", hp: "full" },
  { arrow: "partial", hp: "full" },
  { arrow: "num", hp: "full" },
  { arrow: "num", hp: "num" },
  { arrow: "off", hp: "num" },
  { arrow: "off", hp: "off" },
];
/** 6F-16：`FIRM_STEPS` 裡開始放寬 HP 條（圓可以碰到）的第一步。 */
export const FIRM_HP_FIRST = FIRM_STEPS.findIndex((f) => f.hp !== "full");
/** 圓蓋到三角形面積的上限（6F-15：「徽章不能蓋住三角形的大部分」；放寬的第 ② 步）。 */
export const ARROW_MAX_COVER = 0.4;

function roleOf(o: Obstacle): FirmRole {
  return o.role ?? "arrow";
}

/** 三角形（`poly`，沒有時用方框）裡的取樣點（間距 0.5，確定性）。 */
const samplesMemo = new WeakMap<readonly number[], Array<[number, number]>>();
function polySamples(o: Obstacle): Array<[number, number]> {
  const b = o.box!;
  const hit = o.poly !== undefined ? samplesMemo.get(o.poly) : undefined;
  if (hit !== undefined) return hit;
  const p = o.poly ?? [b.l, b.t, b.r, b.t, b.r, b.b, b.l, b.t, b.r, b.b, b.l, b.b];
  const tris: number[][] = [];
  for (let i = 0; i + 5 < p.length; i += 6) tris.push(p.slice(i, i + 6));
  const inTri = (x: number, y: number, t: number[]) => {
    const d = (ax: number, ay: number, bx: number, by: number) => (x - bx) * (ay - by) - (ax - bx) * (y - by);
    const d1 = d(t[0]!, t[1]!, t[2]!, t[3]!);
    const d2 = d(t[2]!, t[3]!, t[4]!, t[5]!);
    const d3 = d(t[4]!, t[5]!, t[0]!, t[1]!);
    return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
  };
  const out: Array<[number, number]> = [];
  for (let y = Math.ceil(b.t * 2) / 2; y <= b.b; y += 0.5)
    for (let x = Math.ceil(b.l * 2) / 2; x <= b.r; x += 0.5) if (tris.some((t) => inTri(x, y, t))) out.push([x, y]);
  if (o.poly !== undefined) samplesMemo.set(o.poly, out);
  return out;
}

/** 圓蓋到三角形面積的比例（6F-15；取樣點，確定性）。 */
export function coverFraction(c: Circle, o: Obstacle): number {
  const pts = polySamples(o);
  if (pts.length === 0) return 0;
  let n = 0;
  for (const [x, y] of pts) if ((x - c.x) ** 2 + (y - c.y) ** 2 < c.r * c.r) n++;
  return n / pts.length;
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
    if (box !== null && numHits(box, o)) return false;
  }
  // 6F-15：圓可以蓋到三角形，但不能蓋住大部分（最後才算，取樣比較慢）
  for (const o of avoid) if (o.maxCover !== undefined && o.box !== null && circleHitsBox(circle, o.box) && coverFraction(circle, o) > o.maxCover + 1e-9) return false;
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
  /** 6F-15：`firm` 放寬到 `FIRM_STEPS` 的第幾步（0 ＝ 三角形、HP 條全部避開）。 */
  firm: number;
  /** 6F-17：用到 `tiers` 的第幾層（`tiers.length` ＝ 只顧臉和格子）。 */
  level?: number;
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
  const levels: ReadonlyArray<readonly Obstacle[]> = [...tiers, []];
  const faceObs = faceObstacles(faces);
  const passes: ReadonlyArray<readonly Obstacle[]> = faces.length > 0 ? [faceObs, []] : [[]];
  // 數字的位置：同一層裡先試右下（任何位置），放不下才換左下、正下方（灌注沒有數字）
  const corners: readonly NumCorner[] = kind === "infused" ? ["br"] : NUM_CORNERS;
  // 6F-15：每個點、每個數字位置和每個形狀碰不碰只算一次（`HitCache`），每一層只是查表（擁擠時一層一層放寬要試很多次）
  const all: Obstacle[] = [];
  const index = new Map<Obstacle, number>();
  for (const o of [...levels.flat(), ...hard, ...firm, ...faceObs])
    if (!index.has(o)) {
      index.set(o, all.length);
      all.push(o);
    }
  const order = searchOrder(pref);
  const caches = corners.map((corner) => new HitCache(kind, sc, digits, corner, all, order));
  // 6F-17：`hard`（狀態圖示）每一步都避開：先篩掉碰到的點，之後每一步只看剩下的（徽章再排很多次時省時間）
  const hardIdx = [...new Set(hard.filter((o) => o.numOnly !== true).map((o) => index.get(o)!))];
  for (const c of caches) c.setHard(hardIdx);
  // 6F-14：`firm`（朝向三角形）每一層都避開；6F-15 起照 `FIRM_STEPS` 一步一步放寬
  // （三角形先讓圓蓋到一小部分、再只讓數字避開；HP 條只讓數字避開）。和前面一樣的步驟跳過
  const roles = [...new Set(firm.map(roleOf))].sort();
  let tier = 0;
  const seen = new Set<string>(); // 6F-16：和前面任何一步一樣的步驟跳過（沒有三角形或 HP 條時）
  for (const [fi, step] of FIRM_STEPS.entries()) {
    const key = roles.map((r) => `${r}:${step[r]}`).join(",");
    if (seen.has(key)) continue;
    seen.add(key);
    const keep: Array<[Obstacle, FirmMode]> = firm.map((o) => [o, step[roleOf(o)]]);
    for (const [pi, near] of passes.entries())
      for (const [li, avoid] of levels.entries()) {
        const spec = [...[...avoid, ...hard, ...near].map((o): [Obstacle, FirmMode] => [o, o.numOnly === true ? "num" : "full"]), ...keep].map(([o, m]): [number, FirmMode] => [index.get(o)!, m]);
        for (const [ci, corner] of corners.entries()) {
          const at = caches[ci]!.first(spec);
          if (at !== null) return { ...at, tier, faceOk: pi === 0, corner, firm: fi, level: li };
        }
        tier++;
      }
  }
  const c = badgeShapes(kind, pref, sc, digits).circle;
  const clamp = (v: number) => Math.min(Math.max(v, -LIM + c.r), LIM - c.r);
  return { x: clamp(pref.x), y: clamp(pref.y), tier, faceOk: faces.length === 0, corner: "br", firm: FIRM_STEPS.length, level: levels.length };
}

/**
 * 搜尋的順序（6F-15）：原位 `pref`，再來是格點（間距 `STEP`），離原位近的先；一樣近時先上後下、先左後右
 * （和 6F-12 的 `nearest` 一樣：原位合格就是原位，否則離原位最近的合格格點）。照原位記下來（原位只有幾種）。
 */
const orderMemo = new Map<string, ReadonlyArray<{ x: number; y: number }>>();
function searchOrder(pref: { x: number; y: number }): ReadonlyArray<{ x: number; y: number }> {
  const step = STEP;
  const key = `${pref.x},${pref.y}`;
  const hit = orderMemo.get(key);
  if (hit !== undefined) return hit;
  const n = Math.round(LIM / step);
  const grid: Array<{ x: number; y: number; d: number; i: number }> = [];
  for (let iy = -n; iy <= n; iy++)
    for (let ix = -n; ix <= n; ix++) {
      const p = { x: ix * step, y: iy * step };
      grid.push({ ...p, d: (p.x - pref.x) ** 2 + (p.y - pref.y) ** 2, i: grid.length });
    }
  grid.sort((a, b) => (Math.abs(a.d - b.d) > 1e-9 ? a.d - b.d : a.i - b.i));
  const out = [{ ...pref }, ...grid.map((g) => ({ x: g.x, y: g.y }))];
  orderMemo.set(key, out);
  return out;
}

/** 每個搜尋點碰到哪些形狀（6F-15；用到才算，算過就記住）。 */
class HitCache {
  /** 0 ＝ 還沒算；1 ＝ 在格子裡、不碰自己的臉；2 ＝ 不合格。 */
  private readonly base: Uint8Array;
  /** 每個形狀：0 還沒算；bit 1 已算、bit 2 圓碰到、bit 4 數字碰到、bit 8 圓蓋住三角形太多（bit 16 ＝ bit 8 已算）。 */
  private readonly hits: Uint8Array[];
  constructor(
    private readonly kind: BadgeKind,
    private readonly sc: BadgeScales,
    private readonly digits: number,
    private readonly corner: NumCorner,
    private readonly all: readonly Obstacle[],
    private readonly order: ReadonlyArray<{ x: number; y: number }>,
  ) {
    this.base = new Uint8Array(order.length);
    this.hits = all.map(() => new Uint8Array(order.length));
  }

  private shape(i: number): { circle: Circle; box: Box | null } {
    return badgeShapes(this.kind, this.order[i]!, this.sc, this.digits, this.corner);
  }

  private baseOk(i: number): boolean {
    if (this.base[i] === 0) {
      const { circle, box } = this.shape(i);
      const ok = insideCell(circle, box) && !circleHitsCircle(circle, FACE, BADGE_GAP) && !(box !== null && circleHitsBox(FACE, box, BADGE_GAP));
      this.base[i] = ok ? 1 : 2;
    }
    return this.base[i] === 1;
  }

  private hit(i: number, j: number, want8: boolean): number {
    const h = this.hits[j]!;
    if (h[i] === 0) {
      const { circle, box } = this.shape(i);
      const o = this.all[j]!;
      let v = 1;
      // 6F-17：`numOnly` 的形狀只有數字要避開（圓可以蓋到）
      if (o.numOnly !== true && ((o.circle !== null && circleHitsCircle(circle, o.circle, BADGE_GAP)) || (o.box !== null && circleHitsBox(circle, o.box, BADGE_GAP)))) v |= 2;
      if (box !== null && numHits(box, o)) v |= 4;
      h[i] = v;
    }
    let v = h[i]!;
    // 圓蓋住三角形太多（只有放寬成「圓可以蓋一小部分」時才問，取樣比較慢）
    if (want8 && (v & 24) === 0) {
      const { circle } = this.shape(i);
      const o = this.all[j]!;
      v |= o.box !== null && circleHitsBox(circle, o.box) && coverFraction(circle, o) > ARROW_MAX_COVER + 1e-9 ? 24 : 16;
      h[i] = v;
    }
    return v;
  }

  /** 照搜尋順序第一個合格的點（`spec`：形狀的索引與避開的方式）；沒有 `null`。 */
  /**
   * 6F-17：在格子裡、不碰自己的臉、不碰 `hard`（每一步都要避開的形狀）的點（照搜尋順序）。用到才往下找、找過的記住：
   * 徽章再排很多次、每一步都從頭找時，不用每次都重看被狀態圖示擋住的點。
   */
  private readonly cands: number[] = [];
  private scanned = 0;
  private hardIdx: readonly number[] = [];
  setHard(hard: readonly number[]): void {
    this.hardIdx = hard;
  }
  private candAt(n: number): number | null {
    while (this.cands.length <= n && this.scanned < this.order.length) {
      const i = this.scanned++;
      if (this.baseOk(i) && this.hardIdx.every((j) => (this.hit(i, j, false) & 6) === 0)) this.cands.push(i);
    }
    return n < this.cands.length ? this.cands[n]! : null;
  }

  first(spec: ReadonlyArray<[number, FirmMode]>): { x: number; y: number } | null {
    const need = spec.filter(([j, m]) => m !== "off" && !(m === "full" && this.hardIdx.includes(j))).map(([j, m]): [number, number] => [j, m === "full" ? 6 : m === "partial" ? 12 : 4]);
    for (let n = 0; ; n++) {
      const i = this.candAt(n);
      if (i === null) break;
      let ok = true;
      for (const [j, mask] of need)
        if ((this.hit(i, j, (mask & 8) !== 0) & mask) !== 0) {
          ok = false;
          break;
        }
      if (ok) return { ...this.order[i]! };
    }
    return null;
  }
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
  /** 6F-17：`rowBoxes` 裡的數字（「+N」字、「+N」角標；同一個物件）：圖示一律避開，這些照 6F-16 最後才可以蓋到。 */
  rowNums?: readonly Box[];
  /** 6F-14：每一層都避開、最後才放寬的方框（朝向三角形）。 */
  firmBoxes?: readonly Box[];
  /** 6F-15：朝向三角形的三個頂點（`firmBoxes` 第一個方框的形狀；算圓蓋到多少）。 */
  arrowPoly?: readonly number[];
  /** 6F-15：HP 條（含護盾條）：徽章不蓋到；放不下時只讓數字避開，數字一律不壓在上面。 */
  hpBoxes?: readonly Box[];
}

export interface BadgeLayout {
  at: { x: number; y: number };
  sc: BadgeScales;
  tier: number;
  faceOk: boolean;
  corner: NumCorner;
  /** 6F-15：`FIRM_STEPS` 放寬到第幾步。 */
  firm: number;
  /** 6F-17：用到第幾層（2 以上 ＝ 蓋到「+N」或回合數徽章）。 */
  level?: number;
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
  // 6F-17（美術 PM 6F-16 檢查必修 1：徽章的圓蓋住防禦圖示）：狀態列的圖示每一層都避開（`hard`），
  // 不再有「徽章畫在圖示上面」的那一層；放不下時由狀態列換顯示方式（`chooseRowLayout`）讓出位置。
  // 「+N」字與「+N」角標（`rowNums`）照 6F-16：最後才可以蓋到（比徽章的數字碰到朝向三角形先）
  const nums = new Set(opts.rowNums ?? []);
  const icons: Obstacle[] = rowBoxes.filter((b) => !nums.has(b)).map((b) => ({ circle: null, box: b }));
  const soft: Obstacle[] = rowBoxes.filter((b) => nums.has(b)).map((b) => ({ circle: null, box: b }));
  const must: Obstacle[] = [...turns, ...soft];
  const placed: Obstacle[] = [...must];
  const faces = opts.faces ?? [];
  const plus: Obstacle[] = (opts.plusBoxes ?? []).map((b) => ({ circle: null, box: b }));
  const base: Obstacle[] = [
    ...(opts.firmBoxes ?? []).map((b, i): Obstacle => ({ circle: null, box: b, role: "arrow", ...(i === 0 && opts.arrowPoly !== undefined ? { poly: opts.arrowPoly } : {}) })),
    ...(opts.hpBoxes ?? []).map((b): Obstacle => ({ circle: null, box: b, role: "hp" })),
  ];
  return reqs.map((r) => {
    const sc = badgeScales(r.kind, boardScale);
    // 6F-18（美術 PM 6F-17 檢查必修 3）：數字一律在圓外、緊貼自己的圓（6F-16 的位置：右下、左下、正下方），不放進圓裡
    const p = placeBadgeTier(r.kind, { x: r.at.x * T, y: r.at.y * T }, sc, [placed, must, turns], r.digits, faces, r.kind === "infused" ? [...icons, ...plus] : icons, base);
    const at = { x: p.x, y: p.y };
    placed.push(badgeShapes(r.kind, at, sc, r.digits, p.corner));
    return { at, sc, tier: p.tier, faceOk: p.faceOk, corner: p.corner, firm: p.firm, ...(p.level === undefined ? {} : { level: p.level }) };
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

/** 6F-17：不是精簡列時，徽章怎麼放都會蓋到狀態列才用的「只留 +N」（`chooseRowLayout`）。 */
export interface RowRescue {
  rescue?: () => Partial<Record<RowMode, RowVariantShapes>>;
  /** 6F-18：狀態 2 個以內時的「只留 +N」：徽章在任何顯示方式都放不下（`firm` ＝ `FIRM_STEPS.length`）才用。 */
  lastResort?: () => Partial<Record<RowMode, RowVariantShapes>>;
}

/** 一種顯示方式畫出來的形狀：`boxes` 全部（圖示、角標、「+N」字），`plus` 其中的「+N」字。 */
export interface RowVariantShapes {
  boxes: Box[];
  plus: Box[];
  /** 6F-17：其中的數字（「+N」字、「+N」角標的外接方框）：徽章最後才可以蓋到（`layoutBadges` 的 `rowNums`）。沒有時用 `plus`。 */
  nums?: Box[];
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
  more: Pick<BadgeLayoutOpts, "arrowPoly" | "hpBoxes"> & RowRescue = {},
): RowMode {
  return chooseRowLayout(reqs, boardScale, extra, variants, compact, faces, firmBoxes, more).mode;
}

/** `chooseRowMode` 連同選到的那一種的徽章排法（6F-15：同一種顯示方式只排一次；沒有排過時 `lays` 是 `undefined`）。 */
export function chooseRowLayout(
  reqs: BadgeReq[],
  boardScale: number,
  extra: Circle[],
  variants: Partial<Record<RowMode, RowVariantShapes>>,
  compact: boolean,
  faces: readonly Circle[] = [],
  firmBoxes: readonly Box[] = [],
  more: Pick<BadgeLayoutOpts, "arrowPoly" | "hpBoxes"> & RowRescue = {},
): { mode: RowMode; lays: BadgeLayout[] | undefined } {
  if (reqs.length === 0) return { mode: "normal", lays: undefined };
  const memo = new Map<RowMode, BadgeLayout[]>();
  const layOf = (m: RowMode, v: RowVariantShapes): BadgeLayout[] => {
    let got = memo.get(m);
    if (got === undefined) {
      got = layoutBadges(reqs, boardScale, extra, v.boxes, { faces, plusBoxes: v.plus, rowNums: v.nums ?? v.plus, firmBoxes, ...more });
      memo.set(m, got);
    }
    return got;
  };
  const strict = (m: RowMode) => {
    const v = variants[m];
    return v !== undefined && layOf(m, v).every((l) => l.tier === 0);
  };
  const done = (mode: RowMode) => ({ mode, lays: memo.get(mode) });
  const plusOk = compact && variants["plus-c"] !== undefined;
  // 6F-14：沒有灌注時，只留「+N」先放在第一顆徽章的另一側（徽章在左就先試靠右），字和徽章的數字不擠在一起
  const away = reqs[0]!.at.x;
  const plusOrder: readonly RowMode[] = away < 0 ? ["plus-r", "plus-l", "plus-c"] : away > 0 ? ["plus-l", "plus-r", "plus-c"] : PLUS_ONLY_MODES;
  const infused = plusOk && reqs.some((r) => r.kind === "infused");
  const order: RowMode[] = infused ? [...PLUS_ONLY_MODES] : ["normal", ...SHIFT_MODES, ...(plusOk ? plusOrder : [])];
  const hit = order.find(strict);
  if (hit !== undefined || infused) return done(hit ?? "plus-c");
  // 6F-14：都放不下時（例如 800 寬朝北：三角形在正中間），選徽章放寬得最少的一種（一樣時照順序），不一律只留「+N」
  let best: { m: RowMode; t: number } | null = null;
  for (const m of order) {
    const v = variants[m];
    if (v === undefined) continue;
    const t = Math.max(...layOf(m, v).map((l) => l.tier));
    if (best === null || t < best.t) best = { m, t };
  }
  // 6F-17：徽章的圓不蓋狀態列以後，1600 寬（不是精簡列）身上 3 個狀態加蓄力時，有的徽章怎麼放都會蓋到圖示。
  // 這時才用只留「+N」（`more.rescue`，最後的手段；圖示的資訊在格子資訊卡）
  const unplaced = (m: RowMode) => memo.get(m)?.some((l) => placedPoorly(l)) ?? true;
  const rescue = more.rescue !== undefined && (best === null || unplaced(best.m)) ? more.rescue() : {};
  for (const m of plusOrder) {
    const v = rescue[m];
    if (v === undefined) continue;
    const t = Math.max(...layOf(m, v).map((l) => l.tier));
    if (!unplaced(m) && (best === null || unplaced(best.m) || t < best.t)) best = { m, t };
  }
  // 6F-18：狀態 2 個以內時不為了徽章只留「+N」（美術 PM 6F-17 檢查必修 2）；只有徽章在任何顯示方式都放不下
  // （格子裡沒有不碰臉、狀態圖示的位置）時才用（`more.lastResort`）
  const nowhere = (m: RowMode) => memo.get(m)?.some((l) => l.firm >= FIRM_STEPS.length) ?? true;
  const last = more.lastResort !== undefined && (best === null || nowhere(best.m)) ? more.lastResort() : {};
  for (const m of plusOrder) {
    const v = last[m];
    if (v === undefined) continue;
    const t = Math.max(...layOf(m, v).map((l) => l.tier));
    if (!nowhere(m) && (best === null || nowhere(best.m) || t < best.t)) best = { m, t };
  }
  return done(best?.m ?? (plusOk ? "plus-c" : "normal"));
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

/** 一顆徽章（圓＋數字的方框）是否碰到方框 `b`（6F-14；測試用）。 */
export function shapeHitsBox(shape: { circle: Circle; box: Box | null }, b: Box, gap = 0): boolean {
  return circleHitsBox(shape.circle, b, gap) || (shape.box !== null && boxHitsBox(shape.box, b, gap));
}
