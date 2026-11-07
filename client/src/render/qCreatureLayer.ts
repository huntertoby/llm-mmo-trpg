// QK-4：異形、頭目的 Q 版畫法層（照 docs/art/sample/qCreature.js 的 layer）：離屏畫好平塗部件 → 剪影染外框色 → 膨脹 → 墊在底下。
// 和人形的 qStamp 不同：異形照樣張用 16 方向 × 3 圈的圓盤膨脹，另外有霧材質的 3 段淡出、頭目外光（剪影再膨脹的平塗光）、
// 受擊白閃（剪影染白）與整隻單色剪影（殘影）。沒有 DOM 時呼叫端不要呼叫（改直接平塗）。
import { TAU, type Ctx } from "./artDraw";

/** Q 版外框色（同 qDoll 的 OUT）。 */
export const QC_OUT = "#16121a";

export interface QLayerOpt {
  /** 外框粗（單位，預設 1.3）。 */
  ow?: number;
  /** 本體透明度（霧 0.62、霧隱 0.75、分身 0.35、動畫淡出）。 */
  alpha?: number;
  /** 頭目外光色：剪影再膨脹 `glowW` 單位、半透明平塗。 */
  glow?: string | null | undefined;
  glowW?: number;
  glowA?: number;
  /** 霧材質：[下緣 y, 開始淡出的 y]（單位），分 3 段平塗淡出，本體和外框一起。 */
  fade?: readonly [number, number] | null;
  /** 整隻剪影單色平塗（殘影用）。 */
  flat?: string;
  /** 受擊白閃強度（0～1）。 */
  flash?: number;
  flashColor?: string | undefined;
}

// 離屏畫布池：一層要 4～6 張同尺寸的暫用畫布，用完放回（同步呼叫，不會交錯）；不池化時大量格子會撞到瀏覽器的畫布記憶體上限。
const POOL: HTMLCanvasElement[] = [];
let lent: HTMLCanvasElement[] = [];
function mkc(w: number, h: number): HTMLCanvasElement {
  const c = POOL.pop() ?? document.createElement("canvas");
  c.width = Math.max(1, w); // 設寬高也會清空內容
  c.height = Math.max(1, h);
  lent.push(c);
  return c;
}
function giveBack(list: HTMLCanvasElement[]): void {
  for (const c of list) if (POOL.length < 24) POOL.push(c);
}

function tint(src: HTMLCanvasElement, color: string): HTMLCanvasElement {
  const c = mkc(src.width, src.height);
  const g = c.getContext("2d")!;
  g.drawImage(src, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = color;
  g.fillRect(0, 0, c.width, c.height);
  return c;
}

/** 圓盤膨脹：N 個方向 × 3 圈（1、0.66、0.33 倍半徑），同樣張。 */
function dilate(src: HTMLCanvasElement, r: number, N = 16): HTMLCanvasElement {
  const c = mkc(src.width, src.height);
  const g = c.getContext("2d")!;
  for (const f of [1, 0.66, 0.33])
    for (let i = 0; i < N; i++) {
      const a = (i / N) * TAU;
      g.drawImage(src, Math.cos(a) * r * f, Math.sin(a) * r * f);
    }
  g.drawImage(src, 0, 0);
  return c;
}

/** 有沒有 DOM（沒有時呼叫端直接平塗、不做外框）。 */
export const hasDom = (): boolean => typeof document !== "undefined";

/**
 * 在目前座標系的 box [x0, y0, x1, y1]（單位）裡畫一層：`draw(g)` 畫平塗部件；外框 `ow` 單位。
 * 離屏解析度跟著目前的變換走（getTransform）；鏡像由呼叫端的 scale(-1, 1) 處理。
 */
export function qLayer(ctx: Ctx, box: readonly [number, number, number, number], draw: (g: Ctx) => void, o: QLayerOpt = {}): void {
  const outer = lent;
  lent = [];
  try {
    layerInner(ctx, box, draw, o);
  } finally {
    giveBack(lent);
    lent = outer;
  }
}

function layerInner(ctx: Ctx, box: readonly [number, number, number, number], draw: (g: Ctx) => void, o: QLayerOpt): void {
  const T = ctx.getTransform();
  const m = Math.max(0.5, Math.hypot(T.a, T.b));
  const W = Math.ceil((box[2] - box[0]) * m);
  const H = Math.ceil((box[3] - box[1]) * m);
  if (!(W > 0 && H > 0 && W < 16384 && H < 16384)) {
    return; // 變換壞掉（NaN、過大）時不畫，不讓整張貼圖出錯
  }
  const off = mkc(W, H);
  const g = off.getContext("2d")!;
  g.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m);
  draw(g);
  const ow = (o.ow ?? 1.3) * m;
  const rim = dilate(tint(off, QC_OUT), ow);
  const rg = rim.getContext("2d")!;
  rg.globalCompositeOperation = "destination-out";
  rg.drawImage(off, 0, 0);
  if (o.fade != null) {
    const [yb, yt] = o.fade;
    for (const c of [off, rim]) {
      const q = c.getContext("2d")!;
      q.save();
      q.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m);
      q.globalCompositeOperation = "destination-out";
      [0.35, 0.65, 0.92].forEach((al, i) => {
        const y0 = yt + ((yb - yt) * i) / 3;
        const y1 = i === 2 ? box[3] : yt + ((yb - yt) * (i + 1)) / 3;
        q.globalAlpha = al;
        q.fillRect(box[0], y0, box[2] - box[0], y1 - y0);
      });
      q.restore();
    }
  }
  ctx.save();
  const put = (c: HTMLCanvasElement, a: number): void => {
    ctx.globalAlpha = a; // 同樣張：絕對值（呼叫端事先設的透明度不疊乘）
    ctx.drawImage(c, box[0], box[1], W / m, H / m);
  };
  if (o.flat !== undefined) {
    put(tint(off, o.flat), o.alpha ?? 1);
    ctx.restore();
    return;
  }
  if (o.glow != null) {
    const gl = dilate(tint(off, o.glow), ow + (o.glowW ?? 2.6) * m, 24);
    const gg = gl.getContext("2d")!;
    gg.globalCompositeOperation = "destination-out";
    gg.drawImage(off, 0, 0);
    put(gl, o.glowA ?? 0.6);
  }
  const a = o.alpha ?? 1;
  put(rim, a < 1 ? Math.min(1, a + 0.2 * Math.min(1, a * 5)) : 1); // 外框比本體實一點；本體淡到 0.2 以下時外框跟著淡
  put(off, a);
  if ((o.flash ?? 0) > 0) put(tint(off, o.flashColor ?? "#ffffff"), Math.min(1, o.flash ?? 0) * a);
  ctx.restore();
}
