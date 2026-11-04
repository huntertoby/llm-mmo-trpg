// 大世界圖（M）插畫（Phase 6F-ART1；docs/art/雲嶺區域插畫.md 第 3、4 節，B 俯視彩繪）。照樣張 `docs/art/sample/worldPaintedArt.js` 移植。
// 天空、碎界光帶、雲海、漂浮碎石照尺寸快取（底層）；浮島、浮橋、名字牌、傳送鈕依 `AtlasView` 的狀態畫在上層。
// 方位照 6D-5：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮，主城在中央。亂數一律用固定種子。
import { FONT, H, label, lvTag, mountain, puff, rng, roundRect, selfMark, W, type Ctx, type HitBox } from "./regionMapArt";
import type { Surface, SurfaceFactory } from "./regionMapPainter";

const TAU = Math.PI * 2;

/** 浮島的位置與大小（畫布邏輯座標）；`kind` 決定頂面畫法。 */
export interface IslandGeo {
  x: number;
  y: number;
  rx: number;
  ry: number;
  kind: string;
}

export const ISLAND_GEO: Readonly<Record<string, IslandGeo>> = {
  capital: { x: 650, y: 360, rx: 120, ry: 66, kind: "capital" },
  cloud_ridge: { x: 250, y: 380, rx: 185, ry: 100, kind: "cloud" },
  ashen_waste: { x: 600, y: 615, rx: 185, ry: 84, kind: "ashen" },
  crystal_crown: { x: 650, y: 120, rx: 125, ry: 50, kind: "crown" },
  arcane_hub: { x: 1060, y: 330, rx: 140, ry: 62, kind: "arcane" },
  frost_tide: { x: 1030, y: 640, rx: 140, ry: 62, kind: "frost" },
};

/** 浮島位置（大世界圖插畫與點擊區共用的唯一一份；6D-R2 併入原本 `atlasModel` 的 SPOTS）。表裡沒有的區
 * （內容新增的）照 `regions` 的順序 `index` 沿外圈排（半徑 35%、寬 20%）。 */
export function islandGeo(region: string, index: number): IslandGeo {
  const known = ISLAND_GEO[region];
  if (known !== undefined) return known;
  const angle = (index / 5) * TAU;
  const rx = Math.round((0.2 * W) / 2);
  const x = Math.round(W * (0.5 + 0.35 * Math.cos(angle)));
  const y = Math.round(H * (0.5 + 0.35 * Math.sin(angle)));
  return { x, y, rx, ry: Math.round(rx * 0.45), kind: region };
}

export interface AtlasArtIsland {
  region: string;
  name: string;
  status: "open" | "locked" | "later";
  current: boolean;
  canTeleport: boolean;
  /** 城鎮名（傳送鈕、「你在〇〇」；沒有＝空字串）。 */
  town: string;
  /** 等級牌（該區區域圖的 `level_zh`；沒有＝空字串）。 */
  level: string;
  /** 未開放的條件（`condition_zh`，沒有就寫「之後的賽季」）。 */
  condition: string;
  geo: IslandGeo;
}

export interface AtlasScene {
  islands: AtlasArtIsland[];
  capital: AtlasArtIsland;
}

// ---------------------------------------------------------------------------
// 版面（畫布與 DOM 點擊區共用）
// ---------------------------------------------------------------------------

export interface IslandLayout {
  /** 名字牌中心 y。 */
  nameY: number;
  levelY: number | null;
  /** 傳送鈕中心 y（不畫鈕＝null）。 */
  buttonY: number | null;
  /** 「你在〇〇」中心 y。 */
  hereY: number | null;
  /** 條件牌中心 y（已開放＝null）。 */
  conditionY: number | null;
}

export const buttonText = (is: AtlasArtIsland): string => `傳送到${is.town}`;
export const hereText = (is: AtlasArtIsland): string => `你在${is.town === "" ? is.name : is.town}`;

export function islandLayout(is: AtlasArtIsland): IslandLayout {
  const { y, ry } = is.geo;
  const ly = y + ry + ry * 0.45 + 18;
  if (is.status !== "open") return { nameY: ly, levelY: null, buttonY: null, hereY: null, conditionY: ly + 22 };
  const hasLv = is.level !== "";
  return {
    nameY: ly,
    levelY: hasLv ? ly + 21 : null,
    buttonY: !is.current && is.canTeleport && is.town !== "" ? ly + (hasLv ? 46 : 26) : null,
    hereY: is.current ? ly + (hasLv ? 44 : 24) : null,
    conditionY: null,
  };
}

/** 浮島本體的點擊區（頂面＋島緣厚度）。 */
export function islandHitBox(is: AtlasArtIsland): HitBox {
  const { x, y, rx, ry } = is.geo;
  return { x: x - rx, y: y - ry, w: rx * 2, h: ry * 2 + ry * 0.45 };
}

/** 傳送鈕的點擊區（字寬照 13px 粗體估）。 */
export function buttonHitBox(is: AtlasArtIsland, k = 1): HitBox | null {
  const by = islandLayout(is).buttonY;
  if (by === null) return null;
  const w = (buttonText(is).length * 13 + 22) * k;
  const h = 24 * k;
  return { x: is.geo.x - w / 2, y: by - h / 2, w, h };
}

// ---------------------------------------------------------------------------
// 底層：天空
// ---------------------------------------------------------------------------

export function sky(ctx: Ctx): void {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#5b79b0");
  g.addColorStop(0.55, "#a9c1df");
  g.addColorStop(1, "#f0dcc0");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  // 碎界光帶
  ctx.save();
  ctx.globalAlpha = 0.22;
  ctx.strokeStyle = "#b9a4ff";
  ctx.lineWidth = 34;
  ctx.beginPath();
  ctx.ellipse(W / 2, H / 2 + 30, W * 0.42, H * 0.36, -0.08, 0, TAU);
  ctx.stroke();
  ctx.globalAlpha = 0.35;
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.restore();
  // 雲海
  const r = rng(301);
  for (let i = 0; i < 260; i++) {
    const y = H * 0.35 + Math.pow(r(), 0.7) * H * 0.7;
    puff(ctx, r() * W, y, 30 + r() * 60, 0.25 + (y / H) * 0.45);
  }
  // 漂浮碎石
  for (let i = 0; i < 22; i++) {
    const x = r() * W;
    const y = r() * H;
    const s = 4 + r() * 9;
    ctx.fillStyle = "#6a6070";
    ctx.strokeStyle = "rgba(30,30,40,0.6)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x - s, y);
    ctx.lineTo(x, y - s * 0.6);
    ctx.lineTo(x + s, y);
    ctx.lineTo(x, y + s * 1.2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
}

// ---------------------------------------------------------------------------
// 浮島
// ---------------------------------------------------------------------------

/** 不規則圓形頂面的路徑（直接描在 ctx 上，不用 Path2D）。 */
export function traceBlob(ctx: Ctx, cx: number, cy: number, rx: number, ry: number, seed: number): void {
  const r = rng(seed);
  const n = 28;
  const pts: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU;
    const k = 0.9 + r() * 0.16;
    pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
  }
  ctx.beginPath();
  pts.forEach((q, i) => {
    const nx = pts[(i + 1) % n] as [number, number];
    const mx = (q[0] + nx[0]) / 2;
    const my = (q[1] + nx[1]) / 2;
    if (i === 0) ctx.moveTo(mx, my);
    else ctx.quadraticCurveTo(q[0], q[1], mx, my);
  });
  const p0 = pts[0] as [number, number];
  const p1 = pts[1] as [number, number];
  ctx.quadraticCurveTo(p0[0], p0[1], (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2);
  ctx.closePath();
}

const blobSeed = (g: IslandGeo): number => g.x * 3 + g.y;

function underside(ctx: Ctx, g: IslandGeo, grey: boolean): void {
  const { x, y, rx, ry } = g;
  const depth = ry * 0.45;
  const r = rng(x + y);
  const grad = ctx.createLinearGradient(0, y, 0, y + ry + depth + ry * 1.1);
  grad.addColorStop(0, grey ? "#7c7c84" : g.kind === "ashen" ? "#5a4038" : "#7a6450");
  grad.addColorStop(1, grey ? "#3c3c44" : "#2c2018");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(x - rx * 0.86, y + depth * 0.6);
  for (let k = 0; k <= 10; k++) {
    const t = k / 10;
    ctx.lineTo(x - rx * 0.86 + t * rx * 1.72, y + depth + Math.sin(t * Math.PI) * ry * (1.0 + r() * 0.35) + (k % 2) * 10);
  }
  ctx.lineTo(x + rx * 0.86, y + depth * 0.6);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(25,20,18,0.7)";
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.strokeStyle = "rgba(0,0,0,0.18)";
  ctx.lineWidth = 2;
  for (let k = 1; k <= 3; k++) {
    ctx.beginPath();
    ctx.ellipse(x, y + depth + k * 16, rx * (0.9 - k * 0.15), ry * 0.25, 0, 0.15, Math.PI - 0.15);
    ctx.stroke();
  }
  // 島緣的厚度
  ctx.save();
  ctx.translate(0, depth);
  ctx.fillStyle = grey ? "#6c6c74" : g.kind === "ashen" ? "#6a4a3c" : "#8a7058";
  traceBlob(ctx, x, y, rx, ry, blobSeed(g));
  ctx.fill();
  ctx.restore();
}

function topCloud(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  const r = rng(311);
  ctx.fillStyle = "#7fa65a";
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  for (let i = 0; i < 40; i++) {
    ctx.fillStyle = i % 2 ? "rgba(60,100,40,0.18)" : "rgba(180,200,120,0.18)";
    ctx.beginPath();
    ctx.ellipse(x + (r() - 0.5) * rx * 2, y + (r() - 0.5) * ry * 2, 18 + r() * 20, 10 + r() * 8, 0, 0, TAU);
    ctx.fill();
  }
  // 河
  ctx.strokeStyle = "#3f7fb0";
  ctx.lineWidth = 9;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(x - rx, y + ry * 0.55);
  ctx.quadraticCurveTo(x - 20, y + ry * 0.8, x + rx, y + ry * 0.35);
  ctx.stroke();
  ctx.strokeStyle = "#69a8d4";
  ctx.lineWidth = 4;
  ctx.stroke();
  // 梯田
  for (let i = 5; i >= 0; i--) {
    ctx.beginPath();
    ctx.ellipse(x + 10, y + 30, 18 + i * 7, 10 + i * 4, 0, Math.PI * 1.05, Math.PI * 1.95);
    ctx.strokeStyle = i % 2 ? "#9ccc6e" : "#b6dc87";
    ctx.lineWidth = 4;
    ctx.stroke();
  }
  // 竹林
  for (let i = 0; i < 26; i++) {
    const bx = x - rx * 0.55 + r() * 70;
    const by = y + 10 + r() * 40;
    ctx.strokeStyle = "#4f9a44";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx + 1, by - 12);
    ctx.stroke();
    ctx.fillStyle = "#2f6b34";
    ctx.beginPath();
    ctx.ellipse(bx + 3, by - 12, 4, 1.5, -0.5, 0, TAU);
    ctx.fill();
  }
  // 雪頂群山（北側）
  const pk: [number, number, number][] = [];
  for (let i = 0; i < 11; i++) pk.push([x - rx * 0.75 + i * rx * 0.15 + (r() - 0.5) * 10, y - ry * 0.25 + (r() - 0.5) * 14, 34 + r() * 26]);
  pk.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => mountain(ctx, px, py, h, r, true));
  for (let i = 0; i < 4; i++) puff(ctx, x - rx * 0.5 + i * rx * 0.33, y - 8 + (r() - 0.5) * 8, 16, 0.4);
}

function lavaAndTrees(ctx: Ctx, g: IslandGeo, r: () => number): void {
  const { x, y, rx, ry } = g;
  ctx.save();
  ctx.lineCap = "round";
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 14;
  ctx.strokeStyle = "#c2410c";
  ctx.lineWidth = 11;
  ctx.beginPath();
  ctx.moveTo(x + rx * 0.45, y - ry * 0.35);
  ctx.quadraticCurveTo(x + 10, y + 10, x + rx, y + ry * 0.3);
  ctx.stroke();
  ctx.strokeStyle = "#ff8a2a";
  ctx.lineWidth = 5;
  ctx.stroke();
  ctx.restore();
  for (let i = 0; i < 18; i++) {
    const tx = x - rx * 0.5 + r() * 90;
    const ty = y + r() * 40 - 10;
    ctx.strokeStyle = "#2e2420";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(tx, ty);
    ctx.lineTo(tx, ty - 10);
    ctx.moveTo(tx, ty - 6);
    ctx.lineTo(tx - 4, ty - 10);
    ctx.moveTo(tx, ty - 8);
    ctx.lineTo(tx + 4, ty - 13);
    ctx.stroke();
  }
}

function topAshen(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  const r = rng(313);
  const grad = ctx.createLinearGradient(0, y - ry, 0, y + ry);
  grad.addColorStop(0, "#4a3a32");
  grad.addColorStop(1, "#a0724c");
  ctx.fillStyle = grad;
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  for (let i = 0; i < 30; i++) {
    ctx.fillStyle = i % 2 ? "rgba(30,22,18,0.18)" : "rgba(200,120,70,0.15)";
    ctx.beginPath();
    ctx.ellipse(x + (r() - 0.5) * rx * 2, y + (r() - 0.5) * ry * 2, 16 + r() * 18, 8 + r() * 6, 0, 0, TAU);
    ctx.fill();
  }
  lavaAndTrees(ctx, g, r);
  for (let i = 0; i < 6; i++) mountain(ctx, x - rx * 0.7 + i * 34, y - ry * 0.35 + (r() - 0.5) * 10, 26 + r() * 14, r, false, ["#7a685c", "#43372f"]);
  // 火山
  const vx = x + rx * 0.4;
  const vy = y + ry * 0.05;
  ctx.fillStyle = "#5a4a42";
  ctx.beginPath();
  ctx.moveTo(vx - 46, vy + 10);
  ctx.lineTo(vx - 10, vy - 46);
  ctx.lineTo(vx, vy + 10);
  ctx.fill();
  ctx.fillStyle = "#33281f";
  ctx.beginPath();
  ctx.moveTo(vx - 10, vy - 46);
  ctx.lineTo(vx + 10, vy - 46);
  ctx.lineTo(vx + 46, vy + 10);
  ctx.lineTo(vx, vy + 10);
  ctx.fill();
  ctx.save();
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 16;
  ctx.fillStyle = "#ff8a2a";
  ctx.beginPath();
  ctx.ellipse(vx, vy - 46, 11, 3.5, 0, 0, TAU);
  ctx.fill();
  ctx.restore();
  // 赤沙
  for (let i = 0; i < 6; i++) {
    ctx.fillStyle = "rgba(214,138,82,0.55)";
    ctx.beginPath();
    ctx.ellipse(x - rx * 0.4 + i * 30, y + ry * 0.6 + (i % 2) * 6, 20, 6, 0, Math.PI, TAU);
    ctx.fill();
  }
}

function topCapital(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  ctx.fillStyle = "#d9cdb2";
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  ctx.fillStyle = "#c2b494";
  ctx.fillRect(x - rx, y - 6, rx * 2, 12);
  ctx.fillRect(x - 6, y - ry, 12, ry * 2);
  for (const [ox, oy] of [[-70, -34], [70, -34], [-70, 34], [70, 34]] as const) {
    ctx.fillStyle = "#8fbf6a";
    ctx.beginPath();
    ctx.ellipse(x + ox, y + oy, 26, 14, 0, 0, TAU);
    ctx.fill();
  }
  for (const [ox, oy] of [[-80, -10], [-50, -36], [-36, 20], [44, -38], [70, -8], [40, 24], [-84, 26], [84, 22]] as const) {
    const hx = x + ox;
    const hy = y + oy;
    ctx.fillStyle = "#f6efe0";
    ctx.fillRect(hx - 9, hy - 6, 18, 12);
    ctx.strokeStyle = "#27303a";
    ctx.lineWidth = 1;
    ctx.strokeRect(hx - 9, hy - 6, 18, 12);
    ctx.fillStyle = "#3a5ad0";
    ctx.beginPath();
    ctx.moveTo(hx - 12, hy - 5);
    ctx.lineTo(hx, hy - 15);
    ctx.lineTo(hx + 12, hy - 5);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
}

function tower(ctx: Ctx, g: IslandGeo): void {
  const { x, y } = g;
  const grad = ctx.createRadialGradient(x, y - 50, 0, x, y - 50, 70);
  grad.addColorStop(0, "rgba(160,140,255,0.6)");
  grad.addColorStop(1, "rgba(160,140,255,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(x - 70, y - 120, 140, 140);
  ctx.fillStyle = "#f6efe0";
  ctx.strokeStyle = "#27303a";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.ellipse(x, y, 16, 8, 0, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#c8bcff";
  ctx.beginPath();
  ctx.moveTo(x - 9, y - 2);
  ctx.lineTo(x, y - 82);
  ctx.lineTo(x + 9, y - 2);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#eee8ff";
  ctx.beginPath();
  ctx.moveTo(x - 2, y - 4);
  ctx.lineTo(x, y - 82);
  ctx.lineTo(x + 3, y - 4);
  ctx.closePath();
  ctx.fill();
}

/** 未開放的灰色剪影頂面（依區的地形大致輪廓）。 */
function topLocked(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry, kind } = g;
  const r = rng(x);
  ctx.fillStyle = "#9a9ca4";
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  ctx.fillStyle = "rgba(70,72,82,0.45)";
  if (kind === "crown") {
    for (let i = 0; i < 7; i++) {
      const cx = x - rx * 0.6 + i * rx * 0.2;
      const h = 18 + r() * 22;
      ctx.beginPath();
      ctx.moveTo(cx - 7, y + 8);
      ctx.lineTo(cx, y + 8 - h);
      ctx.lineTo(cx + 7, y + 8);
      ctx.fill();
    }
  } else if (kind === "arcane") {
    for (let i = 0; i < 8; i++) ctx.fillRect(x - rx * 0.6 + i * rx * 0.17, y - 10 - r() * 18, 14, 24 + r() * 10);
  } else {
    for (let i = 0; i < 5; i++) {
      ctx.beginPath();
      ctx.ellipse(x - rx * 0.5 + i * rx * 0.25, y + (r() - 0.5) * 20, 20, 8, 0, 0, TAU);
      ctx.fill();
    }
  }
}

/** 已開放但還沒有地景畫法的區（之後開放的區先用這個）：淡綠的頂面。 */
function topPlain(ctx: Ctx, g: IslandGeo): void {
  ctx.fillStyle = "#9ab07a";
  ctx.fillRect(g.x - g.rx, g.y - g.ry, g.rx * 2, g.ry * 2);
}

const TOPS: Readonly<Record<string, (ctx: Ctx, g: IslandGeo) => void>> = { cloud: topCloud, ashen: topAshen, capital: topCapital };

export function lock(ctx: Ctx, x: number, y: number): void {
  ctx.fillStyle = "#e4e6ea";
  ctx.strokeStyle = "#2b3038";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(x, y - 9, 8, Math.PI, 0);
  ctx.stroke();
  roundRect(ctx, x - 12, y - 9, 24, 19, 4);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#2b3038";
  ctx.beginPath();
  ctx.arc(x, y, 2.5, 0, TAU);
  ctx.fill();
}

/** 主城到各區的浮橋：已開放＝木板橋，未開放＝白色虛線。 */
export function bridge(ctx: Ctx, a: IslandGeo, b: IslandGeo, open: boolean): void {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const x1 = a.x + ux * a.rx * 0.85;
  const y1 = a.y + uy * a.ry * 0.85;
  const x2 = b.x - ux * b.rx * 0.85;
  const y2 = b.y - uy * b.ry * 0.85;
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2 + 24;
  ctx.save();
  if (!open) {
    ctx.setLineDash([6, 8]);
    ctx.strokeStyle = "rgba(255,255,255,0.55)";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.quadraticCurveTo(mx, my, x2, y2);
    ctx.stroke();
    ctx.restore();
    return;
  }
  const nx = -uy;
  const ny = ux;
  for (const off of [-6, 6]) {
    ctx.strokeStyle = "#4a3523";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x1 + nx * off, y1 + ny * off);
    ctx.quadraticCurveTo(mx + nx * off, my + ny * off, x2 + nx * off, y2 + ny * off);
    ctx.stroke();
  }
  ctx.strokeStyle = "#b08a5a";
  ctx.lineWidth = 3.5;
  for (let t = 0.03; t < 1; t += 0.045) {
    const q = (1 - t) * (1 - t);
    const m = 2 * t * (1 - t);
    const u = t * t;
    const cx = q * x1 + m * mx + u * x2;
    const cy = q * y1 + m * my + u * y2;
    ctx.beginPath();
    ctx.moveTo(cx - nx * 6, cy - ny * 6);
    ctx.lineTo(cx + nx * 6, cy + ny * 6);
    ctx.stroke();
  }
  ctx.restore();
}

function pill(ctx: Ctx, text: string, x: number, y: number, h: number, fill: string, color: string, stroke: string | null, font: string): void {
  ctx.font = font;
  const w = ctx.measureText(text).width + 22;
  ctx.fillStyle = fill;
  roundRect(ctx, x - w / 2, y - h / 2, w, h, h / 2);
  ctx.fill();
  if (stroke !== null) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x, y + 1);
}

function islandBody(ctx: Ctx, is: AtlasArtIsland): void {
  const g = is.geo;
  const grey = is.status !== "open";
  underside(ctx, g, grey);
  ctx.save();
  traceBlob(ctx, g.x, g.y, g.rx, g.ry, blobSeed(g));
  ctx.clip();
  if (grey) topLocked(ctx, g);
  else (TOPS[g.kind] ?? topPlain)(ctx, g);
  ctx.restore();
  traceBlob(ctx, g.x, g.y, g.rx, g.ry, blobSeed(g));
  ctx.strokeStyle = "rgba(30,26,22,0.75)";
  ctx.lineWidth = 2;
  ctx.stroke();
  if (g.kind === "capital") tower(ctx, g);
  if (grey) {
    // 雲纏著、上鎖
    const r = rng(g.x + 7);
    for (let i = 0; i < 9; i++) puff(ctx, g.x - g.rx + r() * g.rx * 2, g.y + (r() - 0.3) * g.ry, 26 + r() * 20, 0.7);
    lock(ctx, g.x, g.y - 4);
  }
  if (is.current) selfMark(ctx, g.x - g.rx * 0.55, g.y + g.ry * 0.35 - 10);
}

/** 名字牌、等級牌、條件、傳送鈕、「你在〇〇」。 */
function islandText(ctx: Ctx, is: AtlasArtIsland, k: number): void {
  const lay = islandLayout(is);
  const x = is.geo.x;
  const grey = is.status !== "open";
  const at = (y: number, draw: () => void): void => {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(k, k);
    ctx.translate(-x, -y);
    draw();
    ctx.restore();
  };
  at(lay.nameY, () => label(ctx, is.name, x, lay.nameY, grey));
  if (lay.levelY !== null) {
    const ly = lay.levelY;
    at(ly, () => lvTag(ctx, is.level, x, ly, false));
  }
  if (lay.conditionY !== null) {
    const cy = lay.conditionY;
    at(cy, () => pill(ctx, is.condition, x, cy, 18, "rgba(35,42,51,0.7)", "#d8dce2", null, `bold 12px ${FONT}`));
  }
  if (lay.buttonY !== null) {
    const by = lay.buttonY;
    at(by, () => pill(ctx, buttonText(is), x, by, 24, "#3fb4f0", "#08263a", "#1b2a38", `bold 13px ${FONT}`));
  }
  if (lay.hereY !== null) {
    const hy = lay.hereY;
    at(hy, () => pill(ctx, hereText(is), x, hy, 20, "#2f8cff", "#ffffff", null, `bold 12px ${FONT}`));
  }
}

function atlasLegend(ctx: Ctx): void {
  const w = 360;
  const h = 44;
  const x = 40;
  const y = H - 40 - h;
  ctx.fillStyle = "rgba(35,42,51,0.82)";
  roundRect(ctx, x, y, w, h, 10);
  ctx.fill();
  ctx.font = `13px ${FONT}`;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  const cy = y + h / 2;
  ctx.fillStyle = "#7fa65a";
  ctx.beginPath();
  ctx.arc(x + 22, cy, 7, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "#f2f4f7";
  ctx.fillText("已開放（點了看區域圖）", x + 34, cy);
  ctx.save();
  ctx.translate(x + 210, cy + 3);
  ctx.scale(0.6, 0.6);
  lock(ctx, 0, 0);
  ctx.restore();
  ctx.font = `13px ${FONT}`;
  ctx.textAlign = "left";
  ctx.fillStyle = "#f2f4f7";
  ctx.fillText("未開放", x + 224, cy);
  ctx.fillStyle = "#2f8cff";
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x + 292, cy, 6, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#f2f4f7";
  ctx.fillText("自己", x + 304, cy);
}

function atlasTitle(ctx: Ctx, canTeleport: boolean): void {
  ctx.font = `bold 28px ${FONT}`;
  ctx.fillStyle = "rgba(35,42,51,0.82)";
  roundRect(ctx, 40, 34, 330, 60, 12);
  ctx.fill();
  ctx.strokeStyle = "#e0c27a";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText("大世界", 58, 65);
  ctx.font = `bold 13px ${FONT}`;
  ctx.fillStyle = "#ffe08a";
  ctx.fillText(canTeleport ? "可以點城鎮直接傳送" : "在城鎮或傳送石上才能傳送", 160, 66);
}

function atlasFrame(ctx: Ctx): void {
  ctx.strokeStyle = "#5a3c24";
  ctx.lineWidth = 22;
  ctx.strokeRect(11, 11, W - 22, H - 22);
  ctx.strokeStyle = "#8a5f38";
  ctx.lineWidth = 6;
  ctx.strokeRect(19, 19, W - 38, H - 38);
  ctx.strokeStyle = "#e0c27a";
  ctx.lineWidth = 2;
  ctx.strokeRect(25, 25, W - 50, H - 50);
}

/** 上層：浮橋、浮島、字牌、標題、圖例、外框（邏輯座標）。 */
export function atlasOverlay(ctx: Ctx, scene: AtlasScene, canTeleport: boolean, k = 1): void {
  const cap = scene.capital;
  for (const is of scene.islands) bridge(ctx, cap.geo, is.geo, is.status === "open");
  const all = [cap, ...scene.islands].sort((a, b) => a.geo.y - b.geo.y || a.region.localeCompare(b.region));
  for (const is of all) islandBody(ctx, is);
  for (const is of all) islandText(ctx, is, k);
  atlasTitle(ctx, canTeleport);
  atlasLegend(ctx);
  atlasFrame(ctx);
}

// ---------------------------------------------------------------------------
// 快取與組合
// ---------------------------------------------------------------------------

const asImage = (s: Surface): CanvasImageSource => s as unknown as CanvasImageSource;

export class AtlasPainter {
  private readonly skies = new Map<string, Surface>();
  readonly stats = { sky: 0, overlay: 0 };

  constructor(
    private readonly make: SurfaceFactory,
    private readonly limit = 3,
  ) {}

  /** 底層（天空）：照尺寸與字型版本快取。 */
  skyLayer(w: number, h: number): Surface {
    const key = `${w}x${h}`;
    const hit = this.skies.get(key);
    if (hit !== undefined) return hit;
    const s = this.make(w, h);
    const ctx = s.getContext("2d");
    if (ctx !== null) {
      ctx.setTransform(w / W, 0, 0, h / H, 0, 0);
      sky(ctx);
    }
    this.stats.sky += 1;
    this.skies.set(key, s);
    while (this.skies.size > this.limit) {
      const first = this.skies.keys().next().value;
      if (first === undefined) break;
      this.skies.delete(first);
    }
    return s;
  }

  paintBase(ctx: Ctx, w: number, h: number): void {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(asImage(this.skyLayer(w, h)), 0, 0);
  }

  paintOverlay(ctx: Ctx, scene: AtlasScene, canTeleport: boolean, w: number, h: number, k = 1): void {
    this.stats.overlay += 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.setTransform(w / W, 0, 0, h / H, 0, 0);
    atlasOverlay(ctx, scene, canTeleport, k);
  }
}
