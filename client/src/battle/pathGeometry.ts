// 路徑的幾何（Phase 6A-4c）：沿格子中心的直線段，轉彎處用圓角接起來；虛線依弧長切段。純函式，畫法在 `render/pathArt.ts`。

export interface Pt {
  x: number;
  y: number;
}

/** 轉角圓弧的取樣點數。 */
const CORNER_SAMPLES = 6;

function towards(a: Pt, b: Pt, d: number): Pt {
  const len = Math.hypot(b.x - a.x, b.y - a.y);
  if (len === 0) return { x: a.x, y: a.y };
  const t = Math.min(1, d / len);
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function collinear(a: Pt, b: Pt, c: Pt): boolean {
  return Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) < 1e-6;
}

/** 二次貝茲曲線上 t 的點。 */
function quad(p0: Pt, c: Pt, p1: Pt, t: number): Pt {
  const u = 1 - t;
  return { x: u * u * p0.x + 2 * u * t * c.x + t * t * p1.x, y: u * u * p0.y + 2 * u * t * c.y + t * t * p1.y };
}

/**
 * 依序經過 `points` 的折線，每一段（第 i 段 ＝ points[i-1] → points[i]）各自的取樣點。
 * 轉角處用半徑 `radius` 的圓角（二次曲線，控制點在轉角）：前半段的弧屬於進來的段，後半段屬於出去的段，
 * 所以分段變色時顏色在轉角正中間換。直線經過的點不做圓角。回傳長度 ＝ points.length - 1。
 */
export function roundedPieces(points: readonly Pt[], radius: number): Pt[][] {
  const n = points.length;
  if (n < 2) return [];
  // 每個內部頂點的圓角：進入點、轉角、離開點（直線時為 null）
  const corners: Array<{ a: Pt; c: Pt; b: Pt } | null> = points.map((p, i) => {
    if (i === 0 || i === n - 1) return null;
    const prev = points[i - 1] as Pt;
    const next = points[i + 1] as Pt;
    if (collinear(prev, p, next)) return null;
    const r = Math.min(radius, Math.hypot(p.x - prev.x, p.y - prev.y) / 2, Math.hypot(next.x - p.x, next.y - p.y) / 2);
    return { a: towards(p, prev, r), c: p, b: towards(p, next, r) };
  });
  const pieces: Pt[][] = [];
  for (let i = 1; i < n; i++) {
    const start = corners[i - 1];
    const end = corners[i];
    const piece: Pt[] = [];
    if (start != null) {
      for (let k = CORNER_SAMPLES / 2; k <= CORNER_SAMPLES; k++) piece.push(quad(start.a, start.c, start.b, k / CORNER_SAMPLES));
    } else piece.push({ ...(points[i - 1] as Pt) });
    if (end != null) {
      for (let k = 0; k <= CORNER_SAMPLES / 2; k++) piece.push(quad(end.a, end.c, end.b, k / CORNER_SAMPLES));
    } else piece.push({ ...(points[i] as Pt) });
    pieces.push(piece);
  }
  return pieces;
}

/** 折線的長度。 */
export function polylineLength(pts: readonly Pt[]): number {
  let len = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1] as Pt;
    const b = pts[i] as Pt;
    len += Math.hypot(b.x - a.x, b.y - a.y);
  }
  return len;
}

/** 把折線切成虛線：每段實線長 `on`、空白 `off`（從頭開始畫實線）。回傳各段實線的折線。 */
export function dashRuns(pts: readonly Pt[], on: number, off: number): Pt[][] {
  if (pts.length < 2 || on <= 0) return [];
  const period = on + Math.max(0, off);
  const runs: Pt[][] = [];
  let cur: Pt[] | null = null;
  let walked = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1] as Pt;
    const b = pts[i] as Pt;
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    let t = 0;
    while (t < len) {
      const phase = (walked + t) % period;
      const drawing = phase < on;
      const left = drawing ? on - phase : period - phase;
      const step = Math.min(left, len - t);
      const p0 = { x: a.x + ((b.x - a.x) * t) / len, y: a.y + ((b.y - a.y) * t) / len };
      const p1 = { x: a.x + ((b.x - a.x) * (t + step)) / len, y: a.y + ((b.y - a.y) * (t + step)) / len };
      if (drawing) {
        if (cur === null) {
          cur = [p0];
          runs.push(cur);
        }
        cur.push(p1);
      } else cur = null;
      t += step;
      if (step <= 1e-9) break;
    }
    walked += len;
  }
  return runs.filter((r) => r.length >= 2);
}

export type Side = "n" | "s" | "w" | "e";

/** 一群格子的外緣：相鄰格不在群裡的邊（格子、哪一邊）；依座標排序，結果固定。 */
export function outerEdges(cells: ReadonlyArray<{ x: number; y: number }>): Array<{ x: number; y: number; side: Side }> {
  const key = (x: number, y: number) => `${x},${y}`;
  const set = new Set(cells.map((c) => key(c.x, c.y)));
  const out: Array<{ x: number; y: number; side: Side }> = [];
  const seen = new Set<string>();
  for (const { x, y } of [...cells].sort((a, b) => a.y - b.y || a.x - b.x)) {
    if (seen.has(key(x, y))) continue;
    seen.add(key(x, y));
    if (!set.has(key(x, y - 1))) out.push({ x, y, side: "n" });
    if (!set.has(key(x, y + 1))) out.push({ x, y, side: "s" });
    if (!set.has(key(x - 1, y))) out.push({ x, y, side: "w" });
    if (!set.has(key(x + 1, y))) out.push({ x, y, side: "e" });
  }
  return out;
}
