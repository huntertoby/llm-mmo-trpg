// 「灰燼荒原」的物件畫法（Phase 5A-ART6；docs/art/四區移植需求.md 第 2 節；畫法移植自 docs/art/sample/regions4.js）。
// 換皮不換功能：擋視線的要高（斷柱、枯樹畫到格頂）、半掩護的要矮（破木箱、殘牆、倒木約 0.3 T）、
// 可燃的看得出木頭或草、會爆的鐵油桶有四區共用的黃色三角危險記號。
// 這個檔案不匯入 objectArt 的值（避免循環匯入）；表由 objectArt 組裝。
import { dot, hazardMark, roundRect, shadowEllipse, TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";
import { ASH, ashGlowAt } from "./ashenTerrain";
import { drawLowWall, type LowWallPalette } from "./lowWallArt";
import { rng } from "./artRandom";
import type { ObjectArtSpec } from "./objectArt";
import { drawCoolingWell } from "./coolingWellArt";

const T = 52;
const OUT = ASH.outline;

type ObjectDrawer = (ctx: Ctx, s: ObjectArtSpec) => void;

function box(ctx: Ctx, x: number, y: number, w: number, h: number, fill: string, lw = 2, r = 2): void {
  roundRect(ctx, x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = lw;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

/** 破木箱：一角破洞，鐵包角（半掩護、可燃）。 */
function brokenCrate(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 7, T * 0.34, T * 0.28);
  const s = T * 0.62;
  const o = (T - s) / 2;
  box(ctx, o, o, s, s, "#7a5a38", 2, 3);
  ctx.strokeStyle = "rgba(40,24,12,0.6)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let k = 1; k < 4; k++) {
    ctx.moveTo(o + 2, o + (s * k) / 4);
    ctx.lineTo(o + s - 2, o + (s * k) / 4);
  }
  ctx.stroke();
  for (const [cx, cy] of [[o, o], [o + s - 7, o], [o, o + s - 7], [o + s - 7, o + s - 7]] as const) box(ctx, cx, cy, 7, 7, ASH.ash, 1.2, 1);
  // 破洞（右上角）
  ctx.fillStyle = "#1a120c";
  ctx.beginPath();
  ctx.moveTo(o + s * 0.55, o + 1);
  ctx.lineTo(o + s * 0.8, o + s * 0.3);
  ctx.lineTo(o + s - 1, o + s * 0.2);
  ctx.lineTo(o + s - 1, o + 1);
  ctx.closePath();
  ctx.fill();
}

/** 殘牆：灰褐石的矮牆（共用矮牆外框規則），頂端有一角崩缺。 */
const ASH_LOW_WALL: LowWallPalette = {
  top: ASH.ruinTop,
  topEdge: "#9a8e84",
  face: ASH.ruinFace,
  mortar: "#2e2620",
  outline: "#1a1410",
};

function ruinedWall(ctx: Ctx, s: ObjectArtSpec): void {
  drawLowWall(ctx, s, ASH_LOW_WALL);
  // 崩缺：只在牆的右端（不和右鄰相連）或約 1/3 的格子；畫在壓頂石內，不比矮牆頂高
  if (!s.joinR || rng(s.x, s.y, 211)() < 1 / 3) {
    const x1 = s.joinR ? T - 6 : T - 4;
    const capY = T * 0.3;
    ctx.fillStyle = "#1a1410";
    ctx.beginPath();
    ctx.moveTo(x1 - 14, capY - 1);
    ctx.lineTo(x1 - 8, capY + 6);
    ctx.lineTo(x1 + 1, capY + 2);
    ctx.lineTo(x1 + 1, capY - 1);
    ctx.closePath();
    ctx.fill();
  }
}

/** 斷柱：頂端斷口參差、有裂紋（擋視線，畫到格頂）。 */
function brokenPillar(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.moveTo(c - 6, 46);
  ctx.lineTo(c + 6, 46);
  ctx.lineTo(c + 22, 52);
  ctx.lineTo(c + 8, 52);
  ctx.fill();
  box(ctx, c - 11, 40, 22, 8, ASH.ruinFace);
  ctx.beginPath();
  ctx.moveTo(c - 7, 41);
  ctx.lineTo(c - 7, 10);
  ctx.lineTo(c - 3, 6);
  ctx.lineTo(c, 11);
  ctx.lineTo(c + 3, 3);
  ctx.lineTo(c + 7, 9);
  ctx.lineTo(c + 7, 41);
  ctx.closePath();
  ctx.fillStyle = ASH.ruinTop;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.fillRect(c + 2, 10, 4, 30);
  ctx.strokeStyle = "rgba(0,0,0,0.45)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const y of [18, 28]) {
    ctx.moveTo(c - 6, y);
    ctx.lineTo(c + 6, y + 2);
  }
  ctx.stroke();
  for (const [dx, dy] of [[-4, 24], [2, 34]] as const) dot(ctx, c + dx, dy, 1.6, "#1a120c");
}

/** 鐵油桶（鏽）：灰鐵桶身、鏽斑，桶身貼四區共用的危險記號（會爆）。 */
function rustyBarrel(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 8, T * 0.3, T * 0.24);
  const cx = T / 2;
  const top = 10;
  const bot = 42;
  const w = 16;
  ctx.beginPath();
  ctx.moveTo(cx - w, top + 4);
  ctx.lineTo(cx - w, bot);
  ctx.ellipse(cx, bot, w, 5, 0, Math.PI, 0, true);
  ctx.lineTo(cx + w, top + 4);
  ctx.closePath();
  ctx.fillStyle = "#5a5e60";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.fillRect(cx + w * 0.4, top + 4, w * 0.55, bot - top - 2);
  ctx.strokeStyle = "#3a3c3e";
  ctx.lineWidth = 2.5;
  for (const y of [top + 11, bot - 7]) {
    ctx.beginPath();
    ctx.moveTo(cx - w, y);
    ctx.quadraticCurveTo(cx, y + 4, cx + w, y);
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.ellipse(cx, top + 4, w, 5, 0, 0, TAU);
  ctx.fillStyle = "#6a6e70";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  for (const [dx, dy, rad] of [[-8, 22, 4], [6, 32, 3], [-3, 38, 2.5]] as const) dot(ctx, cx + dx, dy, rad, "#9a4a20");
  hazardMark(ctx, cx - 3, top + 24, 6.5);
}

/** 焦黑倒木：中段炭化，上面有餘燼點（半掩護、可燃）。 */
function charredLog(ctx: Ctx, s: ObjectArtSpec): void {
  shadowEllipse(ctx, T / 2 + 2, T / 2 + 9, T * 0.42, T * 0.14);
  const y = T / 2 - 4;
  box(ctx, 6, y, T - 12, 13, "#4a3628", 2, 6);
  ctx.strokeStyle = "rgba(0,0,0,0.5)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(10, y + 5);
  ctx.lineTo(T - 16, y + 4);
  ctx.moveTo(14, y + 9);
  ctx.lineTo(T - 12, y + 9);
  ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(T - 8, y + 6.5, 4, 6.5, 0, 0, TAU);
  ctx.fillStyle = "#8a6a48";
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "#1a120c";
  ctx.fillRect(16, y + 1, 10, 11);
  ctx.fillRect(30, y + 1, 5, 11);
  if (ashGlowAt(s.x, s.y, 212)) for (const x of [20, 32]) dot(ctx, x, y + 6, 1.2, ASH.ember);
}

/** 枯草堆（隱蔽、可燃）：一叢較高的乾黃草葉。 */
function dryTuft(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 213);
  shadowEllipse(ctx, T / 2 + 2, T * 0.74, T * 0.36, T * 0.12);
  ctx.lineCap = "round";
  ctx.lineWidth = 2.6;
  for (let i = 0; i < 16; i++) {
    const x = 10 + r() * (T - 20);
    const y = T * 0.72;
    const h = 14 + r() * 16;
    ctx.strokeStyle = i % 3 === 0 ? "#7a6438" : ASH.bladeLight;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x + (r() - 0.5) * 4, y - h * 0.6, x + (r() - 0.5) * 12, y - h);
    ctx.stroke();
  }
}

/** 焦木渡橋：橋板兩端焦黑，兩側有橋樁；橋下是下面的地形（通常是岩漿）。沿南北方向畫，東西向時轉 90°。 */
function charredBridge(ctx: Ctx, s: ObjectArtSpec): void {
  ctx.save();
  if (!s.vertical) {
    ctx.translate(T, 0);
    ctx.rotate(Math.PI / 2);
  }
  const x0 = 6;
  const x1 = T - 6;
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(x0 + 3, 0, x1 - x0, T);
  for (let y = 1; y < T; y += 8) {
    box(ctx, x0 + 2, y, x1 - x0 - 4, 6.5, shade("#7a5a38", 0.9 + ((y * 7) % 10) / 50), 1.4, 1);
    ctx.fillStyle = "#1e140c";
    ctx.fillRect(x0 + 2, y, 5, 6.5);
    ctx.fillRect(x1 - 9, y, 7, 6.5);
  }
  for (const y of [0, T - 8]) {
    box(ctx, x0 - 3, y, 6, 8, "#3a2a1e", 1.4, 1);
    box(ctx, x1 - 3, y, 6, 8, "#3a2a1e", 1.4, 1);
  }
  ctx.restore();
}

/** 枯樹（本區主場）：焦黑分枝，有餘燼點（擋視線，畫到格頂；可燃、可推倒）。 */
function charredTree(ctx: Ctx, s: ObjectArtSpec): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.beginPath();
  ctx.ellipse(c + 3, 46, 12, 4, 0, 0, TAU);
  ctx.fill();
  const br: ReadonlyArray<readonly [number, number, number, number, number]> = [
    [c, 46, c, 22, 7],
    [c, 30, c - 12, 16, 4],
    [c, 26, c + 12, 12, 4],
    [c + 12, 12, c + 18, 4, 2.5],
    [c - 12, 16, c - 16, 6, 2.5],
    [c + 4, 22, c + 2, 3, 3],
  ];
  ctx.lineCap = "round";
  for (const [color, extra] of [[OUT, 3], ["#3a2a20", 0]] as const) {
    ctx.strokeStyle = color;
    for (const [ax, ay, bx, by, w] of br) {
      ctx.lineWidth = w + extra;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.stroke();
    }
  }
  if (ashGlowAt(s.x, s.y, 214)) for (const [x, y] of [[c - 1, 34], [c + 9, 15], [c - 10, 19]] as const) dot(ctx, x, y, 1.4, ASH.ember);
}

/** 灰水上的浮板：木板拼成，架在灰水坑上；受損時木縫變大，最後缺一塊露出灰水（薄冰自己畫裂痕）。 */
function floatPlanks(ctx: Ctx, s: ObjectArtSpec): void {
  const stage = s.hpStage;
  const r = rng(s.x, s.y, 215);
  ctx.fillStyle = "#2c3034";
  ctx.fillRect(0, 0, T, T);
  ctx.globalAlpha = stage === 2 ? 0.8 : 0.95;
  roundRect(ctx, 5, 5, T - 10, T - 10, 6);
  ctx.fillStyle = "#8a6a48";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#3a2a1e";
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = rgba("#000000", stage === 0 ? 0.35 : 0.55);
  ctx.lineWidth = stage === 0 ? 1.2 : 2;
  ctx.beginPath();
  for (let y = 14; y < T - 8; y += 9) {
    ctx.moveTo(7, y);
    ctx.lineTo(T - 7, y + (stage === 0 ? 0 : (r() - 0.5) * 3));
  }
  ctx.stroke();
  if (stage >= 1) {
    // 裂開的木紋
    ctx.strokeStyle = "#2a1c10";
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    const px = 14 + r() * 20;
    ctx.moveTo(px, 15);
    ctx.lineTo(px + 4, 22);
    ctx.lineTo(px + 1, 30);
    ctx.stroke();
  }
  if (stage === 2) {
    // 缺一塊板：露出灰水
    ctx.fillStyle = "#1e2226";
    ctx.fillRect(9, 24, T - 18, 8);
  }
}

/** 灰燼荒原的物件畫法（物件 ID → 畫法）；需求第 2 節「物件」九種＋CW-1 的冷卻井。 */
export const ASHEN_OBJECTS: Readonly<Record<string, ObjectDrawer>> = {
  crate: brokenCrate,
  low_wall: ruinedWall,
  stone_pillar: brokenPillar,
  oil_barrel: rustyBarrel,
  fallen_log: charredLog,
  grass: dryTuft,
  wooden_bridge: charredBridge,
  dead_tree: charredTree,
  thin_ice: floatPlanks,
  cooling_well: drawCoolingWell, // CW-1：冷卻井（docs/art/冷卻井-移植需求.md）
};
