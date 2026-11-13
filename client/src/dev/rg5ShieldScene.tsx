// 開發用：RG-5 玩家大盾的「實機一時到不了」畫面（`dev/rg5-shield-scene.html`；不屬於正式 build）。
// 用正式元件與正式資料流畫：戰場是 `BattleRenderer`＋`buildDrawModel`（單位的 `equipment` 走 dollGear → resolveGear → 紙娃娃，和實機同一條路）；
// 背包與裝備欄是 `BagContents`（42 格）與 `WornSlot`（48 格），圖示走 `GearIcon` → gearIconCanvas → qWeaponDef。資料是假的。
// 參數：?mode=scene&w=1600|800（格子 63／25 px，等於 1600、800 寬視窗的地圖縮放 1.31／0.53）｜?mode=bag
//       ｜?mode=c&w=1600|800：盾陣（shield_formation）的預覽沿用盾兵小盾＋點線（RG-4 驗收待決 9）
//       ｜?mode=d&w=1600|800：單位資訊卡層數（KW-3 待決 3：四種計量 StackPips，其他照舊）
//       ｜?mode=k3&w=1600|800：RG-4 驗收 K3（持盾弟子身邊的粉紅小點）的對照——南鄰格比較高的單位畫 6F-22 舊剪影（敵方 #ffb3a8 虛線人形），平地的不畫。
import { createRoot } from "react-dom/client";
import type { BattleView, Glossary, HeroGearSlot, PreviewOut, TileView, UnitView, WorldInventory, WorldBagItem } from "../api/types";
import { guardDraw } from "../battle/rgMarks";
import { unitNames } from "../battle/units";
import { UnitInfo } from "../ui/UnitInfo";
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
  p.textContent = `gearAppearance.json（正式資料）resolveGear：sect_great ${ready("sect_great") ? "認得" : "不認得（會退回鳶盾）"}、molten_shell ${ready("molten_shell") ? "認得" : "不認得（會退回鳶盾）"}`;
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
/** K3 對照：第 1 列 (1,0) 持盾弟子南鄰 (1,1) 高 2 → 畫虛線剪影；(3,0) 持盾弟子南鄰平地 → 不畫；(5,0) 拿劍的一般敵人南鄰高 2 → 一樣畫（不是碑盾特有）。 */
function k3Scene(): BattleView {
  const tiles = grid(3).map((t) => (t.y === 1 && (t.x === 1 || t.x === 5) ? { ...t, height: 2 } : t));
  const units: UnitView[] = [
    unit("unit_0090", "enemy", 1, 0, { template_id: "sect_shield_disciple", name_zh: "持盾弟子（南鄰高）", facing: "west", doll_look: UNIT_DOLLS["sect_shield_disciple"] } as Partial<UnitView>),
    unit("unit_0091", "enemy", 3, 0, { template_id: "sect_shield_disciple", name_zh: "持盾弟子（平地）", facing: "west", doll_look: UNIT_DOLLS["sect_shield_disciple"] } as Partial<UnitView>),
    unit("unit_0092", "enemy", 5, 0, { template_id: "t", name_zh: "劍兵（南鄰高）", facing: "west" } as Partial<UnitView>),
    unit(HERO, "ally", 2, 2, { template_id: "hero_fighter", name_zh: "主角", facing: "north", weapon_id: "one_handed_sword" } as Partial<UnitView>),
  ];
  return { ...scene(), units, tiles, height: 3 } as BattleView;
}
async function showK3(): Promise<void> {
  const cell = W === 800 ? 25 : 63;
  const box = document.createElement("div");
  const h = document.createElement("h2");
  h.textContent = `K3 對照（格子 ${cell}px、真 1 倍）：左 持盾弟子南鄰高 2｜中 持盾弟子平地｜右 一般敵人南鄰高 2`;
  box.appendChild(h);
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(cell / 48);
  r.draw(buildDrawModel(k3Scene(), HERO));
  document.body.dataset["ready"] = "1";
}
/** C：主角（弓）瞄準敵方符籙師；旁邊持塔盾（帶盾陣）的熔殼兵擋著 → 預覽 cover.kind＝shield_formation。 */
function cScene(): BattleView {
  const units: UnitView[] = [
    unit("unit_0090", "enemy", 2, 1, { template_id: "t", name_zh: "符籙師", facing: "south" } as Partial<UnitView>),
    unit("unit_0091", "enemy", 3, 1, { template_id: "t", name_zh: "盾陣兵", facing: "south", equipment: [{ slot: "off_hand", appearance: shield("molten_shell", "iron") }] } as Partial<UnitView>),
    unit(HERO, "ally", 2, 4, { template_id: "hero_fighter", name_zh: "主角", facing: "north", weapon_id: "short_bow", weapon_class: "ranged" } as Partial<UnitView>),
  ];
  return { ...scene(), units, tiles: grid(5), height: 5 } as BattleView;
}
async function showC(): Promise<void> {
  const cell = W === 800 ? 25 : 63;
  const v = cScene();
  const preview = { action: { type: "attack", unit_id: HERO, target_id: "unit_0090" }, cover: { penalty: 2, kind: "shield_formation", name_zh: "盾陣兵的盾陣", pos: [3, 1], unit_id: "unit_0091" } } as unknown as PreviewOut;
  const box = document.createElement("div");
  const h = document.createElement("h2");
  h.textContent = `盾陣預覽（格子 ${cell}px、真 1 倍）：主角瞄準符籙師，旁邊持塔盾（盾陣）的人擋著 → 小盾＋點線（同盾兵）；預覽字（伺服器給的 name_zh 為假資料）：`;
  box.appendChild(h);
  const t = document.createElement("div");
  t.id = "preview-text";
  // 預覽框那一行的格式照 previewText.previewLines（「目標有{cover.name_zh}掩護（命中 −n）」）；整段 previewLines 要完整的 PreviewOut，這裡只示意那一行
  const c = preview.cover;
  t.textContent = c !== null ? `預覽框：目標有${c.name_zh}掩護（命中 −${c.penalty}）` : "";
  box.appendChild(t);
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(cell / 48);
  r.draw(buildDrawModel(v, HERO));
  r.setHighlights({ moves: [], attacks: [{ x: 2, y: 1 }], directions: [], preview: [], telegraph: [], focus: null, hover: { x: 2, y: 1 }, overlays: [], picked: [], vaults: [], guard: guardDraw(preview, v) });
  setTimeout(() => (document.body.dataset["ready"] = "1"), 800);
}
/** D：單位資訊卡（正式元件 UnitInfo）：連擊 3＋怒氣滿＋專注 1＋氣 2＋其他層數。 */
function CardD() {
  const u = unit("unit_0090", "enemy", 1, 1, { name_zh: "刀客", stacks: { combo_point: 3, fury: 4, focus: 1, ki: 2, static_charge: 2 } } as Partial<UnitView>);
  const u2 = unit("unit_0091", "enemy", 2, 1, { name_zh: "拳師", stacks: { ki: 1, static_charge: 1 } } as Partial<UnitView>);
  const v = { ...scene(), units: [u, u2] } as BattleView;
  const names = unitNames(v);
  return (
    <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
      {[u, u2].map((x) => (
        <div key={x.id} className="unit-float bridge-left pinned" style={{ position: "relative", left: 0, top: 0, pointerEvents: "auto" }}>
          <UnitInfo unit={x} names={names} heroId={HERO} skills={{}} view={v} />
        </div>
      ))}
    </div>
  );
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
} else if (MODE === "d") {
  const h = document.createElement("h2");
  h.textContent = `單位資訊卡層數（視窗 ${W}、真 1 倍）：連擊、怒氣、專注、氣是 HUD 同尺寸計量，其他層數（靜電）照舊`;
  document.body.appendChild(h);
  const root = document.createElement("div");
  document.body.appendChild(root);
  createRoot(root).render(<CardD />);
  setTimeout(() => (document.body.dataset["ready"] = "1"), 500);
} else if (MODE === "c") await showC();
else if (MODE === "k3") await showK3();
else await showScene();
