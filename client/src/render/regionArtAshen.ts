// 灰燼荒原的區域插畫地景（Phase 6F-ART1；docs/art/雲嶺區域插畫.md 第 2 節）。照樣張 `docs/art/sample/ashenRegionArt.js` 移植：
// 焦土（發光裂縫）、灰河、赤沙、灰泥沼、焦油坑、冷卻井（4 口）、熔岩河和石橋、枯木林、北方岩山、東北火山、廢墟要塞、飄散的火星、地名小字。
// 避開地點用內容檔 `content/world/maps/ashen_waste.yaml` 的全部 pos（含隱藏地點），理由同 `regionArtCloud.ts`。
import { FONT, H, mountain, P, pathThrough, puff, rng, W, type Ctx, type Pt, type Rand, type RegionArtDef } from "./regionMapArt";

export const POS: readonly Pt[] = [
  [15, 80], [5, 95], [32, 72], [20, 56], [48, 62], [40, 88], [12, 40], [34, 44], [64, 70],
  [8, 24], [46, 30], [80, 78], [94, 90], [30, 12], [62, 34], [84, 44], [66, 14], [90, 8],
];
const LAVA: readonly Pt[] = [[89, 11], [86, 20], [80, 30], [74, 40], [72, 52], [78, 60], [90, 62], [102, 60]];
const ROCK = ["#7a685c", "#43372f"] as const;

const near = (px: number, py: number, d: number, yk = 1): boolean => POS.some(([x, y]) => Math.hypot(x - px, (y - py) * yk) < d);

function cracks(ctx: Ctx, r: Rand): void {
  for (let i = 0; i < 26; i++) {
    let x = r() * W;
    let y = r() * H;
    const glow = i % 3 === 0;
    ctx.save();
    ctx.strokeStyle = glow ? "#ff7a1a" : "rgba(30,20,15,0.6)";
    ctx.lineWidth = glow ? 2 : 1.5;
    if (glow) {
      ctx.shadowColor = "#ff6a1a";
      ctx.shadowBlur = 8;
    }
    ctx.beginPath();
    ctx.moveTo(x, y);
    for (let k = 0; k < 4; k++) {
      x += (r() - 0.5) * 40;
      y += (r() - 0.3) * 20;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();
  }
}

function base(ctx: Ctx): void {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#3d302b");
  g.addColorStop(0.4, "#6b5848");
  g.addColorStop(0.8, "#94714f");
  g.addColorStop(1, "#b07a4c");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  const r = rng(201);
  const tones = ["rgba(30,22,18,0.12)", "rgba(150,110,80,0.12)", "rgba(120,60,30,0.10)"] as const;
  for (let i = 0; i < 300; i++) {
    const x = r() * W;
    const y = r() * H;
    const rad = 15 + r() * 60;
    ctx.fillStyle = tones[i % 3] ?? tones[0];
    ctx.beginPath();
    ctx.ellipse(x, y, rad, rad * 0.6, r() * 3, 0, Math.PI * 2);
    ctx.fill();
  }
  cracks(ctx, r);
}

function ashRiver(ctx: Ctx): void {
  const pts = ([[-2, 85], [7, 89], [12, 95], [16, 103]] as const).map((p) => P(p[0], p[1]));
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const [color, width] of [["#4a3e36", 36], ["#5f7178", 26], ["#8a9ca2", 10]] as const) {
    pathThrough(ctx, pts);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  }
}

function lavaCrust(ctx: Ctx, pts: readonly Pt[]): void {
  const r = rng(207);
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i] as Pt;
    const b = pts[i + 1] as Pt;
    for (let t = 0.2; t < 1; t += 0.3) {
      const x = a[0] + (b[0] - a[0]) * t + (r() - 0.5) * 10;
      const y = a[1] + (b[1] - a[1]) * t + (r() - 0.5) * 8;
      ctx.fillStyle = "rgba(50,25,15,0.75)";
      ctx.beginPath();
      ctx.ellipse(x, y, 5 + r() * 5, 3 + r() * 2, r() * 3, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function lavaRiver(ctx: Ctx): void {
  const pts = LAVA.map((p) => P(p[0], p[1]));
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.save();
  const line = (color: string, width: number): void => {
    pathThrough(ctx, pts);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  };
  line("#2a1610", 42);
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 24;
  line("#c2410c", 28);
  line("#ff7a1a", 16);
  ctx.shadowBlur = 0;
  line("#ffd36b", 4);
  ctx.restore();
  lavaCrust(ctx, pts);
  // 熔岩洞窟－角魔古祭壇之間的石橋
  const [bx, by] = P(75, 39);
  ctx.save();
  ctx.translate(bx, by);
  ctx.rotate(0.25);
  ctx.fillStyle = "#6e6258";
  ctx.fillRect(-34, -8, 68, 16);
  ctx.strokeStyle = "#2b221d";
  ctx.lineWidth = 2;
  ctx.strokeRect(-34, -8, 68, 16);
  for (let k = -26; k <= 26; k += 13) {
    ctx.beginPath();
    ctx.moveTo(k, -8);
    ctx.lineTo(k, 8);
    ctx.stroke();
  }
  ctx.restore();
}

function volcanoShape(ctx: Ctx): Pt {
  const [x, y] = P(89, 26);
  const h = 190;
  const w = 170;
  ctx.fillStyle = "#5a4a42";
  ctx.beginPath();
  ctx.moveTo(x - w, y);
  ctx.lineTo(x - 34, y - h);
  ctx.lineTo(x, y - h + 6);
  ctx.lineTo(x + 4, y);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#33281f";
  ctx.beginPath();
  ctx.moveTo(x, y - h + 6);
  ctx.lineTo(x + 34, y - h);
  ctx.lineTo(x + w, y);
  ctx.lineTo(x + 4, y);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(25,18,14,0.8)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x - w, y);
  ctx.lineTo(x - 34, y - h);
  ctx.moveTo(x + 34, y - h);
  ctx.lineTo(x + w, y);
  ctx.stroke();
  // 火口與流下來的熔岩
  ctx.save();
  ctx.shadowColor = "#ff6a1a";
  ctx.shadowBlur = 30;
  ctx.fillStyle = "#ff8a2a";
  ctx.beginPath();
  ctx.ellipse(x, y - h + 2, 36, 9, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ffd36b";
  ctx.beginPath();
  ctx.ellipse(x, y - h + 2, 20, 4, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#ff7a1a";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(x - 12, y - h + 8);
  ctx.quadraticCurveTo(x - 30, y - h * 0.5, x - 20, y - 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x + 16, y - h + 8);
  ctx.quadraticCurveTo(x + 40, y - h * 0.55, x + 70, y - 30);
  ctx.stroke();
  ctx.restore();
  return [x, y - h];
}

function plume(ctx: Ctx, x: number, y: number): void {
  const r = rng(211);
  for (let i = 0; i < 14; i++) {
    const t = i / 14;
    puff(ctx, x - t * 160 + (r() - 0.5) * 20, y - 20 - t * 60 + (r() - 0.5) * 16, 18 + t * 30, 0.55 - t * 0.25, [92, 80, 74]);
  }
}

function ridges(ctx: Ctx): void {
  const r = rng(223);
  const list: [number, number, number][] = [];
  for (let gx = -4; gx <= 76; gx += 6.5) {
    for (let gy = 4; gy <= 22; gy += 6) {
      const px = gx + (r() - 0.5) * 4;
      const py = gy + (r() - 0.5) * 3;
      if (near(px, py, 5.5, 1.3)) continue;
      list.push([px, py, 40 + (24 - py) * 2 + r() * 22]);
    }
  }
  // 東側和南邊的岩台
  for (let i = 0; i < 6; i++) list.push([92 + r() * 10, 36 + r() * 16, 36 + r() * 20]);
  for (let i = 0; i < 4; i++) list.push([62 + r() * 10, 86 + r() * 8, 26 + r() * 12]);
  list.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => {
    const [x, y] = P(px, py);
    mountain(ctx, x, y, h, r, false, ROCK);
  });
}

function deadTree(ctx: Ctx, x: number, y: number, k: number, r: Rand): void {
  ctx.strokeStyle = "#2e2420";
  ctx.lineCap = "round";
  ctx.lineWidth = 3 * k;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x, y - 22 * k);
  ctx.stroke();
  ctx.lineWidth = 1.6 * k;
  for (const [sx, sy, ex, ey] of [[0, -12, -9, -20], [0, -16, 8, -26], [0, -22, -4, -30], [-5, -17, -10, -16]] as const) {
    ctx.beginPath();
    ctx.moveTo(x + sx * k, y + sy * k);
    ctx.lineTo(x + (ex + (r() - 0.5) * 3) * k, y + ey * k);
    ctx.stroke();
  }
}

function deadwood(ctx: Ctx): void {
  const r = rng(227);
  const [cx, cy] = P(48, 62);
  const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 130);
  g.addColorStop(0, "rgba(60,52,48,0.45)");
  g.addColorStop(1, "rgba(60,52,48,0)");
  ctx.fillStyle = g;
  ctx.fillRect(cx - 140, cy - 140, 280, 280);
  const items: [number, number, number][] = [];
  for (let i = 0; i < 60; i++) {
    const a = r() * Math.PI * 2;
    const d = Math.sqrt(r()) * 12;
    const px = 48 + Math.cos(a) * d * 1.3;
    const py = 62 + Math.sin(a) * d * 0.8;
    if (near(px, py, 4.5)) continue;
    items.push([...P(px, py), 0.8 + r() * 0.5]);
  }
  items.sort((a, b) => a[1] - b[1]).forEach(([x, y, k]) => deadTree(ctx, x, y, k, r));
}

function mire(ctx: Ctx): void {
  const [x, y] = P(12, 40);
  ctx.fillStyle = "#4e4a3c";
  ctx.beginPath();
  ctx.ellipse(x + 10, y + 6, 92, 50, 0.1, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#666049";
  ctx.beginPath();
  ctx.ellipse(x + 18, y + 2, 64, 32, 0.1, 0, Math.PI * 2);
  ctx.fill();
  const r = rng(229);
  ctx.strokeStyle = "rgba(200,190,160,0.6)";
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 12; i++) {
    ctx.beginPath();
    ctx.arc(x + (r() - 0.4) * 120, y + (r() - 0.5) * 60, 2 + r() * 4, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.strokeStyle = "#6f6a3a";
  ctx.lineWidth = 1.6;
  for (let i = 0; i < 18; i++) {
    const rx = x - 70 + r() * 170;
    const ry = y - 40 + r() * 90;
    ctx.beginPath();
    ctx.moveTo(rx, ry);
    ctx.lineTo(rx + (r() - 0.5) * 4, ry - 10 - r() * 8);
    ctx.stroke();
  }
}

function tarPits(ctx: Ctx): void {
  const [x, y] = P(46, 30);
  for (const [ox, oy, rx, ry] of [[-60, 10, 34, 16], [50, 18, 30, 14], [-10, -34, 26, 12], [30, -20, 18, 9], [-50, -24, 16, 8]] as const) {
    ctx.fillStyle = "#0f0c0b";
    ctx.beginPath();
    ctx.ellipse(x + ox, y + oy, rx, ry, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#3a2e28";
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.fillStyle = "rgba(170,160,200,0.35)";
    ctx.beginPath();
    ctx.ellipse(x + ox - rx * 0.3, y + oy - ry * 0.3, rx * 0.35, ry * 0.25, 0, 0, Math.PI * 2);
    ctx.fill();
  }
}

function coolingWells(ctx: Ctx): void {
  const [x, y] = P(34, 44);
  for (const [ox, oy] of [[-46, -18], [46, -18], [-50, 22], [50, 22]] as const) {
    ctx.fillStyle = "#8a8078";
    ctx.beginPath();
    ctx.arc(x + ox, y + oy, 11, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#2b221d";
    ctx.lineWidth = 1.6;
    ctx.stroke();
    ctx.fillStyle = "#4aa3d8";
    ctx.beginPath();
    ctx.arc(x + ox, y + oy, 6.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(220,245,255,0.8)";
    ctx.beginPath();
    ctx.arc(x + ox - 2, y + oy - 2, 2, 0, Math.PI * 2);
    ctx.fill();
  }
}

function redSand(ctx: Ctx): void {
  const r = rng(233);
  for (let i = 0; i < 26; i++) {
    const [x, y] = P(24 + r() * 40, 80 + r() * 18);
    ctx.fillStyle = i % 2 ? "rgba(196,112,63,0.55)" : "rgba(214,138,82,0.5)";
    ctx.beginPath();
    ctx.ellipse(x, y, 40 + r() * 30, 10 + r() * 6, 0, Math.PI, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,210,160,0.45)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse(x, y, 30, 7, 0, Math.PI * 1.15, Math.PI * 1.85);
    ctx.stroke();
  }
}

function fortress(ctx: Ctx): void {
  const [x, y] = P(66, 14);
  ctx.fillStyle = "#6e6258";
  ctx.strokeStyle = "#2b221d";
  ctx.lineWidth = 1.6;
  for (const [ox, oy, w, h] of [[-60, 10, 40, 12], [-10, 24, 50, 10], [40, 6, 14, 30], [-64, -20, 12, 30]] as const) {
    ctx.fillRect(x + ox, y + oy, w, h);
    ctx.strokeRect(x + ox, y + oy, w, h);
  }
}

function settlements(ctx: Ctx): void {
  const [tx, ty] = P(15, 80);
  for (const [ox, oy] of [[-48, 6], [42, 12], [-30, -30], [36, -26]] as const) {
    const x = tx + ox;
    const y = ty + oy;
    ctx.fillStyle = "#c9b79a";
    ctx.fillRect(x - 7, y - 6, 14, 9);
    ctx.fillStyle = "#8a4a2a";
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

function embers(ctx: Ctx): void {
  const r = rng(239);
  ctx.save();
  ctx.shadowColor = "#ff8a2a";
  ctx.shadowBlur = 6;
  for (let i = 0; i < 90; i++) {
    ctx.fillStyle = `rgba(255,${140 + Math.floor(r() * 80)},60,${0.4 + r() * 0.5})`;
    ctx.beginPath();
    ctx.arc(r() * W, r() * H, 1 + r() * 1.6, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function labels(ctx: Ctx): void {
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `italic 15px ${FONT}`;
  ctx.fillStyle = "rgba(255,236,210,0.8)";
  for (const [t, px, py] of [["赤　沙", 52, 95], ["灰　河", 13, 99], ["焦　土", 28, 64], ["熔岩河", 80, 66]] as const) {
    const [x, y] = P(px, py);
    ctx.fillText(t, x, y);
  }
}

function terrain(ctx: Ctx): void {
  base(ctx);
  redSand(ctx);
  ashRiver(ctx);
  mire(ctx);
  tarPits(ctx);
  coolingWells(ctx);
  lavaRiver(ctx);
  deadwood(ctx);
  settlements(ctx);
  fortress(ctx);
  ridges(ctx);
  volcanoShape(ctx);
  embers(ctx);
  labels(ctx);
}

/** 煙霧上方仍看得到火山口和噴煙（只是地景，不洩漏地點）。 */
function afterFog(ctx: Ctx): void {
  const [, y] = P(89, 26);
  ctx.save();
  ctx.globalAlpha = 0.85;
  ctx.beginPath();
  ctx.rect(0, 0, W, y - 120);
  ctx.clip();
  const top = volcanoShape(ctx);
  ctx.restore();
  plume(ctx, top[0], top[1]);
}

export const ASHEN_WASTE_ART: RegionArtDef = {
  terrain,
  afterFog,
  fog: { base: "#7d736b", puff: [176, 166, 156], shade: "60,50,44" },
};
