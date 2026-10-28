// 紙娃娃的裝備外觀新部件（Phase 3G-G5b；移植自美術 PM 樣張 docs/art/sample/paperdoll.js，九格新增的造型與形制）。
// 座標同 paperdoll.ts：腳底中心為原點、往上為負；武器函式的原點在握把（手的位置），`front` ＝ 正面／側面（武器朝前）。
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import type { GearItem } from "./appearance";

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

