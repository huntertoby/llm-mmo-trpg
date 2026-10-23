// 第一區「雲嶺」的地形畫法（Phase 3-37b；docs/art/雲嶺移植需求.md 第 2、3 節；畫法移植自 docs/art/sample/realms.js）。
// 低彩度的青綠墨灰，只用朱紅與燈火暖黃當重點。座標以 52 的虛擬格為單位（同 terrainArt 的 ART_T）。
// 功能特徵不變：牆要比單位高、深淵與岩漿與冰窟要看得出致命（崖線、紅色、深色水）。
// 這個檔案不匯入 terrainArt 的值（避免循環匯入）；表由 terrainArt 組裝。
import { roundRect, TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./artPalette";
import { rng } from "./artRandom";
import type { TileArtSpec } from "./terrainArt";

const T = 52;

/** 雲嶺色票（需求第 2 節）。 */
export const CLOUD = {
  slate: "#7d8c84", // 青石（地板）
  ink: "#56645c", // 墨灰（接縫、陰影）
  moss: "#5a8a3a", // 苔
  bamboo: "#6aa84a", // 竹青
  bambooDark: "#4f8a3a",
  bambooNode: "#2f5a22",
  red: "#b8432f", // 朱紅
  redDark: "#8a2f20",
  tile: "#3c4a48", // 黛瓦
  mist: "#e8e8e0", // 霧白
  lamp: "#ffcf6a", // 燈火暖黃
  outline: "#1c1712",
} as const;

type TerrainDrawer = (ctx: Ctx, s: TileArtSpec) => void;

/** 青石板：2～4 塊一格，帶苔點。 */
function cloudStone(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 101);
  ctx.fillStyle = CLOUD.ink;
  ctx.fillRect(0, 0, T, T);
  const split = r() < 0.5;
  const blocks: ReadonlyArray<readonly [number, number, number, number]> = split
    ? [[0, 0, 0.55, 0.5], [0.55, 0, 0.45, 0.5], [0, 0.5, 1, 0.5]]
    : [[0, 0, 1, 0.45], [0, 0.45, 0.4, 0.55], [0.4, 0.45, 0.6, 0.55]];
  for (const [bx, by, bw, bh] of blocks) {
    ctx.fillStyle = shade(CLOUD.slate, 0.92 + r() * 0.16);
    roundRect(ctx, bx * T + 1.5, by * T + 1.5, bw * T - 3, bh * T - 3, 3);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.12)";
    ctx.fillRect(bx * T + 2, by * T + 2, bw * T - 4, 2);
  }
  if (r() < 0.45) {
    ctx.fillStyle = rgba(CLOUD.moss, 0.75);
    for (let i = 0; i < 4; i++) {
      ctx.beginPath();
      ctx.arc(r() * T, r() * T, 2 + r() * 3, 0, TAU);
      ctx.fill();
    }
  }
}

/** 偏青的草地：竹葉般細長的草葉。 */
function cloudGrass(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 102);
  ctx.fillStyle = shade("#689a70", 0.96 + r() * 0.08);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(232,232,224,0.07)" : "rgba(0,0,0,0.05)";
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
    ctx.fill();
  }
  const n = 6 + Math.floor(r() * 4);
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  for (let i = 0; i < n; i++) {
    const gx = 5 + r() * (T - 10);
    const gy = 8 + r() * (T - 13);
    ctx.strokeStyle = r() < 0.55 ? "#9ccf86" : CLOUD.bambooDark;
    ctx.beginPath();
    ctx.moveTo(gx, gy);
    ctx.quadraticCurveTo(gx - 1, gy - 5, gx - 4, gy - 8);
    ctx.moveTo(gx, gy);
    ctx.quadraticCurveTo(gx + 1, gy - 5, gx + 4, gy - 9);
    ctx.stroke();
  }
}

/** 黃土小徑。 */
function cloudDirt(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 103);
  ctx.fillStyle = shade("#a99560", 0.95 + r() * 0.1);
  ctx.fillRect(0, 0, T, T);
  const n = 5 + Math.floor(r() * 5);
  for (let i = 0; i < n; i++) {
    ctx.fillStyle = r() < 0.5 ? "#8a7748" : "#c4b27c";
    ctx.beginPath();
    ctx.ellipse(4 + r() * (T - 8), 4 + r() * (T - 8), 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU, 0, TAU);
    ctx.fill();
  }
  ctx.strokeStyle = "rgba(110,90,50,0.35)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const yy = T * (0.3 + r() * 0.4);
  ctx.moveTo(0, yy);
  ctx.bezierCurveTo(T * 0.3, yy - 6, T * 0.6, yy + 6, T, yy - 2);
  ctx.stroke();
}

/** 白牆黛瓦：頂上一排深色瓦，立面是白牆；比單位高（立面與瓦頂對比強）。 */
function cloudWall(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 104);
  ctx.fillStyle = CLOUD.mist;
  ctx.fillRect(0, 0, T, T);
  // 白牆的細縫與水漬
  ctx.strokeStyle = "rgba(86,100,92,0.28)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 13; x < T; x += 13) {
    ctx.moveTo(x + (r() - 0.5) * 2, 18);
    ctx.lineTo(x + (r() - 0.5) * 2, T);
  }
  ctx.stroke();
  ctx.fillStyle = "rgba(86,100,92,0.12)";
  ctx.fillRect(Math.floor(r() * 3) * 16 + 3, 24 + r() * 8, 12, 10);
  // 瓦頂：黛瓦一排（上方 18px），瓦片是一列弧形
  ctx.fillStyle = CLOUD.tile;
  ctx.fillRect(0, 0, T, 18);
  ctx.strokeStyle = "rgba(232,232,224,0.22)";
  ctx.lineWidth = 1.2;
  for (let row = 0; row < 2; row++) {
    for (let x = row ? 4 : 0; x < T + 8; x += 8) {
      ctx.beginPath();
      ctx.arc(x, 4 + row * 7, 4, 0, Math.PI);
      ctx.stroke();
    }
  }
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(0, 18, T, 3); // 簷下陰影
  ctx.fillStyle = "#2a3534";
  ctx.fillRect(0, 16, T, 2); // 瓦簷線
  if (s.wallFace) {
    ctx.fillStyle = "#b9bab0";
    ctx.fillRect(0, T - 9, T, 9);
    ctx.fillStyle = "rgba(0,0,0,0.12)";
    ctx.fillRect(0, T - 9, T, 1.5);
  }
}

function cliffLip(ctx: Ctx, r: () => number, p: readonly [number, number, number, number], n: readonly [number, number]): void {
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
  // 崖線：邊緣一條深色的線，一眼看得出是斷崖
  ctx.strokeStyle = "#2c3833";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x0 + n[0] * 5, y0 + n[1] * 5);
  ctx.lineTo(x1 + n[0] * 5, y1 + n[1] * 5);
  ctx.stroke();
}

/** 雲海山谷：往下是流動的白霧，邊緣是青石崖。致命地形要比能走的地板暗（美術 PM 3-37b 驗收：底色加深、霧團減淡）。 */
function cloudChasm(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 105);
  const g = ctx.createLinearGradient(0, 0, 0, T);
  g.addColorStop(0, "#26333a");
  g.addColorStop(1, "#5f727a");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  // 流動的雲：幾道橫向的白霧
  for (let i = 0; i < 4; i++) {
    const cy = 6 + i * 12 + r() * 6;
    const rg = ctx.createRadialGradient(r() * T, cy, 1, r() * T, cy, 18 + r() * 10);
    rg.addColorStop(0, "rgba(232,232,224,0.45)");
    rg.addColorStop(1, "rgba(232,232,224,0)");
    ctx.fillStyle = rg;
    ctx.fillRect(0, 0, T, T);
  }
  ctx.fillStyle = CLOUD.ink;
  if (s.lip.n) cliffLip(ctx, r, [0, 0, T, 0], [0, 1]);
  if (s.lip.s) cliffLip(ctx, r, [0, T, T, T], [0, -1]);
  if (s.lip.w) cliffLip(ctx, r, [0, 0, 0, T], [1, 0]);
  if (s.lip.e) cliffLip(ctx, r, [T, 0, T, T], [-1, 0]);
  // 崖面的陰影讓邊緣更深
  if (s.lip.n) {
    const gg = ctx.createLinearGradient(0, 0, 0, 16);
    gg.addColorStop(0, "rgba(60,72,66,0.85)");
    gg.addColorStop(1, "rgba(60,72,66,0)");
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, 16);
  }
}

/** 地熱泉：橘紅的泉水，冒白煙（保留紅色，致命）。 */
function cloudLava(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 106);
  ctx.fillStyle = "#d9532a";
  ctx.fillRect(0, 0, T, T);
  const glow = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * 0.7);
  glow.addColorStop(0, "rgba(255,200,90,0.6)");
  glow.addColorStop(1, "rgba(255,200,90,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, T, T);
  // 泉面的波紋
  ctx.strokeStyle = "rgba(255,230,160,0.55)";
  ctx.lineWidth = 1.3;
  for (let i = 0; i < 3; i++) {
    const wx = 5 + r() * (T - 22);
    const wy = 12 + i * 14 + r() * 4;
    ctx.beginPath();
    ctx.moveTo(wx, wy);
    ctx.quadraticCurveTo(wx + 5, wy - 3, wx + 10, wy);
    ctx.quadraticCurveTo(wx + 15, wy + 3, wx + 20, wy);
    ctx.stroke();
  }
  // 白煙
  for (let i = 0; i < 4; i++) {
    const px = 6 + r() * (T - 12);
    const py = 6 + r() * (T - 12);
    const rad = 7 + r() * 7;
    const sg = ctx.createRadialGradient(px, py, 0, px, py, rad);
    sg.addColorStop(0, "rgba(240,240,232,0.65)");
    sg.addColorStop(1, "rgba(240,240,232,0)");
    ctx.fillStyle = sg;
    ctx.beginPath();
    ctx.arc(px, py, rad, 0, TAU);
    ctx.fill();
  }
}

/** 寒潭：深青黑的水，邊緣一圈霜（致命）。 */
function cloudIceHole(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 107);
  ctx.fillStyle = "#0e2a2e";
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = rgba("#4f8f8a", 0.6);
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
  ctx.fillStyle = "rgba(214,236,232,0.55)";
  if (s.lip.n) ctx.fillRect(0, 0, T, 4);
  if (s.lip.w) ctx.fillRect(0, 0, 4, T);
  if (s.lip.e) ctx.fillRect(T - 4, 0, 4, T);
  if (s.lip.s) ctx.fillRect(0, T - 4, T, 4);
}

// ---- `look` 覆寫（雲嶺的地圖用；也可單獨寫在其他地圖上）----

/** `floor: plank_walk`：木棧道——橫向的木板，釘孔與木紋。 */
function plankWalk(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 108);
  ctx.fillStyle = "#3e2e1c";
  ctx.fillRect(0, 0, T, T);
  const rows = 4;
  const h = T / rows;
  for (let i = 0; i < rows; i++) {
    ctx.fillStyle = shade("#9a7848", 0.88 + r() * 0.2);
    ctx.fillRect(0, i * h + 1, T, h - 2);
    ctx.fillStyle = "rgba(255,240,200,0.14)";
    ctx.fillRect(0, i * h + 1, T, 1.5);
    ctx.strokeStyle = "rgba(70,48,24,0.4)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    const gy = i * h + 3 + r() * (h - 6);
    ctx.moveTo(0, gy);
    ctx.lineTo(T, gy + (r() - 0.5) * 2);
    ctx.stroke();
    ctx.fillStyle = "#3e2e1c";
    ctx.beginPath();
    ctx.arc(3.5, i * h + h / 2, 1.1, 0, TAU);
    ctx.arc(T - 3.5, i * h + h / 2, 1.1, 0, TAU);
    ctx.fill();
  }
}

/** `floor: paddy`：泥田＋田埂（四周一圈較高的土埂，裡面是泥水與秧苗）。 */
function paddy(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 109);
  ctx.fillStyle = "#a08a58"; // 田埂
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = "rgba(255,255,255,0.12)";
  ctx.fillRect(0, 0, T, 2);
  ctx.fillRect(0, 0, 2, T);
  ctx.fillStyle = shade("#6e6040", 0.94 + r() * 0.12); // 泥水
  roundRect(ctx, 5, 5, T - 10, T - 10, 4);
  ctx.fill();
  ctx.strokeStyle = "rgba(154,184,176,0.45)"; // 水面的天光
  ctx.lineWidth = 1.3;
  ctx.beginPath();
  for (let i = 0; i < 2; i++) {
    const wx = 9 + r() * 10;
    const wy = 12 + i * 18 + r() * 5;
    ctx.moveTo(wx, wy);
    ctx.quadraticCurveTo(wx + 6, wy - 3, wx + 13, wy);
  }
  ctx.stroke();
  // 秧苗：兩列小簇
  ctx.strokeStyle = CLOUD.bamboo;
  ctx.lineWidth = 1.3;
  ctx.lineCap = "round";
  for (let row = 0; row < 2; row++) {
    for (let col = 0; col < 3; col++) {
      const px = 11 + col * 15 + (row % 2) * 4 + (r() - 0.5) * 2;
      const py = 18 + row * 17;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px - 3, py - 6);
      ctx.moveTo(px, py);
      ctx.lineTo(px, py - 7);
      ctx.moveTo(px, py);
      ctx.lineTo(px + 3, py - 6);
      ctx.stroke();
    }
  }
}

/** `wall: canyon_rock`：灰褐色的山壁岩石（切面分明，頂面亮、底部立面暗）。 */
function canyonRock(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 110);
  ctx.fillStyle = "#6f6558";
  ctx.fillRect(0, 0, T, T);
  const cols = ["#8a7e6e", "#7a6f60", "#9a8e7c", "#665c4f"];
  for (let i = 0; i < 5; i++) {
    const cx = r() * T;
    const cy = r() * T;
    const n = 5;
    ctx.beginPath();
    for (let k = 0; k < n; k++) {
      const a = (k / n) * TAU + r() * 0.6;
      const rad = 10 + r() * 9;
      const px = cx + Math.cos(a) * rad;
      const py = cy + Math.sin(a) * rad * 0.8;
      if (k === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = cols[i % cols.length] ?? "#7a6f60";
    ctx.fill();
    ctx.strokeStyle = "rgba(38,32,26,0.55)";
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(30,26,20,0.6)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  let px = T * (0.2 + r() * 0.6);
  let py = 0;
  ctx.moveTo(px, py);
  for (let i = 0; i < 4; i++) {
    px += (r() - 0.5) * 12;
    py += T / 4;
    ctx.lineTo(px, py);
  }
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.08)";
  ctx.fillRect(0, 0, T, 3);
  if (s.wallFace) {
    ctx.fillStyle = "#3f372d";
    ctx.fillRect(0, T - 9, T, 9);
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.fillRect(0, T - 9, T, 1.5);
  }
}

/** 雲嶺的地形畫法（地形 ID → 畫法）；需求第 3 節「地形」七種。 */
export const CLOUD_TERRAIN: Readonly<Record<string, TerrainDrawer>> = {
  stone: cloudStone,
  grass: cloudGrass,
  dirt: cloudDirt,
  wall: cloudWall,
  chasm: cloudChasm,
  lava: cloudLava,
  ice_hole: cloudIceHole,
};

/** `look` 覆寫的地形畫法：地板 `floor`（石、草、土都換）與牆 `wall`。 */
export const CLOUD_LOOK_TERRAIN: Readonly<Record<string, Readonly<Record<string, TerrainDrawer>>>> = {
  "floor=plank_walk": { stone: plankWalk, grass: plankWalk, dirt: plankWalk },
  "floor=paddy": { stone: paddy, grass: paddy, dirt: paddy },
  "wall=canyon_rock": { wall: canyonRock },
};

/** 薄霧的一格（相鄰格的霧會接起來：每個霧團在格內衰減到 0）。`alpha` 為最濃處的不透明度。 */
export function drawMistTile(ctx: Ctx, x: number, y: number, alpha: number): void {
  const r = rng(x, y, 111);
  const n = 2 + Math.floor(r() * 2);
  for (let i = 0; i < n; i++) {
    const cx = 16 + r() * (T - 32);
    const cy = 16 + r() * (T - 32);
    const rad = Math.min(cx, T - cx, cy, T - cy) * (0.85 + r() * 0.15); // 衰減到格緣為 0，相鄰格的霧才接得起來
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
    g.addColorStop(0, rgba(CLOUD.mist, alpha));
    g.addColorStop(1, rgba(CLOUD.mist, 0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, rad, 0, TAU);
    ctx.fill();
  }
}
