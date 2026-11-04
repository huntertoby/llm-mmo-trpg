// 等待動畫的畫法（RT-3；docs/art/等待動畫.md 第 1、4、5 節，區域主題移植需求.md 第 3 節）：C 羽毛筆與羊皮紙。
// 四個場合各一種畫法，同一套道具（羊皮紙、羽毛筆、墨、封蠟、金邊），節奏與構圖各不相同：
// - skill（技能生成，120px）：羊皮紙展開 → 羽毛筆描卡框 → 畫中間的圖樣（淡淡上色）→ 蓋區域色封蠟 → 鑲金邊；一輪 3.2 秒，
//   還沒好就換一張紙重畫（換一個圖樣）。完成：卡面淡入 0.3 秒。
// - judge（事件判定，80px）：沙漏翻轉、區域色的沙流下；一輪 1.4 秒。完成：沙漏停住（接擲骰結果）。
// - npc（NPC 聊天，小泡泡）：羊皮紙泡泡裡，羽毛筆依序點出三個墨點；一輪 0.9 秒。
// - retell（多講一點）：皮面書翻開，羽毛筆沿右頁一行行寫，寫滿翻頁；一輪 2.6 秒。完成：闔書。
// 墨色、封蠟、點綴（荒原的火星、主城的紫晶光）讀 RT-1 的 `region_themes`（呼叫端傳 `WaitPalette`），不寫死在畫法裡。
// 確定性：畫面只由「時間 t、種子 seed、狀態」決定，不用 Math.random、不讀時鐘（時鐘在 `ui/WaitScene.tsx`）。
// 減少動態：每個場合有自己的靜態版（`STATIC_T` 那一刻，不畫流動的沙、點綴不動）。
import { TAU, type Ctx } from "./artDraw";
import { fmix32 } from "./attackVariants";
import { lcg } from "./inkStyle";
import type { WaitSceneId } from "../ui/waitNarration";

/** 一輪的長度（毫秒）。 */
export const WAIT_CYCLE_MS: Readonly<Record<WaitSceneId, number>> = { skill: 3200, judge: 1400, npc: 900, retell: 2600 };
/** 完成時的收尾長度（毫秒）：卡面淡入、闔書。 */
export const WAIT_DONE_MS = 300;
/** 畫布的邏輯大小（CSS 像素）。 */
export const WAIT_SIZE: Readonly<Record<WaitSceneId, { w: number; h: number }>> = {
  skill: { w: 120, h: 120 },
  judge: { w: 80, h: 80 },
  npc: { w: 64, h: 30 },
  retell: { w: 104, h: 64 },
};
/** 減少動態時固定畫的那一刻（一輪裡的毫秒）：技能＝畫好的圖樣、判定＝停住的沙漏、聊天＝三個墨點、回顧＝寫了一半的頁。 */
export const STATIC_T: Readonly<Record<WaitSceneId, number>> = { skill: 3000, judge: 770, npc: 720, retell: 1050 };
/** 技能生成的圖樣種類數。 */
export const SKILL_GLYPHS = 5;

export type WaitStatus = "wait" | "done" | "fail";
export type WaitFxKind = "none" | "ember" | "crystal";

export interface WaitPalette {
  /** 墨色（區域 `ink`）。 */
  ink: string;
  /** 封蠟、沙子、書籤（區域 `seal`）。 */
  seal: string;
  fx: WaitFxKind;
  gold: string;
  parch: string;
  parchEdge: string;
  leather: string;
  /** 技能圖樣的淡色（技能的元素色；沒有＝用墨色）。 */
  tint: string;
}

const GOLD = "#e8bb48";
const PARCH = "#e9d6a8";
const PARCH_EDGE = "#8a6a40";
const LEATHER = "#6a3a20";
const FEATHER = "#f2f0e8";

/** 區域主題（RT-1 的 `ink`、`seal`、`wait_fx`）→ 調色盤；`grey`＝失敗時變灰。 */
export function waitPalette(theme: { ink: string; seal: string; wait_fx?: WaitFxKind }, opts: { grey?: boolean; tint?: string | null } = {}): WaitPalette {
  if (opts.grey === true) return { ink: "#4a4a4a", seal: "#8a8a8a", fx: "none", gold: "#9a9a9a", parch: "#d4d0c8", parchEdge: "#8a8680", leather: "#5a5a5a", tint: "#7a7a7a" };
  return { ink: theme.ink, seal: theme.seal, fx: theme.wait_fx ?? "none", gold: GOLD, parch: PARCH, parchEdge: PARCH_EDGE, leather: LEATHER, tint: opts.tint ?? theme.ink };
}

export interface WaitFrame {
  scene: WaitSceneId;
  /** 動畫時間（毫秒，已乘上開發用的 `?anim=` 倍率；失敗、完成時是停住那一刻）。 */
  t: number;
  /** 請求編號的種子（`waitSeed`）：技能生成的圖樣、點綴的位置。 */
  seed: number;
  palette: WaitPalette;
  reduced: boolean;
  status: WaitStatus;
  /** 完成後過了多久（毫秒）；減少動態時直接當作收尾結束。 */
  doneT?: number;
}

const clamp01 = (v: number): number => (v < 0 ? 0 : v > 1 ? 1 : v);
const ease = (v: number): number => {
  const x = clamp01(v);
  return x * x * (3 - 2 * x);
};
/** `p` 在 [a, b) 裡的進度（0～1）。 */
const span = (p: number, a: number, b: number): number => clamp01((p - a) / (b - a));

/** 一輪裡的進度：第幾輪、0～1。 */
export function waitPhase(scene: WaitSceneId, t: number): { cycle: number; p: number } {
  const len = WAIT_CYCLE_MS[scene];
  const tt = Math.max(0, t);
  return { cycle: Math.floor(tt / len), p: (tt % len) / len };
}

/** 這一輪的技能圖樣（照種子挑，下一輪一定換一個）。 */
export function skillGlyphIndex(seed: number, cycle: number): number {
  return ((fmix32(seed) % SKILL_GLYPHS) + cycle * 2) % SKILL_GLYPHS;
}

type P = readonly [number, number];

/** 折線取前 `k`（0～1，照長度）的部分；回傳畫到的點與筆尖位置。 */
export function partialPolyline(pts: readonly P[], k: number): { pts: P[]; tip: P } {
  const first = pts[0] ?? ([0, 0] as P);
  if (pts.length < 2) return { pts: [first], tip: first };
  const seg: number[] = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1]!;
    const b = pts[i]!;
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
    seg.push(d);
    total += d;
  }
  let left = clamp01(k) * total;
  const out: P[] = [first];
  for (let i = 1; i < pts.length; i++) {
    const d = seg[i - 1]!;
    const a = pts[i - 1]!;
    const b = pts[i]!;
    if (left >= d) {
      out.push(b);
      left -= d;
      continue;
    }
    const f = d === 0 ? 0 : left / d;
    const tip: P = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
    out.push(tip);
    return { pts: out, tip };
  }
  return { pts: out, tip: out[out.length - 1]! };
}

function polyline(ctx: Ctx, pts: readonly P[], closed = false): void {
  ctx.beginPath();
  pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p[0], p[1]) : ctx.lineTo(p[0], p[1])));
  if (closed) ctx.closePath();
}

/** 羊皮紙（鋸齒的上下緣）；`open`＝展開的比例（由上往下）。 */
function parchment(ctx: Ctx, x: number, y: number, w: number, h: number, pal: WaitPalette, open = 1): void {
  const hh = h * clamp01(open);
  if (hh <= 0.5) return;
  const n = 8;
  const pts: P[] = [];
  for (let i = 0; i <= n; i++) pts.push([x + (i * w) / n, y + (i % 2 === 0 ? 2.5 : 0)]);
  for (let i = n; i >= 0; i--) pts.push([x + (i * w) / n, y + hh - (i % 2 === 0 ? 2.5 : 0)]);
  ctx.fillStyle = pal.parch;
  polyline(ctx, pts, true);
  ctx.fill();
  ctx.strokeStyle = pal.parchEdge;
  ctx.globalAlpha = 0.55;
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.globalAlpha = 1;
}

/** 羽毛筆：筆尖在 (x, y)，往右上斜（angle＞0＝順時針）；`s` 縮放。 */
export function quill(ctx: Ctx, x: number, y: number, pal: WaitPalette, s = 1, angle = 0.6): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  ctx.scale(s, s);
  ctx.fillStyle = FEATHER;
  ctx.strokeStyle = pal.ink;
  ctx.lineWidth = 0.9;
  ctx.beginPath();
  ctx.moveTo(0, -3);
  ctx.quadraticCurveTo(-7, -18, -2, -36);
  ctx.quadraticCurveTo(7, -20, 0, -3);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, -1);
  ctx.lineTo(-1.6, -32);
  ctx.stroke();
  // 筆尖（墨色）
  ctx.fillStyle = pal.ink;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(-1.4, -4);
  ctx.lineTo(1.4, -4);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

/** 點綴：荒原的火星（往上飄）、主城的紫晶光（閃）。`still`＝減少動態（停在固定一刻）。 */
function waitFx(ctx: Ctx, w: number, h: number, pal: WaitPalette, seed: number, t: number, still: boolean): void {
  if (pal.fx === "none") return;
  const r = lcg(fmix32(seed ^ 0x5bd1e995));
  const tt = still ? 600 : t;
  if (pal.fx === "ember") {
    for (let i = 0; i < 5; i++) {
      const x0 = w * (0.15 + 0.7 * r());
      const off = r();
      const ph = (tt / 1700 + off) % 1;
      const x = x0 + Math.sin((ph + off) * TAU) * 3;
      const y = h * (0.95 - ph * 0.85);
      ctx.globalAlpha = 0.85 * (1 - ph);
      ctx.fillStyle = i % 2 === 0 ? "#ff8a2a" : "#ffc46a";
      ctx.beginPath();
      ctx.arc(x, y, 1.1 + (1 - ph) * 0.8, 0, TAU);
      ctx.fill();
    }
  } else {
    for (let i = 0; i < 4; i++) {
      const x = w * (0.1 + 0.8 * r());
      const y = h * (0.1 + 0.8 * r());
      const a = 0.35 + 0.45 * (0.5 + 0.5 * Math.sin(tt / 420 + i * 1.7));
      const s = 2.2 + r() * 1.2;
      ctx.globalAlpha = a;
      ctx.fillStyle = "#c8b4ff";
      polyline(ctx, [[x, y - s], [x + s * 0.4, y], [x, y + s], [x - s * 0.4, y]], true);
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
}

// ---------------------------------------------------------------- 技能生成

const CARD = { x: 18, y: 12, w: 84, h: 96, r: 6 } as const;

function cardOutline(): P[] {
  const { x, y, w, h } = CARD;
  // 由左上順時針繞一圈（羽毛筆描的順序）
  return [
    [x + 4, y],
    [x + w - 4, y],
    [x + w, y + 4],
    [x + w, y + h - 4],
    [x + w - 4, y + h],
    [x + 4, y + h],
    [x, y + h - 4],
    [x, y + 4],
    [x + 4, y],
  ];
}

/** 技能圖樣（中心 60,54，半徑約 22）：螺旋、五芒星、符文三角、火焰波、新月。 */
export function skillGlyph(index: number): P[] {
  const cx = 60;
  const cy = 54;
  const R = 22;
  const pts: P[] = [];
  switch (index % SKILL_GLYPHS) {
    case 0:
      for (let i = 0; i <= 40; i++) {
        const s = i / 40;
        const a = -Math.PI / 2 + s * Math.PI * 3.2;
        const rr = R * (0.15 + 0.85 * s);
        pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
      }
      return pts;
    case 1:
      for (let i = 0; i <= 5; i++) {
        const a = -Math.PI / 2 + ((i * 2) % 5) * (TAU / 5);
        pts.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R]);
      }
      return pts;
    case 2:
      return [
        [cx, cy - R],
        [cx + R * 0.9, cy + R * 0.7],
        [cx - R * 0.9, cy + R * 0.7],
        [cx, cy - R],
        [cx, cy + R * 0.7],
        [cx - R * 0.45, cy - R * 0.05],
        [cx + R * 0.45, cy - R * 0.05],
      ];
    case 3:
      for (let i = 0; i <= 30; i++) {
        const s = i / 30;
        pts.push([cx + Math.sin(s * Math.PI * 3) * R * 0.45 * (1 - s * 0.5), cy + R - s * R * 2]);
      }
      return pts;
    default:
      for (let i = 0; i <= 24; i++) {
        const a = Math.PI * 0.25 + (i / 24) * Math.PI * 1.5;
        pts.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R]);
      }
      for (let i = 24; i >= 0; i--) {
        const a = Math.PI * 0.35 + (i / 24) * Math.PI * 1.3;
        pts.push([cx + R * 0.35 + Math.cos(a) * R * 0.8, cy + Math.sin(a) * R * 0.8]);
      }
      return pts;
  }
}

// ---------------------------------------------------------------- 封蠟（RT-3b 小修：不規則的蠟緣＋壓印紋）

/** 蠟緣的點數。 */
export const SEAL_EDGE_POINTS = 18;

/**
 * 蠟緣每一點的半徑倍率（0.8～1.08）：固定的雜湊（`fmix32(點的序號＋常數)`），每次都一樣，不用 Math.random。
 * 有兩處比較大的鼓起（蠟溢出去的地方），其餘小小起伏。
 */
export const SEAL_EDGE: readonly number[] = Array.from({ length: SEAL_EDGE_POINTS }, (_, i) => {
  const h = fmix32(0x5ea1 + i * 0x9e37) / 0xffffffff;
  const bulge = i === 4 || i === 11 ? 0.1 : 0;
  return 0.84 + h * 0.14 + bulge - (i % 3 === 0 ? 0.04 : 0);
});

/** 蠟緣的點（以 (x, y) 為中心、半徑 r；確定性）。 */
export function sealOutline(x: number, y: number, r: number): P[] {
  return SEAL_EDGE.map((m, i) => {
    const a = (i / SEAL_EDGE_POINTS) * TAU + 0.2;
    return [x + Math.cos(a) * r * m, y + Math.sin(a) * r * m] as P;
  });
}

/** 平滑的封閉曲線（相鄰兩點的中點用二次曲線接起來，蠟緣才會圓潤不尖）。 */
function smoothClosed(ctx: Ctx, pts: readonly P[]): void {
  const n = pts.length;
  const mid = (a: P, b: P): P => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  ctx.beginPath();
  const m0 = mid(pts[n - 1]!, pts[0]!);
  ctx.moveTo(m0[0], m0[1]);
  for (let i = 0; i < n; i++) {
    const p = pts[i]!;
    const m = mid(p, pts[(i + 1) % n]!);
    ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
  }
  ctx.closePath();
}

function seal(ctx: Ctx, x: number, y: number, r: number, pal: WaitPalette, alpha: number): void {
  if (alpha <= 0) return;
  ctx.globalAlpha = alpha;
  // 蠟緣：不規則的一攤蠟（往右下偏一點的陰影，讓它像凸起的）
  const edge = sealOutline(x, y, r * 1.08);
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  smoothClosed(
    ctx,
    edge.map((p) => [p[0] + 0.6, p[1] + 0.8] as P),
  );
  ctx.fill();
  ctx.fillStyle = pal.seal;
  smoothClosed(ctx, edge);
  ctx.fill();
  ctx.strokeStyle = "rgba(0,0,0,0.3)";
  ctx.lineWidth = 0.6;
  ctx.stroke();
  // 壓下去的圓餅：內圈比外緣暗一點，左上一道亮邊（壓印的斜面）
  const inner = r * 0.62;
  ctx.fillStyle = "rgba(0,0,0,0.18)";
  ctx.beginPath();
  ctx.arc(x, y, inner, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  ctx.arc(x, y, inner, Math.PI * 0.95, Math.PI * 1.65);
  ctx.stroke();
  ctx.strokeStyle = "rgba(0,0,0,0.4)";
  ctx.beginPath();
  ctx.arc(x, y, inner, Math.PI * 1.95, Math.PI * 2.65);
  ctx.stroke();
  // 壓印紋：中間一顆星芒（四道長、四道短）加一圈小點
  ctx.strokeStyle = "rgba(0,0,0,0.42)";
  ctx.lineWidth = 0.6;
  ctx.beginPath();
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU;
    const len = inner * (i % 2 === 0 ? 0.62 : 0.34);
    ctx.moveTo(x, y);
    ctx.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len);
  }
  ctx.stroke();
  ctx.fillStyle = "rgba(0,0,0,0.38)";
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU + TAU / 16;
    ctx.beginPath();
    ctx.arc(x + Math.cos(a) * inner * 0.8, y + Math.sin(a) * inner * 0.8, Math.max(0.35, r * 0.05), 0, TAU);
    ctx.fill();
  }
  // 蠟面的高光（左上一小塊）
  ctx.fillStyle = "rgba(255,255,255,0.28)";
  ctx.beginPath();
  ctx.ellipse(x - r * 0.45, y - r * 0.5, r * 0.22, r * 0.12, -0.6, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
}

function drawSkill(ctx: Ctx, f: WaitFrame): void {
  const pal = f.palette;
  const { cycle, p } = waitPhase("skill", f.t);
  const glyph = skillGlyph(skillGlyphIndex(f.seed, cycle));
  const done = f.status === "done";
  const q = done ? 1 : p;
  parchment(ctx, 8, 4, 104, 112, pal, ease(span(q, 0, 0.12)));
  // 卡框
  const frameK = span(q, 0.12, 0.42);
  let tip: P | null = null;
  if (frameK > 0) {
    const part = partialPolyline(cardOutline(), frameK);
    ctx.strokeStyle = pal.ink;
    ctx.lineWidth = 1.6;
    ctx.lineJoin = "round";
    polyline(ctx, part.pts);
    ctx.stroke();
    if (frameK < 1) tip = part.tip;
  }
  // 圖樣（淡淡上色＋墨線）
  const glyphK = span(q, 0.42, 0.72);
  if (glyphK > 0) {
    ctx.globalAlpha = 0.22 * glyphK;
    ctx.fillStyle = pal.tint;
    ctx.beginPath();
    ctx.arc(60, 54, 26, 0, TAU);
    ctx.fill();
    ctx.globalAlpha = 1;
    const part = partialPolyline(glyph, glyphK);
    ctx.strokeStyle = pal.ink;
    ctx.lineWidth = 1.5;
    polyline(ctx, part.pts);
    ctx.stroke();
    if (glyphK < 1) tip = part.tip;
    // 兩行小字的線
    ctx.globalAlpha = 0.55 * glyphK;
    ctx.lineWidth = 1;
    for (let l = 0; l < 2; l++) {
      ctx.beginPath();
      ctx.moveTo(30, 88 + l * 7);
      ctx.lineTo(30 + 60 * glyphK - l * 14, 88 + l * 7);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  // 封蠟（由大壓到小）
  const sealK = span(q, 0.72, 0.86);
  if (sealK > 0) {
    const s = 1 + (1 - ease(sealK)) * 0.6;
    seal(ctx, CARD.x + CARD.w - 10, CARD.y + CARD.h - 10, 8 * s, pal, Math.min(1, sealK * 1.6));
  }
  // 金邊
  const goldK = span(q, 0.86, 1);
  if (goldK > 0) {
    ctx.globalAlpha = goldK;
    ctx.strokeStyle = pal.gold;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.roundRect(CARD.x + 3, CARD.y + 3, CARD.w - 6, CARD.h - 6, 4);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  // 完成：卡面淡入（深藍底、金框、圖樣轉金色）
  if (done) {
    const k = f.reduced ? 1 : clamp01((f.doneT ?? 0) / WAIT_DONE_MS);
    ctx.globalAlpha = k;
    ctx.fillStyle = "#1e2236";
    ctx.beginPath();
    ctx.roundRect(CARD.x, CARD.y, CARD.w, CARD.h, CARD.r);
    ctx.fill();
    ctx.strokeStyle = pal.gold;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.strokeStyle = pal.gold;
    ctx.lineWidth = 1.5;
    polyline(ctx, glyph);
    ctx.stroke();
    ctx.globalAlpha = 1;
    seal(ctx, CARD.x + CARD.w - 10, CARD.y + CARD.h - 10, 8, pal, 1);
    return;
  }
  // 羽毛筆：畫框、畫圖樣時在筆尖；其他時候停在右上
  if (tip !== null) quill(ctx, tip[0], tip[1], pal, 0.9);
  else quill(ctx, 104, 30, pal, 0.9, 0.35);
}

// ---------------------------------------------------------------- 事件判定

/** 判定的羊皮紙小卡（畫布座標）；沙漏以 (40, 40) 為中心。 */
export const JUDGE_PARCH = { x: 4, y: 2, w: 72, h: 76 } as const;
/** 沙漏外框（木框）的半寬、半高（未旋轉；木框 ±20、上下 ±34，加 1px 線寬餘裕）。 */
export const HOURGLASS_HALF = { w: 21, h: 35 } as const;
/** 翻轉時沙漏離羊皮紙邊至少留多少（CSS 像素）。 */
const HOURGLASS_INSET = 1;

/** 沙漏轉到 `angle`、縮放 `k` 時，外框的半寬、半高（軸對齊的外接框）。 */
export function hourglassExtent(angle: number, k = 1): { w: number; h: number } {
  const c = Math.abs(Math.cos(angle));
  const s = Math.abs(Math.sin(angle));
  return { w: k * (HOURGLASS_HALF.w * c + HOURGLASS_HALF.h * s), h: k * (HOURGLASS_HALF.w * s + HOURGLASS_HALF.h * c) };
}

/** 翻轉到 `angle` 時要縮多少，外接框才收在羊皮紙裡（直立時是 1）。 */
export function hourglassFlipScale(angle: number): number {
  const e = hourglassExtent(angle);
  const maxW = JUDGE_PARCH.w / 2 - HOURGLASS_INSET;
  const maxH = JUDGE_PARCH.h / 2 - HOURGLASS_INSET;
  return Math.min(1, maxW / e.w, maxH / e.h);
}

/** 沙漏玻璃在高度 y（-30～30，0 是頸部）的半寬。 */
const bulbW = (y: number): number => 2 + 14 * (Math.abs(y) / 30);

function drawJudge(ctx: Ctx, f: WaitFrame): void {
  const pal = f.palette;
  const { p } = waitPhase("judge", f.reduced ? STATIC_T.judge : f.t);
  const flip = span(p, 0, 0.15);
  const flow = span(p, 0.15, 1);
  const moving = !f.reduced && f.status === "wait";
  // 羊皮紙底（墨線在深藍底上看不見；同一張紙，沙漏放在上面）
  ctx.fillStyle = pal.parch;
  ctx.beginPath();
  ctx.roundRect(JUDGE_PARCH.x, JUDGE_PARCH.y, JUDGE_PARCH.w, JUDGE_PARCH.h, 10);
  ctx.fill();
  ctx.strokeStyle = pal.parchEdge;
  ctx.globalAlpha = 0.55;
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.save();
  ctx.translate(40, 40);
  // 翻轉時：上一輪的沙都在下面，整個沙漏轉半圈（轉完＝沙都在上面，和不轉、沙在上面的畫面一樣），之後不再旋轉、沙往下流
  // RT-3b：轉到斜的時候木框對角會超出羊皮紙約 2px，翻轉中跟著角度縮小，整個沙漏收在紙裡（`hourglassFlipScale`）
  const flipping = flip < 1 && !f.reduced;
  if (flipping) {
    const angle = Math.PI * ease(flip);
    ctx.rotate(angle);
    const k = hourglassFlipScale(angle);
    ctx.scale(k, k);
  }
  const top = flipping ? 0 : 1 - flow;
  const bottom = flipping ? 1 : flow;
  // 上下木框
  ctx.fillStyle = pal.ink;
  for (const yy of [-34, 30]) {
    ctx.beginPath();
    ctx.roundRect(-20, yy, 40, 4, 1.5);
    ctx.fill();
  }
  ctx.strokeStyle = pal.gold;
  ctx.globalAlpha = 0.7;
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.moveTo(-18, -33);
  ctx.lineTo(18, -33);
  ctx.moveTo(-18, 33);
  ctx.lineTo(18, 33);
  ctx.stroke();
  ctx.globalAlpha = 1;
  // 柱子
  ctx.strokeStyle = pal.ink;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(-18, -30);
  ctx.lineTo(-18, 30);
  ctx.moveTo(18, -30);
  ctx.lineTo(18, 30);
  ctx.stroke();
  // 沙（區域色）
  ctx.fillStyle = pal.seal;
  if (top > 0.01) {
    // 上半：沙在靠近頸部的那一段（倒置時在 y＜0 這邊）
    const ys = -2 - 26 * top;
    polyline(ctx, [[-bulbW(ys), ys], [bulbW(ys), ys], [1.5, -1], [-1.5, -1]], true);
    ctx.fill();
  }
  if (bottom > 0.01) {
    const ys = 29 - 22 * bottom;
    polyline(ctx, [[-bulbW(29), 29], [bulbW(29), 29], [bulbW(ys + 3), ys + 3], [0, ys], [-bulbW(ys + 3), ys + 3]], true);
    ctx.fill();
  }
  // 沙流（只在流動中畫；停住、減少動態不畫）
  if (moving && flip >= 1 && top > 0.01) {
    const ys = 29 - 22 * bottom;
    ctx.strokeStyle = pal.seal;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, ys);
    ctx.stroke();
    for (let i = 0; i < 4; i++) {
      const g = (f.t / 260 + i / 4) % 1;
      ctx.beginPath();
      ctx.arc(0, g * ys, 0.9, 0, TAU);
      ctx.fill();
    }
  }
  // 玻璃（墨線）
  ctx.strokeStyle = pal.ink;
  ctx.lineWidth = 1.2;
  ctx.fillStyle = "rgba(220,235,255,0.18)";
  polyline(ctx, [[-16, -30], [16, -30], [2, 0], [16, 30], [-16, 30], [-2, 0]], true);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------- NPC 聊天

const DOTS: readonly P[] = [
  [20, 15],
  [32, 15],
  [44, 15],
];

function drawNpc(ctx: Ctx, f: WaitFrame): void {
  const pal = f.palette;
  const { p } = waitPhase("npc", f.reduced ? STATIC_T.npc : f.t);
  // 泡泡（尾巴朝左，指向頭像）
  ctx.fillStyle = pal.parch;
  ctx.beginPath();
  ctx.roundRect(6, 3, 56, 24, 8);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(8, 17);
  ctx.lineTo(1, 23);
  ctx.lineTo(11, 21);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = pal.parchEdge;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(6, 3, 56, 24, 8);
  ctx.stroke();
  const shown = f.reduced ? 3 : Math.min(3, Math.floor(p / 0.22) + 1);
  ctx.fillStyle = pal.ink;
  for (let i = 0; i < shown; i++) {
    const d = DOTS[i]!;
    const grow = f.reduced ? 1 : clamp01((p - i * 0.22) / 0.08);
    ctx.globalAlpha = 0.35 + 0.6 * grow;
    ctx.beginPath();
    ctx.ellipse(d[0], d[1], 2.6 * grow + 0.4, 2.3 * grow + 0.4, 0.3, 0, TAU);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  if (f.reduced) {
    quill(ctx, 54, 18, pal, 0.32, 0.75);
    return;
  }
  // 羽毛筆點在目前那一點上（點下去再抬起）
  const i = Math.min(2, Math.floor(p / 0.22));
  const d = p < 0.66 ? DOTS[i]! : ([54, 15] as P);
  const tap = p < 0.66 ? Math.abs(Math.sin(((p % 0.22) / 0.22) * Math.PI)) * 4 : 2;
  quill(ctx, d[0] + 2, d[1] - tap, pal, 0.32, 0.75);
}

// ---------------------------------------------------------------- 多講一點

const PAGE = { lx: 7, rx: 53, y: 9, w: 44, h: 48 } as const;
const LINES = 5;

function pageLines(ctx: Ctx, x: number, k: number, pal: WaitPalette, alpha: number): P | null {
  ctx.strokeStyle = pal.ink;
  ctx.lineWidth = 1;
  ctx.globalAlpha = alpha;
  let tip: P | null = null;
  for (let l = 0; l < LINES; l++) {
    const lk = clamp01(k * LINES - l);
    if (lk <= 0) break;
    const y = PAGE.y + 8 + l * 8;
    const len = (PAGE.w - 10) * lk;
    ctx.beginPath();
    for (let i = 0; i <= 12; i++) {
      const s = i / 12;
      const px = x + 5 + s * len;
      const py = y + Math.sin(s * 14 + l) * 0.8;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
    if (lk < 1) tip = [x + 5 + len, y];
  }
  ctx.globalAlpha = 1;
  return tip;
}

function drawRetell(ctx: Ctx, f: WaitFrame): void {
  const pal = f.palette;
  const { p } = waitPhase("retell", f.reduced ? STATIC_T.retell : f.t);
  if (f.status === "done") {
    // 闔書：右頁往左蓋上，最後只剩封面
    const k = f.reduced ? 1 : clamp01((f.doneT ?? 0) / WAIT_DONE_MS);
    const w = 96 - 46 * ease(k);
    ctx.fillStyle = pal.leather;
    ctx.beginPath();
    ctx.roundRect(52 - w / 2, 6, w, 54, 4);
    ctx.fill();
    if (k < 1) {
      ctx.fillStyle = pal.parch;
      ctx.fillRect(52 - w / 2 + 4, 9, w - 8, 48);
    } else {
      ctx.strokeStyle = pal.gold;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(31, 10, 42, 46, 3);
      ctx.stroke();
    }
    seal(ctx, 52, 52, 4, pal, 1);
    return;
  }
  // 皮面＋兩頁
  ctx.fillStyle = pal.leather;
  ctx.beginPath();
  ctx.roundRect(3, 5, 98, 56, 4);
  ctx.fill();
  ctx.fillStyle = pal.parch;
  ctx.fillRect(PAGE.lx, PAGE.y, PAGE.w, PAGE.h);
  ctx.fillRect(PAGE.rx, PAGE.y, PAGE.w, PAGE.h);
  ctx.strokeStyle = "rgba(0,0,0,0.25)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(52, PAGE.y);
  ctx.lineTo(52, PAGE.y + PAGE.h);
  ctx.stroke();
  // 書籤（區域色）
  ctx.fillStyle = pal.seal;
  polyline(ctx, [[70, 57], [75, 57], [75, 63], [72.5, 61], [70, 63]], true);
  ctx.fill();
  // 左頁已寫滿
  pageLines(ctx, PAGE.lx, 1, pal, 0.5);
  const writeK = span(p, 0, 0.8);
  const turn = span(p, 0.8, 1);
  const tip = turn > 0 ? null : pageLines(ctx, PAGE.rx, writeK, pal, 0.8);
  if (turn > 0) {
    // 翻頁：右頁沿書脊翻到左邊（寬度照 cos 縮放）
    const c = Math.cos(Math.PI * ease(turn));
    const w = PAGE.w * Math.abs(c);
    const x = c >= 0 ? 52 : 52 - w;
    pageLines(ctx, PAGE.rx, 0, pal, 0);
    ctx.fillStyle = pal.parch;
    ctx.fillRect(x, PAGE.y - 1, w, PAGE.h + 2);
    ctx.strokeStyle = pal.parchEdge;
    ctx.globalAlpha = 0.6;
    ctx.strokeRect(x, PAGE.y - 1, w, PAGE.h + 2);
    ctx.globalAlpha = 1;
  }
  if (tip !== null) quill(ctx, tip[0], tip[1] + 1, pal, 0.55, 0.55);
  else quill(ctx, 96, 24, pal, 0.55, 0.3);
}

const DRAW: Readonly<Record<WaitSceneId, (ctx: Ctx, f: WaitFrame) => void>> = { skill: drawSkill, judge: drawJudge, npc: drawNpc, retell: drawRetell };

/** 畫一格等待動畫（邏輯座標 `WAIT_SIZE[scene]`；呼叫端先清畫布、縮放）。 */
export function drawWait(ctx: Ctx, frame: WaitFrame): void {
  const size = WAIT_SIZE[frame.scene];
  const f: WaitFrame = frame.scene === "skill" && frame.reduced && frame.status !== "done" ? { ...frame, t: STATIC_T.skill } : frame;
  ctx.save();
  DRAW[f.scene](ctx, f);
  if (f.status !== "fail") waitFx(ctx, size.w, size.h, f.palette, f.seed, f.t, f.reduced || f.status === "done");
  ctx.restore();
}
