// 「霜潮海境」的物件畫法（Phase 5A-ART7；docs/art/四區移植需求.md 第 5 節；畫法移植自 docs/art/sample/regions4.js）。
// 地板是亮色系，所以物件一律 2px 深色外框（草叢的草葉也先描一圈深色），否則會糊在沙上。
// 換皮不換功能：擋視線的要高（珊瑚礁柱、斷桅畫到格頂）、半掩護的要矮（漁貨箱、防波石堤、漂流木約 0.3 T）、
// 可燃的看得出木頭、布或草、會爆的鯨油桶有四區共用的黃色三角危險記號。
// `thin_ice`（薄冰，本區主場）同預設：不在表內，退回 objectArt 的預設畫法。
// 這個檔案不匯入 objectArt 的值（避免循環匯入）；表由 objectArt 組裝。
import { dot, hazardMark, roundRect, shadowEllipse, TAU, type Ctx } from "./artDraw";
import { shade } from "./color";
import { FROST, FROST_OUTLINE_WIDTH } from "./frostTerrain";
import { drawLowWall, type LowWallPalette } from "./lowWallArt";
import { rng } from "./artRandom";
import type { ObjectArtSpec } from "./objectArt";

const T = 52;
const OUT = FROST.outline;
const LW = FROST_OUTLINE_WIDTH;

type ObjectDrawer = (ctx: Ctx, s: ObjectArtSpec) => void;

function box(ctx: Ctx, x: number, y: number, w: number, h: number, fill: string, r = 2): void {
  roundRect(ctx, x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

/** 漁貨箱：箱面畫一條魚的線稿（半掩護、可燃）。 */
function fishCrate(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 7, T * 0.34, T * 0.28);
  const s = T * 0.62;
  const o = (T - s) / 2;
  box(ctx, o, o, s, s, "#9a8460", 3);
  ctx.strokeStyle = "rgba(40,30,16,0.5)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (const k of [1, 3]) {
    ctx.moveTo(o + 2, o + (s * k) / 4);
    ctx.lineTo(o + s - 2, o + (s * k) / 4);
  }
  ctx.stroke();
  ctx.strokeStyle = "#f2ead8";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.ellipse(T / 2 - 2, T / 2, 7, 3.5, 0, 0, TAU);
  ctx.moveTo(T / 2 + 5, T / 2);
  ctx.lineTo(T / 2 + 10, T / 2 - 4);
  ctx.lineTo(T / 2 + 10, T / 2 + 4);
  ctx.closePath();
  ctx.stroke();
}

/** 防波石堤的色盤（灰藍石；共用矮牆外框規則，外框 2px）。 */
export const FROST_LOW_WALL: LowWallPalette = {
  top: "#8a989c",
  topEdge: "#b8c6ca",
  face: "#5a6a70",
  mortar: "#34404a",
  outline: OUT,
};

/** 防波石堤：灰藍石的矮牆，正面一排浪花白點（畫在正面內，不比矮牆頂高）。 */
function breakwater(ctx: Ctx, s: ObjectArtSpec): void {
  drawLowWall(ctx, s, FROST_LOW_WALL);
  const x0 = s.joinL ? 0 : 4;
  const x1 = s.joinR ? T : T - 4;
  const y = T * 0.46 + T * 0.26 - 4;
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  for (let k = 6; k < T - 3; k += 9) {
    if (k < x0 + 3 || k > x1 - 3) continue;
    ctx.beginPath();
    ctx.arc(k, y, 2, 0, TAU);
    ctx.fill();
  }
}

/** 珊瑚礁柱：不規則的岩柱，長著珊瑚枝（擋視線，畫到格頂）。 */
function coralPillar(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.moveTo(c - 6, 46);
  ctx.lineTo(c + 6, 46);
  ctx.lineTo(c + 22, 52);
  ctx.lineTo(c + 8, 52);
  ctx.fill();
  box(ctx, c - 11, 40, 22, 8, "#5a6a70");
  ctx.beginPath();
  ctx.moveTo(c - 9, 41);
  ctx.quadraticCurveTo(c - 11, 22, c - 6, 6);
  ctx.quadraticCurveTo(c, 1, c + 6, 6);
  ctx.quadraticCurveTo(c + 11, 22, c + 9, 41);
  ctx.closePath();
  ctx.fillStyle = FROST.reef;
  ctx.fill();
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.fillRect(c + 3, 12, 5, 28);
  // 珊瑚枝：先描深色外框再上珊瑚色
  const branches = (): void => {
    ctx.beginPath();
    ctx.moveTo(c - 4, 20);
    ctx.lineTo(c - 10, 14);
    ctx.moveTo(c - 7, 17);
    ctx.lineTo(c - 7, 11);
    ctx.moveTo(c + 3, 30);
    ctx.lineTo(c + 10, 25);
    ctx.stroke();
  };
  ctx.lineCap = "round";
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 2.5 + LW;
  branches();
  ctx.strokeStyle = FROST.coral;
  ctx.lineWidth = 2.5;
  branches();
  for (const [dx, dy] of [[-3, 34], [1, 14], [4, 22]] as const) dot(ctx, c + dx, dy, 1.2, "rgba(255,255,255,0.4)");
}

/** 鯨油桶：深色木桶，藍灰色鐵箍；貼四區共用的危險記號（會爆）。 */
function whaleOilBarrel(ctx: Ctx): void {
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
  ctx.fillStyle = "#6a5a40";
  ctx.fill();
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.fillRect(cx + w * 0.4, top + 4, w * 0.55, bot - top - 2);
  ctx.strokeStyle = "#2a3a4a";
  ctx.lineWidth = 2.5;
  for (const y of [top + 11, bot - 7]) {
    ctx.beginPath();
    ctx.moveTo(cx - w, y);
    ctx.quadraticCurveTo(cx, y + 4, cx + w, y);
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.ellipse(cx, top + 4, w, 5, 0, 0, TAU);
  ctx.fillStyle = "#8a7650";
  ctx.fill();
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  hazardMark(ctx, cx - 3, top + 24, 6.5);
}

/** 漂流木：灰白色木頭（半掩護、可燃）。 */
function driftwood(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 2, T / 2 + 9, T * 0.42, T * 0.14);
  const y = T / 2 - 4;
  box(ctx, 6, y, T - 12, 13, "#a8a090", 6);
  ctx.strokeStyle = "rgba(60,56,48,0.5)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(10, y + 5);
  ctx.lineTo(T - 16, y + 4);
  ctx.moveTo(14, y + 9);
  ctx.lineTo(T - 12, y + 9);
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.25)";
  ctx.fillRect(8, y + 2, T - 20, 2);
  ctx.beginPath();
  ctx.ellipse(T - 8, y + 6.5, 4, 6.5, 0, 0, TAU);
  ctx.fillStyle = "#d8d0c0";
  ctx.fill();
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

/** 海草叢（隱蔽、可燃）：一叢彎曲的高海草；每片草葉先描 2px 深色外框。 */
function kelpTuft(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 511);
  shadowEllipse(ctx, T / 2 + 2, T * 0.74, T * 0.36, T * 0.12);
  const blades: Array<readonly [number, number, number, string]> = [];
  for (let i = 0; i < 14; i++) {
    const x = 10 + r() * (T - 20);
    const h = 14 + r() * 16;
    blades.push([x, h, (r() - 0.5) * 6, i % 3 === 0 ? "#1e5a44" : "#3a8a6a"]);
  }
  const y = T * 0.72;
  ctx.lineCap = "round";
  for (const pass of [0, 1] as const) {
    for (const [x, h, tip, color] of blades) {
      ctx.strokeStyle = pass === 0 ? OUT : color;
      ctx.lineWidth = pass === 0 ? 2.6 + LW : 2.6;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.bezierCurveTo(x - 5, y - h * 0.3, x + 5, y - h * 0.6, x + tip, y - h);
      ctx.stroke();
    }
  }
}

/** 碼頭棧道：兩側有樁、繩索，中間木板（可燃、可破）。沿南北方向畫，東西向時轉 90°。 */
function pier(ctx: Ctx, s: ObjectArtSpec): void {
  ctx.save();
  if (!s.vertical) {
    ctx.translate(T, 0);
    ctx.rotate(Math.PI / 2);
  }
  const x0 = 6;
  const x1 = T - 6;
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(x0 + 3, 0, x1 - x0, T);
  for (let y = 1; y < T; y += 8) box(ctx, x0 + 2, y, x1 - x0 - 4, 6.5, shade("#9a8460", 0.9 + ((y * 7) % 10) / 50), 1);
  ctx.strokeStyle = "#c8b48a";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  for (const x of [x0 - 1, x1 + 1]) {
    ctx.moveTo(x, 0);
    ctx.lineTo(x, T);
  }
  ctx.stroke();
  for (const y of [0, T - 8]) {
    box(ctx, x0 - 3, y, 6, 8, "#5a4a36", 1);
    box(ctx, x1 - 3, y, 6, 8, "#5a4a36", 1);
  }
  ctx.restore();
}

/** 斷桅：桅杆、橫桁、破帆（擋視線，畫到格頂；可燃、可推倒）。 */
function brokenMast(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.beginPath();
  ctx.ellipse(c + 3, 46, 12, 4, 0, 0, TAU);
  ctx.fill();
  box(ctx, c - 3, 4, 6, 42, "#7a6448", 1);
  // 斷口
  ctx.beginPath();
  ctx.moveTo(c - 3, 4);
  ctx.lineTo(c - 1, 1);
  ctx.lineTo(c + 1, 4);
  ctx.lineTo(c + 3, 0);
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  box(ctx, c - 16, 13, 32, 4, "#7a6448", 1);
  ctx.beginPath();
  ctx.moveTo(c - 14, 17);
  ctx.lineTo(c + 12, 17);
  ctx.lineTo(c + 8, 30);
  ctx.lineTo(c + 2, 26);
  ctx.lineTo(c - 4, 33);
  ctx.lineTo(c - 12, 28);
  ctx.closePath();
  ctx.fillStyle = "#e8e0cc";
  ctx.fill();
  ctx.lineWidth = LW;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = "rgba(60,50,40,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(c - 16, 15);
  ctx.lineTo(c - 6, 44);
  ctx.stroke();
}

/** 霜潮海境的物件畫法（物件 ID → 畫法）；需求第 5 節九種物件中的八種（`thin_ice` 同預設，不在表內）。 */
export const FROST_OBJECTS: Readonly<Record<string, ObjectDrawer>> = {
  crate: fishCrate,
  low_wall: breakwater,
  stone_pillar: coralPillar,
  oil_barrel: whaleOilBarrel,
  fallen_log: driftwood,
  grass: kelpTuft,
  wooden_bridge: pier,
  dead_tree: brokenMast,
};
