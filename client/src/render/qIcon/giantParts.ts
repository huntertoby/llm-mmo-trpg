// 灰燼之心 3×3 的部位小圖與本體圖示（GB-4b A3；照 docs/art/sample/qBossGiantIcons.js 逐行搬，需求 docs/art/GB巨型頭目-移植需求.md 4）。
// 只放圖樣（±10 單位）；放進 48 格、外框、灰化、紅「×」、快取都走 `bossParts.ts`（和霧鎖真人同一套，需求 4.3 第 2 條）。
// - 熔岩噴口＝火山錐＋往上噴的熔岩舌；殼縫＝上下兩端缺 V 口的玄武岩板＋鋸齒熔岩縫；核心＝殼窩＋兩片掀開殼蓋上的七邊形晶體
//   （晶體自己包外框，後面一圈核心色光暈在外框之下＝`pre`）。玄武岩照規則 6 換亮一階（本色 `#7c6c62`）。
// - 本體＝灰燼之心整隻縮圖：取 `qBossGiant.ts` 的 `giantFill()`（第 2 階段・熔殼不在、不描外框、不帶金外光），裁整隻貼進 22.6 單位寬；
//   ≤32px 在裝置像素上做 alpha 門檻、暗色像素換亮一階、核心光加粗、前殼三隻甲蟲的火眼合成 1 px 熔岩色點（需求 4.2）。
// 沒有 DOM（vitest）時 `giantFill` 回傳 null，本體退回向量的玄武岩剪影（只為了測試畫得出來；正式畫面一定有 DOM）。
import { ASH } from "../qBoss";
import { giantFill, type GiantState } from "../qBossGiant";
import { blank, ci, el, glow, halo, ln, poly, TAU, type Ctx, type DrawFn, type Pt, type QOpts } from "./core";

/** 玄武岩（圖示用，換亮一階：第 1 稿 `#6a5a52` 本色時 20px 平均亮度 94，規則 6 要 100）。 */
const ROCK = "#7c6c62";
const ROCK_HI = "#9a8a7e";
const ROCK_SH = "#5e4e46";
const RIM = "#8a7a70";
const { LAVA, LAVA_HOT, EMBER, CORE } = ASH;

const path = (c: Ctx, pts: readonly Pt[]): void => {
  c.beginPath();
  pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
  c.closePath();
};

/** 熔岩噴口：火山錐＋口緣＋熔岩＋往上噴的熔岩舌（主色＋亮色＋白芯，規則 5）。 */
export function ventGlyph(c: Ctx, o: QOpts): void {
  c.save();
  c.translate(0, 0.6); // 第 1 稿錐身只佔 16×17／20（規則 7 要 70% 以上），加寬加高
  const cone = (q: Ctx): void => {
    q.beginPath();
    q.moveTo(-10.2, 9.2);
    q.quadraticCurveTo(-4.8, 4.4, -4.8, -1.6);
    q.lineTo(4.8, -1.6);
    q.quadraticCurveTo(4.8, 4.4, 10.2, 9.2);
    q.closePath();
  };
  c.fillStyle = ROCK;
  cone(c);
  c.fill();
  c.save();
  cone(c);
  c.clip();
  c.fillStyle = ROCK_HI;
  c.beginPath();
  c.moveTo(-11, 9.2);
  c.quadraticCurveTo(-5.6, 4, -5.4, -1.6);
  c.lineTo(-2.2, -1.6);
  c.quadraticCurveTo(-2.6, 4.2, -5.2, 9.2);
  c.closePath();
  c.fill(); // 左側亮面
  c.fillStyle = ROCK_SH;
  c.beginPath();
  c.moveTo(11, 9.2);
  c.quadraticCurveTo(5.4, 4, 5.2, -1.6);
  c.lineTo(3.2, -1.6);
  c.quadraticCurveTo(3.2, 4.6, 6.2, 9.2);
  c.closePath();
  c.fill(); // 右側暗面
  if (!o.small)
    for (const x of [-5, 0, 5]) {
      ci(c, RIM, x, 6.2, 2.6);
      ci(c, ROCK_HI, x - 0.7, 5.5, 1.0);
    } // 殼瓦（20px 省掉）
  c.fillStyle = LAVA;
  c.beginPath();
  c.moveTo(-3.0, -0.8);
  c.quadraticCurveTo(-3.6, 3.4, -2.1, 4.8);
  c.quadraticCurveTo(-1.0, 3.4, -1.0, -0.8);
  c.closePath();
  c.fill(); // 口緣溢出的熔岩（一道）
  c.restore();
  // 口緣與口裡的熔岩
  el(c, RIM, 0, -1.8, 5.9, 2.3);
  el(c, LAVA, 0, -1.7, 4.3, 1.4);
  // 熔岩舌（噴發）：從口往上，自己包外框（和錐身分開）
  halo(c, o, (x) => {
    x.fillStyle = LAVA;
    x.beginPath();
    x.moveTo(-3.4, -1.9);
    x.bezierCurveTo(-5.0, -6.2, -1.6, -8.4, 0.4, -11.2);
    x.bezierCurveTo(0.8, -8.6, 5.0, -6.4, 3.4, -1.9);
    x.closePath();
    x.fill();
    x.fillStyle = LAVA_HOT;
    x.beginPath();
    x.moveTo(-1.7, -2.1);
    x.bezierCurveTo(-2.5, -5.2, -0.6, -6.8, 0.3, -8.6);
    x.bezierCurveTo(0.7, -6.6, 2.5, -5.2, 1.7, -2.1);
    x.closePath();
    x.fill();
    if (!o.tiny) ci(x, "#ffffff", -0.1, -4.4, 0.9);
  });
  c.restore();
}

/** 殼板：上下兩端在熔岩縫出口各缺一個 V 口（剪影是「裂開的石板」，和核心、本體分得開，規則 11）。 */
const SLAB: readonly Pt[] = [
  [-6.4, -9.2],
  [-2.4, -9.6],
  [0.6, -4.6],
  [3.4, -9.8],
  [4.6, -9.6],
  [8.6, -4.4],
  [8.2, 6.6],
  [3.6, 9.6],
  [2.4, 9.8],
  [-0.2, 5.4],
  [-2.8, 9.8],
  [-6.0, 9.4],
  [-8.8, 4.4],
  [-8.6, -5.2],
];
const CRACK: readonly Pt[] = [
  [0.6, -10.4],
  [-1.9, -5.4],
  [1.7, -1.6],
  [-1.6, 2.6],
  [1.8, 6.4],
  [-0.2, 10.4],
];

/** 殼縫：玄武岩殼板＋上下貫穿的鋸齒熔岩縫（同身上 seam：暗紅寬邊、熔岩、黃芯）＋一條分岔。 */
export function seamGlyph(c: Ctx, o: QOpts): void {
  poly(c, ROCK, SLAB, 1.2);
  c.save();
  path(c, SLAB);
  c.clip();
  poly(c, ROCK_HI, [
    [-9.6, -10.4],
    [-1.4, -10.6],
    [-4.2, -4.8],
    [-6.4, 1.4],
    [-9.8, 2.6],
  ]); // 左上亮面
  poly(c, ROCK_SH, [
    [9.6, -1.6],
    [9.6, 10.6],
    [3.2, 10.6],
    [6.2, 4.4],
  ]); // 右下暗面
  // 熔岩縫：暗紅寬邊 → 熔岩 → 黃芯（20px 黃芯照畫，是這個圖示的亮面）
  const br: Pt[] = [
    [1.7, -1.6],
    [6.0, -3.6],
    [9.6, -2.6],
  ];
  ln(c, EMBER, 4.4, CRACK);
  ln(c, EMBER, 3.0, br);
  ln(c, LAVA, 2.8, CRACK);
  ln(c, LAVA, 1.6, br);
  ln(c, LAVA_HOT, o.small ? 1.3 : 1.0, CRACK.slice(1, 5));
  c.restore();
}

/** 晶體（qBoss `core()` 的七邊形 CORE_PTS，縮 0.66、上移 1.6）。 */
const CORE_PTS: readonly Pt[] = (
  [
    [0, -15],
    [10, -8],
    [11, 4],
    [4, 13],
    [-6, 12],
    [-11, 3],
    [-9, -9],
  ] as const
).map(([x, y]) => [x * 0.66, y * 0.66 - 1.6] as const);

/** 核心：殼窩（玄武岩下半圈）＋兩片掀開的殼蓋＋晶體（自己包外框）；光暈在外框底下（`coreGlyphPre`）。 */
export function coreGlyph(c: Ctx, o: QOpts): void {
  const P = CORE_PTS;
  c.fillStyle = ROCK;
  c.beginPath();
  c.ellipse(0, 4.6, 9.4, 5.2, 0, 0, Math.PI);
  c.lineTo(-9.4, 2.6);
  c.quadraticCurveTo(0, 5.4, 9.4, 2.6);
  c.closePath();
  c.fill();
  c.fillStyle = ROCK_HI;
  c.beginPath();
  c.ellipse(-4.6, 6.4, 3.6, 1.5, -0.25, 0, TAU);
  c.fill();
  for (const s of [-1, 1])
    poly(
      c,
      RIM,
      [
        [s * 6.6, 3.4],
        [s * 9.8, -3.6],
        [s * 10.2, 1.4],
        [s * 9.6, 4.4],
      ],
      0.6,
    );
  halo(c, o, (x) => {
    poly(x, CORE, P, 0.3);
    poly(x, "#ffd98a", [P[0]!, P[6]!, P[5]!, [0.66, -1.6]]); // 左上亮面
    poly(x, "#e8962a", [P[2]!, P[3]!, [0.66, -1.6]]); // 右下暗面
    x.fillStyle = "#ffffff";
    x.fillRect(-3.4, -7.6, 1.6, o.small ? 3.4 : 3.0);
    if (!o.tiny) x.fillRect(-1.4, -8.8, 1.1, 1.1);
  });
}

/** 核心的光暈（48 格座標，畫在外框底下）。 */
export const coreGlyphPre: DrawFn = (c) => glow(c, 24, 21, 19, CORE, 0.55);

// ---------------- 本體：灰燼之心整隻縮圖（需求 4.2） ----------------

/**
 * 本體圖示的參數（樣張 `BODY`）：暗色像素提亮倍數、取哪一個外觀、裁切框（模型 px：x, y, w, h）、圖樣寬（單位）、
 * 填色層解析度、核心與三顆火眼的位置（模型 px）。
 */
export const GIANT_BODY = {
  lift: 1.25,
  /** 第 2 階段・熔殼不在（殼蓋掀開、核心露出）；`t` 照樣張 300 ms（呼吸的那一刻）。 */
  st: { phase: 2, shell: 0, breakT: 1, t: 300 } as GiantState,
  box: [-78, -159, 156, 160] as const,
  span: 22.6,
  z: 6,
  core: [0, -73] as const,
  eyes: [
    [-47, -15],
    [0, -14],
    [47, -15],
  ] as const,
} as const;

/** 暗色像素換亮一階（規則 6）：不透明、亮度 < 120 的像素 RGB ×1.25＋6（四捨五入、上限 255）。原地修改 RGBA 陣列。 */
export function liftDarkPixels(d: Uint8ClampedArray | number[]): void {
  for (let i = 0; i < d.length; i += 4) {
    if (!d[i + 3]) continue;
    const lum = 0.299 * d[i]! + 0.587 * d[i + 1]! + 0.114 * d[i + 2]!;
    if (lum < 120) for (let j = 0; j < 3; j++) d[i + j] = Math.min(255, Math.round(d[i + j]! * GIANT_BODY.lift + 6));
  }
}

type Fill = NonNullable<ReturnType<typeof giantFill>>;
let bodyCache: Fill | null | undefined;
const bodyFill = (): Fill | null => {
  if (bodyCache === undefined) bodyCache = giantFill(GIANT_BODY.st, GIANT_BODY.z);
  return bodyCache;
};

/** 沒有 DOM 時的本體（測試用）：玄武岩圓頂＋核心一點。 */
function bodyFallback(c: Ctx): void {
  c.fillStyle = ROCK;
  c.beginPath();
  c.ellipse(0, 2, 10, 8, 0, Math.PI, 0);
  c.lineTo(10, 8);
  c.lineTo(-10, 8);
  c.closePath();
  c.fill();
  ci(c, CORE, 0, -1, 2.2);
}

/** 本體圖樣（樣張 `bodyGlyph`，座標 ±10）。 */
export function giantBodyGlyph(c: Ctx, o: QOpts): void {
  const F = bodyFill();
  if (F === null) {
    bodyFallback(c);
    return;
  }
  const [bx, by, bw, bh] = GIANT_BODY.box;
  const span = GIANT_BODY.span;
  const k = span / bw;
  const put = (g: Ctx): void => {
    g.imageSmoothingEnabled = true;
    g.imageSmoothingQuality = "high";
    g.drawImage(F.canvas, F.ox + bx * F.z, F.oy + by * F.z, bw * F.z, bh * F.z, -span / 2, -(bh * k) / 2, span, bh * k);
  };
  if (48 / o.u > 32) {
    c.save();
    put(c);
    c.restore();
    return; // >32px：向量
  }
  // ≤32px：裝置像素
  const Mg = c.getTransform();
  const Md = Mg.translate(-span / 2 - bx * k, -(bh * k) / 2 - by * k).scale(k, k); // 模型 px → 裝置像素
  const W = c.canvas.width;
  const Hh = c.canvas.height;
  const L = blank(W, Hh);
  const lg = L.getContext("2d", { willReadFrequently: true });
  if (lg === null) return;
  lg.setTransform(Mg);
  put(lg);
  const img = lg.getImageData(0, 0, W, Hh);
  const d = img.data;
  for (let i = 3; i < d.length; i += 4) d[i] = d[i]! >= 128 ? 255 : 0; // a：alpha 門檻
  if (o.flat !== true) liftDarkPixels(d); // a2：玄武岩換亮一階（只動暗色像素，熔岩、核心不變）
  lg.putImageData(img, 0, 0);
  if (o.small && o.flat !== true) {
    const dp = Math.max(1, Math.round(W / (48 / o.u))); // 裝置像素／CSS px（20px res1＝1、res2＝2）
    const at = (mx: number, my: number): [number, number] => {
      const p = Md.transformPoint(new DOMPoint(mx, my));
      return [p.x, p.y];
    };
    lg.setTransform(1, 0, 0, 1, 0, 0);
    const [cx, cy] = at(...GIANT_BODY.core);
    lg.save();
    lg.fillStyle = LAVA_HOT;
    for (const [r, al] of [
      [3.6, 0.3],
      [2.6, 0.4],
    ] as const) {
      lg.globalAlpha = al;
      lg.beginPath();
      lg.arc(cx, cy, r * dp, 0, TAU);
      lg.fill();
    }
    lg.restore(); // b：核心柔光
    const bw2 = 2 * dp;
    const bh2 = 3 * dp;
    const x0 = Math.round(cx - bw2 / 2);
    const y0 = Math.round(cy - bh2 / 2);
    lg.fillStyle = CORE;
    lg.fillRect(x0, y0, bw2, bh2);
    lg.fillStyle = "#fff4d0";
    lg.fillRect(x0, y0, dp, dp); // b：晶體塊、左上 1 px 亮點
    lg.fillStyle = LAVA;
    for (const [ex, ey] of GIANT_BODY.eyes) {
      const [x, y] = at(ex, ey);
      lg.fillRect(Math.round(x - dp / 2), Math.round(y - dp / 2), dp, dp);
    } // c：火眼
  }
  c.save();
  c.setTransform(1, 0, 0, 1, 0, 0);
  c.drawImage(L, 0, 0);
  c.restore();
}

// ---------------- 對照表 ----------------

/** 巨型頭目的範本（本體列用灰燼之心整隻縮圖，不用霧鎖真人的頭像）。 */
export const GIANT_BOSS_TEMPLATE = "ashen_heart";

/** 一個部位圖樣：名稱、圖樣（±10 單位）、外框底下的光暈（48 格座標）。 */
export interface GiantGlyph {
  zh: string;
  d: DrawFn;
  pre?: DrawFn;
}

/** 伺服器部位 ID（`content/units/ashen_heart.yaml`）→ 圖樣。樣張的 `seam` 在伺服器叫 `shell_seam`。 */
export const GIANT_PART_GLYPH: Readonly<Record<string, GiantGlyph>> = {
  vent: { zh: "熔岩噴口", d: ventGlyph },
  shell_seam: { zh: "殼縫", d: seamGlyph },
  core: { zh: "核心", d: coreGlyph, pre: coreGlyphPre },
};

/** 部位 ID 清單（伺服器順序依 ID 排序：core、shell_seam、vent）。 */
export const GIANT_PART_IDS: readonly string[] = Object.keys(GIANT_PART_GLYPH).sort();

/** 本體圖樣（樣張 `GLYPH.body`）。 */
export const GIANT_BODY_GLYPH: GiantGlyph = { zh: "本體", d: giantBodyGlyph };

/** 測試用：清掉本體填色層的快取。 */
export function clearGiantBodyFill(): void {
  bodyCache = undefined;
}
