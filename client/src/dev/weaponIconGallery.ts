// 開發用：武器、副手的 Q 版小圖示一覽（Phase 3T-4b 起；QI-1a 改成 Q 版、清單由 gearAppearance.json 產生）。
// 開 `client/dev/weaponicon-gallery.html`（自己的 vite 後 /dev/weaponicon-gallery.html?mute=1）。不屬於正式 build。
// 參數（驗收截圖用，規格 docs/phases/PhaseQI-1計畫.md 第 6 節 A7、第 8.2 節）：
//   ?px=<CSS px>        圖示邊長（預設 28；圓章 20／24／28、裝備格 32／48／64）
//   &res=<1|2>          內部解析度（預設 2＝遊戲現在的畫法；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>           放大 k 倍顯示（CSS zoom ＋ image-rendering: pixelated，最近鄰）；截圖用裝置像素比 1 拍
//   &frame=badge|gear   米色圓章（底用和 `.weapon-icon` 同樣的 CSS）或裝備格（`gearIcon` 的框）；預設 badge
//   &rarity=<稀有度>     全部款式套這個稀有度（預設 common）
//   &set=all|sizes|rarity|material|element|closeup|audit
//        all       武器 17 種 53 款＋副手 4 種 8 款（預設材質）
//        sizes     全部 61 款的圓章 24、28 與裝備格 48、64（DPR 2 原大）
//        rarity    直劍、鳶盾 × 5 種稀有度：裝備格 32 真 1 倍（×zoom）一列、64 DPR 2 原大一列
//        material  每種武器、副手（第一款）× 全部可用材質
//        element   4 個元素關鍵字（金屬劍、晶石匕首、長杖、水晶球）＋一個非元素關鍵字（典籍的寶石換色）
//        closeup   點名款特寫：鞭三款、雙左輪、雙彎匕、弓三款、拳刃（圓章）；拳刃、蛇骨鞭（裝備格）；真 1 倍與 DPR 2 各一列（忽略 &res、&frame）
//        audit     規則 6 亮度自查表（深底裝備格 32px：圖樣平均亮度 ≥100、亮度 ≥150 的亮面 ≥5%），每款預設材質＋全部材質
//   &from=<i>&n=<k>     set=all 只列第 i 款起的 k 款（截圖分張用）
//   &label=0            不顯示名稱
// 另外掛 `window.__qiDev`（像素比對用）：badge(look, px, res)、gear(look, px, res)、list。
import appearance from "../render/gearAppearance.json";
import type { GearItem } from "../render/appearance";
import { gearIconCanvas, type GearLook } from "../render/gearIcon";
import { GEAR_PAD, render } from "../render/qIcon/core";
import { weaponIconDef, weaponItemIconCanvas } from "../render/weaponIcon";

interface Form { id: string; zh: string; materials?: string[]; defaultMaterial?: string }
interface Kind { id: string; slotType: string; zh: string; forms: Form[]; materials: string[] }
interface Entry { look: GearLook & GearItem; label: string; frame?: "badge" | "gear"; px?: number; res?: number; zoom?: number }

const q = new URLSearchParams(location.search);
const PX = Number(q.get("px") ?? 28);
const RES = Number(q.get("res") ?? 2);
const ZOOM = Number(q.get("zoom") ?? 1);
const FRAME = q.get("frame") === "gear" ? "gear" : "badge";
const RARITY = q.get("rarity") ?? "common";
const SET = q.get("set") ?? "all";
const LABEL = q.get("label") !== "0";

const KINDS = (appearance.kinds as unknown as Kind[]).filter((k) => k.slotType === "weapon" || k.slotType === "offhand");
/** 全部款式（kind × form），預設材質。 */
const ALL: Entry[] = KINDS.flatMap((k) => k.forms.map((f) => ({ look: { kind: k.id, form: f.id, rarity: RARITY }, label: k.id.startsWith("dual_") ? `雙・${f.zh}` : f.zh })));

/** 一個圖示（含框）的畫布：圓章＝透明圖樣（底是 CSS）；裝備格＝含框。 */
function iconCanvas(look: GearLook & GearItem, frame: "badge" | "gear", px: number, res: number): HTMLCanvasElement | null {
  return frame === "badge" ? weaponItemIconCanvas(look, px, res) : gearIconCanvas(look, px, "main_hand", res);
}

function cell(e: Entry): HTMLElement {
  const frame = e.frame ?? FRAME, px = e.px ?? PX, res = e.res ?? RES;
  const box = document.createElement("div");
  box.className = "cell";
  const art = iconCanvas(e.look, frame, px, res);
  if (art !== null) {
    const c = document.createElement("canvas");
    c.width = art.width;
    c.height = art.height;
    c.style.width = `${px}px`;
    c.style.height = `${px}px`;
    if (frame === "badge") c.className = "weapon-icon";
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

function section(title: string, entries: Entry[]): void {
  const h = document.createElement("h2");
  h.textContent = title;
  const row = document.createElement("div");
  row.className = "row";
  for (const e of entries) row.appendChild(cell(e));
  document.body.append(h, row);
}

/** 規則 6 自查（照樣張 q-icons-weapons.html 的 ?part=audit）：圖樣在裝備格 32px 的邊長、內部解析度 8、不含外框，量 α ≥ 200 的像素。 */
function lum(look: GearLook & GearItem): { lum: number; bright: number } | null {
  const def = weaponIconDef(look);
  if (def === null) return null;
  const cv = render({ d: def.d }, 32 * (1 - GEAR_PAD * 2), 8, { ow: 0 });
  const ctx = cv?.getContext("2d");
  if (cv == null || ctx == null) return null;
  const S = cv.width, d = ctx.getImageData(0, 0, S, S).data;
  let n = 0, sum = 0, bright = 0;
  for (let i = 0; i < S * S * 4; i += 4) {
    if ((d[i + 3] ?? 0) < 200) continue;
    const L = 0.299 * (d[i] ?? 0) + 0.587 * (d[i + 1] ?? 0) + 0.114 * (d[i + 2] ?? 0);
    n += 1;
    sum += L;
    if (L >= 150) bright += 1;
  }
  return { lum: sum / n, bright: bright / n };
}

function audit(): void {
  const lines = ["kind/form | material | 平均亮度 | 亮面(>=150) | 結果"];
  let bad = 0, badAll = 0;
  const row = (k: Kind, f: Form, material: string | undefined, tally: () => void): void => {
    const m = lum({ kind: k.id, form: f.id, ...(material !== undefined ? { material } : {}) });
    if (m === null) return;
    const ok = m.lum >= 100 && m.bright >= 0.05;
    if (!ok) tally();
    lines.push(`${k.id}/${f.id} | ${material ?? "(預設 " + (f.defaultMaterial ?? "") + ")"} | ${m.lum.toFixed(1)} | ${(m.bright * 100).toFixed(1)}% | ${ok ? "過" : "不過" + (m.lum < 100 ? " 亮度" : "") + (m.bright < 0.05 ? " 亮面" : "")}`);
  };
  for (const k of KINDS) for (const f of k.forms) row(k, f, undefined, () => (bad += 1));
  lines.push(`預設材質共 ${ALL.length} 款，不過 ${bad} 款`, "", "---- 全部可用材質 ----");
  for (const k of KINDS) for (const f of k.forms) for (const m of f.materials ?? k.materials) row(k, f, m, () => (badAll += 1));
  lines.push(`全部材質不過 ${badAll} 組`);
  const pre = document.createElement("pre");
  pre.id = "audit";
  pre.textContent = lines.join("\n");
  document.body.appendChild(pre);
}

const L = (kind: string, form: string, extra: Partial<GearLook & GearItem> = {}): GearLook & GearItem => ({ kind, form, rarity: RARITY, ...extra });

if (SET === "audit") audit();
else if (SET === "rarity") {
  // 裝備格 32 真 1 倍（×zoom）與 64 DPR 2（原大）各一列（忽略 &px、&res、&frame）
  for (const [px, res, zoom] of [[32, 1, ZOOM], [64, 2, 1]] as const) {
    section(`直劍、鳶盾 × 稀有度（裝備格 ${px}px、${res === 1 ? "真 1 倍" : "DPR 2"}、×${zoom}）`, (["sword:straight:直劍", "kite_shield:kite:鳶盾"] as const).flatMap((s) => {
      const [kind, form, zh] = s.split(":") as [string, string, string];
      return appearance.rarities.map((r) => ({ look: { kind, form, rarity: r }, label: `${zh} ${r}`, frame: "gear" as const, px, res, zoom }));
    }));
  }
} else if (SET === "sizes") {
  // 原大（×1）：圓章 24、28 與裝備格 48、64，DPR 2（忽略 &px、&res、&frame、&zoom）
  for (const [frame, px] of [["badge", 24], ["badge", 28], ["gear", 48], ["gear", 64]] as const) {
    section(`${frame === "badge" ? "圓章" : "裝備格"} ${px}px（DPR 2）`, ALL.map((e) => ({ ...e, frame, px, res: 2, zoom: 1 })));
  }
} else if (SET === "material") {
  section("每種武器、副手的全部可用材質", KINDS.flatMap((k) => {
    const f = k.forms[0] as Form;
    return (f.materials ?? k.materials).map((m) => ({ look: L(k.id, f.id, { material: m }), label: `${k.zh} ${m}` }));
  }));
  section("鞭全部材質（鏈鞭的銀、骨暗節）", ["leather", "chain", "bladed"].flatMap((form) => ["leather", "iron", "steel", "copper", "silver", "gold", "bone"].map((m) => ({ look: L("whip", form, { material: m }), label: `${form} ${m}` }))));
} else if (SET === "element") {
  const EL_KW = appearance.elementKeywords as string[];
  section("元素關鍵字：金屬（直劍）、晶石（匕首）、杖頭（長杖）、法器珠（水晶球）", EL_KW.flatMap((kw) => [
    { look: L("sword", "straight", { keywords: [kw] }), label: `劍 ${kw}` },
    { look: L("dagger", "short", { material: "crystal", keywords: [kw] }), label: `晶石匕首 ${kw}` },
    { look: L("staff", "long", { keywords: [kw] }), label: `長杖 ${kw}` },
    { look: L("orb", "ball", { keywords: [kw] }), label: `水晶球 ${kw}` },
  ]));
  section("非元素關鍵字（寶石換關鍵字色、>36px 疊小圖樣）", [
    { look: L("tome", "book", { keywords: ["marked"] }), label: "典籍 marked" },
    { look: L("tome", "book"), label: "典籍（無）" },
    { look: L("sword", "straight", { keywords: ["ignite", "marked"] }), label: "劍 ignite+marked" },
    { look: L("fist", "katar", { keywords: ["frozen"] }), label: "拳刃 frozen" },
  ]);
} else if (SET === "closeup") {
  const badge: Entry[] = [
    ...["leather", "chain", "bladed"].map((f) => ({ look: L("whip", f), label: `鞭 ${f}` })),
    { look: L("dual_pistol", "revolver"), label: "雙左輪" },
    { look: L("dual_dagger", "kris"), label: "雙彎匕" },
    ...["short", "long", "recurve"].map((f) => ({ look: L("bow", f), label: `弓 ${f}` })),
    { look: L("fist", "katar"), label: "拳刃" },
  ];
  const gear: Entry[] = [{ look: L("fist", "katar"), label: "拳刃 32" }, { look: L("whip", "bladed"), label: "蛇骨鞭 32" }];
  for (const res of [1, 2]) {
    section(`特寫（${res === 1 ? "真 1 倍" : "DPR 2"}、×${ZOOM}）`, [
      ...badge.map((e) => ({ ...e, frame: "badge" as const, px: 20, res })),
      ...gear.map((e) => ({ ...e, frame: "gear" as const, px: 32, res })),
    ]);
  }
} else {
  const from = Number(q.get("from") ?? 0), n = Number(q.get("n") ?? ALL.length), part = ALL.slice(from, from + n);
  section(`武器＋副手 ${ALL.length} 款${part.length < ALL.length ? `（第 ${from + 1}～${from + part.length} 款）` : ""}（${FRAME === "badge" ? "圓章" : "裝備格"} ${PX}px、${RES === 1 ? "真 1 倍" : `res ${RES}`}、×${ZOOM}）`, part);
}
document.body.dataset["ready"] = "1";

declare global {
  interface Window {
    __qiDev?: unknown;
  }
}
window.__qiDev = {
  badge: (look: GearLook & GearItem, px: number, res: number) => weaponItemIconCanvas(look, px, res),
  gear: (look: GearLook & GearItem, px: number, res: number) => gearIconCanvas(look, px, "main_hand", res),
  list: ALL.map((e) => e.look),
};
