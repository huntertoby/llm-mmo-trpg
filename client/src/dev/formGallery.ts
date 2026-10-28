// 開發用：形態外觀一覽（Phase 3J-5）。開 `client/form-gallery.html`（pnpm dev 後 /form-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。用真正的 BattleRenderer 畫：10 種 × 4 朝向（第一格是變身前的角色，同比例對照）、
// 元素化身與龍的三種元素、不認得的形態 id、倒地、頭頂狀態列、變身前後的小戰場。
// `#名稱` 只顯示該段（south／north／east／west／element／unknown／status／battle）。
import type { BattleView, Glossary, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { FORM_LOOKS } from "../render/inkForm";

type FormView = NonNullable<UnitView["form"]>;

setGlossary(glossary as unknown as Glossary);

const ONLY = decodeURIComponent(location.hash.slice(1));
const COLS = 6;
const HERO = "unit_0001";
const LOOKS = Object.keys(FORM_LOOKS);
const NAMES: Readonly<Record<string, string>> = { form_bear: "熊", form_cat: "貓", form_roc: "鳥", form_elemental: "元素化身", form_werewolf: "狼人", form_demon: "惡魔", form_giant: "巨人", form_shadow: "暗影形態", form_treant: "樹人", form_dragon: "龍" };

function formView(look: string, element: string | null = null): FormView {
  return { form_id: look.replace("form_", ""), name_zh: NAMES[look] ?? look, category: "physical", look, element, natural_weapon_zh: "", effects_zh: [], upkeep_zh: "" };
}

function baseView(width: number, height: number, tiles: TileView[], units: UnitView[]): BattleView {
  return {
    team: "ally",
    map_id: "gallery",
    map_name_zh: "形態一覽",
    width,
    height,
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

function body(i: number, x: number, y: number, look: string | null, facing: UnitView["facing"], element: string | null = null, over: Partial<UnitView> = {}): UnitView {
  return unit(`unit_${String(10 + i).padStart(4, "0")}`, "ally", x, y, {
    template_id: "hero_fighter",
    name_zh: look === null ? "戰士" : (NAMES[look] ?? look),
    facing,
    weapon_id: "one_handed_sword",
    form: look === null ? null : formView(look, element),
    ...over,
  });
}

async function scene(title: string, key: string, view: BattleView, names: string[] = [], scale = 2.8): Promise<void> {
  if (ONLY !== "" && ONLY !== key) return;
  const box = document.createElement("div");
  box.className = "scene";
  const h = document.createElement("h2");
  h.textContent = title;
  box.appendChild(h);
  document.body.appendChild(box);
  const renderer = new BattleRenderer();
  await renderer.init(box);
  renderer.setScale(scale);
  renderer.draw(buildDrawModel(view, HERO));
  if (names.length > 0) {
    const row = document.createElement("div");
    row.className = "names";
    for (const n of names) row.appendChild(Object.assign(document.createElement("span"), { textContent: n }));
    box.appendChild(row);
  }
}

function flat(rows: number): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < rows; y++) for (let x = 0; x < COLS; x++) tiles.push(tile(x, y));
  return tiles;
}

async function facingScene(facing: UnitView["facing"]): Promise<void> {
  const rows = Math.ceil((LOOKS.length + 1) / COLS);
  const units: UnitView[] = [unit(HERO, "ally", 0, 0, { template_id: "hero_fighter", name_zh: "戰士", facing })];
  LOOKS.forEach((look, i) => units.push(body(i, (i + 1) % COLS, Math.floor((i + 1) / COLS), look, facing, look === "form_elemental" || look === "form_dragon" ? "fire" : null)));
  await scene(`10 種形態・朝向 ${facing}（左上是變身前的角色）`, facing, baseView(COLS, rows, flat(rows), units), ["戰士（對照）", ...LOOKS.map((l) => NAMES[l] ?? l)]);
}

async function elementScene(): Promise<void> {
  const els = ["fire", "ice", "lightning", null];
  const units: UnitView[] = [unit(HERO, "ally", 5, 1, { template_id: "hero_fighter", name_zh: "戰士", facing: "east" })];
  els.forEach((el, i) => units.push(body(i, i, 0, "form_elemental", "east", el)));
  els.forEach((el, i) => units.push(body(i + 4, i, 1, "form_dragon", "east", el)));
  await scene("元素化身（上）與龍（下）：火／冰／雷／無元素（無元素＝紫光環）", "element", baseView(COLS, 2, flat(2), units), ["火", "冰", "雷", "無元素"]);
}

async function unknownScene(): Promise<void> {
  const units: UnitView[] = [
    body(0, 0, 0, "form_unknown", "south"),
    body(1, 1, 0, "", "east"),
    body(2, 2, 0, "form_bear", "west", "plasma"),
    body(3, 3, 0, "form_bear", "north"),
    body(4, 4, 0, "form_bear", "south", null, { downed: true, hp: 0 }),
    unit(HERO, "ally", 5, 0, { template_id: "hero_fighter", name_zh: "戰士", facing: "south" }),
  ];
  await scene("不認得的形態 id（退回原角色＋光環）／空 id／不認得的元素／熊朝北／倒地的單位帶形態", "unknown", baseView(COLS, 1, flat(1), units), ["未知 id", "空 id", "熊（plasma 元素）", "熊朝北", "倒地帶熊", "戰士"]);
}

async function statusScene(): Promise<void> {
  const ids = ["burning", "poison", "stun"];
  const units: UnitView[] = [unit(HERO, "ally", 0, 1, { template_id: "hero_fighter", name_zh: "戰士", facing: "south" })];
  ["form_bear", "form_treant", "form_dragon", "form_werewolf", "form_cat"].forEach((look, i) =>
    units.push(body(i, i + 1, 1, look, "south", look === "form_dragon" ? "ice" : null, { statuses: ids.map((status_id) => ({ status_id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false })) })),
  );
  units.push(unit("unit_0090", "enemy", 0, 0, { template_id: "t", name_zh: "上一格的敵人", facing: "south" }));
  await scene("頭頂狀態列跟體型上移（下排單位帶 3 個狀態；上排是上一格單位的血條）", "status", baseView(COLS, 2, flat(2), units), ["戰士", "熊", "樹人", "龍", "狼人", "貓"]);
}

async function battleScene(): Promise<void> {
  const mk = (form: boolean): UnitView[] => [
    unit(HERO, "ally", 1, 2, { template_id: "hero_fighter", name_zh: "戰士", facing: "east", form: form ? formView("form_bear") : null }),
    unit("unit_0002", "ally", 0, 3, { template_id: "hero_archer", name_zh: "弓手", facing: "east" }),
    unit("unit_0003", "enemy", 3, 2, { template_id: "t", name_zh: "敵人", facing: "west" }),
    unit("unit_0004", "enemy", 4, 3, { template_id: "t", name_zh: "敵人", facing: "west" }),
  ];
  await scene("實戰：變身前", "battle", baseView(COLS, 5, flat(5), mk(false)), [], 2);
  await scene("實戰：變身後（熊）", "battle", baseView(COLS, 5, flat(5), mk(true)), [], 2);
}

for (const f of ["south", "north", "east", "west"] as const) await facingScene(f);
await elementScene();
await unknownScene();
await statusScene();
await battleScene();
