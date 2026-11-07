// Q 版召喚物（非人形 13 種）的畫法（QK-3；照 docs/art/sample/qSummon.js 改寫，圖 docs/art/shots/misc/q-summons-forms.png）。
// 畫法層同 qSummonCore（平塗、細縫線、整隻剪影外框 1.3、方眼、Q 大頭）。座標：腳底 (0,0)、往上 −y，身高和 Q 版主角同一套。
// 朝向：漂浮靈、構造體、圖騰、植物畫正面，只差眼睛位置（背面不畫眼睛）；野獸畫側面，朝西鏡像、朝南用朝東、朝北用朝西。
// 人形 4 種用 Q 版紙娃娃（summonArt.ts）；不發外光（外光只代表頭目）。確定性：不用亂數。
import type { Ctx } from "./artDraw";
import { beye, dark, dot, ellPts, groundShadow, ink, limb, OUT, qeye, scaleAt, smooth, stroke, TAU, type Face, type Pt } from "./qSummonCore";

/** 遊戲的關鍵字 id → 樣張的元素名（顏色表 KW、漂浮靈配色 SPIRIT 的鍵）。 */
const ELEM: Readonly<Record<string, string>> = {
  ignite: "ignite",
  wet: "wet",
  charged: "shock",
  frozen: "freeze",
  prone: "prone",
  collision: "impact",
  marked: "mark",
  high_ground: "high",
  concealed: "hidden",
  summon: "summon",
};
/** 元素色（樣張 KW）。 */
const KW: Readonly<Record<string, string>> = {
  ignite: "#ff6a1a",
  wet: "#4aa8ff",
  shock: "#fff36b",
  freeze: "#8fe3ff",
  prone: "#e0b080",
  impact: "#ff9a4a",
  mark: "#d06aff",
  high: "#ffe9a8",
  hidden: "#a0a0c8",
  summon: "#7dffb0",
};
const kw = (el: string | undefined, def: string): string => KW[ELEM[el ?? ""] ?? ""] ?? KW[def]!;

/** 畫一隻需要的外觀（summonArt 的 ResolvedLook 子集）。 */
export interface QSummonLook {
  body: string;
  variant: string;
  element: string | undefined;
  trait: string | undefined;
}

// ============================== 漂浮靈（火、冰、雷、水） ==============================
interface Pal {
  c: string;
  l: string;
  d: string;
}
const SPIRIT: Readonly<Record<string, Pal>> = {
  ignite: { c: "#ff7a2a", l: "#ffd04a", d: "#c84a14" },
  freeze: { c: "#8fd8f5", l: "#e8fbff", d: "#4a9ac0" },
  shock: { c: "#ffd84a", l: "#fff7c0", d: "#b88a10" },
  wet: { c: "#4a9aff", l: "#d8f0ff", d: "#2a64c0" },
};
const eyesAt = (f: Face, y: number, gap: number, fn: (x: number, y: number) => void): void => {
  if (f.ex === null) return;
  fn(f.ex - gap, y);
  fn(f.ex + gap, y);
};

/** 水滴形身體（整隻就是大頭）＋元素決定頭頂與身邊的形狀；底下沒有腳。 */
function spirit(ctx: Ctx, s: QSummonLook, f: Face): void {
  const el = SPIRIT[ELEM[s.element ?? ""] ?? ""] ? ELEM[s.element ?? ""]! : "ignite";
  const P = SPIRIT[el]!;
  ctx.save();
  ctx.translate(0, -7);
  if (el === "freeze")
    for (const [x, y, h] of [[-13, -22, 3.4], [12.5, -16, 2.8]] as const) ink(ctx, [[x, y - h], [x + h * 0.55, y], [x, y + h], [x - h * 0.55, y]], P.l, { sharp: true });
  if (el === "wet") for (const [x, y, r] of [[-12, -19, 1.6], [11.6, -25, 1.3]] as const) ink(ctx, [[x, y - r * 2.2], [x + r, y], [x, y + r], [x - r, y]], P.l);
  if (el === "shock")
    for (const [x, y, sg] of [[-13, -24, 1], [12.5, -18, -1]] as const)
      stroke(ctx, [[x, y - 3], [x + sg * 1.6, y - 0.6], [x - sg * 0.6, y + 0.4], [x + sg * 1.2, y + 3]], 1.1, P.d);
  // 尾巴（下緣收成一個尖）
  ink(ctx, el === "ignite" ? [[-6, -13], [-3, -6], [-1, -9], [1, -3], [3, -9], [6, -13]] : [[-6, -13], [0, -3], [6, -13]], P.c, { sharp: el === "freeze" || el === "shock" });
  // 頭頂：火焰三舌／冰晶三根／雷角兩根／水滴尖
  if (el === "ignite") ink(ctx, [[-8, -28], [-6.6, -38], [-3.4, -32], [0, -44], [3.4, -32], [6.6, -39], [8, -28]], P.c);
  else if (el === "freeze")
    for (const [x, h, a] of [[-5, 7, -0.35], [0, 10, 0], [5, 7, 0.35]] as const) {
      ctx.save();
      ctx.translate(x, -31);
      ctx.rotate(a);
      ink(ctx, [[-2.2, 2], [0, -h], [2.2, 2]], P.l, { sharp: true });
      ctx.restore();
    }
  else if (el === "shock")
    for (const sg of [-1, 1]) ink(ctx, [[sg * 3, -31], [sg * 6.6, -38], [sg * 5, -38.4], [sg * 8.6, -44], [sg * 8.4, -37], [sg * 9.6, -37.4], [sg * 7.4, -30]], P.c, { sharp: true });
  else ink(ctx, [[-7, -27], [0, -40], [7, -27]], P.c);
  const body: Pt[] = [[0, -36], [7.6, -32], [10.6, -23], [8.6, -14.4], [0, -11.4], [-8.6, -14.4], [-10.6, -23], [-7.6, -32]];
  ink(ctx, body, P.c);
  ink(ctx, ellPts(f.ex === null ? 0 : f.ex * 0.5, -17.6, 5.4, 3.6, 14), P.l, { line: false }); // 肚子亮色
  if (el === "shock" && f.ex !== null) stroke(ctx, [[-6, -29], [-3.6, -26], [-5.4, -25], [-2.6, -21.6]], 0.8, P.d);
  if (el === "wet") ink(ctx, ellPts(-4.4, -29, 1.4, 2.4, 10), "#ffffff", { line: false });
  for (const sg of [-1, 1]) ink(ctx, ellPts(sg * 10.8, -19.6, 2.2, 2.6, 10), P.c); // 小手
  eyesAt(f, -24, 3.3, (x, y) => qeye(ctx, x, y, "#1d1a22", 1));
  if (f.ex !== null) {
    ctx.fillStyle = "rgba(220,90,90,0.35)";
    ctx.fillRect(f.ex - 6.4, -21, 2, 1.1);
    ctx.fillRect(f.ex + 4.4, -21, 2, 1.1);
  }
  ctx.restore();
}

// ============================== 構造體（石像、爆裂傀儡、土牆） ==============================
const STONE = "#8f969a";
const STONE_D = "#6e7478";
function golem(ctx: Ctx, s: QSummonLook, f: Face): void {
  const acc = kw(s.element, "impact");
  const B = f.ex === null;
  for (const sg of [-1, 1]) ink(ctx, [[sg * 1.2, -13], [sg * 8, -13], [sg * 8.4, 0], [sg * 0.8, 0]], STONE_D, { sharp: true }); // 腿
  for (const sg of [-1, 1]) {
    ink(ctx, [[sg * 10.6, -30], [sg * 17.6, -28.4], [sg * 18.4, -14], [sg * 11.6, -14.6]], STONE_D, { sharp: true }); // 手臂
    ink(ctx, ellPts(sg * 15.2, -11.6, 4.4, 3.8, 12), STONE); // 拳頭
  }
  ink(ctx, [[-12, -31], [12, -31], [11, -13], [-11, -13]], STONE, { sharp: true }); // 軀幹
  if (!B) stroke(ctx, [[-5, -26], [-2, -22.4], [-4.4, -19.6], [-1, -16]], 1.1, acc); // 胸口發光刻紋
  else stroke(ctx, [[0, -30], [0, -14]], 0.6, STONE_D);
  for (const sg of [-1, 1]) dot(ctx, sg * 12.6, -31, 2.4, 1.3, "#6a9a4a"); // 肩上青苔
  ink(ctx, [[-8.4, -42], [8.4, -42], [9, -30.6], [-9, -30.6]], STONE, { sharp: true }); // 頭
  if (!B)
    eyesAt(f, -36.4, 3.4, (x, y) => {
      ctx.fillStyle = acc;
      ctx.fillRect(x - 1.6, y - 0.9, 3.2, 1.8);
    });
}
function bomb(ctx: Ctx, f: Face): void {
  const acc = SPIRIT.ignite!;
  for (const sg of [-1, 1]) ink(ctx, [[sg * 1.5, -5], [sg * 6, -5], [sg * 6.4, 0], [sg * 1.1, 0]], "#3e3a44", { sharp: true });
  for (const sg of [-1, 1]) ink(ctx, ellPts(sg * 10.6, -11.4, 2.2, 2.6, 10), "#4a4650");
  ink(ctx, ellPts(0, -13, 9.6, 9, 20), "#55505c");
  ctx.save();
  smooth(ctx, ellPts(0, -13, 9.6, 9, 20));
  ctx.clip();
  const c1: Pt[] = [[-9, -9], [-5, -11.4], [-6, -6.6], [-1, -8]];
  const c2: Pt[] = [[9, -17], [5.4, -15], [6, -19.6]];
  stroke(ctx, c1, 1.5, acc.c);
  stroke(ctx, c1, 0.6, acc.l); // 發光裂紋
  stroke(ctx, c2, 1.4, acc.c);
  stroke(ctx, c2, 0.55, acc.l);
  ctx.restore();
  ink(ctx, [[-2.4, -21], [2.4, -21], [2.2, -23.4], [-2.2, -23.4]], "#8a8478", { sharp: true }); // 引信座
  stroke(ctx, [[0, -23.2], [1.6, -26.6], [4.4, -27.4]], 1.4, "#a8845a");
  ink(ctx, [[4.4, -31.4], [5.6, -28.6], [8.4, -27.4], [5.6, -26.2], [4.4, -23.4], [3.2, -26.2], [0.4, -27.4], [3.2, -28.6]], "#ffd04a", { sharp: true, line: false }); // 火花
  dot(ctx, 4.4, -27.4, 1, 1, "#ffffff");
  eyesAt(f, -14, 3, (x, y) => qeye(ctx, x, y, acc.l, 0.9));
}
function wall(ctx: Ctx): void {
  const c = "#b08a5a";
  const d = "#7a5a34";
  const top = "#c8a070";
  ink(ctx, [[-20, 0], [-20, -22], [20, -22], [20, 0]], c, { sharp: true }); // 牆身
  ink(ctx, [[-21, -22], [-21, -25], [-12, -25.6], [-4, -24.8], [5, -25.8], [13, -25], [21, -25.4], [21, -22]], top, { sharp: true }); // 牆頂
  for (const [i, y] of [-15, -8].entries()) {
    stroke(ctx, [[-19.6, y], [19.6, y]], 0.7, d);
    for (const x of i ? [-13, -1, 11] : [-7, 5, 16]) stroke(ctx, [[x, y], [x, y + 7]], 0.7, d);
  }
  for (const x of [-12, 1, 12]) stroke(ctx, [[x, -22], [x, -15]], 0.7, d);
  for (const x of [-15, 3, 16]) ink(ctx, [[x - 2.4, -24.6], [x - 1, -28], [x, -25.4], [x + 1.4, -28.4], [x + 2.4, -24.8]], "#6a9a4a", { sharp: true, line: false }); // 牆頭的草
  stroke(ctx, [[6, -21.4], [8, -18], [6.6, -15.4]], 0.7, d); // 一道裂縫
}

// ============================== 野獸（戰狼、鷹隼）：側面，Q 大頭 ==============================
function wolf(ctx: Ctx, s: QSummonLook): void {
  const P = { base: "#7a7a82", d: "#5e5e66", l: "#b8b8c0" };
  const acc = kw(s.element, "prone");
  for (const x of [-12, 6]) ink(ctx, [[x, -12], [x + 4, -12], [x + 4.4, 0], [x - 0.4, 0]], P.d);
  ink(ctx, [[-14, -20], [-22, -25], [-26, -21], [-20, -17], [-13, -15]], P.base);
  ink(ctx, [[-16, -12], [-17, -20], [-10, -25], [4, -25], [12, -22], [13, -12], [0, -10]], P.base);
  ink(ctx, ellPts(-1, -13.4, 9, 2.4, 14), P.l, { line: false }); // 肚子亮色
  for (const x of [-9, 8]) ink(ctx, [[x, -13], [x + 4, -13], [x + 4.6, 0], [x - 0.4, 0]], P.base);
  scaleAt(ctx, 12, -22, 1.3, () => {
    ink(ctx, [[12, -29], [13, -36], [16.4, -30]], P.d, { sharp: true });
    ink(ctx, [[8, -22], [11, -30], [17, -31], [22, -28], [28, -26], [28, -23], [21, -21], [14, -18]], P.base);
    dot(ctx, 28, -25, 0.9, 0.8, OUT);
    beye(ctx, 19, -27.4, "#ffd23a");
    ink(ctx, [[23.2, -22.2], [24, -20.2], [24.8, -22.2]], "#f4ecd8", { sharp: true, line: false });
  });
  // 項圈（元素色）：順著脖子繞過去的帶子，後半圈暗一階，前面掛一個金環
  limb(ctx, [[8.2, -26.8], [9.6, -22.4], [11.2, -18]], 1.9, dark(acc, 0.25));
  limb(ctx, [[9.6, -27.4], [11.4, -22.6], [12.8, -18.4]], 1.9, acc);
  ink(ctx, ellPts(13.4, -16.8, 1.2, 1.2, 10), "#e8bb48");
}
function hawk(ctx: Ctx, s: QSummonLook): void {
  const c = "#8a6a40";
  const d = "#5e4628";
  const acc = kw(s.element, "mark");
  ctx.save();
  ctx.translate(0, -10);
  ink(ctx, [[-2, -4], [-12, -14], [-20, -15], [-16, -10], [-21, -9], [-13, -4], [-4, 2]], d, { sharp: true }); // 遠側翅
  ink(ctx, [[-8, 2], [-17, 6], [-15, 1.4], [-18.6, 2.4], [-9, -1]], d, { sharp: true, line: false });
  ink(ctx, ellPts(0, 0, 8.6, 5.4, 16), c);
  ink(ctx, ellPts(1.4, 1.8, 5.6, 2.6, 12), "#f0e6d0", { line: false });
  ink(ctx, [[1, -3], [9, -15], [18, -17], [14, -11], [20, -10], [12, -4], [3, 2]], c, { sharp: true }); // 近側翅
  ink(ctx, [[13, -12.6], [18, -17], [20, -10], [15.6, -10.6]], acc, { sharp: true }); // 翼尖：標記色
  scaleAt(ctx, 7, -1, 1.25, () => {
    ink(ctx, ellPts(9, -4, 4.2, 4.2, 12), c);
    ink(ctx, [[12.4, -5.2], [16.6, -3.2], [12.4, -1.2]], "#e8bb48", { sharp: true, line: false });
    beye(ctx, 10.6, -5, "#ffd23a", 0.8);
    stroke(ctx, [[8.4, -7.6], [12, -6.8]], 0.7, acc);
  });
  for (const x of [-2, 2.6]) stroke(ctx, [[x, 4.6], [x, 7.6]], 1.2, "#e8bb48");
  ctx.restore();
}

// ============================== 植物（藤蔓）：貼地 ==============================
function vine(ctx: Ctx): void {
  const g = "#4f8a3a";
  const l = "#7ab84a";
  const stems: Pt[][] = [
    [[0, -2], [-7, -3], [-13, -1], [-16, -5], [-13, -8]],
    [[0, -2], [6, -5], [12, -3], [15, -7], [12.4, -10]],
    [[0, -2], [-2, -8], [1, -12], [4, -10]],
  ];
  for (const pts of stems) limb(ctx, pts, 1.6, g);
  for (const [x, y, a] of [[-9, -4.4, -0.6], [8.6, -6, 0.5], [-1.6, -10, -0.2], [13.6, -2.2, 1.2], [-14, -2.4, -1.4]] as const) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(a);
    ink(ctx, [[0, 0], [-1.8, -2.4], [0, -4.6], [1.8, -2.4]], l);
    ctx.restore();
  }
  for (const [x, y] of [[-4, -3.4], [5, -4.4]] as const) ink(ctx, [[x - 0.8, y], [x, y - 2], [x + 0.8, y]], "#e8e0c8", { sharp: true, line: false }); // 刺
}

// ============================== 圖騰（戰意、吸引、高台） ==============================
function totem(ctx: Ctx, s: QSummonLook, f: Face): void {
  const wood = "#8a5a32";
  const wl = "#a8763e";
  const B = f.ex === null;
  for (const [x, r] of [[-6, 3], [5.6, 2.6], [0, 3.4]] as const) ink(ctx, ellPts(x, -1.4, r, r * 0.6, 10), "#8a847e"); // 底座石頭
  ink(ctx, [[-3.2, -1], [-3.2, -34], [3.2, -34], [3.2, -1]], wood, { sharp: true });
  ink(ctx, [[-7, -28], [7, -28], [6.4, -13], [-6.4, -13]], wl, { sharp: true }); // 雕臉的木塊
  if (!B) {
    eyesAt(f, -23.6, 2.6, (x, y) => {
      ctx.fillStyle = "#2b1e16";
      ctx.fillRect(x - 1.2, y - 1.4, 2.4, 2.8);
    });
    ctx.fillStyle = "#2b1e16";
    ctx.fillRect((f.ex ?? 0) - 2.6, -17.4, 5.2, 1.4);
  } else stroke(ctx, [[0, -27], [0, -14]], 0.6, wood);
  if (s.variant === "war") {
    stroke(ctx, [[0, -34], [0, -46]], 1.6, wood);
    ink(ctx, [[0.6, -46], [15, -42.6], [11, -40.4], [15, -38], [0.6, -36.4]], "#d23c3c", { sharp: true });
  } else if (s.variant === "pull") {
    ink(ctx, ellPts(0, -40, 7.4, 7.4, 20), "#a86ad8");
    stroke(ctx, [[0, -40], [2.6, -41], [2.4, -43.4], [-1, -44], [-4, -41.6], [-3.4, -37.4], [1, -35.6], [5, -37.6]], 0.9, "#e8d0ff");
  } else if (s.variant === "plateau") {
    ink(ctx, [[-10.6, -38], [10.6, -38], [11.4, -33.4], [-11.4, -33.4]], "#b8b0a0", { sharp: true });
    if (!B) ink(ctx, [[-3, -34.6], [0, -37.2], [3, -34.6], [1.6, -34.6], [0, -35.8], [-1.6, -34.6]], KW.high!, { sharp: true, line: false });
    stroke(ctx, [[-2, -33.6], [-2, -32]], 1.2, wood);
  }
}

// ============================== 組合 ==============================
/** 野獸畫側面：朝西、朝北鏡像（朝南用朝東、朝北用朝西）。 */
export const qSummonMirrored = (s: QSummonLook, facing: string): boolean => s.body === "beast" && (facing === "west" || facing === "north");
const FACE: Readonly<Record<string, Face>> = { south: { ex: 0 }, east: { ex: 2.4 }, west: { ex: -2.4 }, north: { ex: null } };
export const faceOf = (facing: string): Face => FACE[facing] ?? FACE.south!;

/** 身體（未套大小、不含地面）：腳底為原點；野獸朝西／北已鏡像、鷹隼已抬高 22。人形什麼都不畫。 */
export function drawQSummonBody(ctx: Ctx, s: QSummonLook, facing: string): void {
  if (s.body === "humanoid") return;
  const f = faceOf(facing);
  ctx.save();
  ctx.scale(qSummonMirrored(s, facing) ? -1 : 1, 1);
  if (s.trait === "flying") ctx.translate(0, -22);
  if (s.body === "spirit") spirit(ctx, s, f);
  else if (s.body === "construct") {
    if (s.variant === "bomb") bomb(ctx, f);
    else if (s.variant === "wall") wall(ctx);
    else golem(ctx, s, f);
  } else if (s.body === "beast") {
    if (s.variant === "bird") hawk(ctx, s);
    else wolf(ctx, s);
  } else if (s.body === "plant") vine(ctx);
  else totem(ctx, s, f);
  ctx.restore();
}

/** 地面（未套大小）：水精的一攤水、地面影子（漂浮靈、鷹隼較淡較小；藤蔓沒有）。 */
export function drawQSummonGround(ctx: Ctx, s: QSummonLook): void {
  if (s.body === "humanoid") return;
  const hover = s.body === "spirit";
  const flying = s.trait === "flying";
  if (s.trait === "puddle") {
    ctx.save();
    ctx.globalAlpha = 0.45;
    ctx.fillStyle = "#4aa8ff";
    ctx.beginPath();
    ctx.ellipse(0, 0, 14, 4.2, 0, 0, TAU);
    ctx.fill();
    ctx.restore();
  }
  if (s.body !== "plant") groundShadow(ctx, hover ? 7 : flying ? 8 : s.variant === "wall" ? 20 : 10, 0.2, hover || flying ? 0.22 : 0.3);
}

/** 戰意圖騰腳下的虛線光環（召喚物淡綠，平塗不發光；樣張半徑 17，大小照 max(1, size×0.9)）。
 *  rx：戰場的陣營底圈比樣張的環大（約 20 單位），光環要在底圈外面才看得出來，由呼叫端給（預設樣張的 17）。 */
export function drawQSummonAura(ctx: Ctx, rx = 17): void {
  ctx.save();
  ctx.strokeStyle = "#7dffb0";
  ctx.globalAlpha = 0.9;
  ctx.lineWidth = 1.1;
  ctx.setLineDash([3, 2.4]);
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
}

/**
 * 陣營環的大小（樣張審查第 3 輪：比身體寬）：[半徑（單位）, 中心往前移]；已含大小。
 * 石像 22、戰狼 25（往頭的方向移 3），其他 13×max(1, size×0.9)。
 */
export function qSummonRing(s: QSummonLook, size: number): { rx: number; dx: number } {
  const R: Readonly<Record<string, readonly [number, number]>> = { golem: [22, 0], wolf: [25, 3] };
  const r = s.body === "construct" || s.body === "beast" ? R[s.variant] : undefined;
  if (r) return { rx: r[0] * Math.max(1, size), dx: r[1] * size };
  return { rx: 13 * Math.max(1, size * 0.9), dx: 0 };
}
