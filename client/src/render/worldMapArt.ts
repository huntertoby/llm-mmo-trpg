// 大世界圖（M）插畫第 2 版（Phase 6F-ART1b；docs/art/雲嶺區域插畫.md 第 3 節最後，B 俯視彩繪）。
// 照樣張 `docs/art/sample/worldPaintedArt.js`（第 2 版）移植：光從左上來（太陽光暈、光束）、有明暗壓扁成層的雲、
// 長草的小浮石、未開放航線的一串光點、深藍底金色雙框的字牌、帶小晶石的傳送鈕、外框四角金飾。
// 這支檔放共用的位置、版面、天空雲層、浮橋、字牌與外框；浮島本體在 `worldIslandArt.ts`，快取與漂浮在 `worldMapPainter.ts`。
// 方位照 6D-5：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮，主城在中央。亂數一律用固定種子（不用 Math.random）。
import { FONT, H, pine, rng, roundRect, selfMark, W, type Ctx, type HitBox, type Rand } from "./regionMapArt";

export const TAU = Math.PI * 2;
export const SERIF = '"Noto Serif TC","PMingLiU","MingLiU",serif';
/** 光從左上來。 */
export const LIGHT: readonly [number, number] = [-0.6, -0.8];

type Rgb = readonly [number, number, number];

/** 浮島的位置與大小（畫布邏輯座標）；`kind` 決定頂面畫法。 */
export interface IslandGeo {
  x: number;
  y: number;
  rx: number;
  ry: number;
  kind: string;
}

/** 第 2 版樣張的浮島位置（`worldPaintedArt.js` 的 ISLANDS）。 */
export const ISLAND_GEO: Readonly<Record<string, IslandGeo>> = {
  capital: { x: 650, y: 350, rx: 125, ry: 66, kind: "capital" },
  cloud_ridge: { x: 260, y: 360, rx: 185, ry: 98, kind: "cloud" },
  ashen_waste: { x: 610, y: 600, rx: 180, ry: 84, kind: "ashen" },
  crystal_crown: { x: 660, y: 112, rx: 120, ry: 48, kind: "crown" },
  arcane_hub: { x: 1050, y: 300, rx: 135, ry: 58, kind: "arcane" },
  frost_tide: { x: 1030, y: 590, rx: 135, ry: 58, kind: "frost" },
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

/** 島緣厚度（頂面往下這麼多是島緣的下緣）。 */
export const lipDepth = (g: IslandGeo): number => g.ry * 0.42;

export interface AtlasArtIsland {
  region: string;
  name: string;
  status: "open" | "locked" | "later";
  current: boolean;
  canTeleport: boolean;
  /** 第一次免費傳送（RT-5：還沒到過新手區的小鎮）：傳送鈕發金光、寫「免費」。省略＝否。 */
  free?: boolean;
  /** 城鎮名（傳送鈕；沒有＝空字串）。 */
  town: string;
  /** 自己所在的地點名（「你在〇〇」，6F-3：不再固定寫該區的城鎮；沒給＝城鎮名或區名）。 */
  here?: string;
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

/** 字牌高度；第二行（等級、城鎮或條件）在字牌裡。 */
export const PLAQUE_H = 50;
const BUTTON_H = 26;
const HERE_H = 22;
const GAP = 6;

export interface IslandLayout {
  /** 字牌上緣 y（字牌整組以這點為中心縮放 `k` 倍）。 */
  plaqueY: number;
  /** 名字中心 y。 */
  nameY: number;
  /** 第二行中心 y（已開放＝等級或城鎮；沒有＝null）。 */
  levelY: number | null;
  /** 傳送鈕中心 y（不畫鈕＝null）。 */
  buttonY: number | null;
  /** 「你在〇〇」中心 y。 */
  hereY: number | null;
  /** 條件中心 y（已開放＝null）。 */
  conditionY: number | null;
}

/** 「免費」的寫法（RT-5 ③，樣張 capital-opening 第 3 格）。 */
export const FREE_ZH = "免費";
export const buttonText = (is: AtlasArtIsland): string => (is.free === true ? `傳送到${is.town}（${FREE_ZH}）` : `傳送到${is.town}`);
export const hereText = (is: AtlasArtIsland): string =>
  `你在${is.here !== undefined && is.here !== "" ? is.here : is.town === "" ? is.name : is.town}`;

/** 字牌第二行：已開放＝等級（沒有就寫城鎮）；未開放＝條件。 */
export const plaqueSub = (is: AtlasArtIsland): string => (is.status !== "open" ? is.condition : is.level !== "" ? is.level : is.town);

/** 版面（未縮放的邏輯座標；`k` 倍時各點照 `plaqueY + (y - plaqueY) * k` 換算）。 */
export function islandLayout(is: AtlasArtIsland): IslandLayout {
  const { y, ry } = is.geo;
  const top = y + ry + lipDepth(is.geo) + 12;
  const below = top + PLAQUE_H + GAP;
  if (is.status !== "open") return { plaqueY: top, nameY: top + 18, levelY: null, buttonY: null, hereY: null, conditionY: top + 37 };
  return {
    plaqueY: top,
    nameY: top + 18,
    levelY: plaqueSub(is) !== "" ? top + 37 : null,
    buttonY: !is.current && is.canTeleport && is.town !== "" ? below + BUTTON_H / 2 : null,
    hereY: is.current ? below + HERE_H / 2 : null,
    conditionY: null,
  };
}

/** 浮島本體的點擊區（頂面＋島緣厚度）；點擊區不跟著漂浮。 */
export function islandHitBox(is: AtlasArtIsland): HitBox {
  const { x, y, rx, ry } = is.geo;
  return { x: x - rx, y: y - ry, w: rx * 2, h: ry * 2 + lipDepth(is.geo) };
}

/** 傳送鈕寬度（字寬照 13px 粗體估，畫布上用 measureText）。 */
const buttonWidth = (text: string): number => text.length * 13 + 40;

/** 傳送鈕的點擊區（字牌整組放大 `k` 倍時跟著放大）。 */
export function buttonHitBox(is: AtlasArtIsland, k = 1): HitBox | null {
  const lay = islandLayout(is);
  if (lay.buttonY === null) return null;
  const w = buttonWidth(buttonText(is)) * k;
  const h = BUTTON_H * k;
  const cy = lay.plaqueY + (lay.buttonY - lay.plaqueY) * k;
  return { x: is.geo.x - w / 2, y: cy - h / 2, w, h };
}

/** 字牌、傳送鈕、自己標記這一組的範圍（邏輯座標；給離屏快取用，留了陰影的邊）。 */
export function marksBounds(is: AtlasArtIsland, k = 1): HitBox {
  const { x, y, rx, ry } = is.geo;
  const lay = islandLayout(is);
  const plaqueW = Math.max(is.name.length * 19, plaqueSub(is).length * 12) + 44;
  const btnW = Math.max(buttonWidth(buttonText(is)), hereText(is).length * 12 + 30);
  let half = (Math.max(plaqueW, btnW) / 2) * k * 1.15 + 16;
  let top = lay.plaqueY - 12;
  if (is.current) {
    half = Math.max(half, rx * 0.55 + 44);
    top = Math.min(top, y + ry * 0.3 - 10 - 30);
  }
  const bottom = lay.plaqueY + (PLAQUE_H + GAP + BUTTON_H + 14) * k;
  return { x: x - half, y: top, w: half * 2, h: bottom - top };
}

// ---------------------------------------------------------------------------
// 雲
// ---------------------------------------------------------------------------

const rgb = (c: Rgb): string => c.join(",");

/** 有明暗的雲團：上亮下暗，`sy` 壓扁。 */
export function cloudPuff(ctx: Ctx, x: number, y: number, r: number, a: number, tint: Rgb = [255, 255, 255], shade: Rgb = [176, 190, 214], sy = 1): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(1, sy);
  const g = ctx.createRadialGradient(-r * 0.25, -r * 0.45, r * 0.1, 0, 0, r);
  const mid: Rgb = [0, 1, 2].map((i) => Math.round((tint[i] ?? 0) * 0.6 + (shade[i] ?? 0) * 0.4)) as unknown as Rgb;
  g.addColorStop(0, `rgba(${rgb(tint)},${a})`);
  g.addColorStop(0.55, `rgba(${rgb(mid)},${a})`);
  g.addColorStop(0.9, `rgba(${rgb(shade)},${a * 0.9})`);
  g.addColorStop(1, `rgba(${rgb(shade)},0)`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, TAU);
  ctx.fill();
  ctx.restore();
}

/** 一排壓扁的雲（由遠到近排序後畫）。 */
export function cloudBank(ctx: Ctx, y: number, count: number, rMin: number, rMax: number, a: number, seed: number, tint: Rgb, shade: Rgb, spread = 30, sy = 0.62): void {
  const r = rng(seed);
  const items: [number, number, number][] = [];
  for (let i = 0; i < count; i++) items.push([(i / count) * (W + 200) - 100 + (r() - 0.5) * 60, y + (r() - 0.5) * spread, rMin + r() * (rMax - rMin)]);
  items.sort((p, q) => p[1] - q[1]).forEach(([x, yy, rr]) => cloudPuff(ctx, x, yy, rr, a, tint, shade, sy));
}

function sunAndRays(ctx: Ctx): void {
  const s = ctx.createRadialGradient(150, 70, 10, 150, 70, 520);
  s.addColorStop(0, "rgba(255,240,205,0.85)");
  s.addColorStop(0.25, "rgba(255,226,170,0.35)");
  s.addColorStop(1, "rgba(255,226,170,0)");
  ctx.fillStyle = s;
  ctx.fillRect(0, 0, W, H);
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < 6; i++) {
    const a0 = 0.15 + i * 0.13;
    ctx.fillStyle = `rgba(255,236,190,${0.035 + (i % 2) * 0.02})`;
    ctx.beginPath();
    ctx.moveTo(150, 70);
    ctx.lineTo(150 + Math.cos(a0) * 1600, 70 + Math.sin(a0) * 1600);
    ctx.lineTo(150 + Math.cos(a0 + 0.05) * 1600, 70 + Math.sin(a0 + 0.05) * 1600);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

function riftCracks(ctx: Ctx): void {
  ctx.save();
  ctx.strokeStyle = "rgba(210,195,255,0.55)";
  ctx.lineWidth = 1.2;
  ctx.shadowColor = "#b9a4ff";
  ctx.shadowBlur = 10;
  const r = rng(401);
  for (let i = 0; i < 4; i++) {
    let x = 380 + r() * 760;
    let y = 30 + r() * 140;
    ctx.beginPath();
    ctx.moveTo(x, y);
    for (let k = 0; k < 5; k++) {
      x += 20 + r() * 40;
      y += (r() - 0.5) * 30;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  ctx.restore();
}

/** 天空：漸層、太陽光暈與光束、碎界裂痕、遠方雲層。 */
export function sky(ctx: Ctx): void {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#36507f");
  g.addColorStop(0.35, "#6f93c4");
  g.addColorStop(0.62, "#c7cfe0");
  g.addColorStop(0.85, "#f2d6b0");
  g.addColorStop(1, "#f6e2c4");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  sunAndRays(ctx);
  riftCracks(ctx);
  cloudBank(ctx, 230, 26, 30, 60, 0.35, 403, [236, 240, 250], [150, 168, 200], 30);
  cloudBank(ctx, 330, 22, 40, 80, 0.45, 405, [245, 244, 248], [160, 172, 202], 40);
}

export function lowerClouds(ctx: Ctx): void {
  cloudBank(ctx, 520, 20, 50, 95, 0.55, 407, [255, 250, 244], [178, 182, 206], 60);
  cloudBank(ctx, 690, 24, 50, 90, 0.7, 409, [255, 248, 236], [200, 190, 200], 50, 0.55);
}

/** 最前面一排雲，蓋住島的下緣，做出深度。 */
export function frontClouds(ctx: Ctx): void {
  cloudBank(ctx, 845, 22, 50, 90, 0.85, 411, [255, 246, 232], [214, 196, 190], 24, 0.5);
}

// ---------------------------------------------------------------------------
// 長草的小浮石
// ---------------------------------------------------------------------------

function islet(ctx: Ctx, x: number, y: number, s: number, r: Rand, haze: number): void {
  ctx.save();
  ctx.globalAlpha = haze;
  const g = ctx.createLinearGradient(x - s, 0, x + s, 0);
  g.addColorStop(0, "#9a7f62");
  g.addColorStop(1, "#4a3828");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.moveTo(x - s, y);
  ctx.lineTo(x - s * 0.4, y + s * 1.3);
  ctx.lineTo(x + s * 0.15, y + s * 1.9);
  ctx.lineTo(x + s * 0.6, y + s * 1.1);
  ctx.lineTo(x + s, y);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#6d9a4c";
  ctx.beginPath();
  ctx.ellipse(x, y, s, s * 0.38, 0, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,220,0.35)";
  ctx.beginPath();
  ctx.ellipse(x - s * 0.3, y - s * 0.12, s * 0.45, s * 0.15, 0, 0, TAU);
  ctx.fill();
  if (r() < 0.5) pine(ctx, x + s * 0.2, y + 1, s / 14);
  ctx.restore();
}

const ISLETS: readonly (readonly [number, number, number, number])[] = [
  [470, 220, 9, 0.7],
  [860, 190, 7, 0.6],
  [880, 450, 10, 0.85],
  [420, 520, 8, 0.8],
  [130, 560, 12, 0.85],
  [1180, 150, 8, 0.6],
  [820, 720, 11, 0.9],
  [1200, 440, 7, 0.6],
  [330, 140, 6, 0.55],
];

export function islets(ctx: Ctx): void {
  const r = rng(421);
  for (const [x, y, s, h] of ISLETS) islet(ctx, x, y, s, r, h);
}

/** 底層的天空整組（快取）：天空、小浮石、下方雲層。 */
export function skyScene(ctx: Ctx): void {
  sky(ctx);
  islets(ctx);
  lowerClouds(ctx);
}

/** 島下雲層上的投影（不跟著島漂浮：投影在雲上）。 */
export function shadowBelow(ctx: Ctx, g: IslandGeo): void {
  const cy = g.y + g.ry * 3.2;
  const grad = ctx.createRadialGradient(g.x + 30, cy, 10, g.x + 30, cy, g.rx * 1.1);
  grad.addColorStop(0, "rgba(70,70,110,0.22)");
  grad.addColorStop(1, "rgba(70,70,110,0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.ellipse(g.x + 30, cy, g.rx * 1.1, g.ry * 0.5, 0, 0, TAU);
  ctx.fill();
}

// ---------------------------------------------------------------------------
// 浮橋
// ---------------------------------------------------------------------------

/** 主城到各區的浮橋：已開放＝木板吊橋（繩索、欄柱），未開放＝一串淡淡的光點。浮橋不跟著島漂浮。 */
export function bridge(ctx: Ctx, a: IslandGeo, b: IslandGeo, open: boolean): void {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const x1 = a.x + ux * a.rx * 0.82;
  const y1 = a.y + uy * a.ry * 0.82;
  const x2 = b.x - ux * b.rx * 0.82;
  const y2 = b.y - uy * b.ry * 0.82;
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2 + 22;
  const at = (t: number): [number, number] => {
    const q = (1 - t) * (1 - t);
    const m = 2 * t * (1 - t);
    const u = t * t;
    return [q * x1 + m * mx + u * x2, q * y1 + m * my + u * y2];
  };
  ctx.save();
  if (!open) {
    for (let t = 0.08; t < 0.95; t += 0.06) {
      const [cx, cy] = at(t);
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 5);
      g.addColorStop(0, "rgba(255,250,230,0.7)");
      g.addColorStop(1, "rgba(255,250,230,0)");
      ctx.fillStyle = g;
      ctx.fillRect(cx - 5, cy - 5, 10, 10);
    }
    ctx.restore();
    return;
  }
  const nx = -uy;
  const ny = ux;
  for (let t = 0.02; t < 0.99; t += 0.035) {
    const [cx, cy] = at(t);
    ctx.strokeStyle = "rgba(40,30,20,0.35)";
    ctx.lineWidth = 4.5;
    ctx.beginPath();
    ctx.moveTo(cx - nx * 7, cy - ny * 7 + 2);
    ctx.lineTo(cx + nx * 7, cy + ny * 7 + 2);
    ctx.stroke();
    ctx.strokeStyle = Math.round(t * 100) % 2 ? "#c49a62" : "#b08452";
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.moveTo(cx - nx * 7, cy - ny * 7);
    ctx.lineTo(cx + nx * 7, cy + ny * 7);
    ctx.stroke();
  }
  for (const off of [-8, 8]) {
    ctx.strokeStyle = "#3e2c1c";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(x1 + nx * off, y1 + ny * off - 6);
    ctx.quadraticCurveTo(mx + nx * off, my + ny * off - 10, x2 + nx * off, y2 + ny * off - 6);
    ctx.stroke();
  }
  for (const [px, py] of [[x1, y1], [x2, y2]] as const) {
    for (const off of [-8, 8]) {
      ctx.fillStyle = "#4a3523";
      ctx.fillRect(px + nx * off - 2, py + ny * off - 10, 4, 12);
      ctx.fillStyle = "#e0c27a";
      ctx.beginPath();
      ctx.arc(px + nx * off, py + ny * off - 11, 2.2, 0, TAU);
      ctx.fill();
    }
  }
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 徽章、字牌、傳送鈕
// ---------------------------------------------------------------------------

/** 未開放的金框鎖頭徽章。 */
export function medallion(ctx: Ctx, x: number, y: number): void {
  ctx.save();
  const g = ctx.createRadialGradient(x - 4, y - 4, 2, x, y, 17);
  g.addColorStop(0, "#5b6378");
  g.addColorStop(1, "#2a2f3e");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, 16, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#d8b860";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.strokeStyle = "rgba(216,184,96,0.5)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(x, y, 12.5, 0, TAU);
  ctx.stroke();
  ctx.strokeStyle = "#e9d9a6";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x, y - 3, 4.5, Math.PI, 0);
  ctx.stroke();
  ctx.fillStyle = "#e9d9a6";
  ctx.fillRect(x - 6, y - 3, 12, 9);
  ctx.fillStyle = "#2a2f3e";
  ctx.fillRect(x - 1, y, 2, 4);
  ctx.restore();
}

/** 深藍底、金色雙框、襯線字的字牌；未開放是灰色版。 */
function plaque(ctx: Ctx, name: string, sub: string, x: number, y: number, grey: boolean): void {
  ctx.font = `bold 19px ${SERIF}`;
  const nameW = ctx.measureText(name).width;
  ctx.font = `bold 12px ${FONT}`;
  const subW = ctx.measureText(sub).width;
  const w = Math.max(nameW, subW) + 44;
  const h = PLAQUE_H;
  const left = x - w / 2;
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.35)";
  ctx.shadowBlur = 8;
  ctx.shadowOffsetY = 3;
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, grey ? "#4a4e5c" : "#2c3550");
  g.addColorStop(1, grey ? "#33363f" : "#1b2136");
  ctx.fillStyle = g;
  roundRect(ctx, left, y, w, h, 6);
  ctx.fill();
  ctx.restore();
  const gold = grey ? "#9a9ca6" : "#d8b860";
  ctx.strokeStyle = gold;
  ctx.lineWidth = 1.6;
  roundRect(ctx, left, y, w, h, 6);
  ctx.stroke();
  ctx.strokeStyle = grey ? "rgba(154,156,166,0.45)" : "rgba(216,184,96,0.45)";
  ctx.lineWidth = 1;
  roundRect(ctx, left + 3, y + 3, w - 6, h - 6, 4);
  ctx.stroke();
  for (const sx of [left, left + w]) {
    ctx.fillStyle = gold;
    ctx.beginPath();
    ctx.moveTo(sx, y + h / 2 - 6);
    ctx.lineTo(sx + 5, y + h / 2);
    ctx.lineTo(sx, y + h / 2 + 6);
    ctx.lineTo(sx - 5, y + h / 2);
    ctx.closePath();
    ctx.fill();
  }
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `bold 19px ${SERIF}`;
  ctx.fillStyle = grey ? "#d6d8de" : "#fbf3dc";
  ctx.fillText(name, x, y + 18);
  if (sub !== "") {
    ctx.font = `bold 12px ${FONT}`;
    ctx.fillStyle = grey ? "#a8acb6" : "#f2c96a";
    ctx.fillText(sub, x, y + 37);
  }
}

/** 傳送鈕的兩種顏色：一般藍色；第一次免費傳送（RT-5）藍底金框、外面一圈金光。 */
const BUTTON_STYLE = {
  normal: { glow: "rgba(40,140,220,0.6)", blur: 10, top: "#6fd0ff", bottom: "#2a8fd6", edge: "#0f3a5a", lw: 1.4 },
  free: { glow: "rgba(255,214,110,0.95)", blur: 18, top: "#6fd0ff", bottom: "#2a8fd6", edge: "#ffe08a", lw: 2.2 },
} as const;

/** 藍色傳送鈕（左邊一顆小晶石）；`y` 是上緣。`free`＝第一次免費傳送：金框加金光（RT-5）。 */
function teleportButton(ctx: Ctx, text: string, x: number, y: number, free = false): void {
  const st = BUTTON_STYLE[free ? "free" : "normal"];
  ctx.font = `bold 13px ${FONT}`;
  const w = ctx.measureText(text).width + 40;
  const h = BUTTON_H;
  const bx = x - w / 2;
  ctx.save();
  ctx.shadowColor = st.glow;
  ctx.shadowBlur = st.blur;
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, st.top);
  g.addColorStop(1, st.bottom);
  ctx.fillStyle = g;
  roundRect(ctx, bx, y, w, h, 13);
  ctx.fill();
  if (free) ctx.fill(); // 金光疊兩次（樣張：雲嶺的傳送鈕發金光）
  ctx.restore();
  ctx.strokeStyle = st.edge;
  ctx.lineWidth = st.lw;
  roundRect(ctx, bx, y, w, h, 13);
  ctx.stroke();
  const cx = bx + 14;
  const cy = y + h / 2;
  ctx.fillStyle = "#e9fbff";
  ctx.beginPath();
  ctx.moveTo(cx, cy - 7);
  ctx.lineTo(cx + 4.5, cy);
  ctx.lineTo(cx, cy + 7);
  ctx.lineTo(cx - 4.5, cy);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#082a40";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + 8, y + h / 2 + 1);
}

/** 「你在〇〇」（左邊一顆藍點）；`y` 是上緣。 */
function hereTag(ctx: Ctx, text: string, x: number, y: number): void {
  ctx.font = `bold 12px ${FONT}`;
  const w = ctx.measureText(text).width + 30;
  const h = HERE_H;
  ctx.fillStyle = "rgba(20,30,50,0.75)";
  roundRect(ctx, x - w / 2, y, w, h, 11);
  ctx.fill();
  ctx.strokeStyle = "#5fb0ff";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.fillStyle = "#2f8cff";
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(x - w / 2 + 12, y + h / 2, 4.5, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#e6f2ff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + 6, y + h / 2 + 1);
}

/** 跟著島一起漂浮的標記：自己（藍圈＋定位釘）、字牌、傳送鈕或「你在〇〇」。字牌整組以字牌上緣為中心放大 `k` 倍。 */
export function islandMarks(ctx: Ctx, is: AtlasArtIsland, k = 1): void {
  const g = is.geo;
  if (is.current) selfMark(ctx, g.x - g.rx * 0.55, g.y + g.ry * 0.3 - 10);
  const lay = islandLayout(is);
  const top = lay.plaqueY;
  ctx.save();
  ctx.translate(g.x, top);
  ctx.scale(k, k);
  ctx.translate(-g.x, -top);
  plaque(ctx, is.name, plaqueSub(is), g.x, top, is.status !== "open");
  if (lay.buttonY !== null) teleportButton(ctx, buttonText(is), g.x, lay.buttonY - BUTTON_H / 2, is.free === true);
  if (lay.hereY !== null) hereTag(ctx, hereText(is), g.x, lay.hereY - HERE_H / 2);
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 標題、圖例、外框
// ---------------------------------------------------------------------------

export function atlasTitle(ctx: Ctx, canTeleport: boolean): void {
  const x = 44;
  const y = 38;
  const w = 330;
  const h = 62;
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.35)";
  ctx.shadowBlur = 10;
  ctx.shadowOffsetY = 3;
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, "#2c3550");
  g.addColorStop(1, "#1b2136");
  ctx.fillStyle = g;
  roundRect(ctx, x, y, w, h, 8);
  ctx.fill();
  ctx.restore();
  ctx.strokeStyle = "#d8b860";
  ctx.lineWidth = 1.8;
  roundRect(ctx, x, y, w, h, 8);
  ctx.stroke();
  ctx.strokeStyle = "rgba(216,184,96,0.45)";
  ctx.lineWidth = 1;
  roundRect(ctx, x + 4, y + 4, w - 8, h - 8, 5);
  ctx.stroke();
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.font = `bold 30px ${SERIF}`;
  ctx.fillStyle = "#fbf3dc";
  ctx.fillText("大世界", x + 20, y + h / 2 + 1);
  ctx.font = `bold 13px ${FONT}`;
  ctx.fillStyle = "#f2c96a";
  ctx.fillText(canTeleport ? "可以點城鎮直接傳送" : "在城鎮或傳送石上才能傳送", x + 132, y + h / 2 + 1);
}

export function atlasLegend(ctx: Ctx): void {
  const w = 330;
  const h = 40;
  const x = 44;
  const y = H - 44 - h;
  ctx.fillStyle = "rgba(27,33,54,0.85)";
  roundRect(ctx, x, y, w, h, 8);
  ctx.fill();
  ctx.strokeStyle = "rgba(216,184,96,0.7)";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.font = `13px ${FONT}`;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  const cy = y + h / 2;
  ctx.fillStyle = "#86b862";
  ctx.strokeStyle = "#d8b860";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.arc(x + 20, cy, 6.5, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#f2f4f7";
  ctx.fillText("已開放（點了看區域圖）", x + 32, cy);
  ctx.save();
  ctx.translate(x + 206, cy);
  ctx.scale(0.55, 0.55);
  medallion(ctx, 0, 0);
  ctx.restore();
  ctx.fillStyle = "#f2f4f7";
  ctx.fillText("未開放", x + 220, cy);
  ctx.fillStyle = "#2f8cff";
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(x + 280, cy, 5.5, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#f2f4f7";
  ctx.fillText("自己", x + 291, cy);
}

export function atlasFrame(ctx: Ctx): void {
  const v = ctx.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, W * 0.7);
  v.addColorStop(0, "rgba(0,0,0,0)");
  v.addColorStop(1, "rgba(20,10,30,0.28)");
  ctx.fillStyle = v;
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = "#4a3020";
  ctx.lineWidth = 24;
  ctx.strokeRect(12, 12, W - 24, H - 24);
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, "#8a5f38");
  g.addColorStop(1, "#5a3c24");
  ctx.strokeStyle = g;
  ctx.lineWidth = 8;
  ctx.strokeRect(20, 20, W - 40, H - 40);
  ctx.strokeStyle = "#d8b860";
  ctx.lineWidth = 1.6;
  ctx.strokeRect(26, 26, W - 52, H - 52);
  for (const [cx, cy, sx, sy] of [[26, 26, 1, 1], [W - 26, 26, -1, 1], [26, H - 26, 1, -1], [W - 26, H - 26, -1, -1]] as const) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(sx, sy);
    ctx.strokeStyle = "#e6c878";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 34);
    ctx.lineTo(0, 0);
    ctx.lineTo(34, 0);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(10, 10, 6, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = "#e6c878";
    ctx.beginPath();
    ctx.arc(10, 10, 2.5, 0, TAU);
    ctx.fill();
    ctx.restore();
  }
}
