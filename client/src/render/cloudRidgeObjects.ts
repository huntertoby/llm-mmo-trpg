// 第一區「雲嶺」的物件畫法（Phase 3-37b；docs/art/雲嶺移植需求.md 第 3 節；畫法移植自 docs/art/sample/realms.js）。
// 換皮不換功能：擋視線的要高（樑柱、老松）、半掩護的要矮（竹籠、矮垣、倒竹）、可燃的是竹木色、會爆的罈身有危險記號。
// 這個檔案不匯入 objectArt 的值（避免循環匯入）；表由 objectArt 組裝。
import { roundRect, shadowEllipse, TAU, type Ctx } from "./artDraw";
import { rgba } from "./color";
import { CLOUD } from "./cloudRidgeTerrain";
import { drawLowWall, type LowWallPalette } from "./lowWallArt";
import { rng } from "./artRandom";
import type { ObjectArtSpec } from "./objectArt";

const T = 52;

type ObjectDrawer = (ctx: Ctx, s: ObjectArtSpec) => void;

const BAMBOO_TAN = "#b9a05a"; // 竹籠、竹編的竹木色（可燃）

/** 竹籠貨箱：竹篾編成的方籠（半掩護，矮；斜紋編織＋竹框＋蓋）。 */
function bambooCrate(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * 0.34, T * 0.3);
  const s = T * 0.62;
  const o = (T - s) / 2;
  roundRect(ctx, o, o, s, s, 3);
  ctx.fillStyle = BAMBOO_TAN;
  ctx.fill();
  ctx.save();
  ctx.beginPath();
  ctx.rect(o + 1, o + 1, s - 2, s - 2);
  ctx.clip();
  ctx.strokeStyle = "rgba(92,70,28,0.55)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let k = -s; k < s * 2; k += 5) {
    ctx.moveTo(o + k, o);
    ctx.lineTo(o + k + s, o + s);
    ctx.moveTo(o + k + s, o);
    ctx.lineTo(o + k, o + s);
  }
  ctx.stroke();
  ctx.restore();
  roundRect(ctx, o, o, s, s, 3);
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = "#5c4620";
  ctx.stroke();
  ctx.strokeStyle = CLOUD.bambooDark; // 竹框
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(o + 2, o + s * 0.5);
  ctx.lineTo(o + s - 2, o + s * 0.5);
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.2)";
  ctx.fillRect(o + 2, o + 2, s - 4, 3);
}

/** 白牆矮垣（黛瓦壓頂）：沿用矮牆的外框規則（相連的一側不畫外框），換白牆與黛瓦。 */
const CLOUD_LOW_WALL: LowWallPalette = {
  top: CLOUD.tile,
  topEdge: "#6a7a76",
  face: CLOUD.mist,
  mortar: "#a9aca2",
  outline: "#1f2a28",
};

/** 朱紅樑柱：高大的紅柱，頂有斗拱與黛瓦，腳下石礎（擋視線）。 */
function redPillar(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.moveTo(c - 6, 46);
  ctx.lineTo(c + 6, 46);
  ctx.lineTo(c + 22, 52);
  ctx.lineTo(c + 8, 52);
  ctx.fill();
  roundRect(ctx, c - 11, 40, 22, 8, 2); // 石礎
  ctx.fillStyle = CLOUD.slate;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = CLOUD.outline;
  ctx.stroke();
  roundRect(ctx, c - 6, 9, 12, 32, 2); // 柱身
  ctx.fillStyle = CLOUD.red;
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = CLOUD.redDark; // 右側暗面
  ctx.fillRect(c + 1, 10, 4, 30);
  ctx.fillStyle = "rgba(255,255,255,0.22)"; // 左側亮線
  ctx.fillRect(c - 4, 11, 2, 28);
  roundRect(ctx, c - 12, 6, 24, 6, 1); // 斗拱橫梁
  ctx.fillStyle = CLOUD.redDark;
  ctx.fill();
  ctx.stroke();
  ctx.beginPath(); // 黛瓦頂
  ctx.moveTo(c - 18, 8);
  ctx.lineTo(c - 10, 1);
  ctx.lineTo(c + 10, 1);
  ctx.lineTo(c + 18, 8);
  ctx.lineTo(c + 10, 6);
  ctx.lineTo(c - 10, 6);
  ctx.closePath();
  ctx.fillStyle = CLOUD.tile;
  ctx.fill();
  ctx.stroke();
}

/** 酒罈：圓肚陶罈，紅布封口綁繩；罈身貼危險記號（會爆）。 */
function wineJar(ctx: Ctx): void {
  shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * 0.3, T * 0.28);
  const c = T / 2;
  const r = T * 0.29;
  ctx.fillStyle = "#4a2a1c";
  ctx.beginPath();
  ctx.ellipse(c, c + 5, r, r * 0.92, 0, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "#9a6a44"; // 罈身
  ctx.beginPath();
  ctx.ellipse(c, c + 1, r, r * 0.92, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = CLOUD.outline;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.2)";
  ctx.beginPath();
  ctx.ellipse(c - 6, c - 6, 4, 2.4, -0.6, 0, TAU);
  ctx.fill();
  // 紅布封口與綁繩
  roundRect(ctx, c - 7, c - r - 1, 14, 9, 3);
  ctx.fillStyle = CLOUD.red;
  ctx.fill();
  ctx.stroke();
  ctx.strokeStyle = "#e0c890";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(c - 7, c - r + 5);
  ctx.lineTo(c + 7, c - r + 5);
  ctx.stroke();
  // 危險記號（同油桶）：黃底黑火焰
  ctx.save();
  ctx.beginPath();
  ctx.arc(c, c + 4, r * 0.45, 0, TAU);
  ctx.clip();
  ctx.fillStyle = "#f2b33d";
  ctx.fillRect(c - r, c - r, r * 2, r * 2 + 8);
  ctx.fillStyle = "#1a120a";
  ctx.beginPath();
  ctx.moveTo(c, c - 1.5);
  ctx.bezierCurveTo(c + 5, c + 4.5, c + 4, c + 9, c, c + 9);
  ctx.bezierCurveTo(c - 4, c + 9, c - 5, c + 4.5, c, c - 1.5);
  ctx.fill();
  ctx.restore();
}

/** 倒竹：一捆倒下的竹子（半掩護，矮、可燃），斜放，竹節與斷口。 */
function fallenBamboo(ctx: Ctx): void {
  ctx.save();
  ctx.translate(T / 2, T / 2);
  ctx.rotate(-0.5);
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  roundRect(ctx, -T * 0.4 + 3, -9 + 7, T * 0.8, 20, 7);
  ctx.fill();
  for (let i = 0; i < 3; i++) {
    const y = -9 + i * 6.5;
    ctx.fillStyle = i === 1 ? CLOUD.bambooDark : CLOUD.bamboo;
    roundRect(ctx, -T * 0.4, y, T * 0.8, 7, 3.5);
    ctx.fill();
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = CLOUD.outline;
    ctx.stroke();
    ctx.fillStyle = CLOUD.bambooNode;
    for (let k = -T * 0.28; k < T * 0.36; k += 11) ctx.fillRect(k, y + 0.5, 1.8, 6);
    ctx.fillStyle = "#d8dca0"; // 斷口
    ctx.beginPath();
    ctx.ellipse(T * 0.4, y + 3.5, 1.8, 3.2, 0, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

/** 矮竹叢（隱蔽、可燃）：一叢短短的竹桿與葉。 */
function bambooBush(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 112);
  shadowEllipse(ctx, T / 2 + 2, T * 0.78, T * 0.36, T * 0.12);
  const stalks = 5;
  for (let i = 0; i < stalks; i++) {
    const bx = T * (0.2 + (0.6 * i) / (stalks - 1)) + (r() - 0.5) * 3;
    const base = T * (0.76 + (i % 2) * 0.04);
    const top = base - (18 + r() * 8);
    ctx.fillStyle = i % 2 ? CLOUD.bambooDark : CLOUD.bamboo;
    ctx.fillRect(bx - 2, top, 4, base - top);
    ctx.strokeStyle = CLOUD.outline;
    ctx.lineWidth = 1.2;
    ctx.strokeRect(bx - 2, top, 4, base - top);
    ctx.fillStyle = CLOUD.bambooNode;
    for (let k = top + 7; k < base - 2; k += 8) ctx.fillRect(bx - 2.5, k, 5, 1.6);
    ctx.fillStyle = "#7cc05a";
    ctx.beginPath();
    ctx.ellipse(bx + 5, top + 3 + r() * 4, 6, 2.2, -0.5, 0, TAU);
    ctx.ellipse(bx - 5, top + 6 + r() * 4, 6, 2.2, 0.5, 0, TAU);
    ctx.fill();
  }
}

/** 竹木吊橋：兩側繩索與繩樁，竹木橋板；橋下是雲海（下面的地形）。 */
function suspensionBridge(ctx: Ctx, s: ObjectArtSpec): void {
  ctx.save();
  if (s.vertical) {
    ctx.translate(T, 0);
    ctx.rotate(Math.PI / 2);
  }
  const r = rng(s.x, s.y, 113);
  ctx.fillStyle = "#6a4a28";
  ctx.fillRect(0, 9, T, T - 18);
  for (let px = 0; px < T; px += T / 6) {
    ctx.fillStyle = `rgba(${200 + Math.floor(r() * 30)},${160 + Math.floor(r() * 30)},90,1)`;
    ctx.fillRect(px + 1, 10, T / 6 - 2, T - 20);
    ctx.fillStyle = "rgba(255,240,200,0.18)";
    ctx.fillRect(px + 1, 10, T / 6 - 2, 2);
  }
  ctx.strokeStyle = "#3a2814";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let px = 0; px <= T; px += T / 6) {
    ctx.moveTo(px, 10);
    ctx.lineTo(px, T - 10);
  }
  ctx.stroke();
  // 兩側的繩索：略為下垂，繩樁在兩端
  for (const ry of [6, T - 6]) {
    ctx.strokeStyle = CLOUD.outline;
    ctx.lineWidth = 3.4;
    ctx.beginPath();
    ctx.moveTo(0, ry);
    ctx.quadraticCurveTo(T / 2, ry + (ry < T / 2 ? 2 : -2), T, ry);
    ctx.stroke();
    ctx.strokeStyle = "#c8a870";
    ctx.lineWidth = 1.8;
    ctx.stroke();
    ctx.fillStyle = "#5a3c1e";
    for (const px of [2, T - 2]) {
      ctx.fillRect(px - 1.5, ry - 3, 3, 6);
    }
  }
  ctx.restore();
}

/** 老松：深綠針葉成層，彎曲的樹幹（擋視線、高、可燃、可推倒）。 */
function oldPine(ctx: Ctx, s: ObjectArtSpec): void {
  const r = rng(s.x, s.y, 114);
  shadowEllipse(ctx, T / 2 + 4, T * 0.84, T * 0.34, T * 0.1);
  ctx.strokeStyle = CLOUD.outline;
  ctx.lineCap = "round";
  ctx.lineWidth = 7;
  ctx.beginPath(); // 彎曲樹幹
  ctx.moveTo(24, 47);
  ctx.quadraticCurveTo(30, 34, 24, 22);
  ctx.quadraticCurveTo(22, 14, 28, 8);
  ctx.stroke();
  ctx.strokeStyle = "#5a4030";
  ctx.lineWidth = 4;
  ctx.stroke();
  // 針葉層（由下往上，越上越小）
  const layers: ReadonlyArray<readonly [number, number, number, number]> = [
    [18, 34, 17, 6],
    [34, 26, 15, 6],
    [20, 19, 14, 5.5],
    [32, 12, 12, 5],
    [26, 6, 9, 4],
  ];
  for (const [cx, cy, rx, ry] of layers) {
    ctx.fillStyle = "#274a34";
    ctx.beginPath();
    ctx.ellipse(cx + 1, cy + 2, rx, ry, 0, 0, TAU);
    ctx.fill();
    ctx.fillStyle = r() < 0.5 ? "#2f5a3a" : "#356642";
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = CLOUD.outline;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = "rgba(190,230,170,0.22)";
    ctx.beginPath();
    ctx.ellipse(cx - rx * 0.25, cy - ry * 0.35, rx * 0.5, ry * 0.3, 0, 0, TAU);
    ctx.fill();
  }
}

/** 寒潭薄冰：架在寒潭上的冰板，裂痕隨耐久增加（級距 0／1／2），最後露出黑水。 */
function pondIce(ctx: Ctx, s: ObjectArtSpec): void {
  const stage = s.hpStage;
  ctx.fillStyle = "#0e2a2e";
  ctx.fillRect(0, 0, T, T);
  const r = rng(s.x, s.y, 115);
  ctx.beginPath();
  ctx.roundRect(3, 3, T - 6, T - 6, 8);
  ctx.fillStyle = rgba("#cfe8e4", stage === 2 ? 0.62 : 0.86);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#eef8f4";
  ctx.stroke();
  ctx.fillStyle = rgba("#0e2a2e", 0.25);
  ctx.beginPath();
  ctx.ellipse(T / 2, T / 2, T * 0.26, T * 0.2, 0.3, 0, TAU);
  ctx.fill();
  const rays = stage === 0 ? 2 : stage === 1 ? 4 : 7;
  ctx.strokeStyle = stage === 2 ? "#0e2a2e" : "#5a8a88";
  ctx.lineWidth = stage === 2 ? 2 : 1.3;
  ctx.beginPath();
  for (let i = 0; i < rays; i++) {
    const ang = (i / rays) * TAU + r();
    let px = T / 2;
    let py = T / 2;
    ctx.moveTo(px, py);
    for (let k = 0; k < 3; k++) {
      px += Math.cos(ang + (r() - 0.5) * 0.8) * 7;
      py += Math.sin(ang + (r() - 0.5) * 0.8) * 7;
      ctx.lineTo(px, py);
    }
  }
  ctx.stroke();
  if (stage === 2) {
    ctx.fillStyle = "#07191c";
    ctx.beginPath();
    ctx.moveTo(T * 0.44, T * 0.42);
    ctx.lineTo(T * 0.58, T * 0.44);
    ctx.lineTo(T * 0.56, T * 0.58);
    ctx.lineTo(T * 0.42, T * 0.55);
    ctx.fill();
  }
}

/** 雲嶺的物件畫法（物件 ID → 畫法）；需求第 3 節「物件」九種。 */
export const CLOUD_OBJECTS: Readonly<Record<string, ObjectDrawer>> = {
  crate: bambooCrate,
  low_wall: (ctx, s) => drawLowWall(ctx, s, CLOUD_LOW_WALL),
  stone_pillar: redPillar,
  oil_barrel: wineJar,
  fallen_log: fallenBamboo,
  grass: bambooBush,
  wooden_bridge: suspensionBridge,
  dead_tree: oldPine,
  thin_ice: pondIce,
};
