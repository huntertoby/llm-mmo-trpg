// 地表併塊（Phase 6A-4a；docs/art/戰鬥D版樣張.md 第 2 節）：同種地表的相鄰格併成一塊圓角有機形狀。
// 每格仍各畫各的貼圖，但形狀由「四鄰與四個斜鄰是不是同種地表」決定：
// - 和同種鄰格相接的邊（接縫）一律貼齊格子邊界，補滿；
// - 露在外面的邊內縮 1.5～4.5 單位（≤ MAX_INSET），沿邊有一點起伏；起伏只看格子座標雜湊（artRandom），結果固定；
// - 邊在格子頂點的內縮量只看「頂點座標＋邊的方向」，所以相鄰兩格的外緣在接縫處接得起來；
// - 兩邊都露在外面的角畫成圓角（凸角）；兩邊都是接縫但斜鄰不是同種的角畫成內凹的小圓角。
// 所有點都在格子內（0～T），看起來的範圍＝實際判定的格子。純函式，不碰 Canvas（畫法在 `blobPath` 等小工具）。
import type { Ctx } from "./artDraw";
import { hash } from "./artRandom";
import type { Sides } from "./terrainArt";

/** 繪圖用的虛擬格邊長（同 terrainArt 的 ART_T）。 */
export const BLOB_T = 52;
/** 露在外面的邊最多內縮的單位（規格：≤ 5）。 */
export const MAX_INSET = 5;
const MIN_INSET = 1.5;
const INSET_SPAN = MAX_INSET - 0.5 - MIN_INSET;
/** 凸角半徑 10～14 單位。 */
const RADIUS_MIN = 10;
const RADIUS_SPAN = 4;
/** 一條邊的起伏控制點數（段數）與取樣數。 */
const KNOTS = 4;
const SIDE_STEPS = 12;
const CORNER_STEPS = 6;
/** 邊的方向（N、E、S、W）各自的雜湊鹽。 */
const SIDE_SALT = [301, 302, 303, 304] as const;
const KNOT_SALT = 320;
const RADIUS_SALT = 340;

/** 四個斜鄰是不是同種地表（西北、東北、東南、西南）。 */
export interface Corners {
  nw: boolean;
  ne: boolean;
  se: boolean;
  sw: boolean;
}

export const ALL_CORNERS: Corners = { nw: true, ne: true, se: true, sw: true };

export interface BlobPoint {
  x: number;
  y: number;
  /** 從這一點到下一點（最後一點接回第一點）是露在外面的外緣（要描邊）；否則是接縫。 */
  edge: boolean;
}

export interface BlobShape {
  /** 順時針的封閉多邊形（格子座標，0～T）。 */
  points: BlobPoint[];
  /** 整格填滿（四邊與四角都是同種地表）。 */
  full: boolean;
}

type Pt = readonly [number, number];

/** 邊與角的索引：邊 0＝N、1＝E、2＝S、3＝W；角 k 在邊 k−1 與邊 k 之間（0＝西北、1＝東北、2＝東南、3＝西南）。 */
const CORNER_OFFSET: readonly Pt[] = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

const insetOf = (h: number): number => MIN_INSET + ((h % 1000) / 1000) * INSET_SPAN;

/** 邊 `side` 在角 `corner` 那個頂點的內縮量：只看頂點的全域座標與邊的方向，相鄰格共用。 */
function vertexInset(x: number, y: number, corner: number, side: number): number {
  const [dx, dy] = CORNER_OFFSET[corner]!;
  return insetOf(hash(x + dx, y + dy, SIDE_SALT[side]!));
}

/** 邊 k 的內縮量曲線：t＝0 在角 k、t＝1 在角 k＋1；兩端只看頂點，中間看格子。餘弦內插，值域不超出控制點。 */
function sideProfile(x: number, y: number, side: number): (t: number) => number {
  const knots: number[] = [vertexInset(x, y, side, side)];
  for (let i = 1; i < KNOTS; i++) knots.push(insetOf(hash(x, y, KNOT_SALT + side * 8 + i)));
  knots.push(vertexInset(x, y, (side + 1) % 4, side));
  return (t: number) => {
    const s = Math.min(KNOTS - 1, Math.max(0, Math.floor(t * KNOTS)));
    const u = Math.min(1, Math.max(0, t * KNOTS - s));
    const w = (1 - Math.cos(u * Math.PI)) / 2;
    return knots[s]! * (1 - w) + knots[s + 1]! * w;
  };
}

function cornerRadius(x: number, y: number, corner: number): number {
  const [dx, dy] = CORNER_OFFSET[corner]!;
  return RADIUS_MIN + ((hash(x + dx, y + dy, RADIUS_SALT) % 1000) / 1000) * RADIUS_SPAN;
}

/** 以西北角為準的座標轉到角 k（順時針轉 k 次 90°）。 */
function rot(p: Pt, k: number, T: number): Pt {
  let [px, py] = p;
  for (let i = 0; i < k; i++) [px, py] = [T - py, px];
  return [px, py];
}

function quad(a: Pt, c: Pt, b: Pt, steps: number): Pt[] {
  const out: Pt[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const u = 1 - t;
    out.push([u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]]);
  }
  return out;
}

interface Ctx4 {
  x: number;
  y: number;
  T: number;
  exposed: readonly boolean[];
  diag: readonly boolean[];
  profile: ReadonlyArray<((t: number) => number) | null>;
  radius: readonly number[];
}

const convexAt = (c: Ctx4, k: number): boolean => c.exposed[(k + 3) % 4]! && c.exposed[k]!;

/** 角 k 的點（以西北角為準算，再轉過去）。 */
function cornerPoints(c: Ctx4, k: number): BlobPoint[] {
  const prev = (k + 3) % 4;
  const pp = c.profile[prev];
  const cp = c.profile[k];
  const T = c.T;
  let local: { p: Pt; edge: boolean }[];
  if (pp && cp) {
    const R = c.radius[k]!;
    const a = pp(1 - R / T);
    const b = cp(R / T);
    local = quad([a, R], [a, b], [R, b], CORNER_STEPS).map((p) => ({ p, edge: true }));
  } else if (cp) {
    local = [{ p: [0, cp(0)], edge: true }];
  } else if (pp) {
    local = [{ p: [pp(1), 0], edge: false }];
  } else if (c.diag[k]) {
    local = [{ p: [0, 0], edge: false }];
  } else {
    // 內凹角：西鄰（以本角為準）的北邊在 y＝ih 接進來，北鄰的西邊在 x＝iv 接出去
    const ih = vertexInset(c.x, c.y, k, k);
    const iv = vertexInset(c.x, c.y, k, prev);
    const pts = quad([0, ih], [iv, ih], [iv, 0], CORNER_STEPS);
    local = pts.map((p, i) => ({ p, edge: i < pts.length - 1 }));
  }
  return local.map(({ p, edge }) => {
    const [px, py] = rot(p, k, T);
    return { x: px, y: py, edge };
  });
}

/** 邊 k 中間的取樣點（不含兩端，兩端由角給）。 */
function sidePoints(c: Ctx4, k: number): BlobPoint[] {
  const prof = c.profile[k];
  if (!prof) return [];
  const T = c.T;
  const t0 = convexAt(c, k) ? c.radius[k]! / T : 0;
  const t1 = convexAt(c, (k + 1) % 4) ? 1 - c.radius[(k + 1) % 4]! / T : 1;
  const out: BlobPoint[] = [];
  for (let i = 1; i < SIDE_STEPS; i++) {
    const t = t0 + ((t1 - t0) * i) / SIDE_STEPS;
    const [px, py] = rot([t * T, prof(t)], k, T);
    out.push({ x: px, y: py, edge: true });
  }
  return out;
}

/**
 * 一格地表的形狀。`same`：四鄰是不是同種地表；`diag`：四個斜鄰是不是同種（只影響兩邊都是接縫的角）。
 * `x`、`y` 是格子座標（雜湊用），`T` 是格子邊長（預設 52 單位）。
 */
export function blobShape(x: number, y: number, same: Sides, diag: Corners = ALL_CORNERS, T = BLOB_T): BlobShape {
  const exposed = [!same.n, !same.e, !same.s, !same.w];
  const d = [diag.nw, diag.ne, diag.se, diag.sw];
  const c: Ctx4 = {
    x,
    y,
    T,
    exposed,
    diag: d,
    profile: exposed.map((e, k) => (e ? sideProfile(x, y, k) : null)),
    radius: [0, 1, 2, 3].map((k) => cornerRadius(x, y, k)),
  };
  const points: BlobPoint[] = [];
  for (let k = 0; k < 4; k++) points.push(...cornerPoints(c, k), ...sidePoints(c, k));
  const full = exposed.every((e) => !e) && d.every(Boolean);
  return { points, full };
}

/** 把形狀加進目前的路徑（呼叫端自己 `beginPath`／`fill`／`clip`）。 */
export function blobPath(ctx: Ctx, shape: BlobShape): void {
  const pts = shape.points;
  if (pts.length === 0) return;
  ctx.moveTo(pts[0]!.x, pts[0]!.y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i]!.x, pts[i]!.y);
  ctx.closePath();
}

/** 外緣的折線（只含露在外面的段，接縫不畫）；每條是一串連續的點。 */
export function blobEdges(shape: BlobShape): { x: number; y: number }[][] {
  const pts = shape.points;
  const n = pts.length;
  const start = pts.findIndex((p, i) => !p.edge && pts[(i + 1) % n]!.edge);
  if (start < 0) return pts.some((p) => p.edge) ? [[...pts, pts[0]!].map(({ x, y }) => ({ x, y }))] : [];
  const runs: { x: number; y: number }[][] = [];
  let run: { x: number; y: number }[] = [];
  for (let j = 1; j <= n; j++) {
    const i = (start + j) % n;
    const p = pts[i]!;
    if (run.length === 0) run.push({ x: p.x, y: p.y });
    if (p.edge) {
      const q = pts[(i + 1) % n]!;
      run.push({ x: q.x, y: q.y });
    } else {
      if (run.length > 1) runs.push(run);
      run = [];
    }
  }
  if (run.length > 1) runs.push(run);
  return runs;
}

/** 只描露在外面的外緣（筆觸樣式由呼叫端先設好）。 */
export function strokeBlobEdges(ctx: Ctx, shape: BlobShape): void {
  const runs = blobEdges(shape);
  if (runs.length === 0) return;
  ctx.beginPath();
  for (const run of runs) {
    ctx.moveTo(run[0]!.x, run[0]!.y);
    for (let i = 1; i < run.length; i++) ctx.lineTo(run[i]!.x, run[i]!.y);
  }
  ctx.stroke();
}
