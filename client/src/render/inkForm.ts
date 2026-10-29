// 形態外觀（C 畫風；Phase 3J-5）。移植自美術 PM 樣張 docs/art/sample/storyDoll.js 的 `FORMS`、`aura`、`drawForm`，
// 規則見 docs/art/形態外觀.md 的「定稿方向」與 docs/art/C畫風移植需求.md 第 5 節：10 種全部另畫、帶主角主色、
// 比同類召喚物大一號（`size`）、元素化身與龍吃元素色；腳下形態光環是元素色虛線橢圓＋18% 同色填色（無元素 #9a86ff）。
// 全部用 `ink()`／`stroke()`（確定性抖動，禁止 Math.random()）；不認得的形態 id 由呼叫端退回原角色紙娃娃＋光環。
// 座標：腳底 (0,0)、往上是 -y、朝東（+x 是前方）；西與北用左右鏡像。
import type { Facing } from "../api/types";
import { TAU, type Ctx } from "./artDraw";
import { darken, isHex, lighten, mix } from "./color";
import { dot, ellPts, ink, INK, shadow, stroke, withShadeDir, type Pt } from "./inkStyle";

/** 無元素的光環色。 */
export const FORM_AURA_NEUTRAL = "#9a86ff";
/** 找不到身體裝備顏色與披風顏色時的主角主色（陣營藍）。 */
export const FORM_HERO_FALLBACK = "#4f7fbf";
const dark = (c: string, t = 0.3): string => darken(c, t);
const light = (c: string, t = 0.3): string => lighten(c, t);

const limb = (ctx: Ctx, key: string, pts: readonly Pt[], w: number, color: string): void => {
  stroke(ctx, key, pts, w + 1.4, INK);
  stroke(ctx, key, pts, w, color);
};

type Element = "fire" | "ice" | "lightning";
/** 元素 → [身體色, 亮色]；元素色也是光環色。 */
const ELEMENT_COLORS: Readonly<Record<Element, readonly [string, string]>> = {
  fire: ["#ff7a1a", "#ffd04a"],
  ice: ["#8fe3ff", "#e8fbff"],
  lightning: ["#ffe14a", "#fff7c0"],
};
const elementOf = (el: string | null | undefined): Element | null => (el === "fire" || el === "ice" || el === "lightning" ? el : null);

/** 光環色：認得的元素用元素色，其餘（無元素、不認得的元素）用 #9a86ff。 */
export function formAuraColor(element: string | null | undefined): string {
  const el = elementOf(element);
  return el === null ? FORM_AURA_NEUTRAL : ELEMENT_COLORS[el][0];
}

interface FormArt {
  zh: string;
  /** 大小倍率（同 formArt.js）。 */
  size: number;
  /** 畫出來的最高點（腳底往上，樣張座標）；頭頂狀態列要避開。 */
  top: number;
  draw: (ctx: Ctx, hero: string, element: string | null | undefined) => void;
}

function drawBear(ctx: Ctx, h: string): void {
  const c = mix("#6a4a32", h, 0.3);
  for (const x of [-11, 6]) ink(ctx, `bear-legf-${x}`, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], dark(c, 0.25));
  ink(ctx, "bear-body", [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], c);
  for (const x of [-8, -2, 4]) stroke(ctx, `bear-stripe-${x}`, [[x, -28], [x + 2, -21]], 2, h);
  for (const x of [-6, 11]) ink(ctx, `bear-leg-${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], c);
  ink(ctx, "bear-head", [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], c);
  ink(ctx, "bear-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), c, { shade: false, w: 0.7 });
  ink(ctx, "bear-snout", ellPts(23.4, -22.2, 2.6, 2, 10), light(c, 0.3), { shade: false, w: 0.6 });
  dot(ctx, 25.2, -23, 0.9, 0.8, INK);
  dot(ctx, 18.6, -25.6, 0.8, 1.1, INK);
}

function drawWerewolf(ctx: Ctx, h: string): void {
  const c = mix("#5a5a66", h, 0.25);
  ink(ctx, "ww-legfar", [[-5, -16], [-1, -16], [-2, -6], [-6, 0], [-9.6, 0], [-5.6, -6]], dark(c, 0.25));
  ink(ctx, "ww-tail", [[-7, -18], [-16, -17], [-21, -11], [-17, -11.4], [-8, -13]], c);
  ink(ctx, "ww-body", [[-8, -18], [-7, -32], [0, -40], [8, -37], [8, -26], [4, -16], [-4, -14]], c);
  ink(ctx, "ww-chest", [[1, -36], [7, -34], [6.4, -24], [2, -22]], light(c, 0.35), { shade: false, w: 0.6 });
  for (const y of [-33, -29]) stroke(ctx, `ww-band-${y}`, [[-6, y], [-1, y - 1]], 1.6, h);
  ink(ctx, "ww-leg", [[-1, -16], [4, -16], [5, -6], [9.6, 0], [3, 0], [0, -6]], c);
  ink(ctx, "ww-ear", [[3, -45], [3.4, -53.6], [8, -46.6]], dark(c, 0.15), { w: 0.7, sharp: true });
  ink(ctx, "ww-head", [[0.6, -40], [2.6, -46.4], [8, -48.4], [12.6, -46], [20.6, -43.4], [21, -40.4], [14.6, -39], [12.4, -36.6], [6, -34.6]], c);
  ink(ctx, "ww-ear2", [[6.4, -46.6], [8.6, -54.6], [11.4, -46]], c, { w: 0.7, sharp: true });
  ink(ctx, "ww-jaw", [[12.6, -39], [19, -39.2], [14.6, -36.4], [11.6, -36.6]], light(c, 0.3), { shade: false, w: 0.5 });
  ink(ctx, "ww-fang", [[17, -39.2], [17.6, -37.4], [18.2, -39.2]], "#f4ecd8", { shade: false, w: 0.35, sharp: true });
  dot(ctx, 11.6, -43.6, 1, 0.75, "#ffd23a");
  dot(ctx, 11.8, -43.6, 0.3, 0.6, INK);
  dot(ctx, 20.4, -42.4, 0.9, 0.8, INK);
  ink(ctx, "ww-arm", [[2, -34], [6, -36], [12, -27], [12.4, -22], [9.6, -23], [8, -27]], c);
  for (const d of [0, 1.4, 2.8]) stroke(ctx, `ww-claw-${d}`, [[10 + d * 0.6, -22.2], [10.6 + d * 0.6, -19.6]], 0.6, "#f4ecd8");
}

function drawDragon(ctx: Ctx, h: string, element: string | null | undefined): void {
  const c = mix("#8a3a2a", h, 0.3);
  const e = ELEMENT_COLORS[elementOf(element) ?? "fire"][0];
  ink(ctx, "dr-wingfar", [[10, -29], [7, -40], [2, -49], [-7, -54], [-4.6, -46.4], [-6.4, -38.6], [-2, -40.4], [-1.6, -32.6], [2, -34], [2, -28]], dark(c, 0.3));
  for (const x of [-13, 4]) ink(ctx, `dr-legfar-${x}`, [[x - 2.6, -12], [x + 2.6, -12], [x + 2.4, 0], [x - 3, 0]], dark(c, 0.25));
  ink(ctx, "dr-tail", [[-14, -14], [-26, -12], [-34, -4], [-28, -4.6], [-14, -8]], c);
  ink(ctx, "dr-body", [[-17, -10], [-16, -22], [-6, -28], [8, -27], [16, -20], [14, -10], [0, -7.6]], c);
  ink(ctx, "dr-belly", [[-12, -10], [10, -10], [8, -15], [-10, -15]], light(c, 0.4), { shade: false, w: 0.5 });
  for (const x of [-10, -3, 4]) ink(ctx, `dr-spine-${x}`, [[x - 1.8, -27], [x, -31.4], [x + 1.8, -27]], h, { shade: false, w: 0.5 });
  for (const x of [-9, 9]) ink(ctx, `dr-leg-${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.4, 0]], c);
  ink(ctx, "dr-neck", [[8, -25], [14, -38], [19, -38], [16, -22]], c);
  ink(ctx, "dr-head", [[12, -38], [16, -44], [22, -43], [29, -39], [28, -35.6], [19, -34.4], [13.6, -35]], c);
  ink(ctx, "dr-horn", [[15, -42.6], [11, -50], [18, -43.6]], "#e8d8b8", { shade: false, w: 0.6 });
  dot(ctx, 20.4, -40.4, 1.1, 0.8, "#ffd23a");
  dot(ctx, 20.4, -40.4, 0.3, 0.7, INK);
  ink(ctx, "dr-wing", [[6, -27], [2, -38], [-4, -48], [-14, -52], [-11, -44], [-13, -35.6], [-8, -37.6], [-8.4, -29.6], [-4, -31.6], [-4, -27]], c, { alpha: 0.96 });
  const bones: readonly Pt[] = [[-11, -44], [-8, -37.6], [-4, -31.6]];
  bones.forEach((p, i) => stroke(ctx, `dr-wing-bone${i}`, [[2, -38], p], 0.5));
  ctx.save();
  ctx.globalAlpha = 0.85;
  ink(ctx, "dr-breath", [[29, -37.6], [36, -40.6], [34, -37.4], [38, -36], [33.6, -35.4], [36, -32.6], [29, -35.6]], e, { shade: false, w: 0.5 });
  ctx.restore();
}

function drawCat(ctx: Ctx, h: string): void {
  const c = mix("#3a3440", h, 0.35);
  const d = dark(c, 0.3);
  for (const x of [-8, 10]) ink(ctx, `cat-legfar-${x}`, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], d, { shade: false, w: 0.6 });
  ink(ctx, "cat-tail", [[-12, -12.4], [-21, -14.6], [-23.6, -22], [-21.6, -25.4], [-19.4, -22.6], [-18.6, -16.6], [-12, -9]], c);
  ink(ctx, "cat-tailtip", [[-23.4, -21.6], [-21.6, -25.4], [-19.4, -22.6], [-21.2, -20.6]], h, { shade: false, w: 0.6 });
  ink(ctx, "cat-body", ellPts(0, -11, 14, 5, 20), c);
  for (const x of [-8, -3, 2]) stroke(ctx, `cat-spot${x}`, [[x, -15], [x + 1.5, -10]], 1.6, h);
  for (const x of [-11, 7]) ink(ctx, `cat-leg${x}`, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], c, { shade: false, w: 0.6 });
  for (const x of [13, 17.4]) ink(ctx, `cat-ear${x}`, [[x - 2.2, -16.6], [x, -22.6], [x + 2.2, -16.6]], c, { w: 0.6, sharp: true });
  ink(ctx, "cat-head", ellPts(15, -14.5, 5.4, 4.6, 16), c);
  ink(ctx, "cat-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), light(c, 0.35), { shade: false, w: 0.5 });
  dot(ctx, 17.2, -15.4, 1.3, 0.9, "#ffe14d");
  dot(ctx, 17.3, -15.4, 0.3, 0.8, INK);
  dot(ctx, 21, -13.4, 0.6, 0.5, INK);
}

function drawRoc(ctx: Ctx, h: string): void {
  const c = "#a07a4a";
  const d = dark(c, 0.3);
  ctx.save();
  ctx.translate(0, -16);
  ink(ctx, "roc-wingfar", [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]], d, { sharp: true });
  ink(ctx, "roc-wingfar-tip", [[-12, -26], [-20, -30], [-16, -22], [-22, -24], [-17, -18]], dark(h, 0.2), { sharp: true, shade: false, w: 0.6 });
  ink(ctx, "roc-tail", [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]], h, { sharp: true, shade: false, w: 0.6 });
  ink(ctx, "roc-body", ellPts(0, 0, 9, 6, 16), c);
  ink(ctx, "roc-belly", ellPts(1.5, 2, 6, 3, 12), "#f0e6d0", { shade: false, w: 0.5 });
  ink(ctx, "roc-wing", [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]], c, { sharp: true });
  ink(ctx, "roc-wing-tip", [[10, -28], [18, -34], [15, -24], [22, -27], [16, -19]], h, { sharp: true, shade: false, w: 0.6 });
  ink(ctx, "roc-crest", [[6, -7], [4, -12], [8, -8.4], [9, -13], [10, -7.5]], h, { sharp: true, shade: false, w: 0.5 });
  ink(ctx, "roc-head", ellPts(9, -4, 4.2, 4.2, 12), c);
  ink(ctx, "roc-beak", [[12.5, -5.2], [17, -3], [12.5, -1]], "#e8bb48", { sharp: true, shade: false, w: 0.5 });
  dot(ctx, 10.6, -5, 0.9, 0.9, INK);
  for (const x of [-2, 3]) {
    stroke(ctx, `roc-claw${x}`, [[x, 5], [x, 9]], 1.4, "#e8bb48");
    stroke(ctx, `roc-claw2${x}`, [[x - 1.2, 9.6], [x, 8.6], [x + 1.2, 9.6]], 0.6);
  }
  ctx.restore();
}

function drawDemon(ctx: Ctx, h: string): void {
  const skin = "#6a3a7a";
  const wing = "#3a1a40";
  ink(ctx, "dm-wing-l", [[-3, -30], [-20, -42], [-17, -34], [-22, -32], [-16, -26], [-18, -20], [-4, -22]], wing, { sharp: true });
  ink(ctx, "dm-wing-r", [[3, -30], [18, -44], [16, -36], [21, -33], [15, -27], [17, -21], [4, -22]], wing, { sharp: true });
  limb(ctx, "dm-tail", [[-2, -14], [-8, -6], [-6, -2]], 1.4, skin);
  for (const x of [-3, 3]) ink(ctx, `dm-leg${x}`, [[x - 1.8, -14], [x + 1.8, -14], [x + 2, 0], [x - 2, 0]], skin, { w: 0.6 });
  ink(ctx, "dm-torso", [[-7, -30], [7, -30], [7.4, -13], [-7.4, -13]], h);
  ink(ctx, "dm-hem", [[-7, -15], [7, -15], [5, -11], [-5, -11]], dark(h, 0.35), { shade: false, w: 0.6 });
  limb(ctx, "dm-arm-l", [[-7, -28], [-10, -19]], 2.6, skin);
  limb(ctx, "dm-arm-r", [[7, -28], [11, -20]], 2.6, skin);
  ink(ctx, "dm-blade-l", [[-10.6, -19], [-14.6, -33.6], [-13, -33.2], [-9.4, -19.6]], "#c8c0e0", { shade: false, w: 0.5, sharp: true });
  ink(ctx, "dm-blade-r", [[10.4, -20.4], [17.6, -33.6], [16, -33.4], [11.6, -19.6]], "#c8c0e0", { shade: false, w: 0.5, sharp: true });
  ink(ctx, "dm-head", ellPts(0, -36, 6, 6, 14), skin);
  for (const s of [-1, 1]) ink(ctx, `dm-horn${s}`, [[s * 4, -40], [s * 8.6, -44], [s * 7, -50.4], [s * 6, -45], [s * 2, -41.4]], "#2a1a2a", { shade: false, w: 0.6 });
  for (const x of [-2.2, 2.2]) dot(ctx, x, -36, 1.1, 1.1, "#ff5a8a");
}

function drawGiant(ctx: Ctx, h: string): void {
  const skin = "#c89a78";
  const sd = dark(skin, 0.25);
  for (const x of [-5, 5]) ink(ctx, `gi-leg${x}`, [[x - 3, -16], [x + 3, -16], [x + 3.2, 0], [x - 3.2, 0]], sd, { w: 0.7 });
  limb(ctx, "gi-arm-far", [[-10, -35], [-13, -22]], 4.2, sd);
  ink(ctx, "gi-torso", [[-10, -38], [10, -38], [10.4, -18], [-10.4, -18]], skin);
  ink(ctx, "gi-cloth", [[-9, -20], [9, -20], [8, -12], [3, -14], [0, -11], [-4, -14], [-8, -12]], h);
  ink(ctx, "gi-pauldron", ellPts(-9, -36, 4.5, 3, 12), h, { w: 0.7 });
  ink(ctx, "gi-club", [[13, -21], [20, -38], [24.6, -40], [25.6, -46.4], [21, -47.6], [17.6, -40], [15.4, -23]], "#8a847e");
  limb(ctx, "gi-arm", [[10, -35], [14, -24]], 4.2, skin);
  ink(ctx, "gi-head", ellPts(0, -43, 6, 6, 14), skin);
  stroke(ctx, "gi-band", [[-6, -46.4], [6, -46.4]], 2.4, "#5a3a20");
  for (const x of [-2.2, 2.2]) dot(ctx, x, -43, 0.9, 1.2, INK);
}

function drawAvatar(ctx: Ctx, h: string, element: string | null | undefined): void {
  const el = elementOf(element) ?? "fire";
  const [ec, el2] = ELEMENT_COLORS[el];
  ctx.save();
  ctx.globalAlpha = 0.8;
  for (const [x, y, s] of [[-6, -4, 3], [5, -2, 2.5], [0, 1, 2]] as const) ink(ctx, `av-wisp${x}`, ellPts(x, y, s, s, 10), ec, { shade: false, w: 0.5 });
  ctx.restore();
  ink(ctx, "av-body", [[-8, -32], [-9.6, -20], [-6, -9], [-3, -4.6], [0, -2], [3, -5], [6, -9], [9.6, -20], [8, -32]], ec);
  ink(ctx, "av-glow", [[-5, -30], [-5.6, -20], [-2, -12], [2, -12], [5.6, -20], [5, -30]], el2, { shade: false, line: false, alpha: 0.6 });
  limb(ctx, "av-arm-l", [[-8, -30], [-13, -20]], 3, ec);
  limb(ctx, "av-arm-r", [[8, -30], [13, -20]], 3, ec);
  if (el === "ice") for (const x of [-4, 0, 4]) ink(ctx, `av-ice${x}`, [[x - 1.5, -42], [x, -48], [x + 1.5, -42]], "#ffffff", { sharp: true, shade: false, w: 0.5 });
  else for (const x of [-3, 0, 3]) ink(ctx, `av-flame${x}`, [[x - 2, -42], [x, -49.6], [x + 2, -42]], ec, { sharp: true, shade: false, w: 0.5 });
  ink(ctx, "av-head", ellPts(0, -38, 6, 6, 14), el2);
  ink(ctx, "av-core", [[0, -27], [3.5, -23], [0, -19], [-3.5, -23]], h, { sharp: true, shade: false, w: 0.6 });
  for (const x of [-2.2, 2.2]) dot(ctx, x, -38, 1.1, 1.1, "#ffffff");
}

function drawShadow(ctx: Ctx, h: string): void {
  const c = "#3a3248";
  ctx.save();
  ctx.globalAlpha = 0.9;
  ink(ctx, "sh-body", [[-9, -34], [-11, -20], [-7.6, -8], [-4, -2], [0, -5], [3, -1], [6.6, -6], [11, -20], [9, -34]], c);
  ctx.restore();
  for (const s of [-1, 1]) ink(ctx, `sh-spike${s}`, [[s * 9, -34], [s * 14, -38], [s * 6, -36]], c, { sharp: true, shade: false, w: 0.6 });
  limb(ctx, "sh-arm-l", [[-9, -30], [-14, -20], [-16, -14]], 2.4, c);
  limb(ctx, "sh-arm-r", [[9, -30], [14, -20], [17, -15]], 2.4, c);
  stroke(ctx, "sh-rib-l", [[-2, -26], [-6, -16], [-3, -8], [-8, -2]], 1.8, h);
  stroke(ctx, "sh-rib-r", [[2, -26], [5, -15], [2, -8], [6, -3]], 1.8, h);
  ink(ctx, "sh-head", ellPts(0, -39, 6, 6.5, 14), c);
  ctx.save();
  ctx.shadowColor = h;
  ctx.shadowBlur = 3;
  for (const x of [-2.4, 2.4]) dot(ctx, x, -39, 1.6, 0.9, light(h, 0.5));
  ctx.restore();
}

function drawTreant(ctx: Ctx, h: string): void {
  const bark = "#6a4a2a";
  const bd = dark(bark, 0.3);
  const leaf = mix("#4a8a3a", h, 0.35);
  for (const x of [-5, 5]) ink(ctx, `tr-root${x}`, [[x - 3, -14], [x + 3, -14], [x + 4, 0], [x + 1, -1.4], [x - 1.6, 0], [x - 4, 0]], bd, { w: 0.7 });
  ink(ctx, "tr-trunk", [[-8, -38], [8, -38], [8.6, -12], [-8.6, -12]], bark);
  for (const y of [-32, -25, -18]) stroke(ctx, `tr-bark${y}`, [[-5, y], [-2, y + 3]], 0.6);
  limb(ctx, "tr-arm-l", [[-8, -32], [-15, -26], [-16, -18]], 2.8, bark);
  limb(ctx, "tr-arm-r", [[8, -32], [15, -27], [17, -20]], 2.8, bark);
  for (const [x, y, r] of [[-14, -28, 4], [16, -29, 4], [-6, -44, 7], [5, -45, 7.5], [0, -50, 6.5]] as const) ink(ctx, `tr-leaf${x}`, ellPts(x, y, r, r * 0.92, 14), leaf);
  for (const x of [-2.4, 2.4]) dot(ctx, x, -32, 1.2, 1.2, "#ffe9a0");
}

/** 10 種形態（鍵 ＝ 樣張的形態 id；`top` ＝ 各畫法實際最高點，量自上面的座標）。 */
export const FORM_ARTS: Readonly<Record<string, FormArt>> = {
  bear: { zh: "熊", size: 1.3, top: 31.4, draw: drawBear },
  werewolf: { zh: "狼人", size: 1.25, top: 54.6, draw: drawWerewolf },
  dragon: { zh: "龍", size: 1.5, top: 54, draw: drawDragon },
  cat: { zh: "貓", size: 1.25, top: 25.4, draw: drawCat },
  roc: { zh: "鳥", size: 1.2, top: 50, draw: drawRoc },
  demon: { zh: "惡魔", size: 1.2, top: 50.4, draw: drawDemon },
  giant: { zh: "巨人", size: 1.45, top: 47.6, draw: drawGiant },
  avatar: { zh: "元素化身", size: 1.2, top: 49.6, draw: drawAvatar },
  shadow: { zh: "暗影形態", size: 1.2, top: 45.5, draw: drawShadow },
  treant: { zh: "樹人", size: 1.3, top: 59.5, draw: drawTreant },
};

/** 形態外觀 id（`FormView.look`，內容檔 `forms.yaml` 的 `look`）→ 畫法 id。 */
export const FORM_LOOKS: Readonly<Record<string, string>> = {
  form_bear: "bear",
  form_cat: "cat",
  form_roc: "roc",
  form_elemental: "avatar",
  form_werewolf: "werewolf",
  form_demon: "demon",
  form_giant: "giant",
  form_shadow: "shadow",
  form_treant: "treant",
  form_dragon: "dragon",
};

/** 外觀 id → 畫法；不認得（含空值）回傳 `null`，呼叫端退回原角色紙娃娃＋光環。 */
export function formArtOf(look: string | null | undefined): { id: string; art: FormArt } | null {
  if (look === null || look === undefined || !Object.hasOwn(FORM_LOOKS, look)) return null;
  const id = FORM_LOOKS[look];
  const art = id === undefined ? undefined : FORM_ARTS[id];
  return id === undefined || art === undefined ? null : { id, art };
}

/** 形態小人的畫面縮放（相對 52px 虛擬格）：樣張戰場用 0.6 × min(size, 1.3)，免得龍與巨人超出一格太多。 */
export function formScale(art: FormArt): number {
  return 0.6 * Math.min(art.size, 1.3);
}

/** 光環半徑（52px 虛擬格單位，已含縮放）：樣張的 16 × size × 縮放；不認得的形態用預設 20 × 小人縮放。 */
export function formAuraRadius(look: string | null | undefined, doll: number): number {
  const f = formArtOf(look);
  return f === null ? 20 * doll : 16 * f.art.size * formScale(f.art);
}

/** 頭頂狀態列要比一般小人再往上移多少（畫面像素，≥ 0）：形態比小人高出的部分；`tile` ＝ 格子像素、`doll` ＝ 小人縮放、`humanTop` ＝ 小人最高點。 */
export function formRowRise(look: string | null | undefined, tile: number, doll: number, humanTop = 44): number {
  const f = formArtOf(look);
  if (f === null) return 0;
  const k = tile / 52;
  return Math.max(0, f.art.top * formScale(f.art) * k - humanTop * doll * k);
}

/** 主角主色：身體裝備 color → 披風 color → 陣營藍；不是 #rrggbb 的值跳過。 */
export function formHeroColor(bodyColor?: string, cloakColor?: string): string {
  for (const c of [bodyColor, cloakColor]) if (c !== undefined && isHex(c)) return c;
  return FORM_HERO_FALLBACK;
}

/** 手繪光環：元素色虛線橢圓（線寬 1.1、虛線 2.4／1.6）＋18% 同色填色；原點是腳下。 */
export function drawFormAura(ctx: Ctx, color: string, rx: number): void {
  ctx.save();
  ctx.globalAlpha = 0.85;
  ctx.setLineDash([2.4, 1.6]);
  stroke(ctx, `aura-${rx}`, [...ellPts(0, 0, rx, rx * 0.3, 24), [rx, 0] as Pt], 1.1, color);
  ctx.restore();
  ctx.save();
  ctx.globalAlpha = 0.18;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU);
  ctx.fill();
  ctx.restore();
}

/** 倒地：整個形態橫躺（頭朝右），躺在腳底附近。 */
function lieDown(ctx: Ctx, art: FormArt): void {
  ctx.translate(-art.top * 0.45, -art.top * 0.2);
  ctx.rotate(Math.PI / 2);
}

/**
 * 畫一個形態（原點 ＝ 腳底；單位 ＝ 樣張座標，由呼叫端先縮放）：影子＋形態本體。朝東與南看右、西與北鏡像（樣張只有側面）。
 * 光環另外畫（`drawFormAura`），因為不認得的形態也要有光環。不認得的 id 回傳 `false`、什麼都不畫。
 */
export function drawForm(ctx: Ctx, id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean): boolean {
  const art = Object.hasOwn(FORM_ARTS, id) ? FORM_ARTS[id] : undefined;
  if (art === undefined) return false;
  withShadeDir(ctx, -1, () => {
    ctx.save();
    if (facing === "west" || facing === "north") ctx.scale(-1, 1);
    if (downed) lieDown(ctx, art);
    else shadow(ctx, 14);
    art.draw(ctx, hero, element);
    ctx.restore();
  });
  return true;
}

/** 形態貼圖畫布（寬於小人，免得龍的尾巴與吐息被切掉）。腳底在 (FORM_W/2, FORM_FOOT_Y)。 */
export const FORM_W = 96;
export const FORM_H = 88;
export const FORM_FOOT_Y = FORM_H - 6;
/** 光環貼圖畫布（中心 ＝ 橢圓中心）。 */
export const AURA_W = 72;
export const AURA_H = 28;

/** 形態貼圖的快取鍵。 */
export function formKey(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean): string {
  return `${id}|${hero}|${elementOf(element) ?? "-"}|${facing}|${downed ? "down" : "up"}`;
}

/** 產生形態離屏 canvas（`dpr` 倍解析度；`dollScale` ＝ 小人縮放，畫面比例以它為基準）；沒有 DOM 或不認得的形態回傳 `null`。 */
export function renderFormCanvas(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean, dpr: number, dollScale: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const art = Object.hasOwn(FORM_ARTS, id) ? FORM_ARTS[id] : undefined;
  if (art === undefined) return null;
  const c = document.createElement("canvas");
  c.width = FORM_W * dpr;
  c.height = FORM_H * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  ctx.translate(FORM_W / 2, FORM_FOOT_Y);
  const k = formScale(art) / dollScale;
  ctx.scale(k, k);
  drawForm(ctx, id, hero, element, facing, downed);
  return c;
}

/** 產生光環離屏 canvas（原點在中心；`rx` 為 52px 虛擬格單位）；沒有 DOM 時回傳 `null`。 */
export function renderAuraCanvas(color: string, rx: number, dpr: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = AURA_W * dpr;
  c.height = AURA_H * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  ctx.translate(AURA_W / 2, AURA_H / 2);
  drawFormAura(ctx, color, Math.min(rx, AURA_W / 2 - 2));
  return c;
}
