// 開發用：戰場效果的 9×6 場景（Phase 3-36b），對照 docs/art/battlefield-fx.png 的「提案」。
// 開 `client/fx-gallery.html`（pnpm dev 後 /fx-gallery.html）；不屬於正式 build。用真正的 BattleRenderer 畫：
// 煙霧／黑暗霧、冰牆（3／3＋HP50%／最後 1 回合）、荊棘（2／1）、倒塌物（完整／30%）、薄冰（50%／20%）、
// 四種陷阱（含未揭露的敵方）、有害移動火區域、有益跟隨聖光區域、各種狀態單位。
import type { BattleView, Glossary, StatusView, TileView, UnitView, ZoneView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import type { FxSkill } from "../battle/fxSkills";
import { setGlossary } from "../battle/glossary";
import { object, tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const HERO = "unit_0001";
const st = (...ids: string[]): StatusView[] => ids.map((status_id) => ({ status_id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false }));

const SURF: Record<string, string> = { "0,0": "smoke", "1,0": "smoke", "0,1": "smoke", "1,1": "smoke", "2,0": "darkness", "2,1": "darkness" };

function board(): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < 6; y++) {
    for (let x = 0; x < 9; x++) {
      const terrain = x === 8 && y >= 4 ? "ice_hole" : x <= 3 && y >= 3 ? "grass" : "stone";
      tiles.push(tile(x, y, { terrain, surface: (SURF[`${x},${y}`] ?? "none") as TileView["surface"] }));
    }
  }
  const objects = [
    object("o1", "ice_wall", 4, 0, { hp: 10, max_hp: 10, expires_in: 3 }),
    object("o2", "ice_wall", 4, 1, { hp: 5, max_hp: 10, expires_in: 3 }),
    object("o3", "ice_wall", 4, 2, { hp: 10, max_hp: 10, expires_in: 1 }),
    object("o4", "thorn_wall", 6, 0, { hp: 10, max_hp: 10, expires_in: 2 }),
    object("o5", "thorn_wall", 7, 0, { hp: 10, max_hp: 10, expires_in: 1 }),
    object("o6", "rubble", 6, 5, { hp: 10, max_hp: 10 }),
    object("o7", "rubble", 7, 5, { hp: 3, max_hp: 10 }),
    object("o8", "thin_ice", 8, 4, { hp: 5, max_hp: 10 }),
    object("o9", "thin_ice", 8, 5, { hp: 2, max_hp: 10 }),
  ];
  const u = (id: string, team: "ally" | "enemy", x: number, y: number, statuses: StatusView[], over: Partial<UnitView> = {}): UnitView =>
    unit(id, team, x, y, { statuses, name_zh: id, ...over });
  const units: UnitView[] = [
    u("unit_0002", "enemy", 1, 1, st("concealed")),
    u("unit_0003", "enemy", 3, 1, st("stun", "poison")),
    u("unit_0004", "enemy", 6, 3, st("burning", "slow", "vulnerable", "marked")),
    u(HERO, "ally", 1, 4, st("shielded", "hasted", "regenerating"), { template_id: "hero_fighter" }),
    u("unit_0006", "ally", 4, 3, st("root", "bleed")),
    u("unit_0007", "ally", 7, 1, st("frozen")),
  ];
  const traps = [
    { owner_id: HERO, team: "ally" as const, pos: { x: 3, y: 5 }, skill_id: "t_fire", remaining: 3 },
    { owner_id: HERO, team: "ally" as const, pos: { x: 4, y: 5 }, skill_id: "t_bolt", remaining: 2 },
    { owner_id: "unit_0004", team: "enemy" as const, pos: { x: 5, y: 5 }, skill_id: "t_poison", remaining: 2 },
  ];
  const zone = (id: number, over: Partial<ZoneView>): ZoneView => ({
    id,
    owner_id: HERO,
    team: "ally",
    skill_id: "z",
    name_zh: "區域",
    anchor: "tile",
    affects: "enemies",
    when: "both",
    cells: [],
    direction: null,
    speed: 0,
    expires_round: 3,
    harmful: true,
    next_cells: null,
    ...over,
  });
  const zones: ZoneView[] = [
    zone(1, {
      owner_id: "unit_0004",
      team: "enemy",
      skill_id: "z_fire",
      anchor: "moving",
      direction: "east",
      speed: 1,
      expires_round: 3,
      cells: [5, 6, 7].flatMap((x) => [2, 3].map((y) => ({ x, y }))),
    }),
    zone(2, {
      skill_id: "z_holy",
      anchor: "caster",
      affects: "allies",
      harmful: false,
      expires_round: 4,
      cells: [0, 1, 2].flatMap((x) => [3, 4, 5].map((y) => ({ x, y }))),
    }),
    // 我方的火牆只打敵人：不影響我方（3-37b 第三種樣式）
    zone(3, { skill_id: "z_fire", expires_round: 3, cells: [4, 5].flatMap((x) => [4, 5].map((y) => ({ x, y }))) }),
  ];
  return {
    team: "ally",
    map_id: "fx_gallery",
    map_name_zh: "戰場效果一覽",
    width: 9,
    height: 6,
    tiles,
    objects,
    units,
    traps,
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
    zones,
    runes: [],
  } as unknown as BattleView;
}

const SKILLS: Record<string, FxSkill> = {
  t_fire: { element: "fire", zoneElement: null, surface: null, trapTrigger: "enter" },
  t_bolt: { element: "lightning", zoneElement: null, surface: null, trapTrigger: "delay" },
  t_poison: { element: "poison", zoneElement: null, surface: null, trapTrigger: "enter" },
  z_fire: { element: null, zoneElement: "fire", surface: "fire", trapTrigger: null },
  z_holy: { element: null, zoneElement: "holy", surface: null, trapTrigger: null },
};

const box = document.createElement("div");
box.className = "scene";
box.appendChild(Object.assign(document.createElement("h2"), { textContent: "戰場效果 9×6（對照 docs/art/battlefield-fx.png 提案）" }));
document.body.appendChild(box);
const renderer = new BattleRenderer();
await renderer.init(box);
renderer.setScale(2);
renderer.draw(buildDrawModel(board(), HERO, undefined, (id) => SKILLS[id]));
