// 組裝式技能圖示的底圖（Phase 3-17）：元素標誌與紋理、形狀主圖、骨架徽章、外框形狀。
// 全部在 100×100 的座標系畫（呼叫端先縮放），只有 Canvas 2D 繪圖，沒有任何外部素材。
// 不認得的元素＝紫色六角（預設）、不認得的形狀＝自身光環、不認得的骨架＝空心圓徽章，永遠畫得出來。
// 元素色與 `battle/vfxPalette.ts` 的 `ELEMENT_VFX` 取自同一張 `render/palette.ts` 的 `ELEMENT_COLORS`。
import { ELEMENT_COLORS } from "./palette";

export type Ctx = CanvasRenderingContext2D;

const TAU = Math.PI * 2;

export interface ElementIcon {
  name: string;
  /** 標誌與主圖的亮色。 */
  accent: string;
  /** 底色漸層的暗端與亮端。 */
  dark: string;
  light: string;
}

/** 元素 → 圖示配色；顏色與特效共用 `render/palette.ts` 的 `ELEMENT_COLORS`（唯一來源）。 */
export const ELEMENT_ICON: Readonly<Record<string, ElementIcon>> = Object.fromEntries(
  Object.entries(ELEMENT_COLORS).map(([id, c]) => [id, { name: c.name, accent: c.accent, dark: c.dark, light: c.light }]),
);

export const DEFAULT_ELEMENT_ICON: ElementIcon = { name: "（無）", accent: "#e8e0ff", dark: "#221c44", light: "#6a5ad0" };
/** 工坊還沒選元素時的中性色。 */
export const NEUTRAL_ELEMENT_ICON: ElementIcon = { name: "（未選）", accent: "#c8ccd4", dark: "#23262d", light: "#4a4f5a" };

/** 元素代碼 → 配色；`undefined` ＝ 還沒選（中性），其他不認得 ＝ 預設。 */
export function elementPalette(el: string | null | undefined): ElementIcon {
  if (el === undefined) return NEUTRAL_ELEMENT_ICON;
  if (el === null) return DEFAULT_ELEMENT_ICON;
  return ELEMENT_ICON[el] ?? DEFAULT_ELEMENT_ICON;
}

export const RARITY_COLOR: Readonly<Record<string, string>> = {
  common: "#9aa0a6",
  rare: "#4da3ff",
  epic: "#b06cff",
  legendary: "#ffbf3a",
};
export const rarityColor = (rarity: string): string => RARITY_COLOR[rarity] ?? "#6a6f7a";

export const SKELETON_NAME: Readonly<Record<string, string>> = {
  strike: "打擊",
  area: "範圍",
  control: "控制",
  aura: "增益",
  summon: "召喚",
  trap: "陷阱",
  displace: "位移",
  consume_status: "引爆狀態",
  builder_finisher: "累積終結",
  stance: "姿態",
  reaction: "反應",
  modifier: "改造",
  passive: "被動",
  combo: "連段",
  rune: "刻印",
  sacrifice: "獻祭",
};

// ---- 小工具 ----

export function starPath(ctx: Ctx, cx: number, cy: number, n: number, ro: number, ri: number, rot = -Math.PI / 2): void {
  ctx.beginPath();
  for (let i = 0; i < n * 2; i++) {
    const r = i % 2 === 0 ? ro : ri;
    const a = rot + (i / (n * 2)) * TAU;
    ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
  }
  ctx.closePath();
}

function figure(ctx: Ctx, cx: number, cy: number, k: number, color: string): void {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(cx, cy - 9 * k, 6 * k, 0, TAU);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(cx - 11 * k, cy + 12 * k);
  ctx.quadraticCurveTo(cx - 11 * k, cy - 2 * k, cx, cy - 1 * k);
  ctx.quadraticCurveTo(cx + 11 * k, cy - 2 * k, cx + 11 * k, cy + 12 * k);
  ctx.closePath();
  ctx.fill();
}

/** 先畫深色描邊再畫本體，縮小時仍清楚。 */
function outlined(ctx: Ctx, path: () => void, color: string, width = 5): void {
  ctx.save();
  ctx.strokeStyle = "rgba(0,0,0,0.55)";
  ctx.lineWidth = width;
  ctx.lineJoin = "round";
  path();
  ctx.stroke();
  ctx.restore();
  ctx.fillStyle = color;
  path();
  ctx.fill();
}

// ---- 元素標誌（也用在飛行物的彈頭）----

export function elementGlyph(ctx: Ctx, el: string, cx: number, cy: number, k: number, color: string): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(k, k);
  ctx.fillStyle = color;
  ctx.strokeStyle = color;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  switch (el) {
    case "fire":
      ctx.beginPath();
      ctx.moveTo(0, -10);
      ctx.bezierCurveTo(7, -3, 8, 3, 0, 9);
      ctx.bezierCurveTo(-8, 3, -6, -2, -2, -4);
      ctx.bezierCurveTo(-2, -1, 0, 0, 0, -10);
      ctx.fill();
      break;
    case "ice":
      iceGlyph(ctx);
      break;
    case "lightning":
      ctx.beginPath();
      ctx.moveTo(3, -11);
      ctx.lineTo(-6, 1);
      ctx.lineTo(0, 1);
      ctx.lineTo(-3, 11);
      ctx.lineTo(7, -2);
      ctx.lineTo(1, -2);
      ctx.lineTo(5, -11);
      ctx.closePath();
      ctx.fill();
      break;
    case "poison":
      ctx.beginPath();
      ctx.moveTo(0, -10);
      ctx.bezierCurveTo(8, -1, 8, 8, 0, 8);
      ctx.bezierCurveTo(-8, 8, -8, -1, 0, -10);
      ctx.fill();
      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.beginPath();
      ctx.arc(-2, 2, 2.2, 0, TAU);
      ctx.arc(2.5, 4.5, 1.4, 0, TAU);
      ctx.fill();
      break;
    case "wind":
      ctx.lineWidth = 2.6;
      ctx.beginPath();
      ctx.moveTo(-10, -4);
      ctx.lineTo(4, -4);
      ctx.arc(4, -7.5, 3.5, Math.PI / 2, -Math.PI * 0.9, true);
      ctx.moveTo(-10, 2);
      ctx.lineTo(7, 2);
      ctx.arc(7, 6, 4, -Math.PI / 2, Math.PI * 0.9);
      ctx.moveTo(-7, 8);
      ctx.lineTo(-1, 8);
      ctx.stroke();
      break;
    case "earth":
      ctx.beginPath();
      ctx.moveTo(-11, 8);
      ctx.lineTo(-4, -6);
      ctx.lineTo(0, 0);
      ctx.lineTo(4, -9);
      ctx.lineTo(11, 8);
      ctx.closePath();
      ctx.fill();
      break;
    case "holy":
      starPath(ctx, 0, 0, 4, 11, 3.2);
      ctx.fill();
      starPath(ctx, 0, 0, 4, 6, 2, -Math.PI / 4);
      ctx.fill();
      break;
    case "shadow":
      ctx.beginPath();
      ctx.arc(0, 0, 9, 0, TAU);
      ctx.arc(4, -3, 7.5, 0, TAU, true);
      ctx.fill("evenodd");
      break;
    case "physical":
      starPath(ctx, 0, 0, 4, 10, 2.6, 0);
      ctx.fill();
      break;
    default:
      ctx.beginPath();
      for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU) * 8, Math.sin((i / 6) * TAU) * 8);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.6)";
      ctx.fillRect(-2, -5, 3, 10);
      break;
  }
  ctx.restore();
}

function iceGlyph(ctx: Ctx): void {
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  for (let i = 0; i < 3; i++) {
    const a = (i / 3) * Math.PI + Math.PI / 2;
    ctx.moveTo(Math.cos(a) * 9, Math.sin(a) * 9);
    ctx.lineTo(-Math.cos(a) * 9, -Math.sin(a) * 9);
  }
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU + Math.PI / 2;
    const bx = Math.cos(a) * 5.5;
    const by = Math.sin(a) * 5.5;
    ctx.moveTo(bx, by);
    ctx.lineTo(bx + Math.cos(a + 0.8) * 3.5, by + Math.sin(a + 0.8) * 3.5);
    ctx.moveTo(bx, by);
    ctx.lineTo(bx + Math.cos(a - 0.8) * 3.5, by + Math.sin(a - 0.8) * 3.5);
  }
  ctx.stroke();
}

// ---- 元素紋理（底圖，淡淡的；確定性，沒有亂數）----

export function elementTexture(ctx: Ctx, el: string, p: ElementIcon): void {
  ctx.save();
  ctx.globalAlpha = 0.18;
  ctx.strokeStyle = p.accent;
  ctx.fillStyle = p.accent;
  ctx.lineWidth = 2;
  switch (el) {
    case "fire":
      for (let i = 0; i < 5; i++) elementGlyph(ctx, "fire", 10 + i * 20, 96, 1.3 + (i % 2) * 0.5, p.accent);
      break;
    case "ice":
      ctx.beginPath();
      ctx.moveTo(0, 30);
      ctx.lineTo(30, 0);
      ctx.moveTo(60, 100);
      ctx.lineTo(100, 55);
      ctx.moveTo(0, 70);
      ctx.lineTo(45, 100);
      ctx.moveTo(70, 0);
      ctx.lineTo(100, 25);
      ctx.stroke();
      break;
    case "lightning":
      ctx.beginPath();
      ctx.moveTo(0, 20);
      ctx.lineTo(20, 32);
      ctx.lineTo(12, 40);
      ctx.lineTo(36, 54);
      ctx.moveTo(100, 60);
      ctx.lineTo(82, 70);
      ctx.lineTo(90, 78);
      ctx.lineTo(66, 96);
      ctx.stroke();
      break;
    case "poison":
      for (const [x, y, r] of [
        [14, 30, 6],
        [86, 40, 8],
        [28, 88, 5],
        [74, 86, 4],
        [60, 12, 3],
      ] as const) {
        ctx.beginPath();
        ctx.arc(x, y, r, 0, TAU);
        ctx.stroke();
      }
      break;
    case "wind":
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.arc(50, 50, 22 + i * 14, -0.4 + i, 1.4 + i);
        ctx.stroke();
      }
      break;
    case "earth":
      ctx.beginPath();
      ctx.moveTo(0, 78);
      ctx.lineTo(30, 72);
      ctx.lineTo(60, 80);
      ctx.lineTo(100, 70);
      ctx.moveTo(0, 90);
      ctx.lineTo(40, 86);
      ctx.lineTo(100, 92);
      ctx.stroke();
      break;
    case "holy":
      holyRays(ctx);
      break;
    case "shadow":
      ctx.globalAlpha = 0.25;
      ctx.fillStyle = "#000";
      for (const [x, y, r] of [
        [10, 90, 26],
        [90, 10, 22],
        [95, 85, 16],
      ] as const) {
        ctx.beginPath();
        ctx.arc(x, y, r, 0, TAU);
        ctx.fill();
      }
      break;
    case "physical":
      ctx.beginPath();
      for (let i = -100; i < 100; i += 9) {
        ctx.moveTo(i, 100);
        ctx.lineTo(i + 100, 0);
      }
      ctx.globalAlpha = 0.07;
      ctx.stroke();
      break;
    default:
      break;
  }
  ctx.restore();
}

function holyRays(ctx: Ctx): void {
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * TAU;
    ctx.beginPath();
    ctx.moveTo(50, 50);
    ctx.lineTo(50 + Math.cos(a - 0.08) * 80, 50 + Math.sin(a - 0.08) * 80);
    ctx.lineTo(50 + Math.cos(a + 0.08) * 80, 50 + Math.sin(a + 0.08) * 80);
    ctx.fill();
  }
}

/** 畫元素底色（漸層＋淡紋理）；`el` 為 `undefined`（還沒選）時只有中性漸層。 */
export function paintBackground(ctx: Ctx, el: string | null | undefined): void {
  const p = elementPalette(el);
  const bg = ctx.createRadialGradient(38, 30, 4, 50, 50, 78);
  bg.addColorStop(0, p.light);
  bg.addColorStop(1, p.dark);
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, 100, 100);
  if (el !== undefined) elementTexture(ctx, el ?? "default", p);
}

// ---- 形狀主圖 ----

function projectile(ctx: Ctx, el: string, p: ElementIcon): void {
  const x0 = 22;
  const y0 = 78;
  const x1 = 64;
  const y1 = 36;
  const g = ctx.createLinearGradient(x0, y0, x1, y1);
  g.addColorStop(0, "rgba(255,255,255,0)");
  g.addColorStop(1, p.accent);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1 - 6, y1 - 6);
  ctx.lineTo(x1 + 6, y1 + 6);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = p.accent;
  ctx.globalAlpha = 0.5;
  ctx.beginPath();
  ctx.arc(x1, y1, 17, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.save();
  ctx.translate(x1, y1);
  ctx.rotate(Math.PI / 4);
  ctx.translate(-x1, -y1);
  elementGlyph(ctx, el, x1, y1, 1.55, "#ffffff");
  ctx.restore();
}

function slash(ctx: Ctx, el: string, p: ElementIcon): void {
  const crescent = (dx: number, dy: number) => {
    ctx.beginPath();
    ctx.moveTo(24 + dx, 24 + dy);
    ctx.quadraticCurveTo(90 + dx, 12 + dy, 78 + dx, 80 + dy);
    ctx.quadraticCurveTo(70 + dx, 34 + dy, 24 + dx, 24 + dy);
    ctx.closePath();
  };
  crescent(3, 3);
  ctx.fillStyle = "rgba(0,0,0,0.4)";
  ctx.fill();
  crescent(0, 0);
  const g = ctx.createLinearGradient(24, 24, 80, 80);
  g.addColorStop(0, p.accent);
  g.addColorStop(0.5, "#ffffff");
  g.addColorStop(1, p.accent);
  ctx.fillStyle = g;
  ctx.fill();
  elementGlyph(ctx, el, 40, 62, 1.3, p.accent);
}

function buffTarget(ctx: Ctx, el: string, p: ElementIcon): void {
  ctx.fillStyle = p.accent;
  ctx.globalAlpha = 0.35;
  ctx.beginPath();
  ctx.ellipse(46, 78, 24, 8, 0, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
  figure(ctx, 46, 64, 1.25, "#ffffff");
  ctx.strokeStyle = p.accent;
  ctx.lineWidth = 4.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const y of [36, 48]) {
    ctx.beginPath();
    ctx.moveTo(64, y + 8);
    ctx.lineTo(72, y);
    ctx.lineTo(80, y + 8);
    ctx.stroke();
  }
  elementGlyph(ctx, el, 46, 30, 0.9, p.accent);
}

function beam(ctx: Ctx, el: string, p: ElementIcon): void {
  ctx.save();
  ctx.translate(50, 50);
  ctx.rotate(-Math.PI / 4);
  ctx.fillStyle = p.accent;
  ctx.globalAlpha = 0.45;
  ctx.fillRect(-42, -12, 84, 24);
  ctx.globalAlpha = 1;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(-42, -5, 84, 10);
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  for (let i = -1; i <= 1; i++) ctx.fillRect(i * 24 - 5, -5, 10, 10);
  ctx.restore();
  elementGlyph(ctx, el, 74, 26, 1.0, p.accent);
}

function fan(ctx: Ctx, el: string, p: ElementIcon): void {
  const ox = 22;
  const oy = 78;
  const a = -Math.PI / 4;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(ox, oy);
  ctx.arc(ox, oy, 66, a - 0.55, a + 0.55);
  ctx.closePath();
  const g = ctx.createRadialGradient(ox, oy, 4, ox, oy, 66);
  g.addColorStop(0, "#ffffff");
  g.addColorStop(1, p.accent);
  ctx.fillStyle = g;
  ctx.globalAlpha = 0.9;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = "rgba(0,0,0,0.3)";
  ctx.lineWidth = 2;
  for (const rr of [30, 48]) {
    ctx.beginPath();
    ctx.arc(ox, oy, rr, a - 0.55, a + 0.55);
    ctx.stroke();
  }
  ctx.restore();
  elementGlyph(ctx, el, 60, 42, 1.3, "rgba(0,0,0,0.45)");
}

const GRID: Readonly<Record<string, readonly number[]>> = {
  square3: [1, 1, 1, 1, 1, 1, 1, 1, 1],
  cross: [0, 1, 0, 1, 1, 1, 0, 1, 0],
  ring: [1, 1, 1, 1, 0, 1, 1, 1, 1],
};

function grid(ctx: Ctx, el: string, p: ElementIcon, shape: string): void {
  const cells = GRID[shape] ?? GRID["square3"] ?? [];
  const cs = 19;
  const gap = 3;
  const o = 50 - (cs * 3 + gap * 2) / 2;
  for (let i = 0; i < 9; i++) {
    const x = o + (i % 3) * (cs + gap);
    const y = o + Math.floor(i / 3) * (cs + gap);
    ctx.beginPath();
    ctx.roundRect(x, y, cs, cs, 3);
    if (cells[i] === 1) {
      ctx.fillStyle = p.accent;
      ctx.globalAlpha = 0.85;
      ctx.fill();
      ctx.globalAlpha = 1;
    } else {
      ctx.strokeStyle = "rgba(255,255,255,0.45)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
  if (shape === "ring") figure(ctx, 50, 52, 0.62, "#ffffff");
  else {
    outlined(ctx, () => starPath(ctx, 50, 50, 8, 17, 8), "#ffffff", 4);
    elementGlyph(ctx, el, 50, 50, 0.9, p.dark);
  }
}

function chain(ctx: Ctx, el: string, p: ElementIcon): void {
  const pts: ReadonlyArray<readonly [number, number]> = [
    [22, 72],
    [48, 30],
    [78, 62],
  ];
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.beginPath();
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, ay] = pts[i] as readonly [number, number];
    const [bx, by] = pts[i + 1] as readonly [number, number];
    ctx.moveTo(ax, ay);
    for (let k = 1; k < 5; k++) {
      const t = k / 5;
      const nx = -(by - ay);
      const ny = bx - ax;
      const len = Math.hypot(nx, ny);
      const off = (k % 2 === 1 ? 5 : -5) / len;
      ctx.lineTo(ax + (bx - ax) * t + nx * off, ay + (by - ay) * t + ny * off);
    }
    ctx.lineTo(bx, by);
  }
  ctx.stroke();
  for (const [x, y] of pts) {
    ctx.fillStyle = p.accent;
    ctx.beginPath();
    ctx.arc(x, y, 9, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,0.4)";
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  elementGlyph(ctx, el, 48, 30, 0.6, p.dark);
}

function groundMarker(ctx: Ctx, p: ElementIcon): void {
  ctx.save();
  for (const [rx, a] of [
    [30, 0.35],
    [22, 0.6],
    [13, 0.9],
  ] as const) {
    ctx.strokeStyle = p.accent;
    ctx.globalAlpha = a;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(50, 70, rx, rx * 0.4, 0, 0, TAU);
    ctx.stroke();
  }
  ctx.restore();
}

function trapJaws(ctx: Ctx, el: string, p: ElementIcon): void {
  for (const [base, tip, color] of [
    [50, 62, "#ffffff"],
    [76, 64, "#d8dce4"],
  ] as const) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(26, base);
    for (let i = 0; i < 6; i++) {
      ctx.lineTo(26 + i * 8 + 4, tip);
      ctx.lineTo(26 + (i + 1) * 8, base);
    }
    ctx.lineTo(74, base + (base < tip ? -4 : 4));
    ctx.lineTo(26, base + (base < tip ? -4 : 4));
    ctx.closePath();
    ctx.fill();
  }
  elementGlyph(ctx, el, 50, 28, 1.0, p.accent);
}

function ground(ctx: Ctx, el: string, p: ElementIcon, skeleton: string | null): void {
  groundMarker(ctx, p);
  if (skeleton === "summon") {
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, 100, 70);
    ctx.clip();
    figure(ctx, 50, 54, 1.25, "#ffffff");
    ctx.restore();
    elementGlyph(ctx, el, 50, 42, 0.7, p.dark);
  } else if (skeleton === "trap") {
    trapJaws(ctx, el, p);
  } else {
    ctx.fillStyle = p.accent;
    ctx.beginPath();
    ctx.moveTo(50, 60);
    ctx.lineTo(40, 46);
    ctx.lineTo(60, 46);
    ctx.closePath();
    ctx.fill();
    elementGlyph(ctx, el, 50, 32, 1.4, "#ffffff");
  }
}

function selfAura(ctx: Ctx, p: ElementIcon, skeleton: string | null): void {
  for (const [r, a] of [
    [36, 0.25],
    [28, 0.45],
    [20, 0.7],
  ] as const) {
    ctx.strokeStyle = p.accent;
    ctx.globalAlpha = a;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(50, 52, r, 0, TAU);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
  figure(ctx, 50, 56, 1.0, "#ffffff");
  if (skeleton === "stance") {
    outlined(
      ctx,
      () => {
        ctx.beginPath();
        ctx.moveTo(50, 40);
        ctx.lineTo(62, 45);
        ctx.lineTo(60, 60);
        ctx.lineTo(50, 68);
        ctx.lineTo(40, 60);
        ctx.lineTo(38, 45);
        ctx.closePath();
      },
      p.accent,
      4,
    );
  }
}

function alliesRadius(ctx: Ctx, el: string, p: ElementIcon): void {
  ctx.strokeStyle = p.accent;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(50, 72, 38, Math.PI, 0);
  ctx.stroke();
  ctx.globalAlpha = 0.2;
  ctx.fillStyle = p.accent;
  ctx.fill();
  ctx.globalAlpha = 1;
  figure(ctx, 28, 66, 0.7, "rgba(255,255,255,0.75)");
  figure(ctx, 72, 66, 0.7, "rgba(255,255,255,0.75)");
  figure(ctx, 50, 60, 1.0, "#ffffff");
  elementGlyph(ctx, el, 50, 30, 0.9, p.accent);
}

function hurl(ctx: Ctx, el: string, p: ElementIcon): void {
  ctx.strokeStyle = p.accent;
  ctx.setLineDash([5, 4]);
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(24, 76);
  ctx.quadraticCurveTo(50, 8, 76, 70);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#c8894a";
  ctx.fillRect(40, 22, 20, 20);
  ctx.strokeStyle = "#5a3412";
  ctx.lineWidth = 2;
  ctx.strokeRect(40, 22, 20, 20);
  elementGlyph(ctx, el, 76, 70, 1.0, "#ffffff");
}

function pair(ctx: Ctx, p: ElementIcon): void {
  figure(ctx, 30, 58, 0.85, "#ffffff");
  figure(ctx, 70, 58, 0.85, p.accent);
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(36, 30);
  ctx.quadraticCurveTo(50, 20, 64, 30);
  ctx.moveTo(64, 30);
  ctx.lineTo(57, 27);
  ctx.moveTo(64, 30);
  ctx.lineTo(60, 23);
  ctx.stroke();
}

/** 形狀主圖需要的資料（一段技能）。 */
export interface MotifSpec {
  shape_id: string | null;
  skeleton: string | null;
  /** 遠程（射程 ≥ 2，或武器射程且需要遠程武器）：單體畫飛行物，否則揮砍月牙。 */
  ranged: boolean;
}

/** 單體技能的遠近：有射程看射程；射程是武器（`null`）時看武器需求。 */
export function isRanged(range: number | null, weaponReq: string): boolean {
  if (typeof range === "number") return range >= 2;
  return weaponReq === "ranged";
}

/** 畫形狀主圖；形狀不認得（含 `single` 以外的未知值）退回自身光環。 */
export function drawMotif(ctx: Ctx, spec: MotifSpec, el: string, p: ElementIcon): void {
  const shape = spec.shape_id;
  if (shape === "single" && spec.skeleton === "aura") buffTarget(ctx, el, p);
  else if (shape === "single") (spec.ranged ? projectile : slash)(ctx, el, p);
  else if (shape === "line") beam(ctx, el, p);
  else if (shape === "cone") fan(ctx, el, p);
  else if (shape !== null && GRID[shape] !== undefined) grid(ctx, el, p, shape);
  else if (shape === "chain") chain(ctx, el, p);
  else if (shape === "ground_tile") ground(ctx, el, p, spec.skeleton);
  else if (shape === "allies_in_radius") alliesRadius(ctx, el, p);
  else if (shape === "object_then_tile") hurl(ctx, el, p);
  else if (shape === "unit_pair" || shape === "unit_then_tile") pair(ctx, p);
  else selfAura(ctx, p, spec.skeleton);
}

// ---- 骨架徽章 ----

export function skeletonGlyph(ctx: Ctx, sk: string | null, cx: number, cy: number): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.strokeStyle = "#ffffff";
  ctx.fillStyle = "#ffffff";
  ctx.lineWidth = 2.2;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const line = (...pts: number[]) => {
    ctx.beginPath();
    for (let i = 0; i < pts.length; i += 2) {
      const x = pts[i] as number;
      const y = pts[i + 1] as number;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  };
  switch (sk) {
    case "strike":
      ctx.beginPath();
      ctx.moveTo(-6, 6);
      ctx.lineTo(6, -6);
      ctx.moveTo(-6, 1);
      ctx.lineTo(-1, 6);
      ctx.stroke();
      break;
    case "area":
      starPath(ctx, 0, 0, 6, 7.5, 3.5);
      ctx.fill();
      break;
    case "control":
      ctx.beginPath();
      ctx.arc(0, -2, 4, Math.PI, 0);
      ctx.stroke();
      ctx.fillRect(-5.5, -1.5, 11, 8);
      break;
    case "aura":
      ctx.beginPath();
      ctx.moveTo(-5, 1);
      ctx.lineTo(0, -4);
      ctx.lineTo(5, 1);
      ctx.moveTo(-5, 6);
      ctx.lineTo(0, 1);
      ctx.lineTo(5, 6);
      ctx.stroke();
      break;
    case "summon":
      ctx.beginPath();
      ctx.moveTo(0, -6);
      ctx.lineTo(0, 6);
      ctx.moveTo(-6, 0);
      ctx.lineTo(6, 0);
      ctx.stroke();
      break;
    case "trap":
      line(-7, -1, -4, 4, -1, -1, 2, 4, 5, -1, 7, 3);
      break;
    case "displace":
      ctx.beginPath();
      ctx.moveTo(-7, 0);
      ctx.lineTo(7, 0);
      ctx.moveTo(3, -4);
      ctx.lineTo(7, 0);
      ctx.lineTo(3, 4);
      ctx.moveTo(-3, -4);
      ctx.lineTo(-7, 0);
      ctx.lineTo(-3, 4);
      ctx.stroke();
      break;
    case "rune":
      ctx.beginPath();
      ctx.moveTo(0, -7);
      ctx.lineTo(7, 0);
      ctx.lineTo(0, 7);
      ctx.lineTo(-7, 0);
      ctx.closePath();
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, -2.6);
      ctx.lineTo(2.6, 0);
      ctx.lineTo(0, 2.6);
      ctx.lineTo(-2.6, 0);
      ctx.closePath();
      ctx.fill();
      break;
    case "consume_status":
      starPath(ctx, 0, 0, 5, 7, 3);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, 0, 1.8, 0, TAU);
      ctx.fill();
      break;
    case "builder_finisher":
      for (let i = 0; i < 3; i++) ctx.fillRect(-6 + i * 4.5, 4 - i * 4, 3, 3 + i * 4);
      break;
    case "stance":
      ctx.beginPath();
      ctx.moveTo(0, -7);
      ctx.lineTo(6, -4);
      ctx.lineTo(5, 3);
      ctx.lineTo(0, 7);
      ctx.lineTo(-5, 3);
      ctx.lineTo(-6, -4);
      ctx.closePath();
      ctx.stroke();
      break;
    case "reaction":
      ctx.beginPath();
      ctx.arc(0, 0, 5.5, -2.6, 1.4);
      ctx.stroke();
      line(-6, -6, -5, -1, -1, -3.5);
      break;
    default:
      ctx.beginPath();
      ctx.arc(0, 0, 5, 0, TAU);
      ctx.stroke();
      break;
  }
  ctx.restore();
}

// ---- 外框形狀（技能類型）----

/** 外框路徑（100×100 座標）：主動＝圓角方、反應＝盾形、被動＝圓、姿態＝六角、修正＝齒輪。 */
export function framePath(ctx: Ctx, kind: string, inset = 0): void {
  const i = inset;
  ctx.beginPath();
  switch (kind) {
    case "reaction":
      ctx.moveTo(8 + i, 6 + i);
      ctx.lineTo(92 - i, 6 + i);
      ctx.lineTo(92 - i, 50);
      ctx.quadraticCurveTo(92 - i, 82 - i, 50, 96 - i * 1.4);
      ctx.quadraticCurveTo(8 + i, 82 - i, 8 + i, 50);
      ctx.closePath();
      break;
    case "passive":
      ctx.arc(50, 50, 46 - i, 0, TAU);
      break;
    case "stance":
      for (let k = 0; k < 6; k++) {
        const a = (k / 6) * TAU;
        ctx.lineTo(50 + Math.cos(a) * (48 - i), 50 + Math.sin(a) * (48 - i));
      }
      ctx.closePath();
      break;
    case "modifier": {
      const teeth = 12;
      for (let k = 0; k < teeth * 4; k++) {
        const a = (k / (teeth * 4)) * TAU;
        const r = (k % 4 < 2 ? 48 : 43) - i;
        ctx.lineTo(50 + Math.cos(a) * r, 50 + Math.sin(a) * r);
      }
      ctx.closePath();
      break;
    }
    default:
      ctx.roundRect(4 + i, 4 + i, 92 - i * 2, 92 - i * 2, 14);
  }
}
