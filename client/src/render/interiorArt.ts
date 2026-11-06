// 室內（Phase 6B-ART1；需求 docs/archive/art/Phase6剩餘美術移植需求.md 1.3）：房間外框、後牆擺設、地板、家具外觀。
// 照樣張 docs/art/sample/townTiles.js 的 room() 與 P.*、ashenTiles.js 的 forge() 移植。全部程式繪製、確定性。
// 室內圖的外圈是牆格：最上一列畫成後牆（1.6 格高，蓋到第 2 列的上緣），左右與下方的牆格畫成暗處加一道牆邊；
// 下方的出口格畫地板與入口光圈。座標是 52 虛擬單位一格。
import { dot, TAU, type Ctx } from "./artDraw";
import { shade } from "./color";
import { entrance, glow, ICON, shadow } from "./townArt";
import { drawCrystalLamp, drawSkyBridge, drawStele, type BridgeSide } from "./capitalArt";
import { drawPostbox, postboxMaterial } from "./objectArt";

const U = 52;
const OUT = "#1c1712";
const DARK = "#14100c";
const K = { stone: "#e8dcc0", stoneD: "#b8aa8a", gold: "#e8bb48", wood: "#8a6440", woodL: "#a8804e", rug: "#8a2f3a" } as const;

/** 室內的種類（依室內圖裡有哪些設施決定；優先序 導師 ＞ 鐵匠 ＞ 酒館）。 */
export type RoomKind = "tavern" | "smithy" | "mentor" | "plain";
/** 配色：一般（霧渡鎮、主城）或荒原（餘燼集：鐵灰牆、焦木地板）。 */
export type RoomTheme = "town" | "ashen";
export type FloorStyle = "plank" | "slab";

export interface RoomPalette {
  wall: string;
  floor: string;
  style: FloorStyle;
}

export function roomKindOf(facilities: readonly string[]): RoomKind {
  if (facilities.includes("mentor")) return "mentor";
  if (facilities.includes("smithy") || facilities.includes("enchanter")) return "smithy";
  if (facilities.includes("tavern")) return "tavern";
  return "plain";
}

/** 荒原室內的鐵灰牆（掛件的小窗看到暗紅黃昏）。 */
const ROOM_ASHEN_WALL = "#5a5e60";

/** 牆與地板的顏色：酒館、鐵匠鋪是木板，導師殿是石板；荒原換鐵灰牆、焦木地板。 */
export function roomPalette(kind: RoomKind, theme: RoomTheme): RoomPalette {
  if (theme === "ashen") return { wall: ROOM_ASHEN_WALL, floor: "#5a4434", style: "plank" };
  if (kind === "mentor") return { wall: "#3a3a5a", floor: "#b8aa8a", style: "slab" };
  if (kind === "smithy") return { wall: "#4a3e38", floor: "#7a6a58", style: "plank" };
  return { wall: "#5a4030", floor: "#9a7448", style: "plank" };
}

function box(ctx: Ctx, x: number, y: number, w: number, h: number, fill: string, stroke: string | null = OUT, lw = 2, r = 2): void {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke !== null) {
    ctx.lineWidth = lw;
    ctx.strokeStyle = stroke;
    ctx.stroke();
  }
}

// ---------------- 地板與牆（一格一張）----------------

/** 紅地毯的一格：`edges` ＝ 這一格在地毯的哪幾邊（n/e/s/w）。 */
export interface RugCell {
  n: boolean;
  e: boolean;
  s: boolean;
  w: boolean;
}

/** 地板一格（木板或石板，明暗照座標變化）；`rug` 有值時鋪紅地毯（金邊在地毯外緣）。 */
export function drawFloor(ctx: Ctx, gx: number, gy: number, p: RoomPalette, rug: RugCell | null): void {
  ctx.fillStyle = shade(p.floor, 0.92 + ((gx * 7 + gy * 3) % 5) / 30);
  ctx.fillRect(0, 0, U, U);
  ctx.strokeStyle = "rgba(0,0,0,0.25)";
  ctx.lineWidth = 1;
  if (p.style === "plank") {
    for (let k = 1; k < 4; k++) {
      ctx.beginPath();
      ctx.moveTo(0, k * 13);
      ctx.lineTo(U, k * 13);
      ctx.stroke();
    }
    const off = ((gx + gy) % 2) * 26;
    for (let k = 0; k < 4; k++) {
      const x = (off + k * 17) % U;
      ctx.beginPath();
      ctx.moveTo(x, k * 13);
      ctx.lineTo(x, k * 13 + 13);
      ctx.stroke();
    }
  } else {
    ctx.strokeRect(0.5, 0.5, U - 1, U - 1);
    ctx.beginPath();
    ctx.moveTo(U / 2, 0);
    ctx.lineTo(U / 2, U / 2);
    ctx.moveTo(0, U / 2);
    ctx.lineTo(U, U / 2);
    ctx.stroke();
  }
  if (rug === null) return;
  const x0 = rug.w ? 6 : 0;
  const y0 = rug.n ? 6 : 0;
  const x1 = rug.e ? U - 6 : U;
  const y1 = rug.s ? U - 6 : U;
  ctx.fillStyle = K.rug;
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 2;
  ctx.beginPath();
  if (rug.n) (ctx.moveTo(x0, y0), ctx.lineTo(x1, y0));
  if (rug.s) (ctx.moveTo(x0, y1), ctx.lineTo(x1, y1));
  if (rug.w) (ctx.moveTo(x0, y0), ctx.lineTo(x0, y1));
  if (rug.e) (ctx.moveTo(x1, y0), ctx.lineTo(x1, y1));
  ctx.stroke();
  ctx.strokeStyle = K.gold;
  ctx.lineWidth = 2;
  ctx.beginPath();
  const g = 8;
  if (rug.n) (ctx.moveTo(rug.w ? x0 + g : 0, y0 + g), ctx.lineTo(rug.e ? x1 - g : U, y0 + g));
  if (rug.s) (ctx.moveTo(rug.w ? x0 + g : 0, y1 - g), ctx.lineTo(rug.e ? x1 - g : U, y1 - g));
  if (rug.w) (ctx.moveTo(x0 + g, rug.n ? y0 + g : 0), ctx.lineTo(x0 + g, rug.s ? y1 - g : U));
  if (rug.e) (ctx.moveTo(x1 - g, rug.n ? y0 + g : 0), ctx.lineTo(x1 - g, rug.s ? y1 - g : U));
  ctx.stroke();
}

/** 外圈牆格（後牆以外）：暗處，靠房間那一邊畫一道牆（`side` ＝ 房間在這一格的哪一邊）。 */
export function drawWallCell(ctx: Ctx, side: { n: boolean; e: boolean; w: boolean }, p: RoomPalette): void {
  ctx.fillStyle = DARK;
  ctx.fillRect(0, 0, U, U);
  ctx.fillStyle = shade(p.wall, 0.8);
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 2;
  if (side.e) {
    ctx.fillRect(U - 10, 0, 10, U);
    ctx.beginPath();
    ctx.moveTo(U - 10, 0);
    ctx.lineTo(U - 10, U);
    ctx.stroke();
  }
  if (side.w) {
    ctx.fillRect(0, 0, 10, U);
    ctx.beginPath();
    ctx.moveTo(10, 0);
    ctx.lineTo(10, U);
    ctx.stroke();
  }
  if (side.n) {
    ctx.fillRect(0, 0, U, 8);
    ctx.beginPath();
    ctx.moveTo(0, 8);
    ctx.lineTo(U, 8);
    ctx.stroke();
  }
}

/** 出口格：地板＋門墊＋入口光圈（下牆中間的出口）。 */
export function drawExitCell(ctx: Ctx, gx: number, gy: number, p: RoomPalette): void {
  drawFloor(ctx, gx, gy, p, null);
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.fillRect(0, U - 10, U, 10);
  entrance(ctx, U / 2, U * 0.5);
}

// ---------------- 後牆（一張，寬 w 格、高 1.6 格）----------------

/** 後牆的高度（格）。 */
export const BACK_WALL_ROWS = 1.6;

/** 後牆上的擺設（只畫、不佔格）：`x` ＝ 左緣（格）、`w` ＝ 寬（格）。 */
export interface WallDecor {
  kind: "wine_rack" | "fireplace" | "forge" | "weapon_rack" | "bookshelf" | "statue";
  x: number;
  w: number;
}

const DECOR_SETS: Readonly<Record<RoomKind, ReadonlyArray<{ kind: WallDecor["kind"]; w: number; at: "left" | "right" | "center" }>>> = {
  tavern: [
    { kind: "wine_rack", w: 2, at: "left" },
    { kind: "fireplace", w: 2, at: "right" },
  ],
  smithy: [
    { kind: "forge", w: 1, at: "left" },
    { kind: "forge", w: 1, at: "left" },
    { kind: "weapon_rack", w: 1, at: "right" },
  ],
  mentor: [
    { kind: "statue", w: 1, at: "center" },
    { kind: "bookshelf", w: 2, at: "left" },
    { kind: "bookshelf", w: 2, at: "right" },
  ],
  plain: [],
};

/**
 * 後牆擺設的位置：房間內側是 1～w−2 欄；`blocked` ＝ 第 2 列（緊貼後牆那一列）有物件的欄，擺設避開它們，
 * 也不和彼此重疊。左邊的從左往右找、右邊的從右往左找、中間的放正中央；放不下就不畫。
 */
export function wallDecor(kind: RoomKind, width: number, blocked: readonly number[]): WallDecor[] {
  const taken = new Set<number>(blocked);
  const out: WallDecor[] = [];
  const fits = (x: number, w: number) => x >= 1 && x + w <= width - 1 && Array.from({ length: w }, (_, i) => x + i).every((c) => !taken.has(c));
  const take = (x: number, w: number) => {
    for (let i = 0; i < w; i++) taken.add(x + i);
  };
  for (const d of DECOR_SETS[kind]) {
    let x: number | null = null;
    if (d.at === "center") {
      const c = Math.floor((width - d.w) / 2);
      x = fits(c, d.w) ? c : null;
    } else {
      const order = Array.from({ length: Math.max(0, width - 1 - d.w) }, (_, i) => (d.at === "left" ? 1 + i : width - 1 - d.w - i));
      x = order.find((c) => fits(c, d.w)) ?? null;
    }
    if (x === null) continue;
    take(x, d.w);
    out.push({ kind: d.kind, x, w: d.w });
  }
  return out.sort((a, b) => a.x - b.x);
}

// ---- 後牆掛件（6V-3，Fable 審查第 2 節 B）：工具、掛燈、小窗，依室內種類；只畫、不佔格 ----

/** 掛在後牆上半段的小東西（一格寬）。 */
export type WallHangingKind = "window" | "wall_lamp" | "tools" | "pans" | "banner";

export interface WallHanging {
  kind: WallHangingKind;
  /** 欄（格）。 */
  x: number;
}

/** 各種室內輪流掛的東西（從左往右，照空欄的順序套用）。 */
export const HANGING_SETS: Readonly<Record<RoomKind, readonly WallHangingKind[]>> = {
  tavern: ["window", "wall_lamp", "pans", "wall_lamp", "window"],
  smithy: ["tools", "wall_lamp", "window", "tools", "wall_lamp"],
  mentor: ["window", "wall_lamp", "banner", "wall_lamp", "window"],
  plain: ["window", "wall_lamp", "window"],
};

/** 每面後牆最多幾個掛件（6V-4b；美術 PM 6V-3／6V-4 檢查待決 5：「2 個就好，不要疊在擺設上方」）。 */
export const MAX_HANGINGS = 2;

/**
 * 掛件的位置：房間內側 1～w−2 欄裡，擺設（`decor`）與緊貼後牆的物件（`blocked`）都沒佔的欄（不疊在擺設上方）；
 * 相鄰兩欄只掛一個（隔開才不擠），最多 `MAX_HANGINGS` 個。照欄由左往右、套 `HANGING_SETS` 的順序；確定性。
 */
export function wallHangings(kind: RoomKind, width: number, blocked: readonly number[], decor: readonly WallDecor[]): WallHanging[] {
  const taken = new Set<number>(blocked);
  for (const d of decor) for (let i = 0; i < d.w; i++) taken.add(d.x + i);
  const set = HANGING_SETS[kind];
  const out: WallHanging[] = [];
  const max = Math.min(MAX_HANGINGS, set.length);
  let last = -9;
  for (let x = 1; x <= width - 2 && out.length < max; x++) {
    if (taken.has(x) || x - last < 2) continue;
    out.push({ kind: set[out.length]!, x });
    last = x;
  }
  return out;
}

export function backWallKey(width: number, p: RoomPalette, decor: readonly WallDecor[], hangings: readonly WallHanging[] = []): string {
  const hang = hangings.length === 0 ? "" : `|h:${hangings.map((h) => `${h.kind}@${h.x}`).join(",")}`;
  return `wall|${width}|${p.wall}|${decor.map((d) => `${d.kind}@${d.x}`).join(",")}${hang}`;
}

/** 後牆：牆面（直紋）＋踢腳＋擺設；畫布寬 `width` 格、高 1.6 格。 */
export function drawBackWall(ctx: Ctx, width: number, p: RoomPalette, decor: readonly WallDecor[], hangings: readonly WallHanging[] = []): void {
  const W = width * U;
  const H = BACK_WALL_ROWS * U;
  ctx.fillStyle = DARK;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = p.wall;
  ctx.fillRect(U - 10, 0, W - 2 * U + 20, H);
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  for (let k = 2; k < width * 2 - 1; k++) ctx.fillRect(k * (U / 2), 0, 2, H);
  ctx.fillStyle = shade(p.wall, 0.7);
  ctx.fillRect(U - 10, H - 8, W - 2 * U + 20, 8);
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.strokeRect(U - 10, 0, W - 2 * U + 20, H);
  for (const h of hangings) HANGING[h.kind](ctx, h.x * U + U / 2, p);
  for (const d of decor) DECOR[d.kind](ctx, d.x * U, d.w);
}

/** 掛件的畫法：`cx` ＝ 欄的中心；全部畫在後牆上半段（y 6～46），下面留給擺設與家具。 */
const HANGING: Readonly<Record<WallHangingKind, (ctx: Ctx, cx: number, p: RoomPalette) => void>> = {
  /** 小窗：木框、十字窗櫺、窗外天色（荒原是暗紅黃昏），窗台一條。 */
  window(ctx, cx, p) {
    const ashen = p.wall === ROOM_ASHEN_WALL;
    box(ctx, cx - 13, 8, 26, 28, K.wood, OUT, 2, 3);
    const sky = ctx.createLinearGradient(0, 11, 0, 33);
    sky.addColorStop(0, ashen ? "#5a3a3a" : "#9fd0f0");
    sky.addColorStop(1, ashen ? "#c86a3a" : "#e8f4fa");
    ctx.fillStyle = sky;
    ctx.fillRect(cx - 10, 11, 20, 22);
    ctx.fillStyle = K.wood;
    ctx.fillRect(cx - 1, 11, 2, 22);
    ctx.fillRect(cx - 10, 21, 20, 2);
    ctx.fillStyle = "rgba(255,255,255,0.35)";
    ctx.fillRect(cx - 8, 13, 3, 6);
    box(ctx, cx - 16, 35, 32, 4, K.woodL, OUT, 1.4, 1);
  },
  /** 掛燈：鐵托架＋小提燈＋暖光。 */
  wall_lamp(ctx, cx) {
    glow(ctx, cx, 26, 22, "rgba(255,200,110,0.9)", 0.55);
    ctx.strokeStyle = "#2a2420";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx - 8, 12);
    ctx.lineTo(cx, 12);
    ctx.lineTo(cx, 17);
    ctx.stroke();
    box(ctx, cx - 5, 17, 10, 14, "#3a3230", OUT, 1.6, 2);
    ctx.fillStyle = "#ffd27a";
    ctx.fillRect(cx - 3, 20, 6, 8);
    dot(ctx, cx, 24, 1.8, "#fff2c0");
  },
  /** 工具板：木板＋掛鉤上的鐵鉗、錘子、馬蹄鐵（鐵匠鋪）。 */
  tools(ctx, cx) {
    box(ctx, cx - 18, 8, 36, 30, shade(K.wood, 0.85), OUT, 2, 2);
    for (const hx of [cx - 10, cx, cx + 10]) dot(ctx, hx, 12, 1.4, "#2a2420");
    // 鐵鉗
    ctx.strokeStyle = "#9aa2aa";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx - 12, 13);
    ctx.lineTo(cx - 9, 34);
    ctx.moveTo(cx - 8, 13);
    ctx.lineTo(cx - 11, 34);
    ctx.stroke();
    // 錘子
    ctx.strokeStyle = K.woodL;
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.moveTo(cx, 13);
    ctx.lineTo(cx, 34);
    ctx.stroke();
    box(ctx, cx - 5, 13, 10, 6, "#7a8088", OUT, 1.2, 1);
    // 馬蹄鐵
    ctx.strokeStyle = "#8a9098";
    ctx.lineWidth = 2.6;
    ctx.beginPath();
    ctx.arc(cx + 10, 24, 5, Math.PI * 0.85, Math.PI * 2.15, true);
    ctx.stroke();
  },
  /** 鍋具：橫桿＋掛鉤上的銅鍋、湯杓、一串乾辣椒（酒館）。 */
  pans(ctx, cx) {
    ctx.fillStyle = "#2a2420";
    ctx.fillRect(cx - 18, 10, 36, 3);
    ctx.strokeStyle = "#2a2420";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (const hx of [cx - 11, cx + 2, cx + 13]) {
      ctx.moveTo(hx, 13);
      ctx.lineTo(hx, 18);
    }
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx - 11, 26, 7, 0, TAU);
    ctx.fillStyle = "#b8743a";
    ctx.fill();
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    dot(ctx, cx - 13, 24, 2, "rgba(255,230,180,0.6)");
    ctx.strokeStyle = "#9aa2aa";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(cx + 2, 18);
    ctx.lineTo(cx + 2, 32);
    ctx.stroke();
    dot(ctx, cx + 2, 33, 3, "#9aa2aa");
    for (let k = 0; k < 4; k++) dot(ctx, cx + 13 + (k % 2 ? 1 : -1), 20 + k * 4, 2.2, "#b8322a");
  },
  /** 掛旗：深紫底金邊燕尾、中間一顆晶石紋章（導師殿）。 */
  banner(ctx, cx) {
    ctx.fillStyle = "#2a2420";
    ctx.fillRect(cx - 12, 7, 24, 2.4);
    ctx.beginPath();
    ctx.moveTo(cx - 9, 9);
    ctx.lineTo(cx + 9, 9);
    ctx.lineTo(cx + 9, 40);
    ctx.lineTo(cx, 34);
    ctx.lineTo(cx - 9, 40);
    ctx.closePath();
    ctx.fillStyle = "#4a2a7a";
    ctx.fill();
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = K.gold;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx, 15);
    ctx.lineTo(cx + 5, 21);
    ctx.lineTo(cx, 28);
    ctx.lineTo(cx - 5, 21);
    ctx.closePath();
    ctx.fillStyle = "#c8bcff";
    ctx.fill();
  },
};

const DECOR: Readonly<Record<WallDecor["kind"], (ctx: Ctx, x: number, w: number) => void>> = {
  wine_rack: (ctx, x, w) => shelfArt(ctx, x, 4, w, ["#8a5a30", "#c8a070", "#6a3a20", "#e8e0d0"]),
  bookshelf: (ctx, x, w) => shelfArt(ctx, x, 4, w, ["#5a3a9a", "#3a5ad0", "#c83a2a", "#e8bb48"]),
  fireplace(ctx, x) {
    box(ctx, x + 4, 8, U * 2 - 8, U * 1.2, "#6a5e54", OUT, 2, 3);
    ctx.fillStyle = DARK;
    ctx.beginPath();
    ctx.arc(x + U, U * 1.2, 22, Math.PI, 0);
    ctx.fill();
    glow(ctx, x + U, U, 40, "rgba(255,150,60,0.9)", 0.7);
    ICON.rest(ctx, x + U, U * 1.05, 22);
  },
  forge: (ctx, x) => forgeArt(ctx, x, 14),
  weapon_rack(ctx, x) {
    box(ctx, x + 6, 10, U - 12, 6, K.wood, OUT, 1.6, 1);
    box(ctx, x + 6, U * 1.2, U - 12, 6, K.wood, OUT, 1.6, 1);
    for (let k = 0; k < 3; k++) {
      ctx.strokeStyle = OUT;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x + 14 + k * 12, 14);
      ctx.lineTo(x + 14 + k * 12, U * 1.22);
      ctx.stroke();
      ctx.strokeStyle = "#dfe4ea";
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
  },
  statue: (ctx, x) => statueArt(ctx, x + U / 2, U * 1.5, 0.72),
};

function shelfArt(ctx: Ctx, x: number, y: number, w: number, items: readonly string[]): void {
  box(ctx, x + 4, y, w * U - 8, U * 1.3, K.wood, OUT, 2, 2);
  for (let r = 0; r < 3; r++) {
    ctx.fillStyle = shade(K.wood, 0.7);
    ctx.fillRect(x + 6, y + 14 + r * 20, w * U - 12, 3);
    for (let k = 0; k < w * 5 - 1; k++) {
      ctx.fillStyle = items[(k + r) % items.length]!;
      ctx.fillRect(x + 8 + k * 9.5, y + 2 + r * 20, 6, 12);
    }
  }
}

/** 鍛爐（ashenTiles.js 的 forge）：石爐＋火口火光＋小煙囪；`y` ＝ 爐身頂。 */
function forgeArt(ctx: Ctx, x: number, y: number): void {
  const cx = x + U / 2;
  shadow(ctx, cx + 4, y + 34, 22, 6);
  box(ctx, x + 6, y, U - 12, 30, "#5a4e44", OUT, 2, 4);
  ctx.fillStyle = "#1a120c";
  ctx.beginPath();
  ctx.arc(cx, y + 18, 8, Math.PI, 0);
  ctx.fill();
  glow(ctx, cx, y + 16, 16, "rgba(255,140,40,0.95)", 0.8);
  dot(ctx, cx, y + 17, 4, "#ffb030");
  box(ctx, x + U - 16, y - 12, 9, 16, "#5a4e44", OUT, 1.6, 1);
}

/** 晶石像：石座＋發光的晶石；`base` ＝ 石座底邊，`k` ＝ 縮放。 */
function statueArt(ctx: Ctx, cx: number, base: number, k: number): void {
  const top = base - 18 * k;
  glow(ctx, cx, top - 40 * k, 40 * k, "rgba(143,123,255,0.9)", 0.5);
  box(ctx, cx - 18 * k, top, 36 * k, 18 * k, K.stoneD, OUT, 2, 2);
  ctx.beginPath();
  ctx.moveTo(cx - 12 * k, top);
  ctx.lineTo(cx - 14 * k, top - 52 * k);
  ctx.lineTo(cx, top - 78 * k);
  ctx.lineTo(cx + 14 * k, top - 52 * k);
  ctx.lineTo(cx + 12 * k, top);
  ctx.closePath();
  ctx.fillStyle = "#c8bcff";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

// ---------------- 附魔台的發光環（6V-3）----------------

/**
 * 附魔台上方的符文環（家具畫布座標，`cy` 是相對所在格頂的高度）：`rx`、`ry` 是透視後的橢圓半徑。
 * 靜態貼圖畫亮環與光暈；會轉的符文由環境動態層（`ambientLayer`）疊上去，減少動態時停在第 0 毫秒。
 */
export const ENCHANT_RING = { cy: 16, rx: 19, ry: 7.5 } as const;

/** 靜態的發光環：外圈暈染＋兩道亮環（外粗內細），描線帶紫色光暈。 */
export function drawEnchantRingStatic(ctx: Ctx, cx: number, cy: number): void {
  const { rx, ry } = ENCHANT_RING;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(1, ry / rx);
  const halo = ctx.createRadialGradient(0, 0, rx * 0.4, 0, 0, rx * 1.45);
  halo.addColorStop(0, "rgba(168,152,255,0)");
  halo.addColorStop(0.6, "rgba(168,152,255,0.45)");
  halo.addColorStop(1, "rgba(168,152,255,0)");
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(0, 0, rx * 1.45, 0, TAU);
  ctx.fill();
  ctx.restore();
  ctx.save();
  ctx.shadowColor = "#b8a8ff";
  ctx.shadowBlur = 12;
  ctx.strokeStyle = "#e6e0ff";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.stroke();
  ctx.strokeStyle = "rgba(200,188,255,0.9)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx * 0.72, ry * 0.72, 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
}

/** 會轉的符文環（從正上方看的圓，`r` ＝ 半徑）：8 個符文刻在一圈細環上；環境動態層把它壓扁成透視、慢慢轉。 */
export const ENCHANT_RUNES = 8;
export function drawEnchantRunes(ctx: Ctx, cx: number, cy: number, r: number): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.strokeStyle = "rgba(240,236,255,0.95)";
  ctx.lineWidth = 1.4;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.86, 0, TAU);
  ctx.stroke();
  for (let k = 0; k < ENCHANT_RUNES; k++) {
    const a = (k * TAU) / ENCHANT_RUNES;
    ctx.save();
    ctx.rotate(a);
    ctx.translate(0, -r * 0.86);
    ctx.beginPath();
    // 符文：一豎＋依序換的短撇（確定性，照序號）
    ctx.moveTo(0, -3.2);
    ctx.lineTo(0, 3.2);
    const v = k % 4;
    if (v === 0) (ctx.moveTo(-2.4, -1.6), ctx.lineTo(2.4, 1.6));
    else if (v === 1) (ctx.moveTo(-2.4, 0), ctx.lineTo(2.4, 0));
    else if (v === 2) (ctx.moveTo(0, -3.2), ctx.lineTo(2.6, -0.6));
    else (ctx.moveTo(-2.6, 1.2), ctx.lineTo(0, 3.2), ctx.lineTo(2.6, 1.2));
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
}

// ---------------- 家具（物件的 look；畫布 1×2 格，下面那格是物件所在格）----------------

/** 家具外觀（content `look`）＋附魔台（`enchanter` 設施的格子）。源晶燈、橋頭石碑、浮橋是主城的街景（6D-ART2，畫法在 capitalArt.ts）。郵筒（6T-1b）畫法在 objectArt.ts，材質照 `region`（地圖的區域）。 */
export const FURNITURE_LOOKS = ["barrel", "table", "bar", "counter", "anvil", "forge", "candle", "crystal_statue", "shelf", "enchant", "crystal_lamp", "stele", "sky_bridge", "postbox"] as const;
export type FurnitureLook = (typeof FURNITURE_LOOKS)[number];

export function isFurnitureLook(look: string | null | undefined): look is FurnitureLook {
  return look != null && (FURNITURE_LOOKS as readonly string[]).includes(look);
}

/** 家具的畫法輸入：`joinW`／`joinE` ＝ 左右鄰格是同一種長條家具（吧檯、櫃檯接成一條）。 */
export interface FurnitureSpec {
  look: FurnitureLook;
  joinW: boolean;
  joinE: boolean;
  /** 橋頭石碑的紋章（同一格情境物件的 `stele_region`；6D-ART2）。郵筒（6T-1b）：地圖的區域（材質）。 */
  region?: string;
  /**
   * 浮橋往哪一邊的地圖邊（6D-ART2）。浮橋的 `joinW`／`joinE` ＝ 垂直於橋的方向上的鄰格也是浮橋：
   * 南北向的橋是西／東鄰格，東西向的橋是北／南鄰格。
   */
  side?: BridgeSide;
}

export function furnitureKey(s: FurnitureSpec): string {
  const extra = `${s.region !== undefined ? `|${s.region}` : ""}${s.side !== undefined ? `|${s.side}` : ""}`;
  return `fur|${s.look}|${s.joinW ? 1 : 0}${s.joinE ? 1 : 0}${extra}`;
}

/** 浮橋往外看時左、右邊要不要畫繩欄（鄰格也是浮橋就不畫）。 */
export function bridgeRails(s: FurnitureSpec): { left: boolean; right: boolean } {
  const leftIsW = s.side === undefined || s.side === "n" || s.side === "e"; // n：左＝西；e：左＝北（joinW）；s、w 反過來
  return leftIsW ? { left: !s.joinW, right: !s.joinE } : { left: !s.joinE, right: !s.joinW };
}

/** 家具畫布的列數（上面多 1 格給高的家具）。 */
export const FURNITURE_ROWS = 2;

/** 畫一件家具；原點在畫布左上，物件所在格是 y ＝ U～2U。 */
export function drawFurniture(ctx: Ctx, s: FurnitureSpec): void {
  const y = U; // 所在格的頂
  const cx = U / 2;
  switch (s.look) {
    case "barrel":
      for (const [dx, dy] of [
        [4, 16],
        [24, 16],
        [14, 2],
      ] as const) {
        ctx.beginPath();
        ctx.ellipse(dx + 10, y + dy + 12, 10, 12, 0, 0, TAU);
        ctx.fillStyle = "#8a5a30";
        ctx.fill();
        ctx.lineWidth = 1.6;
        ctx.strokeStyle = OUT;
        ctx.stroke();
        ctx.strokeStyle = "#3a3a3a";
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.ellipse(dx + 10, y + dy + 12, 10, 4, 0, 0, TAU);
        ctx.stroke();
      }
      return;
    case "table":
      shadow(ctx, cx + 3, y + U * 0.8, 20, 6);
      for (const sx of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(cx + sx * 20, y + 36, 6, 4, 0, 0, TAU);
        ctx.fillStyle = K.wood;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = OUT;
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.ellipse(cx, y + 26, 18, 11, 0, 0, TAU);
      ctx.fillStyle = K.woodL;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = OUT;
      ctx.stroke();
      dot(ctx, cx - 6, y + 24, 3, "#c8a070");
      dot(ctx, cx + 6, y + 27, 3, "#e8e0d0");
      return;
    case "bar":
    case "counter": {
      const x0 = s.joinW ? 0 : 2;
      const x1 = s.joinE ? U : U - 2;
      shadow(ctx, cx, y + U * 0.9, U / 2, 6, 0.3);
      ctx.fillStyle = s.look === "bar" ? K.wood : "#7a5a3a";
      ctx.fillRect(x0, y + 18, x1 - x0, 28);
      ctx.fillStyle = K.woodL;
      ctx.fillRect(s.joinW ? 0 : 0, y + 12, s.joinE ? U : U, 9);
      ctx.strokeStyle = OUT;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, y + 12);
      ctx.lineTo(U, y + 12);
      ctx.moveTo(0, y + 21);
      ctx.lineTo(U, y + 21);
      ctx.moveTo(x0, y + 46);
      ctx.lineTo(x1, y + 46);
      if (!s.joinW) (ctx.moveTo(0, y + 12), ctx.lineTo(0, y + 21), ctx.moveTo(x0, y + 21), ctx.lineTo(x0, y + 46));
      if (!s.joinE) (ctx.moveTo(U, y + 12), ctx.lineTo(U, y + 21), ctx.moveTo(x1, y + 21), ctx.lineTo(x1, y + 46));
      ctx.stroke();
      if (s.look === "bar") {
        dot(ctx, 16, y + 9, 3.5, "#c8a070"); // 酒杯
        box(ctx, 32, y + 1, 6, 11, "#6a8a5a", OUT, 1.2, 2); // 酒瓶
      } else {
        box(ctx, 14, y + 4, 22, 8, "#f2e6c8", OUT, 1.2, 1); // 攤開的書
      }
      return;
    }
    case "anvil":
      shadow(ctx, cx + 3, y + U * 0.8, 18, 5);
      ICON.anvil(ctx, cx, y + U / 2, 34);
      return;
    case "forge":
      forgeArt(ctx, 0, y + 12);
      return;
    case "candle":
      shadow(ctx, cx + 2, y + U * 0.82, 10, 4);
      box(ctx, cx - 9, y + 38, 18, 6, "#6a5a4a", OUT, 1.2, 1);
      box(ctx, cx - 3, y + 14, 6, 26, "#f2e6c8", OUT, 1.2, 1);
      glow(ctx, cx, y + 8, 16, "rgba(255,210,120,0.9)", 0.75);
      ICON.rest(ctx, cx, y + 9, 10);
      return;
    case "crystal_statue":
      shadow(ctx, cx + 4, y + U * 0.85, 22, 6);
      statueArt(ctx, cx, y + U * 0.82, 0.62);
      return;
    case "shelf":
      shelfArt(ctx, 0, y - U * 0.4, 1, ["#c83a2a", "#3a5ad0", "#6aa84a", "#e8bb48"]);
      return;
    case "enchant": {
      shadow(ctx, cx + 3, y + U * 0.84, 20, 6);
      box(ctx, 8, y + 24, U - 16, 18, "#3a3450", OUT, 2, 3);
      drawEnchantRingStatic(ctx, cx, y + ENCHANT_RING.cy);
      glow(ctx, cx, y + 8, 16, "rgba(168,152,255,0.9)", 0.6);
      dot(ctx, cx, y + 8, 4.5, "#e0d8ff");
      return;
    }
    case "crystal_lamp":
      drawCrystalLamp(ctx);
      return;
    case "stele":
      drawStele(ctx, s.region ?? "");
      return;
    case "sky_bridge": {
      const r = bridgeRails(s);
      drawSkyBridge(ctx, s.side ?? "n", r.left, r.right);
      return;
    }
    case "postbox":
      drawPostbox(ctx, cx, y + U * 0.82, postboxMaterial(s.region));
      return;
  }
}
