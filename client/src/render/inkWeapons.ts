// C 手繪墨線畫風的其餘武器（Phase C-2b）：巨劍、錘、矛、弩、火槍、霰彈槍、手槍、拳套、鐮刀、鞭，
// 以及魔導劍（sword／arcane）、權杖與圖騰杖（staff／scepter、totem）。成對武器（dual_dagger、dual_pistol）由 dollGear 拆成兩把單手武器。
// 輪廓沿用現行造型（paperdoll.ts／paperdollGear.ts，放大約 1.3 倍到 C 骨架），改用 `ink()`／`stroke()` 畫，顏色照 `itemColors()`。
// 座標：以手心為原點、往上為 -y；槍弩朝 +x（前方／外側）。握法：正面、背面略往外斜，側面往前傾（同 inkGear.ts 的握點規則）。
// 不認得的形制 → 該 kind 的預設形制；不是這一層的 kind 回傳 false。
import type { Ctx } from "./artDraw";
import { elementTint, type GearItem } from "./appearance";
import { darken } from "./color";
import { drawInkWeapon, metalOf, type ColorFn, type HeldOpt } from "./inkGear";
import { dot, ellPts, ink, MAT, stroke, type Pt } from "./inkStyle";

const GOLD = MAT.gold;
const WOOD = MAT.wood;
const WOOD_DARK = "#6a4420";
const STOCK = "#7a5232";
const GRIP = "#3a2a1c";
/** 魔導劍預設劍身色（冷灰，比一般鋼劍暗一點，讓光槽更明顯）。 */
const ARCANE_BLADE = "#8a93a8";
/** 魔導劍的源晶槽預設光色（沒有元素時）；有元素換元素色。 */
export const ARCANE_GLOW = "#9a86ff";
/** 魔導劍的源晶槽顏色：有元素換元素色，否則藍紫（供測試與圖示共用）。 */
export const arcaneGlow = (element: string | undefined): string => elementTint(element) ?? ARCANE_GLOW;
const BRASS = "#b08a4a";

interface Cols {
  metal: string;
  dark: string;
  wood: string;
  grip: string;
  gold: string;
}

type Shape = (ctx: Ctx, it: GearItem, k: string, c: Cols) => void;

const rect = (x0: number, y0: number, x1: number, y1: number): Pt[] => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

/** 木柄：y0（下端）到 y1（上端，較小）。 */
function haft(ctx: Ctx, k: string, y0: number, y1: number, c: string, w = 0.9): void {
  ink(ctx, `${k}-haft`, rect(-w, y1, w, y0), c, { shade: false, w: 0.6 });
}

// ============================== 近戰 ==============================
function drawGreatsword(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const L = 28;
  const zhanma = it.form === "zhanma";
  const pts: Pt[] = zhanma
    ? [[-2.4, -3.6], [-2.4, -L + 2], [2.8, -L], [2.8, -3.6]]
    : [[-2.4, -3.6], [-2.2, -L + 3], [0, -L], [2.2, -L + 3], [2.4, -3.6]];
  ink(ctx, `${k}-blade`, pts, c.metal, { shade: false, w: 0.8 });
  stroke(ctx, `${k}-fuller`, [[0, -7], [0, -L + 5]], 0.4, c.dark);
  if (it.form === "serrated") {
    const teeth: Pt[] = [];
    for (let i = 0; i < 6; i += 1) teeth.push([2.3, -8 - i * 3.2], [4.2, -9.4 - i * 3.2]);
    stroke(ctx, `${k}-teeth`, teeth, 0.5, c.metal);
  }
  ink(ctx, `${k}-guard`, rect(-5.4, -4.8, 5.4, -3.2), c.gold, { shade: false, w: 0.6 });
  ink(ctx, `${k}-grip`, rect(-1, -3.2, 1, 5), c.grip, { shade: false, w: 0.5 });
  ink(ctx, `${k}-pommel`, ellPts(0, 6, 1.6, 1.6, 8), c.gold, { shade: false, w: 0.5 });
}

function drawHammer(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  if (it.form === "mace") {
    haft(ctx, k, 4, -22, c.wood);
    ink(ctx, `${k}-ball`, ellPts(0, -25, 5, 5, 12), c.metal, { w: 0.8 });
    stroke(ctx, `${k}-flange`, [[-5, -25], [5, -25]], 0.5, c.dark);
    return;
  }
  if (it.form === "flail") {
    haft(ctx, k, 4, -18, c.wood);
    stroke(ctx, `${k}-chain`, [[0, -18], [3.8, -22], [3.2, -26]], 0.9, c.dark);
    ink(ctx, `${k}-ball`, ellPts(3, -30, 4.4, 4.4, 12), c.metal, { w: 0.8 });
    return;
  }
  haft(ctx, k, 4, -27, c.wood, 1);
  ink(ctx, `${k}-head`, rect(-7.6, -35, 7.6, -26), c.metal, { w: 0.9 });
  stroke(ctx, `${k}-band`, [[-7.6, -30.5], [7.6, -30.5]], 0.5, c.dark);
}

function drawSpear(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  haft(ctx, k, 8, -36, c.wood, 1);
  if (it.form === "trident") {
    for (const sx of [-3.6, 0, 3.6]) ink(ctx, `${k}-prong${sx}`, [[sx, sx === 0 ? -52 : -49], [sx + 1.4, -38], [sx - 1.4, -38]], c.metal, { shade: false, w: 0.6 });
    ink(ctx, `${k}-cross`, rect(-4.4, -39, 4.4, -37.2), c.metal, { shade: false, w: 0.6 });
    return;
  }
  ink(ctx, `${k}-head`, [[0, -50], [3.6, -43], [0, -36], [-3.6, -43]], c.metal, { w: 0.8 });
  if (it.form === "halberd") ink(ctx, `${k}-axe`, [[1.4, -45], [8.6, -46.4], [8.4, -38.4], [1.4, -39.6]], c.metal, { w: 0.8 });
}

function drawFist(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  ink(ctx, `${k}-block`, rect(-3.4, -4, 3.4, 3), c.metal, { w: 0.8 });
  if (it.form === "knuckle") {
    for (const x of [-2.2, 0, 2.2]) ink(ctx, `${k}-stud${x}`, ellPts(x, -4.6, 1.1, 1.1, 8), c.dark, { shade: false, w: 0.4 });
    return;
  }
  const blades = it.form === "claw" ? [-2.2, 0, 2.2] : [0];
  for (const x of blades) ink(ctx, `${k}-blade${x}`, [[x - 1.3, -4], [x, it.form === "claw" ? -11 : -13], [x + 1.3, -4]], c.metal, { shade: false, w: 0.6 });
}

function drawScythe(ctx: Ctx, _it: GearItem, k: string, c: Cols): void {
  haft(ctx, k, 8, -34, c.wood);
  ink(ctx, `${k}-blade`, [[0, -35], [7, -38], [15, -33], [18.4, -22], [11, -28], [0, -29]], c.metal, { w: 0.8 });
}

function drawWhip(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  ink(ctx, `${k}-handle`, rect(-1.1, -5, 1.1, 5), c.grip, { shade: false, w: 0.5 });
  const lash: Pt[] = [[0, -5], [6, -9], [9, -5], [8, 1], [11, 6], [16, 9]];
  const chain = it.form === "chain";
  stroke(ctx, `${k}-lash`, lash, chain ? 1.3 : 1, chain ? c.dark : c.wood);
  if (chain) for (let i = 1; i < lash.length; i += 1) dot(ctx, lash[i]![0], lash[i]![1], 0.9, 0.9, c.metal);
  if (it.form === "bladed") ink(ctx, `${k}-tip`, [[15, 7], [20, 9.6], [15, 11.4]], c.metal, { shade: false, w: 0.5 });
}

// ============================== 魔導劍、杖 ==============================
function drawArcaneSword(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const L = 21;
  const glow = arcaneGlow(it.element);
  ink(ctx, `${k}-blade`, [[-1.5, -2], [-1.3, -L + 1.8], [0, -L], [1.3, -L + 1.8], [1.5, -2]], c.metal, { shade: false, w: 0.7 });
  ink(ctx, `${k}-groove`, rect(-0.6, -L + 2.4, 0.6, -5), glow, { shade: false, line: false, w: 0.4 });
  for (const y of [-6.5, -10.5, -14.5]) dot(ctx, 0, y, 1, 0.45, "#e8e2ff");
  ink(ctx, `${k}-gear`, ellPts(0, -3.2, 4.6, 2.5, 12), BRASS, { shade: false, w: 0.6 });
  ink(ctx, `${k}-crystal`, ellPts(0, -3.2, 1.4, 1.4, 8), glow, { shade: false, w: 0.4 });
  ink(ctx, `${k}-grip`, rect(-0.9, -1.6, 0.9, 4.6), c.grip, { shade: false, w: 0.5 });
}

function drawScepter(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const gem = elementTint(it.element) ?? c.metal;
  ink(ctx, `${k}-shaft`, rect(-1.3, -30, 1.3, 8), WOOD_DARK, { shade: false, w: 0.6 });
  const ring = ellPts(0, -34, 6, 6, 16);
  stroke(ctx, `${k}-ring`, [...ring, ring[0]!], 1.5, c.gold);
  ink(ctx, `${k}-gem`, ellPts(0, -34, 3, 3, 10), gem, { shade: false, w: 0.6 });
  dot(ctx, -1, -35, 0.8, 0.8, "#ffffff");
}

function drawTotem(ctx: Ctx, _it: GearItem, k: string): void {
  ink(ctx, `${k}-pole`, rect(-1.9, -42, 1.9, 8), "#8f5f2c", { shade: false, w: 0.6 });
  for (const [y, col] of [[-39, "#b83a3a"], [-27, "#3a8a8a"]] as const) {
    ink(ctx, `${k}-face${y}`, rect(-5.2, y, 5.2, y + 9), "#b77f3f", { w: 0.7 });
    stroke(ctx, `${k}-brow${y}`, [[-3.4, y + 2], [3.4, y + 2]], 1.2, col);
    stroke(ctx, `${k}-mouth${y}`, [[-2.4, y + 6], [2.4, y + 6]], 0.9, "#1d1a22");
  }
  for (const s of [-1, 1]) {
    ink(ctx, `${k}-feather${s}`, [[s * 5, -37], [s * 10.5, -43], [s * 11, -33], [s * 5, -31]], "#e6e6e0", { w: 0.6 });
  }
  ink(ctx, `${k}-orb`, ellPts(0, -46, 3.4, 3.4, 10), "#7dffb0", { shade: false, w: 0.6 });
  dot(ctx, -1, -47, 0.9, 0.9, "#ffffff");
}

// ============================== 火器、弩（朝 +x） ==============================
function drawPistol(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const L = it.form === "derringer" ? 6.5 : it.form === "revolver" ? 10.5 : 9;
  ink(ctx, `${k}-grip`, [[-1.8, -1.4], [1.8, -1.4], [1.2, 5.8], [-2, 5.8]], it.form === "flintlock" ? STOCK : GRIP, { shade: false, w: 0.6 });
  ink(ctx, `${k}-barrel`, rect(-1.4, -4.4, L, -1.2), c.metal, { w: 0.7 });
  if (it.form === "derringer") ink(ctx, `${k}-barrel2`, rect(-1.4, -1.2, L, 1.2), c.dark, { shade: false, w: 0.6 });
  if (it.form === "revolver") ink(ctx, `${k}-cyl`, ellPts(1.6, -2.8, 3, 3.2, 10), c.dark, { shade: false, w: 0.6 });
  if (it.form === "flintlock") ink(ctx, `${k}-cock`, [[-0.6, -4.4], [-2.4, -8], [0.4, -8.4], [1.8, -4.4]], c.dark, { shade: false, w: 0.5 });
}

function drawShotgun(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const L = it.form === "blunderbuss" ? 15 : 20;
  ink(ctx, `${k}-stock`, [[-9, -5], [0, -4.6], [0, 0], [-6.4, 1.8], [-9, -1]], STOCK, { shade: false, w: 0.7 });
  ink(ctx, `${k}-grip`, [[-1.6, -1], [1.2, -1], [0.8, 4.6], [-1.8, 4.6]], GRIP, { shade: false, w: 0.5 });
  ink(ctx, `${k}-barrel`, rect(0, -5.2, L, -1.2), c.metal, { w: 0.8 });
  if (it.form === "double") ink(ctx, `${k}-barrel2`, rect(0, -1.2, L, 1.8), c.dark, { shade: false, w: 0.6 });
  if (it.form === "pump") ink(ctx, `${k}-slide`, rect(6, -1.2, 13, 1.6), STOCK, { shade: false, w: 0.6 });
  if (it.form === "blunderbuss") ink(ctx, `${k}-flare`, [[L - 6, -5.2], [L + 2.4, -9], [L + 2.4, 3], [L - 6, -0.8]], c.metal, { w: 0.8 });
}

function drawLongGun(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const sniper = it.form === "sniper";
  const L = sniper ? 25 : it.form === "hunting" ? 24 : 22;
  ink(ctx, `${k}-stock`, [[-10.5, -5], [0, -4.6], [0, 0], [-7.4, 2], [-10.5, -1]], sniper ? c.dark : STOCK, { shade: false, w: 0.7 });
  ink(ctx, `${k}-grip`, [[-1.6, -1], [1.2, -1], [0.8, 4.6], [-1.8, 4.6]], GRIP, { shade: false, w: 0.5 });
  ink(ctx, `${k}-barrel`, rect(0, -4.6, L, -1.4), c.metal, { w: 0.8 });
  if (it.form === "hunting") ink(ctx, `${k}-fore`, rect(L * 0.3, -1.4, L, 1), STOCK, { shade: false, w: 0.6 });
  if (it.form === "flintlock") {
    ink(ctx, `${k}-cock`, [[-0.4, -4.6], [-2.6, -8.4], [0.4, -9], [2, -4.6]], c.dark, { shade: false, w: 0.5 });
    ink(ctx, `${k}-band`, rect(L * 0.45, -4.8, L * 0.45 + 1.8, -1.2), c.gold, { shade: false, w: 0.4 });
  }
  if (sniper) {
    ink(ctx, `${k}-scope`, rect(5, -9, 16, -5.4), "#2a2d33", { w: 0.7 });
    dot(ctx, 16, -7.2, 0.9, 1.4, "#8fe3ff");
    stroke(ctx, `${k}-bipod`, [[20, -1.4], [18.4, 4.6]], 0.7);
    stroke(ctx, `${k}-bipod2`, [[20, -1.4], [22.4, 4.6]], 0.7);
  }
}

function drawCrossbow(ctx: Ctx, it: GearItem, k: string, c: Cols): void {
  const heavy = it.form === "heavy";
  const span = heavy ? 11.6 : 9.6;
  const tip = heavy ? 15 : 14;
  ink(ctx, `${k}-stock`, rect(-3.4, -4.4, tip + 1, -1.4), STOCK, { shade: false, w: 0.7 });
  ink(ctx, `${k}-grip`, [[-1.4, -1.4], [1.4, -1.4], [1, 4.4], [-1.6, 4.4]], GRIP, { shade: false, w: 0.5 });
  if (it.form === "repeater") ink(ctx, `${k}-mag`, rect(1.6, -9.4, 9.6, -4.4), GRIP, { w: 0.7 });
  stroke(ctx, `${k}-string`, [[tip, -2.9 - span], [tip - 8, -2.9], [tip, -2.9 + span]], 0.4, "#e8e0d0");
  stroke(ctx, `${k}-arm`, [[tip - 1, -2.9 - span], [tip + 3, -2.9], [tip - 1, -2.9 + span]], heavy ? 1.8 : 1.3, c.metal);
  ink(ctx, `${k}-bolt`, rect(tip - 12, -5.2, tip + 1, -4.4), c.wood, { shade: false, w: 0.4 });
  ink(ctx, `${k}-bolt-tip`, [[tip + 1, -5.7], [tip + 3.6, -4.8], [tip + 1, -3.9]], c.metal, { shade: false, w: 0.4 });
  if (heavy) {
    const r = ellPts(tip + 3, -2.9, 2.4, 3.2, 10);
    stroke(ctx, `${k}-stirrup`, [...r, r[0]!], 0.8, GRIP);
  }
}

const SHAPES: Readonly<Record<string, Shape>> = {
  greatsword: drawGreatsword,
  hammer: drawHammer,
  spear: drawSpear,
  fist: drawFist,
  scythe: drawScythe,
  whip: drawWhip,
  pistol: drawPistol,
  shotgun: drawShotgun,
  longgun: drawLongGun,
  crossbow: drawCrossbow,
};

/** 槍弩：朝 +x，正面略往外上抬、側面幾乎水平。 */
const GUNS: readonly string[] = ["pistol", "shotgun", "longgun", "crossbow"];
/** [正面／背面往外斜, 側面往前傾]（弧度）；槍弩是朝上抬的角度。 */
const LEAN: Readonly<Record<string, readonly [number, number]>> = {
  greatsword: [0.18, 0.8],
  hammer: [0.2, 0.5],
  spear: [0.12, 0.4],
  scythe: [0.12, 0.3],
  fist: [0.1, 1.2],
  whip: [0, 0],
  pistol: [0.35, 0.05],
  shotgun: [0.35, 0.05],
  longgun: [0.35, 0.05],
  crossbow: [0.35, 0.05],
};

/** 這一層畫得出來的手持物：魔導劍、權杖、圖騰杖，以及上面那些武器 kind。 */
export function isInkWeaponMore(it: GearItem): boolean {
  if (it.kind === "sword") return it.form === "arcane";
  if (it.kind === "staff") return it.form === "scepter" || it.form === "totem";
  return SHAPES[it.kind] !== undefined;
}

function shapeOf(it: GearItem): Shape {
  if (it.kind === "sword") return drawArcaneSword;
  if (it.kind === "staff") return it.form === "totem" ? drawTotem : drawScepter;
  return SHAPES[it.kind]!;
}

function leanOf(it: GearItem, o: HeldOpt): number {
  if (it.kind === "sword") return o.side ? 0.75 : 0;
  if (it.kind === "staff") return o.side ? (it.form === "totem" ? 0.4 : 0.4) : 0;
  const [front, side] = LEAN[it.kind] ?? [0, 0];
  const gun = GUNS.includes(it.kind);
  if (!o.side) return gun ? -front : front;
  return gun ? -side + (o.far ? 0.2 : 0) : side;
}

/**
 * 畫其餘武器。(x, y) ＝ 手的位置；`key` ＝ 抖動種子前綴。外側（正面主手＝畫面左、副手鏡像＝畫面右、背面相反）與側面前方都是 +x。
 * 回傳 false ＝ 不是這一層的武器。
 */
export function drawInkWeaponMore(ctx: Ctx, it: GearItem, key: string, x: number, y: number, o: HeldOpt, colors: ColorFn): boolean {
  if (!isInkWeaponMore(it)) return false;
  const shade = o.far ? 0.25 : 0;
  const metal = it.kind === "sword" && it.color === undefined ? ARCANE_BLADE : metalOf(it, colors);
  const c: Cols = {
    metal: darken(metal, shade),
    dark: darken(colors(it)[1], shade),
    wood: darken(WOOD, shade),
    grip: darken(GRIP, shade),
    gold: darken(GOLD, shade),
  };
  ctx.save();
  ctx.translate(x, y);
  // 外側朝 +x：正面主手（mirror ＝ false）在畫面左，外側是 -x
  if (!o.side && !o.mirror) ctx.scale(-1, 1);
  if (o.side && it.kind === "staff" && it.form === "totem") ctx.translate(2, 0);
  ctx.rotate(leanOf(it, o));
  shapeOf(it)(ctx, it, key, c);
  ctx.restore();
  return true;
}

/**
 * 單獨畫一件主手武器（小圖示用）：原點在手的位置，不是側面；和小人手持的同一套 C 畫法。
 * 以「副手鏡像」的方向畫，外側朝 +x 的武器（斧、槍弩、魔導劍…）槍口與刃朝右。畫不出來的 kind 回傳 false。
 */
export function drawInkWeaponAlone(ctx: Ctx, it: GearItem, colors: ColorFn): boolean {
  const o: HeldOpt = { mirror: true, side: false, far: false, back: true }; // back：匕首不往外斜（圖示本來就斜放）
  return drawInkWeapon(ctx, it, "icon", 0, 0, o, colors) || drawInkWeaponMore(ctx, it, "icon", 0, 0, o, colors);
}
