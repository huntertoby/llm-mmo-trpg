// qIconsKeywords.js：「小圖示改 Q 版」第⑤b 批——裝備圖示上的關鍵字小圖樣（12 個：元素 4＋非元素 8）（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節；紀錄：docs/art/Q版小圖示-第5b批關鍵字.md；樣張頁：q-icons-keywords.html。
// 角落的關鍵字小圓章：染關鍵字色的深色圓底（外圈 1 裝置像素外框色）＋Q 版圖樣（圖樣全部直接呼叫第 3～5 批已畫的形）。
// C 版（使用者 2026-11-12 選 C）：只畫一個圓章（第一個關鍵字）；還有別的關鍵字時，圓章旁邊加一個點版記號（使用者選 B：牌裡是第二個關鍵字色的點）。
// 右上角留給稀有度色塊與作用端，不放。
// ---------------------------------------------------------------------------------------------
// Phase QI-4a：由 docs/art/sample/qIconsKeywords.js（07d85471 之後）逐行搬成 TypeScript（需求 docs/art/Q版小圖示-關鍵字移植需求.md 第 3 節；
// 規格 docs/phases/PhaseQI-4計畫.md A1）。**4a 還沒接到遊戲畫面**（`gearIcon.ts` 換關鍵字層是 QI-4b）。
// 和樣張不同的地方（都不改畫法）：
// - 依賴改 import：元素道具 `ELEMENT`、記號 `ACT` 從 `./skills`；部件 `entry`、`BOX` 從 `./parts`；`render`、`blit`、`outlinePx`、`blank`、`ctxOf`、
//   `rr`／`f`／`poly`／`starPts`、`OUT`、`TAU`、`mix` 從 `./core`（`mix` 就是 `color.ts` 那一份）。
// - 關鍵字色一律用 `palette.ts` 的 `KEYWORD_COLOR`，不搬樣張的 `KC`（值逐筆相同，`qIconKeywords.test.ts` T-A1 鎖住）。
// - `LIST` 裡元素道具與記號改成「畫的時候才查表」（`QS.ELEMENT[id]`、`QS.ACT[id]`），不在載入時取 `.d`：QI-4b 由 `gearIcon.ts` import 這個檔，
//   而 `skills.ts` 也 import `gearIcon.ts`，載入時取值會撞到還沒初始化的表。呼叫順序與參數和樣張相同。
// - 只搬點版（使用者選 B）：記號樣式只有 `kwdot`，不搬 `MORE_STYLES`／`MORE_STYLE`／`MARK`／`setMark`／`styleOf` 與 `dot`／`plus`／`stack`／`pill` 的分支；
//   不搬第 3 版「>36px 斜放單把畫兩個圓章」（`ONE_MAX_PX`、`TWO_DIAG`、`twoDiagOf`、`count`、`opt.one`／`opt.v3`／`opt.cs`／`opt.maxKw`／`opt.min`／`opt.ratio`），
//   `paint` 一律只畫一個圓章（`count` 恆為 1，和樣張預設相同）；`MORE_DIR` 只留採用的 `edge`（`side`／`diag` 與 `opt.moreDir` 是試做）。
// - 不搬：`KC`、`ELEMENT_KW`、`coverOf`／`coverMemo`／`CORNERS`（自查用）、`areas`、`geom` 的環（`opt.ring`）、`bgOf` 的 `opt.tint`、`chip` 的 `opt.bg`／`opt.gk`、
//   `glyph` 的 `opt.ow`、`legacy`／`paintLegacy`（開發頁 `dev/keywordGallery.ts` 另抄一份給「現行」對照）。
// - 造型的查法：樣張收 `def`（`qWeaponDef`／`qArmorDef` 的結果，讀 `meta.r` 與 `meta.diag`）；這裡另收 `{ kind, form, diag }`（給 4b 直接傳 `resolveGear` 的結果），
//   有 `def` 時以 `def` 為準。兩者都沒有時和樣張「沒給 def」相同（右下、記號照 `edge`）。
// - `chipCanvas(kw, px, res)`：單獨一個圓章的畫布（樣張是 `(kw, px, zoom, o)`；放大交給開發頁的 CSS）；沒有畫布時回 null。
// - 樣張 `LIST.zh` 寫「高地」「召喚」，內容 `skill_keywords.yaml` 是「高處」「召喚物」——這裡的 `zh` 只給開發頁當標籤，說明框以內容為準（QI-4b）。
// ---------------------------------------------------------------------------------------------
import { KEYWORD_COLOR } from "../palette";
import { blank, blit, ctxOf, f, ICON_RES, mix, OUT, outlinePx, poly, qCanvasAvailable, render, rr, starPts, TAU, type Ctx, type DrawFn } from "./core";
import { BOX, entry } from "./parts";
import * as QS from "./skills";

/** 畫在 48 格的既有圖樣：縮到 ±10 單位的座標裡（同 qIconsParts.js 的 from48）。 */
const from48 = (d: DrawFn, k = 0.47): DrawFn => (c, o) => { c.save(); c.scale(k, k); c.translate(-24, -24); d(c, { ...o, small: true }); c.restore(); };
/** 第 3 批的元素道具（畫的時候才查表，見檔頭）。 */
const el = (id: string): DrawFn => from48((c, o) => QS.ELEMENT[id]!.d(c, o));
const part = (cat: string, id: string): DrawFn => (c, o) => entry(cat, id).d(c, o);
const act = (id: string): DrawFn => (c, o) => QS.ACT[id]!.d(c, o, QS.ACT[id]!.def ?? ["#ffd23f", "#ffffff"]);
/** 第 2 版：撞擊在圖樣 ≤14px（圓章 13、18——裝備格 32、背包格 42）只留一個主體（規則 8）：撞上石牆、炸開的一顆大撞擊星，三角拿掉。
 *  同題材（第 4 批觸發「造成撞擊後」的牆與撞擊星，色與形照抄：qIconsParts.js 的 wall()、burstStar()，那兩個沒有匯出），>14px 照舊呼叫第 4 批。
 *  ≤14px 不包外框，星和牆靠亮度分：牆用暗石色（STONE_D）、左緣一條亮石邊，星是亮黃＋白芯，壓在牆的左緣上。
 *  第 3 版（複審：和倒地都是一顆大黃星）：牆加厚到右半個圓（寬 9.6），星縮小（外徑 9.4→7.8）、往左上移到牆左緣的上半——主體變成「牆」，和倒地「大星壓在地面上」拉開。題材不變。
 *  QI-4a：放在這個檔、不動 `parts.ts` 的 `on_collision`（需求第 4 節第 2 點；技能組裝列 18px 的撞擊部件圓片與 QI-2d 基準不變）。 */
export const COLLIDE_STONE_D = "#8c8474", COLLIDE_STONE_L = "#ece6d6";
export const collision: DrawFn = (c, o) => {
  if (!o.tiny) { entry("trigger", "on_collision").d(c, o); return; }
  rr(c, COLLIDE_STONE_D, 0.8, -10.4, 9.6, 20.8, 1.6); f(c, COLLIDE_STONE_L, () => c.rect(0.8, -9.4, 2, 18.8));
  poly(c, "#ffd23f", starPts(-2.4, -2.8, 7.8, 3.7, 7, -1.2), 0.3); poly(c, "#ffffff", starPts(-2.4, -2.8, 3.7, 1.9, 7, -1.2));
};
export interface KeywordArt { zh: string; topic: string; src: string; k: number; d: DrawFn }
/** 12 個關鍵字（順序同 gearAppearance.json 的 keywords）。k＝圖樣在圓章裡再縮放（方的、四角有東西的收進環內）；src＝沿用哪一批的哪個形。 */
export const LIST: Readonly<Record<string, KeywordArt | undefined>> = {
  ignite: { zh: "點燃", topic: "火焰（橘外焰、黃內焰、白芯）", src: "b3:el:fire＝b4:element.fire", k: 1.04, d: el("fire") },
  wet: { zh: "潮濕", topic: "水滴落在兩道波浪上（藍、淺藍、白芯）", src: "b3:el:water", k: 0.85, d: el("water") },
  charged: { zh: "帶電", topic: "黃閃電（黃、橘暗面、白亮邊）", src: "b3:el:lightning＝b4:element.lightning", k: 1.02, d: el("lightning") },
  frozen: { zh: "冰凍", topic: "三根冰晶（淡藍、深藍暗面、白亮面）", src: "b3:el:ice＝b4:element.ice", k: 1, d: el("ice") },
  prone: { zh: "倒地", topic: "黃色撞擊星壓在地面線上", src: "b3:knockdown＝b4:effect.knock_prone", k: 0.74, d: act("knockdown") },
  collision: { zh: "撞擊", topic: "米白三角撞上右邊的石牆，中間一顆撞擊星（圖樣 ≤14px：只留石牆＋撞上去的大撞擊星）", src: "b4:trigger.on_collision（≤14px 簡化形）", k: 0.76, d: collision },
  marked: { zh: "標記", topic: "紅色準星", src: "b3:mark＝b4:status.marked＝b5:marked", k: 0.85, d: act("mark") },
  high_ground: { zh: "高地", topic: "一座淺石色的山（左坡米白亮面），山頂一個米白小人頭；圖樣 >14px 右上多一個黃箭頭", src: "b4:condition.height_advantage", k: 0.73, d: part("condition", "height_advantage") },
  concealed: { zh: "隱蔽", topic: "紫色兜帽，裡面兩道發亮的斜眼", src: "b4:status.concealed＝b5:concealed", k: 0.84, d: part("status", "concealed") },
  summon: { zh: "召喚", topic: "青色小靈", src: "b3:summon＝b4:effect.summon", k: 1, d: act("summon") },
  poisoned: { zh: "中毒", topic: "綠毒滴，右上一顆泡", src: "b3:el:poison＝b4:status.poison＝b5:poison", k: 0.96, d: part("status", "poison") },
  form: { zh: "形態", topic: "淡紫色的獸掌印", src: "b4:effect.enter_form", k: 0.94, d: part("effect", "enter_form") },
};
export const KEYS: readonly string[] = Object.keys(LIST);
/** 只有圖樣的 canvas：cpx＝圖樣本身（±10 單位）顯示的 CSS px；≤14px 不包外框（規則 8）。 */
export function glyph(kw: string, cpx: number, res = ICON_RES): HTMLCanvasElement | null {
  const e = LIST[kw]!; return render({ d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 }); c.restore(); } }, cpx * BOX, res, { ow: cpx <= 14 ? 0 : outlinePx(cpx) });
}
/** 圓章的大小（CSS px）：裝備格邊長的 0.42（32→13.5、42→17.5、48→20、64→27，真 1 倍取整數），對齊整數裝置像素。 */
export const RATIO = 0.42, MARGIN = 3.6 / 64; /* 離格邊：現行框線（2～62、線寬 2.5）內緣以內 */
export const sizeOf = (S: number, res: number): number => Math.round(S * RATIO * res) / res;
/** 圓章的幾何：最外一圈 1 個裝置像素的外框色；沒有環；圖樣收在內緣以內。 */
const geom = (D: number, res: number): { ow: number; inner: number } => { const ow = 1 / res, inner = D - 2 * ow; return { ow, inner }; };
/** 圓底：深色混 28% 關鍵字色（第二色 #191b22 佔 72%）。 */
export const bgOf = (kw: string): string => mix(KEYWORD_COLOR[kw]!, "#191b22", 0.72);
/** 在 (x0,y0) 左上角畫一個直徑 D 的關鍵字圓章（ctx 每單位＝1 CSS px、已乘 res；x0、y0 要在整數裝置像素上）。不認得的關鍵字不畫。 */
export function chip(ctx: Ctx, kw: string, x0: number, y0: number, D: number, res: number): void {
  const e = LIST[kw]; if (!e) return; const { ow, inner } = geom(D, res), cx = x0 + D / 2, cy = y0 + D / 2;
  ctx.save();
  ctx.fillStyle = OUT; ctx.beginPath(); ctx.arc(cx, cy, D / 2, 0, TAU); ctx.fill();
  ctx.fillStyle = bgOf(kw); ctx.beginPath(); ctx.arc(cx, cy, D / 2 - ow, 0, TAU); ctx.fill();
  ctx.restore();
  const cpx = inner * e.k, g = glyph(kw, cpx, res), a = cpx * BOX;
  if (g) blit(ctx, g, cx - a / 2, cy - a / 2, a, res);
}
/** 只留認得的關鍵字（同遊戲端 resolveGear：KEYWORD_COLOR 認得的、前 2 個）。 */
export const known = (kws: readonly string[] | null | undefined, max = 2): string[] => (kws ?? []).filter((k) => LIST[k] !== undefined).slice(0, max);
export type Corner = "br" | "tl" | "bl";
/** 角的左上座標（CSS px，對齊整數裝置像素）：右下 (far, far)、左上 (near, near)、左下 (near, far)。 */
export const at = (corner: Corner, size: number, D: number, res: number): [number, number] => { const m = size * MARGIN, snap = (v: number) => Math.round(v * res) / res, far = snap(size - m - D), near = snap(m); return [corner[1] === "r" ? far : near, corner[0] === "b" ? far : near]; };
/** 例外表（照樣張原表）：右下會蓋到主圖最好認的那一頭的款，直接寫要放的角。先找 kind/form，再找 kind；沒列的右下。
 *  陣列是樣張第 3 版的「第一個、第二個」角；C 版只畫一個圓章，只用第一個。理由與 --audit keywords 的數字見樣張註解。 */
export const KEY_CORNER: Readonly<Record<string, readonly Corner[] | undefined>> = {
  axe: ["tl"], /* 斧刃在右下（手斧右下蓋作用端 11%、戰斧 16%）；左上是柄頭外的空處。雙刃斧兩片刃上下對稱，同一種一起放左上 */
  "hammer/flail": ["bl"], /* 錘頭甩在右下（右下蓋作用端 39%），左上也擦到鍊（5%）→ 左下的握把 */
  "scythe/crescent": ["tl"], /* 月牙刃在右下（22%） */
  bow: ["bl"], /* 弓臂伸到右下、左上兩個角（各蓋 15～19%）→ 左下的握把 */
  crossbow: ["bl"], /* 同弓：弩臂在右下、左上 → 左下的弩托 */
  shoes: ["tl"], boots: ["tl"], iron_boots: ["tl"], greaves: ["tl"], /* 鞋尖朝右下（右下蓋 70%～94%）→ 左上的鞋筒口（四種鞋同一個角） */
  pendant: ["tl"], /* 墜子（寶石）在右下 → 左上的鍊子 */
  "circlet/bandana": ["bl"], /* 第 3 版（複審必修）：右下垂的頭巾結是唯一的辨識點，右下蓋掉後讀成圓頂帽 → 左下（6.9%） */
  cloth_gloves: ["bl"], leather_gloves: ["bl"], gauntlets: ["bl"], /* 第 3 版（複審可修）：右下壓掌根與拇指（28%～31.5%）→ 左下只蓋護腕下緣（15%～19%），拇指留著 */
  "charm/bone": ["bl"], /* 看圖加的：大獠牙的尖朝右下（右下蓋 22%、蓋掉牙尖）→ 左下的小獠牙（9%） */
  "dual_dagger/short": ["br"], "dual_dagger/stiletto": ["br"], /* 必修 1：X 交叉，左上是後面那把的刃，不放；右下蓋前面那把的握把 */
  "dual_pistol/flintlock": ["br"], "dual_pistol/revolver": ["br"], "dual_pistol/derringer": ["br"], /* 必修 2：同上，左上是左邊那把的槍口 */
  whip: ["br"], /* 斜放單把，但甩出去的鞭梢在左上（左上蓋作用端 22%～30%） */
  "longgun/sniper": ["br"], /* 斜放單把，但槍管長到左上（左上蓋作用端 24%） */
};
/** 造型：`def`（`qWeaponDef`／`qArmorDef` 的結果）優先，否則用 `kind`／`form`／`diag`。 */
export interface KeywordLook {
  def?: { meta?: { diag?: boolean; r?: { kind: string; form: string } } } | null | undefined;
  kind?: string | null | undefined;
  form?: string | null | undefined;
  diag?: boolean | undefined;
}
const lookOf = (opt: KeywordLook): { kind?: string | null | undefined; form?: string | null | undefined } => opt.def?.meta?.r ?? { kind: opt.kind, form: opt.form };
const hasLook = (opt: KeywordLook): boolean => !!opt.def || opt.kind != null;
/** 斜放的單把長條（meta.diag 與長槍、霰彈槍）。 */
export const isDiag = (opt: KeywordLook): boolean => { const r = lookOf(opt); return !!(opt.def ? opt.def.meta?.diag : opt.diag) || r.kind === "longgun" || r.kind === "shotgun"; };
/** 這一款的圓章放哪幾個角（C 版只用第一個）：例外表 → 斜放單把 [br, tl] → 其他 [br]；沒給造型 [br, tl]（同樣張）。 */
export function cornersOf(opt: KeywordLook = {}): readonly Corner[] {
  if (!hasLook(opt)) return ["br", "tl"]; const r = lookOf(opt);
  return KEY_CORNER[r.kind + "/" + r.form] ?? KEY_CORNER[r.kind ?? ""] ?? (isDiag(opt) ? ["br", "tl"] : ["br"]);
}
/* ---------------------------------------------------------------- C 版記號（點版）：
 * 記號貼在圓章外緣、沿著格子的左右邊朝格子中段（MORE_DIR.edge）：右下、左下的圓章記號在它正上方，左上的在它正下方——
 * 不往右上（稀有度色塊）、不往圖的正中間、不沿下緣往另一個角。兩條例外：45° 斜放的長條右下圓章 → 記號改放圓章左邊（MORE_DIR_DIAG）；看圖加的例外表 MORE_DIR_KIND。 */
type Dir = readonly [number, number];
/** 記號往哪個方向貼（單位向量，CSS px 座標 +y 向下）。只留採用的 edge（樣張的 side、diag 是試做）。 */
export const MORE_DIR: Readonly<{ edge: Readonly<Record<Corner, Dir>> }> = {
  edge: { br: [0, -1], bl: [0, -1], tl: [0, 1] }, /* 採用：沿左右格邊——右下→正上方（右緣中段）、左下→正上方（左緣中段）、左上→正下方（左緣中段） */
};
/** 記號方向的例外表（kind/form 或 kind → 單位向量）：手套 → 圓章右邊（護腕上）；卷軸匣、寬簷帽 → 圓章左邊。 */
export const MORE_DIR_KIND: Readonly<Record<string, Dir | undefined>> = { cloth_gloves: [1, 0], leather_gloves: [1, 0], gauntlets: [1, 0], "tome/scroll": [-1, 0], "hat/wide": [-1, 0] };
/** 斜放的長條、圓章在右下時：記號放圓章左邊（握把那一側）。 */
export const MORE_DIR_DIAG: Dir = [-1, 0];
/** 這一款的記號方向：例外表 → 斜放長條的右下 → edge。 */
export const moreDirOf = (corner: Corner, opt: KeywordLook = {}): Dir => { const r = lookOf(opt), t = MORE_DIR_KIND[r.kind + "/" + r.form] ?? MORE_DIR_KIND[r.kind ?? ""];
  return t ?? (corner === "br" && hasLook(opt) && isDiag(opt) ? MORE_DIR_DIAG : MORE_DIR.edge[corner]); };
export const MORE_CREAM = "#f2e6c8", MORE_DARK = "#191b22";
/** 記號的邊長（裝置像素，整數）：圓章直徑的 0.42，偶數減 1，最小 7。 */
export function moreSize(D: number, res: number): number { const v = Math.round(D * res * 0.42); return Math.max(7, v % 2 ? v : v - 1); }
/** 記號的位置與大小（CSS px；左上角對齊整數裝置像素）：只疊進圓章 2 個裝置像素，夾在格內（離格邊 MARGIN）。 */
export function moreBox(corner: Corner, x0: number, y0: number, D: number, size: number, res: number, opt: KeywordLook = {}): { s: number; G: number; w: number; h: number; x: number; y: number } {
  const [dx, dy] = moreDirOf(corner, opt), u = 1 / res, snap = (v: number) => Math.round(v * res) / res, m = size * MARGIN;
  const clamp = (v: number, sz: number) => Math.min(Math.max(v, snap(m)), snap(size - m) - sz);
  const s = moreSize(D, res), G = s - 2 <= 3 ? s - 2 : s - 4;
  const w = s * u, h = s * u, cx = x0 + D / 2, cy = y0 + D / 2;
  const r = D / 2 + Math.max(w, h) / 2 - 2 * u; /* 中心離圓心：圓章半徑＋記號半邊−2 個裝置像素 */
  return { s, G, w, h, x: clamp(snap(cx + dx * r - w / 2), w), y: clamp(snap(cy + dy * r - h / 2), h) };
}
/** 在圓章 (x0,y0,D) 旁邊畫「還有」的點版記號：深底小圓牌（外框色一圈）＋第二個關鍵字色（原色）的實心點；不認得時米白。畫在圓章之後。 */
export function more(ctx: Ctx, corner: Corner, x0: number, y0: number, D: number, size: number, res: number, kw2: string | undefined, opt: KeywordLook = {}): void {
  const u = 1 / res;
  ctx.save();
  const { s, G, x: mx, y: my, w, h: hgt } = moreBox(corner, x0, y0, D, size, res, opt);
  const pill = (fill: string, inset: number) => { const r = (hgt - 2 * inset) / 2; ctx.fillStyle = fill; ctx.beginPath(); ctx.roundRect(mx + inset, my + inset, w - 2 * inset, hgt - 2 * inset, r); ctx.fill(); };
  pill(OUT, 0); pill(MORE_DARK, u);
  /* 點版：第二個關鍵字色（KEYWORD_COLOR 原色，不混白）的實心點，直徑＝G；G≤4（真 1 倍 7px 牌的 3px）畫成整數像素的方點，較大時畫圓 */
  const o = (s - G) / 2; ctx.fillStyle = (kw2 !== undefined ? KEYWORD_COLOR[kw2] : undefined) ?? MORE_CREAM;
  if (G <= 4) ctx.fillRect(mx + o * u, my + o * u, G * u, G * u); else { ctx.beginPath(); ctx.arc(mx + (s / 2) * u, my + (s / 2) * u, (G / 2) * u, 0, TAU); ctx.fill(); }
  ctx.restore();
}
/** 裝備格上的關鍵字層：size＝裝備格邊長（CSS px），ctx 每單位＝1 CSS px、已乘 res（原點在整數裝置像素上）。
 *  只畫一個圓章（第一個認得的關鍵字，角＝cornersOf(opt)[0]）；還有別的關鍵字時在圓章旁邊加點版記號（點色＝第二個）。
 *  `keywords` 由呼叫端先過 `resolveGear`；不認得的、空陣列、null 不畫。畫不畫（px ≥ 32）由呼叫端決定（QI-4b）。 */
export function paint(ctx: Ctx, keywords: readonly string[] | null | undefined, size: number, res: number, opt: KeywordLook = {}): void {
  const kws = known(keywords); if (!kws.length) return;
  const D = sizeOf(size, res), corner = cornersOf(opt)[0]!, [x0, y0] = at(corner, size, D, res);
  chip(ctx, kws[0]!, x0, y0, D, res);
  if (kws.length > 1) more(ctx, corner, x0, y0, D, size, res, kws[1], opt);
}
/** 單獨一個圓章的 canvas（px 邊長、圓章撐滿；畫布 round(px × res) 裝置像素）。沒有畫布時回 null。 */
export function chipCanvas(kw: string, px: number, res = ICON_RES): HTMLCanvasElement | null {
  if (!qCanvasAvailable()) return null; const cv = blank(Math.round(px * res)), x = ctxOf(cv); x.scale(res, res); chip(x, kw, 0, 0, px, res); return cv;
}
