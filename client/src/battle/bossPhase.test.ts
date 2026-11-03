// Phase 5F-2：Boss 階段的單位卡文字與轉換提示
import { describe, expect, it } from "vitest";
import { unit } from "./testFixtures";
import { phaseNotices, phaseText } from "./bossPhase";
import { phaseRows } from "../ui/UnitInfo";

describe("phaseText", () => {
  it("沒有階段時不列", () => {
    expect(phaseText(unit("unit_0002", "enemy", 1, 1))).toBeNull();
    expect(phaseRows(unit("unit_0002", "enemy", 1, 1))).toEqual([]);
  });

  it("列出目前階段與下一個門檻", () => {
    const u = unit("unit_0002", "enemy", 1, 1, {
      boss_phase: { index: 2, total: 3, name_zh: "鎖霧", next_name_zh: "歸一", next_permille: 300 },
    });
    expect(phaseText(u)).toBe("2/3 鎖霧（HP 30% 以下進入「歸一」）");
    expect(phaseRows(u)).toEqual([["階段", "2/3 鎖霧（HP 30% 以下進入「歸一」）"]]);
  });

  it("最後階段", () => {
    const u = unit("unit_0002", "enemy", 1, 1, {
      boss_phase: { index: 3, total: 3, name_zh: "歸一", next_name_zh: null, next_permille: null },
    });
    expect(phaseText(u)).toBe("3/3 歸一（最後階段）");
  });
});

describe("phaseNotices", () => {
  it("只取階段轉換事件的文字", () => {
    const steps = [
      {
        actor_id: null,
        step: null,
        view: {} as never,
        events: [
          { type: "turn_started", text: "回合開始" },
          { type: "boss_phase_changed", text: "◆ 霧鎖真人進入第 2 階段「鎖霧」（HP 60% 以下）" },
        ],
      },
    ];
    expect(phaseNotices({ steps })).toEqual(["◆ 霧鎖真人進入第 2 階段「鎖霧」（HP 60% 以下）"]);
    expect(phaseNotices({ steps: [] })).toEqual([]);
  });
});
