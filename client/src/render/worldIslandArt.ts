// 大世界圖第 2 版的浮島本體（Phase 6F-ART1b；照 `docs/art/sample/worldPaintedArt.js` 的 drawIsland）。
// 島下四色岩層（左亮右暗、裂縫、垂根）、島緣厚度、頂面內緣陰影與左上高光；雲嶺有瀑布、荒原有熔岩瀑布流進雲海。
// 未開放的島：照該區地景畫出來，再去色、罩薄霧、纏雲，加金框鎖頭徽章。
// 樣張用 Path2D；這裡改成每次重描路徑（點先算好），測試的假 ctx 才記得到，也不依賴 Path2D。
import { mountain, pine, puff, rng, type Ctx, type Rand } from "./regionMapArt";
import { cloudPuff, LIGHT, lipDepth, medallion, TAU, type AtlasArtIsland, type IslandGeo } from "./worldMapArt";

type Pts = readonly (readonly [number, number])[];

/** 不規則圓形頂面的點（30 點，半徑 0.9～1.05 倍）。 */
export function blobPoints(g: IslandGeo): Pts {
  const r = rng(g.x * 3 + g.y);
  const n = 30;
  const pts: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU;
    const k = 0.9 + r() * 0.15;
    pts.push([g.x + Math.cos(a) * g.rx * k, g.y + Math.sin(a) * g.ry * k]);
  }
  return pts;
}

/** 描頂面路徑（`dy` 往下平移，島緣用）。 */
export function traceBlob(ctx: Ctx, pts: Pts, dy = 0): void {
  const n = pts.length;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const q = pts[i] as readonly [number, number];
    const nx = pts[(i + 1) % n] as readonly [number, number];
    const mx = (q[0] + nx[0]) / 2;
    const my = (q[1] + nx[1]) / 2 + dy;
    if (i === 0) ctx.moveTo(mx, my);
    else ctx.quadraticCurveTo(q[0], q[1] + dy, mx, my);
  }
  const p0 = pts[0] as readonly [number, number];
  const p1 = pts[1] as readonly [number, number];
  ctx.quadraticCurveTo(p0[0], p0[1] + dy, (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + dy);
  ctx.closePath();
}

const ROCK: Readonly<Record<string, readonly string[]>> = {
  cloud: ["#a08466", "#7a6048", "#5a4434", "#3a2a20"],
  capital: ["#b8a688", "#8e7c62", "#66563f", "#3e3326"],
  ashen: ["#6e4e40", "#54382c", "#3e2820", "#241612"],
  grey: ["#8c90a0", "#6c7080", "#4e5262", "#33364a"],
};
const LIP: Readonly<Record<string, string>> = { cloud: "#5e8a3e", capital: "#a69878", ashen: "#4a3028", grey: "#7c8090" };

function conePoints(g: IslandGeo, r: Rand): Pts {
  const { x, y, rx, ry } = g;
  const depth = lipDepth(g);
  const pts: [number, number][] = [[x - rx * 0.9, y + depth * 0.5]];
  const tips = 7;
  for (let k = 0; k <= tips * 2; k++) {
    const t = k / (tips * 2);
    const base = Math.sin(t * Math.PI);
    pts.push([x - rx * 0.9 + t * rx * 1.8, y + depth + (k % 2 ? base * ry * (1.2 + r() * 0.5) : base * ry * (0.55 + r() * 0.3))]);
  }
  pts.push([x + rx * 0.9, y + depth * 0.5]);
  return pts;
}

function tracePoly(ctx: Ctx, pts: Pts): void {
  ctx.beginPath();
  pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
  ctx.closePath();
}

function rockBands(ctx: Ctx, g: IslandGeo, pal: readonly string[]): void {
  const { x, y, rx, ry } = g;
  const depth = lipDepth(g);
  const bandH = ry * 0.55;
  for (let i = 0; i < 4; i++) {
    ctx.fillStyle = pal[i] ?? "#5a4434";
    ctx.beginPath();
    ctx.moveTo(x - rx, y + depth + i * bandH);
    for (let k = 0; k <= 12; k++) ctx.lineTo(x - rx + (k / 12) * rx * 2, y + depth + i * bandH + Math.sin(k * 1.7 + i) * 5);
    ctx.lineTo(x + rx, y + ry * 2.3); // 樣張寫 ry*4；反正被倒錐裁掉，收小才不超出離屏圖範圍
    ctx.lineTo(x - rx, y + ry * 2.3);
    ctx.closePath();
    ctx.fill();
  }
  const lg = ctx.createLinearGradient(x - rx, 0, x + rx, 0);
  lg.addColorStop(0, "rgba(255,240,210,0.18)");
  lg.addColorStop(0.45, "rgba(0,0,0,0)");
  lg.addColorStop(1, "rgba(10,10,30,0.45)");
  ctx.fillStyle = lg;
  ctx.fillRect(x - rx, y, rx * 2, ry * 2.3);
}

/** 島下的倒錐：四色岩層、右側壓暗、裂縫；雲嶺、主城有垂根。 */
function underside(ctx: Ctx, g: IslandGeo, pal: readonly string[]): void {
  const { x, y, rx, ry } = g;
  const depth = lipDepth(g);
  const r = rng(x * 5 + y);
  const cone = conePoints(g, r);
  ctx.save();
  tracePoly(ctx, cone);
  ctx.clip();
  rockBands(ctx, g, pal);
  ctx.strokeStyle = "rgba(20,14,10,0.35)";
  ctx.lineWidth = 1.4;
  for (let i = 0; i < 9; i++) {
    let cx = x - rx * 0.7 + r() * rx * 1.4;
    let cy = y + depth + r() * ry * 0.4;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    for (let k = 0; k < 4; k++) {
      cx += (r() - 0.5) * 10;
      cy += 8 + r() * 12;
      ctx.lineTo(cx, cy);
    }
    ctx.stroke();
  }
  ctx.restore();
  tracePoly(ctx, cone);
  ctx.strokeStyle = "rgba(20,14,10,0.55)";
  ctx.lineWidth = 1.5;
  ctx.stroke();
  if (g.kind === "cloud" || g.kind === "capital") {
    ctx.strokeStyle = "rgba(60,44,30,0.7)";
    ctx.lineWidth = 1.2;
    for (let i = 0; i < 10; i++) {
      const sx = x - rx * 0.8 + r() * rx * 1.6;
      const sy = y + depth + 4;
      const len = 16 + r() * 26;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.quadraticCurveTo(sx + (r() - 0.5) * 12, sy + len * 0.6, sx + (r() - 0.5) * 8, sy + len);
      ctx.stroke();
    }
  }
}

/** 島緣厚度：頂面往下一點的同形狀，左亮右暗。 */
function lip(ctx: Ctx, g: IslandGeo, top: Pts, col: string): void {
  const depth = lipDepth(g);
  traceBlob(ctx, top, depth);
  ctx.fillStyle = col;
  ctx.fill();
  ctx.save();
  traceBlob(ctx, top, depth);
  ctx.clip();
  const lg = ctx.createLinearGradient(g.x - g.rx, 0, g.x + g.rx, 0);
  lg.addColorStop(0, "rgba(255,240,210,0.2)");
  lg.addColorStop(1, "rgba(0,0,30,0.35)");
  ctx.fillStyle = lg;
  ctx.fillRect(g.x - g.rx, g.y, g.rx * 2, g.ry * 2);
  ctx.restore();
}

/** 頂面的立體感：內緣陰影＋左上邊緣高光。 */
function topShade(ctx: Ctx, g: IslandGeo, top: Pts): void {
  ctx.save();
  traceBlob(ctx, top);
  ctx.clip();
  ctx.lineWidth = 22;
  ctx.strokeStyle = "rgba(20,20,40,0.22)";
  ctx.stroke();
  ctx.lineWidth = 8;
  ctx.strokeStyle = "rgba(20,20,40,0.2)";
  ctx.stroke();
  const grad = ctx.createLinearGradient(g.x + LIGHT[0] * g.rx, g.y + LIGHT[1] * g.ry, g.x - LIGHT[0] * g.rx, g.y - LIGHT[1] * g.ry);
  grad.addColorStop(0, "rgba(255,240,200,0.14)");
  grad.addColorStop(0.5, "rgba(255,240,200,0)");
  grad.addColorStop(1, "rgba(20,20,50,0.22)");
  ctx.fillStyle = grad;
  ctx.fillRect(g.x - g.rx, g.y - g.ry, g.rx * 2, g.ry * 2);
  ctx.restore();
  traceBlob(ctx, top);
  ctx.strokeStyle = "rgba(30,24,18,0.55)";
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

/** 從島緣流進雲海的瀑布（`lava`＝熔岩瀑布）。 */
function fall(ctx: Ctx, x: number, y: number, len: number, lava: boolean): void {
  ctx.save();
  if (lava) {
    ctx.shadowColor = "#ff6a1a";
    ctx.shadowBlur = 14;
  }
  const g = ctx.createLinearGradient(0, y, 0, y + len);
  g.addColorStop(0, lava ? "rgba(255,150,60,0.95)" : "rgba(230,245,255,0.95)");
  g.addColorStop(1, lava ? "rgba(255,90,20,0)" : "rgba(200,225,245,0)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.moveTo(x - 5, y);
  ctx.lineTo(x + 5, y);
  ctx.lineTo(x + 9, y + len);
  ctx.lineTo(x - 9, y + len);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = lava ? "rgba(255,230,150,0.8)" : "rgba(255,255,255,0.9)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(x - 1, y);
  ctx.lineTo(x - 2, y + len * 0.7);
  ctx.stroke();
  ctx.restore();
  for (let i = 0; i < 3; i++) {
    if (lava) puff(ctx, x + (i - 1) * 12, y + len * 0.7, 14, 0.4, [120, 100, 90]);
    else cloudPuff(ctx, x + (i - 1) * 12, y + len * 0.8, 14, 0.6);
  }
}

// ---------------------------------------------------------------------------
// 各島頂面
// ---------------------------------------------------------------------------

function speckles(ctx: Ctx, g: IslandGeo, r: Rand, n: number, dark: string, light: string, w: [number, number], h: [number, number]): void {
  for (let i = 0; i < n; i++) {
    ctx.fillStyle = i % 2 ? dark : light;
    ctx.beginPath();
    ctx.ellipse(g.x + (r() - 0.5) * g.rx * 2, g.y + (r() - 0.5) * g.ry * 2, w[0] + r() * w[1], h[0] + r() * h[1], r() * 3, 0, TAU);
    ctx.fill();
  }
}

function cloudRiver(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  ctx.lineCap = "round";
  ctx.strokeStyle = "#356b94";
  ctx.lineWidth = 11;
  ctx.beginPath();
  ctx.moveTo(x - rx * 1.05, y + ry * 0.5);
  ctx.bezierCurveTo(x - 60, y + ry * 0.95, x + 40, y + ry * 0.2, x + rx * 1.05, y + ry * 0.45);
  ctx.stroke();
  ctx.strokeStyle = "#5c9cc8";
  ctx.lineWidth = 6;
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.6)";
  ctx.lineWidth = 1.2;
  ctx.setLineDash([6, 10]);
  ctx.stroke();
  ctx.setLineDash([]);
}

function cloudTerraces(ctx: Ctx, g: IslandGeo): void {
  for (let i = 5; i >= 0; i--) {
    ctx.beginPath();
    ctx.ellipse(g.x + 20, g.y + 34, 18 + i * 7, 10 + i * 4, 0, Math.PI * 1.05, Math.PI * 1.95);
    ctx.strokeStyle = i % 2 ? "#93c466" : "#b6dc87";
    ctx.lineWidth = 4.5;
    ctx.stroke();
    ctx.strokeStyle = "rgba(225,240,250,0.8)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

function cloudWoods(ctx: Ctx, g: IslandGeo, r: Rand): void {
  const { x, y, rx, ry } = g;
  for (let i = 0; i < 34; i++) {
    const bx = x - rx * 0.62 + r() * 80;
    const by = y + 4 + r() * 46;
    ctx.strokeStyle = "#5c9c48";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx + 1, by - 13);
    ctx.stroke();
    ctx.fillStyle = ["#2f6b34", "#4f9a44", "#6cb455"][i % 3] ?? "#4f9a44";
    ctx.beginPath();
    ctx.ellipse(bx + 3, by - 12, 4.5, 1.6, -0.5, 0, TAU);
    ctx.fill();
  }
  const trees: [number, number][] = [];
  for (let i = 0; i < 22; i++) trees.push([x + rx * 0.15 + r() * rx * 0.7, y - ry * 0.05 + r() * ry * 0.4]);
  trees.sort((a, b) => a[1] - b[1]).forEach(([tx, ty]) => pine(ctx, tx, ty, 0.6));
  for (const [ox, oy] of [[-rx * 0.55, ry * 0.32], [-rx * 0.45, ry * 0.4], [-rx * 0.62, ry * 0.45]] as const) {
    const hx = x + ox;
    const hy = y + oy;
    ctx.fillStyle = "#efe4cc";
    ctx.fillRect(hx - 5, hy - 4, 10, 7);
    ctx.fillStyle = "#c0503a";
    ctx.beginPath();
    ctx.moveTo(hx - 7, hy - 3);
    ctx.lineTo(hx, hy - 9);
    ctx.lineTo(hx + 7, hy - 3);
    ctx.fill();
  }
}

function topCloud(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  const r = rng(311);
  ctx.fillStyle = "#7fa65a";
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  speckles(ctx, g, r, 60, "rgba(60,100,40,0.16)", "rgba(190,210,120,0.16)", [14, 22], [8, 8]);
  cloudRiver(ctx, g);
  cloudTerraces(ctx, g);
  cloudWoods(ctx, g, r);
  const pk: [number, number, number][] = [];
  for (let i = 0; i < 12; i++) pk.push([x - rx * 0.78 + i * rx * 0.14 + (r() - 0.5) * 10, y - ry * 0.22 + (r() - 0.5) * 16, 32 + r() * 30 + (i > 7 ? 14 : 0)]);
  pk.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => mountain(ctx, px, py, h, r, true));
  for (let i = 0; i < 5; i++) cloudPuff(ctx, x - rx * 0.55 + i * rx * 0.28, y - 2 + (r() - 0.5) * 8, 13, 0.55);
}

function ashenCracksAndSand(ctx: Ctx, g: IslandGeo, r: Rand): void {
  const { x, y, rx, ry } = g;
  ctx.save();
  ctx.strokeStyle = "#ff7a1a";
  ctx.lineWidth = 1.4;
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 6;
  for (let i = 0; i < 8; i++) {
    let cx = x + (r() - 0.5) * rx * 1.6;
    let cy = y + (r() - 0.3) * ry;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    for (let k = 0; k < 3; k++) {
      cx += (r() - 0.5) * 22;
      cy += (r() - 0.5) * 10;
      ctx.lineTo(cx, cy);
    }
    ctx.stroke();
  }
  ctx.restore();
  for (let i = 0; i < 8; i++) {
    const sx = x - rx * 0.55 + i * 26;
    const sy = y + ry * 0.62 + (i % 2) * 6;
    ctx.fillStyle = "rgba(220,140,80,0.6)";
    ctx.beginPath();
    ctx.ellipse(sx, sy, 18, 6, 0, Math.PI, TAU);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,210,160,0.5)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(sx, sy, 13, 4, 0, Math.PI * 1.15, Math.PI * 1.85);
    ctx.stroke();
  }
}

function lavaRiver(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  ctx.save();
  ctx.lineCap = "round";
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 16;
  ctx.beginPath();
  ctx.moveTo(x + rx * 0.38, y - ry * 0.2);
  ctx.bezierCurveTo(x + 10, y + 10, x + rx * 0.5, y + ry * 0.5, x + rx * 1.05, y + ry * 0.3);
  for (const [col, lw] of [["#2a1610", 14], ["#c2410c", 10], ["#ff8a2a", 5], ["#ffd36b", 1.5]] as const) {
    ctx.strokeStyle = col;
    ctx.lineWidth = lw;
    ctx.stroke();
  }
  ctx.restore();
}

function topAshen(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  const r = rng(313);
  const grad = ctx.createLinearGradient(0, y - ry, 0, y + ry);
  grad.addColorStop(0, "#3e302a");
  grad.addColorStop(0.5, "#6b5240");
  grad.addColorStop(1, "#a7744a");
  ctx.fillStyle = grad;
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  speckles(ctx, g, r, 50, "rgba(25,18,14,0.16)", "rgba(210,130,70,0.14)", [12, 18], [6, 6]);
  ashenCracksAndSand(ctx, g, r);
  lavaRiver(ctx, g);
  for (let i = 0; i < 24; i++) {
    const tx = x - rx * 0.45 + r() * 100;
    const ty = y + r() * 34 - 6;
    ctx.strokeStyle = "#241a16";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(tx, ty);
    ctx.lineTo(tx, ty - 11);
    ctx.moveTo(tx, ty - 6);
    ctx.lineTo(tx - 4, ty - 10);
    ctx.moveTo(tx, ty - 8);
    ctx.lineTo(tx + 4, ty - 13);
    ctx.stroke();
  }
  const pk: [number, number, number][] = [];
  for (let i = 0; i < 8; i++) pk.push([x - rx * 0.72 + i * 30, y - ry * 0.32 + (r() - 0.5) * 12, 24 + r() * 16]);
  pk.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => mountain(ctx, px, py, h, r, false, ["#86705f", "#40332b"]));
}

function volcano(ctx: Ctx, g: IslandGeo): void {
  const vx = g.x + g.rx * 0.4;
  const vy = g.y + g.ry * 0.02;
  ctx.fillStyle = "#5e4c42";
  ctx.beginPath();
  ctx.moveTo(vx - 52, vy + 8);
  ctx.lineTo(vx - 12, vy - 56);
  ctx.lineTo(vx + 2, vy + 8);
  ctx.fill();
  ctx.fillStyle = "#2f241c";
  ctx.beginPath();
  ctx.moveTo(vx - 12, vy - 56);
  ctx.lineTo(vx + 12, vy - 56);
  ctx.lineTo(vx + 52, vy + 8);
  ctx.lineTo(vx + 2, vy + 8);
  ctx.fill();
  ctx.strokeStyle = "rgba(20,14,10,0.6)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(vx - 52, vy + 8);
  ctx.lineTo(vx - 12, vy - 56);
  ctx.lineTo(vx + 12, vy - 56);
  ctx.lineTo(vx + 52, vy + 8);
  ctx.stroke();
  ctx.save();
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 20;
  ctx.fillStyle = "#ff8a2a";
  ctx.beginPath();
  ctx.ellipse(vx, vy - 56, 13, 4, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#ff7a1a";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(vx - 4, vy - 54);
  ctx.quadraticCurveTo(vx - 18, vy - 30, vx - 10, vy + 4);
  ctx.stroke();
  ctx.restore();
  for (let i = 0; i < 9; i++) puff(ctx, vx - i * 12, vy - 66 - i * 7, 10 + i * 2.4, 0.5 - i * 0.04, [96, 84, 78]);
}

function capitalHouse(ctx: Ctx, hx: number, hy: number): void {
  ctx.fillStyle = "rgba(40,40,60,0.25)";
  ctx.fillRect(hx - 8, hy + 4, 20, 4);
  ctx.fillStyle = "#faf4e6";
  ctx.fillRect(hx - 9, hy - 6, 18, 11);
  ctx.fillStyle = "#e4dccb";
  ctx.fillRect(hx + 3, hy - 6, 6, 11);
  ctx.fillStyle = "#3a5ad0";
  ctx.beginPath();
  ctx.moveTo(hx - 12, hy - 5);
  ctx.lineTo(hx, hy - 15);
  ctx.lineTo(hx + 12, hy - 5);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#2a43a6";
  ctx.beginPath();
  ctx.moveTo(hx, hy - 15);
  ctx.lineTo(hx + 12, hy - 5);
  ctx.lineTo(hx + 2, hy - 5);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#4a6a8a";
  ctx.fillRect(hx - 5, hy - 2, 3, 3);
}

const HOUSES: readonly (readonly [number, number])[] = [[-92, -6], [-56, -40], [-40, 22], [-100, 22], [46, -42], [88, -10], [44, 26], [96, 24], [-18, -48], [20, -50]];

function topCapital(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry } = g;
  const r = rng(317);
  ctx.fillStyle = "#ddd2b8";
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  for (const [ox, oy] of [[-72, -30], [72, -30], [-74, 30], [74, 30]] as const) {
    ctx.fillStyle = "#86b862";
    ctx.beginPath();
    ctx.ellipse(x + ox, y + oy, 28, 15, 0, 0, TAU);
    ctx.fill();
    for (let k = 0; k < 5; k++) {
      ctx.fillStyle = ["#f2c230", "#e06a8a", "#ffffff"][k % 3] ?? "#ffffff";
      ctx.beginPath();
      ctx.arc(x + ox + (r() - 0.5) * 36, y + oy + (r() - 0.5) * 16, 1.6, 0, TAU);
      ctx.fill();
    }
  }
  ctx.fillStyle = "#c6b693";
  ctx.fillRect(x - rx, y - 7, rx * 2, 14);
  ctx.fillRect(x - 7, y - ry, 14, ry * 2);
  ctx.strokeStyle = "rgba(110,95,70,0.35)";
  ctx.lineWidth = 1;
  for (let k = -rx; k < rx; k += 10) {
    ctx.beginPath();
    ctx.moveTo(x + k, y - 7);
    ctx.lineTo(x + k, y + 7);
    ctx.stroke();
  }
  ctx.fillStyle = "#e8dfc8";
  ctx.beginPath();
  ctx.ellipse(x, y, 30, 17, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#a99a78";
  ctx.lineWidth = 1.5;
  ctx.stroke();
  [...HOUSES].sort((a, b) => a[1] - b[1]).forEach(([ox, oy]) => capitalHouse(ctx, x + ox, y + oy));
  ctx.save();
  ctx.strokeStyle = "#f2ead6";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.ellipse(x, y, rx * 0.86, ry * 0.82, 0, 0, TAU);
  ctx.stroke();
  ctx.strokeStyle = "rgba(120,105,80,0.6)";
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.restore();
}

function tower(ctx: Ctx, g: IslandGeo): void {
  const { x, y } = g;
  const grad = ctx.createRadialGradient(x, y - 60, 0, x, y - 60, 90);
  grad.addColorStop(0, "rgba(180,160,255,0.55)");
  grad.addColorStop(1, "rgba(180,160,255,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(x - 90, y - 150, 180, 180);
  ctx.fillStyle = "#f6efe0";
  ctx.strokeStyle = "#3a3550";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.ellipse(x, y, 18, 9, 0, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#e4dccb";
  ctx.fillRect(x - 12, y - 10, 24, 10);
  ctx.strokeRect(x - 12, y - 10, 24, 10);
  ctx.fillStyle = "#e8e0ff";
  ctx.beginPath();
  ctx.moveTo(x - 10, y - 10);
  ctx.lineTo(x, y - 96);
  ctx.lineTo(x, y - 10);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#9d8ef0";
  ctx.beginPath();
  ctx.moveTo(x, y - 96);
  ctx.lineTo(x + 10, y - 10);
  ctx.lineTo(x, y - 10);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#3a3550";
  ctx.beginPath();
  ctx.moveTo(x - 10, y - 10);
  ctx.lineTo(x, y - 96);
  ctx.lineTo(x + 10, y - 10);
  ctx.stroke();
  for (const [ox, oy, s] of [[-26, -70, 5], [24, -58, 4], [-18, -40, 3.5], [30, -86, 3]] as const) {
    ctx.fillStyle = "#cfc4ff";
    ctx.beginPath();
    ctx.moveTo(x + ox, y + oy - s * 1.6);
    ctx.lineTo(x + ox + s, y + oy);
    ctx.lineTo(x + ox, y + oy + s * 1.6);
    ctx.lineTo(x + ox - s, y + oy);
    ctx.closePath();
    ctx.fill();
  }
}

const LATER_GROUND: Readonly<Record<string, string>> = { crown: "#d8ccb0", arcane: "#5a5248", frost: "#cfe0ea" };

/** 之後的區（晶冠、樞市、霜潮）的地景；之後才會去色、罩霧。沒有畫法的區只鋪底色。 */
function topLater(ctx: Ctx, g: IslandGeo): void {
  const { x, y, rx, ry, kind } = g;
  const r = rng(x);
  ctx.fillStyle = LATER_GROUND[kind] ?? "#c8ccd4";
  ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
  if (kind === "crown") {
    for (let i = 0; i < 9; i++) {
      const cx = x - rx * 0.65 + i * rx * 0.16;
      const h = 16 + r() * 26;
      ctx.fillStyle = "#b9a4ff";
      ctx.beginPath();
      ctx.moveTo(cx - 6, y + 8);
      ctx.lineTo(cx, y + 8 - h);
      ctx.lineTo(cx + 6, y + 8);
      ctx.fill();
      ctx.fillStyle = "#e8e0ff";
      ctx.beginPath();
      ctx.moveTo(cx - 6, y + 8);
      ctx.lineTo(cx, y + 8 - h);
      ctx.lineTo(cx, y + 8);
      ctx.fill();
    }
  } else if (kind === "arcane") {
    for (let i = 0; i < 9; i++) {
      const tx = x - rx * 0.62 + i * rx * 0.15;
      const h = 18 + r() * 22;
      ctx.fillStyle = "#8a7a66";
      ctx.fillRect(tx, y - h, 12, h + 6);
      ctx.fillStyle = "#4ad6c8";
      ctx.fillRect(tx + 3, y - h + 4, 3, 3);
    }
  } else if (kind === "frost") {
    ctx.fillStyle = "#4f8fb8";
    ctx.beginPath();
    ctx.ellipse(x + 20, y + 8, rx * 0.6, ry * 0.5, 0, 0, TAU);
    ctx.fill();
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = "#f2f8ff";
      ctx.beginPath();
      ctx.ellipse(x - rx * 0.4 + i * 30, y + (r() - 0.5) * 30, 10, 5, 0, 0, TAU);
      ctx.fill();
    }
  }
}

/** 已開放但還沒有地景畫法的區（之後開放的區先用這個）：淡綠的頂面。 */
function topPlain(ctx: Ctx, g: IslandGeo): void {
  ctx.fillStyle = "#9ab07a";
  ctx.fillRect(g.x - g.rx, g.y - g.ry, g.rx * 2, g.ry * 2);
}

const OPEN_TOPS: Readonly<Record<string, (ctx: Ctx, g: IslandGeo) => void>> = { cloud: topCloud, ashen: topAshen, capital: topCapital };

/** 島的地景本身（未去色）：岩層、島緣、頂面、陰影；已開放的另有晶塔、火山、瀑布。 */
function rawIsland(ctx: Ctx, g: IslandGeo, open: boolean): void {
  const top = blobPoints(g);
  underside(ctx, g, open ? (ROCK[g.kind] ?? ROCK.cloud ?? []) : (ROCK.grey ?? []));
  lip(ctx, g, top, open ? (LIP[g.kind] ?? "#5e8a3e") : (LIP.grey ?? "#7c8090"));
  ctx.save();
  traceBlob(ctx, top);
  ctx.clip();
  const openTop = OPEN_TOPS[g.kind];
  if (open) (openTop ?? topPlain)(ctx, g);
  else (openTop ?? topLater)(ctx, g);
  ctx.restore();
  topShade(ctx, g, top);
  if (!open) return;
  if (g.kind === "capital") tower(ctx, g);
  if (g.kind === "ashen") volcano(ctx, g);
  if (g.kind === "cloud") fall(ctx, g.x + g.rx * 0.8, g.y + g.ry * 0.5, 150, false);
  if (g.kind === "ashen") fall(ctx, g.x + g.rx * 0.82, g.y + g.ry * 0.4, 110, true);
}

/** 未開放：霧纏住（光暈＋兩層壓扁的雲）。 */
function lockedHaze(ctx: Ctx, g: IslandGeo): void {
  const r = rng(g.x + 7);
  const hz = ctx.createRadialGradient(g.x, g.y, g.rx * 0.2, g.x, g.y, g.rx * 1.2);
  hz.addColorStop(0, "rgba(236,240,248,0.45)");
  hz.addColorStop(1, "rgba(236,240,248,0)");
  ctx.fillStyle = hz;
  ctx.beginPath();
  ctx.ellipse(g.x, g.y + g.ry * 0.3, g.rx * 1.25, g.ry * 1.6, 0, 0, TAU);
  ctx.fill();
  const tint = [246, 246, 250] as const;
  const shade = [176, 184, 206] as const;
  for (let i = 0; i < 16; i++) cloudPuff(ctx, g.x - g.rx * 1.05 + r() * g.rx * 2.1, g.y + g.ry * (0.35 + r() * 0.8), 20 + r() * 20, 0.7, tint, shade, 0.5);
  for (let i = 0; i < 5; i++) cloudPuff(ctx, g.x - g.rx * 0.9 + r() * g.rx * 1.8, g.y - g.ry * 0.1 + r() * g.ry * 0.4, 16 + r() * 12, 0.45, tint, shade, 0.45);
}

/** 暫存畫布（未開放的島先畫在這裡再去色貼回）；`ctx` 已設好和目標同樣的變換。 */
export interface Scratch {
  ctx: Ctx;
  image: CanvasImageSource;
}

/** 一座浮島的本體（不含字牌、傳送鈕、自己；那些在 `islandMarks`）。 */
export function islandBody(ctx: Ctx, is: AtlasArtIsland, scratch: () => Scratch | null): void {
  const g = is.geo;
  if (is.status === "open") {
    ctx.save();
    ctx.filter = "saturate(1.15) contrast(1.06)";
    rawIsland(ctx, g, true);
    ctx.restore();
    return;
  }
  const tmp = scratch();
  ctx.save();
  if (tmp === null) {
    ctx.filter = "grayscale(0.85) brightness(0.92) contrast(0.85)";
    ctx.globalAlpha = 0.82;
    rawIsland(ctx, g, false);
  } else {
    rawIsland(tmp.ctx, g, false);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.filter = "grayscale(0.85) brightness(0.92) contrast(0.85)";
    ctx.globalAlpha = 0.82;
    ctx.drawImage(tmp.image, 0, 0);
  }
  ctx.restore();
  lockedHaze(ctx, g);
  medallion(ctx, g.x, g.y - 2);
}

/** 浮島本體的範圍（邏輯座標；離屏快取用，含晶塔、火山煙、瀑布、纏雲）。 */
export function bodyBounds(g: IslandGeo): { x: number; y: number; w: number; h: number } {
  const half = g.rx * 1.3 + 30;
  const top = g.y - Math.max(g.ry + 20, 165);
  const bottom = g.y + Math.max(g.ry * 2.3, g.ry * 0.5 + 175, g.ry * 1.95 + 40) + 12;
  return { x: g.x - half, y: top, w: half * 2, h: bottom - top };
}
