// 介面動畫的時間軸（Phase 6N-10；動畫方案 2.8）：純函式，進度 p（0→1）→ 樣子。不用 Math.random()、不讀時鐘。
// - 傷害數字「彈一下再淡出」：出現時從 0.6 倍彈過頭再落回 1（暴擊字本來就大一號，從 0.5 倍彈、停在 1.15 倍），往上飄，最後 30% 淡出。
// - 減少動態（prefers-reduced-motion）：直接顯示，不彈不飄，到時間就收掉。

export interface FloatFrame {
  alpha: number;
  /** 往上飄的距離（像素，正 ＝ 往上）。 */
  rise: number;
  scale: number;
}

/** 彈跳的長度（佔整段的比例）。 */
export const POP_SPAN = 0.22;

/** 0→1 的彈跳：快速放大超過、落回、小小回彈（easeOutBack 的變形）。 */
function bounce(u: number): number {
  if (u >= 1) return 1;
  const c = 2.2;
  const v = u - 1;
  return 1 + (c + 1) * v * v * v + c * v * v;
}

/** 放大字（暴擊等）彈完停住的倍率。 */
export const BIG_REST = 1.15;

export function floatFrame(p: number, big: boolean, reduced = false): FloatFrame {
  const rest = big ? BIG_REST : 1;
  if (reduced) return { alpha: p < 1 ? 1 : 0, rise: 0, scale: rest };
  const q = Math.max(0, Math.min(1, p));
  const alpha = q < 0.7 ? 1 : 1 - (q - 0.7) / 0.3;
  const rise = Math.min(1, q * 1.5) * (big ? 22 : 16);
  const from = big ? 0.5 : 0.6;
  const scale = q < POP_SPAN ? from + (rest - from) * bounce(q / POP_SPAN) : rest;
  return { alpha, rise, scale };
}

// ---- 放大字的大小（6N-6，美術 PM 6N-5 驗收：「暴擊 −N」太大會蓋到旁邊） ----

/** 一般浮動字（傷害數字）的字級（模型像素）。 */
export const FLOAT_FONT = 20;
/** 放大字停住時是一般字的幾倍。 */
export const BIG_RATIO = 1.3;
/** 放大字整串的寬度上限（格寬的倍數）；超過再縮。 */
export const BIG_MAX_CELLS = 1.8;

/** 字級：放大字 × 停住的倍率（`BIG_REST`）＝ 一般字 × 1.3。 */
export function floatFontSize(big: boolean): number {
  return big ? (FLOAT_FONT * BIG_RATIO) / BIG_REST : FLOAT_FONT;
}

/** 放大字再縮的倍率：`width` ＝ 用 `floatFontSize` 量到的字寬，停住時（× `BIG_REST`）寬度不超過格寬 × 1.8。一般字不縮（1）。 */
export function floatFit(width: number, cell: number, big: boolean): number {
  if (!big || width <= 0) return 1;
  return Math.min(1, (BIG_MAX_CELLS * cell) / (width * BIG_REST));
}

// ---- 浮動字從頭頂冒出（6N-7 追加，美術 PM 6N-6 驗收：從身體中間冒出來會擋住弧光） ----

/** 字的下緣和頭頂之間的空隙（模型像素）。 */
export const FLOAT_HEAD_GAP = 2;
/** 同一格的第二、三個字往上疊的間距（模型像素；沿用 6N-10 以前的 22）。 */
export const FLOAT_SLOT_STEP = 22;
/** 往上飄的最大距離（`floatFrame` 的 rise，放大字 22、一般字 16）。 */
export const FLOAT_RISE_MAX = 22;

/**
 * 浮動字（傷害數字、暴擊、格擋、閃避、失手、背刺…）一開始的中心 y：字的下緣貼在單位頭頂上方 `FLOAT_HEAD_GAP`。
 * - `centerY`：格子頂面中心；`topY`：單位畫出來的頂端（相對格子中心，往上為負；`unitSprite.unitTopY`）；
 * - `textH`：字停住時的高度（已乘縮放）；`slot`：同一格第幾個字（往上疊）；
 * - `minY`：地圖上緣（世界座標）：字飄到最高時不超出地圖（第一排的人頭頂上沒空間時往下讓，寧可蓋到身體也不切掉字）。
 */
export function floatBaseY(centerY: number, topY: number, textH: number, slot: number, minY = Number.NEGATIVE_INFINITY): number {
  const y = centerY + topY - FLOAT_HEAD_GAP - textH / 2 - slot * FLOAT_SLOT_STEP;
  return Math.max(y, minY + textH / 2 + FLOAT_RISE_MAX);
}
