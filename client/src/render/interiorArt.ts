// 室內（Phase 6B-ART1；需求 docs/art/Phase6剩餘美術移植需求.md 1.3）：房間外框、後牆擺設、地板、家具外觀。
// 照樣張 docs/art/sample/townTiles.js 的 room() 與 P.*、ashenTiles.js 的 forge() 移植。全部程式繪製、確定性。
// 室內圖的外圈是牆格：最上一列畫成後牆（1.6 格高，蓋到第 2 列的上緣），左右與下方的牆格畫成暗處加一道牆邊；
// 下方的出口格畫地板與入口光圈。座標是 52 虛擬單位一格。
import { dot, TAU, type Ctx } from "./artDraw";
import { shade } from "./color";
import { entrance, glow, ICON, shadow } from "./townArt";

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

/** 牆與地板的顏色：酒館、鐵匠鋪是木板，導師殿是石板；荒原換鐵灰牆、焦木地板。 */
export function roomPalette(kind: RoomKind, theme: RoomTheme): RoomPalette {
  if (theme === "ashen") return { wall: "#5a5e60", floor: "#5a4434", style: "plank" };
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

export function backWallKey(width: number, p: RoomPalette, decor: readonly WallDecor[]): string {
  return `wall|${width}|${p.wall}|${decor.map((d) => `${d.kind}@${d.x}`).join(",")}`;
}

/** 後牆：牆面（直紋）＋踢腳＋擺設；畫布寬 `width` 格、高 1.6 格。 */
export function drawBackWall(ctx: Ctx, width: number, p: RoomPalette, decor: readonly WallDecor[]): void {
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
  for (const d of decor) DECOR[d.kind](ctx, d.x * U, d.w);
}

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

// ---------------- 家具（物件的 look；畫布 1×2 格，下面那格是物件所在格）----------------

/** 家具外觀（content `look`）＋附魔台（`enchanter` 設施的格子）。 */
export const FURNITURE_LOOKS = ["barrel", "table", "bar", "counter", "anvil", "forge", "candle", "crystal_statue", "shelf", "enchant"] as const;
export type FurnitureLook = (typeof FURNITURE_LOOKS)[number];

export function isFurnitureLook(look: string | null | undefined): look is FurnitureLook {
  return look != null && (FURNITURE_LOOKS as readonly string[]).includes(look);
}

/** 家具的畫法輸入：`joinW`／`joinE` ＝ 左右鄰格是同一種長條家具（吧檯、櫃檯接成一條）。 */
export interface FurnitureSpec {
  look: FurnitureLook;
  joinW: boolean;
  joinE: boolean;
}

export function furnitureKey(s: FurnitureSpec): string {
  return `fur|${s.look}|${s.joinW ? 1 : 0}${s.joinE ? 1 : 0}`;
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
      ctx.save();
      ctx.shadowColor = "#a898ff";
      ctx.shadowBlur = 10;
      ctx.strokeStyle = "#c8bcff";
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.ellipse(cx, y + 18, 16, 6, 0, 0, TAU);
      ctx.stroke();
      for (let k = 0; k < 5; k++) {
        const a = 0.5 + (k * TAU) / 5;
        dot(ctx, cx + Math.cos(a) * 16, y + 12 + Math.sin(a) * 6, 2, "#e0d8ff");
      }
      ctx.restore();
      glow(ctx, cx, y + 12, 18, "rgba(168,152,255,0.9)", 0.55);
      dot(ctx, cx, y + 10, 5, "#c8bcff");
      return;
    }
  }
}
