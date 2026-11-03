// 確定性亂數（格子座標＋用途 → 種子）：同一格每次畫都一樣，禁止 Math.random。

export function hash(x: number, y: number, salt: number): number {
  let h = 2166136261 ^ salt;
  h = Math.imul(h ^ (x + 374761393), 16777619);
  h = Math.imul(h ^ (y + 668265263), 16777619);
  h ^= h >>> 13;
  h = Math.imul(h, 1274126177);
  return (h ^ (h >>> 16)) >>> 0;
}

/** 回傳 [0,1) 的確定性亂數產生器。 */
export function rng(x: number, y: number, salt: number): () => number {
  return seeded(hash(x, y, salt));
}

/** 直接以整數種子起算的確定性亂數（mulberry32）。區域插畫（6F-ART1）用，與樣張 `docs/art/sample/regionArt.js` 的 `rng(seed)` 同一序列。 */
export function seeded(seed: number): () => number {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
