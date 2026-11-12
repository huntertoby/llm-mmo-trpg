// 頭目部位的小圖示（PB-1c；照 docs/art/sample/bossParts.js 第 2 版逐行搬，需求 docs/art/頭目部位-移植需求.md 1.1、1.4、2.1、3.1）。
// 用在選部位小選單（`ui/PartMenu.tsx`）每列名稱左邊的 20px 圖示，與角色卡的部位列（`ui/UnitInfo.tsx`）。
// - 圖樣畫在 ±10 單位，48 格裡放大 1.8 倍（同 `parts.ts` 的 `def`），外框照 `outlinePx`，2 倍內部解析度、貼整數裝置像素（樣張 `icon()`）。
// - 拂塵 `whiskGlyph`、氣海 `dantianGlyph` 是新畫的（第 2 版）；長劍＝第④批 `COND.wielding_weapon`；原因「從背後」＝`COND.from_behind`。
// - 本體＝霧鎖真人小頭像（1.4）：頭目 doll 用遊戲端 Q 版紙娃娃 `drawQ` 畫正面（不描外框、不帶傳說外光、不帶頭像配件、拿掉主手副手），
//   裁頭肩、縮進圖示格；≤32px alpha 門檻、≤24px 鬍子下緣暗面＋實心方眼（樣張 `PORTRAIT`、`bossFill`、`portraitGlyph`）。
// - 打不到、還沒露出：`grayIcon`（去色＋亮度 0.8＋透明度 0.45，樣張 `gray()`）。已破壞的紅「×」由呼叫端（CSS／畫布）壓在上面。
// 沒有 DOM（vitest）時 `bossPartIcon` 回傳 null；`setQCanvasFactory` 換假畫布時只測得到向量部分（頭像需要 `getImageData`）。
import { resolveDoll, type DollInput } from "../appearance";
import { drawQ } from "../qDoll";
import { GAME_HOOKS, qUnitOf } from "../qSpec";
import { blank, ci, ctxOf, halo, ln, outlinePx, qCanvasAvailable, render, rr, type Ctx, type QDef, type QOpts } from "./core";
import { bust, COND } from "./parts";

/** 米白（同第④批 `CREAM`）。 */
const CREAM = "#f2e6c8";

/** 拂塵（第 2 版）：柄短、斜在左上；毛從金箍往下甩成一條 S 形的長流線，根部寬、尾端收尖，尾端分出一綹細毛。 */
export function whiskGlyph(c: Ctx, o: QOpts): void {
  c.save();
  c.translate(0.3, 0);
  c.scale(0.88, 0.88); // 整支縮 12%（不縮時外接 16×20，上下貼到 20 格邊）
  const F: [number, number] = [-3.4, -5.0];
  const Hd: [number, number] = [-9.8, -11.2]; // 金箍、柄尾
  const B: [number, number][] = [
    [-2.6, -4.0],
    [11.2, -4.2],
    [-9.2, 4.6],
    [6.4, 11.6],
  ]; // 毛的中心線（三次貝茲）
  const at = (t: number): [number, number] => {
    const u = 1 - t;
    const k = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t];
    return [0, 1].map((j) => B.reduce((s, p, i) => s + p[j]! * k[i]!, 0)) as [number, number];
  };
  const N = 28;
  const L: [number, number][] = [];
  const R: [number, number][] = [];
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const p = at(t);
    const q = at(Math.min(1, t + 0.01));
    const p0 = at(Math.max(0, t - 0.01));
    const dx = q[0] - p0[0];
    const dy = q[1] - p0[1];
    const l = Math.hypot(dx, dy) || 1;
    const w = 3.7 * Math.pow(1 - t, 0.7) + 0.2;
    const nx = -dy / l;
    const ny = dx / l;
    L.push([p[0] + nx * w, p[1] + ny * w]);
    R.push([p[0] - nx * w, p[1] - ny * w]);
  }
  const plume = (q: Ctx): void => {
    q.beginPath();
    L.forEach(([x, y], i) => (i ? q.lineTo(x, y) : q.moveTo(x, y)));
    for (let i = R.length - 1; i >= 0; i--) q.lineTo(R[i]![0], R[i]![1]);
    q.closePath();
  };
  const strand = (q: Ctx): void => {
    const s = at(0.62);
    const e = [s[0] - 4.4, s[1] + 5.2] as const;
    q.beginPath();
    q.moveTo(s[0] - 1.2, s[1] - 1.0);
    q.quadraticCurveTo(s[0] - 3.6, s[1] + 1.8, e[0], e[1]);
    q.quadraticCurveTo(s[0] - 1.8, s[1] + 2.6, s[0] + 0.6, s[1] + 0.8);
    q.closePath();
  };
  c.fillStyle = "#f2f0ea";
  plume(c);
  c.fill();
  strand(c);
  c.fill();
  if (!o.tiny) {
    c.save();
    plume(c);
    c.clip();
    c.strokeStyle = "#c8c4b8";
    c.lineWidth = 2.4;
    c.lineJoin = "round";
    c.beginPath();
    R.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
    c.stroke(); // 暗面：沿右緣
    c.strokeStyle = "#ffffff";
    c.lineWidth = 1.5;
    c.beginPath();
    L.slice(2, 15).forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
    c.stroke(); // 亮面：左上緣
    c.strokeStyle = "#b8b2a4";
    c.lineWidth = o.small ? 0.9 : 0.7;
    c.lineCap = "round";
    c.beginPath();
    for (let i = 3; i <= 22; i++) {
      const p = at(i / N);
      if (i === 3) c.moveTo(p[0], p[1]);
      else c.lineTo(p[0], p[1]);
    }
    c.stroke(); // 分綹線
    c.restore();
    c.fillStyle = "#c8c4b8";
    strand(c);
    c.fill();
  }
  // 柄：金箍往左上（握柄端在左上），亮一階的木色
  ln(c, "#a8703e", 2.7, [F, Hd]);
  if (!o.small)
    ln(c, "rgba(255,255,255,0.45)", 0.8, [
      [F[0] - 1.4, F[1] - 2.0],
      [Hd[0] + 0.6, Hd[1] + 0.2],
    ]);
  c.save();
  c.translate(F[0], F[1]);
  c.rotate(Math.atan2(Hd[1] - F[1], Hd[0] - F[0]) + Math.PI / 2);
  rr(c, "#e8bb48", -2.4, -1.5, 4.8, 3.2, 1.3);
  if (!o.tiny) rr(c, "#f6d878", -1.8, -1.1, 1.8, 1.1, 0.5);
  c.restore();
  c.restore();
}

/** 氣海（第 2 版）：米白人形（同本體占位的 bust）＋下腹一團亮青氣團（自己包一圈外框），兩條逗號形的氣尾往左右甩出人形外。 */
export function dantianGlyph(c: Ctx, o: QOpts): void {
  const gx = 0;
  const gy = 4.6;
  bust(c, CREAM, 0, 0.0, 1.32);
  const tail = (q: Ctx): void => {
    q.beginPath();
    q.moveTo(gx + 1.6, gy - 3.0);
    q.bezierCurveTo(gx + 6.4, gy - 6.8, gx + 10.8, gy - 4.6, gx + 10.6, gy + 0.2);
    q.bezierCurveTo(gx + 9.6, gy - 3.4, gx + 6.4, gy - 4.4, gx + 3.4, gy - 1.6);
    q.closePath();
  };
  halo(c, o, (x) => {
    for (const rot of [0, Math.PI]) {
      x.save();
      x.translate(gx, gy);
      x.rotate(rot);
      x.translate(-gx, -gy);
      x.fillStyle = "#3fb8a8";
      tail(x);
      x.fill();
      if (!o.small) {
        x.fillStyle = "#8ff0e0";
        x.translate(gx, gy);
        x.scale(0.9, 0.62);
        x.translate(-gx, -gy);
        tail(x);
        x.fill();
      }
      x.restore();
    } // 兩條逗號形氣尾（中心對稱，像在轉）
    ci(x, "#3fb8a8", gx, gy, 4.1);
    ci(x, "#8ff0e0", gx - 0.4, gy - 0.4, 2.9);
    ci(x, "#ffffff", gx - 0.7, gy - 0.7, 1.5);
  });
}

/** 本體的米白人形（第 1、2 版占位，樣張 `bodyV1`）：沒有頭目外觀時退回它。 */
export function bodyV1Glyph(c: Ctx): void {
  bust(c, CREAM, 0, 1.2, 1.32);
}

// ---------------- 本體：頭目小頭像（1.4） ----------------

/** 頭像的參數（樣張 `PORTRAIT`）：裁切框（紙娃娃座標 x, y, w, h）、離屏解析度、眼睛矩形、鬍子暗面。 */
export const PORTRAIT = {
  box: [-12.8, -40.4, 25.6, 28] as const,
  dpr: 12,
  eyeW: 2.6,
  eyeH: 3.6,
  eyeX: -2.9,
  eyeY: -30.4,
  beardShade: "#bbbbbb",
  beardFromY: -21,
  eye: "#1d1a22",
} as const;
/** 樣張 `QNpc.BOX`：紙娃娃畫布 128×112、腳底離下緣 14（只用來對齊樣張的像素格）。 */
const BOX = { W: 128, H: 112, FOOT: 14 } as const;
/** raceArt.js face() 的大鬍子（正面）原樣照抄。 */
const BEARD = (q: Ctx): void => {
  q.moveTo(-7, -27);
  q.quadraticCurveTo(-7, -18, 0, -16);
  q.quadraticCurveTo(7, -18, 7, -27);
  q.quadraticCurveTo(0, -23, -7, -27);
  q.closePath();
};

/** 頭目的紙娃娃輸入（`UnitView` 的範本、外觀、武器）。 */
export type BossDoll = Pick<DollInput, "template" | "dollLook" | "weaponId" | "weaponClass">;

interface Fill {
  canvas: HTMLCanvasElement;
  ox: number;
  oy: number;
  D: number;
}
const fills = new Map<string, Fill | null>();

/**
 * 頭目正面的本體圖層（樣張 `bossFill`：`QDoll.stamp` 不描外框＝遊戲端 `drawQ`）：1 紙娃娃單位＝`PORTRAIT.dpr` px，
 * 只畫裁切框那一塊（像素格和樣張的整張 128×112 畫布對齊）。頭像不拿手持物（劍刃、拂塵毛會從框角伸進來）。
 */
function bossFill(doll: BossDoll): Fill | null {
  const key = JSON.stringify(doll);
  const hit = fills.get(key);
  if (hit !== undefined) return hit;
  if (typeof document === "undefined") return null;
  const D = PORTRAIT.dpr;
  const [bx, by, bw, bh] = PORTRAIT.box;
  const fx = (BOX.W / 2) * D;
  const fy = (BOX.H - BOX.FOOT) * D;
  const x0 = Math.floor(fx + bx * D);
  const y0 = Math.floor(fy + by * D);
  const spec = resolveDoll({ ...doll, team: "enemy", summon: false });
  const gear = { ...spec.gear };
  delete gear.main_hand;
  delete gear.off_hand;
  const unit = qUnitOf({ ...spec, gear });
  const c = blank(Math.ceil(bw * D) + 2, Math.ceil(bh * D) + 2);
  const g = ctxOf(c);
  g.translate(fx - x0, fy - y0);
  g.scale(D, D);
  drawQ(g, unit, "front", GAME_HOOKS, null, false);
  const out = { canvas: c, ox: fx - x0, oy: fy - y0, D };
  fills.set(key, out);
  return out;
}

/** 頭像第 4 步：alpha ≥128 改成 255、其餘改成 0（顏色不動；原地修改 RGBA 陣列）。 */
export function alphaThreshold(d: Uint8ClampedArray | number[]): void {
  for (let i = 3; i < d.length; i += 4) d[i] = d[i]! >= 128 ? 255 : 0;
}

/**
 * 頭像第 5 步之一：鬍子下緣 V 形 1 裝置 px 暗面——y ≥ `y0` 的範圍內，自己在鬍子遮罩裡且不透明、正下方一格不在鬍子遮罩裡
 * 但不透明的像素改成 `PORTRAIT.beardShade`。
 */
export function shadeBeardEdge(d: Uint8ClampedArray | number[], W: number, H: number, inBeard: (x: number, y: number) => boolean, y0: number): void {
  const sh = [0, 1, 2].map((j) => parseInt(PORTRAIT.beardShade.slice(1 + 2 * j, 3 + 2 * j), 16));
  for (let y = Math.max(0, y0); y < H - 1; y++)
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      const j = i + W * 4;
      if (inBeard(x, y) && d[i + 3] && !inBeard(x, y + 1) && d[j + 3]) {
        d[i] = sh[0]!;
        d[i + 1] = sh[1]!;
        d[i + 2] = sh[2]!;
      }
    }
}

/** 一塊方眼（裝置像素）。 */
export interface EyeBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * 頭像第 5 步之二：左眼矩形的兩個角（裝置像素，小數）→ 兩塊方眼：寬高各 max(2, round)、左上 round(中心 − 一半)；
 * 右眼＝左眼對畫布中線（寬 `W`）的鏡像。
 */
export function eyeBoxes(p0: { x: number; y: number }, p1: { x: number; y: number }, W: number): [EyeBox, EyeBox] {
  const w = Math.max(2, Math.round(p1.x - p0.x));
  const h = Math.max(2, Math.round(p1.y - p0.y));
  const x = Math.round((p0.x + p1.x) / 2 - w / 2);
  const y = Math.round((p0.y + p1.y) / 2 - h / 2);
  return [
    { x, y, w, h },
    { x: W - x - w, y, w, h },
  ];
}

/** 方眼填實心 `#1d1a22`（alpha 255）。 */
export function paintEyes(d: Uint8ClampedArray | number[], W: number, boxes: readonly EyeBox[]): void {
  for (const b of boxes)
    for (let y = b.y; y < b.y + b.h; y++)
      for (let x = b.x; x < b.x + b.w; x++) {
        const i = (y * W + x) * 4;
        d[i] = 0x1d;
        d[i + 1] = 0x1a;
        d[i + 2] = 0x22;
        d[i + 3] = 255;
      }
}

/**
 * 紙娃娃座標 → 圖示畫布的裝置像素（顯示邊長 `px`、內部解析度 `res`）：圖樣 ±10 在 48 格裡放大 1.8、置中，
 * 裁切框寬 25.6 對到 20 圖樣單位、上下置中（樣張 `Md`）。回傳仿射 [a, d, e, f]（沒有旋轉、x、y 各自縮放）。
 */
export function portraitDeviceMap(px: number, res: number): { a: number; d: number; e: number; f: number } {
  const S = Math.max(4, Math.round(px * res));
  const g = (S / 48) * 1.8; // 圖樣單位 → 裝置像素
  const [bx, by, bw, bh] = PORTRAIT.box;
  const k = 20 / bw;
  return { a: g * k, d: g * k, e: (S / 48) * 24 + g * (-10 - bx * k), f: (S / 48) * 24 + g * (-(bh * k) / 2 - by * k) };
}

/** 頭像的圖樣（樣張 `portraitGlyph`，座標 ±10）。 */
function portraitGlyph(doll: BossDoll): (c: Ctx, o: QOpts) => void {
  return (c, o) => {
    const F = bossFill(doll);
    if (F === null) {
      bodyV1Glyph(c);
      return;
    }
    const [bx, by, bw, bh] = PORTRAIT.box;
    const k = 20 / bw;
    const draw = (g: Ctx): void => {
      g.imageSmoothingEnabled = true;
      g.imageSmoothingQuality = "high";
      g.drawImage(F.canvas, F.ox + bx * F.D, F.oy + by * F.D, bw * F.D, bh * F.D, -10, -(bh * k) / 2, 20, bh * k);
    };
    if (48 / o.u > 32) {
      c.save();
      draw(c);
      c.restore();
      return; // >32px：向量
    }
    // ≤32px：裝置像素
    const Mg = c.getTransform();
    const Md = Mg.translate(-10 - bx * k, -(bh * k) / 2 - by * k).scale(k, k); // 紙娃娃座標 → 裝置像素
    const W = c.canvas.width;
    const H = c.canvas.height;
    const L = blank(W, H);
    const lg = L.getContext("2d", { willReadFrequently: true });
    if (lg === null) return;
    lg.setTransform(Mg);
    draw(lg);
    const img = lg.getImageData(0, 0, W, H);
    const d = img.data;
    alphaThreshold(d); // a
    if (o.small && o.flat !== true) {
      // b：鬍子下緣暗面
      const Bc = blank(W, H);
      const bg = Bc.getContext("2d", { willReadFrequently: true });
      if (bg === null) return;
      bg.setTransform(Md);
      bg.fillStyle = "#fff";
      bg.beginPath();
      BEARD(bg);
      bg.fill();
      const bd = bg.getImageData(0, 0, W, H).data;
      const inB = (x: number, y: number): boolean => x >= 0 && y >= 0 && x < W && y < H && bd[(y * W + x) * 4 + 3]! >= 128;
      const y0 = Math.ceil(Md.transformPoint(new DOMPoint(0, PORTRAIT.beardFromY)).y);
      shadeBeardEdge(d, W, H, inB, y0);
      // c：眼睛矩形（紙娃娃座標）→ 裝置像素取整；右眼＝左眼對中線的鏡像
      const p0 = Md.transformPoint(new DOMPoint(PORTRAIT.eyeX - PORTRAIT.eyeW / 2, PORTRAIT.eyeY));
      const p1 = Md.transformPoint(new DOMPoint(PORTRAIT.eyeX + PORTRAIT.eyeW / 2, PORTRAIT.eyeY + PORTRAIT.eyeH));
      paintEyes(d, W, eyeBoxes(p0, p1, W));
    }
    lg.putImageData(img, 0, 0);
    c.save();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.drawImage(L, 0, 0);
    c.restore();
  };
}

// ---------------- 圖示 ----------------

/** 部位 ID → 圖樣（霧鎖真人三個部位；其他部位退回米白人形，待美術補）。 */
const PART_GLYPH: Readonly<Record<string, (c: Ctx, o: QOpts) => void>> = {
  whisk: whiskGlyph,
  dantian: dantianGlyph,
  sword: (c, o) => COND["wielding_weapon"]!.d(c, o),
};

/** 原因「從背後」的小圖（第④批 `COND.from_behind`）。 */
export const BACK_ICON = "back";

/** 一個圖樣放進 48 格（放大 1.8，同 `QIconsParts.def`）。 */
function cell(d: (c: Ctx, o: QOpts) => void): QDef {
  return {
    d: (c, o) => {
      c.save();
      c.translate(24, 24);
      c.scale(1.8, 1.8);
      d(c, o);
      c.restore();
    },
  };
}

function glyphOf(id: string, doll: BossDoll | null): (c: Ctx, o: QOpts) => void {
  if (id === "body") return doll === null ? (c) => bodyV1Glyph(c) : portraitGlyph(doll);
  if (id === BACK_ICON) return (c, o) => COND["from_behind"]!.d(c, o);
  return PART_GLYPH[id] ?? ((c) => bodyV1Glyph(c));
}

const icons = new Map<string, HTMLCanvasElement | null>();

/** 快取鍵：圖示（部位 ID 或 `body`、`back`）、頭目外觀（只有本體用）、顯示邊長、內部解析度。 */
export function bossPartIconKey(id: string, px: number, res: number, doll: BossDoll | null = null): string {
  return `${id}|${px}|${res}|${id === "body" && doll !== null ? JSON.stringify(doll) : ""}`;
}

/**
 * 部位圖示（樣張 `icon()`）：px＝顯示邊長（CSS px），res＝內部解析度；回傳 round(px×res) 的畫布（沒有 DOM 時 null）。
 * `body` 用頭目小頭像（`doll` 是頭目的紙娃娃輸入；沒給時退回米白人形）。
 */
export function bossPartIcon(id: string, px: number, res: number, doll: BossDoll | null = null): HTMLCanvasElement | null {
  if (!qCanvasAvailable()) return null;
  const key = bossPartIconKey(id, px, res, doll);
  const hit = icons.get(key);
  if (hit !== undefined) return hit;
  const cv = render(cell(glyphOf(id, doll)), px, res, { ow: px <= 14 ? 0 : outlinePx(px) });
  icons.set(key, cv);
  return cv;
}

/** 頭目小頭像（需求 1.4 的匯出名）：`bossPartIcon("body", …)`。 */
export function bossPortraitIcon(doll: BossDoll, px: number, res: number): HTMLCanvasElement | null {
  return bossPartIcon("body", px, res, doll);
}

/** 灰掉（打不到、還沒露出、已破壞）：去色、亮度 0.8、透明度 `a`（樣張 `gray()`）。 */
export function grayIcon(cv: HTMLCanvasElement, a = 0.45): HTMLCanvasElement {
  const c = blank(cv.width, cv.height);
  const x = ctxOf(c);
  x.filter = "grayscale(1) brightness(0.8)";
  x.globalAlpha = a;
  x.drawImage(cv, 0, 0);
  return c;
}

/** 測試用：清掉快取。 */
export function clearBossPartIcons(): void {
  icons.clear();
  fills.clear();
}
