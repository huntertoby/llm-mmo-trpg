import { describe, expect, it } from "vitest";
import type { Action, RaceView } from "../api/types";
import { actionLabel } from "./actions";
import { passiveLabel, passiveLine, passiveSegments, raceBlockedReason, raceBattleCardLines, raceDetailText, raceHudText, raceLabel, raceModes, raceUsesText } from "./race";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { actionAtTile, basicModes, fallbackActions, isSelfOnly } from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const FOE = "unit_0002";

function race(over: Partial<RaceView> = {}): RaceView {
  return {
    id: "seafolk",
    name_zh: "海民",
    skill_id: "race_anchor_haul",
    skill_name_zh: "拋錨",
    skill_description_zh: "把 4 格內一個敵人拉近 2 格，不造成撞擊傷害。每場限用 1 次。",
    skill_ap: 1,
    skill_uses_max: 1,
    skill_uses_left: 1,
    skill_shape: "single",
    skill_range: 4,
    skill_size: null,
    skill_choices: [],
    passive_name_zh: "雨中海步",
    passive_description_zh: "下雨天氣時，移動 +1。",
    passive_active: false,
    look: { skin: "#b07a52", tusks: false, beard: false, slit_eyes: false, ridge: false, spines: false },
    ...over,
  };
}

const pull = { type: "use_race_skill", unit_id: H, target_id: FOE } as Action;

describe("race skill modes (Phase 3R-2)", () => {
  it("has no race modes without a race", () => {
    expect(raceModes(unit(H, "ally", 1, 1), [pull])).toEqual([]);
    expect(raceModes(null, [pull])).toEqual([]);
  });

  it("makes one race mode whose targets are the legal units", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    const [mode] = raceModes(hero, [pull]);
    expect(mode?.kind).toBe("race");
    expect(mode?.label).toBe("拋錨");
    expect(mode?.targets.units.get(FOE)).toBe(pull);
    expect(mode?.blockedReason).toBeUndefined();
  });

  it("is a self-only instant mode for self skills", () => {
    const self = { type: "use_race_skill", unit_id: H } as Action;
    const hero = unit(H, "ally", 1, 1, { race: race({ skill_shape: "self", skill_name_zh: "應變" }) });
    const [mode] = raceModes(hero, [self]);
    expect(mode !== undefined && isSelfOnly(mode.targets)).toBe(true);
    expect(mode?.targets.self).toBe(self);
  });

  it("splits Overcharge into one mode per resource", () => {
    const stamina = { type: "use_race_skill", unit_id: H, choice: "stamina" } as Action;
    const mana = { type: "use_race_skill", unit_id: H, choice: "mana" } as Action;
    const hero = unit(H, "ally", 1, 1, {
      race: race({ skill_shape: "self", skill_name_zh: "過充", skill_choices: ["stamina", "mana"] }),
    });
    const modes = raceModes(hero, [stamina, mana]);
    expect(modes.map((m) => m.label)).toEqual(["過充（耐力）", "過充（法力）"]);
    expect(modes.map((m) => m.targets.self)).toEqual([stamina, mana]);
    expect(modes.map((m) => m.key)).toEqual(["race:stamina", "race:mana"]);
  });

  it("registers a hurl as two stages: the object first, then the landing tile", () => {
    const hurl = { type: "use_race_skill", unit_id: H, target_object_id: "obj_1", target_pos: { x: 3, y: 1 } } as Action;
    const hero = unit(H, "ally", 1, 1, { race: race({ skill_shape: "object_then_tile", skill_name_zh: "蠻力投擲" }) });
    const [mode] = raceModes(hero, [hurl]);
    expect(mode?.targets.pairKind).toBe("hurl");
    expect(mode?.targets.hurls.get("obj_1")?.get("3,1")).toBe(hurl);
  });

  it("registers cone directions and ground tiles", () => {
    const breath = { type: "use_race_skill", unit_id: H, direction: "east" } as Action;
    const tile = { type: "use_race_skill", unit_id: H, target_pos: { x: 2, y: 1 } } as Action;
    const hero = unit(H, "ally", 1, 1, { race: race({ skill_shape: "cone" }) });
    expect(raceModes(hero, [breath])[0]?.targets.directions.get("east")).toBe(breath);
    expect(raceModes(hero, [tile])[0]?.targets.tiles.get("2,1")).toBe(tile);
  });

  it("explains why the button is grey", () => {
    const hero = unit(H, "ally", 1, 1, { ap: 0, race: race() });
    expect(raceBlockedReason(hero, race(), false)).toMatch(/AP 不足/);
    expect(raceBlockedReason(hero, race({ skill_uses_left: 0 }), false)).toMatch(/本場已用完/);
    expect(raceBlockedReason(unit(H, "ally", 1, 1, { ap: 2 }), race(), false)).toMatch(/沒有合法的目標/);
    expect(raceBlockedReason(hero, race(), true)).toBeUndefined();
    const [mode] = raceModes(hero, []);
    expect(mode?.blockedReason).toMatch(/AP 不足/);
  });

  it("keeps race skills out of the basic and fallback actions", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    expect(basicModes([pull])).toEqual([]);
    expect(fallbackActions([pull], hero)).toEqual([]);
  });

  it("labels the action with the race skill name and its target", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    const view = smallView({ units: [hero, unit(FOE, "enemy", 4, 1)] });
    expect(actionLabel(pull, view, {})).toBe("種族技：拋錨 → a 單位2");
    expect(actionLabel({ type: "use_race_skill", unit_id: H, choice: "mana" } as Action, view, {})).toBe("種族技：拋錨 → 法力");
  });

  it("picks the unit under the cursor for a single-target race mode", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    const view = smallView({ units: [hero, unit(FOE, "enemy", 4, 1)] });
    const [mode] = raceModes(hero, [pull]);
    expect(mode !== undefined && actionAtTile(mode, view, hero, { x: 4, y: 1 })).toBe(pull);
  });
});

describe("race text", () => {
  it("builds the card lines from the same data the engine uses", () => {
    const lines = raceBattleCardLines(race());
    expect(lines[0]).toContain("拉近 2 格");
    expect(lines[1]).toBe("花費 1 AP・本場限用 1 次（剩 1 次）・不佔技能欄");
    expect(lines[2]).toBe("選一個目標・射程 4 格");
  });

  it("formats labels, uses and the passive line", () => {
    expect(raceLabel(race(), "")).toBe("拋錨");
    expect(raceLabel(race(), "stamina")).toBe("拋錨（耐力）");
    expect(raceUsesText(race({ skill_uses_left: 0 }))).toBe("1 AP・剩 0／1 次");
    expect(passiveLine(race())).toBe("被動「雨中海步」：下雨天氣時，移動 +1。");
    expect(passiveLine(race({ passive_active: true }))).toBe("被動「雨中海步」：下雨天氣時，移動 +1。・有作用");
  });

  it("writes one HUD line only for raced heroes", () => {
    expect(raceHudText(unit(H, "ally", 1, 1))).toBeNull();
    const hero = unit(H, "ally", 1, 1, { race: race({ passive_active: true }) });
    expect(raceHudText(hero)).toBe("種族：海民｜拋錨 剩 1／1 次｜被動「雨中海步」・有作用");
  });
});

describe("race passive overridden by gear (E3; E3b 用字)", () => {
  it("全部有作用：被動「〇〇」・有作用（沒作用也沒被蓋過時不加註）", () => {
    expect(passiveSegments(race({ passive_active: true }))).toEqual([{ text: "有作用", off: false }]);
    expect(passiveLabel(race({ passive_active: true }))).toBe("被動「雨中海步」・有作用");
    expect(passiveSegments(race())).toEqual([]);
    expect(raceDetailText(race())).toBe("海民・種族技「拋錨」・被動「雨中海步」");
  });

  it("部分被蓋過：灰色只套在被蓋過的那一段", () => {
    const r = race({ passive_active: true, passive_overridden_zh: "水的部分被身體的「站在水上，移動 +2」蓋過", passive_overridden_full: false });
    expect(passiveSegments(r)).toEqual([
      { text: "水的部分被身體的「站在水上，移動 +2」蓋過", off: true },
      { text: "，其他有作用", off: false },
    ]);
    expect(passiveLabel(r)).toBe("被動「雨中海步」・水的部分被身體的「站在水上，移動 +2」蓋過，其他有作用");
    expect(raceDetailText(r)).toBe("海民・種族技「拋錨」・被動「雨中海步」・水的部分被身體的「站在水上，移動 +2」蓋過，其他有作用");
    // 被動此刻沒作用時不寫「其他有作用」
    expect(passiveSegments({ ...r, passive_active: false })).toEqual([{ text: "水的部分被身體的「站在水上，移動 +2」蓋過", off: true }]);
  });

  it("全部被蓋過：整段灰色，寫「沒有作用」", () => {
    const r = race({ passive_active: true, passive_overridden_zh: "被腳的「下雨時移動 +2」蓋過", passive_overridden_full: true });
    expect(passiveSegments(r)).toEqual([{ text: "被腳的「下雨時移動 +2」蓋過，沒有作用", off: true }]);
    expect(passiveLine(r)).toBe("被動「雨中海步」：下雨天氣時，移動 +1。・被腳的「下雨時移動 +2」蓋過，沒有作用");
    const hero = { ...unit(H, "ally", 1, 1), race: r };
    expect(raceHudText(hero)).toBe("種族：海民｜拋錨 剩 1／1 次｜被動「雨中海步」・被腳的「下雨時移動 +2」蓋過，沒有作用");
    // 兩件裝備各蓋一部分、合起來整條被蓋過：照伺服器的 full
    const split = race({ passive_overridden_zh: "水的部分被身體的「A」蓋過；冰的部分被腳的「B」蓋過", passive_overridden_full: true });
    expect(passiveSegments(split)).toEqual([{ text: "水的部分被身體的「A」蓋過；冰的部分被腳的「B」蓋過，沒有作用", off: true }]);
  });

  it("不用括號；HUD 與角色面板都用 RacePassive，灰色與 text-wrap 有 CSS", () => {
    for (const r of [race({ passive_active: true }), race({ passive_overridden_zh: "被腳的「X」蓋過", passive_overridden_full: true })]) {
      expect(passiveLabel(r)).not.toMatch(/[（）]/);
    }
    expect(readFile(SRC_DIR, "ui/Hud.tsx")).toContain("<RacePassive race={hero.race} />");
    expect(readFile(SRC_DIR, "ui/UnitInfo.tsx")).toContain("<RaceDetail");
    expect(readFile(SRC_DIR, "ui/RacePassive.tsx")).toContain('className="race-off"');
    const css = readFile(SRC_DIR, "styles/hud.css");
    expect(css).toMatch(/\.race-passive \.race-off \{\s*color: var\(--muted\);/);
    expect(css).toMatch(/\.hud-race \{\s*text-wrap: pretty;/);
  });
});
