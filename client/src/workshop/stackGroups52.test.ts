// 3-52：層數選單依「累積在你身上」「疊在敵人身上」分組（後端 `info.group_zh`），對象由後端的 effect_fixes 自動改。
import { describe, expect, it } from "vitest";

import type { Choice } from "../api/types";
import { conformAffects, type Json } from "./draft";
import { groupChoices } from "./playerView";

const choice = (value: string, group?: string): Choice =>
  ({ value, name_zh: value, description_zh: "", params: [], info: group === undefined ? {} : { group_zh: group } }) as unknown as Choice;

describe("groupChoices", () => {
  it("依 info.group_zh 分組，組的順序照第一次出現", () => {
    const groups = groupChoices([
      choice("combo_point", "累積在你身上"),
      choice("ki", "累積在你身上"),
      choice("hoarfrost", "疊在敵人身上"),
    ]);
    expect(groups.map(([label, items]) => [label, items.map((c) => c.value)])).toEqual([
      ["累積在你身上", ["combo_point", "ki"]],
      ["疊在敵人身上", ["hoarfrost"]],
    ]);
  });

  it("沒有分組名的欄位全部放同一組（不顯示組名）", () => {
    const groups = groupChoices([choice("a"), choice("b")]);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.[0]).toBeNull();
  });
});

describe("層數的對象自動修正", () => {
  it("後端的 effect_fixes 把疊在敵人身上的層數改成敵方", () => {
    const draft = { effects: [{ type: "add_stack", stack: "hoarfrost", amount: 1, affects: "self" }] } as unknown as Json;
    const options = {
      steps: [],
      problems: [],
      next_step: null,
      effect_fixes: [{ index: 0, value: "enemies", reason_zh: "「寒霜」疊在敵人身上，對象自動決定" }],
    };
    const next = conformAffects(draft, options as never) as { effects: { affects: string }[] };
    expect(next.effects[0]?.affects).toBe("enemies");
  });
});
