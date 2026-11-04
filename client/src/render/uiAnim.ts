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

export function floatFrame(p: number, big: boolean, reduced = false): FloatFrame {
  const rest = big ? 1.15 : 1;
  if (reduced) return { alpha: p < 1 ? 1 : 0, rise: 0, scale: rest };
  const q = Math.max(0, Math.min(1, p));
  const alpha = q < 0.7 ? 1 : 1 - (q - 0.7) / 0.3;
  const rise = Math.min(1, q * 1.5) * (big ? 22 : 16);
  const from = big ? 0.5 : 0.6;
  const scale = q < POP_SPAN ? from + (rest - from) * bounce(q / POP_SPAN) : rest;
  return { alpha, rise, scale };
}
