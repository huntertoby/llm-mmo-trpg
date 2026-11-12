// 開發用：狀態圖示與身上特效一覽（Phase 3-36a；QI-3a 加 Q 版狀態圖示的參數）。開 `client/dev/status-gallery.html`（自己的 vite 後 /dev/status-gallery.html?mute=1）。
// 不屬於正式 build；供美術 PM 驗收與截圖。上：名詞表全部狀態（118 個）的圖示；下：用真正的 BattleRenderer 畫的 9×6 戰場（頭頂狀態列、+N、冰凍／暈眩／護盾／
// 定身／持續傷害、隱蔽、上下相鄰單位的血條、倒下、灌注召喚物；**仍是現行畫法**——QI-3a 不接到遊戲畫面，3b 接線後才變）。
// 上半（QI-3a，規格 docs/phases/PhaseQI-3計畫.md A4、第 8.2 節）：直接呼叫 `render/qIcon/status.ts` 的 `cardCanvas`／`headCanvas`（3b 改走遊戲端）。參數：
//   ?px=<CSS px,…>       圖示邊長，可逗號給多個（預設 52）：20＝狀態卡構圖（cardCanvas：100 單位方塊、半徑 49 圓形裁切、框 16.8）；
//                        其他（11＝頭頂構圖、52＝原總表）＝headCanvas（框邊長 px−2）。`&kind=card|head` 強制指定
//   &res=<1|2,…>         內部解析度，可逗號給多個（預設 2＝遊戲；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>            放大 k 倍顯示（image-rendering: pixelated，最近鄰）；截圖用裝置像素比 1 拍
//   &set=<名稱,…>        all（名詞表全部，預設）｜ctrl｜debuff｜buff｜shield｜neutral｜stance｜element（元素架勢 9 × 5 級）｜boss
//                        ｜near（撞圖組：暖色四六角、冷色四六角、岩石／殼／甲七個、晶能兩個）｜cls（控制類 7 個＋tint=0 對照列）
//                        ｜unknown（brand_new_status、空字串、增益／減益／中性／有類別的假狀態各一）
//                        ｜fitgen（在這個瀏覽器量 fitK 表：結果放 `body.dataset.fit`（statusFit.json 的內容），不畫圖）
//                        ｜compare（和樣張逐像素比，見下）｜none（上半不畫）
//   &tint=0              不染類別底色（對照用）
//   &from=<i>&n=<k>      清單只取第 i 個起的 k 個（截圖分張用）
//   &label=0             不顯示名稱
//   &old=1               每格後面並排現行畫法（statusIcon.ts 的 paintStatusIcon，同尺寸、同 res）
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
import { paintStatusIcon } from "../render/statusIcon";

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
/** Q 版（3a：直接畫 status.ts）。 */
function qIcon(id: string, px: number, res: number, tint: boolean): HTMLCanvasElement {
  const opt = { res, tint };
  return shown((isCard(px) ? QT.cardCanvas(id, px, 1, opt) : QT.headCanvas(id, px, 1, opt))!, px);
}
/** 現行畫法（paintStatusIcon）：同一個構圖、同 res。 */
function oldIcon(id: string, px: number, res: number): HTMLCanvasElement {
  const cv = document.createElement("canvas");
  cv.width = cv.height = Math.round(px * res);
  const x = cv.getContext("2d")!;
  if (isCard(px)) {
    x.scale((px * res) / 100, (px * res) / 100);
    x.beginPath();
    x.arc(50, 50, 49, 0, Math.PI * 2);
    x.clip();
    paintStatusIcon(x, id, 50, 50, 84);
  } else {
    x.scale(res, res);
    paintStatusIcon(x, id, px / 2, px / 2, px - 2);
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

const top = h("div");
document.body.append(top);
top.append(h("h1", { textContent: `狀態圖示一覽：名詞表 ${REAL_IDS.length} 個狀態（Q 版，QI-3a 直接畫 qIcon/status.ts；圓＝增益、方＝減益、六角＝中性）` }));
for (const s of SETS) {
  if (s === "all") section(`全部 ${REAL_IDS.length} 個（名詞表順序）`, REAL_IDS);
  else if (GROUPS[s]) section(GROUPS[s][0], GROUPS[s][1]);
  else if (s === "near") for (const [t, ids] of NEAR) section(t, ids);
  else if (s === "cls") { section("控制類 7 個（染類別底色）", GROUPS["ctrl"]![1], true); section("控制類 7 個 tint=0（不染底，對照）", GROUPS["ctrl"]![1], false); }
  else if (s === "unknown") section("不認得的狀態：brand_new_status、空字串、假狀態（增益／減益／中性／硬控）", UNKNOWN);
  else if (s === "fitgen") { const t = fitTable(); document.body.dataset.fit = JSON.stringify({ _note: "由開發頁 client/dev/status-gallery.html?set=fitgen 在 Chrome（無頭、--disable-gpu＝軟體繪製，同美術自查表 qicons_shots.py）量出（render/qIcon/status.ts 的 fitKMeasured，樣張 fitK 的逐行搬）；不手改。鍵＝id|框邊長 toFixed(2)|inset toFixed(2)", fit: t }, null, 1); top.append(h("pre", { className: "out" }, `fitK：${Object.keys(t).length} 筆`)); }
  else if (s === "compare") await compare();
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
  box.appendChild(Object.assign(document.createElement("h2"), { textContent: "戰場（9×6，現行畫法）：冰凍、暈眩、護盾、定身、燃燒／中毒、隱蔽、+N、上下相鄰、倒下、灌注召喚物" }));
  document.body.appendChild(box);
  const renderer = new BattleRenderer();
  await renderer.init(box);
  renderer.setScale(2);
  renderer.draw(buildDrawModel(board(), HERO));
}
document.body.dataset.ready = "1";
