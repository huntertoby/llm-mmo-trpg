// 紙娃娃的裝備外觀新部件（Phase 3G-G5b；移植自美術 PM 樣張 docs/art/sample/paperdoll.js，九格新增的造型與形制）。
// 座標同 paperdoll.ts：腳底中心為原點、往上為負；武器函式的原點在握把（手的位置），`front` ＝ 正面／側面（武器朝前）。
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import { elementTint, type GearItem, type Look } from "./appearance";

export function mix(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const m = (s: number): number => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
}

export function fill(ctx: Ctx, color: string, path: () => void): void {
  ctx.fillStyle = color;
  ctx.beginPath();
  path();
  ctx.fill();
}

type Colors = readonly [string, string];

// ---- 腳 ----

/** 靴筒高度：布鞋 0、皮靴短 2.5／長 4、鐵靴 3、脛甲 4。 */
function bootHeight(feet: GearItem): number {
  switch (feet.kind) {
    case "greaves":
      return 4;
    case "boots":
      return feet.form === "tall" ? 4 : 2.5;
    case "iron_boots":
      return 3;
    default:
      return 0;
  }
}

/** 兩隻腳：靴筒、護膝、綁帶、鞋底（鐵靴鞋尖亮塊）；沒穿裝備時是預設的矮靴底。 */
export function drawFeet(ctx: Ctx, feet: GearItem | undefined, b: string, bd: string): void {
  const tall = feet === undefined ? 0 : bootHeight(feet);
  const iron = feet?.kind === "iron_boots";
  for (const sx of [-1, 1]) {
    if (tall > 0) fill(ctx, b, () => rr(ctx, sx * 3 - 2.2, -2 - tall, 4.4, tall + 1, 1));
    if (feet?.kind === "greaves" && feet.form === "knee") fill(ctx, mix(b, "#ffffff", 0.3), () => rr(ctx, sx * 3 - 2, -8, 4, 2.4, 1));
    if (feet?.kind === "shoes" && feet.form === "wrapped") {
      ctx.strokeStyle = bd;
      ctx.lineWidth = 0.8;
      for (const y of [-4, -6]) {
        ctx.beginPath();
        ctx.moveTo(sx * 3 - 2, y);
        ctx.lineTo(sx * 3 + 2, y + 1);
        ctx.stroke();
      }
    }
    fill(ctx, bd, () => {
      ctx.beginPath();
      ctx.ellipse(sx * 3.2, -1.2, iron ? 3.6 : 3.2, 2, 0, 0, TAU);
    });
    if (iron) {
      fill(ctx, mix(b, "#ffffff", 0.35), () => {
        ctx.beginPath();
        ctx.ellipse(sx * 3.2, -1.6, 1.6, 1, 0, 0, TAU);
      });
    }
  }
}

// ---- 身 ----

/** 外套：長下襬開衩、翻領、扣子；披風形制多一片肩披。 */
export function drawCoat(ctx: Ctx, it: GearItem | undefined, c: string, d: string): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(-7.5, -21);
    ctx.lineTo(7.5, -21);
    ctx.lineTo(8.5, -3);
    ctx.lineTo(1, -3);
    ctx.lineTo(0, -9);
    ctx.lineTo(-1, -3);
    ctx.lineTo(-8.5, -3);
    ctx.closePath();
  });
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.moveTo(-4, -21);
    ctx.lineTo(0, -15);
    ctx.lineTo(4, -21);
    ctx.closePath();
  });
  for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => ctx.arc(1.8, y, 0.7, 0, TAU));
  if (it?.form === "cape") fill(ctx, d, () => rr(ctx, -9, -22, 18, 5, 2));
}

/** 鎖甲的紋路：鎖環小點，鱗甲形制畫成一片片小鱗。 */
export function drawMailPattern(ctx: Ctx, form: string | undefined, d: string): void {
  ctx.fillStyle = d;
  if (form === "scale") {
    for (let y = -19; y < -9; y += 2.6) {
      for (let x = -6; x < 6.5; x += 3) {
        ctx.beginPath();
        ctx.arc(x + (Math.trunc(y) % 2 !== 0 ? 1.5 : 0), y, 1.3, 0, Math.PI);
        ctx.fill();
      }
    }
    return;
  }
  for (let y = -19; y < -9; y += 2.4) for (let x = -6 + (Math.trunc(y) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1);
}

// ---- 手 ----

/** 兩隻手：臂環只包前臂、手露膚色；露指手套露膚色；長手套多一截袖口（護手有袖口）。 */
export function drawHandsGear(ctx: Ctx, look: Look, hands: GearItem | undefined, [c, d]: Colors): void {
  const bracer = hands?.kind === "bracers";
  // 護手的袖口只在指定形制時才畫（舊範本沒有形制，畫面維持原樣）
  const cuff = bracer || (hands?.kind === "gauntlets" && hands.form !== undefined) || hands?.form === "long";
  for (const x of [-8.5, 8.5]) {
    if (hands !== undefined && cuff) fill(ctx, bracer ? c : d, () => rr(ctx, x - 2.2, -14, 4.4, hands.form === "ring" ? 1.8 : 3.4, 1));
    fill(ctx, bracer || hands?.form === "fingerless" ? look.skin : hands !== undefined ? c : look.skin, () => ctx.arc(x, -9.5, 2.4, 0, TAU));
    if (hands?.form === "fingerless") fill(ctx, c, () => rr(ctx, x - 2.4, -10.5, 4.8, 2, 0.8));
  }
}

// ---- 頭 ----

export function drawWideHat(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.ellipse(0, -34, 14, 3.4, 0, 0, TAU);
  });
  fill(ctx, c, () => rr(ctx, -7, -42, 14, 8, 3));
  fill(ctx, it.trim ?? d, () => ctx.rect(-7, -36.5, 14, 1.6));
}

/** 皮帽／毛帽（形制 `fur`：毛邊白、較厚）。 */
export function drawCap(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(0, -31, 9.2, Math.PI, 0);
    ctx.closePath();
  });
  fill(ctx, it.form === "fur" ? "#e9e3cf" : d, () => rr(ctx, -9.6, -32.5, 19.2, it.form === "fur" ? 4 : 2.4, 1.5));
}

/** 全罩盔：整顆頭包住，正面有細縫與鼻樑條。 */
export function drawGreathelm(ctx: Ctx, [c, d]: Colors, back: boolean): void {
  fill(ctx, c, () => rr(ctx, -9.6, -39, 19.2, 17, 4));
  if (!back) {
    fill(ctx, "#1d1a22", () => ctx.rect(-6.5, -31, 13, 1.8));
    fill(ctx, d, () => ctx.rect(-0.8, -29, 1.6, 6));
  }
  fill(ctx, mix(c, "#ffffff", 0.4), () => rr(ctx, -6, -38, 4, 3, 1.5));
}

// ---- 主手 ----

/** 錘（形制 `mace` 釘頭錘球頭、`flail` 連枷＝短柄加鏈上鐵球、`warhammer` 戰錘方頭）。 */
export function drawHammer(ctx: Ctx, it: GearItem, [c, d]: Colors, front: boolean): void {
  ctx.rotate(front ? -0.3 : 0.3);
  if (it.form === "mace") {
    fill(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 21));
    fill(ctx, c, () => ctx.arc(0, -19, 4, 0, TAU));
    fill(ctx, d, () => ctx.rect(-4, -19.5, 8, 1));
    return;
  }
  if (it.form === "flail") {
    fill(ctx, "#6a4420", () => ctx.rect(-1, -14, 2, 17));
    ctx.strokeStyle = d;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.quadraticCurveTo(front ? 5 : -5, -20, 0, -23);
    ctx.stroke();
    fill(ctx, c, () => ctx.arc(0, -24, 3.4, 0, TAU));
    return;
  }
  fill(ctx, "#6a4420", () => ctx.rect(-1.1, -22, 2.2, 24));
  fill(ctx, c, () => rr(ctx, -6.5, -28, 13, 8, 1.5));
  fill(ctx, d, () => ctx.rect(-6.5, -24.5, 13, 1.2));
}

/** 矛（形制 `halberd` 戟＝側邊多一片斧刃、`trident` 三叉戟；預設單尖矛）。 */
export function drawSpear(ctx: Ctx, it: GearItem, [c]: Colors, front: boolean): void {
  ctx.rotate(front ? -0.15 : 0.15);
  fill(ctx, "#8a6a3a", () => ctx.rect(-0.9, -34, 1.8, 38));
  if (it.form === "trident") {
    for (const sx of [-3, 0, 3]) {
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(sx, sx === 0 ? -43 : -41);
        ctx.lineTo(sx + 1.2, -33);
        ctx.lineTo(sx - 1.2, -33);
        ctx.closePath();
      });
    }
    fill(ctx, c, () => rr(ctx, -3.5, -34, 7, 1.4, 0.6));
    return;
  }
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(0, -42);
    ctx.quadraticCurveTo(3.4, -37, 0, -32);
    ctx.quadraticCurveTo(-3.4, -37, 0, -42);
    ctx.closePath();
  });
  if (it.form === "halberd") {
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.moveTo(1, -37);
      ctx.quadraticCurveTo(7, -38, 6.5, -32);
      ctx.lineTo(1, -33);
      ctx.closePath();
    });
  }
}

/** 拳套（形制 `katar` 拳刃、`claw` 爪、`knuckle` 指虎）：握在手裡的鐵塊，katar／claw 前端多一片刃。 */
export function drawFist(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  fill(ctx, c, () => rr(ctx, -2.5, -3, 5, 5, 1.5));
  if (it.form === "knuckle") {
    for (const x of [-1.8, 0, 1.8]) fill(ctx, d, () => ctx.arc(x, -3.2, 0.8, 0, TAU));
    return;
  }
  const blades = it.form === "claw" ? [-1.6, 0, 1.6] : [0];
  for (const x of blades) {
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.moveTo(x - 1.2, -3);
      ctx.lineTo(x, it.form === "claw" ? -8.5 : -10);
      ctx.lineTo(x + 1.2, -3);
      ctx.closePath();
    });
  }
}

export function drawScythe(ctx: Ctx, [c]: Colors, front: boolean): void {
  const s = front ? 1 : -1;
  ctx.rotate(front ? -0.15 : 0.15);
  fill(ctx, "#6a4420", () => ctx.rect(-1, -26, 2, 30));
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(0, -26);
    ctx.quadraticCurveTo(s * 12, -28, s * 14, -18);
    ctx.quadraticCurveTo(s * 8, -23, 0, -23);
    ctx.closePath();
  });
}

export function drawWhip(ctx: Ctx, [c, d]: Colors, it: GearItem, front: boolean): void {
  const s = front ? -1 : 1;
  fill(ctx, "#4a3020", () => ctx.rect(-1, -4, 2, 5));
  ctx.strokeStyle = it.form === "chain" ? d : c;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(0, -4);
  ctx.bezierCurveTo(s * 8, -8, s * 4, 6, s * 12, 8);
  ctx.stroke();
  if (it.form === "bladed") fill(ctx, "#c3ccd6", () => ctx.arc(s * 12, 8, 1.3, 0, TAU));
}

/** 手槍（形制 `flintlock` 燧發、`revolver` 左輪、`derringer` 袖珍雙管）：槍口朝前下方，握把在手裡。 */
export function drawPistol(ctx: Ctx, it: GearItem, [c, d]: Colors, front: boolean): void {
  ctx.rotate(front ? 0.35 : -0.35);
  const s = front ? -1 : 1;
  const L = it.form === "derringer" ? 5 : it.form === "revolver" ? 8 : 7;
  const x0 = s > 0 ? -1 : -L;
  fill(ctx, it.form === "flintlock" ? "#7a5232" : "#3a2a1c", () => rr(ctx, -1.4, -1, 2.8, 5, 0.8)); // 握把
  fill(ctx, c, () => rr(ctx, x0, -3.2, L + 1, 2.6, 1)); // 槍身
  if (it.form === "derringer") fill(ctx, d, () => rr(ctx, x0, -0.9, L + 1, 1.8, 0.8)); // 第二根槍管
  if (it.form === "revolver") fill(ctx, d, () => rr(ctx, s > 0 ? 0 : -4.2, -4.4, 4.2, 4.4, 1.6)); // 轉輪
  if (it.form === "flintlock") {
    fill(ctx, d, () => {
      ctx.beginPath();
      ctx.moveTo(s * 0.5, -3.2);
      ctx.lineTo(s * -1, -5.8);
      ctx.lineTo(s * 1.2, -6.2);
      ctx.lineTo(s * 2, -3.2);
      ctx.closePath();
    }); // 擊錘
  }
}

/** 霰彈槍（形制 `blunderbuss` 喇叭口、`double` 雙管、`pump` 滑套）：槍托固定木色。 */
export function drawShotgun(ctx: Ctx, it: GearItem, [c, d]: Colors, front: boolean): void {
  ctx.rotate(front ? 0.35 : -0.35);
  const s = front ? -1 : 1;
  const L = it.form === "blunderbuss" ? 12 : 15;
  const x0 = s > 0 ? -1 : -L;
  fill(ctx, "#3a2a1c", () => rr(ctx, -1.2, -1, 2.4, 5, 0.8)); // 握把
  fill(ctx, "#7a5232", () => rr(ctx, s > 0 ? -6 : 1, -3.4, 5.5, 3.4, 1)); // 槍托
  fill(ctx, c, () => rr(ctx, x0, -3.4, L + 1, 3, 1)); // 槍身
  if (it.form === "double") fill(ctx, d, () => rr(ctx, x0, -0.5, L + 1, 2.2, 0.8)); // 第二根槍管
  if (it.form === "pump") fill(ctx, "#7a5232", () => rr(ctx, x0 + (s > 0 ? 5 : L - 11), -0.6, 6, 2.2, 0.8)); // 滑套
  if (it.form === "blunderbuss") {
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.moveTo(s * (L - 5), -3.4);
      ctx.lineTo(s * (L + 1), -6);
      ctx.lineTo(s * (L + 1), 1.6);
      ctx.lineTo(s * (L - 5), -0.4);
      ctx.closePath();
    }); // 喇叭口
  }
}

// ---- 副手 ----

/** 法球（形制 `ball` 握在手裡、`floating` 浮在手上方）：球色取元素色，沒有就用材質色。 */
export function drawOrb(ctx: Ctx, it: GearItem, [c]: Colors): void {
  const orb = elementTint(it.element) ?? c;
  const y = it.form === "floating" ? -9 : -6;
  if (it.form === "floating") {
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.ellipse(0, -2, 4, 1.2, 0, 0, TAU);
    ctx.stroke();
  }
  ctx.fillStyle = orb;
  ctx.globalAlpha = 0.35;
  ctx.beginPath();
  ctx.arc(0, y, 6, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
  fill(ctx, orb, () => ctx.arc(0, y, 3.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, y - 1.2, 1.1, 0, TAU));
}

/** 塔盾：長方形大盾（鳶盾的 `tower` 形制）。 */
export function drawTowerShield(ctx: Ctx, [c, d]: Colors): void {
  fill(ctx, d, () => rr(ctx, -7.5, -16, 15, 21, 2));
  fill(ctx, c, () => rr(ctx, -6, -14.5, 12, 18, 1.5));
  fill(ctx, "#e8e0c8", () => ctx.rect(-0.9, -14, 1.8, 17));
}
