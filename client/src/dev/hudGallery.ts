// 開發用：HUD 的 Q 版小圖示（第⑦批，Phase QI-5）。開 `client/dev/hud-gallery.html`（自己的 vite 後 /dev/hud-gallery.html?mute=1）。不屬於正式 build。
// 需求 docs/art/Q版小圖示-HUD移植需求.md 第 5 節（截圖）、第 2 節（指紋比對）。每格都走遊戲端 `render/hudIcon.ts` 的 `hudIconCanvas`（和 React 元件同一張畫布），
// 複製一份貼上、只用 CSS 放大（`image-rendering: pixelated`，最近鄰）。
// 參數：
//   ?set=<名稱,…>     逗號接多段：
//        a        各類總表（預設）：每個圖示在遊戲裡的每個大小 × `&res=`；`&grp=` 只列這幾類（bar,gen,tool,res,set,pip,crest）
//        weather  天氣六種：大世界 15（旁邊有字，照 `WorldHud` 的 Chip）與戰鬥 18（只有圖示，照 `BattleStatusBox`）各一排，加狀態卡風架勢 20 對照
//        moon     時間欄＋天氣欄並排（晝晴、夜晴夜、夜雨…），月亮與夜晚分開
//        pip      源力圓點：3 格裡亮暗混排（0～3 亮），旁邊放同一張狀態卡的源力小圖 16
//        pin      圖釘三處：浮動卡標題列（已釘／未釘）、底部提示列（未釘）、釘住的說明卡角落（金圓底＋紅頭）；技能卡 `PinGlyph`（cardGlyphCanvas）並排
//        hash     指紋（和樣張 `qicons_shots.py --hash hud` 同一個 FNV 算法、同一個行格式；圖釘只有 A），結果放 `body.dataset.hash`
//        wishhash 許願池三個圖的指紋（WP-3b；和樣張 `qicons_shots.py --hash wish` 的推薦三行同格式），結果放 `body.dataset.wishhash`
//        wish     許願池三個圖（WP-3b）：實際底色上真 1 倍 ×1 與最近鄰 ×4（分頁 16 在 #1e2236、籌碼 15 在 #2e3244）
//   &res=<1|2,…>      內部解析度（預設 1,2；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>         放大 k 倍顯示（預設 3）；截圖用裝置像素比 1 拍
//   &grp=<類,…>        set=a 只列這幾類
//   &label=0          不顯示名稱
// 畫好後 `body.dataset.ready = "1"`；另外掛 `window.__qiHudDev`（canvas、list、pinBadge、hash）。
import type { Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { waitForFonts } from "../render/fontLoad";
import { floatPinCanvas, hudIconCanvas, type HudIconOpt } from "../render/hudIcon";
import * as QH from "../render/qIcon/hud";
import { cardGlyphCanvas, statusIconTile, tileCanvas } from "../render/skillIcon";

setGlossary(glossary as unknown as Glossary);
const q = new URLSearchParams(location.search);
const list = (k: string, d: string): string[] => (q.get(k) ?? d).split(",").filter((s) => s !== "");
const SETS = list("set", "a");
const RESS = list("res", "1,2").map(Number);
const ZOOM = Number(q.get("zoom") ?? 3);
const GRPS = list("grp", "bar,gen,tool,res,set,pip,crest") as QH.HudGroup[];
const LABEL = q.get("label") !== "0";
const GRP_ZH: Record<QH.HudGroup, string> = { bar: "功能列 8（淺色圓底上，圖樣 74%）", gen: "通用小圖（任務、留言在功能列那一列的 20／14／13）", tool: "戰鬥工具鈕 7（20）", res: "資源小圖 8（16）", set: "設定標題 3（16）", pip: "源力圓點（9）", crest: "區域紋章 6（34／30）" };
const BG: Record<QH.HudGroup, string> = { bar: "#1e2236", gen: "#1e2236", tool: "#22202a", res: "#1a1410", set: "#1e2236", pip: "#1a1410", crest: "#1e2236" };

type Kids = (Node | string | null)[];
const h = <T extends keyof HTMLElementTagNameMap>(tag: T, props: Partial<HTMLElementTagNameMap[T]> = {}, ...kids: Kids): HTMLElementTagNameMap[T] => { const e = Object.assign(document.createElement(tag), props); e.append(...kids.filter((k): k is Node | string => k !== null)); return e; };
/** 複製一張畫布，CSS 顯示 px × zoom（最近鄰）。 */
function show(src: HTMLCanvasElement, px: number, zoom = ZOOM): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = src.width; c.height = src.height; c.getContext("2d")!.drawImage(src, 0, 0);
  c.style.width = c.style.height = `${px * zoom}px`;
  return c;
}
const uniq = <T,>(a: readonly T[]): T[] => [...new Set(a)];
const sizesOf = (e: QH.HudIconEntry): number[] => uniq(e.sizes).sort((a, b) => a - b);
/** 某個大小的框（樣張 `qOpt`）：bare 列的大小沒有淺色圓底。 */
const optOf = (e: QH.HudIconEntry, px: number): HudIconOpt => (e.bare?.includes(px) ? { frame: "none" } : {});
const cv = (id: string, px: number, res: number): HTMLCanvasElement => hudIconCanvas(id, px, res, optOf(QH.ICON[id]!, px));

function cell(label: string, bg: string, ...kids: Kids): HTMLElement {
  const icons = h("div", { className: "icons" }, ...kids);
  icons.style.background = bg;
  return h("div", { className: "cell" }, icons, LABEL ? h("div", { className: "label", textContent: label }) : null);
}

function setA(): void {
  for (const g of GRPS) {
    const row = h("div", { className: "row" });
    for (const { id, entry: e } of QH.list(g)) {
      const kids: HTMLCanvasElement[] = [];
      for (const px of sizesOf(e)) for (const res of RESS) kids.push(show(cv(id, px, res), px));
      row.append(cell(`${e.zh} ${id}｜${sizesOf(e).join("/")}｜res ${RESS.join(",")}`, BG[g], ...kids));
    }
    document.body.append(h("h2", { textContent: GRP_ZH[g] }), row);
  }
}

const WEATHER: readonly [string, string][] = [["clear", "晴"], ["rain", "雨"], ["fog", "霧"], ["snow", "雪"], ["wind", "風"], ["night", "晴"]];
function chip(src: HTMLCanvasElement, px: number, text: string | null): HTMLElement {
  const s = h("span", { className: "chip" }, show(src, px, 1));
  if (text !== null) s.append(h("span", { textContent: text }));
  return s;
}
function setWeather(): void {
  for (const res of RESS) {
    const big = h("div", { className: "row" });
    const line15 = h("div", { className: "line" }, ...WEATHER.map(([id, t]) => chip(cv(id, 15, res), 15, t)));
    const line18 = h("div", { className: "line" }, ...WEATHER.map(([id]) => chip(cv(id, 18, res), 18, null)));
    const wind = h("div", { className: "line" }, chip(tileCanvas(statusIconTile("stance_wind_1"), 20, res), 20, "風架勢（狀態卡 20）"), chip(cv("wind", 18, res), 18, "天氣風 18"));
    const zoomed = h("div", { className: "line" }, ...WEATHER.map(([id]) => show(cv(id, 15, res), 15, 6)), h("span", { textContent: "｜" }), ...WEATHER.map(([id]) => show(cv(id, 18, res), 18, 5)), h("span", { textContent: "｜" }), show(tileCanvas(statusIconTile("stance_wind_1"), 20, res), 20, 5));
    big.append(h("div", { className: "box" }, h("div", { className: "sub", textContent: `res ${res}：大世界 15（有字）` }), line15, h("div", { className: "sub", textContent: "戰鬥 18（只有圖示，BattleStatusBox）" }), line18, h("div", { className: "sub", textContent: "對照：狀態卡風架勢" }), wind, h("div", { className: "sub", textContent: "最近鄰放大：15 ×6｜18 ×5｜風架勢 20 ×5" }), zoomed));
    document.body.append(h("h2", { textContent: `天氣六種（晴、雨、霧、雪、風、夜晚）res ${res}` }), big);
  }
}
function setMoon(): void {
  const pairs: [string, string, string, string][] = [["sun", "午", "clear", "晴"], ["moon", "夜", "night", "晴"], ["moon", "夜", "rain", "雨"], ["sun", "早", "fog", "霧"], ["moon", "晚", "snow", "雪"], ["sun", "午", "wind", "風"]];
  for (const res of RESS) {
    const row = h("div", { className: "row" });
    for (const [a, ta, b, tb] of pairs) row.append(h("div", { className: "box" }, h("div", { className: "line" }, chip(cv(a, 15, res), 15, ta), chip(cv(b, 15, res), 15, tb)), h("div", { className: "line" }, show(cv(a, 15, res), 15, 5), show(cv(b, 15, res), 15, 5))));
    document.body.append(h("h2", { textContent: `時間欄＋天氣欄（月亮＝大新月、夜晚＝小新月＋兩顆星）res ${res}` }), row);
  }
}
function setPip(): void {
  for (const res of RESS) {
    const row = h("div", { className: "row" });
    for (let lit = 0; lit <= 3; lit++) {
      const pips = h("span", { className: "pips" }, ...[0, 1, 2].map((i) => show(cv(i < lit ? "pip_on" : "pip_off", 9, res), 9, 1)));
      const big = h("span", { className: "pips big" }, ...[0, 1, 2].map((i) => show(cv(i < lit ? "pip_on" : "pip_off", 9, res), 9, 6)));
      row.append(h("div", { className: "box" }, h("span", { className: "statchip" }, show(cardGlyphCanvas("source", 16, res), 16, 1), pips), big, h("div", { className: "sub", textContent: `${lit}／3 亮` })));
    }
    document.body.append(h("h2", { textContent: `源力圓點（3 格亮暗混排）res ${res}：實際大小（狀態卡膠囊）＋最近鄰 ×6` }), row);
  }
}
function setPin(): void {
  for (const res of RESS) {
    const row = h("div", { className: "row" });
    const pinOn = floatPinCanvas(true, 13, res), pinOff = floatPinCanvas(false, 13, res);
    row.append(h("div", { className: "box float" }, h("div", { className: "sub", textContent: "浮動卡標題列：未釘｜已釘" }), h("div", { className: "line" }, h("span", { className: "fhead" }, "格子資訊", show(pinOff, 13, 1)), h("span", { className: "fhead" }, "格子資訊", show(pinOn, 13, 1)))));
    row.append(h("div", { className: "box float" }, h("div", { className: "sub", textContent: "底部提示列（未釘）" }), h("div", { className: "fbar" }, show(pinOff, 13, 1), " 點擊釘住・Shift＋點：任何格")));
    row.append(h("div", { className: "box float" }, h("div", { className: "sub", textContent: "釘住的說明卡角落（18 金圓底＋深藍外圈，裡面 12 紅頭）" }), show(QH.pinBadge(18, res), 21, 1)));
    row.append(h("div", { className: "box float" }, h("div", { className: "sub", textContent: "技能卡 PinGlyph 13（未釘｜已釘）" }), h("div", { className: "line" }, show(cardGlyphCanvas("pin", 13, res, { pinned: false }), 13, 1), show(cardGlyphCanvas("pin", 13, res, { pinned: true }), 13, 1))));
    row.append(h("div", { className: "box" }, h("div", { className: "sub", textContent: "最近鄰放大：浮動卡 未釘｜已釘 ×6、角落 ×4、PinGlyph 未釘｜已釘 ×6" }), h("div", { className: "line" }, show(pinOff, 13, 6), show(pinOn, 13, 6), show(QH.pinBadge(18, res), 21, 4), show(cardGlyphCanvas("pin", 13, res, { pinned: false }), 13, 6), show(cardGlyphCanvas("pin", 13, res, { pinned: true }), 13, 6))));
    document.body.append(h("h2", { textContent: `圖釘三處（A：紅頭／灰鋼）res ${res}` }), row);
  }
}
/** 樣張 q-icons-hud.html ?part=hash 的 fp()。 */
function fp(c: HTMLCanvasElement): string { const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data; let a = 2166136261; for (let i = 0; i < d.length; i++) { a ^= d[i]!; a = Math.imul(a, 16777619) >>> 0; } return a.toString(16).padStart(8, "0"); }
function hashLines(): string[] {
  const lines = QH.list().map(({ id, entry: e }) => `${id} | ${sizesOf(e).map((px) => `${px}:${fp(QH.canvas(id, px, 2, optOf(e, px)))}/${fp(QH.canvas(id, px, 1, optOf(e, px)))}`).join(" ")}`);
  lines.push(`pin_a | ${fp(QH.pinCanvas(true, 13, 2))}/${fp(QH.pinCanvas(true, 13, 1))}`, `pin_off | ${fp(QH.pinCanvas(false, 13, 2))}/${fp(QH.pinCanvas(false, 13, 1))}`, `pinbadge_a | ${fp(QH.pinBadge(18, 2))}/${fp(QH.pinBadge(18, 1))}`);
  return lines;
}
/** 許願池三個圖（WP-3b）：樣張 `q-icons-hud.html ?part=wish&sec=hash` 的行格式「id | 尺寸:2 倍內部/真 1 倍」。 */
function wishHashLines(): string[] {
  return QH.wishList().map(({ id, entry: e }) => `${id} | ${sizesOf(e).map((px) => `${px}:${fp(QH.canvas(id, px, 2))}/${fp(QH.canvas(id, px, 1))}`).join(" ")}`);
}
function setWishHash(): void { const L = wishHashLines(); document.body.dataset.wishhash = L.join("\n"); document.body.append(h("pre", { className: "out", textContent: L.join("\n") })); }
/** 許願池三個圖：遊戲端同一張畫布（`hudIconCanvas`，`HudBare` 的 frame none），放在實際底色上 ×1 與最近鄰 ×4。 */
function setWish(): void {
  const BGW: Record<string, string> = { wish_text: "#1e2236", wish_menu: "#1e2236", wish_left: "#2e3244" };
  for (const res of RESS) {
    const row = h("div", { className: "row" });
    for (const { id, entry: e } of QH.wishList()) {
      const px = e.sizes[0]!, g = hudIconCanvas(id, px, res, { frame: "none" });
      row.append(cell(`${id} ${px}（res ${res}）`, BGW[id]!, show(g, px, 1), show(g, px, 4)));
    }
    document.body.append(h("h2", { textContent: `許願池三個圖 res ${res}：實際大小｜最近鄰 ×4` }), row);
  }
}
function setHash(): void { const L = hashLines(); document.body.dataset.hash = L.join("\n"); document.body.append(h("pre", { className: "out", textContent: L.join("\n") })); }

(window as unknown as Record<string, unknown>)["__qiHudDev"] = { canvas: QH.canvas, list: QH.list, pinBadge: QH.pinBadge, hash: hashLines, wishHash: wishHashLines };
void waitForFonts().then(() => {
  for (const s of SETS) {
    if (s === "a") setA();
    else if (s === "weather") setWeather();
    else if (s === "moon") setMoon();
    else if (s === "pip") setPip();
    else if (s === "pin") setPin();
    else if (s === "hash") setHash();
    else if (s === "wishhash") setWishHash();
    else if (s === "wish") setWish();
  }
  document.body.dataset.ready = "1";
});
