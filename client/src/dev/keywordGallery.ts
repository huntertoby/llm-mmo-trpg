// 開發用：裝備關鍵字小圓章（Q 版第⑤b 批，Phase QI-4a）。開 `client/dev/keyword-gallery.html`（自己的 vite 後 /dev/keyword-gallery.html?mute=1）。不屬於正式 build。
// 規格 docs/phases/PhaseQI-4計畫.md A2、A6、第 8.2 節；需求 docs/art/Q版小圖示-關鍵字移植需求.md 第 5 節。
// 預設每格＝遊戲端 `drawGear` 的框與主圖（`chips = false`：不畫關鍵字層；元素混色、寶石色照舊）＋`qIcon/keywords.ts` 的 `paint`（頁內組合，4a 起）。
// QI-4b 起遊戲端已接上：`&live=1` 改走遊戲端 `gearIconCanvas`（≥ 32px 才畫關鍵字層；3 個關鍵字的格子遊戲端只會畫前 2 個，照舊頁內組合）。
// 款式清單＝`gearAppearance.json` 的 `kinds`（武器、副手、防具、飾品 105 款；和 weaponicon-gallery、gear-gallery 同一個來源，不複製清單）。
// 參數：
//   ?px=<CSS px,…>      裝備格邊長，可逗號多個（預設 32；set=chips 是圓章直徑，沒給時 13,18,20,27）
//   &res=<1|2,…>        內部解析度，可逗號多個（預設 2＝遊戲；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>           放大 k 倍顯示（image-rendering: pixelated，最近鄰）；截圖用裝置像素比 1 拍
//   &rarity=<稀有度>     全部款式套這個稀有度（預設 common；bag、dots 自己輪流五種）
//   &set=<名稱,…>       逗號接多段：
//        bag      背包模擬 16 件（照樣張 ?part=bag 的清單：一或兩個關鍵字、五種稀有度輪流），8 欄
//        all      105 款總表，每款兩個關鍵字（點燃＋標記，同樣張 ?part=c）；可配 &from=&n= 分張（預設）
//        chips    16 個圓章本身（直徑 13／18／20／27；撞擊 13、18 是簡化形；同樣張 ?part=true1x 的圓章；KW-3 起含連擊、怒氣、專注、氣）
//        hud      KW-3：HUD 層數計量（四種 × 0～滿層；`render/qIcon/stackGauge.ts`，和遊戲端 `StackPips` 同一張畫布）
//        cond     KW-3：條件部件「層數達 N」（圓片 30／26／18／16；`parts.ts` 的 chipCanvas，同技能圖示開發頁）
//        hash     KW-3：新圖指紋（照樣張 q-icons-kw.html?part=hash 的算法與格式，只列 A 案），結果放 `body.dataset.hash`；和 docs/art/KW樣張.md 第 7 節逐字比
//        dots     點版：12 種點色 × 五種稀有度（每列：直劍 32、半身板甲 32、長靴 32、寶石戒 42、鳶盾 42；同樣張 ?part=dots，忽略 &px）
//        corner   例外表的款（KEY_CORNER 或記號方向例外表 MORE_DIR_KIND 列到的：斧、連枷、彎月鐮、弓、弩、四種鞋、墜、骨符、頭巾、手套、雙匕首、
//                 雙手槍、鞭、狙擊槍、卷軸匣、寬簷帽），每款兩個關鍵字；標籤寫角與記號方向
//        count    一個、兩個、三個關鍵字（三個和兩個同一個記號；遊戲端最多 2 個，3 個只在這裡畫）
//        legacy   現行對照：左＝現行接法（Q 版圖＋舊 motif() 疊在 meta.spots，>36px 才畫；頁內抄樣張 legacy()／paintLegacy()），右＝Q 版圓章
//        compare  和樣張逐像素比（見下），結果放 `body.dataset.compare`（JSON）
//        live     QI-4b：頁內組合 vs 遊戲端 `gearIconCanvas` 逐像素比（105 款 × 兩個關鍵字（6 組輪流）× `&px=`（預設 32,42,48,64）× `&res=`（預設 1,2）），
//                 結果放 `body.dataset.live`（JSON：每組 total／same／diffs）
//   &from=<i>&n=<k>     set=all、corner 只列第 i 款起的 k 款
//   &label=0            不顯示名稱
//   &live=1             QI-4b：格子改走遊戲端 `gearIconCanvas`（複製一份貼上，不縮放）
//   &sample=<網址>       set=compare 用：樣張 docs/art/sample/ 的網址（靜態伺服器要帶 CORS）。載入 qIcons.js、qIconsWeapons.js、qIconsArmor.js、qIconsSkills.js、
//                       qIconsParts.js、qIconsStatus.js、qIconsKeywords.js（載入前把 qIcons.js 的 M 換成 core.ts 的 M、qIconsWeapons.js 的 MAT 鐵鋼銅換成
//                       material.ts，同 status-gallery）；兩邊交錯著畫「只有關鍵字層」的畫布（105 款 × 兩個關鍵字（6 組輪流）× 32／42／48／64 × res）
//                       與 12 個圓章 × 13／18／20／27 × res，getImageData 逐像素比。`&px=`、`&res=` 照樣可縮小範圍（預設 32,42,48,64 與 1,2）
// 畫好後 `body.dataset.ready = "1"`。另外掛 `window.__qiKwDev`：paint、chip（＝chipCanvas）、list（105 款）、layer(look, kws, px, res)（只有關鍵字層的畫布）、
// gauge(id, n, res)（KW-3 層數計量畫布）、hash()（KW-3 指紋行）。
import appearance from "../render/gearAppearance.json";
import type { Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { drawGear, gearIconCanvas, gearQDef, resolveGear, type GearLook } from "../render/gearIcon";
import { MATERIAL } from "../render/material";
import { KEYWORD_COLOR } from "../render/palette";
import { M as CORE_M } from "../render/qIcon/core";
import * as K from "../render/qIcon/keywords";
import * as QP from "../render/qIcon/parts";
import * as SG from "../render/qIcon/stackGauge";

interface Form { id: string; zh: string }
interface Kind { id: string; slotType: string; zh: string; forms: Form[] }
interface Item { look: GearLook; label: string }

const q = new URLSearchParams(location.search);
const list = (k: string, d: string): string[] => (q.get(k) ?? d).split(",").filter((s) => s !== "");
const PXS = list("px", "32").map(Number);
const RESS = list("res", "2").map(Number);
const ZOOM = Number(q.get("zoom") ?? 1);
const RARITY = q.get("rarity") ?? "common";
const SETS = list("set", "all");
const FROM = Number(q.get("from") ?? 0);
const N = Number(q.get("n") ?? 9999);
const LABEL = q.get("label") !== "0";
const LIVE = q.get("live") === "1";
const RARS = ["common", "uncommon", "rare", "epic", "legendary"];
/** 裝備外觀的 12 個關鍵字（KW-3 起 `K.KEYS` 多了四個層數關鍵字，裝備不帶；點版、和樣張比都只用這 12 個）。 */
const GEAR_KWS = appearance.keywords as string[];
/** KW-3 的四個層數關鍵字（樣張 qIconsKW.js 的 KEYS 順序）。 */
const STACK_KWS = ["combo_point", "fury", "focus", "ki"] as const;

const KINDS = appearance.kinds as unknown as Kind[];
/** 105 款（kind × form）。 */
const ALL: Item[] = KINDS.flatMap((k) => k.forms.map((f) => ({ look: { kind: k.id, form: f.id, rarity: RARITY }, label: `${k.zh}・${f.zh}` })));
const withKw = (look: GearLook, keywords: readonly string[]): GearLook => ({ ...look, keywords });
const resLabel = (res: number): string => (res === 1 ? "真 1 倍" : "DPR 2");
const zoomLabel = ZOOM !== 1 ? `・最近鄰 ×${ZOOM}` : "";

// ---------------- 畫法 ----------------
/** 造型（`keywords.paint` 的 `def`）：遊戲端 `gearQDef` 的結果（武器帶 `meta.diag`、`meta.r`）。 */
const defOf = (look: GearLook): K.KeywordLook["def"] => gearQDef(look, resolveGear(look)) as unknown as K.KeywordLook["def"];
/** 只有框與主圖（遊戲端 `drawGear`，`chips = false` 不畫關鍵字層）的裝備格畫布。 */
function bare(look: GearLook, px: number, res: number): HTMLCanvasElement {
  const cv = document.createElement("canvas");
  cv.width = cv.height = Math.round(px * res);
  const x = cv.getContext("2d")!;
  x.scale((px * res) / 64, (px * res) / 64);
  x.lineJoin = "round";
  drawGear(x, look, false, undefined, px, res);
  return cv;
}
/** 遊戲端 `gearIconCanvas` 的複本（快取的畫布不能在頁上放兩次；同尺寸 `drawImage`，不縮放）。 */
function live(look: GearLook, px: number, res: number): HTMLCanvasElement {
  const src = gearIconCanvas(look, px, undefined, res)!, cv = document.createElement("canvas");
  cv.width = src.width; cv.height = src.height; cv.getContext("2d")!.drawImage(src, 0, 0);
  return cv;
}
/** 裝備格：框與主圖＋Q 版關鍵字層（頁內組合）。`kws` 沒給時用 `resolveGear(look).keywords`（遊戲端的規則：認得的、最多 2 個）；`&live=1` 且沒給 `kws` 時改走遊戲端。 */
function gear(look: GearLook, px: number, res: number, kws?: readonly string[]): HTMLCanvasElement {
  if (LIVE && kws === undefined) return live(look, px, res);
  const cv = bare(look, px, res), x = cv.getContext("2d")!;
  x.setTransform(res, 0, 0, res, 0, 0);
  K.paint(x, kws ?? resolveGear(look).keywords, px, res, { def: defOf(look) });
  return cv;
}
/** 只有關鍵字層（透明底）的畫布：和樣張逐像素比用。 */
function layer(look: GearLook, kws: readonly string[], px: number, res: number): HTMLCanvasElement {
  const cv = document.createElement("canvas");
  cv.width = cv.height = Math.round(px * res);
  const x = cv.getContext("2d")!;
  x.scale(res, res);
  K.paint(x, kws, px, res, { def: defOf(look) });
  return cv;
}

// ---------------- 現行（舊 motif()，照樣張 qIconsKeywords.js 的 legacy()／paintLegacy() 原樣抄；4b 刪掉遊戲端的 motif() 之後這裡仍可對照） ----------------
const TAU = Math.PI * 2;
function legacy(ctx: CanvasRenderingContext2D, kw: string, x: number, y: number): void {
  const kc = KEYWORD_COLOR[kw]; if (kc === undefined) return; ctx.save(); ctx.fillStyle = kc; ctx.strokeStyle = kc; ctx.lineWidth = 1.6; ctx.lineCap = "round";
  switch (kw) {
    case "ignite": ctx.beginPath(); ctx.moveTo(x, y - 6); ctx.quadraticCurveTo(x + 4.5, y, x, y + 3); ctx.quadraticCurveTo(x - 4.5, y, x, y - 6); ctx.fill(); break;
    case "wet": ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.quadraticCurveTo(x + 4, y + 1, x, y + 3); ctx.quadraticCurveTo(x - 4, y + 1, x, y - 5); ctx.fill(); break;
    case "charged": ctx.beginPath(); ctx.moveTo(x - 3, y - 5); ctx.lineTo(x + 1, y - 1); ctx.lineTo(x - 1, y + 1); ctx.lineTo(x + 3, y + 5); ctx.stroke(); break;
    case "frozen": ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = (i * Math.PI) / 3; ctx.moveTo(x - Math.cos(a) * 4.5, y - Math.sin(a) * 4.5); ctx.lineTo(x + Math.cos(a) * 4.5, y + Math.sin(a) * 4.5); } ctx.stroke(); break;
    case "prone": ctx.beginPath(); ctx.moveTo(x - 4, y - 2); ctx.lineTo(x, y + 2); ctx.lineTo(x + 4, y - 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
    case "collision": ctx.beginPath(); for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU, r = i % 2 ? 2 : 5; ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } ctx.closePath(); ctx.fill(); break;
    case "marked": ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x - 4, y); ctx.moveTo(x + 4, y); ctx.lineTo(x + 6, y); ctx.moveTo(x, y - 6); ctx.lineTo(x, y - 4); ctx.moveTo(x, y + 4); ctx.lineTo(x, y + 6); ctx.stroke(); break;
    case "high_ground": ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x, y - 3); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
    case "concealed": ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(x - 2, y, 2.6, 0, TAU); ctx.arc(x + 2, y - 1, 3, 0, TAU); ctx.arc(x + 1, y + 2, 2.2, 0, TAU); ctx.fill(); break;
    case "poisoned": ctx.beginPath(); ctx.arc(x, y - 1, 3.2, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.moveTo(x - 2.5, y + 3); ctx.lineTo(x + 2.5, y + 6); ctx.moveTo(x + 2.5, y + 3); ctx.lineTo(x - 2.5, y + 6); ctx.stroke(); break;
    case "form": ctx.beginPath(); for (let i = -1; i <= 1; i++) { ctx.moveTo(x + i * 3 - 1.5, y - 5); ctx.lineTo(x + i * 3 + 1.5, y + 5); } ctx.stroke(); break;
    case "summon": ctx.beginPath(); ctx.arc(x, y - 1, 3.4, Math.PI, 0); ctx.lineTo(x + 3.4, y + 4); ctx.lineTo(x + 1.2, y + 2.5); ctx.lineTo(x, y + 4); ctx.lineTo(x - 1.2, y + 2.5); ctx.lineTo(x - 3.4, y + 4); ctx.closePath(); ctx.fill(); break;
  }
  ctx.restore();
}
/** 現行接法：>36px 才畫，位置用 Q 版的 meta.spots（48 格）換算到格內，motif() 原大（64 單位）；每個關鍵字一處、只有一個時兩處。 */
function legacyGear(look: GearLook, px: number, res: number): HTMLCanvasElement {
  const cv = bare(look, px, res), x = cv.getContext("2d")!, kws = resolveGear(look).keywords, def = gearQDef(look, resolveGear(look));
  if (px <= 36 || !kws.length || !def) return cv;
  x.setTransform(res, 0, 0, res, 0, 0);
  const spots = def.meta.spots, p = px * 0.06, a = px - 2 * p, k = px / 64, at = (kw: string, s: readonly [number, number]) => { x.save(); x.translate(p + (s[0] * a) / 48, p + (s[1] * a) / 48); x.scale(k, k); legacy(x, kw, 0, 0); x.restore(); };
  kws.forEach((kw, i) => at(kw, spots[i % spots.length]!)); if (kws.length === 1 && spots[1]) at(kws[0]!, spots[1]);
  return cv;
}

// ---------------- 版面 ----------------
type Kids = (Node | string)[];
const h = <T extends keyof HTMLElementTagNameMap>(tag: T, props: Partial<HTMLElementTagNameMap[T]> = {}, ...kids: Kids): HTMLElementTagNameMap[T] => { const e = Object.assign(document.createElement(tag), props); e.append(...kids); return e; };
const shown = (cv: HTMLCanvasElement, px: number, k = ZOOM): HTMLCanvasElement => { cv.style.width = cv.style.height = `${px * k}px`; return cv; };
const cell = (label: string, ...cvs: HTMLCanvasElement[]): HTMLElement => h("div", { className: "cell" }, h("div", { className: "icons" }, ...cvs), ...(LABEL ? [h("div", { className: "label", textContent: label })] : []));
const section = (title: string, ...kids: Kids): void => { document.body.append(h("h2", { textContent: title }), ...kids); };
const row = (...kids: Kids): HTMLElement => h("div", { className: "row" }, ...kids);
const kwZh = (kws: readonly string[]): string => kws.map((k) => K.LIST[k]?.zh ?? k).join("＋");

/** 背包模擬 16 件（樣張 q-icons-keywords.html 的 BAG：kind、form、material、keywords；稀有度五種輪流）。 */
const BAG: readonly [string, string, string, readonly string[]][] = [["sword", "straight", "steel", ["ignite", "marked"]], ["axe", "battle", "iron", ["charged", "prone"]], ["bow", "long", "wood", ["frozen", "concealed"]], ["longgun", "flintlock", "steel", ["wet", "summon"]],
  ["staff", "long", "wood", ["poisoned", "form"]], ["dual_dagger", "short", "steel", ["collision", "high_ground"]], ["dual_pistol", "revolver", "steel", ["marked"]], ["kite_shield", "kite", "iron", ["ignite", "wet"]],
  ["orb", "ball", "crystal", ["summon", "charged"]], ["tome", "book", "leather", ["form", "frozen"]], ["helmet", "iron", "iron", ["concealed", "ignite"]], ["plate", "half", "steel", ["prone", "poisoned"]],
  ["leather_gloves", "short", "leather", ["high_ground"]], ["boots", "tall", "leather", ["collision", "marked"]], ["ring", "gem", "gold", ["frozen", "summon"]], ["pendant", "pendant", "gold", ["poisoned", "charged"]]];
/** 兩個關鍵字的 6 組（樣張 PAIRS；比對時輪流配給 105 款，12 個關鍵字都會當第一個與第二個）。 */
const PAIRS: readonly (readonly [string, string])[] = [["ignite", "marked"], ["charged", "prone"], ["frozen", "concealed"], ["wet", "summon"], ["poisoned", "form"], ["collision", "high_ground"]];
const labelOf = (look: GearLook): string => ALL.find((e) => e.look.kind === look.kind && e.look.form === look.form)?.label ?? `${look.kind}/${look.form}`;

function bagSection(): void {
  for (const px of PXS) for (const res of RESS) {
    const looks = BAG.map(([kind, form, material, keywords], i): GearLook => ({ kind, form, material, keywords, rarity: RARS[i % RARS.length] }));
    const grid = h("div", { className: "bag" }, ...looks.map((l) => shown(gear(l, px, res), px)));
    grid.style.gridTemplateColumns = `repeat(8, ${px * ZOOM}px)`;
    section(`背包模擬 16 件：裝備格 ${px}・${resLabel(res)}${zoomLabel}（五種稀有度輪流；雙手槍、皮手套一個關鍵字，其他兩個）`, grid);
    if (LABEL) document.body.append(h("div", { className: "label", textContent: looks.map((l) => `${labelOf(l)}（${kwZh(l.keywords ?? [])}）`).join("、") }));
  }
}
function allSection(): void {
  const items = ALL.slice(FROM, FROM + N);
  for (const px of PXS) for (const res of RESS)
    section(`105 款總表（第 ${FROM + 1}～${FROM + items.length} 款）：點燃＋標記，裝備格 ${px}・${resLabel(res)}${zoomLabel}；標籤＝角`, row(...items.map((e) => { const look = withKw(e.look, ["ignite", "marked"]); return cell(`${e.label} ${K.cornersOf({ def: defOf(look) })[0]}`, shown(gear(look, px, res), px)); })));
}
function chipsSection(): void {
  const ds = q.get("px") === null ? [13, 18, 20, 27] : PXS;
  for (const res of RESS)
    section(`${K.KEYS.length} 個圓章：直徑 ${ds.join("／")}・${resLabel(res)}${zoomLabel}（撞擊 13、18 是簡化形；最後四個是 KW-3 的層數關鍵字）`, row(...K.KEYS.map((kw) => cell(`${K.LIST[kw]!.zh} ${kw}`, ...ds.map((d) => shown(K.chipCanvas(kw, d, res)!, d))))));
}
function dotsSection(): void {
  const items: readonly [string, string, string, number][] = [["sword", "straight", "steel", 32], ["plate", "half", "steel", 32], ["boots", "tall", "leather", 32], ["ring", "gem", "gold", 42], ["kite_shield", "kite", "iron", 42]];
  for (const res of RESS) {
    const rows = GEAR_KWS.map((kw2, r) => { const kw1 = GEAR_KWS[(r + 6) % GEAR_KWS.length]!;
      const sw = h("span", { className: "sw" }); sw.style.background = KEYWORD_COLOR[kw2]!;
      return row(h("div", { className: "label" }, sw, ` 點：${K.LIST[kw2]!.zh}（${KEYWORD_COLOR[kw2]}）　圓章：${K.LIST[kw1]!.zh}`), ...items.map(([kind, form, material, px], i) => { const rarity = RARS[(i + r) % RARS.length]!; return cell(rarity, shown(gear({ kind, form, material, rarity, keywords: [kw1, kw2] }, px, res), px)); })); });
    section(`點版：12 種點色 × 五種稀有度・${resLabel(res)}${zoomLabel}（每列：直劍 32、半身板甲 32、長靴 32、寶石戒 42、鳶盾 42；稀有度每列往後錯一格）`, ...rows);
  }
}
const isException = (look: GearLook): boolean => { const kf = `${look.kind}/${look.form}`, k = look.kind ?? ""; return K.KEY_CORNER[kf] !== undefined || K.KEY_CORNER[k] !== undefined || K.MORE_DIR_KIND[kf] !== undefined || K.MORE_DIR_KIND[k] !== undefined; };
const DIR_ZH = (d: readonly [number, number]): string => (d[0] > 0 ? "右" : d[0] < 0 ? "左" : d[1] < 0 ? "上" : "下");
function cornerSection(): void {
  const items = ALL.filter((e) => isException(e.look)).slice(FROM, FROM + N);
  for (const px of PXS) for (const res of RESS)
    section(`例外表的款（${items.length} 款）：點燃＋標記，裝備格 ${px}・${resLabel(res)}${zoomLabel}；標籤＝角／記號在圓章的哪一邊`, row(...items.map((e) => { const look = withKw(e.look, ["ignite", "marked"]), o = { def: defOf(look) }, c = K.cornersOf(o)[0]!; return cell(`${e.label} ${c}／${DIR_ZH(K.moreDirOf(c, o))}`, shown(gear(look, px, res), px)); })));
}
function countSection(): void {
  const items: GearLook[] = [{ kind: "sword", form: "straight", material: "steel" }, { kind: "axe", form: "battle", material: "iron" }, { kind: "bow", form: "long", material: "wood" }, { kind: "plate", form: "half", material: "steel" }, { kind: "boots", form: "tall", material: "leather" }, { kind: "leather_gloves", form: "short", material: "leather" }].map((l) => ({ ...l, rarity: RARITY }));
  const rows: [string, readonly string[]][] = [["一個關鍵字（沒有記號）", ["ignite"]], ["兩個關鍵字", ["ignite", "marked"]], ["三個關鍵字（和兩個同一個記號）", ["ignite", "marked", "summon"]]];
  for (const px of PXS) for (const res of RESS)
    section(`一個／兩個／三個關鍵字：裝備格 ${px}・${resLabel(res)}${zoomLabel}`, ...rows.map(([zh, kws]) => row(h("div", { className: "label", textContent: zh }), ...items.map((l) => cell(labelOf(l), shown(gear(withKw(l, kws.slice(0, 2)), px, res, kws), px))))));
}
function legacySection(): void {
  const items = ALL.slice(FROM, Math.min(FROM + N, FROM + 24));
  for (const px of PXS) for (const res of RESS)
    section(`現行對照（左：現行 motif()，>36px 才畫｜右：Q 版圓章）：點燃＋標記，裝備格 ${px}・${resLabel(res)}${zoomLabel}`, row(...items.map((e) => { const look = withKw(e.look, ["ignite", "marked"]); return cell(e.label, shown(legacyGear(look, px, res), px), shown(gear(look, px, res), px)); })));
}

// ---------------- 和樣張逐像素比 ----------------
interface SampleKw { paint: (ctx: CanvasRenderingContext2D, kws: readonly string[], px: number, res: number, opt: object) => void; chipCanvas: (kw: string, px: number, zoom: number, o: object) => HTMLCanvasElement; cornersOf: (def: unknown) => string[] }
interface SampleGear { def: (look: object, icon?: boolean) => unknown; KINDS?: Record<string, unknown> }
async function loadSample(url: string): Promise<{ K: SampleKw; W: SampleGear; A: SampleGear }> {
  const w = window as unknown as Record<string, unknown>;
  w["QPARTS_GLOSSARY"] = { statuses: (glossary as unknown as Glossary).statuses };
  for (const f of ["qIcons.js", "qIconsWeapons.js", "qIconsArmor.js", "qIconsSkills.js", "qIconsParts.js", "qIconsStatus.js", "qIconsKeywords.js"]) {
    let src = await (await fetch(new URL(f, url))).text();
    if (f === "qIcons.js") { const n = src.replace(/const M = \{[^}]*\};/, `const M = ${JSON.stringify(CORE_M)};`); if (n === src) throw new Error("M not found"); src = n; }
    if (f === "qIconsWeapons.js") for (const k of ["iron", "steel", "copper"]) { const n = src.replace(new RegExp(`(const MAT = \\{[^\\n]*?\\b${k}: )\\["#[0-9a-f]{6}", "#[0-9a-f]{6}"\\]`), `$1${JSON.stringify(MATERIAL[k])}`); if (n === src) throw new Error("MAT " + k); src = n; }
    document.head.append(h("script", { textContent: src }));
  }
  return { K: w["QIconsKeywords"] as SampleKw, W: w["QIconsWeapons"] as SampleGear, A: w["QIconsArmor"] as SampleGear };
}
function diff(a: HTMLCanvasElement, b: HTMLCanvasElement): { px: number; max: number } {
  if (a.width !== b.width || a.height !== b.height) return { px: -1, max: -1 };
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data, B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  let px = 0, max = 0;
  for (let i = 0; i < A.length; i += 4) { let d = 0; for (let j = 0; j < 4; j++) d = Math.max(d, Math.abs((A[i + j] ?? 0) - (B[i + j] ?? 0))); if (d > 0) { px++; max = Math.max(max, d); } }
  return { px, max };
}
async function compare(): Promise<void> {
  const S = await loadSample(q.get("sample") ?? "http://127.0.0.1:8151/");
  const pxs = q.get("px") === null ? [32, 42, 48, 64] : PXS, ress = q.get("res") === null ? [1, 2] : RESS;
  const sDef = (look: GearLook): unknown => (S.A.KINDS?.[look.kind ?? ""] ? S.A.def(look) : S.W.def(look, true));
  type Row = { what: string; px: number; res: number; total: number; same: number; diffs: { id: string; px: number; max: number }[] };
  const out: { gear: Row[]; chips: Row[]; corners: { total: number; same: number; diffs: string[] } } = { gear: [], chips: [], corners: { total: 0, same: 0, diffs: [] } };
  ALL.forEach((e, i) => { const ours = K.cornersOf({ def: defOf(e.look) })[0], theirs = S.K.cornersOf(sDef(e.look))[0]; out.corners.total++; if (ours === theirs) out.corners.same++; else out.corners.diffs.push(`${e.look.kind}/${e.look.form} ${ours}≠${theirs} #${i}`); });
  for (const px of pxs) for (const res of ress) {
    const r: Row = { what: "layer", px, res, total: 0, same: 0, diffs: [] };
    ALL.forEach((e, i) => {
      const kws = PAIRS[i % PAIRS.length]!, look = withKw(e.look, kws);
      const ours = layer(look, kws, px, res);
      const theirs = document.createElement("canvas"); theirs.width = theirs.height = Math.round(px * res);
      const x = theirs.getContext("2d")!; x.scale(res, res); S.K.paint(x, kws, px, res, { def: sDef(look) });
      const d = diff(ours, theirs); r.total++; if (d.px === 0) r.same++; else r.diffs.push({ id: `${e.look.kind}/${e.look.form} ${kws.join("+")}`, ...d });
    });
    out.gear.push(r);
  }
  for (const d of [13, 18, 20, 27]) for (const res of ress) {
    const r: Row = { what: "chip", px: d, res, total: 0, same: 0, diffs: [] };
    for (const kw of GEAR_KWS) { const dd = diff(K.chipCanvas(kw, d, res)!, S.K.chipCanvas(kw, d, 1, { res })); r.total++; if (dd.px === 0) r.same++; else r.diffs.push({ id: kw, ...dd }); }
    out.chips.push(r);
  }
  document.body.dataset.compare = JSON.stringify(out);
  document.body.append(h("pre", { className: "out", textContent: JSON.stringify(out, null, 1) }));
}

/** QI-4b B4：頁內組合（`live=0`）和遊戲端 `gearIconCanvas`（`live=1`）逐像素比。 */
function liveCheck(): void {
  const pxs = q.get("px") === null ? [32, 42, 48, 64] : PXS, ress = q.get("res") === null ? [1, 2] : RESS;
  const out: { px: number; res: number; total: number; same: number; diffs: { id: string; px: number; max: number }[] }[] = [];
  for (const px of pxs) for (const res of ress) {
    const r = { px, res, total: 0, same: 0, diffs: [] as { id: string; px: number; max: number }[] };
    ALL.forEach((e, i) => {
      const kws = PAIRS[i % PAIRS.length]!, look = { ...withKw(e.look, kws), rarity: RARS[i % RARS.length]! };
      const composed = bare(look, px, res), x = composed.getContext("2d")!;
      x.setTransform(res, 0, 0, res, 0, 0);
      if (px >= 32) K.paint(x, resolveGear(look).keywords, px, res, { def: defOf(look) });
      const d = diff(composed, live(look, px, res)); r.total++; if (d.px === 0) r.same++; else r.diffs.push({ id: `${e.look.kind}/${e.look.form} ${kws.join("+")}`, ...d });
    });
    out.push(r);
  }
  document.body.dataset.live = JSON.stringify(out);
  document.body.append(h("pre", { className: "out", textContent: JSON.stringify(out, null, 1) }));
}

// ---------------- KW-3：層數計量、條件部件、指紋 ----------------
/** 計量畫布（顯示＝`gaugeBox`×ZOOM）。 */
const gaugeShown = (id: string, n: number, res: number): HTMLCanvasElement => { const cv = SG.gaugeCanvas(id, n, res)!, { w, h: hh } = SG.gaugeBox(id); cv.style.width = `${w * ZOOM}px`; cv.style.height = `${hh * ZOOM}px`; return cv; };
function hudSection(): void {
  for (const res of RESS)
    section(`HUD 層數計量：四種 × 0～滿層・${resLabel(res)}${zoomLabel}（含膠囊外寬 ${STACK_KWS.map((k) => `${K.LIST[k]!.zh} ${SG.gaugeOuter(k)}`).join("、")}；畫布四邊多 4px 給滿層外暈）`,
      ...STACK_KWS.map((id) => row(h("div", { className: "label", textContent: K.LIST[id]!.zh }), ...Array.from({ length: (SG.GAUGE_MAX[id] ?? 0) + 1 }, (_, n) => cell(`${n}／${SG.GAUGE_MAX[id]}`, gaugeShown(id, n, res))))));
}
function condSection(): void {
  const pxs = q.get("px") === null ? [30, 26, 18, 16] : PXS;
  for (const res of RESS)
    section(`條件部件「層數達 N」：圓片 ${pxs.join("／")}・${resLabel(res)}${zoomLabel}（左：KW-3 A 案；右：同列的「累積層數」「消耗層數」「第一輪」對照）`,
      row(...pxs.map((px) => cell(`${px}`, shown(QP.chipCanvas("condition", "self_stack_at_least", px, 1, { res }), px)))),
      row(...pxs.flatMap((px) => [["effect", "add_stack"], ["effect", "consume_stack"], ["condition", "first_round"]].map(([cat, id]) => cell(`${id} ${px}`, shown(QP.chipCanvas(cat!, id!, px, 1, { res }), px))))));
}
/** 指紋（FNV-1a 32 位元，同樣張 q-icons-kw.html?part=hash）：圓章 13／18／20／27 × res 1、2；條件 30／18／16 × res 1、2；計量 0～滿層 res 1。 */
function fnv(cv: HTMLCanvasElement): string { const d = cv.getContext("2d")!.getImageData(0, 0, cv.width, cv.height).data; let x = 0x811c9dc5; for (let i = 0; i < d.length; i++) { x ^= d[i]!; x = Math.imul(x, 0x01000193) >>> 0; } return x.toString(16).padStart(8, "0"); }
function hashLines(): string[] {
  const lines: string[] = [];
  for (const kw of STACK_KWS) lines.push(`chip ${kw} a ` + [32, 42, 48, 64].map((S) => K.sizeOf(S, 1)).flatMap((D) => [1, 2].map((r) => fnv(K.chipCanvas(kw, D, r)!))).join(" "));
  lines.push("cond a " + [30, 18, 16].flatMap((px) => [1, 2].map((r) => fnv(QP.chipCanvas("condition", "self_stack_at_least", px, 1, { res: r })))).join(" "));
  for (const kw of STACK_KWS) lines.push(`hud ${kw} a ` + Array.from({ length: (SG.GAUGE_MAX[kw] ?? 0) + 1 }, (_, n) => fnv(SG.gaugeCanvas(kw, n, 1)!)).join(" "));
  return lines;
}
function hashSection(): void {
  const lines = hashLines();
  document.body.dataset.hash = lines.join("\n");
  document.body.append(h("pre", { className: "out", id: "hash", textContent: lines.join("\n") }));
}

(window as unknown as Record<string, unknown>)["__qiKwDev"] = { paint: K.paint, chip: K.chipCanvas, list: () => ALL.map((e) => ({ ...e.look, label: e.label })), layer, gear, legacyGear, live, gauge: SG.gaugeCanvas, hash: hashLines };

for (const s of SETS) {
  if (s === "bag") bagSection();
  else if (s === "all") allSection();
  else if (s === "chips") chipsSection();
  else if (s === "dots") dotsSection();
  else if (s === "corner") cornerSection();
  else if (s === "count") countSection();
  else if (s === "legacy") legacySection();
  else if (s === "compare") await compare();
  else if (s === "live") liveCheck();
  else if (s === "hud") hudSection();
  else if (s === "cond") condSection();
  else if (s === "hash") hashSection();
}
document.body.dataset.ready = "1";
