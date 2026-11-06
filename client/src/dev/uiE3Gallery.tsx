// 開發用：UI-E3 面板圖示化（開 `client/uie3-gallery.html`，pnpm dev 後 /uie3-gallery.html?char=<角色 ID>）；不屬於正式 build。
// 畫面用正式元件、正式彈窗（`PopupFrame` 的 hud 位置、`.world-hud-panel`）與樣式；資料是伺服器回的這個角色的世界畫面
// （`GET /api/world/characters/{id}`），實機一時到不了的狀態才在上面疊固定資料：
// - `#bag-full`：穿戴中多幾件、背包裡有裝備、消耗品、材料、別大類的武器（6T-1b 的兩行字），選了別大類那一格；
// - `#bag-confirm`：同上，按下「換上」後的別大類確認框；
// - `#hire`：雇用面板（正式 `HudHirePanel`，傭兵的技能圖示列用真的 `/api/builds` 與技能卡）。
import { useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { api } from "../api/client";
import type { GearCandidate, GearItemInfo, WorldBagItem, WorldInventory, WorldView } from "../api/types";
import { PopupFrame } from "../ui/PopupFrame";
import { useRegionTheme } from "../ui/regionTheme";
import { WorldBagScreen } from "../world/BagScreen";
import { HudHirePanel } from "../world/FieldPanels";
import { hudLayout, isNarrow, popupBox } from "../world/hud";

/** 正式畫面 HUD 舞台上方的標題列高度（px）。 */
const STAGE_TOP = 60;
import "../styles/index.css";

function gear(id: string, name: string, slot: string, look: Record<string, unknown>, over: Partial<GearItemInfo> = {}): GearItemInfo {
  return {
    id,
    name_zh: name,
    slot_type: slot === "main_hand" ? "weapon" : slot,
    weapon: null,
    weapon_name_zh: null,
    offhand: null,
    offhand_name_zh: null,
    offhand_traits_zh: [],
    two_handed: false,
    paired: false,
    tags: [],
    legendary: false,
    affixes: [{ affix_id: "affix_attr_str", text_zh: "力量 +2" }],
    appearance: { form: null, dye: null, style: null, keywords: [], rarity: "uncommon", ...look },
    rarity: "uncommon",
    rarity_zh: "優良",
    item_level: 3,
    base_bonus_zh: null,
    points: 20,
    ...over,
  } as unknown as GearItemInfo;
}

function row(item: string, name: string, kind: string, count: number, over: Partial<WorldBagItem> = {}): WorldBagItem {
  return { item, name_zh: name, kind_zh: kind, count, description_zh: "", sell_price: 5, sellable: true, tradable: true, field_usable: false, gear: false, can_equip: false, ...over } as WorldBagItem;
}

/** 疊固定資料：穿戴中多 3 件、背包 2 件裝備（其中一把別大類的弓）、消耗品與材料、腰包 1 種。 */
function fullBag(inv: WorldInventory): WorldInventory {
  const head = gear("item_demo_helm", "鐵盔", "head", { kind: "helmet", material: "iron" });
  const body = gear("item_demo_mail", "旅人皮甲", "body", { kind: "leather", material: "leather" });
  const ring = gear("item_demo_ring", "霧紋戒指", "ring_1", { kind: "ring", material: "silver" });
  const bow = gear("item_demo_bow", "紫電長弓", "main_hand", { kind: "bow", material: "wood", rarity: "rare" }, { rarity: "rare", rarity_zh: "稀有", weapon: "bow", weapon_name_zh: "弓", two_handed: true });
  const boots = gear("item_demo_boots", "踏雲靴", "feet", { kind: "boots", material: "leather" });
  const equipment = (inv.equipment ?? []).map((e) =>
    e.slot === "head" ? { ...e, item: head } : e.slot === "body" ? { ...e, item: body } : e.slot === "ring_1" ? { ...e, item: ring } : e,
  );
  const cand = (item: GearItemInfo, slot: string, slotZh: string): GearCandidate =>
    ({ item, slot, slot_zh: slotZh, current: equipment.find((e) => e.slot === slot)?.item ?? null, notes_zh: [], weapon_swap_zh: null }) as unknown as GearCandidate;
  const potion = row("item_hp_potion_small", "小回復藥", "消耗品", 3, { field_usable: true, use_zh: "HP +30%", description_zh: "回復少量 HP。" });
  const bag: WorldBagItem[] = [
    row("item_demo_bow", "紫電長弓", "裝備", 1, {
      gear: true,
      can_equip: true,
      cross_class_zh: "別大類：可交易・可分解・可賣",
      cross_class_lost_zh: "換上後不能用：引火射",
    }),
    row("item_demo_boots", "踏雲靴", "裝備", 1, { gear: true, can_equip: true }),
    potion,
    row("item_coarse_material", "粗料", "材料", 6, { description_zh: "鐵匠打造用的材料。" }),
    row("item_mist_dye", "霧青染料", "染料", 1, { description_zh: "換裝備的顏色。" }),
    row("item_ember_shard", "餘燼碎片", "材料", 2),
  ];
  return {
    ...inv,
    equipment,
    bag,
    slots_used: bag.length,
    pouch: [row("item_hp_potion_small", "小回復藥", "消耗品", 2, { field_usable: true, use_zh: "HP +30%" })],
    pouch_count: 2,
    consumables: [potion],
    gear_cards: [cand(bow, "main_hand", "主手"), cand(boots, "feet", "腳")],
  };
}

/** 視窗大小（UI-E3c 必修 1：改視窗大小後要重算面板位置，不然會用舊尺寸的版面拍）。 */
function useWindowSize(): { width: number; height: number } {
  const [size, setSize] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));
  useEffect(() => {
    const onResize = () => setSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return size;
}

/**
 * 大世界面板的外框與位置：照正式 HUD 的 `popupBox`（舞台＝視窗扣掉上方 60px 的標題列，隊友 2 名）。
 * UI-E3c 必修 1：跟著視窗大小重算；右上角補上正式面板的「×」（開發頁沒有動作）。
 */
function Frame({ children, label }: { children: ReactNode; label: string }) {
  const { width: W, height } = useWindowSize();
  const H = height - STAGE_TOP;
  const layout = hudLayout(W, H, { mates: 2, narrow: isNarrow(W), collapsed: false });
  return (
    <PopupFrame placement={{ kind: "hud", box: popupBox(layout, 720) }} className="world-hud-panel" label={label} testId="world-hud-panel">
      <button type="button" className="world-hud-panel-close" aria-label="關閉面板（Esc）" data-testid="world-hud-panel-close">
        ×
      </button>
      {children}
    </PopupFrame>
  );
}

function Scene({ view, scene }: { view: WorldView; scene: string }) {
  useRegionTheme(view.field?.region ?? "cloud_ridge");
  const noop = () => undefined;
  if (scene === "hire") {
    return (
      <Frame label="雇用">
        <HudHirePanel view={view} busy={false} onAct={noop} />
      </Frame>
    );
  }
  const inv = view.inventory == null ? null : fullBag(view.inventory);
  const full = { ...view, inventory: inv } as WorldView;
  return (
    <Frame label="背包">
      <WorldBagScreen view={full} busy={false} onAct={noop} onClose={noop} initialPick="bag:item_demo_bow" />
    </Frame>
  );
}

function App() {
  const char = new URLSearchParams(location.search).get("char") ?? "";
  const [view, setView] = useState<WorldView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scene, setScene] = useState(location.hash.slice(1) || "bag-full");
  useEffect(() => {
    api.world(char).then(
      (v) => setView((v as { view?: WorldView }).view ?? (v as WorldView)),
      (e: unknown) => setError(String(e)),
    );
    const onHash = () => setScene(location.hash.slice(1) || "bag-full");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [char]);
  useEffect(() => {
    if (scene !== "bag-confirm" || view === null) return;
    const t = window.setTimeout(() => (document.querySelector("[data-testid=world-equip-item_demo_bow]") as HTMLButtonElement | null)?.click(), 300);
    return () => window.clearTimeout(t);
  }, [scene, view]);
  if (error !== null) return <div style={{ color: "#f88", padding: 20 }}>{error}</div>;
  if (view === null) return <div style={{ padding: 20 }}>讀取中……</div>;
  return (
    <div className="world-hud-stage" style={{ position: "relative", marginTop: STAGE_TOP, height: `calc(100vh - ${STAGE_TOP}px)`, background: "#20283a" }} data-scene={scene}>
      <Scene key={scene} view={view} scene={scene === "bag-confirm" ? "bag-full" : scene} />
    </div>
  );
}

createRoot(document.getElementById("root") as HTMLElement).render(<App />);
