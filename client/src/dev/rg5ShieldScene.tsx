// 開發用：RG-5 玩家大盾的「實機一時到不了」畫面（`dev/rg5-shield-scene.html`；不屬於正式 build）。
// 用正式元件與正式資料流畫：戰場是 `BattleRenderer`＋`buildDrawModel`（單位的 `equipment` 走 dollGear → resolveGear → 紙娃娃，和實機同一條路）；
// 背包與裝備欄是 `BagContents`（42 格）與 `WornSlot`（48 格），圖示走 `GearIcon` → gearIconCanvas → qWeaponDef。資料是假的。
// 注意：形制要先在 gearAppearance.json 的 kite_shield.forms 裡（resolveGear 才不會退回鳶盾）；畫面上方會寫出目前是不是。
// 參數：?mode=scene&w=1600|800（格子 63／25 px，等於 1600、800 寬視窗的地圖縮放 1.31／0.53）｜?mode=bag
import { createRoot } from "react-dom/client";
import type { BattleView, Glossary, HeroGearSlot, TileView, UnitView, WorldInventory, WorldBagItem } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { resolveGear, type GearLook } from "../render/gearIcon";
import { UNIT_DOLLS } from "../render/testDolls";
import { BagContents, WornSlot } from "../world/BagScreen";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
const q = new URLSearchParams(location.search);
const MODE = q.get("mode") ?? "scene";
const W = q.get("w") === "800" ? 800 : 1600;
const HERO = "unit_0001";
const COLS = 6;
const shield = (form: string, material: string, keywords: string[] = []): GearLook => ({ kind: "kite_shield", form, material, keywords, rarity: "rare" });
const ready = (form: string): boolean => resolveGear(shield(form, "iron"), "off_hand").form === form;

function header(): HTMLElement {
  const p = document.createElement("div");
  p.id = "status";
  p.textContent = `gearAppearance.json：sect_great ${ready("sect_great") ? "有" : "沒有（會退回鳶盾）"}、molten_shell ${ready("molten_shell") ? "有" : "沒有（會退回鳶盾）"}`;
  document.body.appendChild(p);
  return p;
}

// ---------------- 戰場 ----------------
function grid(rows: number): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < rows; y++) for (let x = 0; x < COLS; x++) tiles.push({ ...tile(x, y), height: 0 });
  return tiles;
}
let n = 10;
function hero(x: number, y: number, facing: string, off: GearLook, name: string): UnitView {
  const id = x === 0 && y === 1 ? HERO : `unit_${String(n++).padStart(4, "0")}`;
  return unit(id, "ally", x, y, { template_id: "hero_fighter", name_zh: name, facing, weapon_id: "one_handed_sword", equipment: [{ slot: "off_hand", appearance: off }] } as Partial<UnitView>);
}
function scene(): BattleView {
  const facings = ["south", "east", "north", "west"];
  const units: UnitView[] = [
    unit("unit_0090", "enemy", 1, 0, { template_id: "sect_shield_disciple", name_zh: "持盾弟子", facing: "south", doll_look: UNIT_DOLLS["sect_shield_disciple"] } as Partial<UnitView>),
    unit("unit_0091", "enemy", 3, 0, { template_id: "sect_shield_disciple", name_zh: "持盾弟子", facing: "west", doll_look: UNIT_DOLLS["sect_shield_disciple"] } as Partial<UnitView>),
    ...facings.map((f, i) => hero(i, 1, f, shield("sect_great", "iron"), "碑盾鐵")),
    hero(4, 1, "east", shield("sect_great", "gold"), "碑盾金"),
    hero(5, 1, "south", shield("sect_great", "steel", ["frozen"]), "碑盾鋼冰"),
    ...facings.map((f, i) => hero(i, 2, f, shield("molten_shell", "iron"), "熔殼鐵")),
    hero(4, 2, "east", shield("molten_shell", "silver"), "熔殼銀"),
    hero(5, 2, "south", shield("molten_shell", "copper", ["ignite"]), "熔殼銅火"),
  ];
  return {
    team: "ally", map_id: "rg5", map_name_zh: "RG-5 大盾", width: COLS, height: 3, tiles: grid(3), objects: [], units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 2, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}
async function showScene(): Promise<void> {
  header();
  const cell = W === 800 ? 25 : 63;
  const box = document.createElement("div");
  box.className = "scene";
  const h = document.createElement("h2");
  h.textContent = `戰場（${W} 寬視窗的地圖縮放：格子 ${cell}px、真 1 倍）：上排持盾弟子；第 2 排玩家碑盾（鐵 南東北西、金、鋼＋冰凍）；第 3 排玩家熔殼（鐵 南東北西、銀、銅＋點燃）`;
  box.appendChild(h);
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(cell / 48);
  r.draw(buildDrawModel(scene(), HERO));
  document.body.dataset["ready"] = "1";
}

// ---------------- 背包、裝備欄 ----------------
const gearRow = (id: string, name: string): WorldBagItem => ({ item: id, name_zh: name, kind_zh: "裝備", count: 1, description_zh: "副手・稀有", sell_price: 12, sellable: true, field_usable: false, gear: true, can_equip: true, tradable: true }) as WorldBagItem;
const CARDS: ReadonlyArray<readonly [string, string, GearLook]> = [
  ["g_sect_iron", "雲紋碑盾（鐵）", shield("sect_great", "iron")],
  ["g_shell_iron", "熔殼塔盾（鐵）", shield("molten_shell", "iron")],
  ["g_tower", "塔盾", shield("tower", "iron")],
  ["g_kite", "鳶盾", shield("kite", "iron")],
  ["g_round", "木圓盾", { kind: "round_shield", form: "wood", material: "wood", keywords: [], rarity: "rare" }],
  ["g_sect_gold", "雲紋碑盾（金）", shield("sect_great", "gold")],
  ["g_shell_gold", "熔殼塔盾（金）", shield("molten_shell", "gold")],
  ["g_sect_steel", "雲紋碑盾（鋼）", shield("sect_great", "steel")],
  ["g_shell_silver", "熔殼塔盾（銀）", shield("molten_shell", "silver")],
  ["g_sword", "長劍", { kind: "sword", form: "straight", material: "steel", keywords: [], rarity: "rare" }],
  ["g_sect_copper", "雲紋碑盾（銅）", shield("sect_great", "copper")],
  ["g_shell_copper", "熔殼塔盾（銅＋點燃）", shield("molten_shell", "copper", ["ignite"])],
];
const INVENTORY = {
  bag: CARDS.map(([id, name]) => gearRow(id, name)), slots_used: CARDS.length, slots_max: 30, pouch: [], pouch_count: 0, pouch_max: 3, can_pouch: true, pouch_problem_zh: null,
  consumables: [], equipped_zh: [], resonance_zh: [], equipment: [],
  gear_cards: CARDS.map(([id, name, look]) => ({ item: { id, name_zh: name, slot_type: look.kind === "sword" ? "weapon" : "offhand", affixes: [], tags: [], appearance: look }, slot: look.kind === "sword" ? "main_hand" : "off_hand", slot_zh: "副手", current: null, notes_zh: [] })),
} as unknown as WorldInventory;
const worn = (look: GearLook, name: string): HeroGearSlot => ({ slot: "off_hand", slot_zh: "副手", item: { id: name, name_zh: name, slot_type: "offhand", rarity: "rare", level: 3, affixes: [], tags: [], appearance: look }, opening_note_zh: null }) as unknown as HeroGearSlot;
const NOOP = (): void => undefined;
function Bag() {
  return (
    <div>
      <h2>背包（BagContents，裝備 42 格）：碑盾、熔殼混在塔盾、鳶盾、木圓盾、長劍之間</h2>
      <div className="panel" style={{ width: 700 }}>
        <div className="world-bag-screen" data-crop="bag">
          <BagContents inventory={INVENTORY} busy={false} onAct={NOOP} canUse />
        </div>
      </div>
      <h2>裝備欄（WornSlot，副手 48 格）× 7 種材質</h2>
      <ul className="world-worn" style={{ display: "flex", gap: 8, listStyle: "none", padding: 0 }} data-crop="worn">
        {(["sect_great", "molten_shell"] as const).flatMap((f) =>
          ([["iron", []], ["steel", []], ["copper", []], ["silver", []], ["gold", []], ["iron", ["ignite"]], ["steel", ["frozen"]]] as const).map(([m, kw]) => (
            <WornSlot key={`${f}-${m}-${kw.join()}`} entry={worn(shield(f, m, [...kw]), `${f === "sect_great" ? "雲紋碑盾" : "熔殼塔盾"} ${m}${kw.length ? "+" + kw.join() : ""}`)} />
          )),
        )}
      </ul>
    </div>
  );
}

if (MODE === "bag") {
  header();
  const root = document.createElement("div");
  document.body.appendChild(root);
  createRoot(root).render(<Bag />);
  setTimeout(() => (document.body.dataset["ready"] = "1"), 500);
} else await showScene();
