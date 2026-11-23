// 開發用：E6-c2 打造傳說（開 `client/dev/e6c2-smithy.html`；自己的 vite 後 /dev/e6c2-smithy.html?mute=1）。不屬於正式 build。
// 正式的 `SmithyPanel`（打造分頁）＋正式樣式，資料是假的（傳說開關預設關，實機到不了）：
// - 左：開關打開，選了傳說：部位只剩主手、副手、身體、腳、項鍊，費用寫上料，下拉多一組「或指定獨特效果類型」；
// - 中：同一張，下拉展開（`size`）並選了「獨特效果：改寫規則」；
// - 右：開關關著（後端不列傳說），稀有度只有稀有、史詩，和原本一樣。
// 畫好後 `document.body.dataset.ready = "1"`。
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { WorldCrafting } from "../api/types";
import { waitForFonts } from "../render/fontLoad";
import { SmithyPanel } from "../world/SmithyPanel";
import "../styles/index.css";

await waitForFonts();

const mat = (item: string, name_zh: string, count: number, grade: boolean, leaning_zh: string | null = null) => ({
  item,
  name_zh,
  count,
  grade,
  level_cap: grade ? 8 : null,
  leaning_zh,
  resonance_zh: null,
});

const KW = [
  { id: "affix_kw_burn_duration", text_zh: "你施加的燃燒 +1 回合" },
  { id: "affix_kw_ignite_damage", text_zh: "點燃技能傷害 +6%" },
];
const UNIQUES = [
  { id: "action", text_zh: "獨特效果：新動作" },
  { id: "rule", text_zh: "獨特效果：改寫規則" },
];
const LEGEND_SLOTS = ["weapon", "offhand", "body", "feet", "neck"];

function slot(slot_type: string, name_zh: string, grade_amount: number, on: boolean, uniques = UNIQUES) {
  return { slot_type, name_zh, grade_amount, affixes: KW, signatures: [], uniques: on && LEGEND_SLOTS.includes(slot_type) ? uniques : [] };
}

function crafting(on: boolean): WorldCrafting {
  const rarities = [
    { rarity: "rare", name_zh: "稀有", cost_zh: "金幣 10 × 物品等級", slots: [] },
    { rarity: "epic", name_zh: "史詩", cost_zh: "金幣 20 × 物品等級＋任務幣 2", slots: [] },
  ];
  if (on) rarities.push({ rarity: "legendary", name_zh: "傳說", cost_zh: "金幣 40 × 物品等級＋任務幣 5＋上料 ×1", slots: LEGEND_SLOTS as never });
  return {
    stations: [{ station: "smithy_mist_ferry", kind: "smithy", name_zh: "石記鐵鋪", npc_name_zh: "石師傅" }],
    smithy: "smithy_mist_ferry",
    enchanter: null,
    can_use: true,
    problem_zh: null,
    slots: [
      slot("weapon", "武器", 3, on, [{ id: "action", text_zh: "獨特效果：新動作" }, { id: "behavior", text_zh: "獨特效果：行為改寫" }, { id: "rule", text_zh: "獨特效果：改寫規則" }]),
      slot("offhand", "副手", 1, on),
      slot("head", "頭", 1, on),
      slot("body", "身體", 2, on),
      slot("hands", "手", 1, on),
      slot("feet", "腳", 1, on),
      slot("neck", "項鍊", 1, on),
      slot("ring", "戒指", 1, on),
    ],
    rarities,
    materials: [mat("item_superior_material", "上料", 6, true), mat("item_mist_crystal", "霧晶", 2, false, "傾向：敏捷 +n"), mat("item_wolf_fang", "狼牙", 4, false, "傾向：力量 +n")],
    flavor_max: 3,
    recipes: [],
    gear: [],
    essence: 0,
    note_zh: "沒人試過的材料組合只看得到傾向",
  } as unknown as WorldCrafting;
}

const NOOP = (): void => undefined;
const row = document.createElement("div");
row.className = "row";
document.body.append(row);

function setSelect(pane: HTMLElement, testid: string, value: string): HTMLSelectElement | null {
  const select = pane.querySelector<HTMLSelectElement>(`[data-testid="${testid}"]`);
  if (select === null) return null;
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
  flushSync(() => {
    setter?.call(select, value);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
  return select;
}

function column(caption: string, on: boolean): HTMLElement {
  const box = document.createElement("div");
  box.className = "col";
  const title = document.createElement("h2");
  title.textContent = caption;
  const pane = document.createElement("div");
  pane.className = "panel world-screen-pane world-smithy-screen";
  box.append(title, pane);
  row.append(box);
  flushSync(() => createRoot(pane).render(<SmithyPanel crafting={crafting(on)} busy={false} onAct={NOOP} initialTab="craft" />));
  return pane;
}

const left = column("開關打開，選了傳說：部位只剩五個、費用寫上料", true);
setSelect(left, "world-craft-rarity", "legendary");
setSelect(left, "world-craft-slot", "neck");
const open = column("開關打開：下拉展開、選了「獨特效果：改寫規則」", true);
setSelect(open, "world-craft-rarity", "legendary");
setSelect(open, "world-craft-slot", "neck");
const affix = setSelect(open, "world-craft-affix", "signature:rule");
if (affix !== null) affix.size = 6;
const slots = open.querySelector<HTMLSelectElement>('[data-testid="world-craft-slot"]');
if (slots !== null) slots.size = 5;
column("開關關著：稀有度只有稀有、史詩（和原本一樣）", false);
window.setTimeout(() => {
  document.body.dataset.ready = "1";
}, 300);
