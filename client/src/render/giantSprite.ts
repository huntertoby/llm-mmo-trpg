// GB-4b：3×3 巨型頭目（灰燼之心）在戰場上的地面與框（美術移植需求 docs/art/GB巨型頭目-移植需求.md 2.3、2.4）。
// 單位節點放在中心格中心（和一格的單位同一套座標），掛在南排那一列（`drawModel.unitRowOf`）；
// 貼圖錨點（南排南緣中點）＝節點往南 `GIANT_ANCHOR_DY`。這裡只放地面的東西與 3×3 的框，本體貼圖走 `inkCreature`（`qBossGiant.drawGiantFrame`）。
// - 陣營環（`giantGroundRing`）：南排的 `under`（`GIANT_RING_LABEL`）；
// - 第 3 階段坑底紅光（`giantGroundGlow`）：地面層、所有單位之前——紅光跨 4 排，切成每排一條，掛各排的 `deco`（`giantGlowStrips`）；
// - 行動中的虛線框、目標紅框：框整個 3×3。
import { Graphics, Sprite } from "pixi.js";
import { TILE_SIZE } from "../battle/geometry";
import type { ArtTextures } from "./artTextures";
import { GIANT_ANCHOR_DY, GIANT_GLOW_BOX, GIANT_RING_BOX, giantGroundGlow, giantGroundRing, giantHasGroundGlow, type GiantLook } from "./qBossGiant";
import { GIANT_RING_LABEL } from "./minMark";

const T = TILE_SIZE;
const hex = (c: number): string => `#${c.toString(16).padStart(6, "0")}`;

/** 地面貼圖的解析度（每模型 px 幾個 canvas px）：跟著畫面縮放（`figureRes(1)`）。 */
function groundRes(art: ArtTextures): number {
  return art.figureRes(1);
}

/** 一張「原點＝錨點」的地面畫布（`box`＝模型 px 範圍、相對錨點）。沒有 DOM 時 `null`。 */
function anchorCanvas(box: { x: number; y: number; w: number; h: number }, res: number, draw: (ctx: CanvasRenderingContext2D) => void): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(box.w * res));
  c.height = Math.max(1, Math.ceil(box.h * res));
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.setTransform(res, 0, 0, res, -box.x * res, -box.y * res);
  draw(ctx);
  return c;
}

/** 陣營環的節點（節點座標＝單位節點、原點中心格中心）；畫不出來時 `null`。 */
export function giantRingNode(art: ArtTextures, ring: { fill: number; stroke: number }): Sprite | null {
  const res = groundRes(art);
  const B = GIANT_RING_BOX;
  const tex = art.canvas(`gring|${res}|${ring.fill}|${ring.stroke}`, () => anchorCanvas(B, res, (ctx) => giantGroundRing(ctx, { fill: hex(ring.fill), stroke: hex(ring.stroke) })));
  if (tex === null) return null;
  const s = new Sprite(tex);
  s.label = GIANT_RING_LABEL;
  s.position.set(B.x, GIANT_ANCHOR_DY + B.y);
  s.width = B.w;
  s.height = B.h;
  return s;
}

/** 3×3 外緣（相對中心格中心）：一格的單位 `rx`。 */
export const GIANT_HALF = T * 1.5;

/** 行動中的虛線框（`u.active`；一格的單位是腳下的虛線橢圓）：圓角方框貼 3×3 外緣往內 3。 */
export function giantActiveFrame(color: number): Graphics {
  const g = new Graphics();
  const h = GIANT_HALF - 3;
  const dash = 8;
  const gap = 6;
  for (const [x0, y0, x1, y1] of [
    [-h, -h, h, -h],
    [h, -h, h, h],
    [h, h, -h, h],
    [-h, h, -h, -h],
  ] as const) {
    const len = Math.hypot(x1 - x0, y1 - y0);
    for (let d = 0; d < len; d += dash + gap) {
      const a = d / len;
      const b = Math.min(1, (d + dash) / len);
      g.moveTo(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a).lineTo(x0 + (x1 - x0) * b, y0 + (y1 - y0) * b);
    }
  }
  return g.stroke({ width: 2.5, color });
}

/** 目標紅框（HID-1b 的攻擊紅框，框整個 3×3；世界座標左上 `o`＝3×3 西北角那一格的左上）。 */
export function giantTargetFrame(o: { x: number; y: number }, color: number): Graphics {
  return new Graphics().roundRect(o.x + 2, o.y + 2, 3 * T - 4, 3 * T - 4, 10).stroke({ width: 3, color });
}

/** 坑底紅光的一排（`row`＝相對中心格的排差，−1～2；`node` 放在單位節點同一個位置）。 */
export interface GlowStrip {
  dy: number;
  node: Sprite;
}

/**
 * 第 3 階段坑底紅光（`giantGroundGlow`）切成一排一條：每排一張只含那一排範圍的畫布（同一個畫法、原點都是錨點，所以接縫對齊）。
 * 不用同一張貼圖的子矩形：貼圖快取淘汰時會連來源一起銷毀，子貼圖跟著壞。不是第 3 階段、或畫不出來時空陣列。
 */
export function giantGlowStrips(art: ArtTextures, look: GiantLook, dieT = 0): GlowStrip[] {
  if (!giantHasGroundGlow(look.phase)) return [];
  const res = groundRes(art);
  const B = GIANT_GLOW_BOX;
  const out: GlowStrip[] = [];
  // 錨點＝中心格中心往南 72：一排的上下緣（相對錨點）＝ (dy − 0.5) × T − 72 … (dy + 0.5) × T − 72
  for (const dy of [-1, 0, 1, 2]) {
    const top = Math.max(B.y, (dy - 0.5) * T - GIANT_ANCHOR_DY);
    const bottom = Math.min(B.y + B.h, (dy + 0.5) * T - GIANT_ANCHOR_DY);
    if (bottom <= top) continue;
    const box = { x: B.x, y: top, w: B.w, h: bottom - top };
    const tex = art.canvas(`gglow|${res}|${dieT.toFixed(2)}|${dy}`, () => anchorCanvas(box, res, (ctx) => giantGroundGlow(ctx, { phase: 3, dieT })));
    if (tex === null) continue;
    const s2 = new Sprite(tex);
    s2.position.set(box.x, GIANT_ANCHOR_DY + box.y);
    s2.width = box.w;
    s2.height = box.h;
    out.push({ dy, node: s2 });
  }
  return out;
}
