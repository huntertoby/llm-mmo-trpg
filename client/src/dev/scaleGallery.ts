// 開發用：戰場人物比例對照（Phase 3U-2）。開 `client/scale-gallery.html`（pnpm dev 後 /scale-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。同一場面：高台、精靈、矮人、形態（熊、龍）、野獸與人形召喚物、頭頂狀態列。
// `#cell52`／`#cell88` 以格子像素 52／88 顯示（BattleRenderer 縮放 ＝ 格子像素 ／ 48）；`#perf` 量滿場 20 隻的繪製成本與快取數量。
import type { BattleView, Glossary, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import raceLooks from "../render/fixtures/raceLooks.json";

setGlossary(glossary as unknown as Glossary);

const MODE = decodeURIComponent(location.hash.slice(1)) || "cell52";
const COLS = 7;
const HERO = "unit_0001";
const looks = raceLooks as unknown as Record<string, Record<string, unknown>>;
const race = (id: string): UnitView["race"] => ({ id, name_zh: id, look: looks[id] ?? {} }) as unknown as UnitView["race"];
const statuses = (...ids: string[]): UnitView["statuses"] => ids.map((status_id) => ({ status_id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false })) as UnitView["statuses"];
const formOf = (look: string, element: string | null = null): UnitView["form"] => ({ form_id: look.replace("form_", ""), name_zh: look, category: "physical", look, element, natural_weapon_zh: "", effects_zh: [], upkeep_zh: "" }) as unknown as UnitView["form"];
const summonOf = (body: string, variant: string): UnitView["summon_look"] => ({ body, variant, element: null, size: "medium", trait: null }) as unknown as UnitView["summon_look"];

function view(rows: number, tiles: TileView[], units: UnitView[]): BattleView {
  return {
    team: "ally", map_id: "gallery", map_name_zh: "人物比例", width: COLS, height: rows, tiles, objects: [], units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 2, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}

function grid(rows: number, raised: number[] = []): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < rows; y++) for (let x = 0; x < COLS; x++) tiles.push({ ...tile(x, y), height: raised.includes(y) ? 2 : 0 });
  return tiles;
}

let n = 10;
function ally(x: number, y: number, over: Partial<UnitView> = {}): UnitView {
  return unit(`unit_${String(n++).padStart(4, "0")}`, "ally", x, y, { template_id: "hero_fighter", name_zh: "戰士", facing: "south", weapon_id: "one_handed_sword", ...over });
}

/** 同一場面：第 0 排平地（敵人在最上排，檢查頭頂超出與狀態列）、第 1 排高台、第 2 排平地。 */
function mainScene(): BattleView {
  const st = statuses("burning", "poison", "stun");
  const units: UnitView[] = [
    unit(HERO, "ally", 0, 1, { template_id: "hero_fighter", name_zh: "戰士", facing: "south", weapon_id: "one_handed_sword", statuses: st }),
    ally(1, 1, { name_zh: "精靈", race: race("elf"), statuses: st }),
    ally(2, 1, { name_zh: "矮人", race: race("dwarf"), statuses: st }),
    ally(3, 1, { name_zh: "熊形態", form: formOf("form_bear"), statuses: st }),
    ally(4, 1, { name_zh: "龍形態", form: formOf("form_dragon", "ice"), statuses: st }),
    ally(5, 1, { name_zh: "狼", owner_id: HERO, summon_expires_round: 5, summon_look: summonOf("beast", "wolf"), statuses: st }),
    ally(6, 1, { name_zh: "骷髏", owner_id: HERO, summon_expires_round: 5, summon_look: summonOf("humanoid", "skeleton"), statuses: st }),
    ally(0, 2, { name_zh: "精靈", race: race("elf") }),
    ally(1, 2, { name_zh: "矮人", race: race("dwarf") }),
    ally(2, 2, { name_zh: "狼", owner_id: HERO, summon_expires_round: 5, summon_look: summonOf("beast", "wolf") }),
    ally(3, 2, { name_zh: "熊形態", form: formOf("form_bear") }),
    ally(4, 2, { name_zh: "戰士" }),
    unit("unit_0090", "enemy", 1, 0, { template_id: "t", name_zh: "上排敵人", facing: "south" }),
    unit("unit_0091", "enemy", 2, 0, { template_id: "t", name_zh: "上排敵人", facing: "south" }),
    unit("unit_0092", "enemy", 5, 0, { template_id: "t", name_zh: "上排敵人", facing: "south" }),
  ];
  const shifted = units.map((u) => ({ ...u, y: u.y + 1 }));
  return view(4, grid(4, [2]), shifted);
}

/** 滿場 20 隻（3 排 × 7 欄的前 20 格），各種外觀混合。 */
function fullScene(): BattleView {
  const kinds: Partial<UnitView>[] = [
    {}, { race: race("elf") }, { race: race("dwarf") }, { form: formOf("form_bear") }, { form: formOf("form_dragon", "ice") },
    { owner_id: HERO, summon_expires_round: 5, summon_look: summonOf("beast", "wolf") }, { owner_id: HERO, summon_expires_round: 5, summon_look: summonOf("humanoid", "skeleton") },
  ];
  const units: UnitView[] = [];
  for (let i = 0; i < 20; i++) {
    const x = i % COLS;
    const y = Math.floor(i / COLS);
    const over = { ...kinds[i % kinds.length], statuses: statuses("burning", "poison") };
    units.push(i === 0 ? unit(HERO, "ally", x, y, { template_id: "hero_fighter", name_zh: "戰士", facing: "south", ...over }) : ally(x, y, { facing: i % 4 < 2 ? "south" : "east", ...over }));
  }
  return view(3, grid(3), units);
}

async function show(title: string, v: BattleView, cell: number): Promise<BattleRenderer> {
  const box = document.createElement("div");
  box.className = "scene";
  const h = document.createElement("h2");
  h.textContent = title;
  box.appendChild(h);
  document.body.appendChild(box);
  const renderer = new BattleRenderer();
  await renderer.init(box);
  renderer.setScale(cell / 48);
  renderer.draw(buildDrawModel(v, HERO));
  return renderer;
}

async function perf(): Promise<void> {
  const cell = 88;
  const r = await show("滿場 20 隻（88px 格）", fullScene(), cell);
  const model = buildDrawModel(fullScene(), HERO);
  const N = 200;
  const t0 = performance.now();
  for (let i = 0; i < N; i++) r.draw(model);
  const per = (performance.now() - t0) / N;
  const size = (r as unknown as { art: { size: number } }).art.size;
  const out = document.createElement("div");
  out.id = "perf";
  out.textContent = JSON.stringify({ cell, dpr: window.devicePixelRatio, drawEachMs: Number(per.toFixed(3)), cacheSize: size });
  document.body.appendChild(out);
}

if (MODE === "perf") await perf();
else await show(`人物比例・格子 ${MODE === "cell88" ? 88 : 52}px`, mainScene(), MODE === "cell88" ? 88 : 52);
