// 開發用：狀態圖示與身上特效一覽（Phase 3-36a；QI-3a 加 Q 版狀態圖示的參數；QI-3b 改走遊戲端）。開 `client/dev/status-gallery.html`（自己的 vite 後 /dev/status-gallery.html?mute=1）。
// 不屬於正式 build；供美術 PM 驗收與截圖。上：名詞表全部狀態（118 個）的圖示；下：用真正的 BattleRenderer 畫的 9×6 戰場（頭頂狀態列、+N、冰凍／暈眩／護盾／
// 定身／持續傷害、隱蔽、上下相鄰單位的血條、倒下、灌注召喚物；QI-3b 起是 Q 版，和遊戲同一條路）。
// 上半（規格 docs/phases/PhaseQI-3計畫.md A4、B5、第 8.2 節）：QI-3b 起預設走遊戲端——狀態卡 `tileCanvas(statusIconTile(id), px, res)`、頭頂 `statusIconCanvas(id, px, res)`；
// `&live=0`（或 `&tint=0`，遊戲端沒有不染底的開關）改成 3a 的 `render/qIcon/status.ts` 直畫 `cardCanvas`／`headCanvas`（比對用）。參數：
//   ?px=<CSS px,…>       圖示邊長，可逗號給多個（預設 52）：20＝狀態卡構圖（100 單位方塊、半徑 49 圓形裁切、框 16.8）；
//                        其他（11＝頭頂構圖、52＝原總表）＝頭頂構圖（框邊長 px−2）。`&kind=card|head` 強制指定
//   &live=0              不走遊戲端，直接畫 qIcon/status.ts（3a 的畫法；應和遊戲端逐像素相同）
//   &res=<1|2,…>         內部解析度，可逗號給多個（預設 2＝遊戲；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>            放大 k 倍顯示（image-rendering: pixelated，最近鄰）；截圖用裝置像素比 1 拍
//   &set=<名稱,…>        all（名詞表全部，預設）｜ctrl｜debuff｜buff｜shield｜neutral｜stance｜element（元素架勢 9 × 5 級）｜boss
//                        ｜near（撞圖組：暖色四六角、冷色四六角、岩石／殼／甲七個、晶能兩個）｜cls（控制類 7 個＋tint=0 對照列）
//                        ｜unknown（brand_new_status、空字串、增益／減益／中性／有類別的假狀態各一）
//                        ｜fitgen（在這個瀏覽器量 fitK 表：結果放 `body.dataset.fit`（statusFit.json 的內容），不畫圖）
//                        ｜compare（和樣張逐像素比，見下）｜none（上半不畫）
//                        ｜corner（QI-3b：元素架勢 9 × 5 級＋晶能湧動／狂湧＋有回合數、有數值、空各一，畫成 StatusBadge 同款的 24px 方塊＋角落數字（`statusCorner`）；
//                          每列同元素 5 級，證明各級同圖、只差角落數字）
//                        ｜tile（部件圓片 statusTile，名詞表全部；QI-4a 起 `?px=` 給圓片尺寸清單（18、24、26、30；沒給 px 時 24）× `&res=` 清單；
//                          第④批 32 種標「Q 版」、其餘標「Q 版（hooks）」＝經 hooks.status 畫 qIcon/status.ts 的圖樣；`&old=1` 每格後面並排 QI-4a 以前經 hooks.status 的現行圖樣；
//                          QI-4b：`&nofit=1` 每格後面並排 QI-4a 的圖樣（沒套 fit，美術 QI-4a 驗收可修 1 的「改前」）；`&ids=<id,…>` 只列這些狀態）
//   &tint=0              不染類別底色（對照用）
//   &from=<i>&n=<k>      清單只取第 i 個起的 k 個（截圖分張用）
//   &label=0             不顯示名稱
//   &old=1               每格後面並排 QI-3b 以前的畫法（單色線條圖樣：`drawGlyph`＋`glyphColor`，這個檔裡的 `legacyPaint`，同尺寸、同 res）
//   &scene=0             不畫下半的戰場
//   &sample=<網址>       set=compare 用：樣張 docs/art/sample/ 的網址（靜態伺服器要帶 CORS）。載入 qIcons.js、qIconsWeapons.js、qIconsSkills.js、
//                        qIconsParts.js、qIconsStatus.js（載入前把 qIcons.js 的 M 換成 core.ts 的 M、qIconsWeapons.js 的 MAT 鐵鋼銅換成 material.ts），
//                        餵同一份名詞表，對 px × res 的每個狀態交錯著畫、getImageData 逐像素比；fitK 表的每一筆和樣張 fitK 比。結果放 `body.dataset.compare`（JSON）
// 畫好後 `body.dataset.ready = "1"`。另外掛 `window.__qiStatusDev`（paint、cardCanvas、headCanvas、glyph、entry、list、fitK、fitKMeasured、fitTable()、fitKeys()）。
import type { BattleView, Glossary, StatusView, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary, statusName } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import { MATERIAL } from "../render/material";
import { M as CORE_M } from "../render/qIcon/core";
import * as QT from "../render/qIcon/status";
import * as QP from "../render/qIcon/parts";
import { statusIconTile, statusTile, tileCanvas } from "../render/skillIcon";
import { statusColor, statusGlyph } from "../render/skillParts";
import { drawGlyph, FRAME_COLOR, framePath, glyphColor, polarityOf, STATUS_BASE_BG, statusIconCanvas } from "../render/statusIcon";
import "../styles/status-card.css";
import { statusCorner } from "../ui/statusCard";

const real = glossary as unknown as Glossary;
const REAL_IDS = real.statuses.map((s) => s.id);
/** 不認得的狀態（set=unknown）：名詞表裡沒有 Q 版圖樣的假狀態，增益／減益／中性／有類別各一（只在開發頁加進名詞表）。 */
const FAKE: { id: string; name_zh: string; polarity: string; control_group: string | null }[] = [
  { id: "dev_fake_buff", name_zh: "祝福（假）", polarity: "buff", control_group: null },
  { id: "dev_fake_debuff", name_zh: "詛咒（假）", polarity: "debuff", control_group: null },
  { id: "dev_fake_neutral", name_zh: "中立（假）", polarity: "neutral", control_group: null },
  { id: "dev_fake_ctrl", name_zh: "麻痺（假）", polarity: "debuff", control_group: "hard" },
];
const base = real.statuses.find((s) => s.id === "stun")!;
setGlossary({ ...real, statuses: [...real.statuses, ...FAKE.map((f) => ({ ...base, id: f.id, name_zh: f.name_zh, status_look: { ...base.status_look!, polarity: f.polarity, control_group: f.control_group } }))] } as unknown as Glossary);
await waitForFonts();

const q = new URLSearchParams(location.search);
const list = (k: string, d: string): string[] => (q.get(k) ?? d).split(",").filter((s) => s !== "");
const PXS = list("px", "52").map(Number);
const RESS = list("res", "2").map(Number);
const ZOOM = Number(q.get("zoom") ?? 1);
const SETS = list("set", "all");
const TINT = q.get("tint") !== "0";
const FROM = Number(q.get("from") ?? 0);
const N = Number(q.get("n") ?? 9999);
const LABEL = q.get("label") !== "0";
const OLD = q.get("old") === "1";
const NOFIT = q.get("nofit") === "1";
const TILE_IDS = q.get("ids")?.split(",").filter((s) => s !== "") ?? null;
const LIVE = q.get("live") !== "0";
const KIND = q.get("kind");
const isCard = (px: number): boolean => (KIND ? KIND === "card" : px === 20);

/** 分組（同樣張 q-icons-status.html 的 ORDER；8 組合計 118 個）。 */
const ELEMENT_IDS = QT.ELEMENTS.flatMap((e) => [1, 2, 3, 4, 5].map((n) => `stance_${e}_${n}`));
const GROUPS: Readonly<Record<string, readonly [string, readonly string[]]>> = {
  ctrl: ["控制類 7 個（框的底色染類別色）", ["stun", "frozen", "slow", "root", "taunted", "feared", "silenced"]],
  debuff: ["持續傷害與其他減益 14 個", ["burning", "poison", "bleed", "prone", "weaken", "vulnerable", "blinded", "marked", "armor_broken", "entangled", "overdrawn", "revealed", "time_bomb", "oath_broken"]],
  buff: ["增益 11 個", ["hasted", "empowered", "regenerating", "guarded", "defending", "stoneskin", "overwatch", "infused_fire", "infused_holy", "rallied", "commanding"]],
  shield: ["護盾家族 6 個", ["shielded", "shielded_thorns", "shielded_mending", "shielded_wet", "shielded_charged", "shielded_marking"]],
  neutral: ["中性 11 個", ["concealed", "undying", "soul_link", "heart_link", "race_adapt", "race_stonewall", "charging", "league_truce", "oath_bonus_easy", "oath_bonus_medium", "oath_bonus_hard"]],
  stance: ["姿態 9 個", ["stance_guard", "stance_bulwark", "stance_ironwall", "stance_bastion", "stance_fury", "stance_flame", "stance_blaze", "stance_frost", "stance_glacier"]],
  element: ["元素架勢 9 種 × 5 級（各級同一個圖）", ELEMENT_IDS],
  boss: ["首領戰與詞綴 15 個", ["sword_formation", "array_ward", "summit_array_ward", "shard_burst", "rift_resonance", "rift_channel", "crystal_surge", "crystal_surge_2", "rift_collapse", "mist_return", "molten_burst", "heart_ember_burst", "frost_ember_burst", "molten_shell", "hard_shell"]],
};
/** 撞圖組（需求第 5 節第 4 項）。 */
const NEAR: readonly (readonly [string, readonly string[]])[] = [
  ["暖色四個六角：狂怒、烈焰姿態、焰刃、烈焰架勢", ["stance_fury", "stance_blaze", "stance_flame", "stance_fire_1"]],
  ["冷色四個六角：堅守、霜刃、冰川、寒霜架勢", ["stance_guard", "stance_frost", "stance_glacier", "stance_ice_1"]],
  ["岩石／殼／甲：穩若磐石、大地架勢、硬殼、熔殼、破甲、易傷、石膚", ["race_stonewall", "stance_earth_1", "hard_shell", "molten_shell", "armor_broken", "vulnerable", "stoneskin"]],
  ["晶能湧動／狂湧", ["crystal_surge", "crystal_surge_2"]],
];
const UNKNOWN = ["brand_new_status", "", ...FAKE.map((f) => f.id)];

const h = <K extends keyof HTMLElementTagNameMap>(tag: K, props: Partial<HTMLElementTagNameMap[K]> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[K] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};
/** 放大顯示（最近鄰）。 */
const shown = (cv: HTMLCanvasElement, px: number): HTMLCanvasElement => {
  cv.style.width = cv.style.height = `${px * ZOOM}px`;
  cv.style.imageRendering = "pixelated";
  return cv;
};
/** 遊戲端的快取畫布是共用的：複製一張再放進頁面（同一張不能出現兩次）。 */
function copyOf(src: HTMLCanvasElement): HTMLCanvasElement {
  const cv = document.createElement("canvas");
  cv.width = src.width;
  cv.height = src.height;
  cv.getContext("2d")!.drawImage(src, 0, 0);
  return cv;
}
/** Q 版：預設走遊戲端（QI-3b）；`&live=0` 或不染底時直接畫 status.ts（3a）。 */
function qIcon(id: string, px: number, res: number, tint: boolean): HTMLCanvasElement {
  if (LIVE && tint) return shown(copyOf(isCard(px) ? tileCanvas(statusIconTile(id), px, res) : statusIconCanvas(id, px, res)!), px);
  const opt = { res, tint };
  return shown((isCard(px) ? QT.cardCanvas(id, px, 1, opt) : QT.headCanvas(id, px, 1, opt))!, px);
}
/** QI-3b 以前的 paintStatusIcon（單色線條圖樣），原樣抄在開發頁對照用；遊戲不再呼叫。 */
function legacyPaint(ctx: CanvasRenderingContext2D, id: string, cx: number, cy: number, size: number): void {
  const pol = polarityOf(id);
  const k = size / 26;
  ctx.save();
  ctx.translate(cx, cy);
  framePath(ctx, pol, size / 2);
  ctx.fillStyle = STATUS_BASE_BG;
  ctx.fill();
  ctx.lineWidth = Math.max(1.5, size * 0.09);
  ctx.strokeStyle = FRAME_COLOR[pol];
  ctx.stroke();
  ctx.scale(k * 0.95, k * 0.95);
  ctx.fillStyle = ctx.strokeStyle = glyphColor(id);
  ctx.lineWidth = size <= 18 ? 3 : 2.4;
  ctx.lineCap = ctx.lineJoin = "round";
  drawGlyph(ctx, id);
  ctx.restore();
}
/** QI-3b 以前的畫法：同一個構圖、同 res。 */
function oldIcon(id: string, px: number, res: number): HTMLCanvasElement {
  const cv = document.createElement("canvas");
  cv.width = cv.height = Math.round(px * res);
  const x = cv.getContext("2d")!;
  if (isCard(px)) {
    x.scale((px * res) / 100, (px * res) / 100);
    x.beginPath();
    x.arc(50, 50, 49, 0, Math.PI * 2);
    x.clip();
    legacyPaint(x, id, 50, 50, 84);
  } else {
    x.scale(res, res);
    legacyPaint(x, id, px / 2, px / 2, px - 2);
  }
  cv.style.outline = "1px dashed #555";
  return shown(cv, px);
}
const labelOf = (id: string): string => (id === "" ? "(空字串)" : id === "brand_new_status" ? "不認得" : statusName(id));
function cell(id: string, tint = TINT): HTMLDivElement {
  const icons = h("div", { className: "icons" });
  for (const px of PXS) for (const res of RESS) { icons.append(qIcon(id, px, res, tint)); if (OLD) icons.append(oldIcon(id, px, res)); }
  const c = h("div", { className: "cell" }, icons);
  if (LABEL) c.append(h("span", {}, labelOf(id)), h("code", {}, id === "" ? '""' : id));
  return c;
}
function section(title: string, ids: readonly string[], tint = TINT): void {
  const box = h("div", { className: "scene" }, h("h2", { textContent: `${title}　px ${PXS.join("／")}・res ${RESS.join("／")}${ZOOM !== 1 ? `・×${ZOOM}` : ""}${tint ? "" : "・不染底"}` }));
  const grid = h("div", { className: "grid" });
  for (const id of ids.slice(FROM, FROM + N)) grid.append(cell(id, tint));
  box.append(grid);
  top.append(box);
}

// ---------------- fitK 表 ----------------
/** 會用到的鍵：名詞表全部 × {狀態卡 16.8、頭頂 9} × res {1, 2} 的 inset（只有頭頂染底的 7 個隨 res 變），加上 tint=0（不染底、inset 0）的對照。框邊長照 cardCanvas／headCanvas 的算法。 */
function fitKeys(): [string, number, number][] {
  const out = new Map<string, [string, number, number]>();
  for (const id of REAL_IDS) for (const frame of [84 * (20 / 100), (11 - 2) * 1]) for (const cls of [QT.clsOf(id), null]) for (const res of [1, 2]) { const inset = QT.tintInset(frame, res, cls); out.set(QT.fitKey(id, frame, inset), [id, frame, inset]); }
  return [...out.values()];
}
/** 在這個瀏覽器量（不查表）。 */
function fitTable(): Record<string, number> {
  const t: Record<string, number> = {};
  for (const [id, frame, inset] of fitKeys().sort((a, b) => (QT.fitKey(...a) < QT.fitKey(...b) ? -1 : 1))) t[QT.fitKey(id, frame, inset)] = QT.fitKMeasured(id, frame, inset);
  return t;
}

// ---------------- 和樣張逐像素比 ----------------
interface SampleStatus { cardCanvas: (id: string, px: number, zoom: number, opt: object) => HTMLCanvasElement; headCanvas: (id: string, px: number, zoom: number, opt: object) => HTMLCanvasElement; fitK: (id: string, size: number, inset: number) => number }
async function loadSample(url: string): Promise<SampleStatus> {
  const w = window as unknown as Record<string, unknown>;
  w["QPARTS_GLOSSARY"] = { statuses: real.statuses };
  for (const f of ["qIcons.js", "qIconsWeapons.js", "qIconsSkills.js", "qIconsParts.js", "qIconsStatus.js"]) {
    let src = await (await fetch(new URL(f, url))).text();
    if (f === "qIcons.js") { const n = src.replace(/const M = \{[^}]*\};/, `const M = ${JSON.stringify(CORE_M)};`); if (n === src) throw new Error("M not found"); src = n; }
    if (f === "qIconsWeapons.js") for (const k of ["iron", "steel", "copper"]) { const n = src.replace(new RegExp(`(const MAT = \\{[^\\n]*?\\b${k}: )\\["#[0-9a-f]{6}", "#[0-9a-f]{6}"\\]`), `$1${JSON.stringify(MATERIAL[k])}`); if (n === src) throw new Error("MAT " + k); src = n; }
    document.head.append(h("script", { textContent: src }));
  }
  return w["QIconsStatus"] as SampleStatus;
}
function diff(a: HTMLCanvasElement, b: HTMLCanvasElement): { px: number; max: number } {
  if (a.width !== b.width || a.height !== b.height) return { px: -1, max: -1 };
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data, B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  let px = 0, max = 0;
  for (let i = 0; i < A.length; i += 4) { let d = 0; for (let j = 0; j < 4; j++) d = Math.max(d, Math.abs((A[i + j] ?? 0) - (B[i + j] ?? 0))); if (d > 0) { px++; max = Math.max(max, d); } }
  return { px, max };
}
async function compare(): Promise<void> {
  const S = await loadSample(q.get("sample") ?? "http://127.0.0.1:8136/");
  const out: { images: { px: number; res: number; tint: boolean; total: number; same: number; diffs: { id: string; px: number; max: number }[] }[]; fit: { total: number; same: number; diffs: { key: string; ours: number; sample: number }[] } } = { images: [], fit: { total: 0, same: 0, diffs: [] } };
  if (q.get("fit") !== "0") {
    const t = fitTable();
    for (const [id, frame, inset] of fitKeys()) { const key = QT.fitKey(id, frame, inset), ours = QT.fitK(id, frame, inset), sample = S.fitK(id, frame, inset); out.fit.total++; if (ours === sample && t[key] === ours) out.fit.same++; else out.fit.diffs.push({ key, ours, sample }); }
  }
  const ids = REAL_IDS.slice(FROM, FROM + N);
  for (const px of PXS) for (const res of RESS) for (const tint of TINT ? [true] : [false]) {
    const row = { px, res, tint, total: 0, same: 0, diffs: [] as { id: string; px: number; max: number }[] };
    for (const id of ids) {
      const opt = { res, tint };
      const ours = (isCard(px) ? QT.cardCanvas(id, px, 1, opt) : QT.headCanvas(id, px, 1, opt))!;
      const theirs = isCard(px) ? S.cardCanvas(id, px, 1, opt) : S.headCanvas(id, px, 1, opt);
      const d = diff(ours, theirs);
      row.total++;
      if (d.px === 0) row.same++; else row.diffs.push({ id, ...d });
    }
    out.images.push(row);
  }
  document.body.dataset.compare = JSON.stringify(out);
  top.append(h("pre", { className: "out" }, JSON.stringify(out, null, 1)));
}

// ---------------- 角落數字（QI-3b set=corner） ----------------
/** StatusBadge 同款：24px 深褐方塊＋狀態卡 20px 圖示＋右下角 `statusCorner`（`styles/status-card.css`）。 */
function badge(s: StatusView, res: number): HTMLElement {
  const cv = copyOf(tileCanvas(statusIconTile(s.status_id), 20, res));
  cv.style.width = cv.style.height = "20px";
  const b = h("span", { className: "stat-badge status-badge" }, cv);
  const corner = statusCorner(s);
  if (corner !== "") b.append(h("b", { className: "stat-corner" }, corner));
  return b;
}
function cornerSection(): void {
  const res = RESS[0] ?? 2;
  const sv = (status_id: string, remaining: number | null, amount: number | null): StatusView => ({ status_id, remaining, amount, source_id: null, charge_tiles: [], cost_status: false }) as unknown as StatusView;
  const box = h("div", { className: "scene" }, h("h2", { textContent: `角落數字（StatusBadge 同款，20px・res ${res}${ZOOM !== 1 ? `・×${ZOOM}` : ""}）：元素架勢 9 × 5 級（各級同圖、角落＝級數，優先於回合數）、晶能湧動／狂湧 1／2、一般狀態（回合數／數值／空）` }));
  const rows: [string, StatusView[]][] = [
    ...QT.ELEMENTS.map((e): [string, StatusView[]] => [statusName(`stance_${e}_1`).replace(/\s*[・·‧．.]\s*\S$/u, ""), [1, 2, 3, 4, 5].map((n) => sv(`stance_${e}_${n}`, n === 5 ? 3 : null, null))]),
    ["晶能湧動／狂湧", [sv("crystal_surge", null, null), sv("crystal_surge_2", null, null)]],
    ["一般：回合數 3（燃燒）、數值 4（蓄力）、空（隱蔽）、控制類回合數 2（暈眩）", [sv("burning", 3, null), sv("charging", null, 4), sv("concealed", null, null), sv("stun", 2, null)]],
  ];
  for (const [title, list] of rows) {
    const row = h("div", { className: "badges" });
    for (const s of list) row.append(badge(s, res));
    // 只放大方塊那一列（CSS zoom：畫布最近鄰放大、角落字照字型放大），標籤照原尺寸
    if (ZOOM !== 1) (row.style as unknown as Record<string, string>)["zoom"] = String(ZOOM);
    const wrap = h("div", { className: "badge-row" }, row);
    if (LABEL) wrap.append(h("span", {}, title));
    box.append(wrap);
  }
  top.append(box);
}

const top = h("div");
document.body.append(top);
top.append(h("h1", { textContent: `狀態圖示一覽：名詞表 ${REAL_IDS.length} 個狀態（Q 版，${LIVE ? "QI-3b 走遊戲端 statusIconTile／statusIconCanvas" : "live=0：直接畫 qIcon/status.ts"}；圓＝增益、方＝減益、六角＝中性）` }));
for (const s of SETS) {
  if (s === "all") section(`全部 ${REAL_IDS.length} 個（名詞表順序）`, REAL_IDS);
  else if (GROUPS[s]) section(GROUPS[s][0], GROUPS[s][1]);
  else if (s === "near") for (const [t, ids] of NEAR) section(t, ids);
  else if (s === "cls") { section("控制類 7 個（染類別底色）", GROUPS["ctrl"]![1], true); section("控制類 7 個 tint=0（不染底，對照）", GROUPS["ctrl"]![1], false); }
  else if (s === "unknown") section("不認得的狀態：brand_new_status、空字串、假狀態（增益／減益／中性／硬控）", UNKNOWN);
  else if (s === "fitgen") { const t = fitTable(); document.body.dataset.fit = JSON.stringify({ _note: "由開發頁 client/dev/status-gallery.html?set=fitgen 在 Chrome（無頭、--disable-gpu＝軟體繪製，同美術自查表 qicons_shots.py）量出（render/qIcon/status.ts 的 fitKMeasured，樣張 fitK 的逐行搬）；不手改。鍵＝id|框邊長 toFixed(2)|inset toFixed(2)", fit: t }, null, 1); top.append(h("pre", { className: "out" }, `fitK：${Object.keys(t).length} 筆`)); }
  else if (s === "compare") await compare();
  else if (s === "corner") cornerSection();
  else if (s === "tile") tileSection();
}

/** set=tile：部件圓片 `statusTile`（技能組裝列 18／30、戰場定時炸彈／蓄力徽章 24、工坊狀態選項 26）。第④批 STATUS 32 種是 Q 版；
 *  其餘 86 種經 `hooks.status`，QI-4a 起也是 Q 版（`qIcon/status.ts` 的圖樣，標「Q 版（hooks）」）。`&old=1` 並排 QI-4a 以前經掛鉤畫的現行圖樣（`statusGlyph`＋`statusColor`）。 */
function tileSection(): void {
  const pxs = q.get("px") === null ? [24] : PXS;
  for (const px of pxs) for (const res of RESS) {
    const box = h("div", { className: "scene" }, h("h2", { textContent: `部件圓片 statusTile ${px}px・${res === 1 ? "真 1 倍" : "DPR 2"}${ZOOM !== 1 ? `・×${ZOOM}` : ""}（名詞表全部；「Q 版（hooks）」＝第④批 32 種以外，經 hooks.status 畫 qIcon/status.ts 的圖樣${OLD ? "；每格右邊＝QI-4a 以前的現行圖樣" : ""}）` }));
    const grid = h("div", { className: "grid" });
    for (const id of TILE_IDS ?? REAL_IDS.slice(FROM, FROM + N)) {
      const c = h("div", { className: "cell" });
      if (NOFIT) c.append(shown(legacyTile(id, px, res, (q, o, sid) => QT.entry(sid)?.d(q, o)), px));
      c.append(shown(copyOf(tileCanvas(statusTile(id), px, res)), px));
      if (OLD) c.append(shown(legacyTile(id, px, res), px));
      if (LABEL) c.append(h("span", {}, statusName(id)), h("code", {}, QP.STATUS[id] ? "Q 版" : "Q 版（hooks）"));
      grid.append(c);
    }
    box.append(grid);
    top.append(box);
  }
}
/** QI-4a 以前的部件圓片：同 `statusTile` 的畫法（100 單位、半徑 49 裁切、`QP.chip` 半徑 42、淡色環），掛鉤暫時換回現行圖樣（或 `hook`：QI-4b 的 `&nofit=1` 傳 QI-4a 沒縮的圖樣）。 */
function legacyTile(id: string, px: number, res: number, hook?: (c: CanvasRenderingContext2D, o: Parameters<NonNullable<typeof QP.hooks.status>>[1], sid: string) => void): HTMLCanvasElement {
  const cv = document.createElement("canvas");
  cv.width = cv.height = Math.round(px * res);
  const x = cv.getContext("2d")!;
  x.scale((px * res) / 100, (px * res) / 100);
  x.beginPath();
  x.arc(50, 50, 49, 0, Math.PI * 2);
  x.clip();
  const orig = QP.hooks.status;
  QP.hooks.status = hook ?? ((c, _o, sid) => {
    c.save();
    c.fillStyle = c.strokeStyle = statusColor(sid);
    c.lineWidth = 2.2;
    c.lineCap = c.lineJoin = "round";
    statusGlyph(c, sid);
    c.restore();
  });
  try {
    QP.chip(x, "status", id, 50, 50, 42, { ring: "rgba(255,255,255,0.3)", unitPx: px / 100, res });
  } finally {
    QP.hooks.status = orig;
  }
  return cv;
}

(window as unknown as Record<string, unknown>)["__qiStatusDev"] = { paint: QT.paint, cardCanvas: QT.cardCanvas, headCanvas: QT.headCanvas, glyph: QT.glyph, entry: QT.entry, list: () => QT.list(REAL_IDS), fitK: QT.fitK, fitKMeasured: QT.fitKMeasured, fitTable, fitKeys };

const st = (...ids: string[]): StatusView[] => ids.map((status_id) => ({ status_id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false }));

function board(): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < 6; y++) for (let x = 0; x < 9; x++) tiles.push(tile(x, y));
  const u = (id: string, team: "ally" | "enemy", x: number, y: number, statuses: StatusView[], over: Partial<UnitView> = {}): UnitView =>
    unit(id, team, x, y, { statuses, name_zh: id, ...over });
  const units: UnitView[] = [
    u(HERO, "ally", 1, 1, st("hasted", "empowered"), { template_id: "hero_fighter" }),
    u("unit_0002", "enemy", 3, 1, st("frozen")),
    u("unit_0003", "enemy", 5, 1, st("stun")),
    u("unit_0004", "ally", 7, 1, st("shielded", "regenerating")),
    u("unit_0005", "enemy", 1, 3, st("root", "slow")),
    u("unit_0006", "enemy", 3, 3, st("burning", "poison", "bleed")),
    u("unit_0007", "ally", 5, 3, st("concealed")),
    u("unit_0008", "enemy", 7, 3, st("stun", "burning", "poison", "weaken", "hasted", "empowered", "stance_fury")),
    // 上下相鄰：上面的單位血條不該被下面的單位狀態列蓋住
    u("unit_0009", "ally", 1, 4, st("guarded"), { hp: 6 }),
    u("unit_0010", "enemy", 1, 5, st("marked", "revealed", "time_bomb"), { hp: 8 }),
    u("unit_0011", "enemy", 3, 4, st("stun"), { downed: true, hp: 0 }),
    u("unit_0012", "ally", 5, 5, st("stun", "shielded", "poison"), { owner_id: HERO, summon_expires_round: 5, infused_skill_id: "x" } as Partial<UnitView>),
    u("unit_0013", "enemy", 7, 5, st("brand_new_status")),
  ];
  return {
    team: "ally",
    map_id: "status_gallery",
    map_name_zh: "狀態一覽",
    width: 9,
    height: 6,
    tiles,
    objects: [],
    units,
    traps: [],
    turn_order: [HERO],
    active_unit: HERO,
    round: 2,
    max_rounds: 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
  } as unknown as BattleView;
}

const HERO = "unit_0001";
if (q.get("scene") !== "0") {
  const box = document.createElement("div");
  box.className = "scene";
  box.appendChild(Object.assign(document.createElement("h2"), { textContent: "戰場（9×6，遊戲端畫法）：冰凍、暈眩、護盾、定身、燃燒／中毒、隱蔽、+N、上下相鄰、倒下、灌注召喚物" }));
  document.body.appendChild(box);
  const renderer = new BattleRenderer();
  await renderer.init(box);
  renderer.setScale(2);
  renderer.draw(buildDrawModel(board(), HERO));
}
document.body.dataset.ready = "1";
