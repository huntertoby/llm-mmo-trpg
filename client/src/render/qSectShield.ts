// 持盾弟子的雲紋碑盾（RG-4；`kite_shield` 的敵人專用形制 `sect_great`，docs/art/RG樣張.md 9.1、9.6、9.8）。
// 畫法照樣張 docs/art/sample/rgUnits.js 第 1 節的 A（SHIELDS.A：上緣圓拱＋三峰山紋）原樣移植；B 太極方盾未採用、不做。
// 座標都在盾錨點裡（和塔盾同一個錨點）：正面＝pdHeld2 的 translate(手 x, −9.5)、側面＝shieldSide 的 translate(8.6, −13.5)、
// 背面＝shieldBack 的 translate(手 x − 1, 手 y − 5)。握法、手臂、圖層、朝西換手照塔盾（isTowerLike）。
// 顏色：盾面＝item.color、盾邊＝item.trim（缺時用樣張的青 #5f8f8a／月白 #dfe4e2）；紋樣只認 emblem "peak"（不認得就不畫），
// 紋樣本身的顏色照樣張固定（月白圓章、青山、朱紅峰頂）。
import type { Ctx } from "./artDraw";
import { mix, TAU, type QItem } from "./qCore";

/** 雲嶺色票（樣張 rgUnits.js 的 C）。 */
const C = { qing: "#5f8f8a", moon: "#dfe4e2", red: "#c0392b", wood: "#7a5232", strap: "#3a2414", gold: "#e8bb48" } as const;
/** 正面半寬、上緣、下緣、圓拱高（模型單位）。 */
const FW = 8.5;
const FTOP = -13.5;
const FBOT = 9;
const ARCH = 4;
/** 側面（3/4 視角）盾面橫向壓扁。 */
const SIDE_SX = 0.42;

const dk = (c: string, t = 0.25): string => mix(c, "#000000", t);

function fill(ctx: Ctx, c: string, path: () => void): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  path();
  ctx.fill();
}
function line(ctx: Ctx, c: string, w: number, pts: ReadonlyArray<readonly [number, number]>): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.stroke();
}

/** 碑形外形（上緣半橢圓拱、直邊、下緣小圓角）；i＝往內縮（畫邊框用）。樣張 outlinePath 的 arch 分支。 */
function archPath(ctx: Ctx, x0: number, x1: number, top: number, bot: number, i = 0): void {
  const L = x0 + i;
  const R = x1 - i;
  const T = top + i;
  const B = bot - i;
  const a = ARCH - i * 0.4;
  const cx = (L + R) / 2;
  const rx = (R - L) / 2;
  ctx.moveTo(L, B - 1.2);
  ctx.lineTo(L, T);
  ctx.ellipse(cx, T, rx, a, 0, Math.PI, 0);
  ctx.lineTo(R, B - 1.2);
  ctx.quadraticCurveTo(R, B, R - 1.2, B);
  ctx.lineTo(L + 1.2, B);
  ctx.quadraticCurveTo(L, B, L, B - 1.2);
  ctx.closePath();
}

/** 盾心紋樣（cx, cy 圓心、r 半徑、sx 橫向壓扁）：只認 `peak`（月白圓章裡青色三峰、山腰一道雲、峰頂朱紅一點）。 */
function emblem(ctx: Ctx, kind: string | undefined, cx: number, cy: number, r: number, sx = 1): void {
  if (kind !== "peak") return;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(sx, 1);
  fill(ctx, C.moon, () => ctx.arc(0, 0, r, 0, TAU));
  fill(ctx, dk(C.qing, 0.15), () => {
    ctx.moveTo(-r * 0.78, r * 0.42);
    ctx.lineTo(-r * 0.38, -r * 0.16);
    ctx.lineTo(-r * 0.12, r * 0.08);
    ctx.lineTo(r * 0.22, -r * 0.62);
    ctx.lineTo(r * 0.78, r * 0.42);
    ctx.closePath();
  });
  line(ctx, C.moon, r * 0.2, [
    [-r * 0.62, r * 0.18],
    [-r * 0.12, r * 0.3],
    [r * 0.36, r * 0.1],
  ]);
  fill(ctx, C.red, () => ctx.arc(r * 0.22, -r * 0.62, r * 0.17, 0, TAU));
  ctx.restore();
}

const faceOf = (it: QItem): string => it.color ?? C.qing;
const rimOf = (it: QItem): string => it.trim ?? C.moon;

/** 正面：盾面朝外（樣張 front）。 */
export function sectShieldFront(ctx: Ctx, it: QItem): void {
  const face = faceOf(it);
  const rim = rimOf(it);
  const L = -FW;
  const R = FW;
  const rimW = 1.3;
  ctx.save();
  fill(ctx, rim, () => archPath(ctx, L, R, FTOP, FBOT));
  fill(ctx, face, () => archPath(ctx, L, R, FTOP, FBOT, rimW));
  ctx.save();
  ctx.beginPath();
  archPath(ctx, L, R, FTOP, FBOT, rimW);
  ctx.clip();
  fill(ctx, dk(face, 0.16), () => ctx.rect(R - 4.2, FTOP - ARCH, 6, FBOT - FTOP + ARCH + 2)); // 右側暗面
  fill(ctx, dk(face, 0.16), () => ctx.rect(L, FBOT - 3.4, R - L, 4)); // 下緣暗面
  fill(ctx, "rgba(255,255,255,0.45)", () => ctx.roundRect(L + rimW + 0.9, FTOP + 0.2, 1.3, 9.5, 0.65)); // 左上亮面
  ctx.restore();
  for (const y of [FTOP + 3.2, FBOT - 5.2]) fill(ctx, dk(rim, 0.1), () => ctx.rect(L + rimW, y, R - L - rimW * 2, 0.9)); // 兩道盾骨
  emblem(ctx, it.emblem, 0, -3.2, 4.4);
  const nails: ReadonlyArray<readonly [number, number]> = [
    [L + 2.4, FTOP + 0.6],
    [R - 2.4, FTOP + 0.6],
    [L + 2.4, FBOT - 2.2],
    [R - 2.4, FBOT - 2.2],
  ];
  for (const [x, y] of nails) fill(ctx, C.gold, () => ctx.arc(x, y, 0.75, 0, TAU)); // 四顆銅釘
  ctx.restore();
}

/** 側面：轉 3/4，盾邊厚度在靠身體那一側（樣張 side；朝東座標，朝西由 stamp 鏡像）。 */
export function sectShieldSide(ctx: Ctx, it: QItem): void {
  const face = faceOf(it);
  const rim = rimOf(it);
  const top = -10;
  const bot = 13.3;
  ctx.save();
  fill(ctx, dk(rim, 0.3), () => archPath(ctx, -2.2, 0.6, top + 0.6, bot)); // 盾邊厚度
  ctx.save();
  ctx.translate(2.3, 0);
  ctx.scale(SIDE_SX, 1);
  const L = -FW + 1.5;
  const R = FW - 1.5;
  fill(ctx, rim, () => archPath(ctx, L, R, top, bot));
  fill(ctx, face, () => archPath(ctx, L, R, top, bot, 1.9));
  ctx.save();
  ctx.beginPath();
  archPath(ctx, L, R, top, bot, 1.9);
  ctx.clip();
  fill(ctx, dk(face, 0.16), () => ctx.rect(L, bot - 3.4, R - L, 4));
  ctx.restore();
  for (const y of [top + 3.2, bot - 5.2]) fill(ctx, dk(rim, 0.1), () => ctx.rect(L + 1.9, y, R - L - 3.8, 0.9));
  ctx.restore();
  emblem(ctx, it.emblem, 2.6, 0.2, 3.9, SIDE_SX * 1.1);
  fill(ctx, "rgba(255,255,255,0.45)", () => ctx.roundRect(0.1, top + 0.8, 0.9, 8, 0.45));
  ctx.restore();
}

/** 背面：木板盾背＋兩道板縫＋兩條皮帶，邊＝盾邊色暗 25%（樣張 back）。 */
export function sectShieldBack(ctx: Ctx, it: QItem): void {
  const rim = rimOf(it);
  const L = -FW;
  const R = FW;
  const top = -7.5;
  const bot = 17;
  ctx.save();
  fill(ctx, dk(rim, 0.25), () => archPath(ctx, L, R, top, bot));
  fill(ctx, C.wood, () => archPath(ctx, L, R, top, bot, 1.3));
  ctx.save();
  ctx.beginPath();
  archPath(ctx, L, R, top, bot, 1.3);
  ctx.clip();
  for (const x of [-2.8, 2.8]) fill(ctx, dk(C.wood, 0.22), () => ctx.rect(x - 0.3, top - ARCH, 0.6, bot - top + ARCH)); // 木板縫
  fill(ctx, dk(C.wood, 0.18), () => ctx.rect(R - 3.6, top - ARCH, 5, bot - top + ARCH));
  ctx.restore();
  for (const y of [top + 4.2, bot - 6]) fill(ctx, C.strap, () => ctx.rect(L + 1.3, y, R - L - 2.6, 1.5)); // 兩條橫皮帶
  ctx.restore();
}
