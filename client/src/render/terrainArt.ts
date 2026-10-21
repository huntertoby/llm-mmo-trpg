// 地形、表面、高度的程式繪製（Phase 3-16a；移植自美術 PM 樣張 docs/art/sample/procedural.js）。
// 每個格子畫成一張離屏貼圖（座標以 ART_T ＝ 52 的虛擬格為單位，快取時再縮放到 TILE_SIZE）。
// 圖層順序（移植需求第 2 節）：地形 → 高度明暗 → 表面 → 陰影 → 崖面 → 格線。
// 新地形、新表面沒有畫法時有預設，不會出錯。
import { numToHex, PAL, rgba, shade } from "./artPalette";
import { flame, roundRect, TAU, type Ctx } from "./artDraw";
import { rng } from "./artRandom";

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
export interface TileArtSpec {
  terrain: string;
  x: number;
  y: number;
  height: number;
  /** 表面 ID；沒有表面為 "none"。 */
  surface: string;
  /** 該方向的鄰格也是同一種表面（連成一片）。 */
  surfSame: Sides;
  /** 該方向的鄰格不是同一種地形（畫崖緣、冰緣）；地圖外視為同種。 */
  lip: Sides;
  /** 牆：南鄰不是牆就畫立面。 */
  wallFace: boolean;
  /** 南側崖面高度（虛擬像素）；0 ＝ 沒有。 */
  drop: number;
  /** 較高的北鄰、西鄰投在本格的陰影強度（高度差）；0 ＝ 沒有。 */
  shadowN: number;
  shadowW: number;
  /** 西、東鄰比本格低（畫細邊線）。 */
  lowerW: boolean;
  lowerE: boolean;
  /** 不可站立（牆、深淵、岩漿、冰窟）：不做高度明暗。 */
  blocked: boolean;
  /** 未知地形的色調（0xRRGGBB）；已知地形為 null。 */
  tint: number | null;
}

const flags = (s: Sides): string => `${+s.n}${+s.s}${+s.w}${+s.e}`;

/** 貼圖快取鍵：規格相同 ＝ 圖相同。 */
export function tileArtKey(s: TileArtSpec): string {
  return [
    s.terrain,
    s.x,
    s.y,
    s.height,
    s.surface,
    flags(s.surfSame),
    flags(s.lip),
    +s.wallFace,
    s.drop,
    s.shadowN,
    s.shadowW,
    +s.lowerW,
    +s.lowerE,
    +s.blocked,
    s.tint ?? "-",
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

function drawChasm(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 5);
  const g = ctx.createLinearGradient(0, 0, 0, T);
  g.addColorStop(0, "#05050a");
  g.addColorStop(1, PAL.chasm);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 4; i++) {
    ctx.fillStyle = `rgba(140,130,200,${0.15 + r() * 0.2})`;
    ctx.fillRect(r() * T, r() * T, 1.5, 1.5);
  }
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

function drawLava(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 6);
  ctx.fillStyle = PAL.lava;
  ctx.fillRect(0, 0, T, T);
  const glow = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * 0.7);
  glow.addColorStop(0, "rgba(255,210,80,0.55)");
  glow.addColorStop(1, "rgba(255,210,80,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, T, T);
  const n = 4 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    const cx = r() * T;
    const cy = r() * T;
    const rad = 5 + r() * 7;
    ctx.fillStyle = PAL.lavaCrust;
    ctx.beginPath();
    for (let k = 0; k < 7; k++) {
      const a = (k / 7) * TAU;
      const rr = rad * (0.7 + r() * 0.4);
      const px = cx + Math.cos(a) * rr;
      const py = cy + Math.sin(a) * rr;
      if (k === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "rgba(255,208,74,0.5)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
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

export function hasTerrainArt(terrain: string): boolean {
  return terrain in TERRAIN_DRAW;
}

// ---- 高度 ----

function heightLight(ctx: Ctx, h: number): void {
  if (h <= 0) return;
  ctx.fillStyle = `rgba(255,248,230,${0.07 * h})`;
  ctx.fillRect(0, 0, T, T);
}

/** 南鄰較低：在本格底部畫立面（高度差 × 5 px）；左右較低鄰格畫細邊線。 */
function cliffs(ctx: Ctx, s: TileArtSpec): void {
  if (s.drop > 0) {
    const d = s.drop;
    const levels = Math.max(1, Math.round(d / 5));
    ctx.fillStyle = PAL.cliff;
    ctx.fillRect(0, T - d, T, d);
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    for (let i = 0; i < levels; i++) ctx.fillRect(0, T - d + i * 5, T, 1);
    ctx.fillStyle = "rgba(255,255,255,0.25)";
    ctx.fillRect(0, T - d - 1, T, 1.5);
  }
  ctx.fillStyle = "rgba(40,30,20,0.45)";
  if (s.lowerW) ctx.fillRect(0, 0, 2, T);
  if (s.lowerE) ctx.fillRect(T - 2, 0, 2, T);
}

function castShadow(ctx: Ctx, s: TileArtSpec): void {
  if (s.shadowN > 0) {
    const len = 8 + s.shadowN * 4;
    const g = ctx.createLinearGradient(0, 0, 0, len);
    g.addColorStop(0, "rgba(0,0,0,0.35)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, T, len);
  }
  if (s.shadowW > 0) {
    const g = ctx.createLinearGradient(0, 0, 10, 0);
    g.addColorStop(0, "rgba(0,0,0,0.25)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 10, T);
  }
}

// ---- 表面：相鄰同種表面連成一片，不是一格一格的方塊 ----

function surfaceBlob(ctx: Ctx, s: TileArtSpec, color: string, alpha: number): void {
  const inset = 4;
  const l = s.surfSame.w ? 0 : inset;
  const t = s.surfSame.n ? 0 : inset;
  const rr = s.surfSame.e ? 0 : inset;
  const b = s.surfSame.s ? 0 : inset;
  ctx.fillStyle = rgba(color, alpha);
  ctx.beginPath();
  ctx.roundRect(l, t, T - l - rr, T - t - b, [
    l && t ? 12 : 0,
    rr && t ? 12 : 0,
    rr && b ? 12 : 0,
    l && b ? 12 : 0,
  ]);
  ctx.fill();
}

type SurfaceDrawer = (ctx: Ctx, s: TileArtSpec, r: () => number) => void;

const SURFACE_DRAW: Readonly<Record<string, SurfaceDrawer>> = {
  water(ctx, s, r) {
    surfaceBlob(ctx, s, PAL.water, 0.78);
    ctx.strokeStyle = "rgba(220,240,255,0.7)";
    ctx.lineWidth = 1.5;
    for (let i = 0; i < 2; i++) {
      const wx = 8 + r() * (T - 26);
      const wy = 12 + r() * (T - 22);
      ctx.beginPath();
      ctx.moveTo(wx, wy);
      ctx.quadraticCurveTo(wx + 5, wy - 4, wx + 10, wy);
      ctx.stroke();
    }
  },
  ice(ctx, s, r) {
    surfaceBlob(ctx, s, PAL.ice, 0.85);
    ctx.strokeStyle = "rgba(120,180,220,0.7)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    const cx = T * (0.3 + r() * 0.4);
    const cy = T * (0.3 + r() * 0.4);
    for (let i = 0; i < 4; i++) {
      const a = r() * TAU;
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(a) * 18, cy + Math.sin(a) * 18);
    }
    ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.9)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(10, T - 16);
    ctx.lineTo(18, T - 24);
    ctx.stroke();
  },
  oil(ctx, s, r) {
    surfaceBlob(ctx, s, PAL.oil, 0.85);
    const g = ctx.createLinearGradient(10, 10, 40, 30);
    g.addColorStop(0, "rgba(160,90,220,0.35)");
    g.addColorStop(0.5, "rgba(80,200,160,0.30)");
    g.addColorStop(1, "rgba(230,200,80,0.25)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(T * (0.35 + r() * 0.3), T * (0.35 + r() * 0.3), 12, 6, r() * TAU, 0, TAU);
    ctx.fill();
  },
  fire(ctx, s, r) {
    surfaceBlob(ctx, s, "#7a2a10", 0.6);
    const glow = ctx.createRadialGradient(T / 2, T * 0.6, 2, T / 2, T * 0.6, T * 0.6);
    glow.addColorStop(0, "rgba(255,200,60,0.8)");
    glow.addColorStop(1, "rgba(255,90,20,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, T, T);
    for (let i = 0; i < 3; i++) flame(ctx, 10 + i * 15 + r() * 6, T - 8 - r() * 8, 9 + r() * 5);
  },
  poison(ctx, s, r) {
    surfaceBlob(ctx, s, PAL.poison, 0.7);
    ctx.strokeStyle = "rgba(220,255,180,0.8)";
    ctx.fillStyle = "rgba(160,230,100,0.6)";
    ctx.lineWidth = 1;
    for (let i = 0; i < 4; i++) {
      ctx.beginPath();
      ctx.arc(8 + r() * (T - 16), 8 + r() * (T - 16), 2 + r() * 3, 0, TAU);
      ctx.fill();
      ctx.stroke();
    }
  },
  // ---- 樣張沒有的表面：依同一套規則補（連成一片的底色＋該表面的標誌紋理）----
  smoke(ctx, s, r) {
    // 白灰半透明底＋幾個較大的雲團（貼圖以格子為界，雲團貼著邊緣被裁切，看起來浮在地面上）
    surfaceBlob(ctx, s, PAL.smoke, 0.35);
    const n = 4 + Math.floor(r() * 3);
    for (let i = 0; i < n; i++) {
      ctx.fillStyle = i % 3 === 2 ? "rgba(150,155,170,0.22)" : "rgba(235,238,245,0.38)";
      ctx.beginPath();
      ctx.arc(4 + r() * (T - 8), 4 + r() * (T - 8), 9 + r() * 7, 0, TAU);
      ctx.fill();
    }
  },
  holy(ctx, s, r) {
    surfaceBlob(ctx, s, PAL.holy, 0.5);
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
  },
  darkness(ctx, _s, r) {
    // 深紫徑向暈染（中心較深，不用橢圓斑塊避免和油混淆）＋2–3 道捲曲煙絲
    const g = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * 0.62);
    g.addColorStop(0, rgba(PAL.darkness, 0.85));
    g.addColorStop(1, rgba(PAL.darkness, 0.12));
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
  },
};

function drawSurface(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 20);
  const draw = SURFACE_DRAW[s.surface];
  if (draw !== undefined) draw(ctx, s, r);
  else surfaceBlob(ctx, s, "#9a9aa8", 0.5); // 未知表面：灰色連成一片的底色
}

export function hasSurfaceArt(surface: string): boolean {
  return surface in SURFACE_DRAW;
}

/** 畫一個格子（座標以 ART_T 為單位；呼叫端負責縮放與裁切）。 */
export function drawTile(ctx: Ctx, s: TileArtSpec): void {
  const draw = TERRAIN_DRAW[s.terrain] ?? drawStone;
  draw(ctx, s);
  if (s.tint !== null) {
    // 未知地形：石地畫法，再依 glossary 的地形色調上色
    ctx.fillStyle = rgba(numToHex(s.tint), 0.3);
    ctx.fillRect(0, 0, T, T);
  }
  if (!s.blocked) heightLight(ctx, s.height);
  if (s.surface !== "none") drawSurface(ctx, s);
  castShadow(ctx, s);
  cliffs(ctx, s);
  // 極淡格線：讓地面連成一片又看得出格子
  ctx.strokeStyle = "rgba(0,0,0,0.14)";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, T - 1, T - 1);
}
