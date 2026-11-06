// 實地地圖的只畫裝飾（Phase 6V-4；docs/archive/art/Fable審查.md 第 2 節 C）：花壇、攤布、晾衣繩、堆箱，以及放射狀鋪法。
// 全部只畫：不佔格、不擋路、不改地形與規則。6V-4b 起版面放在地圖檔的 `look.decor`（API `FieldView.decor`），
// 這裡只剩畫法；每次照 FieldView 檢查格子還空著才畫（world/fieldScenery.ts）。畫法是 Canvas 2D 純函式，只看格子座標雜湊。
import type { FieldView } from "../api/types";
import { dot, TAU, type Ctx } from "./artDraw";
import { seeded } from "./artRandom";
import { shade } from "./color";

const U = 52;
const OUT = "#1c1712";

/** API 送來的一件裝飾（地圖檔 `look.decor`）。 */
export type FieldDecorView = FieldView["decor"][number];

/** 一件一件畫的裝飾種類（放射狀鋪法另外畫成 `PavingScene`）。 */
export type PlazaDecorKind = Exclude<FieldDecorView["kind"], "radial_paving">;

/** 一件裝飾：左上格（`x`,`y`）、寬（格；晾衣繩 3 格，其他 1 格）、圖層（內容的種類表：站立／地面）。 */
export interface PlazaDecor {
  kind: PlazaDecorKind;
  x: number;
  y: number;
  w: number;
  /** `ground` 畫在人物下面（裝飾層）；`standing` 和人物一起照 y 排序（所在排的物件層）。 */
  layer: FieldDecorView["layer"];
}

/** 放射狀鋪法的範圍（格）與圓心（格，傳送石那一格的中心）。 */
export interface PavingScene {
  x0: number;
  y0: number;
  w: number;
  h: number;
  cx: number;
  cy: number;
  /** 範圍內畫鋪法的格子（`x,y`，石地；依座標排序）。 */
  cells: readonly string[];
}

/** 畫布高（格）：立著的（晾衣繩、堆箱）上面多 1 格給晾衣桿、箱堆；地面的 1 格。 */
export const DECOR_ROWS: Readonly<Record<PlazaDecorKind, number>> = { flower_bed: 1, stall_cloth: 1, clothesline: 2, crate_stack: 2 };

const rng = (x: number, y: number, k: number): (() => number) => seeded((x * 73856093) ^ (y * 19349663) ^ (k * 83492791));

// ---------------- 放射狀鋪法 ----------------

/** 鋪法的同心圓半徑（格）：傳送陣光圈（約 1.5 格）外面一圈一圈往外。 */
export const PAVING_RINGS: readonly number[] = [1.7, 2.5, 3.3, 4.1, 4.9, 5.7];
/** 金色嵌線在第幾圈。 */
export const PAVING_GOLD_RING = 1;

/** 一圈石板的放射接縫數（周長 ÷ 約 0.62 格，至少 8）。 */
export function pavingJoints(r0: number, r1: number): number {
  return Math.max(8, Math.round((TAU * ((r0 + r1) / 2)) / 0.62));
}

/**
 * 放射狀鋪法的第 `row` 列（相對範圍頂；畫布寬 `p.w` 格、高 1 格）：只在 `p.cells` 的格子裡畫（裁切）。
 * 一圈深一圈淺的環帶、同心接縫、每圈錯半塊的放射接縫，第 2 圈是一道淡金嵌線。
 */
export function drawPavingRow(ctx: Ctx, p: PavingScene, row: number): void {
  const y = p.y0 + row;
  const cells = new Set(p.cells);
  ctx.save();
  ctx.beginPath();
  let any = false;
  for (let i = 0; i < p.w; i++) {
    if (!cells.has(`${p.x0 + i},${y}`)) continue;
    ctx.rect(i * U, 0, U, U);
    any = true;
  }
  if (!any) {
    ctx.restore();
    return;
  }
  ctx.clip();
  ctx.translate((p.cx - p.x0) * U, (p.cy - y) * U);
  const rings = PAVING_RINGS;
  for (let i = 0; i < rings.length - 1; i++) {
    ctx.fillStyle = i % 2 === 0 ? "rgba(255,250,235,0.16)" : "rgba(120,104,78,0.10)";
    ctx.beginPath();
    ctx.arc(0, 0, rings[i + 1]! * U, 0, TAU);
    ctx.arc(0, 0, rings[i]! * U, 0, TAU, true);
    ctx.fill();
  }
  ctx.strokeStyle = "rgba(110,95,70,0.42)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (const r of rings) {
    ctx.moveTo(r * U, 0);
    ctx.arc(0, 0, r * U, 0, TAU);
  }
  ctx.stroke();
  ctx.strokeStyle = "rgba(110,95,70,0.32)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i < rings.length - 1; i++) {
    const n = pavingJoints(rings[i]!, rings[i + 1]!);
    const off = i % 2 === 0 ? 0 : 0.5;
    for (let k = 0; k < n; k++) {
      const a = ((k + off) / n) * TAU;
      ctx.moveTo(Math.cos(a) * rings[i]! * U, Math.sin(a) * rings[i]! * U);
      ctx.lineTo(Math.cos(a) * rings[i + 1]! * U, Math.sin(a) * rings[i + 1]! * U);
    }
  }
  ctx.stroke();
  ctx.strokeStyle = "rgba(232,187,72,0.5)";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.arc(0, 0, (rings[PAVING_GOLD_RING]! + 0.06) * U, 0, TAU);
  ctx.stroke();
  ctx.restore();
}

// ---------------- 花壇、攤布、晾衣繩、堆箱 ----------------

const FLOWER_COLORS = ["#e85a6a", "#f2c84a", "#f4f0f8", "#9a6ad8", "#ff8a4a"] as const;

/** 花壇（1×1）：圓角石框、深色土、綠葉叢、5～7 朵小花（顏色照雜湊）。 */
export function drawFlowerBed(ctx: Ctx, gx: number, gy: number): void {
  const r = rng(gx, gy, 61);
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.beginPath();
  ctx.ellipse(U / 2 + 3, U * 0.8, U * 0.4, 6, 0, 0, TAU);
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(5, 14, U - 10, U - 22, 8);
  ctx.fillStyle = "#d8ccb0";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.beginPath();
  ctx.roundRect(10, 18, U - 20, U - 31, 6);
  ctx.fillStyle = "#5a3e2a";
  ctx.fill();
  for (let i = 0; i < 6; i++) dot(ctx, 13 + r() * (U - 26), 20 + r() * (U - 36), 4 + r() * 2.5, i % 2 === 0 ? "#4f8a3a" : "#6aa84a");
  const n = 5 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    const fx = 13 + r() * (U - 26);
    const fy = 19 + r() * (U - 36);
    const c = FLOWER_COLORS[Math.floor(r() * FLOWER_COLORS.length)]!;
    for (let k = 0; k < 4; k++) dot(ctx, fx + Math.cos((k * TAU) / 4) * 1.8, fy + Math.sin((k * TAU) / 4) * 1.8, 1.6, c);
    dot(ctx, fx, fy, 1, "#f2c84a");
  }
}

const STALL_CLOTHS = ["#b8432f", "#3a5ad0", "#6a8a3a", "#8a3a8a"] as const;

/** 攤布（1×1）：鋪在地上的花布（布色與斜紋照雜湊）、四角壓著，上面幾樣貨（果子、陶罐、布卷）。 */
export function drawStall(ctx: Ctx, gx: number, gy: number): void {
  const r = rng(gx, gy, 62);
  const cloth = STALL_CLOTHS[Math.floor(r() * STALL_CLOTHS.length)]!;
  ctx.fillStyle = "rgba(0,0,0,0.2)";
  ctx.fillRect(7, 15, U - 10, U - 20);
  ctx.beginPath();
  ctx.moveTo(6, 12);
  ctx.lineTo(U - 5, 10);
  ctx.lineTo(U - 6, U - 7);
  ctx.lineTo(4, U - 6);
  ctx.closePath();
  ctx.fillStyle = cloth;
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.save();
  ctx.clip();
  ctx.strokeStyle = shade(cloth, 1.35);
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let k = -U; k < U * 2; k += 9) {
    ctx.moveTo(k, 0);
    ctx.lineTo(k + U, U);
  }
  ctx.stroke();
  ctx.restore();
  ctx.strokeStyle = "#f2e6c8";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(9, 14, U - 18, U - 24);
  // 貨：3 堆果子／陶罐／布卷
  for (let i = 0; i < 3; i++) {
    const x = 14 + i * 12 + (r() - 0.5) * 3;
    const y = 24 + (r() - 0.5) * 8;
    const kind = Math.floor(r() * 3);
    if (kind === 0) {
      for (const [dx, dy] of [[-2.5, 1], [2.5, 1], [0, -2]] as const) dot(ctx, x + dx, y + dy, 3, r() < 0.5 ? "#e8743a" : "#d83a3a");
    } else if (kind === 1) {
      ctx.beginPath();
      ctx.ellipse(x, y, 4.5, 5.5, 0, 0, TAU);
      ctx.fillStyle = "#b87a4a";
      ctx.fill();
      ctx.lineWidth = 1.2;
      ctx.strokeStyle = OUT;
      ctx.stroke();
      ctx.fillStyle = "#8a5a30";
      ctx.fillRect(x - 2.5, y - 7, 5, 2.5);
    } else {
      ctx.beginPath();
      ctx.roundRect(x - 6, y - 3, 12, 6, 3);
      ctx.fillStyle = "#e8dcc0";
      ctx.fill();
      ctx.lineWidth = 1.2;
      ctx.strokeStyle = OUT;
      ctx.stroke();
    }
  }
}

const LAUNDRY = ["#f4f0e8", "#7aa8d8", "#e8bb48", "#d86a5a", "#9ac88a"] as const;

/** 晾衣繩（3×2，下面那一列是所在格）：兩端木桿、中間下垂的繩子、4 件晾著的布（顏色照雜湊）。 */
export function drawClothesline(ctx: Ctx, gx: number, gy: number): void {
  const r = rng(gx, gy, 63);
  const base = U * 1.82;
  const top = U * 0.55;
  const xs = [U * 0.5, U * 2.5];
  for (const x of xs) {
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.beginPath();
    ctx.ellipse(x + 3, base, 7, 3, 0, 0, TAU);
    ctx.fill();
    ctx.beginPath();
    ctx.roundRect(x - 2.5, top - 4, 5, base - top + 4, 1.5);
    ctx.fillStyle = "#8a6440";
    ctx.fill();
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
  const sag = 12;
  const ropeY = (x: number): number => top + 2 + sag * Math.sin(Math.PI * ((x - xs[0]!) / (xs[1]! - xs[0]!)));
  ctx.strokeStyle = "#3a3028";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let i = 0; i <= 20; i++) {
    const x = xs[0]! + ((xs[1]! - xs[0]!) * i) / 20;
    if (i === 0) ctx.moveTo(x, ropeY(x));
    else ctx.lineTo(x, ropeY(x));
  }
  ctx.stroke();
  for (let i = 0; i < 4; i++) {
    const x = xs[0]! + 14 + i * 21 + (r() - 0.5) * 4;
    const w = 13 + r() * 5;
    const h = 16 + r() * 10;
    const y = ropeY(x + w / 2) - 1;
    const c = LAUNDRY[Math.floor(r() * LAUNDRY.length)]!;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w - 1, y + h);
    ctx.lineTo(x + w * 0.5, y + h - 3);
    ctx.lineTo(x + 1, y + h);
    ctx.closePath();
    ctx.fillStyle = c;
    ctx.fill();
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    dot(ctx, x + 2, y, 1.4, "#8a6440");
    dot(ctx, x + w - 2, y, 1.4, "#8a6440");
  }
}

/** 堆箱（1×2，下面那一列是所在格）：兩個木箱並排、上面疊一個小的，加一個麻袋（左右照雜湊）。 */
export function drawCrates(ctx: Ctx, gx: number, gy: number): void {
  const r = rng(gx, gy, 64);
  const flip = r() < 0.5;
  const crate = (x: number, y: number, s: number): void => {
    ctx.beginPath();
    ctx.roundRect(x, y, s, s, 2);
    ctx.fillStyle = shade("#a8804e", 0.9 + r() * 0.2);
    ctx.fill();
    ctx.lineWidth = 1.8;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    ctx.strokeStyle = "#6a4a2a";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(x + 2, y + 2);
    ctx.lineTo(x + s - 2, y + s - 2);
    ctx.moveTo(x + 2, y + s / 2);
    ctx.lineTo(x + s - 2, y + s / 2);
    ctx.stroke();
  };
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.beginPath();
  ctx.ellipse(U / 2 + 3, U * 1.86, U * 0.42, 6, 0, 0, TAU);
  ctx.fill();
  crate(5, U + 16, 21);
  crate(26, U + 18, 19);
  crate(flip ? 10 : 18, U - 2, 18);
  const sx = flip ? 40 : 8;
  ctx.beginPath();
  ctx.ellipse(sx, U + 34, 7, 9, 0, 0, TAU);
  ctx.fillStyle = "#c8b08a";
  ctx.fill();
  ctx.lineWidth = 1.4;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

export const DECOR_DRAW: Readonly<Record<PlazaDecorKind, (ctx: Ctx, gx: number, gy: number) => void>> = {
  flower_bed: drawFlowerBed,
  stall_cloth: drawStall,
  clothesline: drawClothesline,
  crate_stack: drawCrates,
};
