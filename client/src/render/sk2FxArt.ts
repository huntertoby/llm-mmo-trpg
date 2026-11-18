// SK-2 三個新原語的戰鬥演出畫法（AR-SK2；Canvas2D，世界座標＝模型像素、1 格 48）。
// 由 docs/art/sample/sk2Primitives.js 第 2 版（鎖鏈、鉤頭、微粒、撞擊星、地上的 V）與 sk2-primitives.html 的
// sceneAbsorb／sceneContagion／sceneHook（時間軸）逐段搬；紀錄 docs/art/SK-2原語-美術.md 第 2 節與「第 2 版」可修 1、2、4、5、7。
// 和樣張不同的地方（都不改畫法）：
// - 樣張畫整個場景；這裡只畫特效，單位、表面由遊戲端現行畫法畫（倒下用現行的倒下片段、表面縮小用 `surfaceAnim` 的消失）。
// - 位置不寫死：施放者的手、目標胸口、格子由呼叫端給（`Sk2AbsorbGeom` 等）；目標被拉時跟著實際的單位走。
// - 畫面下限 K（移植需求第 5 項）由呼叫端照地圖縮放算（`chainMinK`），不是模組層的全域狀態。
// 確定性：沒有 Math.random；只吃時間 t（毫秒，正常速度）。
import { ci, el, flame, glow, OUT, poly, rr, starPts, TAU, type Ctx, type QOpts } from "./qIcon/core";
import { drop } from "./qIcon/legacy48";
import { HOOK, hookJ, link } from "./qIcon/parts";
import { GERM_COLORS } from "./palette";

const PI = Math.PI;
export const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
export const ease = (t: number): number => {
  const c = clamp(t);
  return c * c * (3 - 2 * c);
};
export const span = (t: number, a: number, b: number): number => clamp((t - a) / (b - a));
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export interface Pt {
  x: number;
  y: number;
}

// =====================================================================
// 畫面下限（移植需求第 5 項；美術第 2 版可修 d、7）
// =====================================================================
/** 鏈節長（模型 px）與畫面下限（畫面 px）。 */
export const LINK_LEN = 4.2;
export const LINK_MIN_PX = 3;
/** K＝max(1, 3 ÷ (4.2 × 地圖縮放))：鏈節、間距、外框、鉤頭、擴散的虛線、箭頭與地上的 V 都乘它（1600 寬 1.00、800 寬 1.35）。 */
export function chainMinK(boardScale: number): number {
  if (!(boardScale > 0)) return 1;
  return Math.max(1, LINK_MIN_PX / (LINK_LEN * boardScale));
}

// =====================================================================
// 鎖鏈與鉤頭
// =====================================================================
const STEEL = HOOK.body;
const STEEL_D = HOOK.dark;
const path = (ctx: Ctx, pts: readonly (readonly [number, number])[]): void => {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
};

export interface ChainOpt {
  phase?: number;
  glow?: number;
  rim?: number;
}

/** 鎖鏈：沿折線每 3.6×K 一節，交錯正面／側面；先整條畫外框色粗線，再畫鏈節。`glow` 繃緊時底下的白光、`rim` 外圈 1 px 米白亮邊。 */
export function chain(ctx: Ctx, pts: readonly (readonly [number, number])[], K: number, opt: ChainOpt = {}): void {
  const step = 3.6 * K, L = LINK_LEN * K, glowA = opt.glow ?? 0;
  const seg: number[] = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1] as readonly [number, number], b = pts[i] as readonly [number, number];
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
    seg.push(d);
    total += d;
  }
  if (total < 0.5) return;
  const pos = (s0: number): [number, number, number] => {
    let s = s0, i = 0;
    while (i < seg.length - 1 && s > (seg[i] as number)) {
      s -= seg[i] as number;
      i++;
    }
    const len = seg[i] as number, t = len ? s / len : 0, a = pts[i] as readonly [number, number], b = pts[i + 1] as readonly [number, number];
    return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), Math.atan2(b[1] - a[1], b[0] - a[0])];
  };
  const stroke = (col: string, w: number, alpha: number): void => {
    ctx.save();
    ctx.globalAlpha *= alpha;
    path(ctx, pts);
    ctx.strokeStyle = col;
    ctx.lineWidth = w;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
    ctx.restore();
  };
  if (glowA > 0) stroke("#ffffff", 5, glowA);
  if (opt.rim) stroke("#fff6d0", L * 0.68 + 1.6 + 2, opt.rim);
  stroke(OUT, L * 0.68 + 1.6, 1);
  const n = Math.max(1, Math.floor(total / step)), off = opt.phase ?? 0;
  for (let k = 0; k <= n; k++) {
    const s = Math.min(total, k * step + (((off % step) + step) % step));
    const [x, y, a] = pos(s);
    link(ctx, x, y, a, L, (k + Math.floor(off / step)) % 2 !== 0, STEEL, STEEL_D, OUT);
  }
}

/** 戰場的鉤頭只用到 `tiny`（樣張傳 `{ tiny: false }`）。 */
const HEAD_OPTS: QOpts = { small: false, tiny: false, owPx: 0, badge: false, u: 1 };
/** 戰場上的爪鉤：繩環在 (x,y)、爪朝 a 方向；k＝圖樣 1 單位幾個模型 px（再乘 K）。 */
export function hookHead(ctx: Ctx, x: number, y: number, a: number, k: number, K: number): void {
  const s = k * K;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(a + PI / 2);
  ctx.scale(s, s);
  ctx.translate(0, -9.4);
  hookJ(ctx, HEAD_OPTS, OUT, 2.6 / s, true);
  hookJ(ctx, HEAD_OPTS, STEEL, 0, false);
  ctx.restore();
}

// =====================================================================
// 特效小零件
// =====================================================================
const FIRE = ["#ff6a1a", "#ffd23f"] as const;
const BLOOD = ["#e8455a", "#ffb0b8"] as const;
const POISON = ["#7ddc3a", "#d6f59a"] as const;
/** 疾病擴散時飛過去的那一團：燃燒＝一小團火、流血＝一滴、中毒＝一顆泡；其他狀態照燃燒。 */
export function moteKind(statusId: string): "burning" | "bleed" | "poison" {
  return statusId === "bleed" || statusId === "poison" ? statusId : "burning";
}
export function mote(ctx: Ctx, kind: string, x: number, y: number, s: number, a = 1, dir = 0): void {
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.translate(x, y);
  if (kind === "bleed") {
    ctx.rotate(dir - PI / 2);
    ctx.scale(s / 10, s / 10);
    drop(ctx, OUT, 0, 0, 1.22);
    drop(ctx, BLOOD[0], 0, 0, 1);
    el(ctx, BLOOD[1], -2.4, 3, 1.6, 2.8, 0.3);
  } else if (kind === "poison") {
    ctx.scale(s / 10, s / 10);
    ci(ctx, OUT, 0, 0, 9.4);
    ci(ctx, POISON[0], 0, 0, 8);
    ci(ctx, POISON[1], -2.6, -2.8, 2.6);
    ci(ctx, OUT, 7.4, -7.4, 4);
    ci(ctx, POISON[0], 7.4, -7.4, 2.8);
  } else {
    ctx.rotate(dir + PI / 2);
    ctx.scale(s / 10, s / 10);
    flame(ctx, OUT, 0, 0, 1.22);
    flame(ctx, FIRE[0], 0, 0, 1.0);
    flame(ctx, FIRE[1], 0.4, 2.6, 0.58);
  }
  ctx.restore();
}

/** 撞擊星（同第③批「擊倒」的黃白七角星）＋往外飛的碎片。p＝0～1。 */
export function impactStar(ctx: Ctx, x: number, y: number, p: number, R = 15): void {
  const k = p < 0.3 ? ease(p / 0.3) : 1 - ease((p - 0.3) / 0.7) * 0.35, a = p < 0.7 ? 1 : 1 - (p - 0.7) / 0.3;
  ctx.save();
  ctx.globalAlpha *= a;
  poly(ctx, OUT, starPts(x, y, R * k + 1.6, R * k * 0.48 + 1.6, 7, -1.2));
  poly(ctx, "#ffd23f", starPts(x, y, R * k, R * k * 0.48, 7, -1.2));
  poly(ctx, "#ffffff", starPts(x, y, R * k * 0.5, R * k * 0.24, 7, -1.2));
  for (let i = 0; i < 6; i++) {
    const ang = -1.2 + (i / 6) * TAU + 0.3, d = R * (0.9 + 1.1 * ease(p));
    rr(ctx, "#fff0b0", x + Math.cos(ang) * d - 1.2, y + Math.sin(ang) * d - 1.2, 2.4, 2.4, 0.8);
  }
  ctx.restore();
}

/** 地上的方向箭頭：從 a 到 b 一列三個 V（病菌黃綠），p＝0～1 依序亮起；大小乘 K。 */
export function chevrons(ctx: Ctx, a: Pt, b: Pt, p: number, K: number, col: string = GERM_COLORS.knob): void {
  const dx = b.x - a.x, dy = b.y - a.y, ang = Math.atan2(dy, dx);
  for (let i = 0; i < 3; i++) {
    const t = 0.3 + i * 0.2, on = clamp((p - i * 0.18) / 0.3);
    if (on <= 0) continue;
    ctx.save();
    ctx.translate(a.x + dx * t, a.y + dy * t);
    ctx.rotate(ang);
    ctx.scale(K, K);
    ctx.globalAlpha *= on * (1 - clamp((p - 0.85) / 0.15));
    const v = (c: string, w: number): void => {
      ctx.beginPath();
      ctx.moveTo(-3.4, -4.4);
      ctx.lineTo(1.6, 0);
      ctx.lineTo(-3.4, 4.4);
      ctx.strokeStyle = c;
      ctx.lineWidth = w;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.stroke();
    };
    v(OUT, 4.4);
    v(col, 2.4);
    ctx.restore();
  }
}

// =====================================================================
// 吸收表面（美術 2.1、第 2 版可修 1、6）：0–1000 ms
// =====================================================================
export const ABSORB_MS = 1000;
/** 表面往中心收縮（沿用 `surfaceAnim` 的消失；150–520）。 */
export const ABSORB_SHRINK = { from: 150, to: 520 } as const;

export interface Sk2AbsorbGeom {
  /** 被吸的那一格中心。 */
  base: Pt;
  /** 施放者的副手（冰晶、光柱收進去的地方）。 */
  hand: Pt;
  /** 施放者頭頂（腳底往上 52）。 */
  head: Pt;
  /** 法杖頭（元素收益時染色）；沒有時不畫。 */
  staff: Pt | null;
  /** 表面色（本色、亮色）。 */
  tint: readonly [string, string];
  /** 收益的圖樣（16 px 的部件圖樣 canvas）與它的邊長（模型 px）。 */
  glyph: HTMLCanvasElement | null;
  glyphPx: number;
  /** 收益是元素（法杖頭染色）。 */
  element: boolean;
}

/** 光柱的兩條邊（單位之下整片、之上只畫邊線）。 */
function columnAt(g: Sk2AbsorbGeom, q: number, side: number): Pt {
  const w0 = 21, w1 = 4, u = 1 - q, x0 = g.base.x + side * w0, y0 = g.base.y + 4, cx = g.base.x + side * w0 * 0.3, cy = g.base.y - 6, x1 = g.hand.x + side * w1, y1 = g.hand.y;
  return { x: u * u * x0 + 2 * u * q * cx + q * q * x1, y: u * u * y0 + 2 * u * q * cy + q * q * y1 };
}
const columnAlpha = (t: number): number => span(t, 160, 260) * (1 - span(t, 460, 560));

/** 單位之下：一整片從表面往上收窄到副手的光柱（55%）。 */
export function absorbUnder(ctx: Ctx, t: number, g: Sk2AbsorbGeom): void {
  const a = columnAlpha(t);
  if (a <= 0) return;
  const w0 = 21, w1 = 4, b = g.base, h = g.hand;
  ctx.save();
  ctx.globalAlpha *= 0.55 * a;
  const gr = ctx.createLinearGradient(0, b.y, 0, h.y);
  gr.addColorStop(0, g.tint[0]);
  gr.addColorStop(1, g.tint[1]);
  ctx.fillStyle = gr;
  ctx.beginPath();
  ctx.moveTo(b.x - w0, b.y + 4);
  ctx.quadraticCurveTo(b.x - w0 * 0.3, b.y - 6, h.x - w1, h.y);
  ctx.lineTo(h.x + w1, h.y);
  ctx.quadraticCurveTo(b.x + w0 * 0.3, b.y - 6, b.x + w0, b.y + 4);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

/** 單位之上：光柱的亮邊與往上跑的亮條、冰晶、光球、收益圖樣、法杖頭染色。 */
export function absorbTop(ctx: Ctx, t: number, g: Sk2AbsorbGeom): void {
  const colA = columnAlpha(t), base = g.base, hand = g.hand, tint = g.tint;
  if (colA > 0) {
    ctx.save();
    ctx.globalAlpha *= 0.85 * colA;
    ctx.strokeStyle = tint[1];
    ctx.lineWidth = 1.4;
    ctx.lineCap = "round";
    for (const side of [-1, 1]) {
      ctx.beginPath();
      for (let i = 0; i <= 10; i++) {
        const p = columnAt(g, i / 10, side);
        if (i) ctx.lineTo(p.x, p.y);
        else ctx.moveTo(p.x, p.y);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "lighter";
    ctx.globalAlpha = 0.4 * colA;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    for (let i = 0; i < 4; i++) {
      const q = (Math.max(0, t - 160) / 260 + i * 0.25) % 1, f = [0.3, 0.62, 0.45, 0.75][i] as number, a = columnAt(g, q, -1), b = columnAt(g, q, 1), x = lerp(a.x, b.x, f), y = lerp(a.y, b.y, f);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + (hand.x - base.x) * 0.06, y - 7);
      ctx.stroke();
    }
    ctx.restore();
  }
  // 冰晶：10 顆，從表面四周沿螺旋往上收進手
  for (let i = 0; i < 10; i++) {
    const t0 = 150 + i * 24, p = span(t, t0, t0 + 300);
    if (p <= 0 || p >= 1) continue;
    const a0 = (i / 10) * TAU + 0.4, r0 = 23, sx = base.x + Math.cos(a0) * r0, sy = base.y + Math.sin(a0) * r0 * 0.55;
    const e = ease(p), sw = (1 - e) * 10, ang = a0 + e * 2.2;
    const x = lerp(sx, hand.x, e) + Math.cos(ang) * sw, y = lerp(sy, hand.y, e) + Math.sin(ang) * sw * 0.6 - Math.sin(e * PI) * 12;
    for (let k = 1; k <= 3; k++) {
      const q = Math.max(0, e - k * 0.06), xx = lerp(sx, hand.x, q) + Math.cos(a0 + q * 2.2) * (1 - q) * 10, yy = lerp(sy, hand.y, q) + Math.sin(a0 + q * 2.2) * (1 - q) * 6 - Math.sin(q * PI) * 6;
      ctx.save();
      ctx.globalAlpha *= 0.5 - k * 0.12;
      ctx.beginPath();
      ctx.arc(xx, yy, 2.2 - k * 0.45, 0, TAU);
      ctx.fillStyle = tint[1];
      ctx.fill();
      ctx.restore();
    }
    const s = 5 * (1 - 0.35 * e);
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(ang);
    const diamond = (r: number, pad: number, col: string): void => {
      ctx.beginPath();
      ctx.moveTo(0, -r - pad);
      ctx.lineTo(r * 0.7 + pad, 0);
      ctx.lineTo(0, r + pad);
      ctx.lineTo(-r * 0.7 - pad, 0);
      ctx.closePath();
      ctx.fillStyle = col;
      ctx.fill();
    };
    diamond(s, 1.2, OUT);
    diamond(s, 0, tint[0]);
    ctx.beginPath();
    ctx.moveTo(0, -s);
    ctx.lineTo(-s * 0.7, 0);
    ctx.lineTo(0, 0);
    ctx.closePath();
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.restore();
  }
  // 光球
  const orb = t < 380 ? 0 : t < 620 ? ease(span(t, 380, 560)) : 1 - span(t, 620, 700);
  if (orb > 0) {
    const R = 6.5 * orb, pulse = t > 560 && t < 640 ? 1 + 0.5 * Math.sin(span(t, 560, 640) * PI) : 1, ox = hand.x + 4, oy = hand.y - 2;
    glow(ctx, ox, oy, R * 2.6 * pulse, tint[1], 0.7);
    ci(ctx, OUT, ox, oy, R + 1.3);
    ci(ctx, tint[0], ox, oy, R);
    ci(ctx, tint[1], hand.x + 4.4, hand.y - 1.6, R * 0.6);
    ci(ctx, "#ffffff", hand.x + 4.8, hand.y - 1.4, R * 0.28);
    if (t > 560) {
      const p = span(t, 560, 700);
      ctx.save();
      ctx.globalAlpha *= 1 - p;
      ctx.beginPath();
      ctx.arc(ox, oy, 6 + p * 14, 0, TAU);
      ctx.strokeStyle = tint[1];
      ctx.lineWidth = 2.2 * (1 - p) + 0.6;
      ctx.stroke();
      ctx.restore();
    }
  }
  // 收益的圖樣：從頭頂浮起、淡出
  if (t > 600 && g.glyph !== null) {
    const p = span(t, 600, 1000), k = p < 0.2 ? ease(p / 0.2) : 1, a = p < 0.7 ? 1 : 1 - (p - 0.7) / 0.3, sz = g.glyphPx * k;
    if (sz > 1) {
      ctx.save();
      ctx.globalAlpha *= a;
      ctx.drawImage(g.glyph, g.head.x - sz / 2, g.head.y - 10 * ease(p) - sz / 2, sz, sz);
      ctx.restore();
    }
  }
  // 法杖頭染成那個元素的亮色外光（這一招的元素換掉了）
  if (t > 640 && g.element && g.staff !== null) {
    const p = span(t, 640, 760), a = p * (1 - 0.4 * span(t, 900, 1000));
    ctx.save();
    ctx.globalAlpha *= a;
    glow(ctx, g.staff.x, g.staff.y, 9, tint[1], 0.9);
    ctx.restore();
  }
}

// =====================================================================
// 疾病擴散（美術 2.2、第 2 版可修 7）：樣張的 220 ms（倒下）＝這裡的 0；到樣張 1150 ms 為止
// =====================================================================
/** 樣張時間軸上倒下的那一刻（這裡的 0）。 */
const SPREAD_T0 = 220;
export const SPREAD_MS = 1150 - SPREAD_T0;

export interface Sk2SpreadGeom {
  /** 倒下的人（那一團從這裡跳起）。 */
  from: Pt;
  /** 被傳染的人的胸口。 */
  dst: Pt;
  /** 地上的 V 從哪格指到哪格（兩格的中心往下 15）。 */
  floorFrom: Pt;
  floorTo: Pt;
  /** 候選範圍格（左上角）與被選中那格（左上角）。 */
  range: readonly Pt[];
  chosen: Pt;
  kind: string;
  K: number;
}

const spreadRangeAlpha = (t: number): number => span(t, 300, 360) * (1 - span(t, 860, 1000));

/** 地上（單位之下）：範圍格一層黃綠（被選中 38%＋框）、一列三個 V。`t0` 是倒下那一刻起算的毫秒。 */
export function spreadUnder(ctx: Ctx, t0: number, g: Sk2SpreadGeom, T: number): void {
  const t = t0 + SPREAD_T0, rng = spreadRangeAlpha(t), leap = span(t, 460, 860);
  if (rng > 0)
    for (const c of g.range) {
      const pick = Math.abs(c.x - g.chosen.x) < 0.5 && Math.abs(c.y - g.chosen.y) < 0.5;
      ctx.save();
      ctx.globalAlpha *= rng * (pick ? 0.38 : 0.18);
      ctx.fillStyle = GERM_COLORS.body;
      ctx.beginPath();
      ctx.roundRect(c.x + 3, c.y + 3, T - 6, T - 6, 8);
      ctx.fill();
      if (pick) {
        ctx.globalAlpha = rng;
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = GERM_COLORS.knob;
        ctx.stroke();
      }
      ctx.restore();
    }
  if (leap > 0) chevrons(ctx, g.floorFrom, g.floorTo, Math.min(1, leap * 1.2) * (1 - span(t, 1000, 1150)), g.K);
}

function trail(ctx: Ctx, pt: (q: number) => Pt, upTo: number, K: number): void {
  ctx.save();
  ctx.setLineDash([4 * K, 3 * K]);
  ctx.lineCap = "round";
  for (const [w, c] of [[4.2 * K, OUT], [2.2 * K, GERM_COLORS.knob]] as const) {
    ctx.beginPath();
    for (let q = 0; q <= upTo + 1e-9; q += 0.02) {
      const p = pt(q);
      if (q) ctx.lineTo(p.x, p.y);
      else ctx.moveTo(p.x, p.y);
    }
    ctx.strokeStyle = c;
    ctx.lineWidth = w;
    ctx.stroke();
  }
  ctx.restore();
}

/** 單位之上：那一團沿弧線跳過去（拖尾巴、黃綠虛線軌跡、末端箭頭）、落地爆開。 */
export function spreadTop(ctx: Ctx, t0: number, g: Sk2SpreadGeom): void {
  const t = t0 + SPREAD_T0, leap = span(t, 460, 860), land = span(t, 860, 1150), K = g.K, from = g.from, dst = g.dst;
  const pt = (q: number): Pt => {
    const e = ease(q);
    return { x: lerp(from.x, dst.x - 4, e), y: lerp(from.y, dst.y, e) - Math.sin(e * PI) * 30 };
  };
  if (leap > 0 && leap < 1) {
    trail(ctx, pt, leap, K);
    for (let k = 3; k >= 1; k--) {
      const p = pt(Math.max(0, leap - k * 0.07));
      mote(ctx, g.kind, p.x, p.y, 7 - k * 1.4, 0.75 - k * 0.15, 0);
    }
    const p = pt(leap), p2 = pt(Math.min(1, leap + 0.02));
    mote(ctx, g.kind, p.x, p.y, 11, 1, Math.atan2(p2.y - p.y, p2.x - p.x));
  }
  if (leap >= 1 && t < 1000) {
    ctx.save();
    ctx.globalAlpha *= 1 - span(t, 900, 1000);
    trail(ctx, pt, 0.86, K);
    const a = pt(0.86), b = pt(0.97), ang = Math.atan2(b.y - a.y, b.x - a.x);
    ctx.translate(b.x, b.y);
    ctx.rotate(ang);
    ctx.scale(K, K);
    ctx.beginPath();
    ctx.moveTo(3, 0);
    ctx.lineTo(-4, -4.4);
    ctx.lineTo(-4, 4.4);
    ctx.closePath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    ctx.fillStyle = GERM_COLORS.knob;
    ctx.fill();
    ctx.restore();
  }
  if (land > 0 && land < 0.6) {
    const p = land / 0.6, c = { x: dst.x - 4, y: dst.y };
    for (let i = 0; i < 5; i++) {
      const a = -PI / 2 + (i - 2) * 0.6, d = 4 + p * 12;
      mote(ctx, g.kind, c.x + Math.cos(a) * d, c.y + Math.sin(a) * d, 5.5 * (1 - p * 0.5), 1 - p, a);
    }
  }
}

// =====================================================================
// 鉤（美術 2.3、第 2 版可修 4、5）
// =====================================================================
/** 鉤的時間點（樣張；正常速度）：射出 100–330（這裡從 0 起算＝出手那一刻）、鉤住 330 起。 */
export const HOOK_FLY_MS = 230;
export const HOOK_HEAD_K = 0.78;

export interface Sk2HookGeom {
  hand: Pt;
  /** 受鉤點（目標胸口；跟著被拉的人走）。 */
  target: () => Pt;
  mode: "pull" | "brake" | "immovable";
  /** 熔岩（致命地形）那一格的中心；煞住時用。 */
  hazard: Pt | null;
  /** 被拉的人腳底（煞住的塵土與拖痕）。 */
  feet: () => Pt;
  K: number;
}

/** 鉤的鎖鏈與鉤頭在 t（毫秒，出手那一刻＝0）時的樣子。`hitMs`＝鉤住的那一刻、`pullFrom`／`pullTo`＝被拉的那一段、`endMs`＝整段結束。 */
export interface HookTimes {
  hitMs: number;
  pullFrom: number;
  pullTo: number;
}

/** 鉤住前：鏈子從手飛向目標（中段往上拱 5），鉤頭在前。 */
function hookFly(ctx: Ctx, h: Pt, tg: Pt, p: number, K: number): void {
  const x = lerp(h.x, tg.x, p), y = lerp(h.y, tg.y, p) - Math.sin(p * PI) * 5;
  chain(ctx, [[h.x, h.y], [x, y]], K, { phase: 0 });
  hookHead(ctx, x, y, Math.atan2(tg.y - h.y, tg.x - h.x), HOOK_HEAD_K, K);
}

/** 單位之上的鎖鏈、鉤頭、撞擊、塵土、熔岩火舌。 */
export function hookOver(ctx: Ctx, t: number, g: Sk2HookGeom, tm: HookTimes): void {
  const h = { x: g.hand.x + 2, y: g.hand.y }, tg = g.target(), K = g.K;
  if (t < tm.hitMs) {
    hookFly(ctx, h, tg, ease(t / Math.max(1, tm.hitMs)), K);
    return;
  }
  // 鉤住的一下：小星
  const bite = t - tm.hitMs;
  if (g.mode === "immovable") {
    hookGiant(ctx, bite, h, tg, K);
    return;
  }
  if (bite < 120) impactStar(ctx, tg.x + 2, tg.y, bite / 120, 6);
  if (t < tm.pullTo) {
    const p = span(t, tm.pullFrom, tm.pullTo);
    chain(ctx, [[h.x, h.y], [tg.x, tg.y]], K, { phase: -p * 60 });
    hookHead(ctx, tg.x, tg.y, Math.atan2(tg.y - h.y, tg.x - h.x), HOOK_HEAD_K, K);
  } else {
    const lava = g.mode === "brake", p = ease(span(t, tm.pullTo, tm.pullTo + (lava ? 240 : 160)));
    if (p < 1) {
      const ex = lerp(tg.x, h.x, p), ey = lerp(tg.y, h.y, p), sag = lava ? 10 * Math.sin(Math.min(1, p * 2) * PI) : 0, mx = (h.x + ex) / 2, my = (h.y + ey) / 2 + sag;
      chain(ctx, [[h.x, h.y], [mx, my], [ex, ey]], K);
      hookHead(ctx, ex, ey, Math.atan2(ey - h.y, ex - h.x) + (lava ? 0.6 * Math.sin(p * PI) : 0), HOOK_HEAD_K, K);
    }
  }
  if (g.mode === "brake") brakeFx(ctx, t - tm.pullTo, g);
}

/** 巨型頭目拉不動：繃緊（0–190：直、微抖、白光、亮邊、受鉤點往外放射的緊繃線）→ 鉤脫開彈回（190–450 波浪縮回）＋撞擊星（190–530）。 */
function hookGiant(ctx: Ctx, bite: number, h: Pt, tg: Pt, K: number): void {
  const t = bite + 330;
  if (t < 450) impactStar(ctx, tg.x + 2, tg.y, span(t, 330, 450), 7);
  const away = Math.atan2(tg.y - h.y, tg.x - h.x) + PI; // 往施放者那一側放射（樣張是往西）
  if (t < 520) {
    const p = span(t, 330, 520), j = Math.sin(t / 9) * 1.2 * p;
    chain(ctx, [[h.x, h.y], [(h.x + tg.x) / 2, (h.y + tg.y) / 2 + j], [tg.x, tg.y]], K, { glow: 0.25 + 0.45 * p, rim: Math.min(1, p * 2) });
    hookHead(ctx, tg.x, tg.y, away + PI, HOOK_HEAD_K, K);
    if (p > 0.25) {
      const q = (p - 0.25) / 0.75;
      ctx.save();
      ctx.lineCap = "round";
      for (const d of [-0.79, -0.39, 0.39, 0.79]) {
        const a = away + d, r0 = 7, r1 = 7 + 6 + 6 * q;
        for (const [w, c] of [[4.4, OUT], [2.4, "#fff6d0"]] as const) {
          ctx.globalAlpha = Math.min(1, q * 1.6);
          ctx.strokeStyle = c;
          ctx.lineWidth = w;
          ctx.beginPath();
          ctx.moveTo(tg.x + Math.cos(a) * r0, tg.y + Math.sin(a) * r0);
          ctx.lineTo(tg.x + Math.cos(a) * r1, tg.y + Math.sin(a) * r1);
          ctx.stroke();
        }
      }
      ctx.restore();
    }
  } else {
    const p = ease(span(t, 520, 780));
    if (p < 1) {
      const L = 1 - p, ex = lerp(h.x, tg.x + Math.cos(away) * 4, L), ey = lerp(h.y, tg.y, L), n = 10, pts: [number, number][] = [];
      for (let i = 0; i <= n; i++) {
        const q = i / n, w = Math.sin(q * PI * 3 + p * 12) * 7 * (1 - p) * Math.sin(q * PI);
        pts.push([lerp(h.x, ex, q), lerp(h.y, ey, q) + w]);
      }
      chain(ctx, pts, K);
      hookHead(ctx, ex, ey, away + 0.5 * (1 - p), HOOK_HEAD_K, K);
    }
  }
  if (t > 520 && t < 860) impactStar(ctx, tg.x + Math.cos(away) * 2, tg.y, span(t, 520, 860), 15);
}

/** 熔岩前煞住（可修 4）：腳前塵土 ×1.5、往熔岩方向的兩道短拖痕、熔岩冒一次亮橘火舌、三顆火星。`s`＝停下那一刻起算的毫秒。 */
function brakeFx(ctx: Ctx, s: number, g: Sk2HookGeom): void {
  if (g.hazard === null) return;
  const f = g.feet(), hz = g.hazard, dir = Math.atan2(hz.y - f.y, hz.x - f.x);
  if (s > -60 && s < 260) {
    const p = span(s, -60, 260), fx = f.x + Math.cos(dir) * 8, fy = f.y + 2;
    for (let i = 0; i < 4; i++) {
      const a = dir + PI * 0.15 + (i - 1.5) * 0.4, d = (3 + p * 9) * 1.5;
      ctx.save();
      ctx.globalAlpha *= 0.85 * (1 - p);
      ctx.beginPath();
      ctx.arc(fx + Math.cos(a) * d, fy + Math.sin(a) * d * 0.5, (3.6 - i * 0.4 + p * 2) * 1.5, 0, TAU);
      ctx.fillStyle = "#d8c8a8";
      ctx.fill();
      ctx.restore();
    }
    for (let i = 0; i < 3; i++) {
      const q = span(s, i * 40, i * 40 + 200);
      if (q <= 0 || q >= 1) continue;
      ctx.save();
      ctx.globalAlpha *= 1 - q;
      ci(ctx, "#ffd23f", hz.x + (i - 1) * 9, hz.y + 6 - q * 16, 1.6);
      ctx.restore();
    }
  }
  if (s > -40 && s < 300) {
    const a = clamp((s + 40) / 60) * (1 - span(s, 160, 300)), fx = f.x + Math.cos(dir) * 3, fy = f.y + 4;
    ctx.save();
    ctx.globalAlpha *= 0.85 * a;
    ctx.lineCap = "round";
    ctx.translate(fx, fy);
    ctx.rotate(dir);
    for (const dy of [-2.6, 2.6]) {
      ctx.strokeStyle = "#3a3026";
      ctx.lineWidth = 2.8;
      ctx.beginPath();
      ctx.moveTo(0, dy * 0.7);
      ctx.lineTo(13, dy);
      ctx.stroke();
      ctx.strokeStyle = "#cbb894";
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      ctx.moveTo(1, dy * 0.7 - 0.8);
      ctx.lineTo(12, dy - 0.8);
      ctx.stroke();
    }
    ctx.restore();
  }
  if (s > -40 && s < 140) {
    const q = span(s, -40, 140), k = Math.sin(q * PI), x = hz.x + 6, y = hz.y + 8 - 10 * k;
    ctx.save();
    ctx.globalAlpha *= Math.min(1, k * 1.6);
    glow(ctx, x, y, 16 * k + 2, "#ffb03a", 0.6);
    ctx.translate(x, y);
    ctx.scale(0.4 + 0.75 * k, 0.4 + 0.95 * k);
    flame(ctx, OUT, 0, 0, 1.18);
    flame(ctx, "#ff8a1a", 0, 0, 1);
    flame(ctx, "#ffe066", 0.4, 2.6, 0.58);
    ctx.restore();
  }
}
