// C 手繪墨線畫風的頭部裝備、手持物（Phase C-1b；移植自 docs/art/sample/storyDoll.js 的 headgear／weapon／offhand，需求第 3、4 節）。
// 這一層只畫樣張畫過的：頭 helmet／hood／wizard_hat、武器 sword／dagger／axe／staff／bow、圓盾 shield_round；
// 其他 kind（以及魔導劍、權杖、圖騰杖）回傳 false，由 inkDoll.ts 退回現行畫法（C-2 換）。不認得的值一律退回預設，不出錯。
import { TAU, type Ctx } from "./artDraw";
import { elementTint, type GearItem } from "./appearance";
import { ellPts, ink, stroke, type Pt } from "./inkStyle";

export type GearView = "front" | "back" | "side";
/** 取一件裝備的 [主色, 暗色]（paperdoll.ts 的 `itemColors`）。 */
export type ColorFn = (it: GearItem) => readonly [string, string];

const MAT = { steel: "#c3ccd6", gold: "#e8bb48", wood: "#a06a36" } as const;
/** 法杖杖頭光暈的預設色（需求第 4 節）。 */
export const STAFF_GLOW = "#8fe3ff";
const SHIELD_FALLBACK = "#2f5fae";

/** 這一層畫得出來的頭部裝備。 */
export function isInkHeadgear(it: GearItem): boolean {
  return it.kind === "helmet" || it.kind === "hood" || it.kind === "wizard_hat";
}

/** 這一層畫得出來的手持物（魔導劍、權杖、圖騰杖仍走現行畫法）。 */
export function isInkWeapon(it: GearItem): boolean {
  switch (it.kind) {
    case "sword":
      return it.form !== "arcane";
    case "staff":
      return it.form !== "scepter" && it.form !== "totem";
    case "dagger":
    case "axe":
    case "bow":
    case "shield_round":
      return true;
    default:
      return false;
  }
}

/** 與白色混合（亮 t）；不是 #rrggbb 的值原樣回傳。 */
export const lighten = (c: string, t: number): string => {
  if (!/^#[0-9a-f]{6}$/i.test(c)) return c;
  const n = parseInt(c.slice(1), 16);
  const m = (s: number): number => Math.round(((n >> s) & 255) * (1 - t) + 255 * t);
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
};

export const darken = (c: string, t: number): string => {
  if (!/^#[0-9a-f]{6}$/i.test(c)) return c;
  const n = parseInt(c.slice(1), 16);
  const m = (s: number): number => Math.round(((n >> s) & 255) * (1 - t));
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
};

/** 金屬部分的顏色：指定顏色或材質色；沒有材質、木材或不認得 → 鋼色（元素仍混色）。 */
export function metalOf(it: GearItem, colors: ColorFn): string {
  const bare = it.color === undefined && (it.material === undefined || it.material === "wood");
  return colors(bare ? { ...it, material: "steel" } : it)[0];
}

// ============================== 頭部裝備 ==============================
export function drawHelmet(ctx: Ctx, it: GearItem, view: GearView, colors: ColorFn): void {
  const m = metalOf(it, colors);
  if (view !== "side") {
    ink(ctx, "helm", [[-10, -42], [-9.6, -49], [-4.6, -53.6], [4.6, -53.6], [9.6, -49], [10, -42], [10.4, -40], [-10.4, -40]], m);
    stroke(ctx, "helm-band", [[-10, -44.6], [10, -44.6]], 0.6);
    if (view === "front") ink(ctx, "helm-nose", [[-0.9, -45], [0.9, -45], [0.7, -38.6], [-0.7, -38.6]], m, { shade: false, w: 0.5 });
    return;
  }
  ink(ctx, "helm-s", [[-9.8, -36], [-10, -47], [-4.6, -53.6], [3.6, -53.4], [8.8, -48.6], [9.6, -44], [6, -44.4], [2, -43], [0.4, -38.6], [-4, -36.4]], m);
  stroke(ctx, "helm-band-s", [[-9.8, -44.4], [9.4, -44.6]], 0.6);
}

const HOOD_BACK: Pt[] = [[-11, -36], [-11.4, -48], [-5, -55], [5, -55], [11.4, -48], [11, -36], [6, -33], [-6, -33]];
const HOOD_FRONT: Pt[] = [[-11, -36], [-11.4, -48], [-5, -55], [5, -55], [11.4, -48], [11, -36], [7.6, -36.6], [8.4, -45], [0, -48], [-8.4, -45], [-7.6, -36.6]];
const HOOD_SIDE: Pt[] = [[-11, -33], [-11.4, -46], [-5, -55], [4, -54.4], [9.6, -48.6], [9.4, -45], [4, -46.6], [0.6, -42], [-1.6, -36], [-6, -33.4]];

function drawHood(ctx: Ctx, view: GearView, c: string): void {
  if (view === "back") ink(ctx, "hood-b", HOOD_BACK, c);
  else if (view === "front") ink(ctx, "hood", HOOD_FRONT, c);
  else ink(ctx, "hood-s", HOOD_SIDE, c);
}

function drawWizardHat(ctx: Ctx, it: GearItem, view: GearView, c: string): void {
  const trim = it.trim ?? MAT.gold;
  if (view !== "side") {
    ink(ctx, "hat-brim", [[-14, -47], [-6, -50.6], [6, -50.6], [14, -47], [6, -45.4], [-6, -45.4]], c);
    ink(ctx, "hat-cone", [[-6.6, -49], [-2, -60], [4, -70], [3.6, -63], [6.6, -49]], c);
    stroke(ctx, "hat-band", [[-6.4, -50], [6.4, -50]], 1.4, trim);
    return;
  }
  ink(ctx, "hat-brim-s", [[-13, -47.6], [-6, -51], [6, -51], [13, -47.6], [6, -46], [-6, -46]], c);
  ink(ctx, "hat-cone-s", [[-6, -49.6], [-4, -60], [-10, -69.6], [-2.4, -63], [6.4, -49.6]], c);
  stroke(ctx, "hat-band-s", [[-6, -50.4], [6.2, -50.4]], 1.4, trim);
}

/** 畫 C 畫風的頭部裝備（座標＝C 骨架，頭心 (0,-42)）。不是這一層畫得出來的 kind 回傳 false。 */
export function drawInkHeadgear(ctx: Ctx, it: GearItem, view: GearView, colors: ColorFn): boolean {
  if (!isInkHeadgear(it)) return false;
  if (it.kind === "helmet") drawHelmet(ctx, it, view, colors);
  else if (it.kind === "hood") drawHood(ctx, view, it.color ?? colors(it)[0]);
  else drawWizardHat(ctx, it, view, it.color ?? colors(it)[0]);
  return true;
}

// ============================== 武器 ==============================
export interface HeldOpt {
  /** 左右鏡像（成對武器的副手、背面的主手）。 */
  mirror: boolean;
  /** 真側面（劍、斧、匕首往前上斜）。 */
  side: boolean;
  /** 側面遠側那把（畫在身體後面，顏色略暗）。 */
  far: boolean;
  /** 背面（匕首不外斜）。 */
  back?: boolean;
}

/** 側面傾斜（弧度）；正面、背面豎直。 */
const SIDE_TILT = 0.75;

function drawBlade(ctx: Ctx, it: GearItem, key: string, metal: string, outward = 1): void {
  const L = it.kind === "sword" ? 21 : 10;
  const half = it.kind === "sword" && it.form === "broad" ? 1.7 : 1;
  // curved（彎刀）、kris（彎匕）：刀身彎約 3px（越靠尖端彎越多）；其他形制筆直。彎刀正面往外彎（outward ＝ -1，3J-5 美術 PM 小修），側面、背面往前／往外
  const bow = it.form === "curved" ? 3 * outward : it.form === "kris" ? 3 : 0;
  const bx = (y: number): number => bow * (y / L) ** 2;
  ink(ctx, `${key}-blade`, [[-1.1 * half, -2], [-1 * half + bx(L - 1.6), -L + 1.6], [bx(L), -L], [1 * half + bx(L - 1.6), -L + 1.6], [1.1 * half, -2]], metal, { shade: false, w: 0.7 });
  ink(ctx, `${key}-guard`, [[-3.4, -3.2], [3.4, -3.2], [3.4, -1.6], [-3.4, -1.6]], it.hilt ?? MAT.gold, { shade: false, w: 0.6 });
}

function drawAxe(ctx: Ctx, key: string, metal: string, wood: string): void {
  ink(ctx, `${key}-haft`, [[-0.8, 9], [0.8, 9], [0.8, -24], [-0.8, -24]], wood, { shade: false, w: 0.6 });
  ink(ctx, `${key}-head`, [[0.6, -23], [7.6, -27], [9.4, -20.6], [7.6, -14], [0.6, -18]], metal, { w: 0.8 });
  ink(ctx, `${key}-head2`, [[-0.6, -22.4], [-4.6, -24.4], [-5.2, -20.4], [-4.6, -16.6], [-0.6, -18.6]], metal, { w: 0.7 });
}

/** 杖頭光暈：用同心半透明圓疊出柔邊（不用漸層，確定性、好測）。 */
function drawStaff(ctx: Ctx, it: GearItem, key: string, wood: string): void {
  ink(ctx, `${key}-pole`, [[-0.8, 22], [0.8, 22], [0.9, -27], [-0.9, -27]], wood, { shade: false, w: 0.6 });
  const glow = elementTint(it.element) ?? STAFF_GLOW;
  ctx.save();
  ctx.fillStyle = glow;
  for (const [r, a] of [[8, 0.14], [6.2, 0.2], [4.4, 0.28]] as const) {
    ctx.globalAlpha = a;
    ctx.beginPath();
    ctx.arc(0, -30, r, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
  ink(ctx, `${key}-claw`, [[-3, -27], [-2.6, -33.4], [0, -29], [2.6, -33.4], [3, -27]], wood, { shade: false, w: 0.6 });
  ink(ctx, `${key}-orb`, ellPts(0, -30.4, 2.4, 2.4, 10), glow, { shade: false, w: 0.6 });
}

function drawBow(ctx: Ctx, key: string, wood: string): void {
  stroke(ctx, `${key}-string`, [[2, -15], [2, 14]], 0.35, "#e8e0d0");
  ink(ctx, `${key}-limb`, [[1.6, -15], [-2.4, -9], [-3.6, 0], [-2.4, 8], [1.6, 14], [0.4, 14.4], [-4.4, 8], [-5.8, 0], [-4.4, -9], [0.4, -15.4]], wood, { shade: false, w: 0.6 });
}

/** 正面圓盾：握在手上，盾心在手的右下方 (0.4, 2.2)（骨架上盾心 (8.6,-21)）。 */
function drawRoundShield(ctx: Ctx, it: GearItem, key: string, colors: ColorFn): void {
  const c = it.color ?? (it.material === undefined ? SHIELD_FALLBACK : colors(it)[0]);
  const cx = -0.4;
  const cy = 2.2;
  ink(ctx, `${key}-shield`, ellPts(cx, cy, 6.6, 7, 20), c, { w: 1 });
  stroke(ctx, `${key}-shield-rim`, [...ellPts(cx, cy, 5.2, 5.6, 20), [cx + 5.2, cy] as Pt], 0.45);
  ink(ctx, `${key}-shield-boss`, ellPts(cx, cy, 1.8, 1.8, 10), it.trim ?? MAT.gold, { shade: false, w: 0.6 });
}

/**
 * 畫 C 畫風的手持物。(x, y) ＝ 手的位置，`key` ＝ 抖動種子前綴（main／off／main-s／off-s／main-b／off-b）。
 * 正面、背面豎起；側面劍、匕首往前上斜 0.75 rad、斧 0.6 rad，法杖、弓直立。不是這一層畫得出來的 kind 回傳 false。
 */
export function drawInkWeapon(ctx: Ctx, it: GearItem, key: string, x: number, y: number, o: HeldOpt, colors: ColorFn): boolean {
  if (!isInkWeapon(it) || it.kind === "shield_round") return false;
  const shade = o.far ? 0.25 : 0;
  const metal = darken(metalOf(it, colors), shade);
  const wood = darken(MAT.wood, shade);
  ctx.save();
  ctx.translate(x, y);
  // 正面、背面的斧頭左右翻轉：大刃朝外、小刃朝內（C-1b 驗收）
  if (o.mirror !== (it.kind === "axe" && !o.side)) ctx.scale(-1, 1);
  // 正面匕首往外斜 0.5 rad，刀身落在身體外（C-1b 驗收）
  const tilt = o.side ? SIDE_TILT : it.kind === "dagger" && o.back !== true ? -0.5 : 0;
  switch (it.kind) {
    case "sword":
    case "dagger":
      ctx.rotate(tilt);
      drawBlade(ctx, it, key, metal, !o.side && o.back !== true ? -1 : 1);
      break;
    case "axe":
      ctx.rotate(tilt * 0.8);
      drawAxe(ctx, key, metal, wood);
      break;
    case "staff":
      if (it.form === "wand") ctx.scale(0.75, 0.75);
      drawStaff(ctx, it, key, wood);
      break;
    default:
      drawBow(ctx, key, it.color ?? wood);
      break;
  }
  ctx.restore();
  return true;
}

/** 正面圓盾（副手）：以手的位置 (x, y) 為準。不是圓盾回傳 false。 */
export function drawInkShieldFront(ctx: Ctx, it: GearItem, x: number, y: number, colors: ColorFn): boolean {
  if (it.kind !== "shield_round") return false;
  ctx.save();
  ctx.translate(x, y);
  drawRoundShield(ctx, it, "off", colors);
  ctx.restore();
  return true;
}

/** 側面圓盾：一條邊（畫在身體前面、頭與手臂之後）。 */
export function drawInkShieldSide(ctx: Ctx, it: GearItem, colors: ColorFn): boolean {
  if (it.kind !== "shield_round") return false;
  const c = it.color ?? (it.material === undefined ? SHIELD_FALLBACK : colors(it)[0]);
  ink(ctx, "shield-s", ellPts(8.5, -23, 2.6, 7, 14), c, { w: 0.8 });
  return true;
}
