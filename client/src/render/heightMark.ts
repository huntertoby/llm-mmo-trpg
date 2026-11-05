// 高度標記「▲N」的位置（純函式；6F-14，美術 PM 6F-13 檢查「下一段要修」第 3、5 點）。
//
// - 標記畫在同一排的單位之上（6F-10）。有人站時，標記可以蓋到頭髮或肩膀，但不能蓋到臉和眼睛（補充 6F-10 的決定）：
//   會蓋到臉時，整個標記往格子下緣移，移到臉的下面（`heightMarkDrop`）。不縮小：800 寬時數字已經是下限 10px。
// - 炸彈、蓄力、灌注徽章畫在標記之上（6F-13），可以蓋到「▲」，但數字一定要看得到：徽章把數字的方框當成要避開的形狀
//   （`heightMarkBoxes(...).num`，`badgeLayout` 的 `firmBoxes`）。
//
// 座標：世界座標、相對格子中心（往下為正）；標記節點的原點在格子左上角，整個節點放大 `k` 倍（`minMark.ts`）。

import { TILE_SIZE } from "../battle/geometry";
import type { Facing } from "../api/types";
import { MIN_HEIGHT_BADGE_FONT_PX, minMarkScale } from "./minMark";
import type { Box } from "./rowLayout";

const T = TILE_SIZE;

/** 高度標記的數字字級（世界座標；`BattleRenderer.HEIGHT_BADGE_FONT` 同值）。 */
export const HEIGHT_MARK_FONT = 10;
/** 標記的底（圓角方框）：節點本地座標，放大前。 */
export const HEIGHT_MARK_BG = { x: 3, y: 3, w: 19, h: 13, r: 4 } as const;
/**
 * 6F-17：角標的底：左右貼緊「▲」和數字（左右各留約 1.5），上下和標記一樣。800 寬時格子放不下原本的寬度
 * （狀態列靠左時右邊只剩 26.1，原本的底 26.5）。
 */
export const HEIGHT_TAG_BG = { x: 4.5, y: 3, w: 17, h: 13, r: 4 } as const;
/** 底的形狀（`HEIGHT_MARK_BG` 或 `HEIGHT_TAG_BG`）。 */
export type MarkBg = { readonly x: number; readonly y: number; readonly w: number; readonly h: number; readonly r: number };
/** 「▲」三角形的三個頂點（本地座標）。 */
export const HEIGHT_MARK_TRI = [6, 13, 9.5, 6, 13, 13] as const;
/** 數字的左上角（本地座標）。 */
export const HEIGHT_MARK_NUM = { x: 14, y: 4 } as const;
/** 數字筆畫的範圍（本地座標，含一點餘裕）：一位數約 6 寬，上下照字級 10 的筆畫（字框上方約 1、下方約 1.5 是空白）。 */
export const HEIGHT_MARK_DIGIT_W = 6.2;
export const HEIGHT_MARK_NUM_INK = { t: 5, b: 15 } as const;
/** 標記和臉之間至少留的空隙（世界座標）。 */
export const HEIGHT_MARK_FACE_GAP = 1;

/** 標記的倍率（數字在畫面上至少 `MIN_HEIGHT_BADGE_FONT_PX`；和 `registerMark` 的基準相同）。 */
export function heightMarkScale(boardScale: number): number {
  return minMarkScale(HEIGHT_MARK_FONT, MIN_HEIGHT_BADGE_FONT_PX, boardScale);
}

/**
 * 6F-17（美術 PM 6F-16 檢查第 2 節選 (b)）：格子上有人站時，「▲N」縮成角標，數字在畫面上剛好 `HEIGHT_TAG_FONT_PX`
 * （各種寬度一樣大；比照 6F-11 角標「+N」的下限 9px）。形狀和沒人站時一樣（底、「▲」、數字），只是整個縮小。
 */
export const HEIGHT_TAG_FONT_PX = 9;
export function heightTagScale(boardScale: number): number {
  if (!(boardScale > 0)) return 1;
  return HEIGHT_TAG_FONT_PX / (HEIGHT_MARK_FONT * boardScale);
}

/**
 * 臉和眼睛的範圍（紙娃娃虛擬單位，腳底 ＝ 0、往上為負；頭頂 −53）：從瀏海下緣（−45）到下巴（−33.4），
 * 正面、背面左右 ±7（眼睛在 ±3.2、−41）；側面往朝向那一邊偏（眼睛 4.4、鼻尖 9.6，後腦、耳朵在 −2.6 以內是頭髮）。
 * 背面看不到臉，但照正面一樣避開（保守）。
 */
export const FACE_DOLL = { top: -45, chin: -33.4, front: [-7, 7], side: [-2.6, 9.8] } as const;
/** 紙娃娃頭頂離腳底（虛擬單位；`inkDoll.DOLL_HEAD_TOP`）。 */
const HEAD_TOP = 53;

/**
 * 一個單位臉的方框（相對格子中心的世界座標）：`top` 是單位圖畫出來的頂端（`unitSprite.unitTopY`），
 * `px` 是紙娃娃 1 虛擬單位的大小（`unitSprite.dollPx`，含精英、外觀大小）。
 */
export function faceBoxOf(facing: Facing, top: number, px: number): Box {
  const [l, r] = facing === "east" ? FACE_DOLL.side : facing === "west" ? [-FACE_DOLL.side[1], -FACE_DOLL.side[0]] : FACE_DOLL.front;
  return { l: l * px, r: r * px, t: top + (HEAD_TOP + FACE_DOLL.top) * px, b: top + (HEAD_TOP + FACE_DOLL.chin) * px };
}

/** 標記的底（圓角方框）放大 `k` 倍、往下 `dy`、往右 `dx`（6F-15）時的範圍（相對格子中心）。 */
export function heightMarkBox(k: number, dy = 0, dx = 0, b: MarkBg = HEIGHT_MARK_BG): Box {
  return { l: -T / 2 + k * b.x + dx, r: -T / 2 + k * (b.x + b.w) + dx, t: -T / 2 + k * b.y + dy, b: -T / 2 + k * (b.y + b.h) + dy };
}

/** 標記放大 `k` 倍、往下 `dy`、往右 `dx` 時的各部分（相對格子中心）：`box` 底、`tri`「▲」、`num` 數字的筆畫。 */
export function heightMarkBoxes(k: number, dy: number, digits: number, dx = 0, bg: MarkBg = HEIGHT_MARK_BG): { box: Box; tri: Box; num: Box } {
  const X = (x: number) => -T / 2 + k * x + dx;
  const Y = (y: number) => -T / 2 + k * y + dy;
  const p = HEIGHT_MARK_TRI;
  return {
    box: heightMarkBox(k, dy, dx, bg),
    tri: { l: X(p[0]), r: X(p[4]), t: Y(p[3]), b: Y(p[1]) },
    num: { l: X(HEIGHT_MARK_NUM.x), r: X(HEIGHT_MARK_NUM.x + HEIGHT_MARK_DIGIT_W * digits), t: Y(HEIGHT_MARK_NUM_INK.t), b: Y(HEIGHT_MARK_NUM_INK.b) },
  };
}

/** 6F-16：標記看得到的筆畫（「▲」和數字，一位數）的外接方框（相對格子中心）。 */
export function heightMarkInk(k: number, dy = 0, dx = 0, digits = 1): Box {
  const m = heightMarkBoxes(k, dy, digits, dx);
  return { l: Math.min(m.tri.l, m.num.l), r: Math.max(m.tri.r, m.num.r), t: Math.min(m.tri.t, m.num.t), b: Math.max(m.tri.b, m.num.b) };
}

/**
 * 有人站時標記往下移多少（世界座標，≥ 0）：標記的底和臉左右重疊時，移到臉的下面（`HEIGHT_MARK_FACE_GAP`）；
 * 最多移到格子下緣（標記下緣離格子下緣 1.5）。沒有人（`face` null）或不重疊時 0。
 */
/** HP 條的上緣（相對格子中心；`unitSprite.hpBar`，沒有護盾條時）。 */
export const HP_BAR_TOP = T * 0.36;
/** 標記移到下緣時，標記的底和 HP 條上緣之間的空隙（世界座標，6F-15）。 */
export const HEIGHT_MARK_HP_GAP = 1;

/**
 * 標記移到下緣時的往下移量（6F-14：徽章避不開「▲N」的數字時）。6F-15（美術 PM 6F-14 檢查第 2 節第 2 點：
 * 標記不能蓋到 HP 條）：標記的底放在 HP 條上方、圓盤的下緣（`hpTop` 是 HP 條上緣，有護盾條時是護盾條上緣）。
 */
export function heightMarkBottomDrop(k: number, hpTop: number = HP_BAR_TOP, bg: MarkBg = HEIGHT_MARK_BG): number {
  return Math.max(0, hpTop - HEIGHT_MARK_HP_GAP - heightMarkBox(k, 0, 0, bg).b);
}

/** 標記的位置（6F-15）：往下 `dy`、往右 `dx`（世界座標）。 */
export interface HeightMarkPos {
  dx: number;
  dy: number;
}

/** 標記移到下緣時左右平移的間距、和朝向三角形之間至少留的空隙（世界座標，6F-15）。 */
export const HEIGHT_MARK_SLIDE_STEP = 1;
export const HEIGHT_MARK_ARROW_GAP = 0.5;

const overlaps = (a: Box, b: Box, gap: number) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;

/**
 * 有人站、身上有炸彈、蓄力、灌注徽章時，標記依序試的位置（6F-15；純函式，確定性）：
 * ① 原位（只往下讓開臉，`heightMarkDrop`）；② 下緣（HP 條上方、圓盤的下緣，`heightMarkBottomDrop`）；
 * ③ 下緣、左右平移（離原位近的先，一樣近時先往右）：800 寬時徽章的圓、數字和標記的數字擠在格子左邊，平移一點就讓得開。
 * 下緣的位置（②③）不蓋到朝向三角形（`arrow`）、臉，整個標記在格子裡（離格子邊緣 1.5）；原位照 6F-14。
 */
export function heightMarkCandidates(k: number, face: Box | null, arrow: Box | null, hpTop: number = HP_BAR_TOP): HeightMarkPos[] {
  const first = heightMarkDrop(k, face);
  const bottom = heightMarkBottomDrop(k, hpTop);
  const out: HeightMarkPos[] = [{ dx: 0, dy: first }];
  if (bottom <= first + 0.5) return out;
  const m = heightMarkBox(k, bottom);
  const lim = T / 2 - 1.5;
  const ok = (dx: number) => {
    const b = { ...m, l: m.l + dx, r: m.r + dx };
    if (b.l < -lim - 1e-9 || b.r > lim + 1e-9) return false;
    if (arrow !== null && overlaps(b, arrow, HEIGHT_MARK_ARROW_GAP)) return false;
    return face === null || !overlaps(b, face, HEIGHT_MARK_FACE_GAP);
  };
  const n = Math.ceil(T / HEIGHT_MARK_SLIDE_STEP);
  for (let i = 0; i <= n; i++)
    for (const dx of i === 0 ? [0] : [i * HEIGHT_MARK_SLIDE_STEP, -i * HEIGHT_MARK_SLIDE_STEP]) if (ok(dx)) out.push({ dx, dy: bottom });
  return out;
}

/**
 * 6F-16：`heightMarkCandidates` 都不行時（徽章的數字和「▲N」的數字分不開，或「▲N」蓋到狀態列），標記再試的位置：
 * 往下 0～下緣（HP 條上方）、左右平移，間距 `HEIGHT_MARK_SLIDE_STEP`；離原位（`heightMarkDrop`）近的先，一樣近時先上後下、先右後左。
 * 和 ②③ 一樣：整個標記在格子裡（離格子邊緣 1.5），不蓋到臉、HP 條、朝東西的三角形（`arrow`）。照參數記下來（確定性）。
 */
const gridMemo = new Map<string, HeightMarkPos[]>();
/**
 * `inkOnly`（6F-16，最後才用）：只有「▲」和數字不碰朝東西的三角形，標記的半透明底可以蓋到三角形的一角
 * （800 寬朝東：徽章在左上、標記在右下，底的右緣會碰到三角形的尖端）。
 */
export function heightMarkGrid(k: number, face: Box | null, arrow: Box | null, hpTop: number = HP_BAR_TOP, inkOnly = false, bg: MarkBg = HEIGHT_MARK_BG): HeightMarkPos[] {
  const key = JSON.stringify([k, face, arrow, hpTop, inkOnly, bg]);
  const hit = gridMemo.get(key);
  if (hit !== undefined) return hit;
  const first = heightMarkDrop(k, face, bg);
  const bottom = heightMarkBottomDrop(k, hpTop, bg);
  const lim = T / 2 - 1.5;
  const m0 = heightMarkBox(k, 0, 0, bg);
  const out: Array<HeightMarkPos & { d: number }> = [];
  const st = HEIGHT_MARK_SLIDE_STEP;
  for (let dy = 0; dy <= bottom + 1e-9; dy += st)
    for (let dx = -T; dx <= T; dx += st) {
      const b = { l: m0.l + dx, r: m0.r + dx, t: m0.t + dy, b: m0.b + dy };
      if (b.l < -lim - 1e-9 || b.r > lim + 1e-9 || b.t < -lim - 1e-9) continue;
      if (arrow !== null && overlaps(inkOnly ? heightMarkInk(k, dy, dx) : b, arrow, HEIGHT_MARK_ARROW_GAP)) continue;
      if (face !== null && overlaps(b, face, HEIGHT_MARK_FACE_GAP)) continue;
      out.push({ dx, dy, d: dx * dx + (dy - first) ** 2 });
    }
  out.sort((a, b) => a.d - b.d || a.dy - b.dy || b.dx - a.dx);
  const res = out.map(({ dx, dy }) => ({ dx, dy }));
  gridMemo.set(key, res);
  return res;
}

export function heightMarkDrop(k: number, face: Box | null, bg: MarkBg = HEIGHT_MARK_BG): number {
  if (face === null) return 0;
  const m = heightMarkBox(k, 0, 0, bg);
  const g = HEIGHT_MARK_FACE_GAP;
  if (m.r + g <= face.l || m.l - g >= face.r) return 0;
  if (face.t >= m.b + g) return 0; // 臉整個在標記下面（不會發生，保守）
  const need = face.b + g - m.t;
  const room = T / 2 - 1.5 - m.b;
  return Math.max(0, Math.min(need, room));
}
