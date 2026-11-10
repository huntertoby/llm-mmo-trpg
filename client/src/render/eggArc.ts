// CB-2c：蜥蜴產卵的蛋（美術 PM `docs/art/CB-2b檢查.md` 小修 1）：從片段拿出來，照拋物線飛到孵化格，落地那一刻爆開、接幼體出現。
// 路線與時間是純函式（`eggArcPlan`、`eggAt`），畫法照 qCreatureAnim 的 egg、glow、burst（只有這裡的座標是戰場的模型像素）。
import { Graphics } from "pixi.js";
import { EGG_SCALE } from "./qCreatureAnim";
import type { Effect } from "./vfxEffects";

type Pt = { x: number; y: number };

export interface EggArcInput {
  /** 起點（身體後方，模型像素）。 */
  from: Pt;
  /** 終點：孵化格的腳底（和幼體的腳底同一點）。 */
  to: Pt;
  startMs: number;
  /** 落地（＝孵化）的時刻：片段的出手格，也是畫面更新出幼體的那一刻。 */
  landMs: number;
  /** 爆開結束（片段結束）。 */
  endMs: number;
  /** 異形座標 → 模型像素的倍率（蛋的大小跟著身體）。 */
  unit: number;
}

export interface EggArcPlan extends EggArcInput {
  /** 拋物線的高度（模型像素）。 */
  peak: number;
}

/** 片段裡的蛋只飛 40 單位、高 18；戰場上距離不同，至少維持片段的高度，遠的拋高一點。 */
const PEAK_UNITS = 18;
const PEAK_OF_DISTANCE = 0.35;

export function eggArcPlan(input: EggArcInput): EggArcPlan {
  const dist = Math.hypot(input.to.x - input.from.x, input.to.y - input.from.y);
  return { ...input, endMs: Math.max(input.endMs, input.landMs + 1), peak: Math.max(PEAK_UNITS * input.unit, dist * PEAK_OF_DISTANCE) };
}

export interface EggFrame {
  x: number;
  y: number;
  rot: number;
  landed: boolean;
  /** 落地後爆開的進度（0～1；還沒落地＝0）。 */
  burst: number;
}

/** 這條拋物線在 `ms` 的位置。沒起飛前在起點，落地後停在終點。 */
export function eggAt(plan: EggArcPlan, ms: number): EggFrame {
  const span = Math.max(1, plan.landMs - plan.startMs);
  const q = Math.max(0, Math.min(1, (ms - plan.startMs) / span));
  const landed = ms >= plan.landMs;
  const side = plan.to.x < plan.from.x ? -1 : 1;
  return {
    x: landed ? plan.to.x : plan.from.x + (plan.to.x - plan.from.x) * q,
    y: landed ? plan.to.y : plan.from.y + (plan.to.y - plan.from.y) * q - plan.peak * Math.sin(Math.PI * q),
    rot: side * q * Math.PI * 2,
    landed,
    burst: landed ? Math.max(0, Math.min(1, (ms - plan.landMs) / (plan.endMs - plan.landMs))) : 0,
  };
}

function drawEgg(g: Graphics, f: EggFrame, s: number, color: string): void {
  // 同 qCreatureAnim 的 egg：腳底在 (0,0)，畫在原點往上（模型像素）
  const cos = Math.cos(f.rot);
  const sin = Math.sin(f.rot);
  const at = (x: number, y: number): [number, number] => [f.x + x * cos - y * sin, f.y + x * sin + y * cos];
  const ellipse = (cx: number, cy: number, rx: number, ry: number): number[] => {
    const pts: number[] = [];
    for (let i = 0; i < 16; i++) {
      const an = (i / 16) * Math.PI * 2;
      pts.push(...at(cx + Math.cos(an) * rx, cy + Math.sin(an) * ry));
    }
    return pts;
  };
  g.poly(ellipse(0, -3.2 * s, 2.6 * s, 3.3 * s)).fill({ color });
  g.poly(ellipse(-0.8 * s, -4.4 * s, 0.8 * s, 1.1 * s)).fill({ color: "#ffe08a" });
}

function drawBurst(g: Graphics, f: EggFrame, unit: number, c: readonly [string, string]): void {
  // 同片段落地後的 glow（亮色）＋burst（星形）：畫在幼體身上一點點（y −4）
  const a = 1 - f.burst;
  const y = f.y - 4 * unit;
  for (const [s, al] of [[1, 0.18], [0.65, 0.26], [0.35, 0.4]] as const) g.circle(f.x, y, 10 * unit * s).fill({ color: c[1], alpha: al * a });
  const r = 5 * unit;
  const pts: number[] = [];
  for (let i = 0; i < 14; i++) {
    const an = (i / 14) * Math.PI * 2 + 0.2;
    const d = i % 2 ? r * 0.45 : r;
    pts.push(f.x + Math.cos(an) * d, y + Math.sin(an) * d);
  }
  g.poly(pts).fill({ color: c[0], alpha: a });
  g.circle(f.x, y, r * 0.32).fill({ color: c[1], alpha: a });
}

/** 放進效果迴圈的蛋（沒標 `motion`：同飛行物，減少動態時照舊畫）。 */
export function eggArcEffect(plan: EggArcPlan, colors: readonly [string, string]): Effect {
  const g = new Graphics();
  g.visible = false;
  return {
    node: g,
    startMs: plan.startMs,
    endMs: plan.endMs,
    update: (t) => {
      const f = eggAt(plan, plan.startMs + t * (plan.endMs - plan.startMs));
      g.visible = true;
      g.clear();
      if (f.landed) drawBurst(g, f, plan.unit, colors);
      else drawEgg(g, f, EGG_SCALE * plan.unit, colors[0]);
    },
  };
}
