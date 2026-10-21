// 技能特效的 PixiJS 繪圖（Phase 3-12）：把 `battle/vfx.ts` 的特效描述變成一組有起訖時間的動態效果。
// 每個效果一個 `Graphics`，每幀 `clear()` 後重畫（粒子數少，不需要粒子套件）；結束時由 `BattleRenderer`
// 的效果迴圈銷毀。座標一律是模型像素（`tileCenter`），與場景其他圖層相同。
import { Container, Graphics } from "pixi.js";
import type { Pos } from "../api/types";
import { chebyshev, type VfxCast, type VfxHit } from "../battle/vfx";
import { elementVfx, jitter, particleAt, type ElementVfx, type ParticleKind } from "../battle/vfxPalette";
import { TILE_SIZE, tileCenter } from "../battle/geometry";

const T = TILE_SIZE;

/** 一個動態效果：`update(t)` 傳入 0–1 的進度；`end()` 在移除前呼叫（還原震動等）。 */
export interface Effect {
  node: Container;
  startMs: number;
  endMs: number;
  update(t: number): void;
  end?(): void;
}

type Pt = { x: number; y: number };

function effect(g: Graphics, startMs: number, endMs: number, update: (t: number) => void): Effect {
  g.visible = false;
  return {
    node: g,
    startMs,
    endMs: Math.max(endMs, startMs + 1),
    update: (t) => {
      g.visible = true;
      g.clear();
      update(t);
    },
  };
}

// ---- 粒子 -------------------------------------------------------------------

function drawParticle(g: Graphics, kind: ParticleKind, c: Pt, p: ReturnType<typeof particleAt>, color: number): void {
  if (p.alpha <= 0.01) return;
  const x = c.x + p.x;
  const y = c.y + p.y;
  const cos = Math.cos(p.rotation);
  const sin = Math.sin(p.rotation);
  switch (kind) {
    case "shard":
    case "rock": {
      const s = p.size;
      const pts = kind === "shard" ? [0, -s * 1.4, s * 0.6, 0, 0, s * 1.4, -s * 0.6, 0] : [-s, -s, s, -s * 0.8, s * 0.9, s, -s * 0.8, s * 0.9];
      const rotated: number[] = [];
      for (let i = 0; i < pts.length; i += 2) {
        const px = pts[i] as number;
        const py = pts[i + 1] as number;
        rotated.push(x + px * cos - py * sin, y + px * sin + py * cos);
      }
      g.poly(rotated).fill({ color, alpha: p.alpha });
      return;
    }
    case "bolt": {
      const len = p.size;
      const mx = x - cos * len * 0.5 + -sin * len * 0.3;
      const my = y - sin * len * 0.5 + cos * len * 0.3;
      g.moveTo(x - cos * len, y - sin * len).lineTo(mx, my).lineTo(x, y).stroke({ width: 2, color, alpha: p.alpha });
      return;
    }
    case "spark":
      g.moveTo(x - cos * p.size, y - sin * p.size).lineTo(x, y).stroke({ width: 2, color, alpha: p.alpha });
      return;
    case "gust":
      g.moveTo(x + Math.cos(p.rotation) * p.size, y + Math.sin(p.rotation) * p.size)
        .arc(x, y, p.size, p.rotation, p.rotation + 1.3)
        .stroke({ width: 2, color, alpha: p.alpha });
      return;
    case "bubble":
      g.circle(x, y, p.size).stroke({ width: 1.5, color, alpha: p.alpha });
      return;
    default:
      g.circle(x, y, p.size).fill({ color, alpha: p.alpha });
  }
}

/** 一處爆發：中心閃光 ＋ 元素粒子（聖光另有光柱）。`scale` 是大小（1 ＝ 一格，範圍的每格較小）。 */
function burstEffect(pos: Pos, pal: ElementVfx, startMs: number, durationMs: number, intensity: number, scale: number): Effect {
  const c = tileCenter(pos);
  const g = new Graphics();
  const n = Math.max(3, Math.round(pal.particles * intensity * scale));
  const reach = T * 0.6 * intensity * scale;
  return effect(g, startMs, startMs + durationMs, (t) => {
    if (pal.column && t < 0.8) {
      const w = T * 0.36 * scale;
      g.rect(c.x - w / 2, c.y - T * 1.3, w, T * 1.3).fill({ color: pal.secondary, alpha: 0.45 * (1 - t / 0.8) });
    }
    if (t < 0.45) {
      const k = t / 0.45;
      g.circle(c.x, c.y, T * (0.18 + 0.3 * k) * scale * intensity).fill({ color: pal.primary, alpha: 0.6 * (1 - k) });
    }
    for (let i = 0; i < n; i += 1) {
      const color = i % 3 === 0 ? pal.primary : pal.secondary;
      drawParticle(g, pal.particle, c, particleAt(pal.particle, i, n, t, reach), color);
    }
  });
}

// ---- 各種特效 ---------------------------------------------------------------

/** 施放前的蓄力光：施放者身上的光暈逐漸變亮，命中前淡出。 */
function chargeEffect(cast: VfxCast, pal: ElementVfx, now: number): Effect {
  const c = tileCenter(cast.from);
  const g = new Graphics();
  const start = now + cast.startMs;
  const end = now + Math.max(cast.startMs + 1, cast.impactMs);
  return effect(g, start, end, (t) => {
    const grow = Math.min(1, t * 2.5);
    const alpha = t < 0.6 ? 0.55 * grow : 0.55 * (1 - (t - 0.6) / 0.4);
    g.circle(c.x, c.y, T * (0.25 + 0.2 * grow)).fill({ color: pal.primary, alpha: alpha * 0.6 });
    g.circle(c.x, c.y, T * (0.5 - 0.15 * grow)).stroke({ width: 2, color: pal.secondary, alpha });
  });
}

function travelStart(cast: VfxCast, now: number, chargeMs: number): number {
  return now + cast.startMs + (cast.charge ? chargeMs : 0);
}

/** 遠程單體：飛行物（拖尾 3 顆；雷改成鋸齒軌跡）。 */
function projectileEffect(cast: VfxCast, pal: ElementVfx, start: number, end: number): Effect {
  const a = tileCenter(cast.from);
  const b = tileCenter(cast.to);
  const g = new Graphics();
  const r = 6 * cast.intensity;
  return effect(g, start, end, (t) => {
    const head = lerp(a, b, t);
    if (pal.jagged) {
      jaggedLine(g, a, head, Math.floor(t * 30), 6);
      g.stroke({ width: 2, color: pal.secondary, alpha: 0.9 });
    }
    for (let k = 3; k >= 1; k -= 1) {
      const p = lerp(a, b, Math.max(0, t - k * 0.07));
      g.circle(p.x, p.y, r * (1 - k * 0.2)).fill({ color: pal.secondary, alpha: 0.5 - k * 0.12 });
    }
    g.circle(head.x, head.y, r * 1.6).fill({ color: pal.primary, alpha: 0.35 });
    g.circle(head.x, head.y, r).fill({ color: pal.primary, alpha: 1 });
    g.circle(head.x, head.y, r * 0.45).fill({ color: 0xffffff, alpha: 0.9 });
  });
}

/** 近戰單體：在目標身上揮出一道弧（垂直於攻擊方向掃過）。 */
function slashEffect(cast: VfxCast, pal: ElementVfx, start: number, end: number): Effect {
  const a = tileCenter(cast.from);
  const b = tileCenter(cast.to);
  const g = new Graphics();
  const dir = Math.atan2(b.y - a.y, b.x - a.x);
  const radius = T * 0.42 * cast.intensity;
  const sweep = Math.PI * 0.9;
  const from = dir - sweep / 2;
  return effect(g, start, end, (t) => {
    const grow = Math.min(1, t * 2);
    const fade = t < 0.5 ? 1 : 1 - (t - 0.5) / 0.5;
    const a0 = from;
    const a1 = from + sweep * grow;
    const cx = b.x - Math.cos(dir) * T * 0.15;
    const cy = b.y - Math.sin(dir) * T * 0.15;
    g.moveTo(cx + Math.cos(a0) * radius, cy + Math.sin(a0) * radius)
      .arc(cx, cy, radius, a0, a1)
      .stroke({ width: 7 * cast.intensity, color: pal.primary, alpha: 0.55 * fade });
    g.moveTo(cx + Math.cos(a0) * radius, cy + Math.sin(a0) * radius)
      .arc(cx, cy, radius, a0, a1)
      .stroke({ width: 2.5, color: 0xffffff, alpha: fade });
  });
}

/** 直線、連鎖：光束沿路徑延伸到底，命中後變細淡出（雷為鋸齒）。 */
function beamEffect(cast: VfxCast, pal: ElementVfx, start: number, impact: number, impactMs: number): Effect {
  const pts = cast.path.map((p) => tileCenter(p));
  const g = new Graphics();
  const end = impact + impactMs * 0.45;
  const reachAt = (impact - start) / (end - start);
  return effect(g, start, end, (t) => {
    const k = reachAt <= 0 ? 1 : Math.min(1, t / reachAt);
    const fade = t <= reachAt ? 1 : 1 - (t - reachAt) / (1 - reachAt);
    const shown = partialPath(pts, k);
    for (const [width, color, alpha] of [
      [12 * cast.intensity * fade + 2, pal.primary, 0.4],
      [3, pal.secondary, 1],
    ] as const) {
      shown.forEach((p, i) => {
        if (i === 0) return;
        const prev = shown[i - 1] as Pt;
        if (pal.jagged) jaggedLine(g, prev, p, Math.floor(t * 24) + i, 7);
        else g.moveTo(prev.x, prev.y).lineTo(p.x, p.y);
      });
      g.stroke({ width, color, alpha: alpha * fade });
    }
  });
}

/** 錐形：從施放者朝目標方向擴散的扇形。 */
function coneEffect(cast: VfxCast, pal: ElementVfx, start: number, impact: number, impactMs: number): Effect {
  const a = tileCenter(cast.from);
  const b = tileCenter(cast.to);
  const dir = Math.atan2(b.y - a.y, b.x - a.x);
  const radius = (Math.max(1, ...cast.tiles.map((p) => chebyshev(p, cast.from))) + 0.5) * T;
  const half = Math.PI / 4;
  const g = new Graphics();
  const end = impact + impactMs * 0.4;
  const reachAt = (impact - start) / (end - start);
  return effect(g, start, end, (t) => {
    const k = reachAt <= 0 ? 1 : Math.min(1, t / reachAt);
    const fade = t <= reachAt ? 1 : 1 - (t - reachAt) / (1 - reachAt);
    const r = radius * k;
    const pts = [a.x, a.y];
    for (let i = 0; i <= 8; i += 1) {
      const ang = dir - half + (2 * half * i) / 8;
      pts.push(a.x + Math.cos(ang) * r, a.y + Math.sin(ang) * r);
    }
    g.poly(pts).fill({ color: pal.primary, alpha: 0.28 * fade });
    g.moveTo(a.x + Math.cos(dir - half) * r, a.y + Math.sin(dir - half) * r)
      .arc(a.x, a.y, r, dir - half, dir + half)
      .stroke({ width: 3, color: pal.secondary, alpha: 0.9 * fade });
  });
}

/** 自身、光環：從施放者向外擴散的兩道環。 */
function auraEffect(cast: VfxCast, pal: ElementVfx, start: number, impact: number, impactMs: number): Effect {
  const c = tileCenter(cast.from);
  const radius = Math.max(T * 0.8, (Math.max(0, ...cast.tiles.map((p) => chebyshev(p, cast.from))) + 0.5) * T);
  const g = new Graphics();
  const end = impact + impactMs * 0.6;
  return effect(g, start, end, (t) => {
    for (const lag of [0, 0.25]) {
      const k = Math.max(0, Math.min(1, (t - lag) / (1 - lag)));
      if (k <= 0) continue;
      const alpha = 1 - k;
      g.circle(c.x, c.y, radius * k).stroke({ width: 4 * cast.intensity, color: lag === 0 ? pal.primary : pal.secondary, alpha });
      if (lag === 0) g.circle(c.x, c.y, radius * k).fill({ color: pal.primary, alpha: 0.12 * alpha });
    }
  });
}

/** 範圍的一格：底色一閃（逐格爆發時的格子標記）。 */
function tileFlash(pos: Pos, pal: ElementVfx, start: number, durationMs: number): Effect {
  const c = tileCenter(pos);
  const g = new Graphics();
  return effect(g, start, start + durationMs, (t) => {
    const alpha = t < 0.25 ? t / 0.25 : 1 - (t - 0.25) / 0.75;
    g.rect(c.x - T / 2 + 2, c.y - T / 2 + 2, T - 4, T - 4).fill({ color: pal.primary, alpha: 0.35 * alpha });
  });
}

/** 範圍的各格依與中心（或施放者）的距離錯開爆發；每格的粒子較少。 */
function tileBursts(cast: VfxCast, pal: ElementVfx, impact: number, impactMs: number, origin: Pos): Effect[] {
  const out: Effect[] = [];
  const stagger = impactMs * 0.08;
  const scale = cast.tiles.length > 1 ? 0.6 : 1;
  for (const p of cast.tiles) {
    const delay = chebyshev(p, origin) * stagger;
    out.push(tileFlash(p, pal, impact + delay, impactMs * 0.7));
    out.push(burstEffect(p, pal, impact + delay, impactMs, cast.intensity, scale));
  }
  return out;
}

/** 一個特效描述 → 一組動態效果（`now` 是目前的效果時鐘；描述內的時間已依播放速度縮放）。 */
export function castEffects(cast: VfxCast, now: number, impactMs: number, chargeMs: number): Effect[] {
  const pal = elementVfx(cast.element);
  const out: Effect[] = [];
  if (cast.charge) out.push(chargeEffect(cast, pal, now));
  const start = travelStart(cast, now, chargeMs);
  const impact = Math.max(start, now + cast.impactMs);
  switch (cast.kind) {
    case "projectile":
      out.push(projectileEffect(cast, pal, start, impact), burstEffect(cast.to, pal, impact, impactMs, cast.intensity, 1));
      break;
    case "slash":
      out.push(slashEffect(cast, pal, start, impact + impactMs * 0.4), burstEffect(cast.to, pal, impact, impactMs, cast.intensity, 0.8));
      break;
    case "burst":
      out.push(burstEffect(cast.to, pal, impact, impactMs, cast.intensity, 1));
      break;
    case "beam":
      out.push(beamEffect(cast, pal, start, impact, impactMs), ...tileBursts(cast, pal, impact, impactMs, cast.from));
      break;
    case "cone":
      out.push(coneEffect(cast, pal, start, impact, impactMs), ...tileBursts(cast, pal, impact, impactMs, cast.from));
      break;
    case "area":
      out.push(...tileBursts(cast, pal, impact, impactMs, cast.to));
      break;
    case "aura":
      out.push(auraEffect(cast, pal, start, impact, impactMs));
      break;
  }
  return out;
}

/** 受擊閃白（暴擊加一圈金色外環）；光環類技能另在命中的單位身上爆發。 */
export function hitEffects(hit: VfxHit, now: number, impactMs: number, withBurst: boolean): Effect[] {
  const c = tileCenter(hit.pos);
  const g = new Graphics();
  const start = now + hit.atMs;
  const flash = effect(g, start, start + impactMs * 0.4, (t) => {
    const alpha = 1 - t;
    g.circle(c.x, c.y, T * 0.36 * (hit.crit ? 1.25 : 1)).fill({ color: 0xffffff, alpha: 0.85 * alpha });
    if (hit.crit) g.circle(c.x, c.y, T * (0.4 + 0.5 * t)).stroke({ width: 4, color: 0xffe066, alpha });
  });
  const out = [flash];
  if (withBurst) out.push(burstEffect(hit.pos, elementVfx(hit.element), start, impactMs, hit.crit ? 1.6 : 1, 0.8));
  return out;
}

/** 畫面震動：振幅隨時間遞減；`apply` 設定場景位移，結束時歸零。 */
export function shakeEffect(level: 1 | 2, startMs: number, durationMs: number, apply: (x: number, y: number) => void): Effect {
  const amp = level === 2 ? 7 : 3;
  return {
    node: new Container(),
    startMs,
    endMs: startMs + Math.max(1, durationMs),
    update: (t) => {
      const a = amp * (1 - t);
      apply(a * Math.sin(t * 47), a * Math.cos(t * 39));
    },
    end: () => apply(0, 0),
  };
}

// ---- 幾何 ------------------------------------------------------------------

function lerp(a: Pt, b: Pt, t: number): Pt {
  const k = Math.max(0, Math.min(1, t));
  return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k };
}

/** 折線的前 `k`（0–1）段長度。 */
function partialPath(pts: readonly Pt[], k: number): Pt[] {
  if (pts.length < 2) return [...pts];
  const lens = pts.slice(1).map((p, i) => Math.hypot(p.x - (pts[i] as Pt).x, p.y - (pts[i] as Pt).y));
  let left = lens.reduce((s, l) => s + l, 0) * k;
  const out: Pt[] = [pts[0] as Pt];
  for (let i = 1; i < pts.length; i += 1) {
    const len = lens[i - 1] as number;
    if (left >= len) {
      out.push(pts[i] as Pt);
      left -= len;
      continue;
    }
    if (len > 0) out.push(lerp(pts[i - 1] as Pt, pts[i] as Pt, left / len));
    break;
  }
  return out;
}

/** 鋸齒線（閃電）：每段中間點往法線方向偏移；`seed` 變動時形狀跟著跳動。 */
function jaggedLine(g: Graphics, a: Pt, b: Pt, seed: number, amp: number): void {
  const segs = Math.max(3, Math.round(Math.hypot(b.x - a.x, b.y - a.y) / 14));
  const nx = -(b.y - a.y);
  const ny = b.x - a.x;
  const nl = Math.hypot(nx, ny) || 1;
  g.moveTo(a.x, a.y);
  for (let i = 1; i < segs; i += 1) {
    const p = lerp(a, b, i / segs);
    const off = (jitter(i, seed) - 0.5) * 2 * amp;
    g.lineTo(p.x + (nx / nl) * off, p.y + (ny / nl) * off);
  }
  g.lineTo(b.x, b.y);
}
