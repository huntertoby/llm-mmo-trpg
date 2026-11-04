// 主城（樞島）的建築與街景（Phase 6D-ART2；需求 docs/art/Phase6剩餘美術移植需求.md 第 2 節、docs/art/城鎮與室內圖庫.md 第 1 節）。
// 照樣張 docs/art/sample/townTiles.js 的 stoneHall()、portalPlaza()、banner()、fountain() 移植；全部程式繪製、確定性
// （沒有亂數，只依尺寸、門的位置、區域與開放狀態）。座標是 52 虛擬單位一格（同 townArt.ts）。
// - 建築：白石藍頂金邊（stone_hall）、導師殿多一座發光晶尖塔（mentor_hall）、帆布帳篷（tent）、圓形石邊的噴水池（fountain）。
//   畫布 w×(h+屋頂列數) 格，同 townArt.ts；招牌只畫圖示，不寫字。
// - 中央傳送陣：地上的光圈（3×3 格）＋中央晶柱（1×2 格）；五區光圈已開放的是該區顏色、沒開放的是灰色。
// - 五面區旗、源晶燈、橋頭石碑（該區紋章）、浮橋（斷在雲上）。
// 只換外觀：規則照伺服器的地形與物件（傳送石、石柱、木橋）。
import { dot, TAU, type Ctx } from "./artDraw";
import { rgba } from "./color";
import { box, closedDoor, doorCenters, drawBuilding, glow, ICON, roofRows, shadow, signOf, windowCenters, type BuildingSpec, type SignIcon } from "./townArt";

const U = 52;
const OUT = "#1c1712";
/** 晶冠的基準風格（townTiles.js 的 K）。 */
const K = { stone: "#e8dcc0", stoneD: "#b8aa8a", roof: "#3a5ad0", roofD: "#2a4098", gold: "#e8bb48", crystal: "#c8bcff", canvas: "#e0d0a8", canvasD: "#b8a47a", water: "#3f8ac8" } as const;

/** 五區的代表色（需求第 2 節）：晶冠紫、雲嶺綠、樞市青、灰燼橘、霜潮藍。順序＝傳送陣光圈與區旗由正北起順時針。 */
export const REGION_ORDER = ["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"] as const;
export type CapitalRegion = (typeof REGION_ORDER)[number];
export const REGION_COLOR: Readonly<Record<CapitalRegion, string>> = {
  crystal_crown: "#8f7bff",
  cloud_ridge: "#6aa84a",
  arcane_hub: "#4ae0d0",
  ashen_waste: "#ff6a1a",
  frost_tide: "#7ad8ff",
};
/** 沒開放的區、不認得的區：灰色。 */
export const LOCKED_COLOR = "#8a8a8a";

export function isCapitalRegion(id: string | null | undefined): id is CapitalRegion {
  return id != null && (REGION_ORDER as readonly string[]).includes(id);
}

export function regionColor(id: string | null | undefined): string {
  return isCapitalRegion(id) ? REGION_COLOR[id] : LOCKED_COLOR;
}

// ---------------- 建築 ----------------

/** 主城的建築種類（其他種類照 townArt.ts 的 `drawBuilding`）。 */
export const CAPITAL_BUILDINGS: ReadonlySet<string> = new Set(["stone_hall", "mentor_hall", "tent", "fountain"]);

/** 任何一種建築的畫法（主城的種類在這裡，其他交給 townArt.ts）。 */
export function paintBuilding(ctx: Ctx, s: BuildingSpec): void {
  if (s.kind === "stone_hall" || s.kind === "mentor_hall") stoneHall(ctx, s);
  else if (s.kind === "tent") tent(ctx, s);
  else if (s.kind === "fountain") fountain(ctx, s);
  else drawBuilding(ctx, s);
}

/** 藍框招牌（townTiles.js 的 stoneHall 招牌）：只畫圖示。 */
function blueSign(ctx: Ctx, x: number, y: number, icon: SignIcon): void {
  box(ctx, x - 12, y, 24, 22, "#2a3a6a", OUT, 2, 3);
  box(ctx, x - 9, y + 3, 18, 16, "#f2e6c8", null, 0, 2);
  ICON[icon](ctx, x, y + 11, 12);
}

/** 白石藍頂的建築（townTiles.js 的 stoneHall）：立面白石＋金邊、藍色瓦頂、金色屋脊；導師殿多一座發光晶尖塔。 */
function stoneHall(ctx: Ctx, s: BuildingSpec): void {
  const H = s.h + roofRows(s);
  const W = s.w * U;
  const faceH = 1.4 * U;
  const faceTop = H * U - faceH;
  const spire = s.kind === "mentor_hall";
  const roofTop = spire && H >= 3 ? 0.8 * U : 6;
  shadow(ctx, W / 2 + 8, H * U - 2, W / 2, 9, 0.35);
  box(ctx, 4, faceTop, W - 8, faceH - 4, K.stone, OUT, 2, 2); // 白石立面
  ctx.strokeStyle = "rgba(120,100,70,0.45)";
  ctx.lineWidth = 1;
  for (let k = 1; k < 4; k++) {
    ctx.beginPath();
    ctx.moveTo(6, faceTop + k * 17);
    ctx.lineTo(W - 6, faceTop + k * 17);
    ctx.stroke();
  }
  ctx.fillStyle = K.gold; // 金邊
  ctx.fillRect(4, faceTop, W - 8, 3);
  // 藍色瓦頂
  ctx.beginPath();
  ctx.moveTo(2, faceTop + 6);
  ctx.lineTo(10, roofTop);
  ctx.lineTo(W - 10, roofTop);
  ctx.lineTo(W - 2, faceTop + 6);
  ctx.closePath();
  ctx.fillStyle = K.roof;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = rgba(K.roofD, 0.8);
  ctx.lineWidth = 1.2;
  for (let k = 12; k < W - 8; k += 8) {
    ctx.beginPath();
    ctx.moveTo(k, roofTop + 2);
    ctx.lineTo(k + (k - W / 2) * 0.08, faceTop + 4);
    ctx.stroke();
  }
  box(ctx, 8, roofTop - 4, W - 16, 6, K.gold, OUT, 1.5, 2); // 金色屋脊
  for (const wx of windowCenters(s)) {
    const x = wx * U;
    box(ctx, x - 7, faceTop + 14, 14, 18, "#3a4a6a", OUT, 1.5, 6);
    ctx.fillStyle = "rgba(255,230,160,0.5)";
    ctx.fillRect(x - 5, faceTop + 18, 10, 12);
  }
  if (s.doors.length === 0) closedDoor(ctx, doorCenters(s)[0]! * U, H * U, "wood");
  const icon = signOf(s);
  if (icon !== null) {
    const dc = doorCenters(s)[0]! * U;
    const sx = dc + 20 + 14 <= W ? dc + 20 : dc - 20; // 門在右端時招牌掛在左邊
    blueSign(ctx, sx, faceTop + 6, icon);
  }
  if (spire) crystalSpire(ctx, W / 2, roofTop);
}

/** 導師殿屋頂的晶尖塔（發光）：底在 `base`，往上最多到畫布頂。 */
function crystalSpire(ctx: Ctx, cx: number, base: number): void {
  const top = Math.max(2, base - 0.75 * U);
  glow(ctx, cx, (top + base) / 2, 30, "rgba(143,123,255,0.9)", 0.55);
  ctx.beginPath();
  ctx.moveTo(cx - 12, base + 4);
  ctx.lineTo(cx, top);
  ctx.lineTo(cx + 12, base + 4);
  ctx.closePath();
  ctx.fillStyle = K.crystal;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.6)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(cx - 3, base);
  ctx.lineTo(cx, top + 8);
  ctx.stroke();
}

/** 傭兵營的帆布帳篷：條紋帆布、中間的門簾、兩側的繩與木樁、頂上的小旗。 */
function tent(ctx: Ctx, s: BuildingSpec): void {
  const H = s.h + roofRows(s);
  const W = s.w * U;
  const foot = H * U - 6;
  const peak = Math.max(10, H * U - (s.h + 0.6) * U);
  const cx = W / 2;
  // 帳篷底下踩平的地面：蓋住整個範圍（底下的牆格不露出來）
  const ground = roofRows(s) * U;
  box(ctx, 0, ground, W, H * U - ground, "#a88a5e", "rgba(60,40,20,0.6)", 1.2, 4);
  ctx.fillStyle = "rgba(255,240,200,0.12)";
  for (let x = 10; x < W - 6; x += 16) ctx.fillRect(x, ground + 4, 6, H * U - ground - 8);
  shadow(ctx, cx + 6, foot, W / 2 - 2, 8, 0.35);
  ctx.beginPath();
  ctx.moveTo(6, foot);
  ctx.quadraticCurveTo(cx * 0.55, peak + (foot - peak) * 0.35, cx, peak);
  ctx.quadraticCurveTo(W - cx * 0.55, peak + (foot - peak) * 0.35, W - 6, foot);
  ctx.closePath();
  ctx.fillStyle = K.canvas;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.save();
  ctx.clip();
  ctx.fillStyle = "rgba(160,60,40,0.35)"; // 條紋
  for (let x = 14; x < W; x += 22) ctx.fillRect(x, peak, 9, foot - peak);
  ctx.restore();
  // 門簾
  ctx.beginPath();
  ctx.moveTo(cx - 14, foot);
  ctx.lineTo(cx, foot - 40);
  ctx.lineTo(cx + 14, foot);
  ctx.closePath();
  ctx.fillStyle = "#3a2a1e";
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = K.canvasD;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, foot - 40);
  ctx.lineTo(cx - 9, foot);
  ctx.stroke();
  // 繩與木樁
  ctx.strokeStyle = "rgba(60,40,20,0.7)";
  ctx.lineWidth = 1;
  for (const [x0, x1] of [
    [cx * 0.6, 2],
    [W - cx * 0.6, W - 2],
  ] as const) {
    ctx.beginPath();
    ctx.moveTo(x0, peak + (foot - peak) * 0.45);
    ctx.lineTo(x1, foot + 2);
    ctx.stroke();
    dot(ctx, x1, foot + 2, 2, "#6a4a2a");
  }
  // 頂上的小旗
  box(ctx, cx - 1.5, peak - 14, 3, 16, "#6a5a4a", OUT, 1, 1);
  ctx.beginPath();
  ctx.moveTo(cx + 1.5, peak - 14);
  ctx.lineTo(cx + 14, peak - 10);
  ctx.lineTo(cx + 1.5, peak - 6);
  ctx.closePath();
  ctx.fillStyle = "#c83a2a";
  ctx.fill();
  ctx.lineWidth = 1.2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

/** 許願池的幾何（畫布座標，6V-4）：池心、外緣半徑（透視橢圓）、石緣厚度、中央噴口。 */
export interface FountainGeom {
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  /** 石緣寬（俯視）與前緣的高（立面）。 */
  rim: number;
  lip: number;
  /** 中央噴口（水從這裡噴出）。 */
  spoutX: number;
  spoutY: number;
}

export function fountainGeom(s: BuildingSpec): FountainGeom {
  const H = s.h + roofRows(s);
  const W = s.w * U;
  const cx = W / 2;
  const rx = Math.min(W, s.h * U) / 2 - 6;
  const ry = rx * 0.62;
  const cy = H * U - ry - 12;
  return { cx, cy, rx, ry, rim: 8, lip: 8, spoutX: cx, spoutY: cy - 30 };
}

/** 石緣的石塊數（沿圓周切開，接縫是放射狀的短線）。 */
export const FOUNTAIN_STONES = 14;

/**
 * 許願池（6V-4，Fable 審查第 2 節 C）：圓形石緣水池（透視成橢圓）＋前緣立面、石塊接縫、池水、
 * 中央兩層石座與金色噴口。噴水由環境動態層畫（`ambientAnim.fountainSpray`；減少動態時停在第 0 毫秒），
 * 這裡只畫一圈落水的漣漪。蓋在水表面上（只畫）。
 */
function fountain(ctx: Ctx, s: BuildingSpec): void {
  const g = fountainGeom(s);
  const { cx, cy, rx, ry, rim, lip } = g;
  shadow(ctx, cx + 4, cy + ry + lip - 2, rx, ry * 0.35, 0.3);
  // 前緣立面（下半圈往下延伸 lip）
  ctx.beginPath();
  ctx.ellipse(cx, cy + lip, rx, ry, 0, 0, Math.PI);
  ctx.lineTo(cx - rx, cy);
  ctx.ellipse(cx, cy, rx, ry, 0, Math.PI, 0, true);
  ctx.closePath();
  ctx.fillStyle = "#a89a7c";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  // 石緣頂面
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.fillStyle = K.stone;
  ctx.fill();
  ctx.stroke();
  // 池水
  const irx = rx - rim;
  const iry = ry - rim * 0.62;
  const water = ctx.createLinearGradient(0, cy - iry, 0, cy + iry);
  water.addColorStop(0, "#2f74b8");
  water.addColorStop(1, "#5ab0e8");
  ctx.beginPath();
  ctx.ellipse(cx, cy, irx, iry, 0, 0, TAU);
  ctx.fillStyle = water;
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  // 石塊接縫：頂面放射狀短線、立面直線
  ctx.strokeStyle = "rgba(90,78,56,0.7)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let k = 0; k < FOUNTAIN_STONES; k++) {
    const a = (k + 0.5) * (TAU / FOUNTAIN_STONES);
    const ox = Math.cos(a);
    const oy = Math.sin(a);
    ctx.moveTo(cx + ox * irx, cy + oy * iry);
    ctx.lineTo(cx + ox * rx, cy + oy * ry);
    if (oy > 0.05) {
      ctx.moveTo(cx + ox * rx, cy + oy * ry);
      ctx.lineTo(cx + ox * rx, cy + oy * ry + lip);
    }
  }
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.3)"; // 頂面左上的受光
  ctx.beginPath();
  ctx.ellipse(cx - rx * 0.35, cy - ry * 0.78, rx * 0.3, 1.6, -0.15, 0, TAU);
  ctx.fill();
  // 落水的漣漪（靜態兩圈）
  ctx.strokeStyle = "rgba(220,240,255,0.55)";
  ctx.lineWidth = 1.1;
  for (const k of [0.42, 0.7]) {
    ctx.beginPath();
    ctx.ellipse(cx, cy + 2, irx * k, iry * k, 0, 0, TAU);
    ctx.stroke();
  }
  // 中央石座（下座＋上層小水盤）與噴口
  box(ctx, cx - 6, cy - 22, 12, 24, K.stone, OUT, 1.6, 2);
  ctx.beginPath();
  ctx.ellipse(cx, cy - 22, 13, 4.5, 0, 0, TAU);
  ctx.fillStyle = K.stoneD;
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(cx, cy - 23, 9.5, 3, 0, 0, TAU);
  ctx.fillStyle = "#5ab0e8";
  ctx.fill();
  box(ctx, cx - 2.5, g.spoutY + 2, 5, cy - 24 - g.spoutY, K.stone, OUT, 1.2, 1);
  dot(ctx, g.spoutX, g.spoutY + 1, 3.4, K.gold);
}

// ---------------- 中央傳送陣與區旗 ----------------

/** 傳送陣光圈的畫布（格）：中心在傳送石那一格的中心。 */
export const PORTAL_TILES = 3;

/** 傳送陣的地面光圈（3×3 格畫布，中心＝傳送石那一格）：金色雙圈＋五區光圈（已開放＝該區顏色並發光，沒開放＝灰色）。 */
export function drawPortalRing(ctx: Ctx, open: readonly string[]): void {
  const c = (PORTAL_TILES * U) / 2;
  ctx.save();
  ctx.strokeStyle = rgba(K.gold, 0.9);
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.ellipse(c, c, 70, 46, 0, 0, TAU);
  ctx.stroke();
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.ellipse(c, c, 58, 38, 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
  REGION_ORDER.forEach((id, k) => {
    const a = -Math.PI / 2 + (k * TAU) / 5;
    const px = c + Math.cos(a) * 64;
    const py = c + Math.sin(a) * 42;
    const on = open.includes(id);
    const col = on ? REGION_COLOR[id] : LOCKED_COLOR;
    if (on) glow(ctx, px, py, 20, col, 0.6);
    ctx.beginPath();
    ctx.ellipse(px, py, 13, 8, 0, 0, TAU);
    ctx.fillStyle = on ? rgba(col, 0.35) : "rgba(60,60,60,0.35)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = col;
    ctx.stroke();
  });
}

/** 傳送陣的中央晶柱（1×2 格畫布，傳送石那一格是下面那格）。 */
export function drawPortalPillar(ctx: Ctx): void {
  const cx = U / 2;
  const cy = U * 1.5;
  shadow(ctx, cx + 4, cy + 16, 16, 5, 0.35);
  glow(ctx, cx, cy - 16, 30, "rgba(143,123,255,0.9)", 0.55);
  ctx.beginPath();
  ctx.moveTo(cx - 9, cy + 14);
  ctx.lineTo(cx - 10, cy - 20);
  ctx.lineTo(cx, cy - 40);
  ctx.lineTo(cx + 10, cy - 20);
  ctx.lineTo(cx + 9, cy + 14);
  ctx.closePath();
  ctx.fillStyle = K.crystal;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.6)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(cx - 3, cy + 8);
  ctx.lineTo(cx - 2, cy - 30);
  ctx.stroke();
}

/**
 * 五面區旗的位置（相對傳送石，格）：外圈，和光圈同一個順序（正北起順時針）。只畫、不佔格；
 * 主城的格子：(0,−2)＝[15,9]、(3,−1)＝[18,10]、(2,2)＝[17,13]、(−2,2)＝[13,13]、(−3,−1)＝[12,10]，都是廣場的石板。
 */
export const BANNER_OFFSETS: readonly (readonly [number, number])[] = [
  [0, -2],
  [3, -1],
  [2, 2],
  [-2, 2],
  [-3, -1],
];

/** 區旗（1×2 格畫布，旗杆立在下面那格的中央）。 */
export function drawBanner(ctx: Ctx, region: CapitalRegion): void {
  const x = U / 2;
  const foot = U * 2 - 8;
  shadow(ctx, x + 3, foot, 8, 3, 0.3);
  box(ctx, x - 2, foot - 48, 4, 48, "#6a5a4a", OUT, 1.2, 1);
  dot(ctx, x, foot - 48, 3, K.gold);
  ctx.beginPath();
  ctx.moveTo(x + 2, foot - 44);
  ctx.lineTo(x + 20, foot - 44);
  ctx.lineTo(x + 20, foot - 22);
  ctx.lineTo(x + 11, foot - 27);
  ctx.lineTo(x + 2, foot - 22);
  ctx.closePath();
  ctx.fillStyle = REGION_COLOR[region];
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

// ---------------- 街景物件（物件的 look；畫布 1×2 格，下面那格是物件所在格）----------------

/** 源晶燈：石座加發光晶石。 */
export function drawCrystalLamp(ctx: Ctx): void {
  const y = U;
  const cx = U / 2;
  shadow(ctx, cx + 3, y + U * 0.84, 13, 4);
  box(ctx, cx - 11, y + 32, 22, 12, K.stoneD, OUT, 1.6, 2);
  box(ctx, cx - 5, y + 8, 10, 26, K.stone, OUT, 1.5, 2);
  ctx.fillStyle = K.gold;
  ctx.fillRect(cx - 5, y + 8, 10, 3);
  glow(ctx, cx, y - 4, 22, "rgba(143,123,255,0.9)", 0.7);
  ctx.beginPath();
  ctx.moveTo(cx, y - 20);
  ctx.lineTo(cx + 8, y - 4);
  ctx.lineTo(cx, y + 8);
  ctx.lineTo(cx - 8, y - 4);
  ctx.closePath();
  ctx.fillStyle = K.crystal;
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  dot(ctx, cx - 2, y - 7, 2, "#ffffff");
}

/** 各區紋章（畫在石碑上的圓章內）：晶冠＝晶石、雲嶺＝雲上的山、樞市＝符文圈、灰燼＝火焰、霜潮＝雪花。不認得的區＝空章。 */
function emblem(ctx: Ctx, cx: number, cy: number, region: string): void {
  const col = regionColor(region);
  ctx.beginPath();
  ctx.arc(cx, cy, 10, 0, TAU);
  ctx.fillStyle = "#3a3450";
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = K.gold;
  ctx.stroke();
  ctx.fillStyle = col;
  ctx.strokeStyle = col;
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  switch (region) {
    case "crystal_crown":
      ctx.moveTo(cx, cy - 7);
      ctx.lineTo(cx + 5, cy);
      ctx.lineTo(cx, cy + 7);
      ctx.lineTo(cx - 5, cy);
      ctx.closePath();
      ctx.fill();
      return;
    case "cloud_ridge":
      ctx.moveTo(cx - 7, cy + 4);
      ctx.lineTo(cx - 2, cy - 5);
      ctx.lineTo(cx + 1, cy);
      ctx.lineTo(cx + 3, cy - 3);
      ctx.lineTo(cx + 7, cy + 4);
      ctx.closePath();
      ctx.fill();
      return;
    case "arcane_hub":
      ctx.arc(cx, cy, 6, 0, TAU);
      ctx.stroke();
      for (let k = 0; k < 4; k++) dot(ctx, cx + Math.cos((k * TAU) / 4) * 6, cy + Math.sin((k * TAU) / 4) * 6, 1.8, col);
      return;
    case "ashen_waste":
      ctx.moveTo(cx, cy - 7);
      ctx.quadraticCurveTo(cx + 7, cy, cx, cy + 6);
      ctx.quadraticCurveTo(cx - 7, cy, cx, cy - 7);
      ctx.fill();
      return;
    case "frost_tide":
      for (let k = 0; k < 3; k++) {
        const a = (k * Math.PI) / 3;
        ctx.moveTo(cx - Math.cos(a) * 7, cy - Math.sin(a) * 7);
        ctx.lineTo(cx + Math.cos(a) * 7, cy + Math.sin(a) * 7);
      }
      ctx.stroke();
      return;
    default:
      return;
  }
}

/** 橋頭石碑：圓頂石碑、金色頂邊、中央刻該區紋章（`region` ＝ 同一格情境物件的 `stele_region`）。 */
export function drawStele(ctx: Ctx, region: string): void {
  const y = U;
  const cx = U / 2;
  shadow(ctx, cx + 4, y + U * 0.84, 17, 5);
  box(ctx, cx - 16, y + 34, 32, 10, K.stoneD, OUT, 1.6, 2); // 碑座
  ctx.beginPath();
  ctx.moveTo(cx - 12, y + 36);
  ctx.lineTo(cx - 12, y - 6);
  ctx.quadraticCurveTo(cx, y - 18, cx + 12, y - 6);
  ctx.lineTo(cx + 12, y + 36);
  ctx.closePath();
  ctx.fillStyle = K.stone;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = K.gold;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx - 9, y - 6);
  ctx.quadraticCurveTo(cx, y - 14, cx + 9, y - 6);
  ctx.stroke();
  emblem(ctx, cx, y + 8, region);
  ctx.strokeStyle = "rgba(120,100,70,0.5)"; // 刻痕（不寫字）
  ctx.lineWidth = 1;
  for (const k of [24, 29]) {
    ctx.beginPath();
    ctx.moveTo(cx - 7, y + k);
    ctx.lineTo(cx + 7, y + k);
    ctx.stroke();
  }
}

/** 浮橋通往的地圖邊（橋面在哪一邊的邊緣）。 */
export type BridgeSide = "n" | "e" | "s" | "w";

/**
 * 浮橋（斷在雲上）：木板橋面加兩側的繩欄，往地圖邊那一端淡進雲裡。
 * `side` ＝ 橋往哪一邊；`railL`／`railR` ＝ 往外看時左／右邊要不要畫繩欄（鄰格也是浮橋就不畫，接成一座寬橋）。
 */
export function drawSkyBridge(ctx: Ctx, side: BridgeSide, railL: boolean, railR: boolean): void {
  const angle = { n: 0, e: Math.PI / 2, s: Math.PI, w: -Math.PI / 2 }[side];
  ctx.save();
  ctx.translate(U / 2, U * 1.5);
  ctx.rotate(angle);
  const h = U / 2;
  // 橋面（往外＝ −y）
  ctx.fillStyle = "#8a6440";
  ctx.fillRect(-h + 4, -h, U - 8, U);
  ctx.strokeStyle = "#4b2f15";
  ctx.lineWidth = 1.4;
  for (let y = -h + 6; y < h; y += 8) {
    ctx.beginPath();
    ctx.moveTo(-h + 4, y);
    ctx.lineTo(h - 4, y);
    ctx.stroke();
  }
  for (const [on, x] of [
    [railL, -h + 5],
    [railR, h - 5],
  ] as const) {
    if (!on) continue;
    ctx.strokeStyle = "#5a4030";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, h);
    ctx.lineTo(x, -h);
    ctx.stroke();
    box(ctx, x - 2.5, h - 14, 5, 12, "#6a4a2a", OUT, 1.2, 1);
  }
  // 斷在雲上：外端的雲
  const g = ctx.createLinearGradient(0, -h, 0, -h + 22);
  g.addColorStop(0, "rgba(240,244,250,0.95)");
  g.addColorStop(1, "rgba(240,244,250,0)");
  ctx.fillStyle = g;
  ctx.fillRect(-h, -h, U, 22);
  for (const [dx, r] of [
    [-12, 9],
    [2, 11],
    [15, 8],
  ] as const) {
    ctx.beginPath();
    ctx.arc(dx, -h + 2, r, 0, TAU);
    ctx.fillStyle = "rgba(246,248,252,0.85)";
    ctx.fill();
  }
  ctx.restore();
}
