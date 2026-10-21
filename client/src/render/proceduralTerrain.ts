// 程式繪製的地形紋理（Phase 3-14）：岩漿、深淵、冰窟沒有素材圖，改用方塊像素風的色塊拼出紋理。
// 純函式：輸入地形與格子座標，輸出矩形清單（相對格子左上角）；只用整數雜湊，同一格永遠長一樣。

export interface Patch {
  x: number;
  y: number;
  w: number;
  h: number;
  color: number;
  alpha: number;
}

export const PROCEDURAL_TERRAINS: ReadonlySet<string> = new Set(["lava", "chasm", "ice_hole"]);

export function isProcedural(terrain: string): boolean {
  return PROCEDURAL_TERRAINS.has(terrain);
}

/** 整數雜湊（不使用 Math.random，確保重畫不閃爍）。 */
function hash(x: number, y: number, i: number): number {
  let h = (Math.imul(x + 1, 73856093) ^ Math.imul(y + 1, 19349663) ^ Math.imul(i + 1, 83492791)) >>> 0;
  h = Math.imul(h ^ (h >>> 15), 2246822519) >>> 0;
  return (h ^ (h >>> 13)) >>> 0;
}

const CELL = 4; // 一個「大像素」的邊長（模型像素）

function lava(gx: number, gy: number, size: number): Patch[] {
  const n = Math.floor(size / CELL);
  const out: Patch[] = [{ x: 0, y: 0, w: size, h: size, color: 0xd8471c, alpha: 1 }];
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const r = hash(gx * n + i, gy * n + j, 1) % 100;
      // 流動的明暗：以斜向波紋加上雜訊，亮處偏黃、暗處偏結殼
      const wave = (i + j + (hash(gx, gy, 2) % 5)) % 6;
      let color = 0;
      let alpha = 0;
      if (r < 14 || wave === 0) {
        color = 0xffb02e;
        alpha = 0.55 + (r % 3) * 0.12;
      } else if (r > 84) {
        color = 0x6a1a0a;
        alpha = 0.6;
      } else if (wave === 3 && r > 55) {
        color = 0xff7a1e;
        alpha = 0.5;
      }
      if (alpha > 0) out.push({ x: i * CELL, y: j * CELL, w: CELL, h: CELL, color, alpha });
    }
  }
  return out;
}

function chasm(gx: number, gy: number, size: number): Patch[] {
  // 漸層黑洞：由外往內一圈圈變黑
  const out: Patch[] = [{ x: 0, y: 0, w: size, h: size, color: 0x2c2c3c, alpha: 1 }];
  const rings = [0x22222f, 0x181822, 0x0e0e15, 0x050509];
  rings.forEach((color, k) => {
    const inset = (k + 1) * Math.floor(size / 10);
    out.push({ x: inset, y: inset, w: size - inset * 2, h: size - inset * 2, color, alpha: 1 });
  });
  // 邊緣少許碎石
  for (let i = 0; i < 4; i++) {
    const h = hash(gx, gy, 10 + i);
    out.push({ x: h % (size - 4), y: i % 2 === 0 ? 0 : size - 3, w: 4, h: 3, color: 0x4a4a5c, alpha: 0.7 });
  }
  return out;
}

function iceHole(gx: number, gy: number, size: number): Patch[] {
  const out: Patch[] = [{ x: 0, y: 0, w: size, h: size, color: 0x17345c, alpha: 1 }];
  const inset = Math.floor(size / 6);
  out.push({ x: inset, y: inset, w: size - inset * 2, h: size - inset * 2, color: 0x0d2442, alpha: 0.9 });
  for (let i = 0; i < 6; i++) {
    const h = hash(gx, gy, 20 + i);
    const w = 6 + (h % 10);
    out.push({ x: (h >>> 4) % (size - w), y: (h >>> 12) % (size - 2), w, h: 2, color: 0x9fd8ff, alpha: 0.35 });
  }
  return out;
}

/** 回傳該地形在 (gx, gy) 格的紋理矩形；不是程式繪製的地形回傳空陣列。 */
export function proceduralPatches(terrain: string, gx: number, gy: number, size: number): Patch[] {
  if (terrain === "lava") return lava(gx, gy, size);
  if (terrain === "chasm") return chasm(gx, gy, size);
  if (terrain === "ice_hole") return iceHole(gx, gy, size);
  return [];
}
