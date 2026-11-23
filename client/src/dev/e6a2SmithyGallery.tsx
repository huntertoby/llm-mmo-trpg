// 開發用：E6-a2 打造指定招牌類型（開 `client/dev/e6a2-smithy.html`；自己的 vite 後 /dev/e6a2-smithy.html?mute=1）。不屬於正式 build。
// 正式的 `SmithyPanel`（打造分頁）＋正式樣式，資料是假的（現有內容還沒有標招牌的詞條，實機到不了）：
// - 左：開關打開，詞條下拉多一組「或指定招牌類型」；
// - 中：同一張，下拉展開（`size`）並選了「招牌：新動作」；
// - 右：開關關著（後端給空的 `signatures`），和原本一樣。
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
  level_cap: grade ? 7 : null,
  leaning_zh,
  resonance_zh: null,
});

const KW = [
  { id: "affix_kw_burn_duration", text_zh: "你施加的燃燒 +1 回合" },
  { id: "affix_kw_ignite_damage", text_zh: "點燃技能傷害 +6%" },
];
const SIGS = [
  { id: "action", text_zh: "招牌：新動作" },
  { id: "behavior", text_zh: "招牌：行為改寫" },
];

function crafting(on: boolean): WorldCrafting {
  return {
    stations: [{ station: "smithy_mist_ferry", kind: "smithy", name_zh: "石記鐵鋪", npc_name_zh: "石師傅" }],
    smithy: "smithy_mist_ferry",
    enchanter: null,
    can_use: true,
    problem_zh: null,
    slots: [
      { slot_type: "weapon", name_zh: "武器", grade_amount: 3, affixes: KW, signatures: on ? SIGS : [] },
      { slot_type: "head", name_zh: "頭", grade_amount: 1, affixes: [{ id: "affix_cond_height_hit", text_zh: "站得比目標高：命中 +5%" }], signatures: [], uniques: [] },
    ],
    rarities: [
      { rarity: "rare", name_zh: "稀有", cost_zh: "金幣 10 × 物品等級", slots: [] },
      { rarity: "epic", name_zh: "史詩", cost_zh: "金幣 20 × 物品等級＋任務幣 2", slots: [] },
    ],
    materials: [mat("item_fine_material", "精料", 5, true), mat("item_mist_crystal", "霧晶", 2, false, "傾向：敏捷 +n"), mat("item_wolf_fang", "狼牙", 4, false, "傾向：力量 +n")],
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

column("開關打開：詞條下拉多一組「或指定招牌類型」", true);
const open = column("開關打開：下拉展開、選了「招牌：新動作」", true);
column("開關關著：和原本一樣（沒有招牌選項）", false);

const select = open.querySelector<HTMLSelectElement>('[data-testid="world-craft-affix"]');
if (select !== null) {
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
  setter?.call(select, "signature:action");
  select.dispatchEvent(new Event("change", { bubbles: true }));
  select.size = 6;
}
window.setTimeout(() => {
  document.body.dataset.ready = "1";
}, 300);
