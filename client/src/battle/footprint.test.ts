// GB-4a：`battle/footprint.ts`（佔格、點格找單位、部位、演出落點）。1 格單位一律退化成只看 `pos`。
import { describe, expect, it } from "vitest";
import { asEvent, isAttackRolled, type PartView, type Pos } from "../api/types";
import {
  giantPartStates,
  hitLocator,
  hitTileOf,
  isGiant,
  nearestTile,
  occupies,
  partAtTile,
  standingAtTile,
  unitAtTile,
  unitTiles,
  unitsOnTile,
} from "./footprint";
import { unit } from "./testFixtures";

const p = (x: number, y: number): Pos => ({ x, y });
const NINE = [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => p(5 + dx, 3 + dy)));
const part = (id: string, tiles: Pos[], over: Partial<PartView> = {}): PartView => ({
  id,
  name_zh: id,
  hp: 1,
  max_hp: 1,
  broken: false,
  exposed: true,
  reach: "any",
  break_lines_zh: [],
  tiles,
  ...over,
});
const giant = unit("unit_0009", "enemy", 5, 3, {
  footprint: 3,
  tiles: NINE,
  parts: [part("core", [p(5, 3)], { exposed: false }), part("shell_seam", [p(4, 3), p(6, 3)]), part("vent", [p(4, 2), p(5, 2), p(6, 2)])],
});
const one = unit("unit_0001", "ally", 2, 2);

describe("佔格", () => {
  it("巨型單位 9 格；1 格單位＝pos", () => {
    expect(isGiant(giant)).toBe(true);
    expect(isGiant(one)).toBe(false);
    expect(unitTiles(giant)).toEqual(NINE);
    expect(unitTiles(one)).toEqual([p(2, 2)]);
  });
  it("occupies：9 格都算、外圍不算；1 格單位只有自己那格", () => {
    for (const t of NINE) expect(occupies(giant, t)).toBe(true);
    for (const t of [p(3, 3), p(7, 3), p(5, 1), p(5, 5), p(3, 1)]) expect(occupies(giant, t)).toBe(false);
    expect(occupies(one, p(2, 2))).toBe(true);
    expect(occupies(one, p(2, 3))).toBe(false);
  });
  it("footprint 沒給（舊資料、1 格）時不認 tiles", () => {
    const odd = unit("unit_0005", "enemy", 1, 1, { tiles: [p(1, 1), p(2, 1)] });
    expect(occupies(odd, p(2, 1))).toBe(false);
  });
});

describe("點格找單位", () => {
  const down = unit("unit_0003", "enemy", 2, 2, { downed: true });
  const units = [down, one, giant];
  it("unitsOnTile 照順序；unitAtTile 站著的優先", () => {
    expect(unitsOnTile(units, p(2, 2)).map((u) => u.id)).toEqual(["unit_0003", "unit_0001"]);
    expect(unitAtTile(units, p(2, 2))?.id).toBe("unit_0001");
    expect(unitAtTile([down], p(2, 2))?.id).toBe("unit_0003");
    expect(unitAtTile(units, p(4, 4))?.id).toBe("unit_0009");
    expect(unitAtTile(units, null)).toBeUndefined();
  });
  it("standingAtTile 不含倒下", () => {
    expect(standingAtTile([down], p(2, 2))).toBeUndefined();
    expect(standingAtTile(units, p(6, 2))?.id).toBe("unit_0009");
  });
});

describe("nearestTile", () => {
  it("夾進方塊；1 格＝pos", () => {
    expect(nearestTile(giant, p(5, 9))).toEqual(p(5, 4));
    expect(nearestTile(giant, p(9, 3))).toEqual(p(6, 3));
    expect(nearestTile(giant, p(0, 0))).toEqual(p(4, 2));
    expect(nearestTile(giant, p(5, 3))).toEqual(p(5, 3));
    expect(nearestTile(one, p(9, 9))).toEqual(p(2, 2));
  });
});

describe("部位", () => {
  it("partAtTile：部位格；前殼為 null", () => {
    expect(partAtTile(giant, p(6, 3))?.id).toBe("shell_seam");
    expect(partAtTile(giant, p(5, 2))?.id).toBe("vent");
    expect(partAtTile(giant, p(5, 3))?.id).toBe("core");
    expect(partAtTile(giant, p(5, 4))).toBeNull();
  });
  it("giantPartStates：沒在選目標時只看破與露出；有選項時灰掉打不到的", () => {
    expect(giantPartStates(giant, null).map((s) => [s.id, s.state])).toEqual([
      ["core", "hidden"],
      ["shell_seam", "ok"],
      ["vent", "ok"],
    ]);
    const opts = [
      { part_id: "core", name_zh: "核心", ok: false, reason_zh: "呼吸階段才露出" },
      { part_id: "shell_seam", name_zh: "殼縫", ok: true, reason_zh: null },
      { part_id: "vent", name_zh: "熔岩噴口", ok: false, reason_zh: "只有遠程才打得到" },
    ];
    const states = giantPartStates(giant, opts);
    expect(states.map((s) => [s.id, s.state, s.reason])).toEqual([
      ["core", "hidden", "呼吸階段才露出"],
      ["shell_seam", "ok", null],
      ["vent", "blocked", "只有遠程才打得到"],
    ]);
    expect(states[2]?.tiles).toEqual([p(4, 2), p(5, 2), p(6, 2)]);
  });
  it("1 格頭目（部位沒綁格）沒有標示", () => {
    const lord = unit("unit_0004", "enemy", 1, 1, { parts: [part("whisk", [], { tiles: null })] });
    expect(giantPartStates(lord, null)).toEqual([]);
    expect(partAtTile(lord, p(1, 1))).toBeNull();
  });
});

describe("事件窄化與演出落點", () => {
  const rolled = (hit_tile?: Pos) =>
    asEvent({ seq: 1, round: 1, type: "attack_rolled", attacker_id: "unit_0001", target_id: "unit_0009", hit: true, ...(hit_tile === undefined ? {} : { hit_tile }) });
  it("attack_rolled.hit_tile", () => {
    expect(isAttackRolled(rolled())).toBe(true);
    expect(hitTileOf(rolled(p(4, 3)))).toEqual(p(4, 3));
    expect(hitTileOf(rolled())).toBeNull();
    expect(hitTileOf(asEvent({ seq: 1, round: 1, type: "damage_dealt", hit_tile: p(1, 1) }))).toBeNull();
  });
  it("hitLocator：命中判定帶 hit_tile 後，目標位置＝那一格；1 格單位照 pos", () => {
    const loc = hitLocator([one, giant]);
    expect(loc.at("unit_0009")).toEqual(p(5, 3));
    loc.note(rolled(p(4, 4)));
    expect(loc.at("unit_0009")).toEqual(p(4, 4));
    expect(loc.at("unit_0001")).toEqual(p(2, 2));
    loc.note(rolled());
    expect(loc.at("unit_0009")).toEqual(p(5, 3));
    expect(loc.at(undefined)).toBeNull();
  });
  it("沒有命中判定的傷害打巨型單位：落在離來源最近的佔格", () => {
    const loc = hitLocator([one, giant]);
    loc.note(asEvent({ seq: 2, round: 1, type: "damage_dealt", source_id: "unit_0001", target_id: "unit_0009", amount: 3 }));
    expect(loc.at("unit_0009")).toEqual(p(4, 2));
  });
  it("1 格目標的傷害不改位置", () => {
    const loc = hitLocator([one, giant]);
    loc.note(asEvent({ seq: 2, round: 1, type: "damage_dealt", source_id: "unit_0009", target_id: "unit_0001", amount: 3 }));
    expect(loc.at("unit_0001")).toEqual(p(2, 2));
  });
});
