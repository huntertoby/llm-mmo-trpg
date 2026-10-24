// 紙娃娃的第三套畫法：真側面（Phase 3S-1；移植自美術 PM 樣張 docs/art/sample/sideArt.js，bodyTurn = headTurn = 1）。
// 面向右（東）；朝西由 paperdoll.ts 左右鏡像。座標同紙娃娃：腳底中心為原點、往上為負，頭心 (0, -29)。
// 圖層順序（側面畫法.md）：披風 → 遠側腿 → 近側腿 → 遠側手臂 → 身體 → 副手 → 頭 → 頭髮 → 頭部裝備 → 近側手臂 → 主手武器。
// 3S-1 只做骨架與身體；頭部裝備、盾、披風在 paperdollSideGear.ts（3S-2）；武器先用最簡退回（3S-3 再換成側面形狀）。
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import type { DollSpec, GearItem, Look } from "./appearance";
import { bootHeight, fill, mix } from "./paperdollGear";
import { dark, drawCloakSide, drawHeadgearSide, drawOffhandSide } from "./paperdollSideGear";

/** 側面時身體的寬度（正面為 15）。 */
export const SIDE_BODY_W = 10;
/** 臉往前（+x）偏移的量。 */
export const SIDE_FACE_X = 4.2;
/** 兩腳前後錯開的角度（弧度）。 */
const STRIDE = 0.28;
/** 近側手臂往前擺的角度。 */
const ARM_SWING = -0.3;

type ItemColors = (it: GearItem) => readonly [string, string];

const HAIR_COVERED = ["helmet", "hood", "wizard_hat", "horned_helm", "greathelm", "cap"];

function drawLeg(ctx: Ctx, look: Look, feet: GearItem | undefined, colors: ItemColors, x: number, ang: number, near: boolean): void {
  const pants = look.pants ?? "#4a4038";
  const [b, bd] = feet !== undefined ? colors(feet) : ["#5a4030", "#3a281c"];
  const tall = feet === undefined ? 0 : bootHeight(feet);
  ctx.save();
  ctx.translate(x, -9);
  ctx.rotate(ang);
  fill(ctx, near ? pants : dark(pants, 0.25), () => rr(ctx, -2, 0, 4, 8.5, 1));
  if (tall > 0) fill(ctx, near ? b : dark(b, 0.2), () => rr(ctx, -2.2, 7.5 - tall, 4.4, tall + 1, 1));
  if (feet?.kind === "greaves" && feet.form === "knee") fill(ctx, mix(b, "#ffffff", 0.3), () => rr(ctx, -2, 1, 4, 2.4, 1));
  const iron = feet?.kind === "iron_boots";
  fill(ctx, near ? bd : dark(bd, 0.2), () => ctx.ellipse(1.6, 8, iron ? 4.2 : 3.8, 2, 0, 0, TAU)); // 鞋尖朝前
  ctx.restore();
}

function drawLegs(ctx: Ctx, look: Look, feet: GearItem | undefined, colors: ItemColors): void {
  drawLeg(ctx, look, feet, colors, 0.5, -STRIDE, false); // 遠側腿較暗、往前
  drawLeg(ctx, look, feet, colors, -0.5, STRIDE, true); // 近側腿往後
}

/** 手臂：袖子＋手；回傳手的位置（拿武器用）。 */
function drawArm(
  ctx: Ctx,
  body: GearItem | undefined,
  look: Look,
  hands: GearItem | undefined,
  colors: ItemColors,
  sx: number,
  swing: number,
  near: boolean,
): { x: number; y: number } {
  const kind = body?.kind ?? "shirt";
  const c = kind === "ribs" ? "#d9d2bd" : body !== undefined ? colors(body)[0] : "#d8cdb4";
  const skinHand = hands === undefined || hands.kind === "bracers" || hands.form === "fingerless";
  const hc = hands !== undefined && !skinHand ? colors(hands)[0] : look.skin;
  ctx.save();
  ctx.translate(sx, -20);
  ctx.rotate(swing);
  fill(ctx, near ? c : dark(c, 0.2), () => rr(ctx, -2, 0, 4, 10, 2));
  if (kind === "plate" && body?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => ctx.ellipse(0, 0.5, 3.2, 2.4, 0, 0, TAU));
  fill(ctx, near ? hc : dark(hc, 0.15), () => ctx.arc(0, 10.5, 2.4, 0, TAU));
  ctx.restore();
  return { x: sx + Math.sin(-swing) * 10.5, y: -20 + Math.cos(swing) * 10.5 };
}

function drawRibsSide(ctx: Ctx): void {
  fill(ctx, "#d9d2bd", () => rr(ctx, -1.5, -21, 3, 13, 1));
  ctx.strokeStyle = "#d9d2bd";
  ctx.lineWidth = 2;
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.moveTo(-4, -19 + i * 3);
    ctx.quadraticCurveTo(0, -17 + i * 3, 4, -19 + i * 3);
    ctx.stroke();
  }
  fill(ctx, "#d9d2bd", () => rr(ctx, -3.5, -9, 7, 2.5, 1));
}

/** 身體主體；回傳背側暗面的高度。 */
function drawTorsoShape(ctx: Ctx, it: GearItem | undefined, look: Look, c: string, d: string): number {
  const kind = it?.kind ?? "shirt";
  const x0 = -SIDE_BODY_W / 2 - 0.5;
  const front = x0 + SIDE_BODY_W; // 前緣
  if (kind === "robe") {
    const hem = it?.form === "short" ? -6 : -1.5;
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.moveTo(x0, -21);
      ctx.lineTo(front, -21);
      ctx.lineTo(front + 4, hem);
      ctx.lineTo(x0 - 1.5, hem);
      ctx.closePath();
    });
    fill(ctx, look.trim ?? d, () => ctx.rect(front - 2.6, -20, 2.4, hem + 19)); // 前襟在前方
    return hem + 21;
  }
  if (kind === "coat") {
    fill(ctx, c, () => rr(ctx, x0, -21, SIDE_BODY_W, 18, 3));
    fill(ctx, d, () => ctx.rect(front - 2.4, -20, 2.4, 14)); // 前襟
    for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => ctx.arc(front - 1.2, y, 0.7, 0, TAU));
    return 18;
  }
  fill(ctx, c, () => rr(ctx, x0, -21, SIDE_BODY_W, 13.5, 3));
  if (kind === "plate") {
    fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, front - 4.5, -19.5, 3, 6, 1.5)); // 胸甲亮片移到前緣
  } else if (kind === "mail") {
    ctx.fillStyle = d;
    for (let y = -19; y < -9; y += 2.4) for (let x = x0 + 1.5; x < front - 1; x += 2.4) ctx.fillRect(x, y, 1, 1);
  } else if (kind === "leather") {
    ctx.strokeStyle = d;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x0 + 2, -20);
    ctx.lineTo(front - 2, -11);
    ctx.stroke();
  }
  fill(ctx, "#3a2a1c", () => ctx.rect(x0, -9.5, SIDE_BODY_W, 2)); // 腰帶
  fill(ctx, "#d8b04a", () => ctx.rect(front - 2.5, -9.5, 2, 2)); // 腰扣在前緣
  return 13.5;
}

function drawTorso(ctx: Ctx, it: GearItem | undefined, look: Look, colors: ItemColors): void {
  if (it?.kind === "ribs") {
    drawRibsSide(ctx);
    return;
  }
  const [c, d] = it !== undefined ? colors(it) : ["#d8cdb4", "#a89c80"];
  const h = drawTorsoShape(ctx, it, look, c, d);
  fill(ctx, "rgba(0,0,0,0.16)", () => rr(ctx, -SIDE_BODY_W / 2 - 0.5, -21, SIDE_BODY_W * 0.32, h, 2)); // 背側暗面
}

function drawHeadSide(ctx: Ctx, look: Look): void {
  fill(ctx, look.skin, () => ctx.arc(0, -29, 8.5, 0, TAU));
  const fx = SIDE_FACE_X;
  ctx.fillStyle = look.eyes ?? "#1d1a22";
  if (look.skull === true) {
    ctx.beginPath();
    ctx.arc(fx + 1.5, -29, 2.4, 0, TAU);
    ctx.fill();
    ctx.fillRect(fx + 0.5, -24.5, 4, 1.2);
    return;
  }
  const eye = fx + 1.8; // 只看得到近側的一隻眼
  ctx.fillRect(eye, -30, 1.8, 3);
  fill(ctx, look.skin, () => {
    ctx.moveTo(8, -28.5); // 鼻子
    ctx.lineTo(10.2, -26.3);
    ctx.lineTo(8.3, -25.5);
    ctx.closePath();
  });
  ctx.fillStyle = "rgba(220,90,90,0.35)";
  ctx.fillRect(eye - 0.5, -26.5, 2, 1.2);
  fill(ctx, dark(look.skin, 0.15), () => ctx.ellipse(-1.5, -28.5, 1.6, 2.4, 0, 0, TAU)); // 耳朵在頭中後方
}

function drawHairSide(ctx: Ctx, look: Look, head: GearItem | undefined): void {
  if (look.hair === undefined || look.hair === "none" || look.skull === true) return;
  if (head !== undefined && HAIR_COVERED.includes(head.kind)) return;
  const c = look.hairColor ?? "#5a3a22";
  // 後腦整片是頭髮、前面只剩瀏海
  fill(ctx, c, () => {
    ctx.arc(-1.5, -29.5, 8.8, Math.PI * 0.75, Math.PI * 1.85);
    ctx.quadraticCurveTo(6, -33, 3, -32.5);
    ctx.closePath();
  });
  if (look.hair === "long") fill(ctx, c, () => rr(ctx, -8.5, -31, 5, 11, 1.5));
}

/** 由 paperdoll.ts 提供的既有畫法（避免循環匯入）。 */
export interface SideHooks {
  colors: ItemColors;
  /** 畫一件手持物（x ＝ 手的 x；原點 y 在 -9.5；不鏡像）。 */
  weapon: (it: GearItem | undefined, x: number) => void;
}

/** 畫一個側面小人（面向右）。 */
export function drawFigureSide(ctx: Ctx, spec: DollSpec, h: SideHooks): void {
  const { look, gear } = spec;
  const farArmX = -1.5;
  const nearArmX = 1.5;
  const offKind = gear.off_hand?.kind;
  const offIsShield = offKind?.startsWith("shield") === true;
  const offHeld = offKind === "tome" || offKind === "orb"; // 不鏡像的副手手持物
  // 成對武器（主手副手同一種武器）與拳套：副手那把畫在身後露出來
  const offItem = gear.off_hand ?? (gear.main_hand?.kind === "fist" ? gear.main_hand : undefined);
  if (gear.cloak !== undefined) drawCloakSide(ctx, h.colors(gear.cloak));
  if (offItem !== undefined && !offIsShield && !offHeld) h.weapon(offItem, farArmX + 3);
  drawLegs(ctx, look, gear.feet, h.colors);
  drawArm(ctx, gear.body, look, gear.hands, h.colors, farArmX, 0.1, false);
  drawTorso(ctx, gear.body, look, h.colors);
  if (gear.off_hand !== undefined && offIsShield) drawOffhandSide(ctx, gear.off_hand, h.colors(gear.off_hand));
  if (gear.off_hand?.kind === "tome") drawOffhandSide(ctx, gear.off_hand, h.colors(gear.off_hand));
  else if (gear.off_hand !== undefined && offHeld) h.weapon(gear.off_hand, farArmX + 5);
  drawHeadSide(ctx, look);
  drawHairSide(ctx, look, gear.head);
  drawHeadgearSide(ctx, gear.head, gear.head !== undefined ? h.colors(gear.head) : undefined);
  const hand = drawArm(ctx, gear.body, look, gear.hands, h.colors, nearArmX, ARM_SWING, true);
  h.weapon(gear.main_hand, hand.x);
}
