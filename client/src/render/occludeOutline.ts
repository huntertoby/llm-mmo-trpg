// OCL-1a：被遮擋剪影外框的純函式（`docs/phases/PhaseOCL-1計畫.md`、`docs/art/被遮擋剪影外框-移植需求.md`）。
// 樣張 `docs/art/sample/occludeOutline.js` 的 `coverRatio`／`band`／`dilate` 改寫成對 alpha 陣列的整數／浮點運算（Q1）：
// - 遮罩：alpha ≥ 128 才算一個像素（`ALPHA_MIN`）。
// - 比例：一律在「模型像素」算（1 格 48、原點對齊整數模型像素），被擋者遮罩 M、大型前排遮罩聯集 O，比例＝|M ∩ O| ÷ |M|。
// - 色帶：精確歐氏距離轉換（Felzenszwalb 兩趟一維）→ 色線＝輪廓往內寬 w、黑邊＝色線兩側各 ink，邊緣 1 px 線性過渡（反鋸齒）。
// - 裁切：色線 ∩ O、黑邊 ∩ dilate(O, ink)；O 照畫的順序疊（大型前排加、畫在它之後的小兵挖掉）。
// 不讀時鐘、不用亂數、不碰 Pixi 與 DOM：同一輸入算兩次逐位元組相同（測試 `ocl1Outline.test.ts`）。

/** alpha ≥ 0.5 才算身體（0～255）。 */
export const ALPHA_MIN = 128;
/** 大型前排：身體面積（模型 px²）≥ 這個值（D2；灰燼之心 8928、碎晶之主 8220、一般單位 506～1963）。 */
export const BIG_FRONT_AREA = 4000;
/** 遲滯：沒畫時 ≥ 55% 才開始畫；畫著時 < 45% 才拿掉（D3）。 */
export const OUTLINE_ON = 0.55;
export const OUTLINE_OFF = 0.45;
/** 色線寬、兩側黑邊寬（螢幕 CSS px，D3）。 */
export const OUTLINE_CSS_PX = 1.5;
export const OUTLINE_INK_CSS_PX = 0.75;
/** 黑邊色（Q 版外框色）。 */
export const OUTLINE_INK = 0x16121a;
/** 整層透明度（D3）。 */
export const OUTLINE_ALPHA = 0.8;
/** 線寬量化的級距（貼圖 px，Q2）。 */
export const OUTLINE_WIDTH_STEP = 0.25;
/** 前排只看被擋者南邊 0～3 排（需求 3 第 2 點）。 */
export const FRONT_ROWS = 3;
/** 模型像素遮罩的取樣：每個模型像素取 n×n 點平均 alpha（≥ 128 才算）。 */
export const MODEL_SAMPLES = 4;

/** 一張貼圖的 alpha（0～255，一個像素一個位元組）。 */
export interface AlphaImage {
  readonly w: number;
  readonly h: number;
  readonly alpha: Uint8Array;
}

/** 貼圖在模型座標的位置：貼圖 (0, 0) 的左上角在 (`left`, `top`)，每個貼圖像素 `sx`×`sy` 模型像素。 */
export interface TexPlace {
  readonly left: number;
  readonly top: number;
  readonly sx: number;
  readonly sy: number;
}

/** 模型像素的二值遮罩：(x0, y0) 起 w×h（整數模型像素）。 */
export interface ModelMask {
  readonly x0: number;
  readonly y0: number;
  readonly w: number;
  readonly h: number;
  readonly bits: Uint8Array;
  /** 遮罩像素數（＝身體面積，模型 px²）。 */
  readonly area: number;
}

/** RGBA（`getImageData` 的 data）→ 只留 alpha。 */
export function alphaOf(rgba: ArrayLike<number>, w: number, h: number): AlphaImage {
  const n = w * h;
  const alpha = new Uint8Array(n);
  for (let i = 0; i < n; i++) alpha[i] = rgba[i * 4 + 3] ?? 0;
  return { w, h, alpha };
}

/** alpha ≥ 128 → 1，其餘 0。 */
export function binaryMask(img: AlphaImage): Uint8Array {
  const out = new Uint8Array(img.w * img.h);
  for (let i = 0; i < out.length; i++) out[i] = (img.alpha[i] ?? 0) >= ALPHA_MIN ? 1 : 0;
  return out;
}

/** 遮罩的像素數。 */
export function maskArea(bits: Uint8Array): number {
  let n = 0;
  for (let i = 0; i < bits.length; i++) n += bits[i] ?? 0;
  return n;
}

/**
 * 貼圖 alpha → 模型像素遮罩：每個整數模型像素取 `MODEL_SAMPLES`² 個點（最近的貼圖像素）平均 alpha，≥ 128 才算（≈ 1 倍畫的覆蓋率 ≥ 0.5）。
 * 原點對齊整數模型像素（`floor`）：同一張貼圖、同樣的小數位置，平移整數格結果只平移。
 */
export function modelMask(img: AlphaImage, p: TexPlace, ss = MODEL_SAMPLES): ModelMask {
  const x0 = Math.floor(p.left);
  const y0 = Math.floor(p.top);
  const w = Math.max(0, Math.ceil(p.left + img.w * p.sx) - x0);
  const h = Math.max(0, Math.ceil(p.top + img.h * p.sy) - y0);
  const bits = new Uint8Array(w * h);
  const need = ALPHA_MIN * ss * ss;
  let area = 0;
  // 每一欄、每一列的取樣點先換成貼圖座標（−1＝畫布外）
  const colOf = new Int32Array(w * ss);
  for (let x = 0; x < w; x++) {
    for (let i = 0; i < ss; i++) {
      const tx = Math.floor((x0 + x + (i + 0.5) / ss - p.left) / p.sx);
      colOf[x * ss + i] = tx >= 0 && tx < img.w ? tx : -1;
    }
  }
  const rowOf = new Int32Array(h * ss);
  for (let y = 0; y < h; y++) {
    for (let j = 0; j < ss; j++) {
      const ty = Math.floor((y0 + y + (j + 0.5) / ss - p.top) / p.sy);
      rowOf[y * ss + j] = ty >= 0 && ty < img.h ? ty : -1;
    }
  }
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let sum = 0;
      for (let j = 0; j < ss; j++) {
        const ty = rowOf[y * ss + j] as number;
        if (ty < 0) continue;
        const base = ty * img.w;
        for (let i = 0; i < ss; i++) {
          const tx = colOf[x * ss + i] as number;
          if (tx >= 0) sum += img.alpha[base + tx] ?? 0;
        }
      }
      if (sum >= need) {
        bits[y * w + x] = 1;
        area += 1;
      }
    }
  }
  return { x0, y0, w, h, bits, area };
}

/** 模型像素 (x, y) 在遮罩裡嗎。 */
function hitAt(m: ModelMask, x: number, y: number): boolean {
  const lx = x - m.x0;
  const ly = y - m.y0;
  return lx >= 0 && ly >= 0 && lx < m.w && ly < m.h && m.bits[ly * m.w + lx] === 1;
}

/** 兩個遮罩的外接矩形相交嗎。 */
export function boxesMeet(a: Pick<ModelMask, "x0" | "y0" | "w" | "h">, b: Pick<ModelMask, "x0" | "y0" | "w" | "h">): boolean {
  return a.x0 < b.x0 + b.w && b.x0 < a.x0 + a.w && a.y0 < b.y0 + b.h && b.y0 < a.y0 + a.h;
}

/** 遮擋比例：|M ∩ (∪ fronts)| ÷ |M|（M 沒有像素時 0）。 */
export function coverRatio(m: ModelMask, fronts: readonly ModelMask[]): { n: number; hit: number; ratio: number } {
  const near = fronts.filter((f) => boxesMeet(m, f));
  let n = 0;
  let hit = 0;
  for (let y = 0; y < m.h; y++) {
    for (let x = 0; x < m.w; x++) {
      if (m.bits[y * m.w + x] !== 1) continue;
      n += 1;
      const gx = m.x0 + x;
      const gy = m.y0 + y;
      if (near.some((f) => hitAt(f, gx, gy))) hit += 1;
    }
  }
  return { n, hit, ratio: n === 0 ? 0 : hit / n };
}

/** 遲滯（D3）：上一次沒畫 → ≥ 55% 才畫；上一次有畫 → < 45% 才拿掉。 */
export function outlineWanted(ratio: number, was: boolean): boolean {
  return was ? ratio >= OUTLINE_OFF : ratio >= OUTLINE_ON;
}

/** 線寬（貼圖 px）：`css` 螢幕 CSS px × 貼圖 px／模型 px ÷ 地圖縮放（CSS px／模型 px），量化到 0.25（Q2）。 */
export function outlineWidthTex(css: number, texPerModel: number, scale: number): number {
  const v = (css * texPerModel) / scale;
  return Math.max(OUTLINE_WIDTH_STEP, Math.round(v / OUTLINE_WIDTH_STEP) * OUTLINE_WIDTH_STEP);
}

// ---- 距離轉換（Felzenszwalb & Huttenlocher，精確歐氏距離的平方）----
const INF = 1e20;

function edt1d(f: Float64Array, n: number, d: Float64Array, v: Int32Array, z: Float64Array): void {
  let k = 0;
  v[0] = 0;
  z[0] = -INF;
  z[1] = INF;
  const sect = (q: number, r: number): number => ((f[q] as number) + q * q - ((f[r] as number) + r * r)) / (2 * q - 2 * r);
  for (let q = 1; q < n; q++) {
    let s = sect(q, v[k] as number);
    while (s <= (z[k] as number)) {
      k -= 1;
      s = sect(q, v[k] as number);
    }
    k += 1;
    v[k] = q;
    z[k] = s;
    z[k + 1] = INF;
  }
  k = 0;
  for (let q = 0; q < n; q++) {
    while ((z[k + 1] as number) < q) k += 1;
    const r = v[k] as number;
    d[q] = (q - r) * (q - r) + (f[r] as number);
  }
}

/** 每個像素到最近的「`bits` 等於 `target`」像素的距離平方（像素中心到像素中心；沒有這種像素時 ≥ 1e20）。 */
export function sqDistTo(bits: Uint8Array, w: number, h: number, target: 0 | 1): Float64Array {
  const out = new Float64Array(w * h);
  const n = Math.max(w, h);
  const f = new Float64Array(n);
  const d = new Float64Array(n);
  const v = new Int32Array(n);
  const z = new Float64Array(n + 1);
  for (let x = 0; x < w; x++) {
    for (let y = 0; y < h; y++) f[y] = bits[y * w + x] === target ? 0 : INF;
    edt1d(f, h, d, v, z);
    for (let y = 0; y < h; y++) out[y * w + x] = d[y] as number;
  }
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) f[x] = out[y * w + x] as number;
    edt1d(f, w, d, v, z);
    for (let x = 0; x < w; x++) out[y * w + x] = d[x] as number;
  }
  return out;
}

const clamp01 = (v: number): number => (v <= 0 ? 0 : v >= 1 ? 1 : v);

/** 色帶（未裁切）：每個像素的色線覆蓋率 `color`、黑邊覆蓋率 `ink`（0～255）。 */
export interface OutlineBand {
  readonly w: number;
  readonly h: number;
  readonly color: Uint8Array;
  readonly ink: Uint8Array;
}

/**
 * 被擋者身體遮罩（貼圖解析度）的色帶（樣張 `band(M, O, 0, w)` 與 `band(M, O, ink, w + ink)`）：
 * 帶號距離 s（身體內為正、像素中心到輪廓）＝ 內：到最近外部像素的距離 − 0.5；外：−(到最近身體像素的距離 − 0.5)。
 * 色線＝ s ∈ (0, w]、黑邊＝ s ∈ (−ink, w + ink]，邊緣各 1 px 線性過渡。畫布邊緣當作身體外。
 */
export function outlineBand(bits: Uint8Array, w: number, h: number, width: number, ink: number): OutlineBand {
  const din = sqDistTo(bits, w, h, 0);
  const dout = sqDistTo(bits, w, h, 1);
  const color = new Uint8Array(w * h);
  const inkOut = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      let s: number;
      if (bits[i] === 1) {
        const edge = Math.min(x + 1, w - x, y + 1, h - y);
        s = Math.min(Math.sqrt(din[i] as number), edge) - 0.5;
        color[i] = Math.round(clamp01(width + 0.5 - s) * 255);
        inkOut[i] = Math.round(clamp01(width + ink + 0.5 - s) * 255);
      } else {
        s = -(Math.sqrt(dout[i] as number) - 0.5);
        inkOut[i] = Math.round(clamp01(ink + 0.5 + s) * 255);
      }
    }
  }
  return { w, h, color, ink: inkOut };
}

/** 被擋者貼圖上的一層前排（照畫的順序）：`big`＝大型前排（加進 O），否則挖掉（需求 3 第 3 點）。 */
export interface ClipLayer {
  readonly img: AlphaImage;
  readonly place: TexPlace;
  readonly big: boolean;
}

/** 裁切遮罩 O（被擋者貼圖解析度）：每個像素中心換到模型座標，照順序疊各層（最近鄰取樣、alpha ≥ 128）。 */
export function clipMask(w: number, h: number, place: TexPlace, layers: readonly ClipLayer[]): Uint8Array {
  const out = new Uint8Array(w * h);
  for (const l of layers) {
    const lp = l.place;
    const v = l.big ? 1 : 0;
    // 只走這一層的外接範圍
    const xa = Math.max(0, Math.floor((lp.left - place.left) / place.sx) - 1);
    const xb = Math.min(w, Math.ceil((lp.left + l.img.w * lp.sx - place.left) / place.sx) + 1);
    const ya = Math.max(0, Math.floor((lp.top - place.top) / place.sy) - 1);
    const yb = Math.min(h, Math.ceil((lp.top + l.img.h * lp.sy - place.top) / place.sy) + 1);
    for (let y = ya; y < yb; y++) {
      const ty = Math.floor((place.top + (y + 0.5) * place.sy - lp.top) / lp.sy);
      if (ty < 0 || ty >= l.img.h) continue;
      for (let x = xa; x < xb; x++) {
        const tx = Math.floor((place.left + (x + 0.5) * place.sx - lp.left) / lp.sx);
        if (tx < 0 || tx >= l.img.w) continue;
        if ((l.img.alpha[ty * l.img.w + tx] ?? 0) >= ALPHA_MIN) out[y * w + x] = v;
      }
    }
  }
  return out;
}

/**
 * 合成外框（RGBA、非預乘，給 `putImageData`）：色線畫白色（之後用 `tint` 上陣營色）、黑邊畫 `#16121a`，先疊成一層不透明的。
 * 色線 ∩ O；黑邊 ∩ dilate(O, ink)（距離轉換，邊緣 1 px 過渡）。
 */
export function composeOutline(band: OutlineBand, clip: Uint8Array, ink: number): Uint8ClampedArray {
  const { w, h } = band;
  const dO = sqDistTo(clip, w, h, 1);
  const out = new Uint8ClampedArray(w * h * 4);
  const ir = (OUTLINE_INK >> 16) & 255;
  const ig = (OUTLINE_INK >> 8) & 255;
  const ib = OUTLINE_INK & 255;
  for (let i = 0; i < w * h; i++) {
    const ci = band.ink[i] as number;
    if (ci === 0) continue;
    const inO = clip[i] === 1;
    const cc = inO ? (band.color[i] as number) / 255 : 0;
    const clipInk = inO ? 1 : clamp01(ink + 1 - Math.sqrt(dO[i] as number));
    const ca = (ci / 255) * clipInk;
    const a = cc + ca * (1 - cc);
    if (a <= 0) continue;
    const k = ca * (1 - cc);
    out[i * 4] = Math.round((255 * cc + ir * k) / a);
    out[i * 4 + 1] = Math.round((255 * cc + ig * k) / a);
    out[i * 4 + 2] = Math.round((255 * cc + ib * k) / a);
    out[i * 4 + 3] = Math.round(a * 255);
  }
  return out;
}

/** 受擊閃白（D4，1b 接上）：色線＝mix(陣營色, 白, k)。`k` 夾在 0～1。 */
export function flashTint(color: number, k: number): number {
  const t = clamp01(k);
  const ch = (s: number): number => {
    const v = (color >> s) & 255;
    return Math.round(v + (255 - v) * t);
  };
  return (ch(16) << 16) | (ch(8) << 8) | ch(0);
}

/** 受擊閃白時整層透明度（D4）：0.8 + 0.2k。 */
export function flashAlpha(k: number): number {
  return OUTLINE_ALPHA + (1 - OUTLINE_ALPHA) * clamp01(k);
}

/** 遮罩的雜湊（FNV-1a 32 位元，十六進位；外框貼圖的快取鍵用）。 */
export function bitsHash(bits: Uint8Array): string {
  let hsh = 0x811c9dc5;
  for (let i = 0; i < bits.length; i++) {
    hsh ^= bits[i] as number;
    hsh = Math.imul(hsh, 0x01000193) >>> 0;
  }
  return `${bits.length.toString(36)}.${hsh.toString(16)}`;
}
