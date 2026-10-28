// C 手繪墨線畫風的副手（Phase C-2a）：鳶盾／塔盾 shield_kite、書 tome、法球 orb。
// 正面：以手心 (x, y) 為原點；側面書、法球畫在身體後面、拿在遠側手，往前移到身體輪廓外（x 約 7～10）並暗 25%；
// 背面可被身體遮住大半。不認得的形制 → 預設（鳶盾／典籍／水晶球）。
import { TAU, type Ctx } from "./artDraw";
import { elementTint, type GearItem } from "./appearance";
import { darken, type ColorFn } from "./inkGear";
import { ellPts, ink, stroke, type Pt } from "./inkStyle";

const GOLD = "#e8bb48";
const PAGE = "#f2ead6";
const WOOD = "#a06a36";

export const isKiteShield = (it: GearItem): boolean => it.kind === "shield_kite";
export const isInkOffhandHeld = (it: GearItem): boolean => it.kind === "tome" || it.kind === "orb" || it.kind === "shield_kite";

const bodyColor = (it: GearItem, colors: ColorFn): string => it.color ?? colors(it)[0];

// ---- 盾 ----
const KITE: Pt[] = [[-6, -6.4], [6, -6.4], [5.8, 2], [0, 12], [-5.8, 2]];
const TOWER: Pt[] = [[-6, -9.4], [6, -9.4], [6.4, 11], [-6.4, 11]];

function drawKiteFront(ctx: Ctx, it: GearItem, colors: ColorFn): void {
  const c = bodyColor(it, colors);
  const tower = it.form === "tower";
  ink(ctx, "kite", tower ? TOWER : KITE, c, { w: 1 });
  if (tower) {
    stroke(ctx, "kite-ridge", [[0, -8.6], [0, 10.4]], 0.7, "#e8e0c8");
    stroke(ctx, "kite-rim", [[-4.8, -8], [4.8, -8], [5.2, 9.6], [-5.2, 9.6], [-4.8, -8]], 0.4);
    for (const y of [-6, 8]) ink(ctx, `kite-rivet-${y}`, ellPts(0, y, 0.9, 0.9, 8), GOLD, { shade: false, w: 0.4 });
  } else {
    stroke(ctx, "kite-ridge", [[0, -5.6], [0, 9.4]], 0.6, "#e8e0c8");
    stroke(ctx, "kite-rim", [[-4.6, -4.8], [4.6, -4.8], [4.4, 1.8], [0, 9.6], [-4.4, 1.8], [-4.6, -4.8]], 0.4);
    ink(ctx, "kite-boss", ellPts(0, -0.6, 1.7, 1.7, 10), it.trim ?? GOLD, { shade: false, w: 0.6 });
  }
}

/** 側面鳶盾／塔盾：一條邊（畫在身體前面、頭之前）。回傳 false ＝ 不是這一層的盾。 */
export function drawInkKiteSide(ctx: Ctx, it: GearItem, colors: ColorFn): boolean {
  if (!isKiteShield(it)) return false;
  const c = bodyColor(it, colors);
  if (it.form === "tower") {
    ink(ctx, "kite-s", [[7, -33], [10.6, -33], [10.8, -10], [6.8, -10]], c, { w: 0.8 });
    stroke(ctx, "kite-s-ridge", [[10, -32], [10, -11]], 0.6, "#e8e0c8");
  } else {
    ink(ctx, "kite-s", [[7.2, -29], [10.6, -29], [10.2, -17], [8.8, -9.6], [7.6, -17]], c, { w: 0.8 });
    stroke(ctx, "kite-s-ridge", [[9.8, -28], [9.4, -16]], 0.5, "#e8e0c8");
  }
  return true;
}

/** 背面鳶盾／塔盾：木色＋皮帶（座標在鏡像後的背面座標）。 */
export function drawInkKiteBack(ctx: Ctx, it: GearItem): void {
  const tower = it.form === "tower";
  ctx.save();
  ctx.translate(8.6, -21);
  ink(ctx, "kite-b", tower ? TOWER : KITE, WOOD, { w: 1 });
  stroke(ctx, "kite-strap", tower ? [[-3.6, -3], [3.6, 3]] : [[-3.6, -3.4], [3.6, 2]], 1.2, "#5a3a1e");
  ctx.restore();
}

// ---- 書 ----
function drawTome(ctx: Ctx, it: GearItem, colors: ColorFn, side: boolean, shade: number): void {
  const [c0, d0] = colors(it);
  const c = darken(c0, shade);
  const d = darken(d0, shade);
  const trim = darken(it.trim ?? GOLD, shade);
  if (it.form === "scroll") {
    const [x0, x1] = side ? [1.4, 5] : [-2.6, 2.6];
    ink(ctx, "scroll", [[x0, -8.4], [x1, -8.4], [x1, 5], [x0, 5]], darken(PAGE, shade), { w: 0.8 });
    for (const y of [-7.4, 4.2]) ink(ctx, `scroll-cap${y}`, [[x0 - 0.6, y - 1], [x1 + 0.6, y - 1], [x1 + 0.6, y + 1], [x0 - 0.6, y + 1]], c, { shade: false, w: 0.6 });
    return;
  }
  if (side) {
    // 側看＝一條厚書脊，前緣露出頁邊
    ink(ctx, "tome-s", [[1, -6.4], [4.8, -6.4], [4.8, 4.6], [1, 4.6]], c, { w: 0.8 });
    ink(ctx, "tome-s-pages", [[4.8, -5.8], [5.8, -5.8], [5.8, 4], [4.8, 4]], darken(PAGE, shade), { shade: false, w: 0.5 });
    stroke(ctx, "tome-s-band", [[1, -1.4], [4.8, -1.4]], 1, trim);
    return;
  }
  ink(ctx, "tome", [[-4.8, -6.4], [4.8, -6.4], [4.8, 3], [-4.8, 3]], c, { w: 0.9 });
  ink(ctx, "tome-spine", [[-4.8, -6.4], [-3.4, -6.4], [-3.4, 3], [-4.8, 3]], d, { shade: false, w: 0.5 });
  stroke(ctx, "tome-pages", [[-2.6, -5.2], [3.6, -5.2]], 0.7, darken(PAGE, shade));
  ink(ctx, "tome-clasp", ellPts(0.4, -1.4, 1.5, 1.5, 8), trim, { shade: false, w: 0.5 });
}

// ---- 法球 ----
function drawOrb(ctx: Ctx, it: GearItem, colors: ColorFn, side: boolean, shade: number): void {
  const glow = elementTint(it.element) ?? colors(it)[0];
  const orb = darken(glow, shade);
  const floating = it.form === "floating";
  const cx = side ? 3.4 : 0;
  const cy = floating ? -9.4 : -5.6;
  if (floating) stroke(ctx, "orb-ring", [...ellPts(cx, cy + 7, 3.8, 1.2, 10), [cx + 3.8, cy + 7] as Pt], 0.4, "rgba(255,255,255,0.7)");
  ctx.save();
  ctx.fillStyle = orb;
  for (const [r, a] of [[6.4, 0.14], [5.2, 0.2], [4.4, 0.28]] as const) {
    ctx.globalAlpha = a;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
  ink(ctx, "orb", ellPts(cx, cy, 3.4, 3.4, 12), orb, { w: 0.8 });
  ink(ctx, "orb-hi", ellPts(cx - 1.1, cy - 1.2, 0.9, 0.9, 6), "#ffffff", { shade: false, line: false, w: 0.3 });
}

/**
 * 畫副手手持物。(x, y) ＝ 手心。正面（`side` ＝ false）：鳶盾、書立在身側、法球托在掌上；
 * 側面（遠側手，身體之後）：往前移出身體輪廓外並暗 25%。不是這一層的 kind 回傳 false。
 */
export function drawInkOffhand(ctx: Ctx, it: GearItem, x: number, y: number, side: boolean, colors: ColorFn): boolean {
  if (!isInkOffhandHeld(it)) return false;
  ctx.save();
  ctx.translate(x, y);
  const shade = side ? 0.25 : 0;
  if (it.kind === "tome") drawTome(ctx, it, colors, side, shade);
  else if (it.kind === "orb") drawOrb(ctx, it, colors, side, shade);
  else if (!side) drawKiteFront(ctx, it, colors);
  ctx.restore();
  return true;
}
