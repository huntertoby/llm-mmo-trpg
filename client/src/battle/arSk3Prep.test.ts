// AR-SK3：戰前佈置的格子記號（取代借來的紅框）與定案字（移植需求第 1 節第 5 項、第 2 節）。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, PrepOut, SkillCard, StepOut } from "../api/types";
import { frameOps, playbackPlan } from "./playback";
import { prepMarksOf, prepPromptText } from "./prep";
import { PREP_HINT_ZH } from "./skillTray";
import { PREP_TIP_ZH } from "../render/prepMarks";
import { tile, unit } from "./testFixtures";

const PREP = {
  unit_id: "unit_0001",
  zone: [[0, 4], [1, 5], [0, 6], [1, 6]],
  options: [
    { skill_id: "skill_trap", kind: "trap", tiles: [[0, 4], [1, 5], [0, 6]] },
    { skill_id: "skill_pool", kind: "surface", tiles: [[0, 4]] },
    { skill_id: "skill_none", kind: "rune", tiles: [] },
  ],
} as unknown as PrepOut;
const POOL = { id: "skill_pool", icon: { segments: [{ effects: [{ type: "create_surface", surface: "ice" }] }] } } as unknown as SkillCard;

describe("戰前佈置的格子記號", () => {
  it("只畫這一招放得下的格子（起始區其他格不畫）；指著放得下的格子才算 hover", () => {
    const d = prepMarksOf(PREP, "skill_trap", { x: 0, y: 6 });
    expect(d).toEqual({ cells: [{ x: 0, y: 4 }, { x: 1, y: 5 }, { x: 0, y: 6 }], hover: { x: 0, y: 6 }, kind: "trap", surface: null });
    expect(prepMarksOf(PREP, "skill_trap", { x: 1, y: 6 })?.hover).toBeNull();
    expect(prepMarksOf(PREP, "skill_trap", null)?.hover).toBeNull();
  });
  it("表面的預覽照技能卡第一個 create_surface 的表面；沒有可放的格子或不認得的招沒有記號", () => {
    expect(prepMarksOf(PREP, "skill_pool", null, POOL)).toMatchObject({ kind: "surface", surface: "ice" });
    expect(prepMarksOf(PREP, "skill_pool", null)).toMatchObject({ kind: "surface", surface: null });
    expect(prepMarksOf(PREP, "skill_none", null)).toBeNull();
    expect(prepMarksOf(PREP, "nope", null)).toBeNull();
  });
});

describe("定案字（移植需求第 2 節）", () => {
  it("視窗提示「框起來的起始區」、技能列「框起來的我方起始區」、滑過提示「放在這裡」", () => {
    expect(prepPromptText(PREP, "skill_trap", "捕獸夾")).toBe("「捕獸夾」：在框起來的起始區格子點一下放陷阱（共 3 格可放）；按 Esc 換一招。");
    expect(PREP_HINT_ZH).toBe("戰前佈置：在上方視窗選一招，再點框起來的我方起始區格子放下；或按「不佈置，直接開戰」。");
    expect(PREP_TIP_ZH).toBe("放在這裡");
    expect(prepPromptText(PREP, "skill_trap", "捕獸夾")).not.toContain("高亮");
  });
});

describe("放下的一下接在 prep_placed", () => {
  const v = { team: "ally", map_id: "t", width: 4, height: 7, tiles: [tile(0, 4)], objects: [], units: [unit("unit_0001", "ally", 2, 5)], traps: [], turn_order: [], active_unit: null, round: 1, max_rounds: 30, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
  const res = (reduced: boolean) =>
    playbackPlan(
      { steps: [{ actor_id: "unit_0001", events: [{ seq: 1, round: 1, type: "prep_placed", unit_id: "unit_0001", skill_id: "skill_trap", kind: "trap", pos: { x: 1, y: 5 } }], view: v, step: { type: "prepare" } } as unknown as StepOut], initial_view: v, view: v } as unknown as BattleResponse,
      "unit_0001",
      "normal",
      {},
      new Set(),
      undefined,
      undefined,
      undefined,
      reduced,
    );
  it("畫面更新之後播放下的一下（那一格）；減少動態時不播", () => {
    const ops = frameOps(res(false).frames[0]!);
    const i = ops.findIndex((o) => o.op === "placed");
    expect(ops[i]).toEqual({ op: "placed", tiles: [{ x: 1, y: 5 }] });
    expect(i).toBe(ops.findIndex((o) => o.op === "view") + 1);
    expect(frameOps(res(true).frames[0]!).some((o) => o.op === "placed")).toBe(false);
  });
});
