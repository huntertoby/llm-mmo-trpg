// 雲嶺的區域插畫地景（Phase 6F-ART1；docs/art/雲嶺區域插畫.md 第 2 節）。照樣張 `docs/art/sample/regionArt.js`
// 的 `painted` 分支移植：草地、霧河、冬湖、梯田、竹林、松林、北方雪山、雲海峽谷和吊橋、藥圃、源晶裂痕、斷崖、鎮旁小屋、地名小字。
// 樹和山避開地點用的是內容檔 `content/world/maps/cloud_ridge.yaml` 的全部 pos（含隱藏地點），寫死在這裡：
// 地景只跟區域有關，不能因為玩家發現了隱藏地點而改變（也不能從地景的空隙洩漏隱藏地點）。
import { CLOUD_FOG, H, mountain, P, pathThrough, pine, puff, rng, W, FONT, type Ctx, type Pt, type Rand, type RegionArtDef } from "./regionMapArt";

/** 雲嶺全部地點的 pos（避開用；含隱藏地點）。 */
export const POS: readonly Pt[] = [
  [10, 80], [25, 85], [30, 65], [45, 70], [50, 55], [15, 55], [60, 80], [35, 45], [60, 45],
  [75, 65], [90, 70], [25, 25], [15, 40], [70, 30], [50, 20], [30, 8], [75, 10], [5, 95],
];

function base(ctx: Ctx): void {
  const r = rng(11);
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#8e9a8c");
  g.addColorStop(0.35, "#86a06a");
  g.addColorStop(1, "#78a552");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 260; i++) {
    const x = r() * W;
    const y = r() * H;
    const rad = 15 + r() * 60;
    ctx.fillStyle = r() < 0.5 ? "rgba(60,100,40,0.10)" : "rgba(180,200,120,0.10)";
    ctx.beginPath();
    ctx.ellipse(x, y, rad, rad * 0.6, r() * 3, 0, Math.PI * 2);
    ctx.fill();
  }
}

function river(ctx: Ctx): void {
  const pts = ([[-2, 91], [8, 90], [18, 92], [32, 94], [48, 91], [62, 90], [74, 86], [86, 80], [102, 77]] as const).map((p) => P(p[0], p[1]));
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const line = (color: string, width: number): void => {
    pathThrough(ctx, pts);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  };
  line("#5e8a4a", 36);
  line("#3f7fb0", 26);
  line("#69a8d4", 14);
  ctx.setLineDash([10, 18]);
  line("rgba(255,255,255,0.55)", 2);
  ctx.setLineDash([]);
  const r = rng(5);
  for (const [x, y] of pts) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, 50);
    g.addColorStop(0, `rgba(255,255,255,${0.25 + r() * 0.2})`);
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - 60, y - 60, 120, 120);
  }
}

function lake(ctx: Ctx): void {
  const [x, y] = P(14, 37);
  ctx.beginPath();
  ctx.ellipse(x, y, 82, 46, -0.1, 0, Math.PI * 2);
  ctx.fillStyle = "#cfe4ee";
  ctx.fill();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 4;
  ctx.stroke();
  ctx.strokeStyle = "rgba(120,160,190,0.7)";
  ctx.lineWidth = 1.2;
  const r = rng(9);
  for (let i = 0; i < 8; i++) {
    ctx.beginPath();
    let px = x + (r() - 0.5) * 100;
    let py = y + (r() - 0.5) * 50;
    ctx.moveTo(px, py);
    for (let k = 0; k < 3; k++) {
      px += (r() - 0.5) * 30;
      py += (r() - 0.5) * 16;
      ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
}

function terraces(ctx: Ctx): void {
  const [cx, cy] = P(46, 77);
  for (let i = 9; i >= 0; i--) {
    const rad = 26 + i * 11;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rad * 1.5, rad, 0, Math.PI * 1.02, Math.PI * 1.98);
    ctx.strokeStyle = i % 2 ? "#9ccc6e" : "#b6dc87";
    ctx.lineWidth = 10;
    ctx.stroke();
    ctx.strokeStyle = "rgba(210,235,245,0.9)";
    ctx.lineWidth = 2;
    ctx.stroke();
  }
}

const LEAVES = ["#2f6b34", "#4f9a44", "#6cb455"] as const;

function bambooCluster(ctx: Ctx, x: number, y: number, r: Rand): void {
  const n = 3 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    const bx = x + (i - n / 2) * 5 + r() * 2;
    const h = 26 + r() * 14;
    ctx.strokeStyle = "#7fb24e";
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.moveTo(bx, y);
    ctx.lineTo(bx + 2, y - h);
    ctx.stroke();
    ctx.strokeStyle = "#4d7f33";
    ctx.lineWidth = 1.4;
    for (let k = 8; k < h; k += 8) {
      ctx.beginPath();
      ctx.moveTo(bx - 2, y - k);
      ctx.lineTo(bx + 3, y - k);
      ctx.stroke();
    }
    for (let k = 0; k < 5; k++) {
      ctx.fillStyle = LEAVES[k % 3] ?? "#4f9a44";
      ctx.save();
      ctx.translate(bx + 2, y - h + k * 5);
      ctx.rotate(-0.6 + r() * 1.2 + (k % 2 ? 0.9 : -0.9));
      ctx.beginPath();
      ctx.ellipse(6, 0, 8, 2.4, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }
}

function bamboo(ctx: Ctx): void {
  const r = rng(21);
  const items: Pt[] = [];
  for (let i = 0; i < 70; i++) {
    const a = r() * Math.PI * 2;
    const d = Math.sqrt(r()) * 13;
    const px = 27 + Math.cos(a) * d * 1.3;
    const py = 63 + Math.sin(a) * d * 0.8;
    if (Math.hypot(px - 30, py - 65) < 4.5) continue;
    items.push(P(px, py));
  }
  items.sort((a, b) => a[1] - b[1]).forEach(([x, y]) => bambooCluster(ctx, x, y, r));
}

const near = (px: number, py: number, d: number, yk = 1): boolean => POS.some(([x, y]) => Math.hypot(x - px, (y - py) * yk) < d);

function forests(ctx: Ctx): void {
  const r = rng(33);
  const spots = [[25, 28, 10], [35, 46, 7], [12, 52, 7], [48, 50, 6], [82, 60, 8], [22, 74, 6], [5, 68, 6], [66, 70, 6]] as const;
  const items: [number, number, number][] = [];
  for (const [cx, cy, rad] of spots) {
    for (let i = 0; i < 16; i++) {
      const a = r() * Math.PI * 2;
      const d = Math.sqrt(r()) * rad;
      const px = cx + Math.cos(a) * d * 1.2;
      const py = cy + Math.sin(a) * d * 0.7;
      if (near(px, py, 4.5)) continue;
      items.push([...P(px, py), 0.8 + r() * 0.5]);
    }
  }
  items.sort((a, b) => a[1] - b[1]).forEach(([x, y, k]) => pine(ctx, x, y, k));
}

function mountains(ctx: Ctx): void {
  const r = rng(47);
  const list: [number, number, number][] = [];
  for (let gx = -4; gx <= 104; gx += 6.5) {
    for (let gy = 6; gy <= 38; gy += 7) {
      const px = gx + (r() - 0.5) * 4;
      const py = gy + (r() - 0.5) * 4;
      const dSummit = Math.hypot(px - 75, py - 10);
      if (near(px, py, 5, 1.3)) continue;
      if (px > 6 && px < 24 && py > 31) continue; // 冬湖
      if (Math.abs((px - 50) * 0.6 - (py - 28) * 0.4) < 2 && py > 26) continue; // 峽谷
      list.push([px, py, 46 + (38 - py) * 1.6 + Math.max(0, 30 - dSummit) * 3 + r() * 20]);
    }
  }
  // 東側的崖、斷崖幫寨背後的石壁
  for (let i = 0; i < 9; i++) list.push([84 + r() * 18, 42 + r() * 22, 40 + r() * 25]);
  for (let i = 0; i < 4; i++) list.push([52 + r() * 6, 84 + r() * 3, 26 + r() * 10]);
  list.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => {
    const [x, y] = P(px, py);
    mountain(ctx, x, y, h, r, py < 30);
  });
}

function gorgeEdges(a: Pt, b: Pt, r: Rand): { left: Pt[]; right: Pt[]; nx: number; ny: number } {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len = Math.hypot(dx, dy);
  const nx = -dy / len;
  const ny = dx / len;
  const half = 34;
  const edge = (sign: number): Pt[] => {
    const pts: Pt[] = [];
    for (let t = 0; t <= 1.0001; t += 0.04) {
      const wob = Math.sin(t * 9 + sign) * 9 + (r() - 0.5) * 10;
      const taper = Math.min(1, t * 5, (1 - t) * 5) * 0.6 + 0.4;
      pts.push([a[0] + dx * t + nx * sign * (half + wob) * taper, a[1] + dy * t + ny * sign * (half + wob) * taper]);
    }
    return pts;
  };
  return { left: edge(1), right: edge(-1), nx, ny };
}

function tracePolygon(ctx: Ctx, pts: readonly Pt[]): void {
  ctx.beginPath();
  pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
  ctx.closePath();
}

function suspensionBridge(ctx: Ctx, nx: number, ny: number, ux: number, uy: number): void {
  const [bx, by] = P(60, 45);
  const bl = 74;
  const x1 = bx + nx * bl;
  const y1 = by + ny * bl;
  const x2 = bx - nx * bl;
  const y2 = by - ny * bl;
  const sag = 14;
  ctx.lineCap = "round";
  for (const off of [-5, 5]) {
    ctx.strokeStyle = "#4a3523";
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.moveTo(x1 + ux * off, y1 + uy * off);
    ctx.quadraticCurveTo(bx + ux * off, by + uy * off + sag, x2 + ux * off, y2 + uy * off);
    ctx.stroke();
  }
  ctx.strokeStyle = "#b08a5a";
  ctx.lineWidth = 3;
  for (let t = 0.04; t < 1; t += 0.07) {
    const q = (1 - t) * (1 - t);
    const m = 2 * t * (1 - t);
    const u = t * t;
    const cx = q * x1 + m * bx + u * x2;
    const cy = q * y1 + m * (by + sag) + u * y2;
    ctx.beginPath();
    ctx.moveTo(cx - ux * 5, cy - uy * 5);
    ctx.lineTo(cx + ux * 5, cy + uy * 5);
    ctx.stroke();
  }
  ctx.fillStyle = "#4a3523";
  for (const [px, py] of [[x1, y1], [x2, y2]] as const) ctx.fillRect(px - 3, py - 12, 6, 14);
}

/** 雲海峽谷（內有雲）和垂直穿過的吊橋。 */
function gorge(ctx: Ctx): void {
  const a = P(49, 27);
  const b = P(71, 61);
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len = Math.hypot(dx, dy);
  const r = rng(57);
  const { left, right, nx, ny } = gorgeEdges(a, b, r);
  const outline = [...left, ...right.slice().reverse()];
  tracePolygon(ctx, outline);
  ctx.fillStyle = "#33404c";
  ctx.fill();
  ctx.save();
  tracePolygon(ctx, outline);
  ctx.clip();
  tracePolygon(ctx, outline);
  ctx.strokeStyle = "#6f6152";
  ctx.lineWidth = 22;
  ctx.stroke();
  ctx.strokeStyle = "#54493e";
  ctx.lineWidth = 10;
  ctx.stroke();
  for (let t = 0; t < 1.05; t += 0.035) puff(ctx, a[0] + dx * t + (r() - 0.5) * 22, a[1] + dy * t + (r() - 0.5) * 18, 16 + r() * 12, 0.75);
  ctx.restore();
  tracePolygon(ctx, outline);
  ctx.strokeStyle = "#3a2f25";
  ctx.lineWidth = 2;
  ctx.stroke();
  suspensionBridge(ctx, nx, ny, dx / len, dy / len);
}

function herbs(ctx: Ctx, r: Rand): void {
  const [hx, hy] = P(76, 66);
  const colors = ["#d65f8a", "#f0d060", "#b47ad8"] as const;
  for (let i = 0; i < 18; i++) {
    const x = hx + (r() - 0.5) * 120;
    const y = hy + (r() - 0.5) * 60;
    if (Math.hypot(x - hx, y - hy) < 30) continue;
    ctx.fillStyle = colors[i % 3] ?? "#d65f8a";
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
  }
}

function smallTerrain(ctx: Ctx): void {
  const r = rng(71);
  herbs(ctx, r);
  // 源晶裂痕
  const [rx, ry] = P(50, 21);
  ctx.strokeStyle = "#b77bff";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(rx - 70, ry + 10);
  ctx.lineTo(rx - 30, ry - 6);
  ctx.lineTo(rx - 5, ry + 8);
  ctx.lineTo(rx + 30, ry - 10);
  ctx.lineTo(rx + 70, ry + 4);
  ctx.stroke();
  // 斷崖：寨子南邊的崖線
  const [fx, fy] = P(60, 80);
  ctx.strokeStyle = "#5b4a3a";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(fx - 80, fy + 34);
  for (let i = 1; i <= 8; i++) ctx.lineTo(fx - 80 + i * 20, fy + 34 + (i % 2 ? 8 : -2));
  ctx.stroke();
  ctx.fillStyle = "rgba(90,75,60,0.5)";
  for (let i = 0; i < 8; i++) ctx.fillRect(fx - 80 + i * 20, fy + 36, 14, 10 + (i % 3) * 4);
  // 霧渡鎮旁的小屋
  const [tx, ty] = P(10, 80);
  for (const [ox, oy] of [[-46, 8], [40, 14], [-30, -30], [34, -24]] as const) {
    const x = tx + ox;
    const y = ty + oy;
    ctx.fillStyle = "#e8dcc4";
    ctx.fillRect(x - 7, y - 6, 14, 9);
    ctx.fillStyle = "#3d5f7a";
    ctx.beginPath();
    ctx.moveTo(x - 10, y - 5);
    ctx.lineTo(x, y - 13);
    ctx.lineTo(x + 10, y - 5);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#27303a";
    ctx.lineWidth = 1;
    ctx.strokeRect(x - 7, y - 6, 14, 9);
  }
}

function terrainLabels(ctx: Ctx): void {
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `italic 15px ${FONT}`;
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  for (const [t, px, py] of [["霧　河", 36, 97.5], ["雲　海", 66, 55], ["梯　田", 40, 81.5], ["竹　林", 20, 70]] as const) {
    const [x, y] = P(px, py);
    ctx.fillText(t, x, y);
  }
}

function terrain(ctx: Ctx): void {
  base(ctx);
  river(ctx);
  lake(ctx);
  terraces(ctx);
  smallTerrain(ctx);
  forests(ctx);
  bamboo(ctx);
  mountains(ctx);
  gorge(ctx);
  terrainLabels(ctx);
}

/** 霧上露出的北方雪峰尖（只是地景，不洩漏地點）。 */
function afterFog(ctx: Ctx): void {
  const rr = rng(5);
  for (const [px, py, h] of [[72, 14, 120], [80, 16, 96], [64, 18, 80], [40, 12, 84], [18, 16, 72], [88, 22, 70]] as const) {
    const [x, y] = P(px, py);
    ctx.save();
    ctx.globalAlpha = 0.75;
    ctx.beginPath();
    ctx.rect(0, 0, W, y - h * 0.45);
    ctx.clip();
    mountain(ctx, x, y, h, rr, true);
    ctx.restore();
  }
}

export const CLOUD_RIDGE_ART: RegionArtDef = { terrain, afterFog, fog: CLOUD_FOG };
