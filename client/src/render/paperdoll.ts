// 紙娃娃小人（Phase 3-16b；Phase C-1a 起骨架與四方向改為 C 手繪墨線畫法，見 inkDoll.ts、inkStyle.ts）。
// 這個檔案保留：外觀顏色解析（itemColors）、還沒換成 C 畫法的頭部裝備與手持物（C-1b、C-2 逐步換掉）、倒地姿勢、貼圖產生。
// 座標：腳底中心為原點、往上為負；C 骨架身高約 52（尖帽到 -70）。
import type { Facing } from "../api/types";
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import { elementTint, MATERIAL, RARITY_GLOW, type DollSpec, type GearItem } from "./appearance";
import {
  drawCap,
  drawFist,
  drawGreathelm,
  drawHammer,
  drawOrb,
  drawPistol,
  drawScythe,
  drawShotgun,
  drawSpear,
  drawTowerShield,
  drawWhip,
  drawWideHat,
  fill,
  mix,
} from "./paperdollGear";
import { drawInkFigure, type InkHooks, type InkView } from "./inkDoll";
import { dark, drawHeadgearSide, drawOffhandSide } from "./paperdollSideGear";
import { sideWeaponPose } from "./paperdollSideWeapon";

/** 離屏畫布的虛擬大小與腳底位置（虛擬像素）。 */
export const DOLL_W = 64;
export const DOLL_H = 88; // C 畫風頭頂最高約 -70（尖帽），要留夠
export const DOLL_FOOT_Y = DOLL_H - 6;
/** C 畫風的戰場縮放：52px 格約 0.74 倍，人約 40px 高（需求第 2 節）。 */
export const DOLL_SCALE = 0.74;
/** 非人形召喚物（summonArt.ts 自己的畫法）沿用的畫布大小與腳底位置：舊的 64×64，不隨 C 骨架改。 */
export const SUMMON_W = 64;
export const SUMMON_H = 64;
export const SUMMON_FOOT_Y = SUMMON_H - 6;

function darker(c: string, f = 0.68): string {
  return mix(c, "#000000", 1 - f);
}

/** 一件裝備的 [主色, 暗色]：指定顏色或材質色（不認得 → 布料色），有元素時混入元素色 45%。 */
export function itemColors(item: GearItem): [string, string] {
  const base = MATERIAL[item.material ?? "cloth"] ?? MATERIAL.cloth!;
  let [main, dark]: [string, string] = item.color !== undefined ? [item.color, darker(item.color)] : [base[0], base[1]];
  const tint = elementTint(item.element);
  if (tint !== undefined) {
    main = mix(main, tint, 0.45);
    dark = mix(dark, tint, 0.3);
  }
  return [main, dark];
}

type View = "front" | "back";

function drawHelmet(ctx: Ctx, it: GearItem, c: string, d: string, view: View): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(0, -30, 9.4, Math.PI, 0);
    ctx.lineTo(9.4, -27);
    ctx.lineTo(-9.4, -27);
    ctx.closePath();
  });
  fill(ctx, d, () => ctx.rect(-9.4, -28, 18.8, 1.6));
  if (view !== "back") fill(ctx, d, () => ctx.rect(-1, -28, 2, 5));
  fill(ctx, mix(c, "#ffffff", 0.4), () => rr(ctx, -5, -37, 4, 3, 1.5));
  if (it.kind !== "horned_helm") return;
  for (const s of [-1, 1]) {
    fill(ctx, "#efe6cc", () => {
      ctx.beginPath();
      ctx.moveTo(s * 8, -33);
      ctx.quadraticCurveTo(s * 15, -35, s * 14, -42);
      ctx.quadraticCurveTo(s * 11, -37, s * 6, -36);
      ctx.closePath();
    });
  }
}

function drawBandana(ctx: Ctx, c: string, d: string, view: View): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(0, -30, 9, Math.PI * 1.05, Math.PI * 1.95);
    ctx.closePath();
  });
  fill(ctx, c, () => ctx.rect(-9, -31.5, 18, 3));
  const tx = view === "back" ? 0 : 8;
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.moveTo(tx, -30);
    ctx.lineTo(tx + 5, -27);
    ctx.lineTo(tx + 2, -25);
    ctx.closePath();
  });
}

function drawHeadgear(ctx: Ctx, it: GearItem | undefined, view: View): void {
  if (it === undefined) return;
  const [c, d] = itemColors(it);
  switch (it.kind) {
    case "helmet":
    case "horned_helm":
      drawHelmet(ctx, it, c, d, view);
      break;
    case "bandana":
      drawBandana(ctx, c, d, view);
      break;
    case "wide_hat":
      drawWideHat(ctx, it, [c, d]);
      break;
    case "cap":
      drawCap(ctx, it, [c, d]);
      break;
    case "greathelm":
      drawGreathelm(ctx, [c, d], view === "back");
      break;
    case "crown":
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(-6, -35);
        ctx.lineTo(-6, -41);
        ctx.lineTo(-3, -38);
        ctx.lineTo(0, -42);
        ctx.lineTo(3, -38);
        ctx.lineTo(6, -41);
        ctx.lineTo(6, -35);
        ctx.closePath();
      });
      fill(ctx, "#d23c3c", () => ctx.arc(0, -37, 1.3, 0, TAU));
      break;
    default:
      break;
  }
}

function drawBlade(ctx: Ctx, it: GearItem, c: string, front: boolean): void {
  const great = it.kind === "greatsword";
  const L = great ? 24 : 16;
  const W = great ? 4 : 2.6;
  ctx.rotate(front ? -0.25 : 0.25);
  const arcane = !great && it.form === ARCANE_FORM;
  fill(ctx, arcane && it.color === undefined ? mix(c, ARCANE_BLADE, 0.7) : c, () => {
    ctx.beginPath();
    ctx.moveTo(-W / 2, -3);
    ctx.lineTo(-W / 2, -L);
    ctx.lineTo(0, -L - 3);
    ctx.lineTo(W / 2, -L);
    ctx.lineTo(W / 2, -3);
    ctx.closePath();
  });
  if (arcane) {
    drawArcaneParts(ctx, it, L);
    return;
  }
  fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
  fill(ctx, it.hilt ?? "#8a6a2a", () => rr(ctx, -4.5, -4, 9, 2, 1));
  fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, 4));
}

/** 魔導劍（#46，`docs/art/魔導劍.md`）：單手劍的形制 `arcane`。不認得這個形制的地方畫一般單手劍。 */
export const ARCANE_FORM = "arcane";
/** 源晶槽的預設顏色（沒有元素）；有元素時換元素色。 */
export const ARCANE_GLOW = "#9a86ff";
/** 黃銅齒輪護手。 */
const ARCANE_BRASS = "#b08a4a";
/** 魔導劍的預設劍身色：冷灰，比一般鋼劍暗一點，讓光槽更明顯（有 `color` 時照該顏色）。 */
const ARCANE_BLADE = "#8a93a8";

/** 魔導劍的源晶槽顏色：有元素換元素色，否則藍紫（供測試與圖示共用）。 */
export function arcaneGlow(element: string | undefined): string {
  return elementTint(element) ?? ARCANE_GLOW;
}

/** 魔導劍（劍身已畫好）：中線一道源晶槽（寬約劍身 40%、帶 4px 外光；小圖示也至少 1px）＋三個淡白符文刻點
 * ＋黃銅齒輪護手（12 齒）與中心源晶。正面、背面、側面共用（側面沿用一般劍的側面畫法再加源晶槽色）。 */
function drawArcaneParts(ctx: Ctx, it: GearItem, length: number): void {
  const glow = arcaneGlow(it.element);
  ctx.save();
  ctx.shadowColor = glow;
  ctx.shadowBlur = 4;
  ctx.fillStyle = glow;
  ctx.fillRect(-0.55, -length + 1, 1.1, length - 5);
  ctx.restore();
  ctx.fillStyle = "#e8e2ff";
  for (const ry of [-6.5, -10, -13.5]) ctx.fillRect(-1.1, ry, 2.2, 0.8);
  fill(ctx, ARCANE_BRASS, () => {
    for (let i = 0; i < 12; i += 1) {
      const a = (i / 12) * TAU;
      const r = i % 2 === 1 ? 3.2 : 4.3;
      ctx.lineTo(Math.cos(a) * r, -3 + Math.sin(a) * r * 0.55);
    }
    ctx.closePath();
  });
  fill(ctx, glow, () => ctx.arc(0, -3, 1.2, 0, TAU));
  fill(ctx, "#4a3020", () => ctx.rect(-1, -1.5, 2, 3.5));
}

/** 權杖：短柄，頂端一個金環＋寶珠（美術樣張 `gearArt.js` 的 scepter 形制）。 */
function drawScepter(ctx: Ctx, it: GearItem, c: string): void {
  fill(ctx, "#6a4420", () => ctx.rect(-1.1, -22, 2.2, 26));
  ctx.strokeStyle = "#e8bb48";
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.arc(0, -26, 5.2, 0, TAU);
  ctx.stroke();
  fill(ctx, elementTint(it.element) ?? c, () => ctx.arc(0, -26, 2.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-0.9, -27, 0.8, 0, TAU));
}

/** 圖騰杖：木柱疊兩張刻臉（紅、青）＋兩側羽毛＋頂端綠珠（美術樣張的 totem 形制）。 */
function drawTotemStaff(ctx: Ctx): void {
  fill(ctx, "#8f5f2c", () => ctx.rect(-1.4, -32, 2.8, 36));
  for (const [y, color] of [
    [-30, "#b83a3a"],
    [-21, "#3a8a8a"],
  ] as const) {
    fill(ctx, "#b77f3f", () => rr(ctx, -4, y, 8, 7, 1.6));
    fill(ctx, color, () => ctx.rect(-2.6, y + 1.4, 5.2, 1.4));
    fill(ctx, "#1d1a22", () => ctx.rect(-2, y + 4, 4, 1));
  }
  for (const s of [-1, 1]) {
    fill(ctx, "#e6e6e0", () => {
      ctx.beginPath();
      ctx.moveTo(s * 4, -28);
      ctx.quadraticCurveTo(s * 11, -33, s * 10, -25);
      ctx.quadraticCurveTo(s * 7, -26, s * 4, -25);
      ctx.closePath();
    });
  }
  fill(ctx, "#7dffb0", () => ctx.arc(0, -35, 2.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-0.8, -36, 0.8, 0, TAU));
}

function drawStaff(ctx: Ctx, it: GearItem, c: string): void {
  if (it.form === "totem") {
    drawTotemStaff(ctx);
    return;
  }
  if (it.form === "scepter") {
    drawScepter(ctx, it, c);
    return;
  }
  fill(ctx, "#6a4420", () => ctx.rect(-1.1, -30, 2.2, 34));
  const orb = elementTint(it.element) ?? c; // 法杖寶珠直接用元素色
  ctx.fillStyle = orb;
  ctx.globalAlpha = 0.35;
  ctx.beginPath();
  ctx.arc(0, -32, 6.5, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
  fill(ctx, orb, () => ctx.arc(0, -32, 3.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -33.2, 1.1, 0, TAU));
}

function drawBow(ctx: Ctx, c: string, front: boolean): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.arc(front ? -4 : 4, -8, 13, front ? -1.2 : Math.PI - 1.2, front ? 1.2 : Math.PI + 1.2);
  ctx.stroke();
  ctx.strokeStyle = "rgba(240,240,240,0.8)";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  const sx = (front ? -4 : 4) + (front ? 1 : -1) * Math.cos(1.2) * 13;
  ctx.moveTo(sx, -8 - Math.sin(1.2) * 13);
  ctx.lineTo(sx, -8 + Math.sin(1.2) * 13);
  ctx.stroke();
}

/** 弩（Phase 3-24a2，形制 `light` 輕弩、`heavy` 重弩、`repeater` 連弩；美術樣張 `paperdoll.js` 的 crossbow）：
 *  木製弩身橫持，前端一張橫向的弩臂（弓身顏色取材質），拉著弦；重弩弩臂更寬更粗並多一個腳蹬環，連弩弩身上多一個箭匣。 */
function drawCrossbow(ctx: Ctx, it: GearItem, c: string, front: boolean): void {
  ctx.rotate(front ? 0.35 : -0.35);
  const s = front ? -1 : 1;
  const heavy = it.form === "heavy";
  const span = heavy ? 10 : 8;
  const tip = s * (heavy ? 11.5 : 10.5);
  fill(ctx, "#7a5232", () => rr(ctx, s > 0 ? 0 : -12.5, -3, 12.5, 2.8, 1));
  fill(ctx, "#4e321c", () => rr(ctx, s > 0 ? -1.5 : -0.5, -3.4, 2, 5, 0.8)); // 握把
  if (it.form === "repeater") {
    fill(ctx, "#4e321c", () => rr(ctx, s > 0 ? 1.5 : -8.5, -6.6, 7, 3.8, 0.8)); // 箭匣
    fill(ctx, "#c3ccd6", () => ctx.rect(s > 0 ? 2.5 : -7.5, -5.6, 5, 0.8));
  }
  ctx.strokeStyle = c;
  ctx.lineWidth = heavy ? 3 : 2;
  ctx.beginPath();
  ctx.moveTo(tip, -span - 1);
  ctx.quadraticCurveTo(tip + s * (heavy ? 3 : 2.5), -1.6, tip, span - 4);
  ctx.stroke();
  ctx.strokeStyle = "rgba(240,240,240,0.8)";
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  ctx.moveTo(tip, -span - 1);
  ctx.lineTo(tip - s * 3.5, -1.6);
  ctx.lineTo(tip, span - 4);
  ctx.stroke();
  if (heavy) {
    ctx.strokeStyle = "#4e321c";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(tip - s * 0.5, -1.6, 2.6, 0, TAU);
    ctx.stroke(); // 腳蹬環
  }
  fill(ctx, "#a06a36", () => rr(ctx, Math.min(tip - s * 3.5, tip), -2.2, 3.6, 0.9, 0.4)); // 弩箭
  fill(ctx, "#c3ccd6", () => {
    ctx.beginPath();
    ctx.moveTo(tip + s * 1.6, -2.7);
    ctx.lineTo(tip - s * 0.4, -1.7);
    ctx.lineTo(tip + s * 1.6, -0.7);
    ctx.closePath();
  });
}

/** 火槍（火器，Phase 3-24a2；形制 `flintlock` 燧發火槍、`hunting` 獵槍、`sniper` 狙擊火槍）：槍口朝前下方，
 *  槍托在手後；槍身金屬色取材質，槍托固定木色（狙擊火槍的槍托是暗色金屬），燧發槍有擊錘、獵槍有木製護木、狙擊槍有瞄準鏡與腳架。 */
function drawLongGun(ctx: Ctx, it: GearItem, c: string, d: string, front: boolean): void {
  ctx.rotate(front ? 0.35 : -0.35);
  const s = front ? -1 : 1;
  const sniper = it.form === "sniper";
  const L = sniper ? 21 : it.form === "hunting" ? 18 : 17;
  const x0 = s > 0 ? -1 : -L;
  fill(ctx, "#3a2a1c", () => rr(ctx, -1.2, -1, 2.4, 5, 0.8)); // 握把
  fill(ctx, sniper ? d : "#7a5232", () => rr(ctx, s > 0 ? -7 : 1, -3.4, 6.5, 3.6, 1)); // 槍托
  fill(ctx, c, () => rr(ctx, x0, -3.2, L + 1, 2.6, 1)); // 槍身
  if (it.form === "hunting") {
    fill(ctx, "#7a5232", () => rr(ctx, x0 + (s > 0 ? 0 : L * 0.35), -0.9, L * 0.65 + 1, 1.8, 0.8)); // 護木
  }
  if (it.form === "flintlock") {
    fill(ctx, d, () => {
      ctx.beginPath();
      ctx.moveTo(s * 0.5, -3.2);
      ctx.lineTo(s * -1.2, -6.2);
      ctx.lineTo(s * 1.2, -6.6);
      ctx.lineTo(s * 2.2, -3.2);
      ctx.closePath();
    }); // 擊錘
    fill(ctx, "#e8bb48", () => ctx.rect(x0 + (s > 0 ? 6 : L - 7), -3.4, 1.4, 3)); // 銅箍
  }
  if (sniper) {
    fill(ctx, "#2a2d33", () => rr(ctx, x0 + (s > 0 ? 5 : L - 12), -6.4, 8, 2.4, 1)); // 瞄準鏡
    fill(ctx, "#8fe3ff", () => ctx.arc(x0 + (s > 0 ? 13 : L - 12), -5.2, 0.9, 0, TAU));
    ctx.strokeStyle = "#1d1a22";
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.moveTo(x0 + (s > 0 ? L - 6 : 6), -0.6);
    ctx.lineTo(x0 + (s > 0 ? L - 8 : 8), 3.4);
    ctx.moveTo(x0 + (s > 0 ? L - 6 : 6), -0.6);
    ctx.lineTo(x0 + (s > 0 ? L - 4 : 4), 3.4);
    ctx.stroke(); // 腳架
  }
}

function drawShield(ctx: Ctx, it: GearItem, c: string, d: string): void {
  if (it.kind === "shield_round") {
    fill(ctx, d, () => ctx.arc(0, -4, 7.5, 0, TAU));
    fill(ctx, c, () => ctx.arc(0, -4, 6, 0, TAU));
    fill(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -4, 2, 0, TAU));
    return;
  }
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.moveTo(-7, -13);
    ctx.lineTo(7, -13);
    ctx.lineTo(6.5, -2);
    ctx.lineTo(0, 6);
    ctx.lineTo(-6.5, -2);
    ctx.closePath();
  });
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(-5.5, -11.5);
    ctx.lineTo(5.5, -11.5);
    ctx.lineTo(5, -2.5);
    ctx.lineTo(0, 3.8);
    ctx.lineTo(-5, -2.5);
    ctx.closePath();
  });
  fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-0.9, -11, 1.8, 13));
  fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-5, -7, 10, 1.8));
}

/** 一件手持物（主手或副手）；`mirror`：左右鏡像（成對武器的副手，兩把向外張開）。 */
function drawWeapon(ctx: Ctx, it: GearItem | undefined, x: number, front: boolean, mirror = false, far = false, side = false): void {
  if (it === undefined) return;
  let [c, d] = itemColors(it);
  ctx.save();
  ctx.translate(x, -9.5);
  if (mirror) ctx.scale(-1, 1);
  if (side) {
    // 真側面（3S-3）：套這個 kind 的側面握法（抵銷形狀內部的旋轉，再轉到指定角度）；遠側那把變暗
    const pose = sideWeaponPose(it, far);
    front = pose.front;
    ctx.translate(pose.dx, pose.dy);
    ctx.rotate(pose.angle - pose.inner);
    if (pose.shade > 0) [c, d] = [dark(c, pose.shade), dark(d, pose.shade)];
  }
  switch (it.kind) {
    case "sword":
    case "greatsword":
      drawBlade(ctx, it, c, front);
      break;
    case "dagger":
      ctx.rotate(front ? -0.6 : 0.6);
      fill(ctx, mix(c, "#ffffff", 0.15), () => {
        ctx.beginPath();
        ctx.moveTo(-1.3, -2);
        ctx.lineTo(0, -12.8); // 刃長 ×1.35
        ctx.lineTo(1.3, -2);
        ctx.closePath();
      });
      fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
      break;
    case "axe":
      ctx.rotate(front ? -0.3 : 0.3);
      fill(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 20));
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(1, -17);
        ctx.quadraticCurveTo(9, -18, 8, -10);
        ctx.lineTo(1, -12);
        ctx.closePath();
      });
      break;
    case "hammer":
      drawHammer(ctx, it, [c, d], front);
      break;
    case "spear":
      drawSpear(ctx, it, [c, d], front);
      break;
    case "pistol":
      drawPistol(ctx, it, [c, d], front);
      break;
    case "shotgun":
      drawShotgun(ctx, it, [c, d], front);
      break;
    case "fist":
      drawFist(ctx, it, [c, d]);
      break;
    case "scythe":
      drawScythe(ctx, [c, d], front);
      break;
    case "whip":
      drawWhip(ctx, [c, d], it, front);
      break;
    case "orb":
      drawOrb(ctx, it, [c, d]);
      break;
    case "staff":
      drawStaff(ctx, it, c);
      break;
    case "bow":
      drawBow(ctx, c, front);
      break;
    case "crossbow":
      drawCrossbow(ctx, it, c, front);
      break;
    case "longgun":
      drawLongGun(ctx, it, c, d, front);
      break;
    case "shield_round":
    case "shield_kite":
      if (it.kind === "shield_kite" && it.form === "tower") drawTowerShield(ctx, [c, d]);
      else drawShield(ctx, it, c, d);
      break;
    case "tome":
      fill(ctx, c, () => rr(ctx, -4.5, -6, 9, 8, 1));
      fill(ctx, "#f2ead6", () => ctx.rect(-3.5, -5.5, 7, 1.2));
      fill(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -2, 1.6, 0, TAU));
      break;
    default:
      break;
  }
  ctx.restore();
}

/** 單獨畫一件主手武器（原點在握把附近、往上為負；小圖示用，Phase 3-18b）。 */
export function drawWeaponAlone(ctx: Ctx, it: GearItem): void {
  drawWeapon(ctx, it, 0, true);
}

/** 圖騰柱（召喚的圖騰）：木柱＋刻出的臉＋頂端寶珠。 */
function drawTotem(ctx: Ctx): void {
  fill(ctx, "rgba(0,0,0,0.25)", () => ctx.ellipse(0, -1, 9, 3, 0, 0, TAU));
  fill(ctx, "#6e4620", () => rr(ctx, -6, -40, 12, 40, 2));
  fill(ctx, "#8f5f2c", () => rr(ctx, -6, -40, 4, 40, 2));
  fill(ctx, "#b77f3f", () => rr(ctx, -8, -28, 16, 5, 1));
  fill(ctx, "#b77f3f", () => rr(ctx, -8, -14, 16, 5, 1));
  ctx.fillStyle = "#1d1a22";
  ctx.fillRect(-4, -36, 2.4, 3);
  ctx.fillRect(1.6, -36, 2.4, 3);
  ctx.fillRect(-2.5, -31, 5, 1.4);
  fill(ctx, "rgba(143,240,226,0.4)", () => ctx.arc(0, -44, 6.5, 0, TAU));
  fill(ctx, "#8ff0e2", () => ctx.arc(0, -44, 3.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -45.2, 1.1, 0, TAU));
}

/** 手的位置：正面時慣用手在畫面左、背面相反、側面時武器在前方。 */
export function handSides(facing: Facing): { main: number; off: number; side: number; view: View } {
  const view: View = facing === "north" ? "back" : "front";
  const side = facing === "east" ? 1 : facing === "west" ? -1 : 0;
  if (side !== 0) return { main: side * 8.5, off: -side * 8.5, side, view };
  return view === "back" ? { main: 8.5, off: -8.5, side, view } : { main: -8.5, off: 8.5, side, view };
}

/** 現行畫法的部件掛進 C 骨架（C-1b、C-2 逐步換成 C 畫法後移除）。 */
function legacyHooks(ctx: Ctx): InkHooks {
  return {
    colors: itemColors,
    weapon: (it, x, y, o) => {
      ctx.save();
      ctx.translate(x, y + 9.5 * o.scale); // drawWeapon 內部會再 translate(x, -9.5)
      ctx.scale(o.scale, o.scale);
      drawWeapon(ctx, it, 0, o.front, o.mirror, o.far, o.side);
      ctx.restore();
    },
    headgear: (it, view) => {
      ctx.save();
      ctx.translate(0, -42); // 現行頭心 (0,-29) → C 頭心 (0,-42)
      ctx.scale(HEAD_GEAR_SCALE, HEAD_GEAR_SCALE);
      ctx.translate(0, 29);
      if (view === "side") drawHeadgearSide(ctx, it, itemColors(it));
      else drawHeadgear(ctx, it, view);
      ctx.restore();
    },
    offhandSide: (it) => {
      ctx.save();
      ctx.scale(1.1, 1.4);
      drawOffhandSide(ctx, it, itemColors(it));
      ctx.restore();
    },
  };
}

/** 現行頭部裝備（頭半徑 8.5）套到 C 的頭（約 9）的縮放。 */
const HEAD_GEAR_SCALE = 1.06;

/** 畫一個小人（腳底中心在 (0, 0)）。facing：south ＝ 正面、north ＝ 背面、east／west ＝ 側面（西 ＝ 東的左右鏡像）。C 畫風（Phase C-1a）。 */
export function drawFigure(ctx: Ctx, spec: DollSpec, facing: Facing, ground = true): void {
  if (spec.totem === true) {
    drawTotem(ctx);
    return;
  }
  ctx.save();
  if (facing === "west") ctx.scale(-1, 1);
  const view: InkView = facing === "north" ? "back" : facing === "south" ? "front" : "side";
  drawInkFigure(ctx, spec, view, legacyHooks(ctx), ground);
  ctx.restore();
}

/** 倒地時橫躺的位置（旋轉前的平移量）。 */
const DOWNED_DX = 27;
const DOWNED_DY = 11;

/** 倒地姿勢：整個小人橫躺（頭朝右），腳底仍在原點附近。 */
export function drawFigurePose(ctx: Ctx, spec: DollSpec, facing: Facing, downed: boolean): void {
  if (!downed || spec.totem === true) {
    drawFigure(ctx, spec, facing);
    return;
  }
  ctx.save();
  ctx.translate(-DOWNED_DX, -DOWNED_DY);
  ctx.rotate(Math.PI / 2);
  drawFigure(ctx, spec, facing, false);
  ctx.restore();
}

/**
 * 產生一張離屏 canvas（`dpr` 倍解析度；沒有 DOM 時回傳 `null`）。腳底在 (DOLL_W/2, DOLL_FOOT_Y)。
 * C 畫風沒有黑色剪影外框（墨線取代它）；史詩、傳說（頭目）保留外光，是唯一的身體外光。
 */
export function renderFigureCanvas(spec: DollSpec, facing: Facing, downed: boolean, dpr: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const make = (): HTMLCanvasElement => {
    const c = document.createElement("canvas");
    c.width = DOLL_W * dpr;
    c.height = DOLL_H * dpr;
    return c;
  };
  const off = make();
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(DOLL_W / 2, DOLL_FOOT_Y);
  drawFigurePose(o, spec, facing, downed);
  const glowColor = spec.rarity !== undefined ? RARITY_GLOW[spec.rarity] : undefined;
  if (glowColor === undefined) return off;
  const glow = make();
  const g = glow.getContext("2d");
  const out = make();
  const ctx = out.getContext("2d");
  if (g === null || ctx === null) return off;
  g.drawImage(off, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = glowColor;
  g.fillRect(0, 0, glow.width, glow.height);
  ctx.save();
  ctx.globalAlpha = 0.5;
  for (let a = 0; a < 12; a++) {
    const ang = (a / 12) * TAU;
    ctx.drawImage(glow, Math.cos(ang) * 2.6 * dpr, Math.sin(ang) * 2.6 * dpr);
  }
  ctx.restore();
  ctx.drawImage(off, 0, 0);
  return out;
}

/** 單獨畫一件側面手持物（面向右；x ＝ 手的位置；`far` ＝ 成對武器的副手）。測試與預覽用。 */
export function drawWeaponSide(ctx: Ctx, it: GearItem, x: number, far = false): void {
  drawWeapon(ctx, it, x, true, false, far, true);
}
