// 開發用：裝備格圖示一覽（Phase 3G-G5a 起；QI-1b 改成 Q 版防具、飾品，清單由 gearAppearance.json 產生）。
// 開 `client/dev/gear-gallery.html`（自己的 vite 後 /dev/gear-gallery.html?mute=1）。不屬於正式 build（vite build 只打包 index.html）。
// 參數（驗收截圖用，規格 docs/phases/PhaseQI-1計畫.md 第 6 節 B4、第 8.2 節）：
//   ?px=<CSS px>        圖示邊長（預設 32；裝備格 32／40／42／48／64）
//   &res=<1|2>          內部解析度（預設 2＝遊戲現在的畫法；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>           放大 k 倍顯示（CSS zoom ＋ image-rendering: pixelated，最近鄰）；截圖用裝置像素比 1 拍
//   &rarity=<稀有度>     全部款式套這個稀有度（預設 common）
//   &set=armor|acc|all|dye|material|element|closeup|sizes|audit|doll（可用逗號接多段，例 material,element）
//        armor     防具 18 種 37 款（預設材質）
//        acc       飾品 3 種 7 款
//        all       防具＋飾品 44 款（預設；可配 &from=&n= 分張）
//        dye       黑、紅、藍、褐 × 長袍、斗篷帽、露指手套、長靴；布（長袍）、皮（皮背心）各 8 色；32 真 1 倍（×zoom）與 DPR 2（×zoom）各一段（忽略 &px、&res）
//        material  每種防具、飾品（第一款）× 全部可用材質（32 DPR 2；忽略 &px、&res）
//        element   4 個元素關鍵字混色（金屬：半身板甲、鐵盔；晶石：寶石戒；布：長袍；另含武器的金屬劍、晶石匕首、長杖、水晶球）＋非元素關鍵字（寶石換色）
//                  ＋>36px 小圖樣位置；32、48、64 DPR 2 各一段（忽略 &px、&res、&zoom）
//        closeup   點名款特寫：黑長袍、黑布兜帽、黑素手套、護膝脛甲、印戒、披風外套（32）；真 1 倍與 DPR 2 各一列（×zoom）
//        sizes     全部 44 款的 42、48、64（DPR 2 原大）
//        audit     規則 6 亮度自查表（深底裝備格 32px：圖樣平均亮度 ≥100、亮度 ≥150 的亮面 ≥5%）；黑染（tone=black）另列、不套門檻
//        doll      和人物並排：遊戲端 Q 版人物（`drawQLookPreview`）穿同一件，旁邊是 48px 圖示（DPR 2）
//   &from=<i>&n=<k>     set=all／armor 只列第 i 款起的 k 款
//   &label=0            不顯示名稱
// 另外掛 `window.__qiDev`（像素比對用）：gear(look, px, res)、art(look, a, res)（只有圖樣）、list。
import appearance from "../render/gearAppearance.json";
import type { DollEquipment } from "../render/dollGear";
import { resolveDoll } from "../render/appearance";
import { drawQLookPreview } from "../render/qLookPreview";
import { gearIconCanvas, gearQDef, resolveGear, type GearLook } from "../render/gearIcon";
import { GEAR_PAD, render } from "../render/qIcon/core";
import { qArmorDef, qArmorResolve } from "../render/qIcon/armor";

interface Form { id: string; zh: string; materials?: string[]; defaultMaterial?: string }
interface Kind { id: string; slotType: string; zh: string; forms: Form[]; materials: string[] }
interface Entry { look: GearLook; label: string; px?: number; res?: number; zoom?: number }

const q = new URLSearchParams(location.search);
const PX = Number(q.get("px") ?? 32);
const RES = Number(q.get("res") ?? 2);
const ZOOM = Number(q.get("zoom") ?? 1);
const RARITY = q.get("rarity") ?? "common";
const SET = q.get("set") ?? "all";
const LABEL = q.get("label") !== "0";

const ARMOR_TYPES = ["head", "body", "hands", "feet"];
const ACC_TYPES = ["ring", "neck"];
const KINDS = appearance.kinds as unknown as Kind[];
const ARMOR = KINDS.filter((k) => ARMOR_TYPES.includes(k.slotType));
const ACC = KINDS.filter((k) => ACC_TYPES.includes(k.slotType));
const entriesOf = (kinds: Kind[]): Entry[] => kinds.flatMap((k) => k.forms.map((f) => ({ look: { kind: k.id, form: f.id, rarity: RARITY }, label: f.zh })));
const ALL: Entry[] = entriesOf([...ARMOR, ...ACC]);

function cell(e: Entry): HTMLElement {
  const px = e.px ?? PX, res = e.res ?? RES;
  const box = document.createElement("div");
  box.className = "cell";
  const art = gearIconCanvas(e.look, px, undefined, res);
  if (art !== null) {
    const c = document.createElement("canvas");
    c.width = art.width;
    c.height = art.height;
    c.style.width = `${px}px`;
    c.style.height = `${px}px`;
    c.getContext("2d")?.drawImage(art, 0, 0);
    const zoomed = document.createElement("div");
    zoomed.className = "zoom";
    zoomed.style.zoom = String(e.zoom ?? ZOOM);
    zoomed.appendChild(c);
    box.appendChild(zoomed);
  }
  if (LABEL) {
    const t = document.createElement("div");
    t.className = "label";
    t.textContent = e.label;
    box.appendChild(t);
  }
  return box;
}

function section(title: string, entries: Entry[] | HTMLElement[]): void {
  const h = document.createElement("h2");
  h.textContent = title;
  const row = document.createElement("div");
  row.className = "row";
  for (const e of entries) row.appendChild(e instanceof HTMLElement ? e : cell(e));
  document.body.append(h, row);
}

const L = (kind: string, form: string, extra: Partial<GearLook> = {}): GearLook => ({ kind, form, rarity: RARITY, ...extra });
const resLabel = (res: number): string => (res === 1 ? "真 1 倍" : "DPR 2");

/** 規則 6 自查（照樣張 q-icons-armor.html 的 ?part=audit）：圖樣在裝備格 32px 的邊長、內部解析度 8、不含外框，量 α ≥ 200 的像素。 */
function lum(look: GearLook): { lum: number; bright: number } | null {
  const def = gearQDef(look, resolveGear(look));
  if (def === null) return null;
  const cv = render({ d: def.d }, 32 * (1 - GEAR_PAD * 2), 8, { ow: 0 });
  const ctx = cv?.getContext("2d");
  if (cv == null || ctx == null) return null;
  const S = cv.width, d = ctx.getImageData(0, 0, S, S).data;
  let n = 0, sum = 0, bright = 0;
  for (let i = 0; i < S * S * 4; i += 4) {
    if ((d[i + 3] ?? 0) < 200) continue;
    const Lm = 0.299 * (d[i] ?? 0) + 0.587 * (d[i + 1] ?? 0) + 0.114 * (d[i + 2] ?? 0);
    n += 1;
    sum += Lm;
    if (Lm >= 150) bright += 1;
  }
  return { lum: sum / n, bright: bright / n };
}

function audit(): void {
  const lines = ["kind/form | material | dye | 平均亮度 | 亮面(>=150) | 結果"];
  const black: string[] = ["", "---- 黑染（tone=black，規則 6 的例外，不套門檻；需求 3.3 第 18 點）----"];
  let bad = 0, badAll = 0, badDye = 0;
  const row = (k: Kind, f: Form, material: string | undefined, dye: string | undefined, tally: () => void): void => {
    const look: GearLook = { kind: k.id, form: f.id, ...(material !== undefined ? { material } : {}), ...(dye !== undefined ? { dye } : {}) };
    const m = lum(look);
    if (m === null) return;
    const isBlack = qArmorDef(qArmorResolve(resolveGear(look)))?.meta.tone === "black";
    const ok = m.lum >= 100 && m.bright >= 0.05;
    const text = `${k.id}/${f.id} | ${material ?? "(預設 " + (f.defaultMaterial ?? k.materials[0] ?? "") + ")"} | ${dye ?? "-"} | ${m.lum.toFixed(1)} | ${(m.bright * 100).toFixed(1)}% | `;
    if (isBlack) { black.push(text + "（例外）"); return; }
    if (!ok) tally();
    lines.push(text + (ok ? "過" : "不過" + (m.lum < 100 ? " 亮度" : "") + (m.bright < 0.05 ? " 亮面" : "")));
  };
  const kinds = [...ARMOR, ...ACC];
  for (const k of kinds) for (const f of k.forms) row(k, f, undefined, undefined, () => (bad += 1));
  lines.push(`預設材質共 ${ALL.length} 款，不過 ${bad} 款`, "", "---- 全部可用材質 ----");
  for (const k of kinds) for (const f of k.forms) for (const m of f.materials ?? k.materials) row(k, f, m, undefined, () => (badAll += 1));
  lines.push(`全部材質不過 ${badAll} 組`, "", "---- 染色（布、皮 × 8 色）----");
  const dyeable = appearance.dyeMaterials as string[];
  for (const k of kinds) for (const f of k.forms) for (const m of (f.materials ?? k.materials).filter((x) => dyeable.includes(x))) for (const dye of appearance.dyes) row(k, f, m, dye, () => (badDye += 1));
  lines.push(`染色不過 ${badDye} 組`, ...black);
  const pre = document.createElement("pre");
  pre.id = "audit";
  pre.textContent = lines.join("\n");
  document.body.appendChild(pre);
}

/** 人物（遊戲端 Q 版，`GAME_HOOKS`）穿同一件與圖示並排。 */
function dollCell(slot: string, look: GearLook, label: string): HTMLElement {
  const box = document.createElement("div");
  box.className = "cell doll";
  const equipment: DollEquipment[] = [{ slot, appearance: look }];
  const spec = resolveDoll({ template: "qi1b-doll", team: "ally", summon: false, weaponId: "", equipment });
  const pv = document.createElement("canvas");
  pv.style.width = "96px";
  pv.style.height = "120px";
  drawQLookPreview(pv, spec, "south", 96, 120, 2);
  const icon = document.createElement("div");
  icon.appendChild(cell({ look, label: "", px: 48, res: 2, zoom: 1 }));
  const pair = document.createElement("div");
  pair.className = "pair";
  pair.append(pv, icon);
  box.appendChild(pair);
  if (LABEL) {
    const t = document.createElement("div");
    t.className = "label";
    t.textContent = label;
    box.appendChild(t);
  }
  return box;
}

const SLOT_OF: Readonly<Record<string, string>> = { head: "head", body: "body", hands: "hands", feet: "feet", neck: "neck", ring: "ring_1" };

function show(SET: string): void {
if (SET === "audit") audit();
else if (SET === "dye") {
  const COLORS = ["black", "red", "blue", "brown"];
  const FOUR: ReadonlyArray<readonly [string, string, string]> = [["robe", "long", "長袍"], ["hood", "cowl", "斗篷帽"], ["cloth_gloves", "fingerless", "露指手套"], ["boots", "tall", "長靴"]];
  for (const res of [1, 2]) {
    section(`染色：黑紅藍褐 × 4 款（32、${resLabel(res)}、×${ZOOM}）`, COLORS.flatMap((dye) => FOUR.map(([k, f, zh]) => ({ look: L(k, f, { dye }), label: `${zh} ${dye}`, px: 32, res }))));
    section(`布（長袍）、皮（皮背心）各 8 色（32、${resLabel(res)}、×${ZOOM}）`, ["robe:long:長袍", "leather:vest:皮背心"].flatMap((s) => {
      const [k, f, zh] = s.split(":") as [string, string, string];
      return [{ look: L(k, f), label: `${zh} 未染`, px: 32, res }, ...appearance.dyes.map((dye) => ({ look: L(k, f, { dye }), label: `${zh} ${dye}`, px: 32, res }))];
    }));
  }
} else if (SET === "material") {
  section("每種防具、飾品（第一款）的全部可用材質（32、DPR 2）", [...ARMOR, ...ACC].flatMap((k) => {
    const f = k.forms[0] as Form;
    return (f.materials ?? k.materials).map((m) => ({ look: L(k.id, f.id, { material: m }), label: `${k.zh} ${m}`, px: 32, res: 2 }));
  }));
  section("另一款有自己材質表的（頭冠、臂環）", [L("circlet", "crown"), L("bracers", "ring")].flatMap((l) => {
    const k = KINDS.find((x) => x.id === l.kind) as Kind, f = k.forms.find((x) => x.id === l.form) as Form;
    return (f.materials ?? k.materials).map((m) => ({ look: { ...l, material: m }, label: `${f.zh} ${m}`, px: 32, res: 2 }));
  }));
} else if (SET === "element") {
  const EL_KW = appearance.elementKeywords as string[];
  for (const px of [32, 48, 64]) {
    section(`元素混色（${px}、DPR 2）：金屬（半身板甲、鐵盔、直劍）、晶石（寶石戒、匕首）、布（長袍）、杖頭（長杖）、法器珠（水晶球）`, EL_KW.flatMap((kw) => [
      { look: L("plate", "half", { keywords: [kw] }), label: `板甲 ${kw}` },
      { look: L("helmet", "iron", { keywords: [kw] }), label: `鐵盔 ${kw}` },
      { look: L("ring", "gem", { material: "crystal", keywords: [kw] }), label: `晶石戒 ${kw}` },
      { look: L("robe", "long", { keywords: [kw] }), label: `長袍 ${kw}` },
      { look: L("sword", "straight", { keywords: [kw] }), label: `劍 ${kw}` },
      { look: L("dagger", "short", { material: "crystal", keywords: [kw] }), label: `晶石匕首 ${kw}` },
      { look: L("staff", "long", { keywords: [kw] }), label: `長杖 ${kw}` },
      { look: L("orb", "ball", { keywords: [kw] }), label: `水晶球 ${kw}` },
    ].map((e) => ({ ...e, px, res: 2, zoom: 1 }))));
    section(`非元素關鍵字（寶石換關鍵字色；>36px 疊小圖樣）（${px}、DPR 2）`, [
      { look: L("ring", "gem", { keywords: ["marked"] }), label: "寶石戒 marked" },
      { look: L("ring", "gem"), label: "寶石戒（無）" },
      { look: L("pendant", "pendant", { keywords: ["summon"] }), label: "項鍊墜 summon" },
      { look: L("circlet", "crown", { keywords: ["prone", "ignite"] }), label: "頭冠 prone+ignite" },
      { look: L("circlet", "crown", { keywords: ["ignite", "prone"] }), label: "頭冠 ignite+prone" },
      { look: L("tome", "book", { keywords: ["marked"] }), label: "典籍 marked" },
      { look: L("mail", "chain", { keywords: ["wet", "high_ground"] }), label: "鎖甲 wet+high_ground" },
    ].map((e) => ({ ...e, px, res: 2, zoom: 1 })));
  }
} else if (SET === "closeup") {
  const close: Entry[] = [
    { look: L("robe", "long", { dye: "black" }), label: "黑長袍" },
    { look: L("hood", "cloth", { dye: "black" }), label: "黑布兜帽" },
    { look: L("cloth_gloves", "plain", { dye: "black" }), label: "黑素手套" },
    { look: L("greaves", "knee"), label: "護膝脛甲" },
    { look: L("ring", "signet"), label: "印戒" },
    { look: L("coat", "cape"), label: "披風外套" },
  ];
  for (const res of [1, 2]) section(`特寫（32、${resLabel(res)}、×${ZOOM}）`, close.map((e) => ({ ...e, px: 32, res })));
} else if (SET === "sizes") {
  for (const px of [42, 48, 64]) section(`防具＋飾品 ${ALL.length} 款（${px}、DPR 2 原大）`, ALL.map((e) => ({ ...e, px, res: 2, zoom: 1 })));
} else if (SET === "doll") {
  section("和人物並排（遊戲端 Q 版人物 × 48px 圖示，DPR 2；戒指人物身上不畫）", [...ARMOR, ...ACC].flatMap((k) => k.forms.map((f) => dollCell(SLOT_OF[k.slotType] ?? "body", L(k.id, f.id), `${k.zh}・${f.zh}`))));
} else {
  const base = SET === "armor" ? entriesOf(ARMOR) : SET === "acc" ? entriesOf(ACC) : ALL;
  const from = Number(q.get("from") ?? 0), n = Number(q.get("n") ?? base.length), part = base.slice(from, from + n);
  section(`${SET === "armor" ? "防具" : SET === "acc" ? "飾品" : "防具＋飾品"} ${base.length} 款${part.length < base.length ? `（第 ${from + 1}～${from + part.length} 款）` : ""}（裝備格 ${PX}px、${RES === 1 ? "真 1 倍" : `res ${RES}`}、×${ZOOM}）`, part);
}
}
for (const s of SET.split(",")) show(s); // 例：&set=material,element 兩段畫在同一頁（截圖合張用）
document.body.dataset["ready"] = "1";

declare global {
  interface Window {
    __qiDev?: unknown;
  }
}
window.__qiDev = {
  gear: (look: GearLook, px: number, res: number) => gearIconCanvas(look, px, undefined, res),
  /** 只有圖樣（不含框；和樣張 `QIcons.render(QIconsArmor.def(look).d …)` 逐像素比對用）。 */
  art: (look: GearLook, a: number, res: number) => {
    const def = gearQDef(look, resolveGear(look));
    return def === null ? null : render(def, a, res);
  },
  list: ALL.map((e) => e.look),
};
