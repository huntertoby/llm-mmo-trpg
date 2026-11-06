// 武器待機的疊加層（QK-7；需求 docs/art/武器待機移植需求.md 第 1 節「量化」）：杖頭光、法球浮沉、魔導劍符文光不量化、不換貼圖，
// 每幀照時鐘即時畫在小人貼圖上面。這裡只算「畫什麼」（小人座標：腳底在 (0,0)、單位同樣張），Pixi 與 Canvas 各自照這份清單畫。
// - 錨點：用 Q 版畫法的 probe 拿到武器座標 → 小人座標的矩陣（握把在原點、作用端朝 −y），同裝備、同朝向、同一格只算一次。
// - 法杖：貼圖照 glow 0 畫（光暈 0.35、半徑 6.5），疊加層補上 glow 的增量，再把光點與高光蓋回去。
// - 法球：貼圖不畫法球（`glowLayer: 1`），疊加層整顆畫（光暈、外框、球、高光），跟著 orbY 浮沉。
// - 魔導劍：源晶槽外面疊兩圈半透明的光（代替 shadowBlur 的增量），符文蓋回去。
import type { Ctx } from "./artDraw";
import { Q_OUT, type M6, type QHooks, type QItem, type QPose, type QUnit, type QView } from "./qCore";
import { drawQ } from "./qDoll";
import { arcaneGlowColor, orbColor, qWeapon, staffOrbColor } from "./qWeapons";
import type { WeaponIdleKind } from "./idleWeapons";

export type GlowKind = "staff" | "orb" | "arcane_blade";

export interface GlowAnchor {
  kind: GlowKind;
  /** 武器座標 → 小人座標。 */
  m: M6;
  color: string;
}

export interface GlowShape {
  /** 圓（小人座標）：[x, y, r]。 */
  circle?: readonly [number, number, number];
  /** 多邊形（小人座標）：[x0, y0, x1, y1, …]。 */
  poly?: readonly number[];
  color: string;
  alpha: number;
}

/** 這種待機有沒有疊加層、在這個朝向畫不畫：背面的法球、魔導劍在身體前面被擋住，不畫（貼圖照舊，光不脈動）。 */
export function glowKindOf(kind: WeaponIdleKind | null, view: QView): GlowKind | null {
  if (kind === "staff") return "staff";
  if (view === "back") return null;
  if (kind === "orb") return "orb";
  if (kind === "arcane_blade") return "arcane_blade";
  return null;
}

/**
 * 量錨點：在 `ctx`（任何有 getTransform 的 2D 畫布；只用來追蹤變換，畫在哪裡無所謂）照遊戲的畫法跑一次，
 * 拿主手武器的矩陣。`ctx` 的變換會被重設。
 */
export function probeGlowAnchor(ctx: Ctx, unit: QUnit, view: QView, west: boolean, hooks: QHooks, pose: QPose, kind: GlowKind): GlowAnchor | null {
  let m: M6 | null = null;
  ctx.save();
  ctx.setTransform(west ? -1 : 1, 0, 0, 1, 0, 0);
  drawQ(ctx, unit, view, hooks, { ...pose, probe: (k, _h, _t, _v, _o, mm) => (m === null && k === kind ? (m = mm) : null) }, west);
  ctx.restore();
  if (m === null) return null;
  const it: QItem | undefined = qWeapon(unit.gear.main_hand)?.item;
  const color = kind === "staff" ? staffOrbColor(it) : kind === "orb" ? orbColor(it) : arcaneGlowColor(it, hooks.tint);
  return { kind, m, color };
}

const tp = (m: M6, x: number, y: number): [number, number] => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
const scaleOf = (m: M6): number => Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) || 1;

function circle(a: GlowAnchor, x: number, y: number, r: number, color: string, alpha: number): GlowShape {
  const [cx, cy] = tp(a.m, x, y);
  return { circle: [cx, cy, r * scaleOf(a.m)], color, alpha };
}
function rect(a: GlowAnchor, x: number, y: number, w: number, h: number, color: string, alpha: number): GlowShape {
  const pts = [tp(a.m, x, y), tp(a.m, x + w, y), tp(a.m, x + w, y + h), tp(a.m, x, y + h)].flat();
  return { poly: pts, color, alpha };
}

/** 法杖光暈在 glow 0 時已經畫進貼圖的透明度；疊加層補到 0.35＋0.35×glow。 */
const STAFF_BASE = 0.35;

/** 這一刻要疊的形狀（小人座標，依序畫）。`glow` 0～1、`orbY` 單位。 */
export function glowShapes(a: GlowAnchor, glow: number, orbY: number): GlowShape[] {
  const g = Math.max(0, Math.min(1, glow));
  if (a.kind === "staff") {
    // 合成：底下已有 0.35 → 疊 x 使 1 −（1 − 0.35）（1 − x）＝ 0.35 ＋ 0.35g
    const x = (STAFF_BASE * g) / (1 - STAFF_BASE);
    const out: GlowShape[] = [];
    if (x > 0.001) out.push(circle(a, 0, -32, 6.5 + 2 * g, a.color, x));
    out.push(circle(a, 0, -32, 3.6, a.color, 1), circle(a, -1.2, -33.2, 1.1, "#ffffff", 0.8));
    return out;
  }
  if (a.kind === "orb") {
    const oy = -3.4 + orbY;
    const halo = 0.35 + 0.35 * g;
    const R = 6 + 2 * g;
    return [
      // 樣張的光暈也算剪影：外框色墊在光暈下面（同透明度），外圈多 1.3
      circle(a, 0, oy, R + 1.3, Q_OUT, halo),
      circle(a, 0, oy, R, a.color, halo),
      circle(a, 0, oy, 3.6 + 1.3, Q_OUT, 1),
      circle(a, 0, oy, 3.6, a.color, 1),
      circle(a, -1.2, oy - 1.2, 1.1, "#ffffff", 0.8),
    ];
  }
  // 魔導劍：源晶槽 (−0.55, −15)～(0.55, −4)（劍長 16）；shadowBlur 4 → 4 ＋ 8g 的增量用兩圈半透明的光代替
  const out: GlowShape[] = [];
  if (g > 0.001) out.push(rect(a, -1.9, -16.3, 3.8, 13.6, a.color, 0.18 * g), rect(a, -1.1, -15.6, 2.2, 12.2, a.color, 0.3 * g));
  for (const ry of [-6.5, -10, -13.5]) out.push(rect(a, -1.1, ry, 2.2, 0.8, "#e8e2ff", 1));
  return out;
}

/** 在 Canvas 2D 照清單畫（畫廊用；ctx 的座標系 ＝ 小人座標）。 */
export function paintGlow(ctx: Ctx, shapes: readonly GlowShape[]): void {
  for (const s of shapes) {
    ctx.save();
    ctx.globalAlpha *= s.alpha;
    ctx.fillStyle = s.color;
    ctx.beginPath();
    if (s.circle) ctx.arc(s.circle[0], s.circle[1], s.circle[2], 0, Math.PI * 2);
    else if (s.poly) {
      for (let i = 0; i + 1 < s.poly.length; i += 2) ctx.lineTo(s.poly[i]!, s.poly[i + 1]!);
      ctx.closePath();
    }
    ctx.fill();
    ctx.restore();
  }
}
