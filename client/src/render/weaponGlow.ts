// 武器待機的疊加層（QK-7；需求 docs/art/武器待機移植需求.md 第 1 節「量化」）：杖頭光、魔導劍符文光不量化、不換貼圖，
// 每幀照時鐘即時畫在小人貼圖上面。這裡只算「畫什麼」（小人座標：腳底在 (0,0)、單位同樣張），Pixi 與 Canvas 各自照這份清單畫。
// - 錨點：用 Q 版畫法的 probe 拿到武器座標 → 小人座標的矩陣（握把在原點、作用端朝 −y），同裝備、同朝向、同一格只算一次。
// - 法杖：貼圖不畫杖頭光暈（`glowLayer: 1`），疊加層畫光暈（墊外框色）、再把光點與高光蓋回去。
// - 法球不走疊加層：樣張裡持球的手畫在法球上面，疊上去會蓋住手；glow、orbY 跟著 8 格放進貼圖（idleWeapons 的 `live: false`）。
// - 魔導劍：源晶槽外面疊兩圈半透明的光（代替 shadowBlur 的增量），符文蓋回去。
import type { Ctx } from "./artDraw";
import { Q_OUT, type M6, type QHooks, type QItem, type QPose, type QUnit, type QView } from "./qCore";
import { drawQ } from "./qDoll";
import { arcaneGlowColor, qWeapon, staffOrbColor } from "./qWeapons";
import type { WeaponIdleKind } from "./idleWeapons";

export type GlowKind = "staff" | "arcane_blade";

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

/** 這種待機有沒有疊加層、在這個朝向畫不畫：背面的魔導劍在身體前面被擋住，不疊（光跟著 8 格放進貼圖）。 */
export function glowKindOf(kind: WeaponIdleKind | null, view: QView): GlowKind | null {
  if (kind === "staff") return "staff";
  if (kind === "arcane_blade" && view !== "back") return "arcane_blade";
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
  const color = kind === "staff" ? staffOrbColor(it) : arcaneGlowColor(it, hooks.tint);
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

/** 這一刻要疊的形狀（小人座標，依序畫）。`glow` 0～1。 */
export function glowShapes(a: GlowAnchor, glow: number): GlowShape[] {
  const g = Math.max(0, Math.min(1, glow));
  if (a.kind === "staff") {
    // 貼圖不畫光暈（glowLayer）；樣張的光暈也算剪影，外框色（同透明度、外圈多 1.3）墊在光暈下面
    const h = 0.35 + 0.35 * g;
    const R = 6.5 + 2 * g;
    return [circle(a, 0, -32, R + 1.3, Q_OUT, h), circle(a, 0, -32, R, a.color, h), circle(a, 0, -32, 3.6, a.color, 1), circle(a, -1.2, -33.2, 1.1, "#ffffff", 0.8)];
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
