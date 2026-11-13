// 頭目部位的「部位圖層」（PB-1e；美術移植需求 docs/art/頭目部位-移植需求.md 3.5、3.6）：照人物畫法直接畫出部位實際露出來的像素。
// 樣張是「部位換記號色、兩張相減」（因為不能改 qDoll.js）；遊戲端照移植需求改成由畫法直接給：
// - 照常畫一次小人（同一個姿勢、朝向、座標），但只有「正在畫那一件手持物」（`S.PAINT`，`qWeapons.mainWeapon`）時照常上色，
//   其他零件一律用 `destination-out` 挖掉——之後畫的手臂、身體會把底下的部位挖掉，所以被擋住的部分不算。
// - 同時記下那一件手持物的變換（`POSE.probe`）：裂紋、飛出去的碎塊、「破」的位置用。
// 氣海沒有實體零件：腹部中心（`qNpc.bellyAt`）。
// 畫布座標同 `paperdoll.renderFigureCanvas`：`w × h` 虛擬 px × `res`、腳底在 (w / 2, footY)，朝西整張鏡像。
import type { Facing } from "../api/types";
import type { DollSpec } from "./appearance";
import type { InkPose } from "./inkPose";
import { S, TAU, type M6, type QView } from "./qCore";
import { drawQ } from "./qDoll";
import { bellyAt, BELLY } from "./qNpc";
import { GAME_HOOKS, qPoseOf, qUnitOf } from "./qSpec";

type C2 = CanvasRenderingContext2D;

/** 部位 → 畫它的手持物 kind（氣海沒有）。 */
export const PART_KIND: Readonly<Record<string, string>> = { whisk: "whisk", sword: "sword" };

/** 畫布的大小與腳底（虛擬 px；同 `paperdoll` 的 DOLL_W／DOLL_H／DOLL_FOOT_Y）。 */
export interface FigureFrame {
  w: number;
  h: number;
  footY: number;
}

export const viewOf = (facing: Facing): QView => (facing === "north" ? "back" : facing === "south" ? "front" : "side");

/** 會上色的方法：只有「正在畫的手持物＝要的那一件」時照常畫，其他時候改成挖掉。 */
const PAINTS = new Set(["fill", "stroke", "fillRect", "strokeRect", "fillText", "strokeText", "drawImage"]);

/**
 * 把真的 2D context 包一層：上色時看 `active()` 決定照常（用畫法自己設的合成方式）或挖掉。
 * 合成方式另外記（含 save／restore 的堆疊），畫法讀到的永遠是它自己設的值。
 */
export function partPainter(real: C2, active: () => boolean): C2 {
  let gco = real.globalCompositeOperation;
  const stack: GlobalCompositeOperation[] = [];
  return new Proxy(real, {
    get(t, p) {
      if (p === "globalCompositeOperation") return gco;
      const v = Reflect.get(t, p, t) as unknown;
      if (typeof v !== "function") return v;
      const fn = v as (...a: unknown[]) => unknown;
      if (p === "save")
        return () => {
          stack.push(gco);
          t.save();
        };
      if (p === "restore")
        return () => {
          gco = stack.pop() ?? gco;
          t.restore();
        };
      if (typeof p === "string" && PAINTS.has(p))
        return (...a: unknown[]) => {
          t.globalCompositeOperation = active() ? gco : "destination-out";
          try {
            return fn.apply(t, a);
          } finally {
            t.globalCompositeOperation = gco;
          }
        };
      return fn.bind(t);
    },
    set(t, p, v) {
      if (p === "globalCompositeOperation") {
        gco = v as GlobalCompositeOperation;
        return true;
      }
      return Reflect.set(t, p, v, t);
    },
  });
}

/** 部位圖層：畫布（只有部位的像素，顏色照畫法）＋記下的手持物變換（畫布像素座標）。 */
export interface PartLayer {
  canvas: HTMLCanvasElement;
  /** 手持物 kind → 第一次畫它時的變換（畫布像素座標）。 */
  mats: Record<string, M6>;
}

function blankCanvas(w: number, h: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(w));
  c.height = Math.max(1, Math.round(h));
  return c;
}

/**
 * 畫部位圖層（沒有 DOM 時 `null`）。`part`＝whisk／sword；其他部位（氣海）只記變換、畫布是空的。
 * 氣海的氣旋、裂痕不畫進來（它們不描外框、是另一層）。
 */
export function renderPartLayer(spec: DollSpec, facing: Facing, part: string, res: number, frame: FigureFrame, pose: InkPose | null = null): PartLayer | null {
  const cv = blankCanvas(frame.w * res, frame.h * res);
  const ctx = cv?.getContext("2d") ?? null;
  if (cv === null || ctx === null) return null;
  const unit = qUnitOf(spec);
  delete unit.dantian;
  const west = facing === "west";
  const want = PART_KIND[part] ?? null;
  const mats: Record<string, M6> = {};
  const p0 = qPoseOf(pose);
  const qp = { ...(p0 ?? {}), probe: (kind: string, _h: unknown, _t: unknown, _v: unknown, _o: unknown, m: M6) => void (mats[kind] ??= m) };
  ctx.scale(res, res);
  ctx.translate(frame.w / 2, frame.footY);
  if (west) ctx.scale(-1, 1);
  const painter = partPainter(ctx, () => want !== null && S.PAINT === want);
  drawQ(painter, unit, viewOf(facing), GAME_HOOKS, qp, west);
  return { canvas: cv, mats };
}

/** 腹部中心在畫布像素的位置（站好的姿勢；朝西鏡像）。 */
export function bellyPx(facing: Facing, res: number, frame: FigureFrame): [number, number] {
  const [bx, by] = bellyAt(viewOf(facing));
  const x = facing === "west" ? -bx : bx;
  return [(frame.w / 2 + x) * res, (frame.footY + by) * res];
}

/** 一點（手持物座標）→ 畫布像素。 */
export function tpM(m: M6, x: number, y: number): [number, number] {
  return [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
}

/** 演出第 2 格的亮金白裂紋（手持物座標；樣張 `stamp` 的 crack）。 */
function crackLines(c: C2, part: string): void {
  c.strokeStyle = "#fff6c8";
  c.lineWidth = 0.55;
  c.lineCap = "round";
  c.beginPath();
  if (part === "sword") {
    c.moveTo(-1.2, -10.6);
    c.lineTo(-0.2, -9.6);
    c.lineTo(0.5, -10.4);
    c.lineTo(1.2, -9.8);
    c.moveTo(-0.1, -10);
    c.lineTo(0.3, -12.4);
  } else {
    c.moveTo(-0.9, -6.8);
    c.lineTo(-2.4, -5.8);
    c.lineTo(-3.2, -4.2);
    c.moveTo(-1.6, -6.4);
    c.lineTo(-3.8, -6.4);
  }
  c.stroke();
}

/** 把 `src` 的不透明處塗成單色。 */
function tinted(src: HTMLCanvasElement, color: string): HTMLCanvasElement {
  const c = blankCanvas(src.width, src.height);
  const g = c?.getContext("2d") ?? null;
  if (c === null || g === null) return src;
  g.drawImage(src, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = color;
  g.fillRect(0, 0, c.width, c.height);
  return c;
}

/** 部位白閃的峰值（樣張 partFlash 0.9）。 */
export const PART_FLASH = 0.9;

/**
 * 破壞演出前兩格疊在人物貼圖上（`renderFigureCanvas` 畫完、外光之前）：`flash`＝部位整塊白閃 0.9、`crack`＝亮金白裂紋。
 * 氣海：腹部橢圓和身體取交集（`source-atop`）。`o`＝人物畫布的 context（目前的變換不管，這裡一律用畫布像素）。
 */
export function paintPartFx(o: C2, spec: DollSpec, facing: Facing, res: number, frame: FigureFrame, pose: InkPose | null): void {
  const fx = spec.parts?.fx;
  if (fx === undefined) return;
  o.save();
  o.setTransform(1, 0, 0, 1, 0, 0);
  if (fx.part === "dantian") {
    const [x, y] = bellyPx(facing, res, frame);
    if (fx.k === "flash") {
      o.globalCompositeOperation = "source-atop";
      o.globalAlpha = PART_FLASH;
      o.fillStyle = "#ffffff";
      o.beginPath();
      o.ellipse(x, y, BELLY.rx * res, BELLY.ry * res, 0, 0, TAU);
      o.fill();
    } else {
      o.strokeStyle = "#f2fffc";
      o.lineWidth = 0.6 * res;
      o.lineCap = "round";
      o.beginPath();
      for (const a of [-0.6, 1.9, 3.6]) {
        const ax = facing === "west" ? Math.PI - a : a;
        o.moveTo(x, y);
        o.lineTo(x + Math.cos(ax) * 3.4 * res, y + Math.sin(ax) * 3.4 * res);
      }
      o.stroke();
    }
    o.restore();
    return;
  }
  const layer = renderPartLayer(spec, facing, fx.part, res, frame, pose);
  if (layer !== null) {
    if (fx.k === "flash") {
      o.globalAlpha = PART_FLASH;
      o.drawImage(tinted(layer.canvas, "#ffffff"), 0, 0);
    } else {
      const m = layer.mats[PART_KIND[fx.part] ?? ""];
      if (m !== undefined) {
        o.setTransform(m.a, m.b, m.c, m.d, m.e, m.f);
        crackLines(o, fx.part);
      }
    }
  }
  o.restore();
}
