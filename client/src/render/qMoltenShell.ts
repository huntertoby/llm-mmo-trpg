// 熔殼塔盾（RG-5，#163 護陣；`kite_shield` 的玩家形制 `molten_shell`，docs/art/RG樣張.md 10.1、10.2、10.4、10.8）。
// 熔殼甲兵身上那片立殼改成人手持的塔盾：畫法照樣張 docs/art/sample/rgPlayerShield.js 第 2 節原樣移植（逐像素比對：dev/rg5-shield-gallery.html）。
// 座標都在盾錨點裡（和塔盾同一個錨點）：正面＝pdHeld2 的 translate(手 x, −9.5)、側面＝shieldSide 的 translate(8.6, −13.5)、
// 背面＝shieldBack 的 translate(手 x − 1, 手 y − 5)。握法、手臂、圖層、朝西換手照塔盾（isTowerLike）。
// 顏色（10.4）：殼板＝材質主色（含元素混色，colors(it)[0]）往玄武岩 #4a3631 混 0.35；迎光、下片、內面、殼緣、板緣亮邊由殼板算；
// 殼縫紅光 #ff6a1a＋芯 #ffd04a 固定，不跟材質、不跟元素（10.8 決定 3）。
// 三道殼縫各一張偏移表（審查 P-2）：上＝只裂左半邊、短；中＝最長、右端往下斜；下＝斜、中段分岔；間距不等分。圖示（qIcon/greatShields.ts）共用同一張表。
import type { Ctx } from "./artDraw";
import { colors, mix, TAU, type QItem } from "./qCore";

/** 固定色：玄武岩（殼板混色的目標）、殼縫紅光與芯、皮帶。 */
export const SHELL_FIX = { basalt: "#4a3631", glow: "#ff6a1a", core: "#ffd04a", strap: "#3a2414" } as const;
/** 殼板混玄武岩的比例（10.8 決定 2）。 */
export const SHELL_K = 0.35;
const OUT = "#16121a";

/** 殼的配色：plate＝殼板本色、lit＝迎光那片、low＝下片、inner＝殼的內面（厚度、背面）、edge＝殼緣。 */
export interface ShellPal {
  plate: string;
  lit: string;
  low: string;
  inner: string;
  edge: string;
}
const dk = (c: string, t = 0.25): string => mix(c, "#000000", t);
/** 材質主色（含元素混色）→ 殼的配色（樣張 shellPal）。 */
export function shellPalOf(a: string): ShellPal {
  const plate = mix(a, SHELL_FIX.basalt, SHELL_K);
  return { plate, lit: mix(plate, "#ffffff", 0.16), low: dk(plate, 0.18), inner: dk(plate, 0.38), edge: dk(plate, 0.3) };
}
/** 紙娃娃的配色：主色＝colors(it)[0]（材質色，有元素時已混元素色）。 */
export const shellPal = (it: QItem): ShellPal => shellPalOf(colors(it)[0]);

type Pt = readonly [number, number];
function fill(ctx: Ctx, c: string, path: () => void): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  path();
  ctx.fill();
}
export function line(ctx: Ctx, c: string, w: number, pts: ReadonlyArray<Pt>): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.stroke();
}

// ---------- 殼縫 ----------
interface CrackDef {
  y: number;
  x0: number;
  x1: number;
  p: ReadonlyArray<Pt>;
  br?: readonly [number, ReadonlyArray<Pt>];
}
/** 三道殼縫（樣張 CRACKS）：y、x0、x1＝正面模型座標；p＝[沿線比例 t, 上下偏移（×齒高 h）]；br＝[從第幾點分岔, 分岔的後續點]。 */
const CRACKS: readonly CrackDef[] = [
  { y: -11.2, x0: -6.6, x1: 0.8, p: [[0, 0.2], [0.24, -0.85], [0.47, 0.45], [0.72, -0.6], [1, 0.3]] },
  { y: -4.6, x0: -7.4, x1: 6.6, p: [[0, -0.45], [0.12, 0.45], [0.27, -0.8], [0.41, 0.3], [0.56, -0.5], [0.71, 0.55], [0.85, -0.2], [1, 1.1]] },
  { y: 4.0, x0: -5.6, x1: 5.2, p: [[0, -1.1], [0.2, -0.2], [0.39, -0.95], [0.6, 0.25], [0.8, -0.15], [1, 1]], br: [2, [[0.46, 0.9], [0.5, 2.1]]] },
];
const ID = (v: number): number => v;
/** 第 v 道殼縫的折線（主縫；有分岔時第二條是分岔）。X、Y＝模型座標 → 畫布座標；h＝齒高；xs＝橫向縮（背面 0.8）。 */
export function crack(v: number, h: number, X: (x: number) => number = ID, Y: (y: number) => number = ID, xs = 1): Pt[][] {
  const C = CRACKS[v]!;
  const pt = ([t, d]: Pt): Pt => [X((C.x0 + (C.x1 - C.x0) * t) * xs), Y(C.y) + d * h];
  const main = C.p.map(pt);
  return C.br ? [main, [main[C.br[0]]!, ...C.br[1].map(pt)]] : [main];
}
function seam(ctx: Ctx, pts: ReadonlyArray<Pt>, w = 1, a = 1): void {
  ctx.save();
  ctx.globalAlpha = a;
  line(ctx, SHELL_FIX.glow, w, pts);
  line(ctx, SHELL_FIX.core, w * 0.38, pts);
  ctx.restore();
}
/** 一道殼縫（一條折線）：裂縫下緣一條下一片殼板的亮邊（板緣），紅光壓在上面。 */
function plateSeam(ctx: Ctx, pts: ReadonlyArray<Pt>, w: number, lit: string, dy: number): void {
  line(
    ctx,
    lit,
    w * 0.55,
    pts.map(([x, y]) => [x, y + dy] as const),
  );
  line(ctx, SHELL_FIX.glow, w, pts);
  line(ctx, SHELL_FIX.core, w * 0.38, pts);
}

/** 正面外形：蛋形頂、兩側往外鼓、下緣微收、圓角；x ±8.5、y −18～9。s＝縮放（數字或 [sx, sy]）、ox／oy＝位移、i＝往內縮。 */
export function shellPath(ctx: Ctx, s: number | readonly [number, number] = 1, ox = 0, oy = 0, i = 0): void {
  const [sx, sy] = typeof s === "number" ? [s, s] : s;
  const X = (x: number): number => ox + x * sx;
  const Y = (y: number): number => oy + y * sy;
  const w = 8.5 - i;
  const wb = 7.2 - i;
  const top = -18 + i;
  const bot = 9 - i;
  ctx.moveTo(X(-wb + 1.4), Y(bot));
  ctx.quadraticCurveTo(X(-wb), Y(bot), X(-wb - 0.2), Y(bot - 2));
  ctx.quadraticCurveTo(X(-w - 0.4), Y(-4), X(-w + 0.6), Y(-11));
  ctx.quadraticCurveTo(X(-w * 0.55), Y(top + 0.4), X(0), Y(top));
  ctx.quadraticCurveTo(X(w * 0.55), Y(top + 0.4), X(w - 0.6), Y(-11));
  ctx.quadraticCurveTo(X(w + 0.4), Y(-4), X(wb + 0.2), Y(bot - 2));
  ctx.quadraticCurveTo(X(wb), Y(bot), X(wb - 1.4), Y(bot));
  ctx.closePath();
}

/** 正面：殼緣暗一圈、上片迎光、下片暗、右緣露一條內面（厚度）、三道殼縫（樣張 shellFront）。 */
export function shellFrontPal(ctx: Ctx, pal: ShellPal): void {
  ctx.save();
  fill(ctx, pal.edge, () => shellPath(ctx));
  fill(ctx, pal.plate, () => shellPath(ctx, 1, 0, 0, 1.1));
  ctx.save();
  ctx.beginPath();
  shellPath(ctx, 1, 0, 0, 1.1);
  ctx.clip();
  fill(ctx, pal.lit, () => ctx.rect(-10, -20, 20, 9.6)); // 上片迎光
  fill(ctx, pal.low, () => ctx.rect(-10, 3.2, 20, 7)); // 下片暗
  fill(ctx, pal.inner, () => {
    // 右緣看到一點殼的厚度（內面）
    ctx.moveTo(5.6, -16);
    ctx.quadraticCurveTo(9.6, -4, 6.4, 10);
    ctx.lineTo(12, 10);
    ctx.lineTo(12, -16);
    ctx.closePath();
  });
  fill(ctx, "rgba(255,255,255,0.4)", () => ctx.ellipse(-4.2, -12.4, 0.9, 2.6, 0.5, 0, TAU));
  ctx.restore();
  const lit = mix(pal.plate, "#ffffff", 0.3);
  for (let v = 0; v < 3; v++) crack(v, 1.5).forEach((pts) => plateSeam(ctx, pts, 1.1, lit, 1.0));
  ctx.restore();
}

/** 側面：敵人那片立殼（inkCreature molten_shield／樣張 rgUnits.js SHELL.a，x 18～29、y 0～−30）等比縮 0.777 進塔盾側面錨點，
 *  新月形、三道殼縫照原座標；不畫扣盾的前腳（手握）。朝東座標，朝西由 stamp 鏡像。 */
export function shellSidePal(ctx: Ctx, pal: ShellPal): void {
  const s = 23.3 / 30;
  ctx.save();
  ctx.translate(-2.2 - 18.2 * s, 13.3);
  ctx.scale(s, s);
  const shape = (): void => {
    ctx.moveTo(18.2, 0);
    ctx.lineTo(18.6, -14);
    ctx.quadraticCurveTo(18.2, -25, 20.4, -28.8);
    ctx.quadraticCurveTo(23.6, -30, 25.6, -24.4);
    ctx.quadraticCurveTo(29, -15, 27.8, -5);
    ctx.quadraticCurveTo(27.4, -1.4, 26.4, 0);
    ctx.closePath();
  };
  fill(ctx, pal.plate, shape);
  ctx.save();
  ctx.beginPath();
  shape();
  ctx.clip();
  fill(ctx, pal.inner, () => {
    ctx.moveTo(17, 0);
    ctx.lineTo(17.4, -30);
    ctx.lineTo(21.4, -30);
    ctx.quadraticCurveTo(20.6, -14, 21.4, 0);
    ctx.closePath();
  });
  fill(ctx, pal.lit, () => {
    ctx.moveTo(21.4, -30);
    ctx.lineTo(30, -30);
    ctx.lineTo(30, -20.6);
    ctx.quadraticCurveTo(25.4, -22.6, 21, -23);
    ctx.closePath();
  });
  fill(ctx, pal.low, () => {
    ctx.moveTo(21.4, -7.2);
    ctx.quadraticCurveTo(25, -8.4, 30, -7.6);
    ctx.lineTo(30, 1);
    ctx.lineTo(21.4, 1);
    ctx.closePath();
  });
  fill(ctx, "rgba(255,255,255,0.4)", () => ctx.ellipse(23, -26.2, 0.8, 2.2, 0.5, 0, TAU));
  ctx.restore();
  const w = (1.1 / s) * 0.85;
  seam(ctx, [[21, -22.6], [22.6, -24.2], [24.2, -22.2], [25.8, -23.4], [27.6, -20.8]], w);
  seam(ctx, [[21.2, -15], [22.8, -16.8], [24.4, -14.6], [26, -16.4], [28.4, -14]], w);
  seam(ctx, [[21.4, -7.2], [23, -9], [24.6, -6.8], [26.2, -8.6], [28, -6.6]], w);
  line(ctx, mix(pal.plate, OUT, 0.5), 0.5, [
    [21.4, 0],
    [20.8, -14],
    [21.6, -29],
  ]);
  ctx.restore();
}

/** 背面：殼的內面（暗）、殼緣一圈殼板色、兩條皮帶；殼縫從裡面透出來（細、淡一點）。和雲紋碑盾背面同一段（y −10～17）。 */
export function shellBackPal(ctx: Ctx, pal: ShellPal): void {
  const oy = 8;
  ctx.save();
  fill(ctx, pal.plate, () => shellPath(ctx, 1, 0, oy));
  fill(ctx, pal.inner, () => shellPath(ctx, 1, 0, oy, 1.2));
  ctx.save();
  ctx.beginPath();
  shellPath(ctx, 1, 0, oy, 1.2);
  ctx.clip();
  fill(ctx, dk(pal.inner, 0.25), () => ctx.rect(4.4, -12, 6, 32));
  ctx.restore();
  for (let v = 0; v < 3; v++) crack(v, 1.1, ID, (y) => y + oy, 0.8).forEach((pts) => seam(ctx, pts, 0.7, 0.75));
  for (const y of [-1.4, 9.6]) fill(ctx, SHELL_FIX.strap, () => ctx.rect(-7.6, y, 15.2, 1.5));
  ctx.restore();
}

export const shellFront = (ctx: Ctx, it: QItem): void => shellFrontPal(ctx, shellPal(it));
export const shellSide = (ctx: Ctx, it: QItem): void => shellSidePal(ctx, shellPal(it));
export const shellBack = (ctx: Ctx, it: QItem): void => shellBackPal(ctx, shellPal(it));
