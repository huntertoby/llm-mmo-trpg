// 開發用：PR-2c 靶場木樁與場景畫法（開 `client/dev/practice-gallery.html`，pnpm dev 後 /dev/practice-gallery.html）。不屬於正式 build。
// 用真正的 `buildDrawModel` 與 `BattleRenderer` 畫 training_range（地圖照 content/maps/training_range.yaml、木樁照
// content/world/newcomer.yaml `range.dummies`，抄在下面；改地圖時一起改）：
// - 測試模式（`practice: true`）：滑軌、方角水池、三種木樁；
// - 不帶測試模式：同一張圖（技能工坊 3F、實戰的地形畫法；木樁照樣換新外觀，PR-2 第 8 點）。
// 參數：`?mode=both|practice|real`、`&scale=1.5`、`&hit=rail|pool|plain`（那個木樁受擊閃白；閃白拉長成 5 秒好截圖）、
// `&bare=1`（不寫標題、不留邊，截圖用）。待機關掉（畫面固定）。畫好後 `document.body.dataset.ready = "1"`。
import type { BattleView, Glossary, TileView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { BATTLE_DRAW, buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { VFX_TIMING, type StepVfx } from "../battle/vfx";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const params = new URLSearchParams(location.search);
const MODE = params.get("mode") ?? "both";
const SCALE = Number(params.get("scale") ?? "1.5") || 1.5;
const HIT = params.get("hit");
if (params.get("bare") === "1") document.body.classList.add("bare");

// content/maps/training_range.yaml（12×10）
const TERRAIN = ["...#########", "...........#", "...###.###.#", "............", "............", "............", "............", "........LL..", "............", "............"];
const HEIGHTS = ["000000000000", "000000000000", "000000000000", "000000000000", "000000000000", "000000000000", "000000000000", "000000000000", "000000000012", "000000000012"];
const LEGEND: Record<string, string> = { ".": "stone", "#": "wall", L: "lava" };
const WATER = ["6,8", "7,8", "6,9"];
const OBJECTS: Array<[number, number, string]> = [[5, 4, "stone_pillar"], [3, 5, "dead_tree"], [2, 6, "crate"], [4, 7, "oil_barrel"], [3, 8, "crate"], [8, 9, "grass"], [9, 9, "grass"], [9, 8, "grass"]];
// content/world/newcomer.yaml range：主角 (2, 5)，木樁 會動 (9, 3)、水上 (6, 8)、普通 (6, 4)
const DUMMIES: Array<{ id: string; kind: string; template: string; at: [number, number] }> = [
  { id: "unit_0002", kind: "rail", template: "training_dummy_moving", at: [9, 3] },
  { id: "unit_0003", kind: "pool", template: "training_dummy", at: [6, 8] },
  { id: "unit_0004", kind: "plain", template: "training_dummy", at: [6, 4] },
];

function rangeView(practice: boolean): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < 10; y++) {
    for (let x = 0; x < 12; x++) {
      const terrain = LEGEND[TERRAIN[y]![x]!] ?? "stone";
      tiles.push(tile(x, y, { terrain, height: Number(HEIGHTS[y]![x]), surface: WATER.includes(`${x},${y}`) ? "water" : "none" } as Partial<TileView>));
    }
  }
  const dummies = DUMMIES.map((d) => unit(d.id, "enemy", d.at[0], d.at[1], { template_id: d.template, name_zh: "木樁", hp: 300, max_hp: 300, facing: "west", weapon_id: "dagger" }));
  const hero = unit("unit_0001", "ally", 2, 5, { template_id: "hero_fighter", name_zh: "主角", weapon_id: "bow", weapon_class: "ranged", facing: "east" });
  return {
    team: "ally",
    map_id: "training_range",
    map_name_zh: "靶場",
    width: 12,
    height: 10,
    tiles,
    objects: OBJECTS.map(([x, y, kind], i) => ({ id: `obj_${i}`, kind, pos: { x, y }, hp: 10, max_hp: 10, burning: null })),
    units: [hero, ...dummies],
    traps: [],
    turn_order: ["unit_0001"],
    active_unit: "unit_0001",
    round: 3,
    max_rounds: practice ? null : 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [{ x: 1, y: 1 }],
    zones: [],
    runes: [],
    summon_command_ap_cost: 1,
    summon_infuse_ap_cost: 1,
    practice,
  } as BattleView;
}

async function scene(title: string, practice: boolean): Promise<void> {
  const box = document.createElement("div");
  box.className = "scene";
  box.appendChild(Object.assign(document.createElement("h2"), { textContent: title }));
  document.body.appendChild(box);
  const host = document.createElement("div");
  box.appendChild(host);
  const r = new BattleRenderer();
  await r.init(host);
  r.setScale(SCALE);
  r.setIdle(false);
  r.draw(buildDrawModel(rangeView(practice), "unit_0001", null, undefined, BATTLE_DRAW));
  const target = DUMMIES.find((d) => d.kind === HIT);
  if (target !== undefined) {
    // 受擊反應（6N-4）只放一個「hit」：命中點拉長 50 倍，木樁的白閃 0.1 秒 → 5 秒（截圖用）
    const vfx: StepVfx = { casts: [], hits: [], blasts: [], shake: 0, leadMs: 0, reactions: [{ unitId: target.id, kind: "hit", atMs: 0 } as never] };
    r.playVfx(vfx, VFX_TIMING.impact * 50, false);
  }
}

if (MODE !== "real") await scene("測試模式（view.practice）：滑軌、方角水池、三種木樁", true);
if (MODE !== "practice") await scene("不帶測試模式（技能工坊 3F／實戰的地形畫法；木樁同樣換新外觀）", false);
document.body.dataset.ready = "1";
