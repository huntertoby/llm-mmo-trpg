// 走路途中踩到特殊地表時腳下的效果（Phase 6A-4d）：冰花、陷阱夾子、冒火、濺油。
// 每個效果一個 `Graphics`，每幀重畫；時間與位置由 `BattleRenderer.animateWalk` 給（`c` 是腳底的模型像素位置）。
import { Graphics } from "pixi.js";
import type { BeatKind } from "../battle/walkAnim";
import { TILE_SIZE } from "../battle/geometry";
import type { Effect } from "./vfxEffects";

const T = TILE_SIZE;

type Pt = { x: number; y: number };

function fx(startMs: number, durationMs: number, draw: (g: Graphics, t: number) => void): Effect {
  const g = new Graphics();
  g.visible = false;
  return {
    node: g,
    startMs,
    endMs: startMs + Math.max(1, durationMs),
    update: (t) => {
      g.visible = true;
      g.clear();
      draw(g, t);
    },
  };
}

const fadeOut = (t: number, from = 0.6) => (t < from ? 1 : Math.max(0, 1 - (t - from) / (1 - from)));

/** 冰花：六瓣白藍冰晶從腳底綻開，再淡掉。 */
function iceFlower(c: Pt, now: number, ms: number): Effect {
  return fx(now, ms, (g, t) => {
    const r = T * (0.12 + 0.2 * Math.min(1, t * 2.2));
    const a = fadeOut(t);
    for (let i = 0; i < 6; i += 1) {
      const ang = (i / 6) * Math.PI * 2 + 0.3;
      const tip = { x: c.x + Math.cos(ang) * r, y: c.y + Math.sin(ang) * r * 0.5 };
      const side = 0.22;
      const l = { x: c.x + Math.cos(ang - side) * r * 0.45, y: c.y + Math.sin(ang - side) * r * 0.22 };
      const rr = { x: c.x + Math.cos(ang + side) * r * 0.45, y: c.y + Math.sin(ang + side) * r * 0.22 };
      g.poly([c.x, c.y, l.x, l.y, tip.x, tip.y, rr.x, rr.y]).fill({ color: 0xdff4ff, alpha: 0.85 * a });
      g.moveTo(c.x, c.y).lineTo(tip.x, tip.y).stroke({ width: 1, color: 0x6fb8ff, alpha: a });
    }
    g.circle(c.x, c.y, 2.5).fill({ color: 0xffffff, alpha: a });
  });
}

/** 滑倒：冰花加兩道往前溜的擦痕。 */
function slipStreaks(c: Pt, now: number, ms: number): Effect {
  return fx(now, ms, (g, t) => {
    const a = fadeOut(t, 0.5);
    const len = T * 0.35 * Math.min(1, t * 3);
    for (const dy of [-3, 3]) {
      g.moveTo(c.x - len / 2, c.y + dy).lineTo(c.x + len / 2, c.y + dy * 0.6).stroke({ width: 2, color: 0xffffff, alpha: 0.8 * a });
    }
  });
}

/** 陷阱夾子：兩排鋸齒從兩側合上，夾住後抖一下。 */
function trapJaws(c: Pt, now: number, ms: number): Effect {
  return fx(now, ms, (g, t) => {
    const close = Math.min(1, t / 0.25); // 前 25% 合上
    const shake = t > 0.25 && t < 0.45 ? Math.sin(t * 90) * 1.5 : 0;
    const a = fadeOut(t, 0.7);
    const w = T * 0.42;
    const gap = T * 0.22 * (1 - close);
    for (const side of [-1, 1]) {
      const y = c.y + side * (gap + 2) + shake;
      const pts: number[] = [c.x - w, y];
      const n = 5;
      for (let i = 0; i <= n; i += 1) {
        const x = c.x - w + (2 * w * i) / n;
        pts.push(x, y, x + w / n / 2, y - side * 5);
      }
      pts.push(c.x + w, y);
      g.poly(pts).fill({ color: 0x9aa0a6, alpha: a }).stroke({ width: 1.5, color: 0x2a2a2a, alpha: a });
    }
    if (close >= 1) g.ellipse(c.x, c.y, w * 1.1, T * 0.12).stroke({ width: 2, color: 0xff5040, alpha: 0.7 * a });
  });
}

/** 冒火：幾束火舌從腳底往上竄。 */
function fireBurst(c: Pt, now: number, ms: number): Effect {
  return fx(now, ms, (g, t) => {
    const a = fadeOut(t, 0.5);
    for (let i = 0; i < 5; i += 1) {
      const x = c.x + (i - 2) * T * 0.09;
      const h = T * (0.22 + 0.08 * ((i * 7) % 3)) * Math.min(1, t * 3) * (1 - 0.4 * t);
      const w = T * 0.06;
      g.poly([x - w, c.y, x, c.y - h, x + w, c.y]).fill({ color: i % 2 === 0 ? 0xff7a1a : 0xffc23a, alpha: 0.9 * a });
    }
    g.ellipse(c.x, c.y, T * 0.28, T * 0.08).fill({ color: 0xff5a10, alpha: 0.35 * a });
  });
}

/** 濺油：深色油滴往外濺開落下。 */
function oilSplash(c: Pt, now: number, ms: number): Effect {
  return fx(now, ms, (g, t) => {
    const a = fadeOut(t, 0.55);
    for (let i = 0; i < 7; i += 1) {
      const ang = Math.PI * (1.1 + (0.8 * i) / 6);
      const d = T * 0.3 * Math.min(1, t * 2.5);
      const lift = Math.sin(Math.min(1, t * 2.5) * Math.PI) * T * 0.12;
      g.circle(c.x + Math.cos(ang) * d, c.y + Math.sin(ang) * d * 0.4 - lift, 2.2).fill({ color: 0x3a2a14, alpha: a });
    }
    g.ellipse(c.x, c.y, T * 0.3 * Math.min(1, t * 2), T * 0.09).fill({ color: 0x2a2010, alpha: 0.45 * a });
  });
}

/** 跳躍落地的揚塵（6M-3，照樣張 heightRow）：腳底左右五團沙色小圓，往外散開、淡掉。 */
export function landingDust(c: Pt, now: number, ms: number): Effect {
  return fx(now, ms, (g, t) => {
    const a = 1 - t;
    for (let k = -2; k <= 2; k += 1) {
      const spread = 1 + 0.6 * t;
      g.circle(c.x + k * 6 * spread, c.y + 2 - 2 * t * (k === 0 ? 0.5 : 1), 3 * (1 + 0.3 * t)).fill({ color: 0xc8b890, alpha: 0.8 * a });
    }
  });
}

/** 一個地表效果在腳底 `c` 的動畫（`ms` 已依播放速度縮放）。 */
export function beatEffects(kind: BeatKind, c: Pt, now: number, ms: number): Effect[] {
  switch (kind) {
    case "ice":
      return [iceFlower(c, now, ms)];
    case "slip":
      return [iceFlower(c, now, ms), slipStreaks(c, now, ms)];
    case "trap":
      return [trapJaws(c, now, ms)];
    case "fire":
      return [fireBurst(c, now, ms)];
    case "oil":
      return [oilSplash(c, now, ms)];
  }
}
