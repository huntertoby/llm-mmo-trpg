// Phase 3J-1a：單位資訊的形態列（只有文字；外觀在 3J-5）
import { describe, expect, it } from "vitest";
import { unit } from "../battle/testFixtures";
import { formRows } from "./UnitInfo";

describe("formRows", () => {
  it("不在形態中、也沒有冷卻時沒有任何列", () => {
    expect(formRows(unit("unit_0001", "ally", 0, 0))).toEqual([]);
  });

  it("列出目前形態、天生武器、效果、維持費與冷卻中的形態", () => {
    const u = unit("unit_0001", "ally", 0, 0, {
      form: {
        form_id: "bear",
        name_zh: "熊",
        category: "physical",
        look: "form_bear",
        element: null,
        natural_weapon_zh: "熊爪 1d8 近戰（力量／體質取較高 × 0.3，目前 +4）",
        effects_zh: ["最大 HP +15%", "防禦 +10%", "移動 −1"],
        upkeep_zh: "每回合開始 −5 耐力（不夠就自動解除）；離開後這個形態冷卻 2 回合",
      },
      form_cooldowns: [{ form_id: "cat", name_zh: "貓", remaining: 2 }],
    });
    const rows = formRows(u);
    expect(rows.map(([k]) => k)).toEqual(["形態", "　天生武器", "　效果", "　維持", "形態冷卻"]);
    expect(rows[0]?.[1]).toBe("熊");
    expect(rows[2]?.[1]).toBe("最大 HP +15%、防禦 +10%、移動 −1");
    expect(rows[4]?.[1]).toBe("貓 2 回合");
  });
});
