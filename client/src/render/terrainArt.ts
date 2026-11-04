// 地形、表面、高度的程式繪製（Phase 3-16a；移植自美術 PM 樣張 docs/art/sample/procedural.js）。
// 每個格子畫成一張離屏貼圖（座標以 ART_T ＝ 52 的虛擬格為單位，快取時再縮放到 TILE_SIZE）。
// 圖層順序（移植需求第 2 節）：地形 → 高度明暗 → 表面 → 格線。
// 崖面、描邊與抬高位移（3-19 整格抬高）由 Pixi 另畫（render/heightArt.ts），不在貼圖裡。
// 新地形、新表面沒有畫法時有預設，不會出錯。
import { PAL } from "./artPalette";
import { numToHex, rgba, shade } from "./color";
import { flame, roundRect, TAU, type Ctx } from "./artDraw";
import { rng } from "./artRandom";
import { ARCANE_TERRAIN } from "./arcaneTerrain";
import { ASHEN_TERRAIN } from "./ashenTerrain";
import { CLOUD_LOOK_TERRAIN, CLOUD_TERRAIN } from "./cloudRidgeTerrain";
import { CAPITAL_INLAY, crystalTerrain } from "./crystalTerrain";
import { FROST_TERRAIN } from "./frostTerrain";
import { pickThemed, themeKey, waterColorOf, type ArtTheme, type LookTable, type RegionTable } from "./regionArt";
import { drawCloudSea, drawLavaBase, drawWaterFill } from "./hazardTerrainArt";
import { ALL_CORNERS, blobPath, blobShape, strokeBlobEdges, type BlobShape, type Corners } from "./surfaceBlobs";

/** 繪圖用的虛擬格邊長（樣張的尺寸；貼圖產生時再縮放到實際格子大小）。 */
export const ART_T = 52;
const T = ART_T;

/** 鄰格四個方向的旗標。 */
export interface Sides {
  n: boolean;
  s: boolean;
  w: boolean;
  e: boolean;
}

/** 一個格子的繪圖規格：純資料，決定貼圖的內容與快取鍵。 */
export interface TileArtSpec extends ArtTheme {
  terrain: string;
  x: number;
  y: number;
  height: number;
  /** 表面 ID；沒有表面為 "none"。 */
  surface: string;
  /** 該方向的鄰格也是同一種表面（連成一片）。 */
  surfSame: Sides;
  /** 四個斜鄰是不是同一種表面（6A-4a 併塊的內凹角）；沒給視為同種（角補滿）。 */
  surfDiag?: Corners;
  /** 該方向的鄰格不是同一種地形（畫崖緣、冰緣）；地圖外視為同種。 */
  lip: Sides;
  /** 牆：南鄰不是牆就畫立面。 */
  wallFace: boolean;
  /** 不可站立（牆、深淵、岩漿、冰窟）：不做高度明暗。 */
  blocked: boolean;
  /** 未知地形的色調（0xRRGGBB）；已知地形為 null。 */
  tint: number | null;
}

const flags = (s: Sides): string => `${+s.n}${+s.s}${+s.w}${+s.e}`;
const diagFlags = (c: Corners): string => `${+c.nw}${+c.ne}${+c.se}${+c.sw}`;

/** 貼圖快取鍵：規格相同 ＝ 圖相同。 */
export function tileArtKey(s: TileArtSpec): string {
  return [
    s.terrain,
    s.x,
    s.y,
    s.height,
    s.surface,
    flags(s.surfSame),
    diagFlags(s.surfDiag ?? ALL_CORNERS),
    flags(s.lip),
    +s.wallFace,
    +s.blocked,
    s.tint ?? "-",
    themeKey(s),
  ].join("|");
}

// ---- 地形 ----

type TerrainDrawer = (ctx: Ctx, s: TileArtSpec) => void;

function drawStone(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 1);
  ctx.fillStyle = PAL.stoneGap;
  ctx.fillRect(0, 0, T, T);
  const slabs: Array<[number, number, number, number]> = [];
  const splitV = r() < 0.5;
  const cut = 0.35 + r() * 0.3;
  if (splitV) slabs.push([0, 0, T * cut, T], [T * cut, 0, T * (1 - cut), T]);
  else slabs.push([0, 0, T, T * cut], [0, T * cut, T, T * (1 - cut)]);
  if (r() < 0.6) {
    const [sx, sy, sw, sh] = slabs.pop() as [number, number, number, number];
    const c2 = 0.4 + r() * 0.2;
    if (splitV) slabs.push([sx, sy, sw, sh * c2], [sx, sy + sh * c2, sw, sh * (1 - c2)]);
    else slabs.push([sx, sy, sw * c2, sh], [sx + sw * c2, sy, sw * (1 - c2), sh]);
  }
  for (const [sx, sy, sw, sh] of slabs) {
    ctx.fillStyle = shade(PAL.stone, 0.94 + r() * 0.12);
    roundRect(ctx, sx + 1.5, sy + 1.5, sw - 3, sh - 3, 3);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.10)";
    ctx.fillRect(sx + 3, sy + 2, sw - 6, 2);
  }
  if (r() < 0.35) {
    ctx.strokeStyle = "rgba(60,56,50,0.55)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    let px = T * (0.2 + r() * 0.6);
    let py = T * (0.2 + r() * 0.2);
    ctx.moveTo(px, py);
    for (let i = 0; i < 3; i++) {
      px += (r() - 0.5) * 12;
      py += 5 + r() * 6;
      ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
}

function drawGrass(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 2);
  ctx.fillStyle = shade(PAL.grass, 0.96 + r() * 0.08);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
    ctx.fill();
  }
  const n = 6 + Math.floor(r() * 4);
  ctx.lineWidth = 1.6;
  ctx.lineCap = "round";
  for (let i = 0; i < n; i++) {
    const gx = 5 + r() * (T - 10);
    const gy = 7 + r() * (T - 12);
    ctx.strokeStyle = r() < 0.6 ? PAL.grassLight : PAL.grassDark;
    ctx.beginPath();
    ctx.moveTo(gx - 3, gy - 4);
    ctx.lineTo(gx, gy);
    ctx.lineTo(gx + 3, gy - 5);
    ctx.moveTo(gx, gy);
    ctx.lineTo(gx, gy - 6);
    ctx.stroke();
  }
  if (r() < 0.3) {
    ctx.fillStyle = r() < 0.5 ? "#f3e27a" : "#f0f0f0";
    ctx.beginPath();
    ctx.arc(6 + r() * (T - 12), 6 + r() * (T - 12), 2, 0, TAU);
    ctx.fill();
  }
}

function drawDirt(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 3);
  ctx.fillStyle = shade(PAL.dirt, 0.95 + r() * 0.1);
  ctx.fillRect(0, 0, T, T);
  const n = 5 + Math.floor(r() * 5);
  for (let i = 0; i < n; i++) {
    ctx.fillStyle = r() < 0.5 ? PAL.dirtDark : PAL.dirtLight;
    ctx.beginPath();
    ctx.ellipse(4 + r() * (T - 8), 4 + r() * (T - 8), 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU, 0, TAU);
    ctx.fill();
  }
  ctx.strokeStyle = "rgba(90,66,40,0.35)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const yy = T * (0.3 + r() * 0.4);
  ctx.moveTo(0, yy);
  ctx.bezierCurveTo(T * 0.3, yy - 6, T * 0.6, yy + 6, T, yy - 2);
  ctx.stroke();
}

function drawWall(ctx: Ctx, s: TileArtSpec): void {
  ctx.fillStyle = PAL.wallTop;
  ctx.fillRect(0, 0, T, T);
  const r = rng(s.x, s.y, 4);
  ctx.strokeStyle = PAL.wallLine;
  ctx.lineWidth = 2;
  const rows = 4;
  const rh = T / rows;
  for (let i = 0; i < rows; i++) {
    ctx.beginPath();
    ctx.moveTo(0, i * rh);
    ctx.lineTo(T, i * rh);
    ctx.stroke();
    const off = i % 2 === 0 ? 0 : T / 4;
    for (let bx = off; bx < T; bx += T / 2) {
      ctx.beginPath();
      ctx.moveTo(bx, i * rh);
      ctx.lineTo(bx, (i + 1) * rh);
      ctx.stroke();
    }
  }
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = `rgba(255,255,255,${0.04 + r() * 0.05})`;
    ctx.fillRect(Math.floor(r() * 2) * (T / 2) + 2, Math.floor(r() * rows) * rh + 2, T / 2 - 4, rh - 4);
  }
  if (s.wallFace) {
    ctx.fillStyle = PAL.wallFace;
    ctx.fillRect(0, T - 9, T, 9);
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.fillRect(0, T - 9, T, 1.5);
  }
}

function jag(ctx: Ctx, r: () => number, p: [number, number, number, number], n: [number, number]): void {
  const [x0, y0, x1, y1] = p;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  const steps = 6;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const d = 3 + r() * 5;
    ctx.lineTo(x0 + (x1 - x0) * t + n[0] * d, y0 + (y1 - y0) * t + n[1] * d);
  }
  ctx.lineTo(x1, y1);
  ctx.closePath();
  ctx.fill();
}

/** 雲海／深淵（6V-2）：白雲團鋪滿格子、邊緣羽化、底下透淡藍（`hazardTerrainArt.drawCloudSea`）；崖緣照舊。 */
function drawChasm(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 5);
  drawCloudSea(ctx, s, 5);
  ctx.fillStyle = PAL.chasmLip;
  if (s.lip.n) {
    jag(ctx, r, [0, 0, T, 0], [0, 1]);
    const gg = ctx.createLinearGradient(0, 0, 0, 16);
    gg.addColorStop(0, "rgba(70,64,80,0.9)");
    gg.addColorStop(1, "rgba(70,64,80,0)");
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, 16);
    ctx.fillStyle = PAL.chasmLip;
  }
  if (s.lip.s) jag(ctx, r, [0, T, T, T], [0, -1]);
  if (s.lip.w) jag(ctx, r, [0, 0, 0, T], [1, 0]);
  if (s.lip.e) jag(ctx, r, [T, 0, T, T], [-1, 0]);
}

/** 熔岩（6V-2）：橘紅發光、黑色岩殼裂紋、靠岸一圈冷卻黑殼（`hazardTerrainArt.drawLavaBase`）；岩殼慢速漂移在 surfaceAnim。 */
function drawLava(ctx: Ctx, s: TileArtSpec): void {
  drawLavaBase(ctx, s, 6);
}

function drawIceHole(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 7);
  ctx.fillStyle = PAL.deep;
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = rgba(PAL.deepLight, 0.6);
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  for (let i = 0; i < 3; i++) {
    const wx = 6 + r() * (T - 20);
    const wy = 8 + r() * (T - 16);
    ctx.beginPath();
    ctx.moveTo(wx, wy);
    ctx.quadraticCurveTo(wx + 4, wy - 3, wx + 8, wy);
    ctx.quadraticCurveTo(wx + 12, wy + 3, wx + 16, wy);
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(220,240,255,0.55)";
  if (s.lip.n) ctx.fillRect(0, 0, T, 4);
  if (s.lip.w) ctx.fillRect(0, 0, 4, T);
  if (s.lip.e) ctx.fillRect(T - 4, 0, 4, T);
  if (s.lip.s) ctx.fillRect(0, T - 4, T, 4);
}

/** 有專屬畫法的地形。 */
export const TERRAIN_DRAW: Readonly<Record<string, TerrainDrawer>> = {
  stone: drawStone,
  grass: drawGrass,
  dirt: drawDirt,
  wall: drawWall,
  chasm: drawChasm,
  lava: drawLava,
  ice_hole: drawIceHole,
};

/** 各區的地形畫法（區域 ID → 地形 ID → 畫法）；預設區不在表內。雲嶺（3-37b）、灰燼荒原與晶冠點綴（5A-ART6）、魔導樞市與霜潮海境（5A-ART7）已加入。 */
export const REGION_TERRAIN_DRAW: RegionTable<TerrainDrawer> = {
  cloud_ridge: CLOUD_TERRAIN,
  ashen_waste: ASHEN_TERRAIN,
  crystal_crown: crystalTerrain({ stone: drawStone, chasm: drawChasm }),
  arcane_hub: ARCANE_TERRAIN,
  frost_tide: FROST_TERRAIN,
  // 6D-ART2：主城的地面是晶冠的白石板、偶有金色嵌線（只換石板；其他地形照預設）
  // 6Q-1：主城嵌線降到約 1/12 格、透明度降低（CAPITAL_INLAY）
  capital: { stone: crystalTerrain({ stone: drawStone, chasm: drawChasm }, CAPITAL_INLAY).stone! },
};

/** `look` 覆寫的地形畫法（`"wall=canyon_rock"` → 地形 ID → 畫法）。 */
export const LOOK_TERRAIN_DRAW: LookTable<TerrainDrawer> = CLOUD_LOOK_TERRAIN;

export function hasTerrainArt(terrain: string): boolean {
  return terrain in TERRAIN_DRAW;
}

// ---- 高度 ----

/** 頂面亮度（3-19 定案第 4 條）：每高一階疊一層暖白。 */
function heightLight(ctx: Ctx, h: number): void {
  if (h <= 0) return;
  ctx.fillStyle = `rgba(255,246,220,${0.1 * h})`;
  ctx.fillRect(0, 0, T, T);
}

/// ---- 表面（6A-4a 地表併塊）：同種表面的相鄰格併成一塊圓角有機形狀（`surfaceBlobs.ts`），不畫成方塊 ----
// 每種表面：填色 → 紋理（裁在形狀內）→ 外緣（只描露在外面的邊，接縫不描）。形狀與紋理都只看格子座標雜湊。

/** 表面外緣的筆觸：顏色、粗細與可選的光暈（火）。光暈只在格子貼圖內，不會畫到別格。 */
interface SurfaceEdge {
  color: string;
  width: number;
  glow?: string;
}

/** 一種表面的畫法：底色、紋理（已裁在形狀內）、外緣。 */
interface SurfaceStyle {
  fill: (s: TileArtSpec) => string;
  texture?: (ctx: Ctx, s: TileArtSpec, r: () => number) => void;
  edge: SurfaceEdge;
}

/** 冰：反光斜線＋細裂紋。 */
function iceTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  const ox = (r() - 0.5) * 10;
  const oy = (r() - 0.5) * 8;
  ctx.strokeStyle = "rgba(255,255,255,0.9)";
  ctx.lineWidth = 2;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(14 + ox, 20 + oy);
  ctx.lineTo(24 + ox, 12 + oy);
  ctx.moveTo(20 + ox, 26 + oy);
  ctx.lineTo(34 + ox, 14 + oy);
  ctx.stroke();
  ctx.strokeStyle = "rgba(90,138,168,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const cx = T * (0.45 + r() * 0.2);
  const cy = T * (0.5 + r() * 0.2);
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + 8, cy + 10);
  ctx.lineTo(cx + 14, cy + 6);
  ctx.moveTo(cx + 8, cy + 10);
  ctx.lineTo(cx + 4 + r() * 6, cy + 16);
  ctx.stroke();
}

/** 油：虹彩亮斑＋一抹白色油光。 */
function oilTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  const cx = T * (0.3 + r() * 0.3);
  const cy = T * (0.3 + r() * 0.3);
  const g = ctx.createLinearGradient(cx - 12, cy - 6, cx + 12, cy + 6);
  g.addColorStop(0, "rgba(160,90,220,0.4)");
  g.addColorStop(0.5, "rgba(80,200,160,0.32)");
  g.addColorStop(1, "rgba(230,200,80,0.3)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(cx, cy, 11, 4.5, -0.4 + (r() - 0.5) * 0.6, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,0.25)";
  ctx.beginPath();
  ctx.ellipse(cx + 11, cy + 11, 6, 2.5, -0.4, 0, TAU);
  ctx.fill();
}

/** 火：中央光暈＋三簇火苗。 */
function fireTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  const glow = ctx.createRadialGradient(T / 2, T * 0.6, 2, T / 2, T * 0.6, T * 0.6);
  glow.addColorStop(0, "rgba(255,200,60,0.8)");
  glow.addColorStop(1, "rgba(255,90,20,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) flame(ctx, 10 + i * 15 + r() * 6, T - 8 - r() * 8, 9 + r() * 5);
}

function poisonTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  ctx.strokeStyle = "rgba(220,255,180,0.8)";
  ctx.fillStyle = "rgba(160,230,100,0.6)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.arc(8 + r() * (T - 16), 8 + r() * (T - 16), 2 + r() * 3, 0, TAU);
    ctx.fill();
    ctx.stroke();
  }
}

/** 煙霧：幾個較大的雲團（裁在形狀內）。 */
function smokeTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  const n = 4 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    ctx.fillStyle = i % 3 === 2 ? "rgba(150,155,170,0.22)" : "rgba(235,238,245,0.38)";
    ctx.beginPath();
    ctx.arc(4 + r() * (T - 8), 4 + r() * (T - 8), 9 + r() * 7, 0, TAU);
    ctx.fill();
  }
}

function holyTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  const g = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * 0.55);
  g.addColorStop(0, "rgba(255,255,240,0.55)");
  g.addColorStop(1, "rgba(255,255,240,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = "rgba(255,255,255,0.9)";
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  for (let i = 0; i < 3; i++) {
    const cx = 10 + r() * (T - 20);
    const cy = 10 + r() * (T - 20);
    const k = 3 + r() * 3;
    ctx.beginPath();
    ctx.moveTo(cx - k, cy);
    ctx.lineTo(cx + k, cy);
    ctx.moveTo(cx, cy - k);
    ctx.lineTo(cx, cy + k);
    ctx.stroke();
  }
}

/** 黑暗：深紫徑向暈染（中心較深，不用橢圓斑塊避免和油混淆）＋2–3 道捲曲煙絲。 */
function darknessTexture(ctx: Ctx, _s: TileArtSpec, r: () => number): void {
  const g = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * 0.62);
  g.addColorStop(0, rgba(PAL.darkness, 0.6));
  g.addColorStop(1, rgba(PAL.darkness, 0));
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = "rgba(190,130,240,0.5)";
  ctx.lineWidth = 1.4;
  ctx.lineCap = "round";
  const wisps = 2 + Math.floor(r() * 2);
  for (let i = 0; i < wisps; i++) {
    const x0 = 8 + r() * (T - 16);
    const y0 = T - 6 - r() * 10;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.bezierCurveTo(x0 + 10, y0 - 10, x0 - 12, y0 - 18, x0 + 4, y0 - 26 - r() * 8);
    ctx.bezierCurveTo(x0 + 10, y0 - 30, x0 + 12, y0 - 24, x0 + 6, y0 - 22);
    ctx.stroke();
  }
}

const SURFACE_STYLE: Readonly<Record<string, SurfaceStyle>> = {
  // 水（6V-2 起由 `hazardTerrainArt.drawWaterFill` 畫，不走併塊）：這一項只讓 `hasSurfaceArt` 認得
  water: { fill: (s) => rgba(waterColorOf(s, PAL.water), 0.86), edge: { color: "rgba(220,240,255,0.55)", width: 1.2 } },
  ice: { fill: () => rgba(PAL.ice, 0.88), texture: iceTexture, edge: { color: "#ffffff", width: 2.2 } },
  oil: { fill: () => rgba(PAL.oil, 0.88), texture: oilTexture, edge: { color: "rgba(200,170,90,0.85)", width: 2 } },
  fire: { fill: () => "rgba(70,26,10,0.7)", texture: fireTexture, edge: { color: "rgba(255,120,40,0.9)", width: 2, glow: "#ff8a2a" } },
  poison: { fill: () => rgba(PAL.poison, 0.7), texture: poisonTexture, edge: { color: "rgba(190,240,140,0.85)", width: 1.6 } },
  // ---- 樣張沒有的表面：沿用原本的顏色，用同一套併塊畫法 ----
  smoke: { fill: () => rgba(PAL.smoke, 0.35), texture: smokeTexture, edge: { color: "rgba(235,238,245,0.6)", width: 1.4 } },
  holy: { fill: () => rgba(PAL.holy, 0.5), texture: holyTexture, edge: { color: "rgba(255,245,200,0.9)", width: 1.6 } },
  darkness: { fill: () => rgba(PAL.darkness, 0.55), texture: darknessTexture, edge: { color: "rgba(150,90,200,0.75)", width: 1.6 } },
};

/** 未知表面：灰色併塊、沒有紋理。 */
const UNKNOWN_SURFACE: SurfaceStyle = { fill: () => rgba("#9a9aa8", 0.5), edge: { color: "rgba(210,210,220,0.6)", width: 1.4 } };

/** 這一格表面的形狀（四鄰、斜鄰的同種旗標 → 併塊）。 */
export function surfaceShape(s: TileArtSpec): BlobShape {
  return blobShape(s.x, s.y, s.surfSame, s.surfDiag ?? ALL_CORNERS, T);
}

function drawSurface(ctx: Ctx, s: TileArtSpec): void {
  if (s.surface === "water") {
    // 6V-2：水面填滿格子、岸邊濕痕、細反光線；水色依區域（`look.water_tint` 優先）
    drawWaterFill(ctx, s, waterColorOf(s, PAL.water));
    return;
  }
  const r = rng(s.x, s.y, 20);
  const style = SURFACE_STYLE[s.surface] ?? UNKNOWN_SURFACE;
  const shape = surfaceShape(s);
  ctx.save();
  ctx.beginPath();
  blobPath(ctx, shape);
  ctx.fillStyle = style.fill(s);
  ctx.fill();
  if (style.texture !== undefined) {
    ctx.clip();
    style.texture(ctx, s, r);
  }
  ctx.restore();
  ctx.save();
  ctx.strokeStyle = style.edge.color;
  ctx.lineWidth = style.edge.width;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  if (style.edge.glow !== undefined) {
    ctx.shadowColor = style.edge.glow;
    ctx.shadowBlur = 6;
  }
  strokeBlobEdges(ctx, shape);
  ctx.restore();
}

export function hasSurfaceArt(surface: string): boolean {
  return surface in SURFACE_STYLE;
}

/** 畫一個格子（座標以 ART_T 為單位；呼叫端負責縮放與裁切）。 */
export function drawTile(ctx: Ctx, s: TileArtSpec): void {
  const draw = pickThemed(s, s.terrain, REGION_TERRAIN_DRAW, LOOK_TERRAIN_DRAW) ?? TERRAIN_DRAW[s.terrain] ?? drawStone;
  draw(ctx, s);
  if (s.tint !== null) {
    // 未知地形：石地畫法，再依 glossary 的地形色調上色
    ctx.fillStyle = rgba(numToHex(s.tint), 0.3);
    ctx.fillRect(0, 0, T, T);
  }
  if (!s.blocked) heightLight(ctx, s.height);
  if (s.surface !== "none") drawSurface(ctx, s);
  // 6A-4a（D 版待機）：不畫格線；選移動、選技能時的格子浮出由高亮層另畫
}
