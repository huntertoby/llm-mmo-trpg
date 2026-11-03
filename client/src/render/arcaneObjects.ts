// 「魔導樞市」的物件畫法（Phase 5A-ART7；docs/art/四區移植需求.md 第 4 節；畫法移植自 docs/art/sample/regions4.js）。
// 換皮不換功能：擋視線的要高（黃銅管柱、木製吊臂畫到格頂）、半掩護的要矮（貨箱、沙包矮牆、木樑約 0.3 T）、
// 可燃的看得出木頭或草、會爆的晶能罐有四區共用的黃色三角危險記號。沙包矮牆的鐵欄杆是細線，不讓牆看起來變高。
// 這個檔案不匯入 objectArt 的值（避免循環匯入）；表由 objectArt 組裝。
import { dot, glowLine, hazardMark, roundRect, shadowEllipse, TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";
import { ARCANE } from "./arcaneTerrain";
import { drawLowWall, type LowWallPalette } from "./lowWallArt";
import { rng } from "./artRandom";
import type { ObjectArtSpec } from "./objectArt";

const T = 52;
const OUT = ARCANE.outline;

type ObjectDrawer = (ctx: Ctx, s: ObjectArtSpec) => void;

function box(ctx: Ctx, x: number, y: number, w: number, h: number, fill: string, lw = 2, r = 2): void {
  roundRect(ctx, x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = lw;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

/** 木殼貨箱：黃銅包角，中間有符文橘點（半掩護、可燃）。 */
function cargoCrate(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 7, T * 0.34, T * 0.28);
  const s = T * 0.62;
  const o = (T - s) / 2;
  box(ctx, o, o, s, s, "#8a6a44", 2, 3);
  ctx.strokeStyle = "rgba(40,26,12,0.55)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let k = 1; k < 4; k++) {
    ctx.moveTo(o + 2, o + (s * k) / 4);
    ctx.lineTo(o + s - 2, o + (s * k) / 4);
  }
  ctx.stroke();
  for (const [cx, cy] of [[o, o], [o + s - 7, o], [o, o + s - 7], [o + s - 7, o + s - 7]] as const) box(ctx, cx, cy, 7, 7, "#c89a52", 1.2, 1);
  dot(ctx, T / 2, T / 2, 3, ARCANE.rune);
}

/** 沙包矮牆的色盤（共用矮牆外框規則）。 */
export const ARCANE_LOW_WALL: LowWallPalette = {
  top: "#a08a60",
  topEdge: "#c8b080",
  face: "#7a6a4a",
  mortar: "#4a3e2a",
  outline: "#1e1810",
};

/** 鐵欄杆最高只到矮牆頂再往上這麼多（規格 43.0 第 2 條：≤ 6）。 */
export const ARCANE_RAIL_RISE = 5;

/** 沙包矮牆＋鐵欄杆：欄杆是 1.2 寬的細線，最高只到矮牆頂上 5 單位（半掩護，不能看起來變高）。 */
function sandbagWall(ctx: Ctx, s: ObjectArtSpec): void {
  drawLowWall(ctx, s, ARCANE_LOW_WALL);
  const x0 = s.joinL ? 0 : 4;
  const x1 = s.joinR ? T : T - 4;
  const capY = T * 0.3;
  const railY = capY - ARCANE_RAIL_RISE;
  ctx.strokeStyle = rgba(ARCANE.coal, 0.85);
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(x0 + (s.joinL ? 0 : 2), railY);
  ctx.lineTo(x1 - (s.joinR ? 0 : 2), railY);
  for (let k = 8; k < T - 3; k += 12) {
    if (k < x0 + 2 || k > x1 - 2) continue;
    ctx.moveTo(k, railY);
    ctx.lineTo(k, capY);
  }
  ctx.stroke();
}

/** 黃銅管柱：豎管、三道環箍、壓力表、一小段晶能光（擋視線，畫到格頂）。 */
function brassPipe(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.moveTo(c - 6, 46);
  ctx.lineTo(c + 6, 46);
  ctx.lineTo(c + 22, 52);
  ctx.lineTo(c + 8, 52);
  ctx.fill();
  box(ctx, c - 11, 40, 22, 8, ARCANE.plate);
  box(ctx, c - 7, 3, 14, 38, ARCANE.brass, 2, 3);
  ctx.fillStyle = "rgba(255,255,255,0.3)";
  ctx.fillRect(c - 5, 5, 2, 34);
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.fillRect(c + 2, 5, 4, 34);
  for (const y of [8, 24, 36]) box(ctx, c - 9, y, 18, 4, "#7a5e30", 1.2, 1);
  ctx.beginPath();
  ctx.arc(c, 17, 4.5, 0, TAU);
  ctx.fillStyle = "#f2ead8";
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(c, 17);
  ctx.lineTo(c + 2.5, 14.5);
  ctx.strokeStyle = "#c03020";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  glowLine(ctx, rgba(ARCANE.energy, 0.7), 1.5, 5, () => {
    ctx.moveTo(c, 29);
    ctx.lineTo(c, 34);
  });
}

/** 晶能罐：黃銅罐身，中間一條發光的晶能窗；貼四區共用的危險記號（會爆）。 */
function energyCanister(ctx: Ctx): void {
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
  ctx.fillStyle = "#9a7a40";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.fillRect(cx + w * 0.4, top + 4, w * 0.55, bot - top - 2);
  ctx.strokeStyle = "#5a4424";
  ctx.lineWidth = 2.5;
  for (const y of [top + 11, bot - 7]) {
    ctx.beginPath();
    ctx.moveTo(cx - w, y);
    ctx.quadraticCurveTo(cx, y + 4, cx + w, y);
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.ellipse(cx, top + 4, w, 5, 0, 0, TAU);
  ctx.fillStyle = "#c89a52";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  // 晶能窗（右側，不蓋住危險記號）
  ctx.save();
  ctx.shadowColor = ARCANE.energy;
  ctx.shadowBlur = 6;
  ctx.fillStyle = rgba(ARCANE.energy, 0.8);
  ctx.fillRect(cx + 6, top + 14, 5, 16);
  ctx.restore();
  hazardMark(ctx, cx - 3, top + 24, 6.5);
}

/** 倒下的木樑：木頭上一排黃銅鉚釘（半掩護、可燃）。 */
function rivetBeam(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 2, T / 2 + 9, T * 0.42, T * 0.14);
  const y = T / 2 - 4;
  box(ctx, 6, y, T - 12, 13, "#7a5a38", 2, 3);
  ctx.strokeStyle = "rgba(0,0,0,0.35)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(10, y + 4);
  ctx.lineTo(T - 16, y + 4);
  ctx.moveTo(10, y + 10);
  ctx.lineTo(T - 12, y + 10);
  ctx.stroke();
  roundRect(ctx, T - 12, y, 6, 13, 1);
  ctx.fillStyle = "#b8905a";
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  for (const x of [14, 24, 34]) dot(ctx, x, y + 6.5, 1.8, "#c89a52");
}

/** 蒸氣苔：苔草、底下一段黃銅管、上面飄著白蒸氣（隱蔽、可燃）。 */
function steamMoss(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 411);
  shadowEllipse(ctx, T / 2 + 2, T * 0.74, T * 0.36, T * 0.12);
  box(ctx, 2, T * 0.66, T - 4, 6, ARCANE.brass, 1.5, 2);
  ctx.lineCap = "round";
  ctx.lineWidth = 2.6;
  for (let i = 0; i < 16; i++) {
    const x = 10 + r() * (T - 20);
    const y = T * 0.68;
    const h = 14 + r() * 16;
    ctx.strokeStyle = i % 3 === 0 ? "#4a6a3a" : "#7aa060";
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x + (r() - 0.5) * 4, y - h * 0.6, x + (r() - 0.5) * 12, y - h);
    ctx.stroke();
  }
  for (let i = 0; i < 3; i++) {
    const gx = 14 + i * 12;
    const gg = ctx.createRadialGradient(gx, 14, 1, gx, 14, 10);
    gg.addColorStop(0, "rgba(235,240,240,0.5)");
    gg.addColorStop(1, "rgba(235,240,240,0)");
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, T);
  }
}

/** 鋼樑橋：兩側鐵樑（黃銅鉚釘），中間鋪木板（木板可燃、可破）。沿南北方向畫，東西向時轉 90°。 */
function steelBridge(ctx: Ctx, s: ObjectArtSpec): void {
  ctx.save();
  if (!s.vertical) {
    ctx.translate(T, 0);
    ctx.rotate(Math.PI / 2);
  }
  const x0 = 6;
  const x1 = T - 6;
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(x0 + 3, 0, x1 - x0, T);
  for (let y = 1; y < T; y += 8) box(ctx, x0 + 2, y, x1 - x0 - 4, 6.5, shade("#9a7448", 0.9 + ((y * 7) % 10) / 50), 1.4, 1);
  ctx.fillStyle = ARCANE.plate;
  ctx.fillRect(x0 - 2, 0, 5, T);
  ctx.fillRect(x1 - 3, 0, 5, T);
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 1.2;
  ctx.strokeRect(x0 - 2, 0, 5, T);
  ctx.strokeRect(x1 - 3, 0, 5, T);
  for (let y = 4; y < T; y += 12) {
    dot(ctx, x0 + 0.5, y, 1.4, "#d8b070");
    dot(ctx, x1 - 0.5, y, 1.4, "#d8b070");
  }
  ctx.restore();
}

/** 木製吊臂：木柱、橫臂、吊鉤（擋視線，畫到格頂；可燃、可推倒）。 */
function woodCrane(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.beginPath();
  ctx.ellipse(c + 3, 46, 12, 4, 0, 0, TAU);
  ctx.fill();
  box(ctx, c - 3, 6, 6, 40, "#8a6a44", 2, 1);
  box(ctx, c - 6, 3, 28, 5, "#8a6a44", 2, 1);
  ctx.strokeStyle = ARCANE.coal;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(c + 18, 8);
  ctx.lineTo(c + 18, 24);
  ctx.stroke();
  box(ctx, c + 15, 24, 6, 5, ARCANE.brass, 1.2, 1);
  ctx.strokeStyle = ARCANE.brass;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(c, 18);
  ctx.lineTo(c + 10, 8);
  ctx.stroke();
  for (const y of [16, 30]) box(ctx, c - 5, y, 10, 3, ARCANE.brass, 1, 1);
}

/** 冷卻槽上的格柵板：黃銅框的鐵格柵；受損時格條彎曲，最後缺兩根露出冷卻液（薄冰自己畫裂痕）。 */
function coolantGrate(ctx: Ctx, s: ObjectArtSpec): void {
  const stage = s.hpStage;
  ctx.fillStyle = ARCANE.coolant;
  ctx.fillRect(0, 0, T, T);
  ctx.globalAlpha = 0.92;
  roundRect(ctx, 5, 5, T - 10, T - 10, 6);
  ctx.fillStyle = rgba(ARCANE.plate, stage === 2 ? 0.55 : 0.75);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = ARCANE.brass;
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = ARCANE.brass;
  ctx.lineWidth = 2;
  ctx.beginPath();
  let bar = 0;
  for (let k = 12; k < T - 6; k += 8, bar++) {
    if (stage === 2 && (bar === 2 || bar === 3)) continue;
    const bend = stage >= 1 && bar === 1 ? 4 : 0;
    ctx.moveTo(k, 7);
    ctx.quadraticCurveTo(k + bend, T / 2, k, T - 7);
  }
  ctx.stroke();
}

/** 魔導樞市的物件畫法（物件 ID → 畫法）；需求第 4 節九種物件。 */
export const ARCANE_OBJECTS: Readonly<Record<string, ObjectDrawer>> = {
  crate: cargoCrate,
  low_wall: sandbagWall,
  stone_pillar: brassPipe,
  oil_barrel: energyCanister,
  fallen_log: rivetBeam,
  grass: steamMoss,
  wooden_bridge: steelBridge,
  dead_tree: woodCrane,
  thin_ice: coolantGrate,
};
