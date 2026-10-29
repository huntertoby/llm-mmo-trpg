// C 手繪墨線畫風的其餘防具（Phase C-2a）：身體 mail／coat、頭 wide_hat／cap／bandana／crown／greathelm／horned_helm、
// 手 gloves／gauntlets／bracers、腳 shoes／iron_boots。沿用現行輪廓，改用 ink()／stroke()，顏色照 itemColors（colors）。
// 不認得的 kind／form／材質退回預設，不出錯。座標同 inkDoll.ts（頭心 (0,-42)）。
import type { Ctx } from "./artDraw";
import type { GearItem } from "./appearance";
import { darken, lighten } from "./color";
import { drawHelmet, metalOf, type ColorFn } from "./inkGear";
import { dot, ellPts, ink, MAT, stroke, type Pt, type View } from "./inkStyle";

const GOLD = MAT.gold;
const FUR = "#e9e3cf";
const HORN = "#efe6cc";

const shiftX = (pts: readonly Pt[], dx: number): Pt[] => pts.map(([x, y]): Pt => [x + dx, y]);

// ============================== 身體 ==============================
const COAT: Record<View, Pt[]> = {
  front: [[-7, -33], [7, -33], [6, -23], [9.4, -6], [1, -5], [0, -9.5], [-1, -5], [-9.4, -6], [-6, -23]],
  back: [[-7, -33], [7, -33], [6, -23], [9.4, -6], [0, -4.6], [-9.4, -6], [-6, -23]],
  side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [7, -6], [-1, -5], [-7, -6], [-4.2, -22]],
};
const MAIL: Record<View, Pt[]> = {
  front: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
  back: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
  side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [5.2, -14], [-1, -12.5], [-5.6, -14], [-4.2, -22]],
};

function drawCoat(ctx: Ctx, it: GearItem, view: View, c: string, d: string): void {
  ink(ctx, `coat-${view}`, COAT[view], c);
  if (view === "front") {
    ink(ctx, "coat-lapel", [[-4.4, -33], [0, -25.6], [4.4, -33], [2, -33.4], [0, -30.6], [-2, -33.4]], d, { shade: false, w: 0.6 });
    stroke(ctx, "coat-open", [[0, -25], [0, -9.5]], 0.5);
    for (const y of [-23, -19, -15]) dot(ctx, 1.8, y, 0.7, 0.7, GOLD);
  } else if (view === "back") {
    stroke(ctx, "coat-split", [[0, -14], [0, -4.8]], 0.5);
  } else {
    stroke(ctx, "coat-split-s", [[-1, -12], [-1, -5.2]], 0.5);
  }
  if (it.form !== "cape") return;
  if (view === "side") ink(ctx, "coat-cape-s", ellPts(-0.6, -30.4, 4.6, 3, 12), d, { w: 0.7 });
  else ink(ctx, `coat-cape-${view}`, [[-9.2, -33.4], [9.2, -33.4], [10.4, -27], [0, -25.6], [-10.4, -27]], d, { w: 0.7 });
}

function drawMail(ctx: Ctx, it: GearItem, view: View, c: string): void {
  ink(ctx, `torso-${view}`, MAIL[view], c);
  const side = view === "side";
  const x0 = side ? -3 : -4.6;
  const x1 = side ? 3 : 4.6;
  const scale = it.form === "scale";
  let row = 0;
  for (let y = -30.4; y < -14; y += 2.6, row++) {
    for (let x = x0 + (row % 2 === 0 ? 0 : 1.3); x <= x1; x += 2.6) {
      const k = `mail-${view}-${row}-${Math.round(x * 10)}`;
      if (scale) stroke(ctx, k, [[x - 1.1, y], [x, y + 1.1], [x + 1.1, y]], 0.3);
      else stroke(ctx, k, [[x - 0.4, y], [x + 0.4, y + 0.3]], 0.35);
    }
  }
}

/** 身體：mail、coat 的 C 版（含軀幹）。回傳 false ＝ 不是這一層的 kind。 */
export function drawInkBodyArmor(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): boolean {
  const [c, d] = colors(it);
  if (it.kind === "mail") drawMail(ctx, it, view, c);
  else if (it.kind === "coat") drawCoat(ctx, it, view, c, d);
  else return false;
  return true;
}

// ============================== 頭 ==============================
const baseColor = (it: GearItem, colors: ColorFn): string => it.color ?? colors(it)[0];

function drawWideHat(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): void {
  const c = baseColor(it, colors);
  const trim = it.trim ?? darken(c, 0.4);
  const dx = view === "side" ? -1 : 0;
  ink(ctx, `wide-brim-${view}`, [[-15.4, -46.4], [-8, -49.8], [8, -49.8], [15.4, -46.4], [8, -44.4], [-8, -44.4]], darken(c, 0.12));
  ink(ctx, `wide-crown-${view}`, shiftX([[-7, -47.6], [-6.6, -55], [-2, -58.4], [2, -58.4], [6.6, -55], [7, -47.6]], dx), c);
  stroke(ctx, `wide-band-${view}`, [[-7 + dx, -49.4], [7 + dx, -49.4]], 1.4, trim);
}

function drawCap(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): void {
  const [c, d] = colors(it);
  const fur = it.form === "fur";
  const dx = view === "side" ? -0.6 : 0;
  ink(ctx, `cap-${view}`, shiftX([[-9.6, -43], [-9.4, -50], [-4.6, -54.4], [4.6, -54.4], [9.4, -50], [9.6, -43]], dx), c);
  const bot = fur ? -41.8 : -43.4;
  ink(ctx, `cap-band-${view}`, shiftX([[-10.2, -46.8], [10.2, -46.8], [10.4, bot], [-10.4, bot]], dx), fur ? FUR : d, { w: 0.7 });
}

function drawCirclet(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): void {
  const c = baseColor(it, colors);
  const dx = view === "side" ? -0.6 : 0;
  if (it.kind === "crown") {
    ink(ctx, `crown-${view}`, shiftX([[-7, -49.4], [-6.6, -56], [-3.4, -52.6], [0, -57.4], [3.4, -52.6], [6.6, -56], [7, -49.4], [0, -48]], dx), c, { w: 0.8 });
    if (view === "front") dot(ctx, 0, -51.4, 1.1, 1.1, "#d23c3c");
    return;
  }
  ink(ctx, `bandana-${view}`, shiftX([[-9.4, -44.4], [-9.1, -49.6], [-4.6, -53.2], [4.6, -53.2], [9.1, -49.6], [9.4, -44.4], [0, -46.4]], dx), c);
  const tail = darken(c, 0.25);
  if (view === "back") ink(ctx, "bandana-knot", [[-1.8, -47], [1.8, -47], [3.4, -42], [0, -43.6], [-3.4, -42]], tail, { w: 0.6 });
  else ink(ctx, `bandana-tail-${view}`, shiftX([[8.4, -47], [13, -44.4], [11.8, -40.4], [9, -44]], dx), tail, { w: 0.6 });
}

const GREAT: Record<View, Pt[]> = {
  front: [[-10.4, -34], [-10.6, -49], [-5, -54.8], [5, -54.8], [10.6, -49], [10.4, -34], [5, -32.4], [-5, -32.4]],
  back: [[-10.4, -34], [-10.6, -49], [-5, -54.8], [5, -54.8], [10.6, -49], [10.4, -34], [5, -32.4], [-5, -32.4]],
  side: [[-10, -35], [-10.4, -48], [-5, -54.6], [4, -54.2], [9.8, -49], [10.6, -39], [7.6, -33.6], [-6, -33.4]],
};

function drawGreathelm(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): void {
  ink(ctx, `great-${view}`, GREAT[view], metalOf(it, colors));
  if (view === "front") {
    ink(ctx, "great-slit", [[-6.8, -44.6], [6.8, -44.6], [6.8, -42.6], [-6.8, -42.6]], "#1d1a22", { shade: false, w: 0.5 });
    stroke(ctx, "great-bar", [[0, -42], [0, -34.4]], 0.7);
  } else if (view === "side") {
    ink(ctx, "great-slit-s", [[1.4, -44.6], [10, -44.6], [10, -42.6], [1.4, -42.6]], "#1d1a22", { shade: false, w: 0.5 });
    stroke(ctx, "great-bar-s", [[8, -42], [8, -34.6]], 0.7);
  } else {
    stroke(ctx, "great-seam", [[0, -54], [0, -33.4]], 0.5);
  }
}

function drawHorned(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): void {
  if (view === "side") {
    // 兩支角都往後彎：遠側那支先畫、暗 30%，近側那支在頭盔之後
    ink(ctx, "horn-far", [[-1, -50.4], [-7, -53.4], [-9, -61], [-4.2, -57.4], [1.6, -52.8]], darken(HORN, 0.3), { w: 0.7 });
    drawHelmet(ctx, { ...it, kind: "helmet" }, view, colors);
    ink(ctx, "horn-side", [[-3, -50], [-9, -53], [-10.6, -61], [-6, -57], [0, -52.6]], HORN, { w: 0.7 });
    return;
  }
  drawHelmet(ctx, { ...it, kind: "helmet" }, view, colors);
  for (const s of [-1, 1]) ink(ctx, `horn-${view}-${s}`, [[s * 9, -48], [s * 15.6, -50.4], [s * 15.4, -59], [s * 11.4, -53.6], [s * 7, -52]], HORN, { w: 0.7 });
}

/** 其餘頭部裝備（dollGear 已把 helmet 的 horned／greathelm 形制轉成 horned_helm／greathelm kind）。 */
export function drawInkHeadgearMore(ctx: Ctx, it: GearItem, view: View, colors: ColorFn): boolean {
  switch (it.kind) {
    case "wide_hat":
      drawWideHat(ctx, it, view, colors);
      return true;
    case "cap":
      drawCap(ctx, it, view, colors);
      return true;
    case "bandana":
    case "crown":
      drawCirclet(ctx, it, view, colors);
      return true;
    case "greathelm":
      drawGreathelm(ctx, it, view, colors);
      return true;
    case "horned_helm":
      drawHorned(ctx, it, view, colors);
      return true;
    default:
      return false;
  }
}

// ============================== 手 ==============================
/**
 * 手與前臂護具。(x, y) ＝ 手心，`ang` ＝ 前臂傾角（弧度；袖口沿前臂往肩膀方向畫）。
 * 沒有手部裝備、`bracers`、露指手套露膚色；其他 kind（含不認得的）用裝備色。
 */
export function drawInkHand(ctx: Ctx, hands: GearItem | undefined, key: string, x: number, y: number, ang: number, skin: string, colors: ColorFn): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(ang);
  let handC = skin;
  let r = 1.8;
  if (hands !== undefined) {
    const [c, d] = colors(hands);
    if (hands.kind === "gauntlets") {
      const m = metalOf(hands, colors);
      ink(ctx, `${key}-cuff`, [[-2.7, -5.8], [2.7, -5.8], [2.4, -1], [-2.4, -1]], m, { w: 0.7 });
      if (hands.form === "mail") for (const yy of [-4.6, -3, -1.8]) stroke(ctx, `${key}-ml${yy}`, [[-1.6, yy], [1.6, yy]], 0.3);
      else stroke(ctx, `${key}-rid`, [[-2.4, -3.4], [2.4, -3.4]], 0.5);
      handC = m;
      r = 2.2;
    } else if (hands.kind === "bracers") {
      if (hands.form === "ring") {
        ink(ctx, `${key}-cuff`, [[-2.4, -4.2], [2.4, -4.2], [2.3, -2.4], [-2.3, -2.4]], metalOf(hands, colors), { shade: false, w: 0.6 });
      } else {
        ink(ctx, `${key}-cuff`, [[-2.5, -5.4], [2.5, -5.4], [2.3, -1.4], [-2.3, -1.4]], c, { shade: false, w: 0.7 });
        stroke(ctx, `${key}-strap`, [[-2.2, -3.4], [2.2, -3.4]], 0.4);
      }
    } else if (hands.form === "fingerless") {
      ink(ctx, `${key}-band`, [[-2.2, -0.3], [2.2, -0.3], [2.2, 1.5], [-2.2, 1.5]], c, { shade: false, w: 0.5 });
    } else {
      if (hands.form === "long") ink(ctx, `${key}-cuff`, [[-2.6, -6.6], [2.6, -6.6], [2.3, -1], [-2.3, -1]], d, { shade: false, w: 0.7 });
      handC = c;
      r = 2.1;
    }
  }
  ink(ctx, key, ellPts(0, 0, r, r, 10), handC, { shade: false, w: 0.6 });
  ctx.restore();
}

// ============================== 腳 ==============================
/** 靴筒上緣：shoes 低鞋、iron_boots 高；其餘由 inkDoll 決定。 */
export function footTop(feet: GearItem | undefined): number | undefined {
  if (feet?.kind === "shoes") return -3.4;
  if (feet?.kind === "iron_boots") return -9;
  return undefined;
}

/** 鞋靴的額外細節（綁腿、鐵靴鞋尖與護片），畫在腿與靴之後。 */
export function drawFootDetail(ctx: Ctx, feet: GearItem | undefined, view: View, colors: ColorFn, heavy = false): void {
  if (feet === undefined) return;
  const sides = view === "side" ? [1] : [-1, 1];
  if (feet.kind === "shoes" && feet.form === "wrapped") {
    const d = colors(feet)[1];
    for (const sx of sides) {
      for (const y of [-5.4, -7.2]) {
        const [a, b] = view === "side" ? [-0.4, 3.8] : sx > 0 ? [0.8, 4.6] : [-4.6, -0.8];
        stroke(ctx, `wrap-${view}-${sx}-${y}`, [[a, y], [b, y + 0.9]], 0.6, d);
      }
    }
  } else if (feet.kind === "greaves" && feet.form === "knee" && view !== "back") {
    // 護膝（美術 PM C-2a 驗收）：膝蓋 y≈-9 的鋼色小橢圓 2.4×1.8；正面兩腿、側面近側腿，背面不畫
    for (const sx of sides) {
      const cx = view === "side" ? 1.6 : sx * 2.7;
      ink(ctx, `knee-${view}-${sx}`, ellPts(cx, -9, 2.4, 1.8, 10), heavy ? lighten(metalOf(feet, colors), 0.35) : metalOf(feet, colors), { shade: false, w: 0.6 });
    }
  } else if (feet.kind === "iron_boots") {
    for (const sx of sides) {
      if (view === "side") stroke(ctx, "ib-cap-s", [[2, -3.2], [6.4, -1.6]], 0.5);
      else stroke(ctx, `ib-cap-${sx}`, [[sx * 1, -2.6], [sx * 4.8, -2.6]], 0.5);
    }
  }
}
