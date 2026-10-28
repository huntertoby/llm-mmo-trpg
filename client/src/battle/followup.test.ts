// 複合技能第二段的暫停選取與延遲段（蓄力）的倒數顯示（Phase 3F-4b）。
import { describe, expect, it } from "vitest";
import type { ChargeOut, FollowupOption, Pending, StatusView, TelegraphOut } from "../api/types";
import {
  chargeCountdown,
  chargeStatusText,
  chargeTiles,
  followupAction,
  followupMode,
  followupPromptText,
  followupTargetOf,
  isFollowupPending,
} from "./followup";
import { telegraphIsEmpty, telegraphLines, telegraphMarks } from "./telegraph";
import { buildDrawModel } from "./drawModel";
import { smallView, unit } from "./testFixtures";

const pending = { kind: "followup", unit_id: "unit_0001", skill_id: "skill_retreating_slash" } as Pending;
const leap = (x: number, y: number): FollowupOption =>
  ({ followup_target: { target_pos: { x, y } }, tiles: [[x, y]] }) as FollowupOption;
const hit = (id: string): FollowupOption =>
  ({ followup_target: { target_id: id }, tiles: [[3, 1]] }) as FollowupOption;

describe("the paused second part", () => {
  it("recognises the followup pause", () => {
    expect(isFollowupPending(pending)).toBe(true);
    expect(isFollowupPending({ ...pending, kind: "copy_skill" } as Pending)).toBe(false);
    expect(isFollowupPending(null)).toBe(false);
  });

  it("turns each option into a clickable action that keeps the followup target", () => {
    const a = followupAction(pending, leap(1, 3));
    expect(a).toMatchObject({ type: "use_skill", skill_id: "skill_retreating_slash", target_pos: { x: 1, y: 3 } });
    expect(followupTargetOf(a)).toEqual({ target_pos: { x: 1, y: 3 } });
    expect(followupTargetOf(null)).toBeNull();
  });

  it("builds a mode with tiles for landings and units for targets", () => {
    const mode = followupMode(pending, [leap(1, 3), leap(1, 2), hit("unit_0003")], "回馬斬");
    expect(mode.label).toBe("回馬斬（第二段）");
    expect([...mode.targets.tiles.keys()].sort()).toEqual(["1,2", "1,3"]);
    expect([...mode.targets.units.keys()]).toEqual(["unit_0003"]);
  });

  it("explains what to do", () => {
    expect(followupPromptText("回馬斬", 3)).toContain("共 3 個可選");
    expect(followupPromptText("回馬斬", 0)).toContain("放棄第二段");
  });
});

const charging = (over: Partial<StatusView> = {}): StatusView => ({
  status_id: "charging",
  remaining: 1,
  source_id: "unit_0001",
  amount: null,
  blast_radius: null,
  skill_id: "skill_charged_cleave",
  release: "next_turn",
  charge_tiles: [
    { x: 0, y: 0 },
    { x: 1, y: 0 },
  ],
  cost_status: false,
  ...over,
});

describe("the charging (delayed segment) countdown", () => {
  it("describes the release and the planned area", () => {
    expect(chargeStatusText(charging(), { skill_charged_cleave: "蓄力斬" })).toBe(
      "蓄力「蓄力斬」：下回合開始時釋放，以自己為中心影響 2 格",
    );
    expect(chargeStatusText(charging({ release: "attacked" }))).toContain("被敵人攻擊就釋放");
  });

  it("puts a countdown badge on the charging unit", () => {
    expect(chargeCountdown([charging()])).toBe(1);
    expect(chargeCountdown([])).toBeNull();
    const view = smallView();
    const hero = unit("unit_0001", "ally", 0, 0, { statuses: [charging()] });
    const drawn = buildDrawModel({ ...view, units: [hero, ...view.units.slice(1)] }, "unit_0001");
    expect(drawn.units.find((u) => u.id === "unit_0001")?.charge).toBe(1);
  });

  const charge: ChargeOut = {
    unit_id: "unit_0001",
    skill_id: "skill_charged_cleave",
    name_zh: "蓄力斬",
    release: "next_turn",
    remaining: 1,
    pos: { x: 1, y: 1 },
    tiles: [
      { x: 1, y: 1 },
      { x: 2, y: 1 },
    ],
    text: "勇者 正在蓄力「蓄力斬」：下回合開始時釋放，以自己為中心影響 2 格",
  };
  const telegraph: TelegraphOut = { round: 1, changes: [], burning: [], upcoming: [], bombs: [], charges: [charge] };

  it("shows in the telegraph with marks on the caster and the area", () => {
    expect(telegraphIsEmpty(telegraph)).toBe(false);
    expect(telegraphLines(telegraph)).toEqual([charge.text]);
    const marks = telegraphMarks(telegraph, smallView());
    expect(marks.map((m) => [m.pos.x, m.pos.y, m.glyph])).toEqual([
      [1, 1, "蓄1"],
      [2, 1, "蓄"],
    ]);
    expect(chargeTiles([charge, charge])).toHaveLength(2);
  });
});

describe("the preview line of the second part", () => {
  it("depends on the kind", async () => {
    const { followupLine } = await import("./scenePreview");
    expect(followupLine(null, "(2, 1)", 3)).toContain("位移到 (2, 1) 後");
    expect(followupLine("delayed", "(2, 1)", 9)).toContain("延遲段：施放後開始蓄力");
    expect(followupLine("after_action", "(2, 1)", 1)).toContain("位移到選的落點");
  });
});
