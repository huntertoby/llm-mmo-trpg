// 開發用：事件卡的 Q 版小圖示（第⑧批）與事件插圖頭頂泡泡（第⑧b 批），Phase QI-6。開 `client/dev/event-gallery.html`（自己的 vite 後 /dev/event-gallery.html?mute=1）。不屬於正式 build。
// 需求 docs/art/Q版小圖示-事件卡移植需求.md 第 5 節（截圖）、第 2 節（指紋比對）。圓環圖示、d20 走遊戲端 `storyIconArt.drawStoryIcon`（和 `StoryIcons.tsx` 的圖片同一個畫法），
// 插圖走遊戲端 `drawEventArt`／`drawAwakenArt`（照卡寬出圖，同 `EventCard` 的 `eventArtScale`）；複製一份貼上、只用 CSS 放大（`image-rendering: pixelated`，最近鄰）。
// 參數：
//   ?set=<名稱,…>     逗號接多段：
//        a        選項、其他、六屬性（預設）：每個圖示在遊戲裡的每個大小 × `&res=`；`&grp=sol,misc,attr` 只列這幾類
//        d20      d20 六色 × 64（寫點數 17）／24／20／16 × `&res=`
//        badge    事件插圖 10 種＋覺醒插圖，卡寬 `&w=`（預設 460,354）× `&res=`：整張實際大小＋左上小牌最近鄰放大；另一列「現行｜Q」小牌（膠囊底）並排
//        bubble   頭頂泡泡：用到的 4 個（現行｜Q，`&res=`）、備用 6 個 × 四種底色；插圖裡的泡泡裁切（卡寬 `&w=`）
//        art      四張有泡泡的插圖整張（卡寬 `&w=` 的第一個）
//        hash     指紋（和樣張 `qicons_shots.py --hash event` 同一個 FNV 算法、同一個行格式，43 行），結果放 `body.dataset.hash`
//   &res=<1|2,…>      內部解析度（預設 1,2；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>         放大 k 倍顯示（預設 4）；截圖用裝置像素比 1 拍
//   &w=<卡寬,…>        插圖顯示寬（CSS px；預設 460,354）
//   &grp=<類,…>        set=a 只列這幾類
//   &label=0          不顯示名稱
//   &full=0           set=badge 不放整張插圖、只放小牌裁切（截圖用）
// 畫好後 `body.dataset.ready = "1"`；另外掛 `window.__qiEventDev`（canvas、glyph、bare、hash）。
import type { Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { resolveDoll } from "../render/appearance";
import { drawEventArt, EVENT_ART_H, EVENT_ART_IDS, EVENT_ART_W, eventArtScale, SCENES, type EventArtId } from "../render/eventArt";
import { rr, bubble, OUT, type BubbleKind, type IconId } from "../render/eventArtParts";
import { AWAKEN_H, AWAKEN_W, drawAwakenArt } from "../render/eventArtAwaken";
import { waitForFonts } from "../render/fontLoad";
import { blit } from "../render/qIcon/core";
import * as QE from "../render/qIcon/event";
import { drawStoryIcon, type StoryIconSpec } from "../render/storyIconArt";
import { LEGACY_BADGE_INK, LEGACY_ICON } from "./eventLegacy";

setGlossary(glossary as unknown as Glossary);
const q = new URLSearchParams(location.search);
const list = (k: string, d: string): string[] => (q.get(k) ?? d).split(",").filter((s) => s !== "");
const SETS = list("set", "a");
const RESS = list("res", "1,2").map(Number);
const ZOOM = Number(q.get("zoom") ?? 4);
const WIDTHS = list("w", "460,354").map(Number);
const GRPS = list("grp", "sol,misc,attr") as QE.EventGroup[];
const LABEL = q.get("label") !== "0";
const FULL = q.get("full") !== "0";
const GRP_ZH: Record<string, string> = { sol: "選項 8（24）", misc: "其他 5（線索 16、模型關閉 14、說書人 16／14、說明 14／12、事件線 14）", attr: "六屬性（20／18）" };

type Kids = (Node | string | null)[];
const h = <T extends keyof HTMLElementTagNameMap>(tag: T, props: Partial<HTMLElementTagNameMap[T]> = {}, ...kids: Kids): HTMLElementTagNameMap[T] => { const e = Object.assign(document.createElement(tag), props); e.append(...kids.filter((k): k is Node | string => k !== null)); return e; };
const blankCv = (w: number, hh = w): HTMLCanvasElement => { const c = document.createElement("canvas"); c.width = w; c.height = hh; return c; };
/** 複製一張畫布，CSS 顯示寬 w × zoom（最近鄰）。 */
function show(src: HTMLCanvasElement, w: number, zoom = ZOOM, hh = (w * src.height) / src.width): HTMLCanvasElement {
  const c = blankCv(src.width, src.height); c.getContext("2d")!.drawImage(src, 0, 0);
  c.style.width = `${w * zoom}px`; c.style.height = `${hh * zoom}px`;
  return c;
}
function cell(label: string, bg: string, ...kids: Kids): HTMLElement {
  const icons = h("div", { className: "icons" }, ...kids); icons.style.background = bg;
  return h("div", { className: "cell" }, icons, LABEL ? h("div", { className: "label", textContent: label }) : null);
}
const uniq = <T,>(a: readonly T[]): T[] => [...new Set(a)];
const sizesOf = (e: QE.EventIconEntry): number[] => uniq(e.sizes).sort((a, b) => a - b);

/** 遊戲端的圓環圖示／d20（`storyIconUrl` 同一個畫法：畫布 ceil(size×res)、scale(res)、`drawStoryIcon`）。 */
function story(spec: StoryIconSpec, size: number, res: number): HTMLCanvasElement {
  const c = blankCv(Math.ceil(size * res)), x = c.getContext("2d")!; x.scale(res, res); drawStoryIcon(x, spec, size, res); return c;
}
const specOf = (id: string, e: QE.EventIconEntry, opt: { color?: string; value?: number } = {}): StoryIconSpec =>
  e.grp === "sol" ? { kind: "solution", icon: id as never } : e.grp === "misc" ? { kind: "misc", icon: id as never } : e.grp === "attr" ? { kind: "attr", attr: id as never } : { kind: "d20", ...opt };

function setA(): void {
  for (const g of GRPS) {
    const row = h("div", { className: "row" });
    for (const { id, entry: e } of QE.list(g)) {
      const kids: HTMLCanvasElement[] = [];
      for (const px of sizesOf(e)) for (const res of RESS) kids.push(show(story(specOf(id, e), px, res), px));
      const actual = sizesOf(e).map((px) => show(story(specOf(id, e), px, 2), px, 1));
      row.append(cell(`${e.zh} ${id}｜${sizesOf(e).join("/")}｜res ${RESS.join(",")} ×${ZOOM}`, "#23202a", ...actual, ...kids));
    }
    document.body.append(h("h2", { textContent: GRP_ZH[g] ?? g }), row);
  }
}

function setD20(): void {
  for (const res of RESS) {
    const row = h("div", { className: "row" });
    for (const [k, col] of Object.entries(QE.D20_COLOR)) {
      const kids = [64, 24, 20, 16].map((px) => show(story({ kind: "d20", color: col, value: 17 }, px, res), px, px === 64 ? 2 : ZOOM));
      row.append(cell(`${k} ${col}｜64（×2，寫 17）／24／20／16（×${ZOOM}）`, "#23202a", ...kids));
    }
    document.body.append(h("h2", { textContent: `d20 六色 res ${res}（真 1 倍＝res 1）` }), row);
  }
}

/** 插圖照卡寬出圖（`EventCard` 的做法：每插圖單位 k＝round(w×res)/364 個裝置像素）。 */
function artAt(scene: EventArtId | "awaken", w: number, res: number): HTMLCanvasElement {
  if (scene === "awaken") {
    const k = Math.round(w * res) / AWAKEN_W, c = blankCv(Math.round(AWAKEN_W * k), Math.round(AWAKEN_H * k)), x = c.getContext("2d")!;
    x.setTransform(k, 0, 0, k, 0, 0);
    drawAwakenArt(x, resolveDoll({ template: "hero", dollLook: null, team: "ally", summon: false, weaponId: "sword", raceLook: null }), 1, ["cloud_ridge"], "樞島・中央廣場");
    return c;
  }
  const k = eventArtScale(w, res), c = blankCv(Math.round(EVENT_ART_W * k), Math.round(EVENT_ART_H * k)), x = c.getContext("2d")!;
  x.scale(k, k); drawEventArt(x, scene, "cloud"); return c;
}
/** 從畫布裁一塊（畫布像素），最近鄰放大。 */
function crop(src: HTMLCanvasElement, sx: number, sy: number, w: number, hh: number, zoom: number): HTMLCanvasElement {
  const c = blankCv(Math.round(w), Math.round(hh)), x = c.getContext("2d")!; x.imageSmoothingEnabled = false; x.drawImage(src, Math.round(sx), Math.round(sy), Math.round(w), Math.round(hh), 0, 0, Math.round(w), Math.round(hh));
  c.style.width = `${Math.round(w) * zoom}px`; c.style.height = `${Math.round(hh) * zoom}px`; return c;
}
const BADGE_ICON: Record<string, IconId> = { ambush: "sword", chest: "coin", stele: "ask", altar: "rest", villager: "bang", caravan: "coin", trap: "warn", camp: "rest", anomaly: "portal", friend: "notes" };
/** 小牌一格：深色膠囊底（BOX 17）上的圖示；legacy＝現行（舊 ICON 以 13 畫）、否則 Q 版 14 置中。 */
function pillCv(icon: IconId, res: number, legacy: boolean): HTMLCanvasElement {
  const BOX = 17, c = blankCv(Math.round(BOX * res)), x = c.getContext("2d")!; x.fillStyle = "#1d1915"; x.fillRect(0, 0, c.width, c.height); x.scale(res, res);
  if (legacy) LEGACY_ICON[icon](x, BOX / 2, BOX / 2, 13, LEGACY_BADGE_INK);
  else { const g = QE.glyph("b_" + icon, 14, res); if (g) blit(x, g, (BOX - 14) / 2, (BOX - 14) / 2, 14, res); }
  return c;
}
function setBadge(): void {
  const pills = h("div", { className: "row" });
  for (const icon of ["sword", "coin", "ask", "rest", "bang", "warn", "portal", "notes"] as const) {
    const kids: HTMLCanvasElement[] = [];
    for (const res of RESS) kids.push(show(pillCv(icon, res, true), 17), show(pillCv(icon, res, false), 17));
    pills.append(cell(`${icon}｜現行｜Q（res ${RESS.join(",")}）×${ZOOM}`, "#2a2a3c", ...kids));
  }
  document.body.append(h("h2", { textContent: "小牌 8 個：現行（ICON 13＋米白墨）｜Q 版（14）並排，膠囊底" }), pills);
  for (const w of WIDTHS) for (const res of RESS) {
    const row = h("div", { className: "row" });
    for (const scene of [...EVENT_ART_IDS, "awaken"] as const) {
      const art = artAt(scene, w, res), k = art.width / (scene === "awaken" ? AWAKEN_W : EVENT_ART_W);
      row.append(cell(`${scene === "awaken" ? "覺醒" : SCENES[scene].zh}｜寬 ${w}`, "#17151b", FULL ? show(art, w, 1) : null, crop(art, 4 * k, 4 * k, 34 * k, 32 * k, res === 1 ? 4 : 3)));
    }
    document.body.append(h("h2", { textContent: `事件插圖小牌（卡寬 ${w}、res ${res}；右＝左上小牌那一塊最近鄰 ×${res === 1 ? 4 : 3}）` }), row);
  }
}

/** 泡泡一格（樣張 bubbleCv：30×34 草地色底、泡泡尖端在 (15,29)）；legacy＝現行的舊圖。 */
const BUW = 30, BUH = 34;
function bubbleCv(icon: IconId, kind: BubbleKind, legacy: boolean, res: number): HTMLCanvasElement {
  const c = blankCv(Math.round(BUW * res), Math.round(BUH * res)), x = c.getContext("2d")!; x.fillStyle = "#4e7a3c"; x.fillRect(0, 0, c.width, c.height); x.scale(res, res);
  if (!legacy) { bubble(x, 15, 29, icon, kind); return c; }
  bubble(x, 15, 29, icon, kind); /* 框照現行；裡面蓋掉再畫舊圖 */
  x.save(); rr(x, 15 - 13, 29 - 26, 26, 22, 8); x.clip(); x.fillStyle = QE.BUBBLE_FILL[kind]!; x.fillRect(15 - 12, 29 - 25, 24, 20); x.restore();
  rr(x, 15 - 13, 29 - 26, 26, 22, 8); x.lineWidth = 2; x.strokeStyle = OUT; x.stroke();
  LEGACY_ICON[icon](x, 15, 29 - 15, 13);
  return c;
}
const BU_AT: Record<string, [number, number]> = { ambush: [239.2, 59.8], villager: [124.8, 80.6], caravan: [280.8, 83.2], friend: [265.2, 46.8] };
function setBubble(): void {
  const used = h("div", { className: "row" });
  for (const { id, entry } of QE.bubbleList().filter((b) => b.entry.use.length > 0)) for (const [scene, kind] of entry.use) {
    const kids: HTMLCanvasElement[] = [];
    for (const res of RESS) kids.push(show(bubbleCv(id as IconId, kind as BubbleKind, true, res), BUW, ZOOM, BUH), show(bubbleCv(id as IconId, kind as BubbleKind, false, res), BUW, ZOOM, BUH));
    used.append(cell(`${SCENES[scene as EventArtId].zh}・${kind}｜現行｜Q（res ${RESS.join(",")}）`, "#2a2a3c", ...kids));
  }
  document.body.append(h("h2", { textContent: `用到的 4 個泡泡：現行｜Q 並排（每對 res ${RESS.join("、")}，×${ZOOM}）` }), used);
  const spare = h("div", { className: "row" });
  for (const { id, entry } of QE.bubbleList().filter((b) => b.entry.use.length === 0)) {
    const kids: HTMLCanvasElement[] = [];
    for (const res of RESS) for (const kind of Object.keys(QE.BUBBLE_FILL)) kids.push(show(bubbleCv(id as IconId, kind as BubbleKind, false, res), BUW, ZOOM, BUH));
    spare.append(cell(`備用：${entry.zh} ${id}｜外框 ${entry.ow}px｜四種底色 × res ${RESS.join(",")}`, "#2a2a3c", ...kids));
  }
  document.body.append(h("h2", { textContent: "備用 6 個泡泡（現在沒有場景用到；開發 PM 照美術建議一起搬）" }), spare);
  for (const w of WIDTHS) {
    const row = h("div", { className: "row" });
    for (const res of RESS) for (const scene of Object.keys(BU_AT) as EventArtId[]) {
      const art = artAt(scene, w, res), k = art.width / EVENT_ART_W, [bx, by] = BU_AT[scene]!;
      row.append(cell(`${SCENES[scene].zh}｜卡寬 ${w}｜res ${res}`, "#17151b", crop(art, (bx - 17) * k, (by - 30) * k, 34 * k, 36 * k, res === 1 ? 4 : 3)));
    }
    document.body.append(h("h2", { textContent: `插圖裡的泡泡（卡寬 ${w}，最近鄰）` }), row);
  }
}
function setArt(): void {
  const w = WIDTHS[0] ?? 460, row = h("div", { className: "row" });
  for (const scene of Object.keys(BU_AT) as EventArtId[]) row.append(cell(`${SCENES[scene].zh}（小牌${BADGE_ICON[scene]}＋泡泡）卡寬 ${w}`, "#17151b", show(artAt(scene, w, 1), w, 1)));
  document.body.append(h("h2", { textContent: `四張有泡泡的插圖（卡寬 ${w}，小牌與泡泡都是 Q 版）` }), row);
}

/** 樣張 q-icons-event.html ?part=hash 的 fp()。 */
function fp(c: HTMLCanvasElement): string { const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data; let a = 2166136261; for (let i = 0; i < d.length; i++) { a ^= d[i]!; a = Math.imul(a, 16777619) >>> 0; } return a.toString(16).padStart(8, "0"); }
/** 樣張的 qCv：小牌＝17 格深色膠囊底＋14 的圖樣置中；其他＝含框的圖示。 */
function qCv(id: string, px: number, res: number): HTMLCanvasElement {
  if (QE.ICON[id]!.grp !== "badge") return QE.canvas(id, px, res);
  const BOX = 17, c = blankCv(Math.round(BOX * res)), x = c.getContext("2d")!; x.fillStyle = "#1d1915"; x.fillRect(0, 0, c.width, c.height); x.scale(res, res);
  const g = QE.glyph(id, 14, res); if (g) blit(x, g, (BOX - 14) / 2, (BOX - 14) / 2, 14, res); return c;
}
function hashLines(): string[] {
  const rows = QE.list().map(({ id, entry: e }) => `${id} | ${sizesOf(e).map((px) => `${px}:${fp(qCv(id, px, 2))}/${fp(qCv(id, px, 1))}`).join(" ")}`);
  for (const [k, col] of Object.entries(QE.D20_COLOR)) rows.push(`d20_${k}_64 | ${fp(QE.canvas("d20", 64, 2, { color: col, value: 17 }))}`);
  for (const { id } of QE.bubbleList()) rows.push(`bubble_${id} | ${Object.keys(QE.BUBBLE_FILL).map((k) => `${k}:${fp(bubbleCv(id as IconId, k as BubbleKind, false, 2))}/${fp(bubbleCv(id as IconId, k as BubbleKind, false, 1))}`).join(" ")}`);
  return rows;
}
function setHash(): void { const L = hashLines(); document.body.dataset.hash = L.join("\n"); document.body.append(h("pre", { className: "out", textContent: L.join("\n") })); }

(window as unknown as Record<string, unknown>)["__qiEventDev"] = { canvas: QE.canvas, glyph: QE.glyph, bare: QE.bareGlyph, hash: hashLines };
void waitForFonts().then(() => {
  for (const s of SETS) {
    if (s === "a") setA();
    else if (s === "d20") setD20();
    else if (s === "badge") setBadge();
    else if (s === "bubble") setBubble();
    else if (s === "art") setArt();
    else if (s === "hash") setHash();
  }
  document.body.dataset.ready = "1";
});
