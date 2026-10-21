// 整格抬高的 Pixi 繪圖（Phase 3-19；docs/art/3-18倒地與高度.md 第 3、5 節）：
// 崖面與描邊、遮擋剪影、升降動畫（位移補間＋碎土／塵土）。幾何在 `heightShapes.ts`，位移在 `battle/elevation.ts`。
import { Container, Graphics } from "pixi.js";
import { liftHeightAt, type EdgeMarks, type HeightShift } from "../battle/elevation";
import type { Effect } from "./vfxEffects";
import {
  CLIFF_BOTTOM,
  CLIFF_TOP,
  dashSegments,
  DIRT,
  dirtBit,
  dirtCount,
  dustRing,
  EDGE,
  mixColor,
  RIM,
  silhouetteLoops,
  strataLines,
} from "./heightShapes";

/** 崖面漸層切成幾條色帶（每條約 2px）。 */
const BAND_PX = 2;

/**
 * 頂面底下的崖面（格子座標系：頂面在 [0, size)，崖面在 [size, size + lift)）：漸層、每階一條暗線、
 * 崖頂 2px 亮唇。`lift` ≤ 0 時不畫。
 */
export function drawCliff(g: Graphics, lift: number, size: number): void {
  g.clear();
  if (lift <= 0) return;
  const bands = Math.max(1, Math.ceil(lift / BAND_PX));
  for (let i = 0; i < bands; i += 1) {
    const y0 = (i * lift) / bands;
    const y1 = ((i + 1) * lift) / bands;
    g.rect(0, size + y0, size, y1 - y0 + 0.5).fill(mixColor(CLIFF_TOP, CLIFF_BOTTOM, bands === 1 ? 0 : i / (bands - 1)));
  }
  for (const y of strataLines(lift)) g.rect(0, size + y, size, 1).fill({ color: 0x000000, alpha: 0.3 });
}

/** 高格的描邊（畫在頂面貼圖之上）：東西較低畫外側暗線（含崖面高度）、北較低畫亮邊、有崖面時畫崖頂亮唇。 */
export function drawEdges(g: Graphics, lift: number, marks: EdgeMarks, size: number): void {
  g.clear();
  if (lift <= 0) return;
  g.rect(0, size - 2, size, 2).fill(RIM); // 崖頂亮唇（南鄰同高時會被南鄰蓋住）
  if (marks.north) g.rect(0, 0, size, 2).fill(RIM);
  if (marks.east) g.rect(size - 1.5, 0, 1.5, size + lift).fill(EDGE);
  if (marks.west) g.rect(0, 0, 1.5, size + lift).fill(EDGE);
}

/** 遮擋剪影：隊伍色 2px 虛線（3/2）、透明度 0.9、不填色（`feetX/feetY` 是抬高後的腳底）。 */
export function silhouette(feetX: number, feetY: number, color: number, size: number): Graphics {
  const g = new Graphics();
  for (const loop of silhouetteLoops(feetX, feetY, size)) {
    for (const [a, b] of dashSegments(loop, true, 3, 2)) g.moveTo(a.x, a.y).lineTo(b.x, b.y);
  }
  g.stroke({ width: 2, color, alpha: 0.9 });
  return g;
}

function timed(node: Container, startMs: number, endMs: number, update: (t: number) => void, end?: () => void): Effect {
  return { node, startMs, endMs: Math.max(endMs, startMs + 1), update, end };
}

/** 升降的時間點與座標：`origin(h)` ＝ 高度 h 時頂面的左上角（世界座標）。 */
export interface LiftPlan {
  shift: HeightShift;
  now: number;
  durationMs: number;
  origin(h: number): { x: number; y: number };
  /** 套用補間中的高度（移動頂面、崖面、格上的物件與單位）。 */
  apply(h: number): void;
  skip(): boolean;
  size: number;
}

/**
 * 一格的升降：高度從舊值以 ease-out 補到新值；升起時邊緣噴出碎土，下降結束時落點一圈塵土。
 * 「略過」時直接套用結果。
 */
export function liftEffects(plan: LiftPlan): Effect[] {
  const { shift, now, durationMs, size } = plan;
  const finish = () => plan.apply(shift.to);
  const tween = timed(
    new Container(),
    now,
    now + durationMs,
    (t) => plan.apply(plan.skip() ? shift.to : liftHeightAt(shift.from, shift.to, t * durationMs, durationMs)),
    finish,
  );
  const out = [tween];
  if (plan.skip()) return out;
  if (shift.to > shift.from) {
    const o = plan.origin(shift.from);
    const n = dirtCount(shift.pos.x, shift.pos.y);
    const g = new Graphics();
    g.visible = false;
    out.push(
      timed(g, now, now + durationMs * 1.6, (t) => {
        g.visible = true;
        g.clear();
        for (let i = 0; i < n; i += 1) {
          const b = dirtBit(i, n, t, size);
          if (b.alpha > 0.01) g.rect(o.x + b.x - b.size / 2, o.y + b.y - b.size / 2, b.size, b.size).fill({ color: DIRT, alpha: b.alpha });
        }
      }),
    );
  } else {
    const o = plan.origin(shift.to);
    const g = new Graphics();
    g.visible = false;
    const start = now + durationMs * 0.85;
    out.push(
      timed(g, start, start + durationMs * 1.4, (t) => {
        g.visible = true;
        g.clear();
        const r = dustRing(t, size);
        g.ellipse(o.x + size / 2, o.y + size * 0.85, r.radius, r.radius * 0.4).stroke({ width: 4, color: DIRT, alpha: r.alpha });
      }),
    );
  }
  return out;
}
