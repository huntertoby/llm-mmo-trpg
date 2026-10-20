// 複合技能（位移 → 動作，Phase 3F-3b）的兩段選取。
import { describe, expect, it } from "vitest";
import type { Action, SkillCard } from "../api/types";
import { buildComposite, secondChoices, soleCenter } from "./composite";
import { smallView, unit } from "./testFixtures";
import {
  actionAtTile,
  compositePromptFor,
  hurlLandings,
  hurlObjectAt,
  hurlPickPos,
  isHurlMode,
  isSelfOnly,
  skillButtons,
  skillMode,
  targetTiles,
} from "./targeting";

const H = "unit_0001";
const use = (extra: Record<string, unknown>): Action =>
  ({ type: "use_skill", unit_id: H, skill_id: "shadow", ...extra }) as Action;
const hero = unit(H, "ally", 0, 1, { skills: ["shadow"] });
const foe = unit("unit_0002", "enemy", 4, 1);
const view = smallView({ units: [hero, foe] });

// 傳送到 (2,1) 或 (3,2)，落點接東／南的錐形
const teleportCone: Action[] = [
  use({ target_pos: { x: 2, y: 1 }, followup_target: { direction: "east" } }),
  use({ target_pos: { x: 2, y: 1 }, followup_target: { direction: "south" } }),
  use({ target_pos: { x: 3, y: 2 }, followup_target: { direction: "east" } }),
];
// 跳到 (1,1) 或 (2,2)，以落點為中心（followup_target 為 null）
const leapSlam: Action[] = [
  use({ target_pos: { x: 1, y: 1 }, followup_target: null }),
  use({ target_pos: { x: 2, y: 2 }, followup_target: null }),
];
const button = (actions: Action[], composite = true) => ({
  skillId: "shadow",
  name: "瞬影旋斬",
  costs: [],
  cooldown: 0,
  actions,
  disabledReason: null,
  composite,
});

describe("buildComposite", () => {
  it("groups the follow-up choices under each landing", () => {
    const set = buildComposite(teleportCone);
    expect([...set.keys()]).toEqual(["p:2,1", "p:3,2"]);
    expect(set.get("p:2,1")?.seconds.map((s) => s.key)).toEqual(["d:east", "d:south"]);
    expect(set.get("p:3,2")?.seconds.map((s) => s.key)).toEqual(["d:east"]);
  });

  it("groups by target unit for a dash and lists single targets as unit choices", () => {
    const dash = [
      use({ target_id: "unit_0002", followup_target: { target_id: "unit_0002" } }),
      use({ target_id: "unit_0002", followup_target: { target_id: "unit_0003" } }),
    ];
    const set = buildComposite(dash);
    expect([...set.keys()]).toEqual(["u:unit_0002"]);
    expect(set.get("u:unit_0002")?.seconds.map((s) => s.key)).toEqual(["u:unit_0002", "u:unit_0003"]);
  });

  it("recognises a landing whose only follow-up is centered on it", () => {
    const set = buildComposite(leapSlam);
    expect(soleCenter(set.get("p:1,1")!)?.key).toBe("c");
    expect(soleCenter(buildComposite(teleportCone).get("p:2,1")!)).toBeNull();
  });
});

describe("a composite skill mode (teleport then cone)", () => {
  const mode = skillMode(button(teleportCone));

  it("is a two-stage mode and not a plain tile or direction mode", () => {
    expect(isHurlMode(mode)).toBe(true);
    expect(mode.targets.pairKind).toBe("composite");
    expect(mode.targets.tiles.size).toBe(0);
    expect(mode.targets.directions.size).toBe(0);
    expect(isSelfOnly(mode.targets)).toBe(false);
  });

  it("stage 1 highlights the landings and clicking one picks it, without an action", () => {
    expect(targetTiles(mode, view, hero).targets).toEqual([{ x: 2, y: 1 }, { x: 3, y: 2 }]);
    expect(hurlObjectAt(mode, view, { x: 2, y: 1 })).toBe("p:2,1");
    expect(hurlObjectAt(mode, view, { x: 0, y: 0 })).toBeNull();
    expect(actionAtTile(mode, view, hero, { x: 2, y: 1 })).toBeNull();
    expect(compositePromptFor(mode, null)).toContain("第 1 段");
  });

  it("stage 2 marks the directions around the landing and clicking one gives the action", () => {
    const tiles = targetTiles(mode, view, hero, "p:2,1");
    expect(tiles.directions).toEqual([
      { pos: { x: 3, y: 1 }, direction: "east" },
      { pos: { x: 2, y: 2 }, direction: "south" },
    ]);
    expect(hurlLandings(mode, "p:2,1", view)).toEqual([{ x: 3, y: 1 }, { x: 2, y: 2 }]);
    expect(actionAtTile(mode, view, hero, { x: 3, y: 1 }, "p:2,1")).toBe(teleportCone[0]);
    expect(actionAtTile(mode, view, hero, { x: 2, y: 2 }, "p:2,1")).toBe(teleportCone[1]);
    expect(actionAtTile(mode, view, hero, { x: 1, y: 1 }, "p:2,1")).toBeNull(); // 落點背後不是方向
    expect(actionAtTile(mode, view, hero, { x: 3, y: 1 }, "p:3,2")).toBeNull(); // 不是這個落點的方向
    expect(hurlPickPos(mode, view, "p:2,1")).toEqual({ x: 2, y: 1 });
    expect(compositePromptFor(mode, "p:2,1")).toContain("第 2 段");
  });

  it("offers the panel buttons for the second stage", () => {
    const first = mode.targets.composite?.get("p:2,1");
    expect(first).toBeDefined();
    expect(secondChoices(first!, view).map((c) => c.label)).toEqual(["→ 向東", "↓ 向南"]);
  });
});

describe("a composite skill mode (leap then centered slam)", () => {
  const mode = skillMode(button(leapSlam));

  it("casts with a single click on the landing", () => {
    expect(hurlObjectAt(mode, view, { x: 1, y: 1 })).toBeNull(); // 不必先選
    expect(actionAtTile(mode, view, hero, { x: 1, y: 1 })).toBe(leapSlam[0]);
    expect(actionAtTile(mode, view, hero, { x: 2, y: 2 })).toBe(leapSlam[1]);
    expect(actionAtTile(mode, view, hero, { x: 3, y: 3 })).toBeNull();
  });
});

describe("a composite skill that dashes at a unit", () => {
  const dash = [
    use({ target_id: "unit_0002", followup_target: { direction: "east" } }),
    use({ target_id: "unit_0002", followup_target: { direction: "west" } }),
  ];
  const mode = skillMode(button(dash));

  it("picks the target first, then the direction from the panel buttons", () => {
    expect(hurlObjectAt(mode, view, { x: 4, y: 1 })).toBe("u:unit_0002");
    expect(hurlPickPos(mode, view, "u:unit_0002")).toEqual({ x: 4, y: 1 });
    const first = mode.targets.composite?.get("u:unit_0002");
    expect(secondChoices(first!, view).map((c) => c.label)).toEqual(["→ 向東", "← 向西"]);
    // 落點未知：戰場上不標方向格
    expect(targetTiles(mode, view, hero, "u:unit_0002").directions).toEqual([]);
  });
});

describe("skillButtons", () => {
  it("marks a skill with a second segment as composite", () => {
    const cards = {
      shadow: { id: "shadow", name_zh: "瞬影旋斬", cost: [], followup: "到達落點後……" } as unknown as SkillCard,
    };
    const [b] = skillButtons(hero, teleportCone, cards);
    expect(b?.composite).toBe(true);
    const [plain] = skillButtons(hero, teleportCone, { shadow: { ...cards.shadow, followup: null } as unknown as SkillCard });
    expect(plain?.composite).toBe(false);
  });
});
