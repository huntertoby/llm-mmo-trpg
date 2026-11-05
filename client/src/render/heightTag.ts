// 6F-17：有人站的格子，「▲N」縮成角標（美術 PM 6F-16 檢查第 2 節選 (b)）：角標放哪裡、徽章與狀態列怎麼排（純函式，確定性）。
//
// 規則（全部是世界座標、相對格子中心；畫面像素 ÷ 地圖縮放 ＝ 世界座標）：
// - 一定做到：角標整個在格子裡、不碰自己的臉、HP 條、朝東西的三角形（`heightMarkGrid`，底可以碰到三角形尖端的位置排最後），
//   不碰相鄰格單位伸進來的頭（`faces`）；左右平移最多 `TAG_MAX_SHIFT`（6F-16 照收的 13，從左邊或右邊的角量起）。
//   徽章的圓與數字不蓋狀態圖示（`badgeLayout.layoutBadges` 的 `hard`）。
// - 盡量做到（照 `tagBetter` 的順序，格子放不下時前面的優先）：
//   ① 看得到：徽章不碰 HP 條、圓蓋到朝向三角形不超過 40%（朝北照收）、不蓋角標的數字或「▲」以外的地方、不蓋「+N」；狀態列不蓋角標的「▲」和數字；
//   ② 角標的數字和別的數字（徽章的數字、「+N」字、「+N」角標）在斜對角，左右、上下都至少隔 2px（6F-16 的規則）；
//   ③ 角標的底不碰狀態列（`HEIGHT_MARK_ROW_GAP`），數字和狀態圖示至少隔 2px；
//   ④ 狀態列照不管角標時的排法（狀態列是戰鬥資訊，美術 PM 不選 (a)）；
//   ⑤ 徽章的圓離角標的數字至少 2px；角標的數字和狀態圖示也在斜對角；徽章放寬得少。
//
// 搜尋：先用不管角標時的徽章與狀態列（徽章不動），在所有位置裡找最好的；不夠好時讓徽章再排（避開角標的數字，`keepBoxes`）；
// 再不夠好時換狀態列的顯示方式；還有看不到的時，徽章再排時兩個數字只要不碰到。一樣好時用前面的位置（離原位近的）。

import { badgeShapes, FIRM_HP_FIRST, FIRM_SEP_LAST, FIRM_STEPS, numbersApart, NUM_SEP_PX, PLUS_ONLY_MODES, SHIFT_MODES, type BadgeLayout, type BadgeReq, type RowMode, type RowVariantShapes } from "./badgeLayout";
import type { HeightMarkPos } from "./heightMark";
import { TILE_SIZE } from "../battle/geometry";
import { circleHitsBox, type Box, type Circle } from "./rowLayout";

const T = TILE_SIZE;

/** 「▲N」和狀態列（圖示、「+N」）之間至少留的空隙（世界座標；6F-16）。 */
export const HEIGHT_MARK_ROW_GAP = 0.5;
/** 角標左右平移最多多少（世界座標；6F-16 照收「下緣 ▲N 平移最多 13」）。 */
export const TAG_MAX_SHIFT = 13;
/** 徽章再排（很慢）最多試幾個位置（效能：最擠的情況一個單位不超過 0.5 秒）。 */
export const TAG_RELAY_TRIES = 30;
/** 徽章再排時搜尋的格點間距（世界座標；一般是 0.5，再排要試很多次，用粗一點的 1）。 */
export const TAG_RELAY_STEP = 1;
/** 狀態列換別的顯示方式時，每一種最多試幾個位置（效能）。 */
export const TAG_RELAY_TRIES_OTHER = 16;
/** 還有看不到的東西時（兩個數字只要不碰到），最多試幾個位置（效能）。 */
export const TAG_LOOSE_TRIES = 8;
/** 再排的位置分散在格子的各處（不要都試緊鄰的幾格）：照數字的中心分成邊長 `RELAY_CELL` 的小區，每區只試最前面的一個。 */
const RELAY_CELL = T / 8;
function regionOf(digit: Box): string {
  const x = (digit.l + digit.r) / 2;
  const y = (digit.t + digit.b) / 2;
  return `${Math.floor(x / RELAY_CELL)},${Math.floor(y / RELAY_CELL)}`;
}

/** 狀態列顯示方式的優先順序（不管角標時選的那一種最先）。 */
export const ROW_MODE_ORDER: readonly RowMode[] = ["normal", ...SHIFT_MODES, ...PLUS_ONLY_MODES];

/** 角標在 `pos` 時的形狀：`box` 底、`ink`「▲」和數字、`digit` 數字。 */
export interface TagGeom {
  box(pos: HeightMarkPos): Box;
  ink(pos: HeightMarkPos): Box;
  digit(pos: HeightMarkPos): Box;
}

/** `pickTag` 的輸入。 */
export interface TagEnv {
  reqs: readonly BadgeReq[];
  variants: Partial<Record<RowMode, RowVariantShapes>>;
  hasRow: boolean;
  /** 角標可以讓狀態列換成哪些顯示方式（沒有時 `variants` 全部；6F-17：不是精簡列時的「只留 +N」只給徽章用）。 */
  switchable?: readonly RowMode[];
  /** 地圖縮放（畫面像素換世界座標）。 */
  s: number;
  geom: TagGeom;
  /** 可以放的位置（照優先順序：離原位近的先）。 */
  positions: readonly HeightMarkPos[];
  /** 相鄰格單位伸進這一格的頭（角標不碰）。 */
  faces: readonly Circle[];
  /** 徽章的圓可以整個蓋到朝向三角形（朝北，6F-15 照收）；其他朝向最多 40%（`FIRM_STEPS` 的 `partial`）。 */
  arrowCoverOk: boolean;
  /** 不管角標、照顯示方式 `m` 排徽章（`null` ＝ 讓排法自己選顯示方式）。 */
  layoutFree(): { mode: RowMode; lays: BadgeLayout[] };
  layoutIn(m: RowMode): BadgeLayout[];
  /** 徽章避開角標在 `pos` 時的數字（`vs` 可以用的顯示方式）。 */
  layoutAround(pos: HeightMarkPos, vs: Partial<Record<RowMode, RowVariantShapes>>, maxFirm: number): { mode: RowMode; lays: BadgeLayout[] };
}

/** 一個選擇的分數（越小越好，照欄位順序比）。 */
export interface TagPick {
  mode: RowMode;
  lays: BadgeLayout[];
  drop: HeightMarkPos | null;
  /** 放寬得最多的一顆徽章（`FIRM_STEPS` 的步數）。 */
  worst: number;
  /** 看不到的東西：2 ＝ 徽章的圓碰到 HP 條（或放不下）；1 ＝ 角標的「▲」或數字被蓋到。 */
  hidden: number;
  /** 0 ＝ 數字和徽章分得開；1 ＝ 兩個數字在斜對角，但徽章的圓離角標的數字不到 2px（沒碰到）；2 ＝ 兩個數字貼在一起（沒有斜對角或不到 2px）；3 ＝ 被蓋到。 */
  numLv: number;
  /** 0 ＝ 和狀態列的圖示都在斜對角；1 ＝ 和圖示至少隔 2px；2 ＝ 貼在一起或底碰到；3 ＝ 「▲」或數字被蓋到。 */
  rowLv: number;
  /** 角標的數字和別的數字（徽章的數字、「+N」）貼在一起（不在斜對角或不到 2px）：讀起來像「▲11」，最不能接受。 */
  numClash: boolean;
  /** 狀態列的顯示方式排第幾（0 ＝ 不管角標時選的那一種）。 */
  modeRank: number;
}

/**
 * 角標的左右平移不超過 `TAG_MAX_SHIFT`：從左上角（原位）或右邊的角（和左邊一樣離格子邊緣）量起，近的那一個。
 * 角標貼著格子左邊或右邊的角都算原位（「角標」）。
 */
export function tagShiftOk(geom: TagGeom, p: HeightMarkPos): boolean {
  const home = geom.box({ dx: 0, dy: 0 });
  const b = geom.box(p);
  const inset = home.l + T / 2;
  const fromLeft = Math.abs(b.l - home.l);
  const fromRight = Math.abs(T / 2 - inset - b.r);
  return Math.min(fromLeft, fromRight) <= TAG_MAX_SHIFT + 1e-9;
}

/** 點（圓心）到方框的距離（在方框裡是 0）。 */
function boxDistance(c: { x: number; y: number }, b: Box): number {
  const dx = Math.max(b.l - c.x, 0, c.x - b.r);
  const dy = Math.max(b.t - c.y, 0, c.y - b.b);
  return Math.hypot(dx, dy);
}

const overlap = (a: Box, b: Box, gap: number) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;

/** 角標在 `pos`、狀態列照 `v` 時的 `rowLv`。 */
export function tagRowLevel(geom: TagGeom, pos: HeightMarkPos, v: RowVariantShapes | undefined, s: number): number {
  if (v === undefined) return 0;
  const sep = NUM_SEP_PX / s;
  const ink = geom.ink(pos);
  const digit = geom.digit(pos);
  if (v.boxes.some((b) => overlap(b, ink, 0))) return 3;
  if (v.boxes.some((b) => overlap(b, geom.box(pos), HEIGHT_MARK_ROW_GAP))) return 2;
  if (v.boxes.some((b) => overlap(b, digit, sep))) return 2;
  return v.boxes.every((b) => numbersApart(b, digit, sep)) ? 0 : 1;
}

/** 角標的數字和狀態列裡的數字（「+N」字、「+N」角標）不在斜對角或不到 2px。 */
export function tagRowNumsClash(geom: TagGeom, pos: HeightMarkPos, v: RowVariantShapes | undefined, s: number): boolean {
  if (v === undefined) return false;
  const digit = geom.digit(pos);
  return (v.nums ?? v.plus).some((b) => !numbersApart(b, digit, NUM_SEP_PX / s));
}

/** 徽章排成 `lays` 時角標數字的 `numLv`（灌注沒有數字：整顆至少隔 2px）。 */
export function tagNumLevel(reqs: readonly BadgeReq[], lays: readonly BadgeLayout[], digit: Box, s: number): number {
  const sep = NUM_SEP_PX / s;
  let lv = 0;
  lays.forEach((l, i) => {
    const r = reqs[i]!;
    const shape = badgeShapes(r.kind, l.at, l.sc, r.digits, l.corner);
    if (circleHitsBox(shape.circle, digit) || (shape.box !== null && overlap(shape.box, digit, 0))) lv = 3;
    else if (shape.box !== null && (r.kind === "infused" ? overlap(shape.box, digit, sep) : !numbersApart(shape.box, digit, sep))) lv = Math.max(lv, 2);
    else if (circleHitsBox(shape.circle, digit, sep)) lv = Math.max(lv, 1);
  });
  return lv;
}

/** 好到不用再找：看得到、數字不貼在一起、角標不碰狀態列。 */
export const tagOk = (p: TagPick) => p.hidden === 0 && !p.numClash && p.rowLv < 2;

/** `a` 比 `b` 好（一樣時用 `b`，也就是先找到的）。 */
export function tagBetter(a: TagPick, b: TagPick | null): boolean {
  if (b === null) return true;
  const key = (p: TagPick) => [p.hidden, p.numClash ? 1 : 0, p.rowLv >= 2 ? 1 : 0, p.modeRank, p.numLv, p.rowLv, p.worst];
  const ka = key(a);
  const kb = key(b);
  for (let i = 0; i < ka.length; i++) if (ka[i] !== kb[i]) return ka[i]! < kb[i]!;
  return false;
}

/** 角標放哪裡、徽章與狀態列怎麼排（見檔頭）。沒有位置可以放時 `drop` 是 `null`。 */
export function pickTag(env: TagEnv): TagPick {
  const { reqs, variants, hasRow, s, geom } = env;
  const free = env.layoutFree();
  const modes = hasRow ? [free.mode, ...ROW_MODE_ORDER.filter((m) => m !== free.mode && variants[m] !== undefined && (env.switchable?.includes(m) ?? true))] : [free.mode];
  const rankOf = (m: RowMode) => Math.max(0, modes.indexOf(m));
  const positions = env.positions.filter((p) => tagShiftOk(geom, p) && !env.faces.some((f) => circleHitsBox(f, geom.box(p))));
  const score = (mode: RowMode, lays: BadgeLayout[], pos: HeightMarkPos): TagPick => {
    const worst = Math.max(0, ...lays.map((l) => l.firm));
    const numLv = tagNumLevel(reqs, lays, geom.digit(pos), s);
    const rowLv = hasRow ? tagRowLevel(geom, pos, variants[mode], s) : 0;
    const numClash = numLv >= 2 || (hasRow && tagRowNumsClash(geom, pos, variants[mode], s));
    // 徽章蓋到「+N」（`level` 2 以上）也算看不到
    const arrowBad = !env.arrowCoverOk && lays.some((l) => l.firm < FIRM_STEPS.length && (FIRM_STEPS[l.firm]!.arrow === "num" || FIRM_STEPS[l.firm]!.arrow === "off"));
    const hidden = worst >= FIRM_HP_FIRST || arrowBad ? 2 : numLv === 3 || rowLv === 3 || lays.some((l) => (l.level ?? 0) >= 2) ? 1 : 0;
    return { mode, lays, drop: pos, worst, hidden, numLv, rowLv, numClash, modeRank: rankOf(mode) };
  };
  if (positions.length === 0) return { mode: free.mode, lays: free.lays, drop: null, worst: Math.max(0, ...free.lays.map((l) => l.firm)), hidden: 0, numLv: 0, rowLv: 0, numClash: false, modeRank: 0 };
  let best: TagPick | null = null;
  const fixed = (rank: number) => {
    const m = modes[rank]!;
    const lays = rank === 0 ? free.lays : env.layoutIn(m);
    for (const p of positions) {
      const next = score(m, lays, p);
      if (tagBetter(next, best)) best = next;
      if (tagOk(best!) && best!.numLv === 0 && best!.rowLv === 0) return;
    }
  };
  // 徽章再排：避開角標的數字，狀態列只用 `m` 這一種顯示方式。角標和它分得開的位置才試；
  // 離不管角標時的徽章越遠的越先試（徽章要移的越少），每一小區只試一個（`regionOf`），最多 `TAG_RELAY_TRIES` 個
  const circles = free.lays.map((l, i) => badgeShapes(reqs[i]!.kind, l.at, l.sc, reqs[i]!.digits, l.corner).circle);
  const room = (p: HeightMarkPos) => Math.min(Infinity, ...circles.map((c) => boxDistance(c, geom.digit(p)) - c.r));
  const byRoom = positions.map((p, i) => ({ p, i, d: room(p) })).sort((x, y) => y.d - x.d || x.i - y.i);
  // `loose`：還有看不到的東西時，兩個數字只要不碰到（`FIRM_STEPS` 的 touch，HP 條照樣不放寬），角標和狀態列只要不互相蓋到
  const relay = (m: RowMode, loose = false, limit = TAG_RELAY_TRIES) => {
    const v = variants[m];
    const tries: HeightMarkPos[] = [];
    const regions = new Set<string>();
    for (const { p } of byRoom) {
      if (tries.length >= limit) break;
      if (hasRow && (loose ? tagRowLevel(geom, p, v, s) > 2 : tagRowLevel(geom, p, v, s) > 1 || tagRowNumsClash(geom, p, v, s))) continue;
      const key = regionOf(geom.digit(p));
      if (regions.has(key)) continue;
      regions.add(key);
      tries.push(p);
    }
    for (const p of tries) {
      const r = env.layoutAround(p, hasRow ? { [m]: v } : variants, loose ? FIRM_HP_FIRST - 1 : FIRM_SEP_LAST);
      const next = score(r.mode, r.lays, p);
      if (tagBetter(next, best)) best = next;
      if (loose ? best!.hidden === 0 : tagOk(best!)) return;
    }
  };
  // ① 徽章不動，狀態列照不管角標時的排法；② 徽章再排（狀態列不換）；③ 狀態列換別的顯示方式（徽章不動）；④ 換顯示方式＋徽章再排。
  // 狀態列是戰鬥資訊（美術 PM 不選 (a)）：能不換就不換
  fixed(0);
  if (!tagOk(best!) && reqs.length > 0) relay(free.mode);
  for (let rank = 1; rank < modes.length && !tagOk(best!); rank++) fixed(rank);
  for (let rank = 1; rank < modes.length && !tagOk(best!) && reqs.length > 0; rank++) relay(modes[rank]!, false, TAG_RELAY_TRIES_OTHER);
  // ⑤ 還有看不到的（徽章蓋到角標的數字或「+N」）：兩個數字只要不碰到也好（6F-15 的規則）
  // （很慢：只試狀態列照原樣的那一種）
  if (best!.hidden > 0 && reqs.length > 0) relay(free.mode, true, TAG_LOOSE_TRIES);
  return best!;
}
