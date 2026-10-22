// 灌注技能（Phase 3-33d）：灌注鈕的限制、技能選單的變灰原因、預覽說明、待施放標示與徽章。
import { describe, expect, it } from "vitest";
import type { InfuseOptions, InfusionPreview, UnitView } from "../api/types";
import { infusedBadge } from "../render/unitLook";
import { actionLabel } from "./actions";
import { buildDrawModel } from "./drawModel";
import {
  infuseAction,
  infuseBlocked,
  infuseRows,
  infusionPreviewText,
  infusionTargetTiles,
  pendingInfusionText,
} from "./summonControl";
import { smallView, unit } from "./testFixtures";
import { unitNames } from "./units";

const HERO = "unit_0001";

function summon(id: string, over: Partial<UnitView> = {}): UnitView {
  return unit(id, "ally", 1, 0, { owner_id: HERO, summon_mode: "follow", summon_expires_round: 4, name_zh: "元素之靈", ...over });
}

const view = (over: Partial<UnitView> = {}) =>
  smallView({
    units: [unit(HERO, "ally", 0, 0, { ap: 3 }), summon("unit_0006", over), unit("unit_0003", "enemy", 2, 1)],
  });

const hero = (ap = 3) => unit(HERO, "ally", 0, 0, { ap });

describe("infuseBlocked（灌注鈕）", () => {
  it("is open on my turn with enough AP", () => {
    expect(infuseBlocked(view(), hero(), summon("unit_0006"), true)).toBeNull();
  });
  it("explains why it is closed", () => {
    expect(infuseBlocked(view(), hero(), summon("unit_0006"), false)).toBe("現在不是你的回合");
    expect(infuseBlocked(view(), hero(0), summon("unit_0006"), true)).toContain("AP 不足");
    expect(infuseBlocked(view(), hero(), summon("unit_0006", { infused: true }), true)).toContain("每隻每輪 1 次");
    const pending = summon("unit_0006", { infused: true, infused_skill_id: "skill_fire_bolt", infused_skill_name_zh: "火球術" });
    expect(infuseBlocked(view(), hero(), pending, true)).toContain("待施放的「火球術」");
  });
});

describe("infuseRows（技能選單）", () => {
  const options: InfuseOptions = {
    summon_id: "unit_0006",
    ap_cost: 1,
    problem: null,
    skills: [
      { skill_id: "skill_fire_bolt", name_zh: "火球術", problem: null },
      { skill_id: "skill_summon_spirit", name_zh: "召喚元素之靈", problem: "召喚技能不能灌注：召喚元素之靈" },
    ],
  };
  it("greys out the ones that cannot be infused, with the Chinese reason", () => {
    expect(infuseRows(options)).toEqual([
      { skillId: "skill_fire_bolt", name: "火球術", reason: null },
      { skillId: "skill_summon_spirit", name: "召喚元素之靈", reason: "召喚技能不能灌注：召喚元素之靈" },
    ]);
  });
  it("uses the summon-side problem when the skill itself is fine", () => {
    const rows = infuseRows({ ...options, problem: "元素之靈本輪已經被灌注過了" });
    expect(rows[0]!.reason).toBe("元素之靈本輪已經被灌注過了");
    expect(rows[1]!.reason).toContain("召喚技能");
  });
  it("builds the infuse_skill action and labels it", () => {
    const action = infuseAction(HERO, "unit_0006", "skill_fire_bolt");
    expect(action).toEqual({ type: "infuse_skill", unit_id: HERO, summon_id: "unit_0006", skill_id: "skill_fire_bolt" });
    expect(actionLabel(action, view(), { skill_fire_bolt: "火球術" })).toBe("灌注：火球術 → 元素之靈");
  });
});

describe("灌注預覽", () => {
  const base: InfusionPreview = {
    summon_id: "unit_0006",
    skill_id: "skill_fire_bolt",
    origin: [1, 0],
    target_id: "unit_0003",
    target_pos: null,
    direction: null,
    tiles: [[2, 1]],
    units: ["unit_0003"],
    no_target: false,
  };
  it("says where it casts from and at whom", () => {
    const names = unitNames(view());
    expect(infusionPreviewText(base, names)).toBe(`從 (1, 0) 施放 → ${names.name("unit_0003")}`);
    expect(infusionTargetTiles(base, view())).toEqual([{ x: 2, y: 1 }]);
  });
  it("warns when nothing can be targeted", () => {
    const none = { ...base, target_id: null, tiles: [], units: [], no_target: true };
    expect(infusionPreviewText(none, unitNames(view()))).toContain("選不到目標");
    expect(infusionTargetTiles(none, view())).toEqual([]);
  });
});

describe("待施放的標示", () => {
  it("shows the pending skill on the panel row", () => {
    expect(pendingInfusionText(summon("unit_0006"))).toBeNull();
    const pending = summon("unit_0006", { infused_skill_id: "skill_fire_bolt", infused_skill_name_zh: "火球術" });
    expect(pendingInfusionText(pending)).toBe("待施放：火球術（下回合開始時）");
  });
  it("draws the 灌 badge over a summon holding an infusion, not after it falls", () => {
    expect(infusedBadge({ infused: false, downed: false })).toBeNull();
    expect(infusedBadge({ infused: true, downed: false })).toMatchObject({ glyph: "灌" });
    expect(infusedBadge({ infused: true, downed: true })).toBeNull();
    const model = buildDrawModel(view({ infused_skill_id: "skill_fire_bolt" }), HERO);
    expect(model.units.find((u) => u.id === "unit_0006")?.infused).toBe(true);
    expect(model.units.find((u) => u.id === HERO)?.infused).toBe(false);
  });
});
