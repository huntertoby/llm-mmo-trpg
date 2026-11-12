// 靶場測試模式的場景（PR-2c，#147）：滑軌與方角水池的位置與幾何（純函式；PixiJS 的畫法在 `render/battle/terrainLayer.ts`）。
// 畫法照 docs/art/sample/obSamples.js 的 `rail()`、`pool()`／`poolRim()`（樣張一格 52，這裡依格子大小等比例縮放）；
// 只在 `BattleView.practice` 為真時畫（`DrawModel.practice`），實戰與技能工坊（3F）的地圖畫法不變。
// 地圖不改（PR-2 第 9 點）：照現行 content/maps/training_range.yaml（12×10、L 形水面）與 content/world/newcomer.yaml
// 「會動的木樁」的位置；`practiceRange.test.ts` 讀兩個檔案鎖住這張表。
import type { Pos } from "../api/types";

/** 一條滑軌：第 `y` 排、從第 `x0` 欄到第 `x1` 欄（含）。只是外觀，不影響規則。 */
export interface RailDraw {
  y: number;
  x0: number;
  x1: number;
}

/** 測試模式戰場的裝飾（`DrawModel.practice`）。 */
export interface PracticeScene {
  rails: readonly RailDraw[];
  /** 水池的範圍（地圖上原本是水面的格子）：方角水面只畫在這些格子裡現在還是水的那幾格，石條圍著整個範圍。 */
  pool: readonly Pos[];
}

/**
 * 各地圖的測試模式裝飾（鍵＝`BattleView.map_id`）。
 * - training_range：會動的木樁站在 (9, 3)（newcomer.yaml `range.dummies`），滑軌照樣張「5 格、木樁在中間偏右」放在第 3 排第 7～11 欄（到地圖右緣）；
 *   水池＝地圖上的三格水面 (6, 8)、(7, 8)、(6, 9)（L 形，南緣貼地圖下緣）。
 */
export const PRACTICE_SCENES: Readonly<Record<string, PracticeScene>> = {
  training_range: {
    rails: [{ y: 3, x0: 7, x1: 11 }],
    pool: [
      { x: 6, y: 8 },
      { x: 7, y: 8 },
      { x: 6, y: 9 },
    ],
  },
};

const NO_SCENE: PracticeScene = { rails: [], pool: [] };

/** 這張地圖的測試模式裝飾；表上沒有的地圖沒有滑軌與水池。 */
export function practiceSceneOf(mapId: string): PracticeScene {
  return PRACTICE_SCENES[mapId] ?? NO_SCENE;
}

// ---------------------------------------------------------------- 顏色（樣張原值）

/** 水面（城鎮圖庫的河水 `Explore.C.water`）。 */
export const POOL_WATER = 0x3f7aa8;
/** 水面的波紋（`Explore.ground("w")`：白色 40%、線寬 1.5）。 */
export const POOL_RIPPLE = { color: 0xffffff, alpha: 0.4, width: 1.5 } as const;
/** 石條：北邊（受光）較亮、其餘三邊（`poolRim` 的 HI／COL）。 */
export const POOL_SLAB_LIGHT = 0xd0c8b8;
export const POOL_SLAB = 0xb8b0a0;
/** 石條接縫短線。 */
export const POOL_JOINT = 0x6a6458;
/** 墨線（`inkStyle.INK`）。 */
export const PRACTICE_INK = 0x2b1e16;
/** 枕木、鐵軌。 */
export const RAIL_TIE = 0x7a5a38;
export const RAIL_STEEL = 0x5a5a64;

// ---------------------------------------------------------------- 幾何

export interface Rect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/** 樣張的長度（一格 52）換成這張圖的長度。 */
const k52 = (T: number) => T / 52;

/** 石條寬（樣張 9）。 */
export function slabWidth(T: number): number {
  return 9 * k52(T);
}

type Side = "n" | "s" | "w" | "e";
const STEP: Readonly<Record<Side, Pos>> = { n: { x: 0, y: -1 }, s: { x: 0, y: 1 }, w: { x: -1, y: 0 }, e: { x: 1, y: 0 } };

/** 一塊方角水面：畫在第 `row` 排的地形層（`tile`＝這一格，抬高照它）。 */
export interface PoolWater {
  row: number;
  tile: Pos;
  rect: Rect;
  /** 波紋的格子（雜湊用）。 */
  seed: Pos;
}

/** 一條石條：畫在第 `row` 排的表面裝飾層（石條在哪一排的格子上就放哪一排，那一排的人站在它上面）。 */
export interface PoolSlab {
  row: number;
  /** 圍著的水池格（抬高照它）。 */
  tile: Pos;
  side: Side;
  rect: Rect;
  /** 北邊的石條受光，較亮（`poolRim` 的 HI）。 */
  light: boolean;
  /** 接縫短線（[x0, y0, x1, y1]）。 */
  joints: readonly (readonly [number, number, number, number])[];
}

export interface PoolGeom {
  water: PoolWater[];
  slabs: PoolSlab[];
}

const keyOf = (p: Pos) => `${p.x},${p.y}`;

/**
 * 水池的幾何（PR-2c 交付第 3 點）：水面方角、整格填滿到石緣（L 形內角也方角，不磨圓）；外圈方角石條，石條在水面外面
 * （壓在隔壁格上，同樣張 `poolRim`）。範圍貼到地圖邊緣的那一邊，石條改放在水面裡面（不畫到地圖外；水面在那一邊停在石條內緣）。
 * 相鄰的水面格互相多蓋 1（格縫不透出底下的地磚，同樣張「先整塊鋪一層同色的水」）。
 * `isWater`：這一格現在是不是水（結冰、蒸發後不畫水面，石條照舊圍著範圍）。
 */
export function poolGeometry(pool: readonly Pos[], isWater: (p: Pos) => boolean, width: number, height: number, T: number): PoolGeom {
  const inPool = new Set(pool.map(keyOf));
  const inMap = (p: Pos) => p.x >= 0 && p.y >= 0 && p.x < width && p.y < height;
  const o = slabWidth(T);
  const water: PoolWater[] = [];
  const slabs: PoolSlab[] = [];
  const sorted = [...pool].filter(inMap).sort((a, b) => a.y - b.y || a.x - b.x);
  for (const p of sorted) {
    const nb = (s: Side): Pos => ({ x: p.x + STEP[s].x, y: p.y + STEP[s].y });
    const pooled = (s: Side) => inPool.has(keyOf(nb(s)));
    const edge = (s: Side) => !inMap(nb(s));
    // 石條往兩端多伸一個石條寬（外角）：只在那一端不是水池、也不是地圖外時
    const ext = (s: Side) => (pooled(s) || edge(s) ? 0 : o);
    const X0 = p.x * T;
    const Y0 = p.y * T;
    const X1 = X0 + T;
    const Y1 = Y0 + T;
    const inset = { n: 0, s: 0, w: 0, e: 0 };
    for (const side of ["n", "s", "w", "e"] as const) {
      if (pooled(side)) continue;
      const inside = edge(side);
      if (inside) inset[side] = o;
      const rect = slabRect(side, inside, { X0, Y0, X1, Y1 }, o, ext);
      const row = inside || side === "w" || side === "e" ? p.y : p.y + STEP[side].y;
      slabs.push({ row, tile: p, side, rect, light: side === "n", joints: slabJoints(side, rect, { X0, Y0 }, T) });
    }
    if (!isWater(p)) continue;
    const grow = (s: Side) => (pooled(s) && isWater(nb(s)) ? 1 : 0);
    water.push({
      row: p.y,
      tile: p,
      seed: p,
      rect: { x0: X0 + inset.w - grow("w"), y0: Y0 + inset.n - grow("n"), x1: X1 - inset.e + grow("e"), y1: Y1 - inset.s + grow("s") },
    });
  }
  return { water, slabs };
}

function slabRect(side: Side, inside: boolean, b: { X0: number; Y0: number; X1: number; Y1: number }, o: number, ext: (s: Side) => number): Rect {
  const { X0, Y0, X1, Y1 } = b;
  if (side === "n") return { x0: X0 - ext("w"), x1: X1 + ext("e"), y0: inside ? Y0 : Y0 - o, y1: inside ? Y0 + o : Y0 };
  if (side === "s") return { x0: X0 - ext("w"), x1: X1 + ext("e"), y0: inside ? Y1 - o : Y1, y1: inside ? Y1 : Y1 + o };
  if (side === "w") return { x0: inside ? X0 : X0 - o, x1: inside ? X0 + o : X0, y0: Y0, y1: Y1 };
  return { x0: inside ? X1 - o : X1, x1: inside ? X1 : X1 + o, y0: Y0, y1: Y1 };
}

/** 接縫短線：每一格的那一段石條在 1/4、3/4 處各一條（相鄰格接起來間距一樣；樣張 2×2 水池約每 30 一條）。 */
function slabJoints(side: Side, r: Rect, b: { X0: number; Y0: number }, T: number): [number, number, number, number][] {
  const m = 1.5 * k52(T);
  if (side === "n" || side === "s") return [0.25, 0.75].map((f) => [b.X0 + T * f, r.y0 + m, b.X0 + T * f, r.y1 - m]);
  return [0.25, 0.75].map((f) => [r.x0 + m, b.Y0 + T * f, r.x1 - m, b.Y0 + T * f]);
}

/** 一格水面的兩道波紋（`Explore.ground("w")`：第 i 道在 y＋12＋22i＋亂數 6、x＋亂數 18，二次曲線寬 20、拱高 5；樣張一格 52）。 */
export function rippleCurves(seed: Pos, T: number): { x: number; y: number; cx: number; cy: number; ex: number; ey: number }[] {
  const r = tileRng(seed.x, seed.y);
  const k = k52(T);
  const out = [];
  for (let i = 0; i < 2; i++) {
    const wy = (12 + i * 22 + r() * 6) * k;
    const wx = r() * 18 * k;
    out.push({ x: seed.x * T + wx, y: seed.y * T + wy, cx: seed.x * T + wx + 10 * k, cy: seed.y * T + wy - 5 * k, ex: seed.x * T + wx + 20 * k, ey: seed.y * T + wy });
  }
  return out;
}

/** 樣張 `Explore.R(gx, gy, 3)` 的 xorshift（同一格每次一樣）。 */
function tileRng(gx: number, gy: number): () => number {
  let s = ((gx * 73856093) ^ (gy * 19349663) ^ (3 * 83492791)) >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >> 17;
    s ^= s << 5;
    s >>>= 0;
    return (s % 100000) / 100000;
  };
}

/** 滑軌的幾何（`rail()`）：兩條鐵軌（軌距 ±6）、枕木（寬 7、上下各 8.5，間距 22）；軌道在那一排格子的 0.62 高度。 */
export interface RailGeom {
  row: number;
  y: number;
  x0: number;
  x1: number;
  /** 兩條鐵軌的 y。 */
  rails: [number, number];
  ties: Rect[];
  /** 鐵軌線寬。 */
  steel: number;
}

export function railGeometry(rail: RailDraw, T: number): RailGeom {
  const k = k52(T);
  const x0 = rail.x0 * T + 6 * k;
  const x1 = (rail.x1 + 1) * T - 6 * k;
  const y = (rail.y + 0.62) * T;
  const ties: Rect[] = [];
  for (let x = x0 + 8 * k; x < x1 - 4 * k; x += 22 * k) ties.push({ x0: x - 3.5 * k, x1: x + 3.5 * k, y0: y - 8.5 * k, y1: y + 8.5 * k });
  return { row: rail.y, y, x0, x1, rails: [y - 6 * k, y + 6 * k], ties, steel: 2.4 * k };
}
