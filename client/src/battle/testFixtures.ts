// 測試用的小型視圖（只給 vitest 用）。
import type { BattleView, ObjectView, TileView, UnitView } from "../api/types";

export function tile(x: number, y: number, over: Partial<TileView> = {}): TileView {
  return {
    x,
    y,
    height: 0,
    terrain: "stone",
    surface: "none",
    surface_remaining: null,
    surface_team: null,
    surface_creator: null,
    object_id: null,
    ...over,
  };
}

export function unit(id: string, team: "ally" | "enemy", x: number, y: number, over: Partial<UnitView> = {}): UnitView {
  return {
    id,
    template_id: "t",
    name_zh: `單位${id.slice(-1)}`,
    team,
    pos: { x, y },
    hp: 10,
    max_hp: 20,
    shield: 0,
    mana: 5,
    max_mana: 10,
    stamina: 5,
    max_stamina: 10,
    ap: 2,
    move_points: 4,
    speed: 4,
    initiative: 10,
    weapon_name_zh: "劍",
    tags: [],
    skills: [],
    statuses: [],
    stacks: {},
    cooldowns: {},
    reaction_available: true,
    reaction_rules: [],
    ap_carry: 0,
    source: 1,
    source_max: 3,
    downed: false,
    escaped: false,
    owner_id: null,
    summon_expires_round: null,
    dismissed: false,
    ...over,
  };
}

export function object(id: string, kind: string, x: number, y: number, over: Partial<ObjectView> = {}): ObjectView {
  return { id, kind, pos: { x, y }, hp: 5, max_hp: 10, burning: null, ...over };
}

/** 4×3 的平地：(1,0) 高 2、(3,0) 深淵、(3,1) 牆、(0,2) 油面；主角 unit_0001 在 (0,0)。 */
export function smallView(over: Partial<BattleView> = {}): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < 3; y++) {
    for (let x = 0; x < 4; x++) {
      let t = tile(x, y);
      if (x === 1 && y === 0) t = tile(x, y, { height: 2 });
      if (x === 3 && y === 0) t = tile(x, y, { terrain: "chasm" });
      if (x === 3 && y === 1) t = tile(x, y, { terrain: "wall" });
      if (x === 0 && y === 2) t = tile(x, y, { surface: "oil" });
      tiles.push(t);
    }
  }
  return {
    team: "ally",
    map_id: "test",
    map_name_zh: "測試地圖",
    width: 4,
    height: 3,
    tiles,
    objects: [object("obj_0001", "oil_barrel", 2, 2), object("obj_0002", "crate", 1, 2, { burning: 2 })],
    units: [
      unit("unit_0001", "ally", 0, 0),
      unit("unit_0002", "ally", 0, 1, { hp: 0, downed: true }),
      unit("unit_0003", "enemy", 2, 1),
      unit("unit_0004", "enemy", 2, 0),
      unit("unit_0005", "enemy", 1, 1, { escaped: true }),
    ],
    traps: [{ owner_id: "unit_0001", team: "ally", pos: { x: 1, y: 1 }, skill_id: "trap", remaining: 3 }],
    turn_order: ["unit_0001", "unit_0003", "unit_0004"],
    active_unit: "unit_0001",
    round: 1,
    max_rounds: 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    ...over,
  };
}
