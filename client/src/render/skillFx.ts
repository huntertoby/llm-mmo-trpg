// 技能片段附帶的特效（Phase 6N-1／6N-2；`skillClips.ts` 的 `FxCue`）：武器發光、符陣、腳下法陣、槍口火光、
// 罩子、往上收的光環、光點（往上、往下、收進身體）、碎片、連線、倒數記號、光柱、風線、黑煙、震波。
// 每個效果一個 `Graphics`，每幀重畫；位置每幀問一次（作用端跟著姿勢走）。全部是時間的函式，沒有亂數（粒子用固定的角度表）。
import { Graphics } from "pixi.js";
import { TILE_SIZE } from "../battle/geometry";
import type { FxKind } from "./skillClips";
import { paletteOf } from "./statusVfx";
import type { Effect } from "./vfxEffects";

const T = TILE_SIZE;
type Pt = { x: number; y: number };

const fade = (t: number, from = 0.65) => (t < from ? 1 : Math.max(0, 1 - (t - from) / (1 - from)));
const TAU = Math.PI * 2;
/** 固定的粒子角度表（確定性；不用亂數）。 */
const SPOKES = [0.1, 0.9, 1.7, 2.5, 3.3, 4.1, 4.9, 5.7];

export interface CueAt {
  /** 片段的起點（作用端、手、腳底…；每幀算）。 */
  anchor: () => Pt;
  /** 施放者腳底。 */
  feet: () => Pt;
  /** 目標格的中心（腳底附近）；沒有目標時同施放者腳底。 */
  target: Pt;
}

function g0(): Graphics {
  const g = new Graphics();
  g.visible = false;
  return g;
}

/** 一個特效提示 → 效果。`where` 的換算由呼叫端先做好（`pos` 每幀回傳位置；`link` 另給起訖）。 */
export function cueEffect(kind: FxKind, pos: () => Pt, element: string, startMs: number, endMs: number, link?: { from: Pt; to: () => Pt }): Effect {
  const pal = paletteOf(element);
  const c1 = pal.primary;
  const c2 = pal.secondary;
  const g = g0();
  const draw = (t: number) => {
    const p = pos();
    const a = fade(t);
    switch (kind) {
      case "glow":
        g.circle(p.x, p.y, 3 + 4 * Math.sin(Math.min(1, t * 2) * Math.PI * 0.5)).fill({ color: c1, alpha: 0.35 * a });
        g.circle(p.x, p.y, 2).fill({ color: 0xffffff, alpha: 0.8 * a });
        return;
      case "sigil": {
        const r = 7 * Math.min(1, t * 1.6);
        g.circle(p.x, p.y, r).stroke({ width: 1.5, color: c1, alpha: a });
        const pts: number[] = [];
        for (let k = 0; k < 5; k++) {
          const ang = -Math.PI / 2 + (k * TAU * 2) / 5 + t * 1.2;
          pts.push(p.x + Math.cos(ang) * r * 0.7, p.y + Math.sin(ang) * r * 0.7);
        }
        g.poly(pts).stroke({ width: 1, color: c2, alpha: a });
        return;
      }
      case "circle": {
        const r = T * 0.42 * Math.min(1, t * 1.6);
        g.ellipse(p.x, p.y, r, r * 0.35).stroke({ width: 2, color: c1, alpha: 0.8 * a });
        g.ellipse(p.x, p.y, r * 0.65, r * 0.23).stroke({ width: 1.2, color: c2, alpha: 0.7 * a });
        return;
      }
      case "muzzle":
        g.circle(p.x, p.y, 5 * (1 - t) + 2).fill({ color: 0xffd23a, alpha: 1 - t });
        return;
      case "ring": {
        const r = T * 0.36;
        g.ellipse(p.x, p.y - T * 0.2, r, r * 1.05).stroke({ width: 2, color: c1, alpha: 0.6 * a * Math.min(1, t * 3) });
        g.ellipse(p.x, p.y - T * 0.2, r, r * 1.05).fill({ color: c2, alpha: 0.12 * a });
        return;
      }
      case "ringUp": {
        const r = T * 0.4 * (1 - 0.45 * t);
        g.ellipse(p.x, p.y - T * 0.35 * t, r, r * 0.35).stroke({ width: 2, color: c1, alpha: a });
        return;
      }
      case "motesUp":
      case "motesDown":
      case "motesIn":
        for (let k = 0; k < SPOKES.length; k++) {
          const s = SPOKES[k] as number;
          const u = (t + k / SPOKES.length) % 1;
          const dx = Math.cos(s) * T * 0.25;
          let x = p.x + dx;
          let y = p.y;
          if (kind === "motesUp") y -= T * 0.6 * u;
          else if (kind === "motesDown") y -= T * 0.6 * (1 - u);
          else {
            x = p.x + Math.cos(s) * T * 0.45 * (1 - u);
            y = p.y - T * 0.3 + Math.sin(s) * T * 0.25 * (1 - u);
          }
          g.circle(x, y, 1.6).fill({ color: k % 2 === 0 ? c1 : c2, alpha: a * Math.sin(u * Math.PI) });
        }
        return;
      case "shards":
        for (const s of SPOKES) {
          const d = T * (0.12 + 0.35 * t);
          const x = p.x + Math.cos(s) * d;
          const y = p.y - T * 0.3 + Math.sin(s) * d * 0.7 + T * 0.3 * t * t;
          g.poly([x, y - 2.5, x + 1.5, y, x, y + 2.5, x - 1.5, y]).fill({ color: c1, alpha: a });
        }
        return;
      case "link": {
        if (link === undefined) return;
        const to = link.to();
        const u = Math.min(1, t * 1.6);
        g.moveTo(link.from.x, link.from.y).lineTo(link.from.x + (to.x - link.from.x) * u, link.from.y + (to.y - link.from.y) * u).stroke({ width: 2, color: c1, alpha: 0.8 * a });
        return;
      }
      case "mark": {
        const r = 6;
        g.circle(p.x, p.y, r).stroke({ width: 2, color: c1, alpha: a });
        g.moveTo(p.x, p.y).lineTo(p.x + Math.sin(t * TAU) * r * 0.8, p.y - Math.cos(t * TAU) * r * 0.8).stroke({ width: 1.5, color: c2, alpha: a });
        return;
      }
      case "pillar": {
        const w = T * 0.22;
        const h = T * 1.1 * Math.min(1, t * 2);
        g.rect(p.x - w / 2, p.y - h, w, h).fill({ color: c1, alpha: 0.28 * a });
        g.rect(p.x - w / 6, p.y - h, w / 3, h).fill({ color: 0xffffff, alpha: 0.35 * a });
        return;
      }
      case "wind":
        for (const dy of [-T * 0.35, -T * 0.2, -T * 0.05]) {
          const len = T * 0.3 * (1 - t * 0.5);
          g.moveTo(p.x - len, p.y + dy).lineTo(p.x - len * 0.2, p.y + dy).stroke({ width: 1.5, color: 0xffffff, alpha: 0.6 * a });
        }
        return;
      case "smoke":
        for (let k = 0; k < 5; k++) {
          const s = SPOKES[k] as number;
          g.circle(p.x + Math.cos(s) * T * 0.15, p.y - T * (0.1 + 0.25 * t) + Math.sin(s) * 3, 4 + 3 * t).fill({ color: 0x1a1420, alpha: 0.45 * a });
        }
        return;
      case "quake": {
        const r = T * (0.2 + 0.9 * t);
        g.ellipse(p.x, p.y, r, r * 0.4).stroke({ width: 3 * (1 - t) + 1, color: 0xd8c8a0, alpha: a });
        return;
      }
    }
  };
  return {
    node: g,
    startMs,
    endMs: Math.max(startMs + 1, endMs),
    update: (t) => {
      g.visible = true;
      g.clear();
      draw(t);
    },
  };
}
