// Q 版畫法層（QK-1 第 1 項；照 docs/art/sample/qDoll.js 的 stamp）：純色填色＋剪影外框。
// 離屏畫一次小人 → 剪影 → 圓盤膨脹（第 14 版：沿 12 個方向各做一次短線段膨脹，合成近似半徑 1.3 單位的圓盤）→ 外框色 → 小人貼在上面。
// 拿弓的人物（背面除外）外框再做一次閉合（先膨脹 1.5 再侵蝕 1.5），填掉弦和弓臂之間的窄縫。墨線的排線、筆觸都不畫。
import type { Ctx } from "./artDraw";
import { getM, Q_OUT, type QHooks, type QPose, type QUnit, type QView } from "./qCore";
import { drawQ } from "./qDoll";
import { qWeapon } from "./qWeapons";

/** 離屏畫布（單位）：128×112、腳下留 14（出招時長槍、法杖伸出去不被切掉）。 */
export const Q_BOX = { W: 128, H: 112, FOOT: 14 } as const;
/** 外框半徑（單位）。 */
export const Q_LINE = 1.3;

export interface QStampOpt {
  /** 離屏解析度倍數（預設 3）。 */
  dpr?: number;
  /** false：不畫外框。 */
  outline?: boolean;
  /** 外框閉合（預設：拿弓且不是背面）。 */
  close?: boolean;
}

type C2 = CanvasRenderingContext2D;

function canvas(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return c;
}

/** 剪影膨脹 r（離屏像素）：12 個方向各做一次 5 步的短線段膨脹（Minkowski 和），每一步都連續，細線和尖端外框是平滑的一圈。 */
function dilate(src: HTMLCanvasElement, r: number): HTMLCanvasElement {
  const N = 12;
  const a = (r * Math.PI) / (2 * N);
  const P = [canvas(src.width, src.height), canvas(src.width, src.height)];
  let cur: HTMLCanvasElement = src;
  let n = 0;
  for (let i = 0; i < N; i++) {
    const t = (Math.PI * i) / N;
    const ux = Math.cos(t) * a;
    const uy = Math.sin(t) * a;
    const c = P[n++ % 2]!;
    const g = c.getContext("2d")!;
    g.clearRect(0, 0, c.width, c.height);
    for (const f of [-1, -0.5, 0, 0.5, 1]) g.drawImage(cur, ux * f, uy * f);
    cur = c;
  }
  const o = canvas(src.width, src.height);
  o.getContext("2d")!.drawImage(cur, 0, 0);
  return o;
}

function tinted(src: HTMLCanvasElement, color: string): HTMLCanvasElement {
  const g = src.getContext("2d")!;
  g.globalCompositeOperation = "source-in";
  g.fillStyle = color;
  g.fillRect(0, 0, src.width, src.height);
  g.globalCompositeOperation = "source-over";
  return src;
}

function inverse(src: HTMLCanvasElement): HTMLCanvasElement {
  const c = canvas(src.width, src.height);
  const g = c.getContext("2d")!;
  g.fillStyle = "#000";
  g.fillRect(0, 0, c.width, c.height);
  g.globalCompositeOperation = "destination-out";
  g.drawImage(src, 0, 0);
  return c;
}

/** 有 DOM 才能做外框（vitest 的 node 環境沒有，直接畫填色）。 */
export const canStamp = (): boolean => typeof document !== "undefined" && typeof document.createElement === "function";

/**
 * 在 ctx 目前的座標系裡，把小人（腳底在 (0,0)、size 單位）連外框一起畫上去。
 * 解析度依 ctx 目前的縮放決定（× dpr 倍取樣再縮小貼上）；沒有 DOM 時直接畫填色、不畫外框。
 */
export function qStampLocal(ctx: Ctx, unit: QUnit, view: QView, west: boolean, hooks: QHooks, pose: QPose | null, opt: QStampOpt = {}): void {
  if (!canStamp()) {
    ctx.save();
    if (west) ctx.scale(-1, 1);
    drawQ(ctx, unit, view, hooks, pose, west);
    ctx.restore();
    return;
  }
  const m = getM(ctx);
  const k = Math.max(0.25, Math.hypot(m.a, m.b), Math.hypot(m.c, m.d));
  // 離屏至少 3 倍取樣（同樣張 stamp 的 dpr 3），低解析度直接膨脹會把外框糊成一圈灰霧；上限 12 倍
  const sc = Math.min(12, k * (opt.dpr ?? 3));
  const { W, H, FOOT } = Q_BOX;
  const off = canvas(W * sc, H * sc);
  const o = off.getContext("2d") as C2;
  o.scale(sc, sc);
  o.translate(W / 2, H - FOOT);
  if (west) o.scale(-1, 1);
  drawQ(o, unit, view, hooks, pose, west);
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  if (opt.outline !== false) {
    const sil = canvas(off.width, off.height);
    sil.getContext("2d")!.drawImage(off, 0, 0);
    tinted(sil, Q_OUT);
    const r = Q_LINE * sc;
    const close = opt.close ?? (qWeapon(unit.gear.main_hand)?.kind === "bow" && view !== "back");
    let line: HTMLCanvasElement;
    if (close) {
      const O = dilate(sil, r);
      const rc = 1.5 * sc;
      const cl = canvas(off.width, off.height);
      const g = cl.getContext("2d")!;
      g.drawImage(inverse(dilate(inverse(dilate(O, rc)), rc)), 0, 0);
      g.drawImage(O, 0, 0);
      line = tinted(cl, Q_OUT);
    } else line = tinted(dilate(sil, r), Q_OUT);
    ctx.drawImage(line, -W / 2, -(H - FOOT), W, H);
  }
  ctx.drawImage(off, -W / 2, -(H - FOOT), W, H);
  ctx.restore();
}

/** 樣張 stamp 的介面：在 (cx, cy) 貼一隻 size 倍的小人（closeups 的 3 倍特寫用 dpr 3）。 */
export function qStamp(ctx: Ctx, unit: QUnit, view: QView, cx: number, cy: number, size: number, west: boolean, hooks: QHooks, pose: QPose | null, opt: QStampOpt = {}): void {
  const dpr = opt.dpr ?? 3;
  const sc = size * dpr;
  if (!canStamp()) return;
  const { W, H, FOOT } = Q_BOX;
  const off = canvas(W * sc, H * sc);
  const o = off.getContext("2d") as C2;
  o.scale(sc, sc);
  o.translate(W / 2, H - FOOT);
  if (west) o.scale(-1, 1);
  drawQ(o, unit, view, hooks, pose, west);
  const sil = canvas(off.width, off.height);
  const s = sil.getContext("2d")!;
  s.drawImage(off, 0, 0);
  tinted(sil, Q_OUT);
  const k = Q_LINE * sc;
  const dx0 = cx - (W / 2) * size;
  const dy0 = cy - (H - FOOT) * size;
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  if (opt.outline === false) {
    /* 不畫外框（只用來比對外框以外的像素） */
  } else if (opt.close ?? (qWeapon(unit.gear.main_hand)?.kind === "bow" && view !== "back")) {
    const O = dilate(sil, k);
    const r = 1.5 * sc;
    const cl = canvas(off.width, off.height);
    const g = cl.getContext("2d")!;
    g.drawImage(inverse(dilate(inverse(dilate(O, r)), r)), 0, 0);
    g.drawImage(O, 0, 0);
    ctx.drawImage(tinted(cl, Q_OUT), dx0, dy0, W * size, H * size);
  } else ctx.drawImage(tinted(dilate(sil, k), Q_OUT), dx0, dy0, W * size, H * size);
  ctx.drawImage(off, dx0, dy0, W * size, H * size);
  ctx.restore();
}
