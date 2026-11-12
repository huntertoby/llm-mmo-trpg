// qIconsEvent.js：「小圖示改 Q 版」全量重畫第 8 批——事件卡（選項 8、其他 5、六屬性 6、d20、事件插圖左上角小牌的圖示 8）＋第⑧b 批事件插圖頭頂泡泡。畫圖 agent 2026-11-12。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節；紀錄：docs/art/Q版小圖示-第8批事件卡.md；樣張頁：q-icons-event.html。
// 框不動（規則 13）：事件卡圓環照現行 drawChip（深底 #2a241e 圓＋選項色圓環，線寬 max(1.2, 6%)），d20 沒有框，小牌的深色膠囊與金邊、泡泡框照現行，只換裡面的圖。
// 和前幾批同題材的一律直接呼叫（src 欄寫出處）：風格樣張 qIcons.js 的 ART.event（戰鬥、說服、調查、交易）、ART.hud.exit（離開）、W.fistArt（拳頭的形）；
// 第 4 批 qIconsParts.js 的狀態「隱蔽」兜帽、狀態「激昂」手臂、效果「揭露」眼睛、卡片「生命」紅心、卡片「源力」晶石、徽章「打擊」斜劍；
// 第 7 批 qIconsHud.js 的金幣、留言、警告。
// 圖樣大小照第 4 批的做法看「圖樣本身」幾 px（圓環裡的圖樣＝圓環 × fill）：≤24px 省小零件（o.small）、≤14px 只留一個主體、不包外框（o.tiny）。
// ---------------------------------------------------------------------------------------------
// Phase QI-6：由 docs/art/sample/qIconsEvent.js（⑧ 第 2 版 8eabffec、⑧b 第 2 版 350ad6b9 之後）逐行搬成 TypeScript（需求 docs/art/Q版小圖示-事件卡移植需求.md）。
// 和樣張不同的地方（都不改畫法）：
// - 依賴改 import：`QIcons` 的 render、outlinePx、H 小工具、W.fistArt → `./core`；`ART.event／hud.exit` → `./legacy48`（ART.event 是 QI-6 搬進去的）；
//   `QIconsParts.entry` → `./parts`；`QIconsHud.def` → `./hud`；`QIconsWeapons.blit` → `./core` 的 `blit`。心形用 `parts.ts` 匯出的 `heart`（和樣張本檔那份相同）。
// - 材質色照 `core.ts` 的 `M`（＝material.ts，QI-1 第 0.0 節第 3 點）：鐵拳（`fistArt` 的 `PW`）與戰鬥的劍比樣張暗一階，和遊戲端其他 Q 版圖示同一份。
// - 沒搬：`live`、`topic` 欄、`D20_ZH`、`GRP_ZH`、`BUBBLE_ZH`、`ringFrame` 以外的樣張頁小工具、`bubbleGlyph` 的 `noPre`（樣張剪影列用）。
// - 建畫布一律 `blank()`／`ctxOf()`；沒有畫布時 `glyph` 回 null、不貼。`canvas(id, px, res, opt)`（樣張 `(id, px, zoom, opt)`）。
// - d20 的點數常數（`D20_FONT_PX`、`D20_HALO`、`D20_HALO_W`）放這裡，`storyIconArt.ts` re-export（現行同值）。
// - 加 `bareGlyph(id, px, res)`：只畫圖樣、不帶深底圓與色環（需求 2.3，給資訊面板段用；照樣張 infoPanels.js 的 evBare()）。
// - 小牌、泡泡的表另開兩張（`BADGE_Q`＝`ICON` 的 `b_*`、`BUBBLE`），`eventArtParts.ts` 的 `ICON` 只留地物營火（需求 4 第 4 點）。
import { blank, blit, ci, ctxOf, el, f, fistArt, flame, glow, halo, ln, mix, OUT, outlinePx, poly, render, rr, starPts, TAU, type Ctx, type QDef, type QOpts } from "./core";
import * as QH from "./hud";
import { ART } from "./legacy48";
import { entry, heart } from "./parts";

const PI = Math.PI;
const CREAM = "#f2e6c8";
type Draw = (c: Ctx, o: QOpts) => void;
const at = (c: Ctx, x: number, y: number, k: number, fn: (x: Ctx) => void, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
const st = (c: Ctx, col: string, w: number, fn: (x: Ctx) => void, cap: CanvasLineCap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
/** ±10 單位的圖樣（第 4 批的卡片小圖、狀態、效果）放進 48 格：中心 24,24、放大 1.8×k（和第 4 批 def() 同一個倍率）。 */
const b10 = (fn: Draw, k = 1, dx = 0, dy = 0): Draw => (c, o) => at(c, 24 + dx, 24 + dy, 1.8 * k, (q) => fn(q, o));
const part = (cat: string, id: string): Draw => (c, o) => entry(cat, id).d(c, o);

// ---------------- 新畫的圖樣（48 格） ----------------
/** 硬闖：第 1 批武器「拳套」的鐵拳（W.fistArt 原樣：指節朝上的握拳、深一階的護腕與指節板，第 1 批過審的形），0.92 倍、略偏左下；右上一顆黃色七角撞擊星（白芯、自己包一圈外框，同風格樣張「塔盾猛擊」的撞擊星）。
 *  試過兩次（紀錄第 5 節）：① 同一個拳頭換膚色、上面三道黃短芒——膚色的指節板＋拇指在 24px 像一張嘴、三道芒像王冠，讀成「戴王冠的臉」；② 自己畫的膚色側面拳＋右邊三道短芒——方塊拳身＋橫的拇指仍像一張臉（機器人頭）。
 *  換回鐵拳（灰鐵色不像皮膚、不會讀成臉），撞擊改成一顆星放在角落。 */
/* 第 2 版（審查可修 1）：拳 0.78→0.92、中心從 (20.6,28.2) 移到 (22.4,26.6)，星往內收、壓在拳的右上角（星自己 halo() 一圈外框，分得開）。 */
const forceArt: Draw = (c, o) => {
  at(c, 22.4, 26.6, 0.92, (q) => { q.translate(-24, -24.9); fistArt(q, o); });
  halo(c, o, (x) => { poly(x, "#ffd23f", starPts(36.4, 12, 9.8, 4.6, 7, -1.2), 0.5); poly(x, "#ffffff", starPts(36.4, 12, 4.4, 2.2, 7, -1.2)); });
};
/** 機遇：四片心形葉的幸運草（葉尖朝中心、每片一道深綠葉脈與一塊亮面），右下一根彎莖，右上一顆發光的白黃四芒星。 */
const cloverArt: Draw = (c, o) => {
  ln(c, "#4f8a3a", 4.2, [[25, 24], [30, 33], [36.5, 41.5]]);
  for (const [i, a] of [0, PI / 2, PI, -PI / 2].entries()) at(c, 23, 22, 1, (q) => { heart(q, i % 2 ? "#5cae3e" : "#6abc46", 0, -7.4, 1.04); el(q, "#a8e078", -3.4, -11.6, 2.6, 1.7, -0.5); if (!o.tiny) ln(q, "#3a7a2a", 1.5, [[0, -1.5], [0, -9]]); }, a);
  poly(c, "#fff4c0", starPts(39.4, 9.2, 7.2, 2.2, 4), 0.5); poly(c, "#ffffff", starPts(39.4, 9.2, 3.4, 1.2, 4));
};
/** 線索：微斜的米白便條（右上折角暗一階），右下蓋一顆金色五角星（深金邊、白芯），星凸出紙外一點。 */
const clueArt: Draw = (c, o) => {
  at(c, 21, 22, 1, (q) => { poly(q, CREAM, [[-14, -17], [9, -17], [15, -11], [15, 18], [-14, 18]], 1.4); poly(q, "#c8b890", [[9, -17], [15, -11], [9, -11]], 0.6); f(q, "rgba(120,90,40,0.2)", () => q.rect(9.5, -8, 5.5, 26)); if (!o.tiny) for (const y of [-7, -1]) rr(q, "#a89a7a", -10, y, 16, 2.2, 1.1); }, -0.1);
  poly(c, "#b8801a", starPts(31, 31.5, 14, 6.4, 5), 1); poly(c, "#ffd23a", starPts(31, 31.5, 11, 5, 5), 0.6); poly(c, "#fff6c8", starPts(31, 31.5, 4.6, 2.2, 5));
};
/** 模型關閉：灰紫色的玻璃水晶球（右下暗一階、左上白亮面），一道深色粗裂痕斜過球面，下面一個木座。 */
const modelOffArt: Draw = (c, o) => {
  poly(c, "#a06a36", [[12, 35.5], [36, 35.5], [41, 44], [7, 44]], 1.4); f(c, "#c88a50", () => c.rect(10, 36.5, 28, 2.4));
  ci(c, "#b4bad0", 24, 20.5, 16.4); f(c, "#868ca6", () => { c.arc(24, 20.5, 16.4, -PI * 0.1, PI * 0.72); c.arc(21.6, 18, 15.4, PI * 0.72, -PI * 0.1, true); c.closePath(); });
  el(c, "#ffffff", 17.4, 12.6, 3.4, 5, 0.65);
  ln(c, OUT, o.tiny ? 3.6 : 2.8, [[16.6, 6.6], [23.4, 15.2], [18.8, 21.4], [28.4, 31.6]], "miter");
};
/** 說書人：攤開的米白書（藍褐書背、右頁暗一階），一支淡紫羽毛筆斜插在書上（筆尖深色、羽片左半亮）。≤14px 時兩件中間墊一道深色縫。 */
const quillPath = (q: Ctx) => { q.beginPath(); q.moveTo(0, -6); q.bezierCurveTo(-7.4, -12, -7.6, -26, 0.6, -37.5); q.bezierCurveTo(5.6, -27, 5, -12, 0, -6); q.closePath(); };
const narratorArt: Draw = (c, o) => at(c, 24, 23, 0.88, (c) => { c.translate(-24, -23);
  f(c, "#5a3e28", () => { c.moveTo(3, 33); c.lineTo(24, 36.5); c.lineTo(45, 33); c.lineTo(45, 45); c.lineTo(24, 46.6); c.lineTo(3, 45); c.closePath(); });
  poly(c, CREAM, [[4, 30], [23, 33.4], [23, 44], [4, 41.6]], 1); poly(c, "#e2d2a8", [[25, 33.4], [44, 30], [44, 41.6], [25, 44]], 1);
  at(c, 20.5, 35, 1, (q) => {
    quillPath(q); q.strokeStyle = OUT; q.lineWidth = o.tiny ? 4.4 : 0; if (o.tiny) { q.lineJoin = "round"; q.stroke(); }
    quillPath(q); q.fillStyle = "#c8bcff"; q.fill(); q.save(); quillPath(q); q.clip(); f(q, "#9a86e0", () => q.rect(0.4, -40, 8, 36)); f(q, "#efeaff", () => q.rect(-5.4, -30, 2.4, 18)); q.restore();
    if (!o.tiny) ln(q, "#6a58b8", 1.4, [[0, -7], [0.4, -33]]);
    poly(q, "#3a3448", [[-2.2, -6.4], [2.2, -6.4], [0, 1.2]], 0.4);
  }, 0.6);
});
/** 說明：粗的「i」（上一顆圓點、下面帶上下橫腳的直筆），淡青白、左側白亮面、右側淡青暗面——符號（規則 10），筆畫寬 19%。 */
const infoArt: Draw = (c, _o) => {
  ci(c, "#e6f6fc", 24, 9.6, 5.8); el(c, "#ffffff", 22.4, 8, 1.8, 1.4, -0.6);
  rr(c, "#e6f6fc", 19.4, 18.4, 9.6, 21, 1.6); rr(c, "#e6f6fc", 14.4, 18.4, 12, 5, 1.6); rr(c, "#e6f6fc", 13.6, 36.4, 21, 6, 1.8);
  f(c, "#ffffff", () => c.rect(20.6, 20, 2.2, 16)); f(c, "#a8d4e4", () => c.rect(26.2, 24, 2.8, 12.4));
};
/** 事件線（線頭）：直立的木線軸（上下兩片淺木色軸盤、左側亮），中間纏滿紅橘色的線（兩道亮色纏紋），右邊拉出一段彎的線頭。
 *  第 1 次試做是毛線球＋左下一段線頭：14 真 1 倍是「紅球＋一根短棍」，讀成棒棒糖、櫻桃，換成剪影是「工」字的線軸。 */
const threadArt: Draw = (c, o) => {
  st(c, "#e0603a", 4.2, (q) => { q.moveTo(28, 21); q.bezierCurveTo(40, 19, 44, 27, 38.4, 31.6); q.quadraticCurveTo(34.6, 35, 40.4, 40.4); });
  rr(c, "#e0603a", 10.6, 9.6, 19.6, 28.8, 2); if (!o.tiny) for (const y of [15, 21, 27, 33]) f(c, "#b03e26", () => c.rect(10.6, y, 19.6, 1.4));
  for (const y of [12.6, 23.4]) rr(c, "#ffa080", 12, y, 16.8, o.tiny ? 4 : 3, 1.4);
  for (const y of [4.4, 36.2]) { rr(c, "#c8925a", 5.6, y, 29.6, 7.4, 3); f(c, "#ecc490", () => c.roundRect(7.4, y + 1.2, 17, 2.2, 1.1)); }
};
/** 敏捷：一根淡薄荷色的羽毛斜放（羽根在左下、羽尖在右上；右半暗一階、羽軸深一階、羽片下緣兩道缺口），左上兩道薄荷色的速度線。 */
const featherPath = (q: Ctx) => { q.beginPath(); q.moveTo(0, 15); q.bezierCurveTo(-8.6, 6, -8.6, -12, 0, -22); q.bezierCurveTo(8.6, -12, 8.6, 6, 0, 15); q.closePath(); };
const dexArt: Draw = (c, o) => {
  for (const [x0, y0, x1, y1] of [[5.6, 21, 15, 11.4], [8.4, 30.6, 15.6, 23.4]] as const) ln(c, "#7fe0c0", 4.6, [[x0, y0], [x1, y1]]);
  at(c, 27, 22, 1, (q) => {
    featherPath(q); q.fillStyle = "#d4f6e8"; q.fill(); q.save(); featherPath(q); q.clip(); f(q, "#8ed8bc", () => q.rect(0.6, -24, 10, 40)); f(q, "#ffffff", () => q.rect(-4.6, -12, 2, 14));
    f(q, "#16121a", () => { q.moveTo(-9, 5); q.lineTo(-3.4, 2.6); q.lineTo(-9, 1.4); q.closePath(); }); q.restore();
    ln(q, "#4a9a7c", o.small ? 2.2 : 1.6, [[0, 21.4], [0, -16]]);
  }, PI / 4);
};
/** 智力：攤開的米白書（深藍封面邊、中縫暗一階），上方一顆發光的淡紫五角星（白芯）。 */
const intArt: Draw = (c, o) => at(c, 24, 25, 0.92, (c) => { c.translate(-24, -25);
  f(c, "#3a54b0", () => { c.moveTo(3, 26); c.lineTo(24, 29.4); c.lineTo(45, 26); c.lineTo(45, 44); c.lineTo(24, 46.4); c.lineTo(3, 44); c.closePath(); });
  poly(c, CREAM, [[4.4, 23], [23, 26.4], [23, 43], [4.4, 40.4]], 1); poly(c, "#e2d2a8", [[25, 26.4], [43.6, 23], [43.6, 40.4], [25, 43]], 1);
  if (!o.small) for (const y of [30, 35]) { rr(c, "#b0a080", 8, y, 11, 1.8, 0.9); rr(c, "#b0a080", 29, y, 11, 1.8, 0.9); }
  poly(c, "#c8bcff", starPts(24, 12, 11.4, 5, 5), 0.8); poly(c, "#ffffff", starPts(24, 12.4, 4.6, 2.2, 5)); el(c, "#efeaff", 20.4, 8.6, 1.6, 1.1, -0.6);
});
/** 意志：一團金橘色的火（外層橘金、中層黃、白芯，規則 5 三層），外圍金色光暈。 */
const wilArt: Draw = (c, _o) => { flame(c, "#ffa22a", 24, 24.6, 2.02); flame(c, "#ffd23f", 24, 30.4, 1.28); flame(c, "#fff6d8", 24, 35.4, 0.62); };
/** d20：照現行的六角外形加中央三角面（P(角度, 半徑)、六角 21、三角 12），分面換成平塗、不描面線（規則 2）：中央三角面最亮；外圈六面相鄰的兩面一定不同階（四個色階：中央三角＝混白 66%；上三角、左下三角＝本色 col；右、下兩塊＝混黑 34%；其他（左上、右下小三角）＝整體底混黑 15%），面與面的交界才看得出是骰子。
 *  第 1 次試做只分三階（左上三面同色、右下三面同色），相鄰同色的面連成一大塊，16、20 只剩「六角形＋三角」，像一顆寶石、方糖；分面是骰子的形，不算規則 2 的亮暗面（紀錄第 7 節例外）。 */
const d20Pt = (a: number, r: number): [number, number] => [24 + Math.cos(a) * r, 24 + Math.sin(a) * r];
const d20Art = (col: string): Draw => (c, o) => {
  type P = [number, number];
  const H = [0, 1, 2, 3, 4, 5].map((i) => d20Pt(-PI / 2 + (i * TAU) / 6, 20.4)), T: [P, P, P] = [d20Pt(-PI / 2, 12), d20Pt(PI / 6, 12), d20Pt((5 * PI) / 6, 12)];
  const [H0, H1, H2, H3, H4, H5] = H as [P, P, P, P, P, P], [T0, T1, T2] = T;
  const dark = mix(col, "#000000", 0.34), base = mix(col, "#000000", 0.15), mid = col, lite = mix(col, "#ffffff", 0.66);
  poly(c, base, H, 0.6);
  poly(c, mid, [H0, H1, T0]); poly(c, mid, [H4, H5, T2]); poly(c, dark, [H1, H2, T1, T0]); poly(c, dark, [H3, H4, T2, T1]);
  poly(c, lite, T, 0.6);
  if (!o.small) f(c, "rgba(255,255,255,0.45)", () => { c.moveTo(H5[0] + 1.6, H5[1] + 1.6); c.lineTo(H0[0], H0[1] + 2.4); c.lineTo(H0[0], H0[1] + 4.6); c.lineTo(H5[0] + 1.6, H5[1] + 4.4); c.closePath(); });
};
/** d20 點數的字高（px，48 格的畫布座標）。 */
export const D20_FONT_PX = 14;
/** 點數外圈的顏色（6Q-1，和三角面同色）。 */
export const D20_HALO = "#fff8e8";
/** 點數外圈露在字外的寬度（6Q-1；描邊一半在字外，所以 `lineWidth ＝ D20_HALO_W × 2 ＝ 3.5`）。 */
export const D20_HALO_W = 1.75;
const D20_INK = "#2b1e16";
/** d20 的點數（29px 以上，照現行 drawD20：14px 粗體 Georgia、(24,29)，先描一圈 #fff8e8（露在字外 1.75）再寫深色字）。畫在外框之上（post）。 */
const d20Num = (n: number | string | undefined | null): Draw => (c) => { if (n === undefined || n === null || n === "") return; c.font = `bold ${D20_FONT_PX}px Georgia, serif`; c.textAlign = "center"; c.lineJoin = "round"; c.lineWidth = D20_HALO_W * 2; c.strokeStyle = D20_HALO; c.strokeText(String(n), 24, 29); c.fillStyle = D20_INK; c.fillText(String(n), 24, 29); c.textAlign = "left"; };
/** 小牌金幣 ≤14px 的形（第 2 版，審查必修 1）：單枚方孔大幣、略斜成橢圓，下緣露一道暗金厚度邊，中間深色方孔（現行 ICON.coin 的方孔），左上一塊亮面；
 *  金色照第 7 批金幣（#e8bb48、#f6d878、#b8862a、#fffbe6）。第 1 版的「兩枚疊幣＋斜靠大幣」在 14 真 1 倍是一團凹凸的金色、讀不出錢幣，也不合規則 8。
 *  只有 o.tiny（小牌 14）走這個形；HUD 金幣 15 不變（同第 7 批「留言」≤14px 另一個形）。 */
const bigCoinArt: Draw = (c, _o) => at(c, 24, 24, 1, (q) => {
  el(q, "#9a6e1e", 0, 3.4, 20.6, 18.2);
  el(q, "#e8bb48", 0, -0.4, 20.6, 18.2);
  el(q, "#f6d878", -1.8, -1.8, 15.4, 13.2);
  rr(q, OUT, -6, -6, 12, 12, 1.4);
  el(q, "#fffbe6", -10.4, -8.4, 4.6, 2.6, -0.6);
}, -0.12);
/** 小牌：粗的黃色驚嘆號（上寬下窄、左側亮）。 */
const bangArt: Draw = (c, _o) => { poly(c, "#ffd04a", [[16.6, 4.4], [31.4, 4.4], [28, 26.6], [20, 26.6]], 2.2); ci(c, "#ffd04a", 24, 39.8, 5.6); f(c, "#fff3a0", () => { c.moveTo(18.4, 6); c.lineTo(23, 6); c.lineTo(22.2, 23); c.lineTo(20.6, 23); c.closePath(); }); f(c, "#d8a020", () => { c.moveTo(27, 6); c.lineTo(29.8, 6); c.lineTo(27.2, 25.4); c.lineTo(25.6, 25.4); c.closePath(); }); }; /* 驚嘆號的直筆與圓點之間留 5.6 單位（13px 真 1 倍約 1.5px）：第 1 次試做只留 1.4 單位，真 1 倍兩段黏成一根 */
/** 小牌：粗的米白問號（現行同色）。 */
const askArt: Draw = (c, _o) => { st(c, CREAM, 8.6, (q) => { q.arc(24, 15.4, 9.2, PI * 1.08, PI * 0.42); q.quadraticCurveTo(24, 26, 24, 30.4); }); ci(c, CREAM, 24, 40.6, 5.4); st(c, "#ffffff", 2.2, (q) => q.arc(24, 15.4, 9.6, PI * 1.12, PI * 1.45)); };
/** 小牌：營火（兩根交叉的木柴、切口淺色，上面一團橘火、黃內焰、白芯）。 */
const restArt: Draw = (c, _o) => {
  for (const s of [-1, 1]) at(c, 24, 38.6, 1, (q) => { rr(q, "#8a5a32", -16, -3.4, 32, 6.8, 3); f(q, "#a8743e", () => q.rect(-13, -2.6, 24, 1.8)); ci(q, "#e0b070", s > 0 ? 13 : -13, 0, 3); }, s * 0.32);
  flame(c, "#ff8a2a", 24, 20.6, 1.62); flame(c, "#ffd23f", 24, 25.4, 0.98); flame(c, "#fff6d8", 24, 29.2, 0.46);
};

// ---------------- 第⑧b 批：事件插圖頭頂的泡泡（eventArtParts.ts 的 bubble()：淺色圓角泡泡裡 ICON[icon](ctx, x, y−15, 13)，不帶 ink） ----------------
// 泡泡是淺色底（黃、白、紅、淡藍），和小牌的深色膠囊相反：現行的驚嘆號、問號在泡泡裡是深色（OUT），在小牌是米白（BADGE_ICON_INK）。
// 所以符號（驚嘆號、問號）另給深色墨的一份（形照小牌的 bangArt、askArt 一筆不改，只換色）；彩色的圖（金幣、劍、營火、警告、源晶、留言）直接呼叫小牌那一份，
// 外面多包 1px 剪影外框（規則 1；規則 8「≤14px 不包外框」的理由是深色底已經夠分明，淺色泡泡上不成立，見紀錄第 13 節）。
/** 深色墨（第 2 版，審查必修 1）：近黑 #16121a（外框色、現行泡泡的 OUT），不加亮條——第 1 版的褐墨 #3a2410＋左側亮一階細條在真 1 倍比現行淺、細。形與中間縫照留。 */
export const BU_INK = "#16121a";
/** 泡泡：深色驚嘆號（小牌 bangArt 同一個形：上寬下窄的直筆＋圓點，兩段之間留 5.6 單位），單色墨（第 2 版拿掉亮條）。 */
const buBangArt: Draw = (c) => { poly(c, BU_INK, [[16.6, 4.4], [31.4, 4.4], [28, 26.6], [20, 26.6]], 2.2); ci(c, BU_INK, 24, 39.8, 5.6); };
/** 泡泡：深色問號（小牌 askArt 同一個形），單色墨（第 2 版拿掉亮弧）。 */
const buAskArt = (): Draw => (c) => { st(c, BU_INK, 8.6, (q) => { q.arc(24, 15.4, 9.2, PI * 1.08, PI * 0.42); q.quadraticCurveTo(24, 26, 24, 30.4); }); ci(c, BU_INK, 24, 40.6, 5.4); };
/** 泡泡：卷軸（只用在泡泡：朋友的足跡，石碑上的淡藍「資訊」泡泡）。第 7 批功能列「任務」bar_J 的卷軸照抄（qIconsHud.js 不動），
 *  拿掉正中的紅色驚嘆號（那是「任務」）、換成兩道粗字線＋一道短字線（「寫了字」＝留言、碑文，現行也是三道字線）；上下兩捲與紅褐軸頭照留（現行的紅色卷軸桿）。 */
const buScrollArt: Draw = (c, _o) => {
  rr(c, CREAM, 11, 8, 26, 32, 1.5); f(c, "rgba(120,90,40,0.2)", () => c.rect(31, 8, 6, 32));
  for (const [y, w] of [[15.4, 18], [22.6, 18], [29.8, 11]] as const) rr(c, "#5a4a30", 15, y, w, 4, 2); /* 第 2 版（審查可修 3）：字線 #7a6a4a→深一階 #5a4a30 */
  for (const y of [4.6, 36.4]) { rr(c, "#e2d0a0", 8, y, 32, 7, 3.5); f(c, "#fff6dc", () => c.rect(10, y + 1.3, 27, 1.6)); ci(c, "#8a2f20", 7.4, y + 3.5, 3.2); ci(c, "#8a2f20", 40.6, y + 3.5, 3.2); }
};

// =====================================================================
// 圖示表。grp：sol 選項（24）｜misc 其他｜attr 六屬性｜d20｜badge 事件插圖小牌（14）
// ring：現行圓環色（storyIconArt.ts 原樣；框不動）。fill：圖樣格佔圓環的比例。src：沿用出處。sizes：遊戲裡實際的大小（CSS px）。
// =====================================================================
export type EventGroup = "sol" | "misc" | "attr" | "d20" | "badge";
export interface EventIconEntry { zh: string; grp: EventGroup; sizes: readonly number[]; ring?: string; fill?: number; src?: string; k10?: number; d?: Draw; d10?: Draw; pre?: Draw }
export const ICON: Readonly<Record<string, EventIconEntry | undefined>> = {
  // ---------------- 選項 8（SolutionGlyph，事件卡選項鈕與情境判定標題 24px） ----------------
  combat: { zh: "戰鬥", grp: "sol", ring: "#d0503a", sizes: [24], fill: 0.96, src: "style:event.combat", d: (c, o) => ART.event.combat.d(c, o) },
  persuade: { zh: "說服", grp: "sol", ring: "#e8bb48", sizes: [24], fill: 0.86, src: "style:event.persuade", d: (c, o) => ART.event.persuade.d(c, o) },
  sneak: { zh: "潛行", grp: "sol", ring: "#8a7ab8", sizes: [24], fill: 0.86, src: "b4:status.concealed", d: b10(part("status", "concealed"), 1.1) },
  investigate: { zh: "調查", grp: "sol", ring: "#4ab0d0", sizes: [24], fill: 0.8, src: "style:event.investigate", d: (c, o) => ART.event.investigate.d(c, o) },
  force: { zh: "硬闖", grp: "sol", ring: "#e07a4a", sizes: [24], fill: 0.86, src: "b1:fist", d: forceArt },
  chance: { zh: "機遇", grp: "sol", ring: "#6aa84a", sizes: [24], fill: 0.86, pre: (c) => glow(c, 39.4, 9.2, 9, "#fff4a0", 0.6), d: cloverArt },
  leave: { zh: "離開", grp: "sol", ring: "#9a8e7c", sizes: [24], fill: 0.84, src: "style:hud.exit", d: (c, o) => ART.hud.exit.d(c, o) },
  trade: { zh: "交易", grp: "sol", ring: "#e8bb48", sizes: [24], fill: 0.9, src: "style:event.trade", d: (c, o) => ART.event.trade.d(c, o) },

  // ---------------- 其他 5（MiscGlyph） ----------------
  clue: { zh: "線索", grp: "misc", ring: "#e8bb48", sizes: [16], fill: 0.86, pre: (c) => glow(c, 31, 31.5, 15, "#ffd23a", 0.45), d: clueArt },
  model_off: { zh: "模型關閉", grp: "misc", ring: "#9a8e7c", sizes: [14], fill: 0.82, d: modelOffArt },
  narrator: { zh: "說書人", grp: "misc", ring: "#a898ff", sizes: [16, 14], fill: 0.86, d: narratorArt },
  info: { zh: "說明", grp: "misc", ring: "#4ab0d0", sizes: [14, 12], fill: 0.82, d: infoArt },
  thread: { zh: "事件線（線頭）", grp: "misc", ring: "#e8bb48", sizes: [14], fill: 0.84, d: threadArt },

  // ---------------- 六屬性（AttrIcon：情境判定 20、判定結果 18） ----------------
  str: { zh: "力量", grp: "attr", ring: "#e07a4a", sizes: [20, 18], fill: 0.86, src: "b4:status.empowered", d: b10(part("status", "empowered"), 1.1) },
  dex: { zh: "敏捷", grp: "attr", ring: "#6ac0a0", sizes: [20, 18], fill: 0.86, d: dexArt },
  con: { zh: "體質", grp: "attr", ring: "#d04a5a", sizes: [20, 18], fill: 0.86, src: "b4:card.hp", d: b10(part("card", "hp"), 1.24) },
  int: { zh: "智力", grp: "attr", ring: "#7a8aff", sizes: [20, 18], fill: 0.86, pre: (c) => glow(c, 24, 12, 13, "#a898ff", 0.55), d: intArt },
  wis: { zh: "感知", grp: "attr", ring: "#4ab0d0", sizes: [20, 18], fill: 0.86, src: "b4:effect.reveal", d: b10(part("effect", "reveal"), 1.2) },
  wil: { zh: "意志", grp: "attr", ring: "#e8bb48", sizes: [20, 18], fill: 0.86, pre: (c) => glow(c, 24, 27, 21, "#ffd23a", 0.45), d: wilArt },

  // ---------------- d20（D20：判定結果的兩顆骰 64（寫點數）、DC 24、結果 20、擲骰鈕 16；沒有框） ----------------
  d20: { zh: "d20 骰", grp: "d20", sizes: [64, 24, 20, 16], d: d20Art(CREAM) },

  // ---------------- 事件插圖左上角的小牌（eventArt.ts 的 SCENES[].icon；364×156 的插圖上現行 ICON 以 13 畫、實際約 14～15，Q 版畫在 14 的格子；照卡寬縮放，實際約 11～18px；深色膠囊、金邊照現行） ----------------
  b_sword: { zh: "小牌：劍（遭遇・伏擊）", grp: "badge", sizes: [14], k10: 1.24, src: "b4:skeleton.strike", d10: part("skeleton", "strike") },
  b_coin: { zh: "小牌：金幣（寶箱、商隊）", grp: "badge", sizes: [14], src: "b7:coin", d: (c, o) => (o.tiny ? bigCoinArt(c, o) : QH.def("coin").d(c, o)) },
  b_ask: { zh: "小牌：問號（古碑）", grp: "badge", sizes: [14], d: askArt },
  b_rest: { zh: "小牌：營火（祭壇・機遇、營火休息）", grp: "badge", sizes: [14], pre: (c) => glow(c, 24, 24, 20, "#ffb23a", 0.5), d: restArt },
  b_bang: { zh: "小牌：驚嘆號（村民求助）", grp: "badge", sizes: [14], d: bangArt },
  b_warn: { zh: "小牌：警告（陷阱）", grp: "badge", sizes: [14], src: "b7:warn", d: (c, o) => QH.def("warn").d(c, o) },
  b_portal: { zh: "小牌：源晶（異象・源晶裂痕）", grp: "badge", sizes: [14], src: "b4:card.source", d10: part("card", "source") },
  b_notes: { zh: "小牌：留言（朋友的足跡）", grp: "badge", sizes: [14], src: "b7:bar_N", d: (c, o) => QH.def("bar_N").d(c, o) },
};
/** d20 的六種顏色（現行 D20_COLOR 與 OUTCOME_COLOR 原樣；開發頁、指紋用）。 */
export const D20_COLOR: Readonly<Record<string, string>> = { normal: CREAM, crit: "#ffe08a", fumble: "#c8c0b8", success: "#5ad06a", partial: "#e8bb48", failure: "#e04a3a" };
/** 小牌在插圖裡的位置（eventArt.ts：ICON[s.icon](ctx, 21, 20, 13, BADGE_ICON_INK)）。現行的 ICON 以 s＝13 畫，實際畫到約 14～15（金幣半徑 0.55s 再加描邊）；
 *  Q 版的圖樣一律畫在中心 (21,20)、邊長 14 的格子裡（仍是 ≤14px：一個主體、不包外框），和現行看起來一樣大。 */
export const BADGE_AT = { x: 21, y: 20, s: 14 } as const;

/** 第⑧b 批：泡泡裡的圖（eventArtParts.ts 的 9 個 IconId；遊戲端目前只有 4 個泡泡、3 種圖：伏擊紅「！」、村民求助黃「！」、商隊白金幣、朋友的足跡淡藍卷軸；
 *  另 6 個沒有場景用到，開發 PM 照美術建議一起搬）。base：直接用小牌那一份（b_*）；d：泡泡另給的形。ow：剪影外框幾 px（深色墨的符號 0，彩色 1）。use：[場景, 泡泡種類]。 */
export interface BubbleEntry { zh: string; ow: number; base?: string; d?: Draw; pre?: Draw; src?: string; use: readonly (readonly [string, string])[] }
export const BUBBLE: Readonly<Record<string, BubbleEntry | undefined>> = {
  bang: { zh: "驚嘆號", ow: 0, src: "b8:b_bang（同形換近黑墨）", use: [["ambush", "danger"], ["villager", "quest"]], d: buBangArt },
  coin: { zh: "金幣", ow: 1, base: "b_coin", use: [["caravan", "talk"]], src: "b8:b_coin" },
  scroll: { zh: "卷軸", ow: 1, use: [["friend", "info"]], src: "b7:bar_J（拿掉驚嘆號）", d: buScrollArt },
  sword: { zh: "劍", ow: 1, base: "b_sword", use: [], src: "b4:skeleton.strike" },
  ask: { zh: "問號", ow: 0, src: "b8:b_ask（同形換近黑墨）", use: [], d: buAskArt() },
  rest: { zh: "營火", ow: 1, base: "b_rest", src: "b8:b_rest", use: [] },
  portal: { zh: "源晶", ow: 1, base: "b_portal", use: [], src: "b4:card.source" },
  notes: { zh: "留言", ow: 1, base: "b_notes", use: [], src: "b7:bar_N" },
  warn: { zh: "警告", ow: 1, base: "b_warn", use: [], src: "b7:warn" },
};
/** 泡泡的四種底色（eventArtParts.ts 的 BUBBLE_FILL 原樣）。 */
export const BUBBLE_FILL: Readonly<Record<string, string>> = { quest: "#ffd23a", talk: "#ffffff", danger: "#ff6a5a", info: "#bfe8ff" };

// ---------------- 出圖 ----------------
export interface EventIconOpt { color?: string; value?: number | string | undefined; ow?: number }
const entryOf = (id: string): EventIconEntry => { const e = ICON[id]; if (e === undefined) throw new Error("qIcon/event: unknown id " + id); return e; };
/** 圖樣定義（48 格）。opt.color／opt.value：d20 的顏色與點數。 */
export function def(id: string, opt: EventIconOpt = {}): QDef {
  const e = entryOf(id);
  if (e.grp === "d20") return { d: d20Art(opt.color ?? CREAM), post: d20Num(opt.value) };
  if (e.d10) return { d: b10(e.d10, e.k10 ?? 1.08) };
  return { d: e.d!, pre: e.pre };
}
/** 圖樣本身（不含框）的邊長：圓環 × fill；d20 撐滿；小牌 14。 */
export const glyphPx = (id: string, size: number): number => { const e = entryOf(id); return e.grp === "d20" || e.grp === "badge" ? size : size * (e.fill ?? 0.84); };
/** 只畫圖樣（不含框）：邊長 a 的 canvas（裝置像素 round(a×res)）。≤14px 不包外框（規則 8），外框粗細照顯示大小（規則 1）。沒有畫布時回 null。 */
export const glyph = (id: string, size: number, res = 2, opt: EventIconOpt = {}): HTMLCanvasElement | null => { const a = glyphPx(id, size); return render(def(id, opt), a, res, { ow: opt.ow ?? (a <= 14 ? 0 : outlinePx(size)) }); };
/** 現行 drawChip 的深底圓（框不動，storyIconArt.ts 的 CHIP_BG）。 */
export const CHIP_BG = "#2a241e";
/** 現行 drawChip 的圓環（框不動）：深底圓、圓環線寬 max(1.2, 6%) 描在圓的邊上（一半在外）。回傳線寬。 */
export function ringFrame(ctx: Ctx, s: number, ring: string): number { const lw = Math.max(1.2, s * 0.06); ctx.beginPath(); ctx.arc(s / 2, s / 2, s / 2, 0, TAU); ctx.fillStyle = CHIP_BG; ctx.fill(); ctx.lineWidth = lw; ctx.strokeStyle = ring; ctx.stroke(); return lw; }
/** 畫一個含框的圖示在 (0,0)～(size,size)。ctx 每單位 res 個裝置像素、原點在整數像素上。opt.frame：小牌預設 "none"（只畫圖）；"pill"＝墊一塊小牌的深色底。 */
export function paint(ctx: Ctx, id: string, size: number, res: number, opt: EventIconOpt & { frame?: "none" | "pill" } = {}): void {
  const e = entryOf(id);
  ctx.save();
  if (e.ring !== undefined) {
    const lw = ringFrame(ctx, size, e.ring), a = glyphPx(id, size);
    ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2 - lw / 2, 0, TAU); ctx.clip(); /* 現行裁在 s/2−1；Q 版裁在圓環內緣，圖樣可以貼到環 */
    const g = glyph(id, size, res, opt); if (g) blit(ctx, g, (size - a) / 2, (size - a) / 2, a, res);
  } else {
    if (opt.frame === "pill") { ctx.fillStyle = "#1d1915"; ctx.fillRect(0, 0, size, size); }
    const g = glyph(id, size, res, opt); if (g) blit(ctx, g, 0, 0, size, res);
  }
  ctx.restore();
}
/** 含框的圖示 canvas：顯示邊長 px、內部解析度 res（canvas 邊長 round(px×res)）。 */
export function canvas(id: string, px: number, res = 2, opt: EventIconOpt & { frame?: "none" | "pill" } = {}): HTMLCanvasElement { const cv = blank(Math.round(px * res)), x = ctxOf(cv); x.scale(res, res); paint(x, id, px, res, opt); x.setTransform(1, 0, 0, 1, 0, 0); return cv; }

/** 給資訊面板的「圖樣本身」（需求 2.3；照樣張 infoPanels.js 的 evBare()）：不畫深底圓與色環；px＝圖樣本身的邊長（撐滿畫布），
 *  簡化程度與外框照圖樣本身的大小（≤14 不包外框；外框粗細照「等效圓環」px ÷ fill，同 `glyph`）。小牌 `b_*` 的 fill 當 1。
 *  回傳邊長 round(px×res) 的 canvas（對齊整數像素）；沒有畫布時 null。 */
export function bareGlyph(id: string, px: number, res = 2): HTMLCanvasElement | null {
  const e = entryOf(id), size = e.grp === "badge" ? px : px / (e.fill ?? 0.84), g = glyph(id, size, res);
  if (g === null) return null;
  const cv = blank(Math.round(px * res)), x = ctxOf(cv); x.scale(res, res); blit(x, g, 0, 0, px, res); x.setTransform(1, 0, 0, 1, 0, 0); return cv;
}

/** 小牌、泡泡的 ctx 每單位幾個裝置像素：讀當下的變換（事件插圖照卡寬縮放，需求 3 第 7 點）；讀不到（測試的假 ctx）時 1。 */
export function ctxRes(ctx: Ctx): number {
  const m = typeof ctx.getTransform === "function" ? (ctx.getTransform() as DOMMatrix | undefined) : undefined;
  const a = m?.a, b = m?.b;
  return typeof a === "number" && typeof b === "number" && a > 0 ? Math.hypot(a, b) : 1;
}
/** 事件插圖小牌裡的 Q 版圖示（`BADGE_Q`）：圖示中心 (x,y)、邊長 14；ctx 每單位 res 個裝置像素（原點在整數像素上）。表裡沒有的 icon 回 false。 */
export function drawBadge(ctx: Ctx, icon: string, x: number, y: number, res: number): boolean { const id = "b_" + icon, S = BADGE_AT.s; if (ICON[id]?.grp !== "badge") return false; const g = glyph(id, S, res); if (g) blit(ctx, g, x - S / 2, y - S / 2, S, res); return true; }
/** 小牌的 Q 版表（需求 4 第 4 點：另開一張表）：IconId → 圖示 id。 */
export const BADGE_Q: Readonly<Record<string, string | undefined>> = { sword: "b_sword", coin: "b_coin", ask: "b_ask", rest: "b_rest", bang: "b_bang", warn: "b_warn", portal: "b_portal", notes: "b_notes" };

/** 第⑧b 批：泡泡裡的圖樣定義（48 格）。 */
export function bubbleDef(icon: string): QDef { const e = BUBBLE[icon]; if (e === undefined) throw new Error("qIcon/event: unknown bubble " + icon); return e.base !== undefined ? def(e.base) : { d: e.d!, pre: e.pre }; }
/** 泡泡裡的圖樣 canvas（邊長 14、裝置像素 round(14×res)）。opt.ow 可改外框（開發頁的做法比較用）。 */
export const bubbleGlyph = (icon: string, res = 2, opt: { ow?: number } = {}): HTMLCanvasElement | null => render(bubbleDef(icon), BADGE_AT.s, res, { ow: opt.ow ?? BUBBLE[icon]!.ow });
/** 給 eventArt 的 bubble() 換畫法：圖樣中心 (x, y)（＝bubble 呼叫 ICON 的位置 (x, y−15)）、邊長 14；ctx 每單位 res 個裝置像素。表裡沒有的 icon 回 false。 */
export function drawBubble(ctx: Ctx, icon: string, x: number, y: number, res: number, opt: { ow?: number } = {}): boolean { const S = BADGE_AT.s; if (BUBBLE[icon] === undefined) return false; const g = bubbleGlyph(icon, res, opt); if (g) blit(ctx, g, x - S / 2, y - S / 2, S, res); return true; }
export const bubbleList = (): { id: string; entry: BubbleEntry }[] => Object.entries(BUBBLE).filter((kv): kv is [string, BubbleEntry] => kv[1] !== undefined).map(([id, e]) => ({ id, entry: e }));
/** 清單（開發頁用）。 */
export const list = (grp?: EventGroup): { id: string; entry: EventIconEntry }[] => Object.entries(ICON).filter((kv): kv is [string, EventIconEntry] => kv[1] !== undefined && (!grp || kv[1].grp === grp)).map(([id, e]) => ({ id, entry: e }));
