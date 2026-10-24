// 真側面的頭部裝備、盾、披風（Phase 3S-2）。面向右（+x ＝ 前）；座標同紙娃娃：腳底為原點、頭心 (0, -29)、頭半徑 8.5。
// 朝西由 paperdoll.ts 整張左右鏡像。每個函式只吃顏色與 GearItem，不匯入 paperdoll.ts（避免循環匯入）。
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import type { GearItem } from "./appearance";
import { fill, mix } from "./paperdollGear";

type Colors = readonly [string, string];

/** 取暗色；不是 6 位十六進位色時原樣回傳。 */
export function dark(c: string, t = 0.3): string {
  return /^#[0-9a-f]{6}$/i.test(c) ? mix(c, "#000000", t) : c;
}

const lighter = (c: string, t = 0.4): string => (/^#[0-9a-f]{6}$/i.test(c) ? mix(c, "#ffffff", t) : c);

/** 一支角：從 (ox, y) 往後上方彎出去。 */
function hornShape(ctx: Ctx, ox: number, y: number, size: number): void {
  ctx.moveTo(ox + 2 * size, y);
  ctx.quadraticCurveTo(ox - 2 * size, y - 6 * size, ox - 6.5 * size, y - 7.5 * size);
  ctx.quadraticCurveTo(ox - 2.5 * size, y - 3 * size, ox - 1 * size, y + 0.5 * size);
  ctx.closePath();
}

/** 角（頭盔角與種族角同一套畫法）：兩支都往後彎，遠側（ `far` ）較暗、畫在頭後面。 */
export function drawHornSide(ctx: Ctx, color: string, far: boolean, base = { x: 0, y: -36 }, size = 1): void {
  const ox = base.x + (far ? -3.2 : 1.2) * size;
  fill(ctx, far ? dark(color, 0.3) : color, () => hornShape(ctx, ox, base.y, size));
}

/** 頭盔（含角盔）：圓頂＋後頸甲，護鼻片在臉前方；角盔的遠側角在盔後、近側角蓋在盔上。 */
function drawHelmetSide(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  const horned = it.kind === "horned_helm";
  const horn = { x: -1, y: -35 };
  if (horned) drawHornSide(ctx, "#efe6cc", true, horn, 1.3);
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(-0.5, -30, 9.6, Math.PI, 0);
    ctx.lineTo(9.1, -27);
    ctx.lineTo(7, -26.5);
    ctx.lineTo(-3, -26.5);
    ctx.lineTo(-3, -22.5); // 後頸甲
    ctx.lineTo(-9.8, -22.5);
    ctx.closePath();
  });
  fill(ctx, d, () => ctx.rect(-10.1, -28.5, 19.2, 1.6)); // 盔緣
  fill(ctx, d, () => ctx.rect(6.8, -28, 2.1, 6.5)); // 護鼻片移到前方
  fill(ctx, lighter(c), () => rr(ctx, -6, -37, 4, 3, 1.5));
  if (horned) drawHornSide(ctx, "#efe6cc", false, horn, 1.3);
}

/** 兜帽：帽身往後垂，臉的開口往前移、變窄。 */
function drawHoodSide(ctx: Ctx, [c, d]: Colors): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.arc(-1.5, -29.5, 10, Math.PI * 0.85, Math.PI * 2.15);
  ctx.lineTo(9, -22);
  ctx.lineTo(-11.5, -21);
  ctx.lineTo(-11, -25);
  ctx.closePath();
  ctx.ellipse(4.5, -28, 4.6, 6, 0, 0, TAU); // 臉的開口
  ctx.fill("evenodd");
  fill(ctx, d, () => ctx.rect(-11, -23, 20, 1.5));
}

/** 巫師帽：整頂朝前傾、帽尖往後彎。 */
function drawWizardHatSide(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  ctx.save();
  ctx.translate(0, -34);
  ctx.rotate(0.1);
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(-8, 0);
    ctx.quadraticCurveTo(-5, -9, -2, -13);
    ctx.quadraticCurveTo(-5, -17, -10, -15); // 帽尖朝後彎
    ctx.quadraticCurveTo(-3, -17, 1, -12);
    ctx.quadraticCurveTo(5, -6, 8, 0);
    ctx.closePath();
  });
  fill(ctx, d, () => ctx.ellipse(0, 0, 13, 3, 0, 0, TAU));
  fill(ctx, it.trim ?? "#e8bb48", () => ctx.rect(-7, -2.8, 14, 1.8));
  ctx.restore();
}

/** 寬簷帽：簷橢圓、頂圓，整頂略朝前傾。 */
function drawWideHatSide(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  ctx.save();
  ctx.translate(0, -34);
  ctx.rotate(0.08);
  fill(ctx, d, () => ctx.ellipse(0.5, 0, 14, 3.2, 0, 0, TAU));
  fill(ctx, c, () => rr(ctx, -6.5, -8, 13, 8, 3));
  fill(ctx, it.trim ?? d, () => ctx.rect(-6.5, -2.5, 13, 1.6));
  ctx.restore();
}

/** 便帽／毛帽：圓頂，毛邊或帽緣在額頭，皮帽前方多一小段帽舌。 */
function drawCapSide(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  const fur = it.form === "fur";
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(-0.5, -31, 9.4, Math.PI, 0);
    ctx.closePath();
  });
  fill(ctx, fur ? "#e9e3cf" : d, () => rr(ctx, -10.1, -32.5, 19.8, fur ? 4 : 2.4, 1.5));
  if (!fur) fill(ctx, d, () => rr(ctx, 7, -31, 4, 1.6, 0.8));
}

/** 全罩盔：整顆頭包住，眼縫只在前半。 */
function drawGreathelmSide(ctx: Ctx, [c, d]: Colors): void {
  fill(ctx, c, () => rr(ctx, -9.8, -39, 19.6, 17, 4));
  fill(ctx, d, () => rr(ctx, 7, -39, 3.6, 17, 1.5)); // 前緣加厚
  fill(ctx, "#1d1a22", () => ctx.rect(1.5, -31, 9, 1.8)); // 眼縫
  fill(ctx, d, () => ctx.rect(2, -27.5, 1.2, 5)); // 面甲條
  fill(ctx, lighter(c), () => rr(ctx, -6, -38, 4, 3, 1.5));
}

/** 頭巾：包住額頭，結在腦後、兩條尾巴往後飄。 */
function drawBandanaSide(ctx: Ctx, [c, d]: Colors): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(-0.5, -30, 9, Math.PI * 1.05, Math.PI * 1.95);
    ctx.closePath();
  });
  fill(ctx, c, () => ctx.rect(-9.5, -31.5, 18.6, 3));
  for (const [dy, len] of [[0, 7], [2.5, 5]] as const) {
    fill(ctx, d, () => {
      ctx.beginPath();
      ctx.moveTo(-9, -30 + dy);
      ctx.lineTo(-9 - len, -28 + dy + 1.5);
      ctx.lineTo(-9 - len + 2, -26 + dy);
      ctx.lineTo(-8, -28.5 + dy);
      ctx.closePath();
    });
  }
}

/** 王冠：側面看到三個尖，寶石在前。 */
function drawCrownSide(ctx: Ctx, [c]: Colors): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(-6, -35);
    ctx.lineTo(-6.5, -41);
    ctx.lineTo(-3, -38);
    ctx.lineTo(0, -42);
    ctx.lineTo(3, -38);
    ctx.lineTo(6.5, -41);
    ctx.lineTo(6, -35);
    ctx.closePath();
  });
  fill(ctx, "#d23c3c", () => ctx.arc(3.5, -36.8, 1.2, 0, TAU));
}

/** 頭部裝備的側面形狀；不認得的 kind 不畫。 */
export function drawHeadgearSide(ctx: Ctx, it: GearItem | undefined, colors: Colors | undefined): void {
  if (it === undefined || colors === undefined) return;
  switch (it.kind) {
    case "helmet":
    case "horned_helm":
      drawHelmetSide(ctx, it, colors);
      break;
    case "hood":
      drawHoodSide(ctx, colors);
      break;
    case "wizard_hat":
      drawWizardHatSide(ctx, it, colors);
      break;
    case "wide_hat":
      drawWideHatSide(ctx, it, colors);
      break;
    case "cap":
      drawCapSide(ctx, it, colors);
      break;
    case "greathelm":
      drawGreathelmSide(ctx, colors);
      break;
    case "bandana":
      drawBandanaSide(ctx, colors);
      break;
    case "crown":
      drawCrownSide(ctx, colors);
      break;
    default:
      break;
  }
}

/** 披風：從肩後垂下，下擺往後飄；內側一道亮褶。 */
export function drawCloakSide(ctx: Ctx, [c, d]: Colors): void {
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.moveTo(-4, -22);
    ctx.lineTo(1.5, -22);
    ctx.lineTo(0, -3);
    ctx.quadraticCurveTo(-7, 1, -14, -3);
    ctx.quadraticCurveTo(-11, -12, -4, -22);
    ctx.closePath();
  });
  ctx.strokeStyle = c;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-3, -19);
  ctx.quadraticCurveTo(-6, -10, -8, -3.5);
  ctx.stroke();
  fill(ctx, c, () => rr(ctx, -4.5, -22.5, 6, 2, 1)); // 領口
}

/** 盾與書（副手）：擋在身前的側邊；法器珠由呼叫端用既有畫法。 */
export function drawOffhandSide(ctx: Ctx, it: GearItem, [c, d]: Colors): void {
  if (it.kind === "tome") {
    fill(ctx, c, () => rr(ctx, 4.5, -19, 4.6, 10, 1)); // 封面（側看＝一條厚書脊）
    fill(ctx, "#f2ead6", () => ctx.rect(8.2, -18.2, 1.3, 8.4)); // 書頁邊
    fill(ctx, it.trim ?? "#e8bb48", () => ctx.rect(4.5, -15.5, 4, 1.2));
    return;
  }
  if (it.kind === "shield_kite" && it.form === "tower") {
    fill(ctx, d, () => rr(ctx, 5.3, -22.5, 4.6, 24.5, 1.5));
    fill(ctx, c, () => rr(ctx, 6, -21.5, 3, 22.5, 1));
    fill(ctx, "#e8e0c8", () => ctx.rect(8.7, -21, 0.9, 21));
    return;
  }
  if (it.kind === "shield_kite") {
    fill(ctx, d, () => {
      ctx.beginPath();
      ctx.moveTo(5.5, -21.5);
      ctx.lineTo(9.6, -21.5);
      ctx.lineTo(8.6, -8);
      ctx.lineTo(7.2, -4); // 鳶盾下尖
      ctx.lineTo(6, -8);
      ctx.closePath();
    });
    fill(ctx, c, () => rr(ctx, 6.3, -20.5, 2.4, 11, 1));
    return;
  }
  // 圓盾
  fill(ctx, d, () => ctx.ellipse(7, -14, 3.1, 7.6, 0, 0, TAU));
  fill(ctx, c, () => ctx.ellipse(7, -14, 2.2, 6.3, 0, 0, TAU));
  fill(ctx, it.trim ?? "#e8bb48", () => ctx.ellipse(8.1, -14, 1, 2.2, 0, 0, TAU)); // 盾心突起朝前
}
