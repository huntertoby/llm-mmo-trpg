// 技能特效的 PixiJS 繪圖（Phase 3-12）：把 `battle/vfx.ts` 的特效描述變成一組有起訖時間的動態效果。
// 每個效果一個 `Graphics`，每幀 `clear()` 後重畫（粒子數少，不需要粒子套件）；結束時由 `BattleRenderer`
// 的效果迴圈銷毀。座標一律是模型像素；格子中心由呼叫端的 `at` 給（3-19 起含高度抬高，預設 `tileCenter`）。
import { Container, Graphics } from "pixi.js";
import type { Pos } from "../api/types";
import { chebyshev, type VfxBlast, type VfxCast, type VfxHit, type VfxShake, type VfxWarp } from "../battle/vfx";
import { shakeOffset } from "../battle/impact";
import { jitter, particleAt, type ElementVfx, type ParticleKind } from "../battle/vfxPalette";
import { paletteOf } from "./statusVfx";
import { TILE_SIZE, tileCenter } from "../battle/geometry";
import { arcMirror, arcStrokes, type ArcSpec } from "./attackVariants";
import { spreadParticle, trajectoryPoint, type BurstShape, type Spread } from "./skillVariants";

const T = TILE_SIZE;

/** 一個動態效果：`update(t)` 傳入 0–1 的進度；`end()` 在移除前呼叫（還原震動等）。 */
/**
 * 6R-F：效果屬於哪一類動態（減少動態時怎麼處理，見 `reducedMotion.ts`）。
 * `body` ＝ 身體片段（跳到結果姿勢）；`fx` ＝ 弧光、殘影、火花（不畫）；`flash` ＝ 全畫面閃白；`shake` ＝ 震動；`dim` ＝ 四周變暗。
 * 沒標的（飛行物、爆發、數字、字樣…）照舊。
 */
export type MotionTag = "body" | "fx" | "flash" | "shake" | "dim";

export interface Effect {
  node: Container;
  startMs: number;
  endMs: number;
  update(t: number): void;
  end?(): void;
  motion?: MotionTag;
  /** 6H-1：`real` ＝ 照實際時間走（傷害數字：停頓、最後一擊放慢時照常速）；省略 ＝ 照效果時鐘。 */
  clock?: "real";
}

type Pt = { x: number; y: number };

/** 格子 → 畫面上的中心點（模型像素）。 */
export type Locate = (p: Pos) => Pt;

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

/** 爆發的樣子（6N-8 技能變體的特效層）：形狀、粒子分布、偏一側時往哪邊。沒有＝原本的圓形閃光＋均勻粒子。 */
interface BurstLook {
  shape: BurstShape;
  spread: Spread;
  side: 1 | -1;
}

/**
 * 6N-8：爆發形狀（放射、圓環、星形）疊在中心閃光上；大小不超過原本粒子的範圍（`reach`），顏色照元素。
 */
function burstShape(g: Graphics, c: Pt, shape: BurstShape, k: number, size: number, pal: ElementVfx): void {
  const alpha = 1 - k;
  if (shape === "ring") {
    g.ellipse(c.x, c.y, size * (0.25 + 0.75 * k), size * (0.16 + 0.46 * k)).stroke({ width: 4 * (1 - k) + 1, color: pal.primary, alpha });
    g.ellipse(c.x, c.y, size * (0.12 + 0.4 * k), size * (0.08 + 0.25 * k)).stroke({ width: 2, color: pal.secondary, alpha });
    return;
  }
  if (shape === "star") {
    const pts: number[] = [];
    for (let i = 0; i < 10; i += 1) {
      const a = -Math.PI / 2 + (i * Math.PI) / 5;
      const r = (i % 2 === 1 ? 0.28 : 0.6 + 0.4 * k) * size * (0.6 + 0.4 * k);
      pts.push(c.x + Math.cos(a) * r, c.y + Math.sin(a) * r);
    }
    g.poly(pts).fill({ color: pal.primary, alpha: 0.8 * alpha });
    return;
  }
  for (let i = 0; i < 8; i += 1) {
    const a = (i / 8) * Math.PI * 2;
    g.moveTo(c.x + Math.cos(a) * size * 0.2 * k, c.y + Math.sin(a) * size * 0.2 * k)
      .lineTo(c.x + Math.cos(a) * size * (0.3 + 0.7 * k), c.y + Math.sin(a) * size * (0.3 + 0.7 * k))
      .stroke({ width: 2.5, color: i % 2 === 0 ? pal.secondary : pal.primary, alpha });
  }
}

/** 一處爆發：中心閃光 ＋ 元素粒子（聖光另有光柱）。`scale` 是大小（1 ＝ 一格，範圍的每格較小）。`look`：6N-8 技能變體的形狀與粒子分布。 */
function burstEffect(pos: Pos, pal: ElementVfx, startMs: number, durationMs: number, intensity: number, scale: number, at: Locate, look?: BurstLook): Effect {
  const c = at(pos);
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
      if (look !== undefined) burstShape(g, c, look.shape, k, reach, pal);
    }
    for (let i = 0; i < n; i += 1) {
      const color = i % 3 === 0 ? pal.primary : pal.secondary;
      const p = particleAt(pal.particle, i, n, t, reach);
      drawParticle(g, pal.particle, c, look === undefined ? p : { ...p, ...spreadParticle(p, look.spread, t, reach, look.side) }, color);
    }
  });
}

/** 技能的爆發樣子（`VfxCast.look`）；偏一側 ＝ 往飛行的水平方向（正下、正上方往東）。 */
function burstLookOf(cast: VfxCast): BurstLook | undefined {
  const look = cast.look;
  if (look === undefined) return undefined;
  return { shape: look.burst, spread: look.spread, side: cast.to.x < cast.from.x ? -1 : 1 };
}

// ---- 各種特效 ---------------------------------------------------------------

/** 施放前的蓄力光：施放者身上的光暈逐漸變亮，命中前淡出。 */
function chargeEffect(cast: VfxCast, pal: ElementVfx, now: number, at: Locate): Effect {
  const c = at(cast.from);
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

function travelStart(cast: VfxCast, now: number): number {
  return now + cast.startMs + cast.chargeMs;
}

const LEGENDARY_GOLD = 0xffbf3a;

/**
 * 傳說技能的蓄力（3-18b）：在一般蓄力光之外，金色的光點從四周向施放者匯聚、兩圈反向旋轉的符文環、
 * 一道往上升的光柱；越接近釋放越亮。
 */
function legendaryChargeEffect(cast: VfxCast, pal: ElementVfx, now: number, at: Locate): Effect {
  const c = at(cast.from);
  const g = new Graphics();
  const start = now + cast.startMs;
  const end = now + Math.max(cast.startMs + 1, cast.startMs + cast.chargeMs);
  const motes = 14;
  return effect(g, start, end, (t) => {
    const glow = Math.min(1, t * 1.6);
    g.rect(c.x - T * 0.14, c.y - T * 1.5 * glow, T * 0.28, T * 1.5 * glow).fill({ color: pal.secondary, alpha: 0.22 * glow });
    for (const [dir, radius, color] of [
      [1, T * 0.62, LEGENDARY_GOLD],
      [-1, T * 0.8, pal.primary],
    ] as const) {
      const spin = dir * t * Math.PI * 3;
      for (let i = 0; i < 8; i += 1) {
        const a = spin + (i / 8) * Math.PI * 2;
        const x = c.x + Math.cos(a) * radius * (1 - t * 0.25);
        const y = c.y + Math.sin(a) * radius * 0.55 * (1 - t * 0.25);
        g.circle(x, y, 2.4).fill({ color, alpha: 0.35 + 0.55 * glow });
      }
    }
    for (let i = 0; i < motes; i += 1) {
      const lag = jitter(i, 5) * 0.4;
      const k = Math.max(0, Math.min(1, (t - lag) / (1 - lag)));
      const a = (i / motes) * Math.PI * 2 + jitter(i, 6);
      const r = T * (1.3 - 1.15 * k);
      g.circle(c.x + Math.cos(a) * r, c.y + Math.sin(a) * r * 0.7 - T * 0.1, 1.8 + 1.6 * k).fill({ color: i % 2 === 0 ? LEGENDARY_GOLD : 0xffffff, alpha: Math.sin(Math.PI * Math.min(1, k + 0.05)) });
    }
    g.circle(c.x, c.y, T * (0.3 + 0.35 * glow)).stroke({ width: 3, color: LEGENDARY_GOLD, alpha: 0.7 * glow });
  });
}

// ---- 傳送的消散與出現（3-18b） ------------------------------------------------

/** 起點消散：光環往內收、微粒往上飄散；終點出現：光環往外擴、微粒從中心湧出。 */
function warpEffect(w: VfxWarp, now: number, at: Locate): Effect {
  const c = at(w.pos);
  const g = new Graphics();
  const pal = BANISH;
  const n = 10;
  return effect(g, now + w.startMs, now + w.endMs, (t) => {
    const vanish = w.kind === "vanish";
    const k = vanish ? t : 1 - t;
    g.circle(c.x, c.y + T * 0.2, T * (0.15 + 0.4 * (vanish ? 1 - t : t))).stroke({ width: 3, color: pal.primary, alpha: 0.9 * (vanish ? 1 - t * 0.4 : 1 - t) });
    g.ellipse(c.x, c.y + T * 0.2, T * 0.34 * (1 - k * 0.3), T * 0.14).fill({ color: pal.secondary, alpha: 0.35 * (vanish ? 1 - t : t < 0.5 ? t * 2 : 2 - t * 2) });
    for (let i = 0; i < n; i += 1) {
      const p = particleAt("sparkle", i, n, vanish ? t : 1 - t, T * 0.7);
      const dir = vanish ? 1 : -1;
      g.circle(c.x + p.x * dir, c.y + p.y, p.size).fill({ color: i % 2 === 0 ? pal.primary : 0xffffff, alpha: p.alpha });
    }
  });
}

/** 傳送類位移的特效（`battle/vfx.warpPlan` 算出的消散與出現）。 */
export function warpEffects(plan: readonly VfxWarp[], now: number, at: Locate = tileCenter): Effect[] {
  return plan.map((w) => warpEffect(w, now, at));
}

const BANISH: ElementVfx = { primary: 0xb890ff, secondary: 0x6a4cc8, particle: "sparkle", particles: 10, jagged: false, column: false };

/** 遠程單體：飛行物（拖尾 3 顆；雷改成鋸齒軌跡）。6N-8：技能照 `look.trail` 走微弧、直線或螺旋，終點一律是目標格。 */
function projectileEffect(cast: VfxCast, pal: ElementVfx, start: number, end: number, at: Locate): Effect {
  const a = at(cast.from);
  const b = at(cast.to);
  const g = new Graphics();
  const r = 6 * cast.intensity;
  const trail = cast.look?.trail;
  const along = (t: number): Pt => (trail === undefined ? lerp(a, b, t) : trajectoryPoint(a, b, t, trail, T));
  return effect(g, start, end, (t) => {
    const head = along(t);
    if (pal.jagged) {
      jaggedLine(g, a, head, Math.floor(t * 30), 6);
      g.stroke({ width: 2, color: pal.secondary, alpha: 0.9 });
    }
    for (let k = 3; k >= 1; k -= 1) {
      const p = along(Math.max(0, t - k * 0.07));
      g.circle(p.x, p.y, r * (1 - k * 0.2)).fill({ color: pal.secondary, alpha: 0.5 - k * 0.12 });
    }
    g.circle(head.x, head.y, r * 1.6).fill({ color: pal.primary, alpha: 0.35 });
    g.circle(head.x, head.y, r).fill({ color: pal.primary, alpha: 1 });
    g.circle(head.x, head.y, r * 0.45).fill({ color: 0xffffff, alpha: 0.9 });
  });
}

/** 暴擊弧光的金色（6N-5）。 */
export const CRIT_GOLD = 0xffc93a;

/** 近戰單體：在目標身上揮出一道弧（垂直於攻擊方向掃過）。 */
function slashEffect(cast: VfxCast, pal: ElementVfx, start: number, end: number, at: Locate): Effect {
  const a = at(cast.from);
  const b = at(cast.to);
  const g = new Graphics();
  const dir = Math.atan2(b.y - a.y, b.x - a.x);
  const radius = T * 0.42 * cast.intensity;
  const sweep = Math.PI * 0.9;
  const from = dir - sweep / 2;
  if (cast.arc !== undefined) return variantSlash(g, cast, cast.arc, pal, start, end, a, b, radius);
  return effect(g, start, end, (t) => {
    const grow = Math.min(1, t * 2);
    const fade = t < 0.5 ? 1 : 1 - (t - 0.5) / 0.5;
    const a0 = from;
    const a1 = from + sweep * grow;
    const cx = b.x - Math.cos(dir) * T * 0.15;
    const cy = b.y - Math.sin(dir) * T * 0.15;
    // 6N-5：暴擊的弧光加粗、變金色
    g.moveTo(cx + Math.cos(a0) * radius, cy + Math.sin(a0) * radius)
      .arc(cx, cy, radius, a0, a1)
      .stroke({ width: (cast.crit ? 9 : 7) * cast.intensity, color: cast.crit ? CRIT_GOLD : pal.primary, alpha: (cast.crit ? 0.75 : 0.55) * fade });
    g.moveTo(cx + Math.cos(a0) * radius, cy + Math.sin(a0) * radius)
      .arc(cx, cy, radius, a0, a1)
      .stroke({ width: cast.crit ? 3.5 : 2.5, color: cast.crit ? 0xfff6c8 : 0xffffff, alpha: fade });
  });
}

/**
 * 6N-6：普攻變體的弧光（由下往上、橫掃、突刺、交叉、迴旋）。形狀與方向照 `attackVariants.arcStrokes`（本地座標朝東，
 * 往西打左右鏡像），中心和半徑同原本的弧；暴擊同樣加粗、變金色。
 */
function variantSlash(g: Graphics, cast: VfxCast, spec: ArcSpec, pal: ElementVfx, start: number, end: number, a: Pt, b: Pt, radius: number): Effect {
  const dir = Math.atan2(b.y - a.y, b.x - a.x);
  const mirror = arcMirror(b.x - a.x, b.y - a.y);
  const cx = b.x - Math.cos(dir) * T * 0.15;
  const cy = b.y - Math.sin(dir) * T * 0.15;
  const toScreen = (p: readonly [number, number]): Pt => ({ x: cx + p[0] * radius * mirror, y: cy + p[1] * radius });
  return effect(g, start, end, (t) => {
    const grow = Math.min(1, t * 2);
    const fade = t < 0.5 ? 1 : 1 - (t - 0.5) / 0.5;
    const strokes = arcStrokes(spec, grow).map((s) => s.map(toScreen));
    const layers: ReadonlyArray<[number, number, number]> = [
      [(cast.crit ? 9 : 7) * cast.intensity, cast.crit ? CRIT_GOLD : pal.primary, (cast.crit ? 0.75 : 0.55) * fade],
      [cast.crit ? 3.5 : 2.5, cast.crit ? 0xfff6c8 : 0xffffff, fade],
    ];
    for (const [width, color, alpha] of layers) {
      for (const s of strokes) {
        s.forEach((p, i) => (i === 0 ? g.moveTo(p.x, p.y) : g.lineTo(p.x, p.y)));
        g.stroke({ width, color, alpha });
      }
    }
  });
}

/** 直線、連鎖：光束沿路徑延伸到底，命中後變細淡出（雷為鋸齒）。 */
function beamEffect(cast: VfxCast, pal: ElementVfx, start: number, impact: number, impactMs: number, at: Locate): Effect {
  const pts = cast.path.map((p) => at(p));
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
function coneEffect(cast: VfxCast, pal: ElementVfx, start: number, impact: number, impactMs: number, at: Locate): Effect {
  const a = at(cast.from);
  const b = at(cast.to);
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
function auraEffect(cast: VfxCast, pal: ElementVfx, start: number, impact: number, impactMs: number, at: Locate): Effect {
  const c = at(cast.from);
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
function tileFlash(pos: Pos, pal: ElementVfx, start: number, durationMs: number, at: Locate): Effect {
  const c = at(pos);
  const g = new Graphics();
  return effect(g, start, start + durationMs, (t) => {
    const alpha = t < 0.25 ? t / 0.25 : 1 - (t - 0.25) / 0.75;
    g.rect(c.x - T / 2 + 2, c.y - T / 2 + 2, T - 4, T - 4).fill({ color: pal.primary, alpha: 0.35 * alpha });
  });
}

/** 範圍的各格依與中心（或施放者）的距離錯開爆發；每格的粒子較少。 */
function tileBursts(cast: VfxCast, pal: ElementVfx, impact: number, impactMs: number, origin: Pos, at: Locate): Effect[] {
  const out: Effect[] = [];
  const stagger = impactMs * 0.08;
  const scale = cast.tiles.length > 1 ? 0.6 : 1;
  for (const p of cast.tiles) {
    const delay = chebyshev(p, origin) * stagger;
    out.push(tileFlash(p, pal, impact + delay, impactMs * 0.7, at));
    out.push(burstEffect(p, pal, impact + delay, impactMs, cast.intensity, scale, at, burstLookOf(cast)));
  }
  return out;
}

/** 一個特效描述 → 一組動態效果（`now` 是目前的效果時鐘；描述內的時間已依播放速度縮放）。 */
export function castEffects(cast: VfxCast, now: number, impactMs: number, at: Locate = tileCenter): Effect[] {
  const pal = paletteOf(cast.element);
  const out: Effect[] = [];
  if (cast.charge) out.push(chargeEffect(cast, pal, now, at));
  if (cast.legendary) out.push(legendaryChargeEffect(cast, pal, now, at));
  const start = travelStart(cast, now);
  const impact = Math.max(start, now + cast.impactMs);
  switch (cast.kind) {
    case "projectile":
      out.push(projectileEffect(cast, pal, start, impact, at), burstEffect(cast.to, pal, impact, impactMs, cast.intensity, 1, at, burstLookOf(cast)));
      break;
    case "slash":
      out.push({ ...slashEffect(cast, pal, start, impact + impactMs * 0.4, at), motion: "fx" }, burstEffect(cast.to, pal, impact, impactMs, cast.intensity, 0.8, at, burstLookOf(cast)));
      break;
    case "burst":
      out.push(burstEffect(cast.to, pal, impact, impactMs, cast.intensity, 1, at, burstLookOf(cast)));
      break;
    case "beam":
      out.push(beamEffect(cast, pal, start, impact, impactMs, at), ...tileBursts(cast, pal, impact, impactMs, cast.from, at));
      break;
    case "cone":
      out.push(coneEffect(cast, pal, start, impact, impactMs, at), ...tileBursts(cast, pal, impact, impactMs, cast.from, at));
      break;
    case "area":
      out.push(...tileBursts(cast, pal, impact, impactMs, cast.to, at));
      break;
    case "aura":
      out.push(auraEffect(cast, pal, start, impact, impactMs, at));
      break;
  }
  return out;
}

/** 受擊閃白（暴擊加一圈金色外環）；光環類技能另在命中的單位身上爆發。`circle` 為假（異形，6M-3）時不畫白圓——改由戰場只閃角色的剪影。 */
export function hitEffects(hit: VfxHit, now: number, impactMs: number, withBurst: boolean, at: Locate = tileCenter, circle = true): Effect[] {
  const c = at(hit.pos);
  const g = new Graphics();
  const start = now + hit.atMs;
  const flash = effect(g, start, start + impactMs * 0.4, (t) => {
    const alpha = 1 - t;
    if (circle) g.circle(c.x, c.y, T * 0.36 * (hit.crit ? 1.25 : 1)).fill({ color: 0xffffff, alpha: 0.85 * alpha });
    if (hit.crit) g.circle(c.x, c.y, T * (0.4 + 0.5 * t)).stroke({ width: 4, color: 0xffe066, alpha });
  });
  const out = [flash];
  if (withBurst) out.push(burstEffect(hit.pos, paletteOf(hit.element), start, impactMs, hit.crit ? 1.6 : 1, 0.8, at));
  return out;
}

/** 符文被引爆（3-28）：在符文格迸出元素色的爆發（沿用爆發型，比一般命中大一點）。 */
export function blastEffect(blast: VfxBlast, now: number, impactMs: number, at: Locate = tileCenter): Effect {
  return burstEffect(blast.pos, paletteOf(blast.element), now + blast.atMs, impactMs, 1.3, 1.2, at);
}

/**
 * 畫面震動：振幅 `px`（畫面像素）隨時間遞減；`apply` 設定場景位移，結束時歸零。
 * 6H-1 起只剩升地形的輕震（1 px）用它；命中的微震用 `impactShakeEffect`。
 */
export function shakeEffect(px: number, startMs: number, durationMs: number, apply: (x: number, y: number) => void): Effect {
  const amp = px;
  return {
    node: new Container(),
    startMs,
    endMs: startMs + Math.max(1, durationMs),
    motion: "shake",
    update: (t) => {
      const a = amp * (1 - t);
      apply(a * Math.sin(t * 47), a * Math.cos(t * 39));
    },
    end: () => apply(0, 0),
  };
}

/**
 * 命中的鏡頭微震（6H-1；只有重擊、爆炸、Boss 大招，`battle/impact.ts`）：一步一個效果，涵蓋這一步所有的震，
 * 每一刻取幅度最大的那個（不疊加）；`now` 是效果時鐘上這一步的原點。沒有震時 `null`。
 */
export function impactShakeEffect(shakes: readonly VfxShake[], now: number, apply: (x: number, y: number) => void): Effect | null {
  if (shakes.length === 0) return null;
  const start = Math.min(...shakes.map((s) => s.atMs));
  const end = Math.max(...shakes.map((s) => s.atMs + s.ms));
  const span = Math.max(1, end - start);
  return {
    node: new Container(),
    startMs: now + start,
    endMs: now + start + span,
    motion: "shake",
    update: (t) => {
      const o = shakeOffset(shakes, start + t * span);
      apply(o.x, o.y);
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
