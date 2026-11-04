// 地表的動畫（Phase 6N-9；docs/art/動畫移植需求第二批.md 第 8 節、動畫方案.md 2.6）。全部是純函式：
// - 出現：新的表面從格子中心擴散開（舊的樣子往外被蓋掉）；消失：舊的表面往中心收縮；
// - 火蔓延：同一次重畫新出現的火，從起點沿相鄰格（上下左右）擴散，每格延遲 0.08 秒；
// - 水面反光線慢慢飄；油面虹彩流動；火面的光暈輕輕閃。
// 只比較前後兩次的畫面資料（格子的表面），不改規則、不讀事件以外的東西；相位只看格子座標的雜湊（`inkStyle.seedOf`）。
// 不用 Math.random()、不讀時間（時鐘由呼叫端給）。
import type { DrawModel } from "../battle/drawModel";
import { seedOf } from "./inkStyle";

const TAU = Math.PI * 2;

/** 火蔓延每格的延遲（毫秒；需求 0.08 秒）。 */
export const SPREAD_STEP_MS = 80;
/** 出現（從中心擴散）、消失（往中心收縮）的長度（毫秒；原型值）。 */
export const APPEAR_MS = 260;
export const VANISH_MS = 260;
/** 一次蔓延最多排幾格的延遲（再遠的格子同時出現，避免一大片油燒很久）。 */
export const SPREAD_MAX_STEPS = 12;

export interface SurfaceChange {
  x: number;
  y: number;
  before: string;
  after: string;
  /** `appear`：新的表面從中心擴散開（含換成另一種）；`vanish`：舊的表面往中心收縮消失。 */
  kind: "appear" | "vanish";
  /** 開始前的延遲（毫秒；火蔓延用，其他 0）。 */
  delayMs: number;
}

const key = (x: number, y: number): string => `${x},${y}`;

/** 前後兩個畫面是不是同一張地圖（大小、主題、每格地形都一樣）；不是時不播轉場（換地圖、換戰鬥）。 */
export function sameBoard(prev: DrawModel, next: DrawModel): boolean {
  if (prev.width !== next.width || prev.height !== next.height || prev.region !== next.region || prev.look !== next.look) return false;
  if (prev.tiles.length !== next.tiles.length) return false;
  const terrain = new Map(prev.tiles.map((t) => [key(t.x, t.y), t.terrain]));
  return next.tiles.every((t) => terrain.get(key(t.x, t.y)) === t.terrain);
}

const NEIGHBORS: ReadonlyArray<readonly [number, number]> = [
  [0, -1],
  [1, 0],
  [0, 1],
  [-1, 0],
];

/** 依 (y, x) 排序（確定性）。 */
const byPos = (a: { x: number; y: number }, b: { x: number; y: number }): number => a.y - b.y || a.x - b.x;

/** 從 `seeds` 沿上下左右走到 `cells` 裡每一格的步數（走不到的不在結果裡）。 */
function bfs(cells: ReadonlySet<string>, seeds: ReadonlyArray<{ x: number; y: number }>): Map<string, number> {
  const dist = new Map<string, number>();
  let frontier = [...seeds].sort(byPos);
  for (const s of frontier) dist.set(key(s.x, s.y), 0);
  let d = 0;
  while (frontier.length > 0) {
    d += 1;
    const next: Array<{ x: number; y: number }> = [];
    for (const p of frontier) {
      for (const [dx, dy] of NEIGHBORS) {
        const q = { x: p.x + dx, y: p.y + dy };
        const k = key(q.x, q.y);
        if (!cells.has(k) || dist.has(k)) continue;
        dist.set(k, d);
        next.push(q);
      }
    }
    frontier = next.sort(byPos);
  }
  return dist;
}

/** 一塊相連的格子裡「最中間」的一格（到其他格最遠步數最小；同分取 (y, x) 最小）。 */
function centerOf(cells: ReadonlyArray<{ x: number; y: number }>): { x: number; y: number } {
  const set = new Set(cells.map((c) => key(c.x, c.y)));
  let best = cells[0]!;
  let bestEcc = Number.POSITIVE_INFINITY;
  for (const c of [...cells].sort(byPos)) {
    const ecc = Math.max(...bfs(set, [c]).values());
    if (ecc < bestEcc) {
      best = c;
      bestEcc = ecc;
    }
  }
  return best;
}

/**
 * 新出現的火每一格的蔓延步數。起點：
 * - 和原本就在燒的格子相鄰的新火格（火從那裡燒過來）；
 * - 一塊新火都不和舊火相鄰時（點燃一整片油），取那一塊最中間的格子（畫面資料裡沒有「從哪一格點燃」）。
 */
export function spreadSteps(newFire: ReadonlyArray<{ x: number; y: number }>, oldFire: ReadonlySet<string>): Map<string, number> {
  const cells = new Set(newFire.map((c) => key(c.x, c.y)));
  const out = new Map<string, number>();
  const left = new Set(cells);
  const sorted = [...newFire].sort(byPos);
  // 先分成相連的塊（上下左右）
  for (const start of sorted) {
    if (!left.has(key(start.x, start.y))) continue;
    const comp = [...bfs(left, [start]).keys()];
    for (const k of comp) left.delete(k);
    const block = sorted.filter((c) => comp.includes(key(c.x, c.y)));
    const compSet = new Set(comp);
    const touching = block.filter((c) => NEIGHBORS.some(([dx, dy]) => oldFire.has(key(c.x + dx, c.y + dy))));
    const seeds = touching.length > 0 ? touching : [centerOf(block)];
    for (const [k, d] of bfs(compSet, seeds)) out.set(k, Math.min(d, SPREAD_MAX_STEPS));
  }
  return out;
}

/** 前後兩個畫面之間改變的表面（依 (y, x) 排序）；不是同一張地圖時沒有。 */
export function surfaceChanges(prev: DrawModel, next: DrawModel): SurfaceChange[] {
  if (!sameBoard(prev, next)) return [];
  const before = new Map(prev.tiles.map((t) => [key(t.x, t.y), String(t.surface)]));
  const changed = next.tiles
    .filter((t) => before.get(key(t.x, t.y)) !== String(t.surface))
    .map((t) => ({ x: t.x, y: t.y, before: before.get(key(t.x, t.y)) ?? "none", after: String(t.surface) }))
    .sort(byPos);
  const oldFire = new Set(prev.tiles.filter((t) => t.surface === "fire").map((t) => key(t.x, t.y)));
  const steps = spreadSteps(
    changed.filter((c) => c.after === "fire"),
    oldFire,
  );
  return changed.map((c) => ({
    ...c,
    kind: c.after === "none" ? "vanish" : "appear",
    delayMs: c.after === "fire" ? (steps.get(key(c.x, c.y)) ?? 0) * SPREAD_STEP_MS : 0,
  }));
}

/** 轉場整段的長度（毫秒，含延遲）；`scale` 是播放速度的時間倍率。 */
export function changeTotalMs(c: SurfaceChange, scale = 1): number {
  return (c.delayMs + (c.kind === "appear" ? APPEAR_MS : VANISH_MS)) * scale;
}

const easeOut = (u: number): number => 1 - (1 - u) * (1 - u);

/**
 * 轉場在 `ms`（從轉場開始算）時「舊的樣子」還看得到的圓：
 * - `appear`：舊的樣子蓋在上面、中間挖一個越來越大的洞（`inverse = true`），`radius` 0 → 1；
 * - `vanish`：舊的樣子只留中間一個越來越小的圓（`inverse = false`），`radius` 1 → 0。
 * `radius` 是格子邊長的倍數，1 ＝ 蓋滿整格（中心到角 ≈ 0.71）。
 */
export function revealAt(c: SurfaceChange, ms: number, scale = 1): { radius: number; inverse: boolean; done: boolean } {
  const len = (c.kind === "appear" ? APPEAR_MS : VANISH_MS) * scale;
  const local = ms - c.delayMs * scale;
  const u = len <= 0 ? 1 : Math.min(1, Math.max(0, local / len));
  const done = ms >= changeTotalMs(c, scale);
  if (c.kind === "appear") return { radius: easeOut(u) * 0.75, inverse: true, done };
  return { radius: (1 - easeOut(u)) * 0.75, inverse: false, done };
}

// ---- 持續的表面動態 ----

export type ShimmerTex = "streak" | "sheen" | "glow";

export interface Shimmer {
  tex: ShimmerTex;
  /** 格子內的位置（0～1，格子左上角為原點）。 */
  x: number;
  y: number;
  scale: number;
  alpha: number;
  rot: number;
  /** 染色（0xRRGGBB）。 */
  tint: number;
}

/** 有持續動態的表面。 */
export const ANIMATED_SURFACES: readonly string[] = ["water", "oil", "fire"];

export const SHIMMER = {
  /** 水面反光線飄過一格的時間（慢）。 */
  waterDriftMs: 5200,
  /** 油面虹彩轉一圈的時間。 */
  oilHueMs: 6000,
  oilDriftMs: 4200,
  /** 火面光暈的閃動。 */
  fireMs: 420,
} as const;

/** 色相（0～1）→ 0xRRGGBB（飽和度、亮度固定，給油面虹彩）。 */
export function hueColor(h: number, s = 0.75, l = 0.68): number {
  const hue = ((h % 1) + 1) % 1;
  const f = (n: number): number => {
    const k = (n + hue * 12) % 12;
    const a = s * Math.min(l, 1 - l);
    return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))));
  };
  return (f(0) << 16) | (f(8) << 8) | f(4);
}

/** 一格表面在 `ms` 時的動態（沒有動態的表面回傳空陣列）。 */
export function surfaceShimmer(surface: string, x: number, y: number, ms: number): Shimmer[] {
  const h = seedOf(`${x},${y}:${surface}`);
  const p = (h % 1000) / 1000;
  if (surface === "water") {
    const out: Shimmer[] = [];
    for (let i = 0; i < 2; i++) {
      const u = (((ms / SHIMMER.waterDriftMs + p + i * 0.5) % 1) + 1) % 1;
      out.push({
        tex: "streak",
        x: 0.22 + 0.56 * u,
        y: 0.32 + i * 0.32 + 0.03 * Math.sin((u + i) * TAU),
        scale: 0.8 + 0.2 * Math.sin(u * Math.PI),
        alpha: 0.42 * Math.sin(u * Math.PI),
        rot: -0.12,
        tint: 0xffffff,
      });
    }
    return out;
  }
  if (surface === "oil") {
    const u = ms / SHIMMER.oilDriftMs + p;
    return [
      {
        tex: "sheen",
        x: 0.5 + 0.12 * Math.sin(u * TAU),
        y: 0.5 + 0.08 * Math.cos(u * TAU * 0.7),
        scale: 1,
        alpha: 0.3,
        rot: u * 0.8,
        tint: hueColor(ms / SHIMMER.oilHueMs + p),
      },
    ];
  }
  if (surface === "fire") {
    const t = ms / SHIMMER.fireMs + p * 7;
    const flicker = 0.5 + 0.3 * Math.sin(t * TAU) + 0.2 * Math.sin(t * TAU * 2.3 + p * 5);
    return [{ tex: "glow", x: 0.5, y: 0.55, scale: 0.92 + 0.08 * flicker, alpha: 0.12 + 0.2 * flicker, rot: 0, tint: 0xffa040 }];
  }
  return [];
}
