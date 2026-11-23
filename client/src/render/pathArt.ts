// 選移動、選技能時的格子與路徑畫法（Phase 6A-4c，`docs/archive/art/戰鬥D版樣張.md` 第 3、5 節）：
// - 格子淡色圓角浮出，範圍外緣加亮線（`drawSoftCells`）；
// - 路徑沿格子走（直線段＋圓角）、每格中心一個點，分段變色（白、藍虛線、紅、灰虛線；`drawPathLine`）；
// - 經過的特殊格加地表色外框、原終點畫虛線框＋淡影、實際停點的紅色驚嘆號（`drawPathMarks`）；
// - 結果小牌（圖示＋一兩個詞；`pathTagNode`）。
// 只負責畫：要畫什麼由 `battle/pathPreview.ts` 依伺服器的路徑預覽決定。畫筆用介面（`Pen`），測試可以換成紀錄器。
import { Container, Graphics, Text } from "pixi.js";
import type { Pos } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import { dashRuns, outerEdges, roundedPieces, type Pt } from "../battle/pathGeometry";
import {
  FRAME_COLORS,
  PATH_COLORS,
  TAG_COLORS,
  TRAIL_COLORS,
  TRAIL_DEFAULT_COLOR,
  type PathDraw,
  type PathTag,
  type TagIcon,
} from "../battle/pathPreview";
import type { FloatBounds } from "./floatStack";
import { label } from "./labels";
import { minMarkScale } from "./minMark";

const T = TILE_SIZE;

export interface StrokeStyle {
  width: number;
  color: number;
  alpha?: number;
  cap?: "round" | "butt" | "square";
  join?: "round" | "miter" | "bevel";
}

/** 用到的 Pixi `Graphics` 方法（測試換成紀錄器）。 */
export interface Pen {
  moveTo(x: number, y: number): unknown;
  lineTo(x: number, y: number): unknown;
  roundRect(x: number, y: number, w: number, h: number, r: number): unknown;
  circle(x: number, y: number, r: number): unknown;
  closePath(): unknown;
  fill(style: { color: number; alpha?: number }): unknown;
  stroke(style: StrokeStyle): unknown;
}

/** 格子頂面左上角、中心（已含高度抬升）。 */
export interface TileGeo {
  origin(p: Pos): Pt;
  center(p: Pos): Pt;
}

export interface SoftStyle {
  fill: number;
  fillAlpha: number;
  line: number;
  lineAlpha: number;
  /** 外緣亮線（`null` ＝ 不畫）。 */
  edge: number | null;
  edgeAlpha?: number;
}

/** 可走格：白描邊＋藍填色（填色比水亮、偏青，疊在水上也分得出來）。 */
export const MOVE_SOFT: SoftStyle = { fill: 0x5aa8ff, fillAlpha: 0.34, line: 0xffffff, lineAlpha: 0.75, edge: 0xc8e4ff, edgeAlpha: 0.95 };
/** 施放範圍：極淡的暖色，外緣亮線較淡。 */
export const RANGE_SOFT: SoftStyle = { fill: 0xffe6a0, fillAlpha: 0.08, line: 0xffe6a0, lineAlpha: 0.2, edge: 0xffe6a0, edgeAlpha: 0.55 };
/** 預覽的命中範圍：橘色，外緣亮線。 */
export const HIT_SOFT: SoftStyle = { fill: 0xff7a3c, fillAlpha: 0.32, line: 0xffc896, lineAlpha: 0.6, edge: 0xff8c46, edgeAlpha: 0.95 };

/** 一格四邊的內縮（PR-2d，`practiceRange.poolInsets`：測試模式貼水池的格子讓出石條）；`null`＝不縮。 */
export type InsetOf = (p: Pos) => { n: number; s: number; w: number; e: number } | null;

const NO_INSET = { n: 0, s: 0, w: 0, e: 0 } as const;

/**
 * 淡淡浮出的格子：每格內縮的圓角方塊，群的外緣加一條較亮的線。
 * `insetOf`（PR-2d，只有測試模式會給）：該格四邊再各縮多少；省略時和改前逐筆相同。
 */
export function drawSoftCells(g: Pen, cells: readonly Pos[], geo: TileGeo, s: SoftStyle, insetOf?: InsetOf): void {
  if (cells.length === 0) return;
  for (const p of cells) {
    const o = geo.origin(p);
    const i = insetOf?.(p) ?? NO_INSET;
    g.roundRect(o.x + 3 + i.w, o.y + 3 + i.n, T - 6 - i.w - i.e, T - 6 - i.n - i.s, 8);
    g.fill({ color: s.fill, alpha: s.fillAlpha });
    g.stroke({ width: 1.2, color: s.line, alpha: s.lineAlpha });
  }
  if (s.edge === null) return;
  for (const e of outerEdges(cells)) {
    const o = geo.origin(e);
    const [x1, y1, x2, y2] = edgeLine(o, e.side, insetOf?.(e) ?? NO_INSET);
    g.moveTo(x1, y1);
    g.lineTo(x2, y2);
  }
  g.stroke({ width: 2.5, color: s.edge, alpha: s.edgeAlpha ?? 0.9, cap: "round" });
}

function edgeLine(o: Pt, side: "n" | "s" | "w" | "e", i: { n: number; s: number; w: number; e: number } = NO_INSET): [number, number, number, number] {
  const lo = 2;
  const hi = T - 2;
  switch (side) {
    case "n":
      return [o.x + lo + i.w, o.y + lo + i.n, o.x + hi - i.e, o.y + lo + i.n];
    case "s":
      return [o.x + lo + i.w, o.y + hi - i.s, o.x + hi - i.e, o.y + hi - i.s];
    case "w":
      return [o.x + lo + i.w, o.y + lo + i.n, o.x + lo + i.w, o.y + hi - i.s];
    case "e":
      return [o.x + hi - i.e, o.y + lo + i.n, o.x + hi - i.e, o.y + hi - i.s];
  }
}

/** 選範圍技能時極淡的格線（只畫地圖內的格子）。 */
export function drawFaintGrid(g: Pen, cells: readonly Pos[], geo: TileGeo): void {
  for (const p of cells) {
    const o = geo.origin(p);
    g.roundRect(o.x + 1, o.y + 1, T - 2, T - 2, 6);
  }
  if (cells.length > 0) g.stroke({ width: 1, color: 0xffffff, alpha: 0.07 });
}

function polyline(g: Pen, pts: readonly Pt[]): void {
  const first = pts[0];
  if (first === undefined) return;
  g.moveTo(first.x, first.y);
  for (let i = 1; i < pts.length; i++) {
    const p = pts[i] as Pt;
    g.lineTo(p.x, p.y);
  }
}

/** 路徑的轉角圓角半徑。 */
export const PATH_CORNER = 12;
export const PATH_DASH: readonly [number, number] = [7, 5];

/** 路徑線：先畫一條黑色底線讓線在任何地表上都看得清楚，再依段的種類上色（冰、到不了用虛線）；每格中心一個點。 */
export function drawPathLine(g: Pen, draw: PathDraw, geo: TileGeo): void {
  const segs = draw.segments;
  if (segs.length === 0) return;
  const first = segs[0] as (typeof segs)[number];
  const pts = [geo.center(first.from), ...segs.map((s) => geo.center(s.to))];
  const pieces = roundedPieces(pts, PATH_CORNER);
  const round = { cap: "round", join: "round" } as const;
  for (const piece of pieces) polyline(g, piece);
  g.stroke({ width: 7, color: 0x000000, alpha: 0.45, ...round });
  segs.forEach((seg, i) => {
    const piece = pieces[i] ?? [];
    const alpha = seg.possible ? 0.6 : 1;
    if (seg.dashed) {
      for (const run of dashRuns(piece, PATH_DASH[0], PATH_DASH[1])) polyline(g, run);
    } else polyline(g, piece);
    g.stroke({ width: 4, color: PATH_COLORS[seg.kind], alpha, ...round });
  });
  for (const d of draw.dots) {
    const c = geo.center(d.pos);
    g.circle(c.x, c.y, 5.5);
    g.fill({ color: 0x000000, alpha: 0.5 });
    g.circle(c.x, c.y, 3.8);
    g.fill({ color: PATH_COLORS[d.kind] });
  }
}

/** 圓角方塊外框的點（畫虛線框用）。 */
export function roundRectPoints(x: number, y: number, w: number, h: number, r: number): Pt[] {
  const pts: Pt[] = [];
  const arc = (cx: number, cy: number, from: number) => {
    for (let k = 0; k <= 4; k++) {
      const a = from + (k / 4) * (Math.PI / 2);
      pts.push({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r });
    }
  };
  arc(x + w - r, y + r, -Math.PI / 2);
  arc(x + w - r, y + h - r, 0);
  arc(x + r, y + h - r, Math.PI / 2);
  arc(x + r, y + r, Math.PI);
  pts.push({ ...(pts[0] as Pt) });
  return pts;
}

/** 特殊格外框、到不了的終點（虛線框＋淡影）、實際停點的紅色驚嘆號泡泡。 */
export function drawPathMarks(g: Pen, draw: PathDraw, geo: TileGeo): void {
  for (const f of draw.frames) {
    const o = geo.origin(f.pos);
    g.roundRect(o.x + 3, o.y + 3, T - 6, T - 6, 8);
    g.fill({ color: FRAME_COLORS[f.kind], alpha: 0.15 });
    g.stroke({ width: 2.5, color: FRAME_COLORS[f.kind], alpha: 0.95 });
  }
  if (draw.missEnd !== null) {
    const o = geo.origin(draw.missEnd);
    g.roundRect(o.x + 5, o.y + 5, T - 10, T - 10, 9);
    g.fill({ color: 0xffffff, alpha: 0.12 });
    for (const run of dashRuns(roundRectPoints(o.x + 5, o.y + 5, T - 10, T - 10, 9), 5, 4)) polyline(g, run);
    g.stroke({ width: 2, color: 0xffffff, alpha: 0.75 });
  }
  for (const c of draw.trail) drawTrailCell(g, geo.origin(c.pos), c.surface);
  for (const p of draw.bangs) drawBang(g, geo.center(p));
  for (const s of draw.slipStops) drawSlipStop(g, geo.center(s.pos));
}

/** E3b（美術 E3 驗收小修 2）：路徑線經過的格子（每段的兩端，不重複）：這些格子的高度標記「▲N」要畫在線上面。 */
export function pathLineCells(draw: Pick<PathDraw, "segments">): Pos[] {
  const seen = new Set<string>();
  const out: Pos[] = [];
  for (const s of draw.segments) {
    for (const p of [s.from, s.to]) {
      const key = `${p.x},${p.y}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(p);
    }
  }
  return out;
}

/** E3b：沿路留表面的格子框線（框內縮、短虛線、不填色）：和地圖上已有的冰（實線外框＋淡填色）分得開。 */
export const TRAIL_INSET = 8;

/** E3b：這次會留下表面的一格（霜行）：內縮的虛線圓角框，顏色依表面；不畫成冰的樣子（美術 E3 驗收待決第 5 點）。 */
function drawTrailCell(g: Pen, o: Pt, surface: string): void {
  const i = TRAIL_INSET;
  for (const run of dashRuns(roundRectPoints(o.x + i, o.y + i, T - 2 * i, T - 2 * i, 6), 4, 3)) polyline(g, run);
  g.stroke({ width: 2, color: TRAIL_COLORS[surface] ?? TRAIL_DEFAULT_COLOR, alpha: 0.95 });
}

const SLIP_STOP_R = 9;

/** 冰面滑倒的停點 ◆（#123，6E-2）：格子中心的藍色菱形（白邊）。 */
function drawSlipStop(g: Pen, c: Pt): void {
  const r = SLIP_STOP_R;
  g.moveTo(c.x, c.y - r);
  g.lineTo(c.x + r, c.y);
  g.lineTo(c.x, c.y + r);
  g.lineTo(c.x - r, c.y);
  g.closePath();
  g.fill({ color: 0x1e78d0, alpha: 0.95 });
  g.stroke({ width: 2, color: 0xffffff, alpha: 0.95 });
}

const BANG_R = 10;

/** 驚嘆號泡泡的中心（格子中心上方）。 */
export function bangCenter(c: Pt): Pt {
  return { x: c.x, y: c.y - T * 0.62 };
}

/** 紅色驚嘆號泡泡（格子上方）。 */
function drawBang(g: Pen, c: Pt): void {
  const { x, y } = bangCenter(c);
  g.moveTo(x - 4, y + 8);
  g.lineTo(x, y + 15);
  g.lineTo(x + 4, y + 8);
  g.closePath();
  g.fill({ color: 0xe0302a });
  g.circle(x, y, BANG_R);
  g.fill({ color: 0xe0302a });
  g.stroke({ width: 2, color: 0x1c1712 });
  g.roundRect(x - 1.6, y - 6, 3.2, 8, 1.6);
  g.fill({ color: 0xffffff });
  g.circle(x, y + 5, 1.8);
  g.fill({ color: 0xffffff });
}

/** 小牌的圖示（中心 x、y）。 */
function drawTagIcon(g: Pen, icon: TagIcon, x: number, y: number): void {
  const out = { width: 1.4, color: 0x1c1712 };
  switch (icon) {
    case "ice":
      g.moveTo(x, y - 7);
      g.lineTo(x + 6, y);
      g.lineTo(x, y + 7);
      g.lineTo(x - 6, y);
      g.closePath();
      g.fill({ color: 0xcdeeff });
      g.stroke(out);
      return;
    case "trap":
      g.circle(x, y, 6);
      g.stroke({ width: 2.4, color: 0x9aa0a8 });
      g.circle(x, y, 2);
      g.fill({ color: 0xc8ccd0 });
      return;
    case "fire":
      g.moveTo(x, y - 8);
      g.lineTo(x + 5, y + 1);
      g.lineTo(x + 3, y + 6);
      g.lineTo(x - 3, y + 6);
      g.lineTo(x - 5, y + 1);
      g.closePath();
      g.fill({ color: 0xff8a3a });
      g.stroke(out);
      return;
    case "water":
      g.moveTo(x, y - 7);
      g.lineTo(x + 5, y + 1);
      g.lineTo(x, y + 6);
      g.lineTo(x - 5, y + 1);
      g.closePath();
      g.fill({ color: 0x6ab8ff });
      g.stroke(out);
      return;
    case "hit":
      g.moveTo(x - 5, y + 5);
      g.lineTo(x + 5, y - 5);
      g.stroke({ width: 3, color: 0xf2f4f8, cap: "round" });
      return;
    case "status":
      g.circle(x, y, 5);
      g.fill({ color: TAG_COLORS.status });
      g.stroke(out);
      return;
  }
}

export const TAG_HEIGHT = 22;
/** 小牌字級（世界座標；1600 寬地圖 1.308 時畫面約 16 px）。 */
export const PATH_TAG_FONT = 12;
/**
 * AR-X10（美術 PM `docs/art/AR-X10驗收.md`）：小牌字在畫面上至少幾 px（同狀態圖示、預告字的「畫面字 ≥10 px」）。
 * 800 寬地圖縮到 0.62 時字原本只剩約 7 px；小牌整張（底、圖示、字）反向放大，變寬蓋到旁邊的格子可以接受。
 */
export const MIN_PATH_TAG_FONT_PX = 10;

/** 這個地圖縮放下小牌的倍率：畫面字 ≥ `MIN_PATH_TAG_FONT_PX`；地圖夠大時 1。不設上限。 */
export function pathTagScale(boardScale: number): number {
  return minMarkScale(PATH_TAG_FONT, MIN_PATH_TAG_FONT_PX, boardScale);
}

/** 小牌字在畫面上的 px（字級 × 地圖縮放 × 倍率）。 */
export function pathTagFontPx(boardScale: number): number {
  return PATH_TAG_FONT * boardScale * pathTagScale(boardScale);
}

/** 小牌節點照倍率放大（AR-X10）；`res`（裝置像素比 × 地圖縮放 × 倍率）給時字的解析度跟著提高，放大後不糊。 */
export function scaleTagNode(node: Container, k: number, res?: number): void {
  node.scale.set(k);
  if (res === undefined) return;
  for (const c of node.children) if (c instanceof Text) c.resolution = Math.max(1, res);
}

/** CR-1b（美術 E3b 驗收小修 1）：一個單位在畫面上佔的範圍（世界座標）：格子頂面往上多算半格的頭，左右各縮一點。 */
export function unitBox(o: Pt): { x: number; y: number; w: number; h: number } {
  return { x: o.x + 4, y: o.y - T * 0.45, w: T - 8, h: T * 1.45 - 4 };
}

type Box = { x: number; y: number; w: number; h: number };

function overlapArea(a: Box, b: Box): number {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}

/**
 * CR-1c（美術 CR-1b 驗收小修 2）：置中放的小牌（左上角 `p`、寬 `w`、高 `h`）像浮動卡一樣往內推，整塊留在地圖可見範圍
 * `bounds`（世界座標）內；比範圍還寬（高）時貼左（上）緣。沒給範圍時照原位。
 */
export function pushInside(p: Pt, w: number, h: number, bounds?: FloatBounds): Pt {
  if (bounds === undefined) return p;
  const x = Math.max(bounds.left, Math.min(p.x, bounds.right - w));
  const y = Math.max(bounds.top, Math.min(p.y, bounds.bottom - h));
  return { x, y };
}

/** 小牌整塊在範圍內（沒給範圍時一律算在內）。 */
function fits(p: Pt, w: number, h: number, bounds?: FloatBounds): boolean {
  if (bounds === undefined) return true;
  return p.x >= bounds.left && p.x + w <= bounds.right && p.y >= bounds.top && p.y + h <= bounds.bottom;
}

/**
 * 各張小牌放在哪裡（世界座標的左上角），依序擺、不互相疊：依序試格子的右上、右下、左上、左下；
 * 都疊到時放右上再往上疊。`o` 是格子頂面的左上角，`w` 是小牌寬度，`h` 是小牌高度（AR-X10：放大後的高度）。
 *
 * CR-1b（美術 E3b 驗收小修 1、佇列 (w)）：`units` 是有單位的格子（頂面左上角）；有給時把它們當成不能放的區域
 * （`unitBox`，含頭部），停點右邊會蓋到單位時依序改擺上方、左邊、下方；都會蓋到時選蓋到最少的那一邊。
 * 沒給 `units` 時和改前一樣。
 *
 * CR-1c（美術 CR-1b 驗收小修 2）：`bounds` 是地圖可見範圍（世界座標）；上方、下方這兩個水平置中的位置先往內推
 * （`pushInside`）再判斷會不會蓋到東西。左右兩邊的位置不推（推進來會蓋到停點），出界時不選；全部的位置都出界時
 * 照舊從全部的位置挑。
 */
export function placeTags(
  items: ReadonlyArray<{ o: Pt; w: number }>,
  avoid: readonly Pt[] = [],
  h: number = TAG_HEIGHT,
  units: readonly Pt[] = [],
  bounds?: FloatBounds,
): Pt[] {
  // `avoid`：驚嘆號泡泡的中心（不讓小牌蓋住）
  const placed: Box[] = avoid.map((c) => ({
    x: c.x - BANG_R,
    y: c.y - BANG_R,
    w: BANG_R * 2,
    h: BANG_R * 2 + 6,
  }));
  const bodies = units.map(unitBox);
  const hits = (x: number, y: number, w: number) =>
    placed.some((r) => x < r.x + r.w + 2 && x + w + 2 > r.x && y < r.y + r.h + 2 && y + h + 2 > r.y);
  const covered = (x: number, y: number, w: number) => bodies.reduce((sum, b) => sum + overlapArea({ x, y, w, h }, b), 0);
  return items.map(({ o, w }) => {
    const above = o.y - h + 4;
    const below = o.y + T - 4;
    const right = o.x + T * 0.5;
    const left = o.x + T * 0.5 - w;
    const mid = o.x + T * 0.5 - w / 2;
    const tries: Pt[] =
      bodies.length === 0
        ? [
            { x: right, y: above },
            { x: right, y: below },
            { x: left, y: above },
            { x: left, y: below },
          ]
        : [
            { x: right, y: above }, // 停點右邊（原本的位置）
            pushInside({ x: mid, y: o.y - T * 0.45 - h }, w, h, bounds), // 上方（停點那一格的頭上；CR-1c 往內推）
            { x: left, y: above }, // 左邊
            pushInside({ x: mid, y: below }, w, h, bounds), // 下方（CR-1c 往內推）
          ];
    // CR-1c：有給範圍時，出界的位置（左右兩邊）不選；全都出界時照舊從全部的位置挑
    const inside = tries.filter((p) => fits(p, w, h, bounds));
    const free = (inside.length > 0 ? inside : tries).filter((p) => !hits(p.x, p.y, w));
    let at = free.find((p) => covered(p.x, p.y, w) === 0);
    if (at === undefined && free.length > 0 && bodies.length > 0) {
      at = free.reduce((best, p) => (covered(p.x, p.y, w) < covered(best.x, best.y, w) ? p : best));
    }
    if (at === undefined) {
      let y = above;
      while (hits(right, y, w)) y -= h + 2;
      at = { x: right, y };
    }
    placed.push({ x: at.x, y: at.y, w, h });
    return at;
  });
}

/** 一張結果小牌：深色圓角底、地表色邊、圖示、文字（`at` 之後再設）。 */
export function pathTagNode(tag: PathTag, at: Pt = { x: 0, y: 0 }): Container {
  const node = new Container();
  const text = label(tag.text, PATH_TAG_FONT, 0xffffff, true);
  const w = Math.ceil(text.width) + 32;
  const bg = new Graphics();
  bg.roundRect(0, 0, w, TAG_HEIGHT, TAG_HEIGHT / 2).fill({ color: 0x181410, alpha: 0.9 }).stroke({ width: 2, color: TAG_COLORS[tag.icon] });
  drawTagIcon(bg, tag.icon, 12, TAG_HEIGHT / 2);
  text.anchor.set(0, 0.5);
  text.position.set(24, TAG_HEIGHT / 2 + 0.5);
  node.addChild(bg, text);
  node.position.set(at.x, at.y);
  return node;
}

/** 「到不了」的小牌（終點下方）；`k` 是放大倍率（AR-X10，同結果小牌），置中照放大後的寬度算。 */
export function missTagNode(o: Pt, k = 1, res?: number): Container {
  const node = new Container();
  const text = label("到不了", PATH_TAG_FONT, 0xffffff, true);
  const w = Math.ceil(text.width) + 16;
  const bg = new Graphics().roundRect(0, 0, w, TAG_HEIGHT, TAG_HEIGHT / 2).fill({ color: 0x181410, alpha: 0.9 }).stroke({ width: 2, color: 0xc8c8c8 });
  text.anchor.set(0.5, 0.5);
  text.position.set(w / 2, TAG_HEIGHT / 2 + 0.5);
  node.addChild(bg, text);
  scaleTagNode(node, k, res);
  placeMissTag(node, o, w * k);
  return node;
}

/** 「到不了」小牌的位置：終點格下緣、水平置中（`w` 是放大後的寬度）。 */
export function placeMissTag(node: Container, o: Pt, w: number): void {
  node.position.set(o.x + (T - w) / 2, o.y + T - 6);
}
