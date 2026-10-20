// 體質旁的「＋N HP」預覽（Phase 3-7）：純函式與實際渲染出的文字。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero } from "../api/types";
import { AttributeAllocator } from "./AttributeAllocator";
import { RunHeroPanel } from "./RunHeroPanel";
import { baseAttributes, conHpBonus, conHpGain, hpDeltaText } from "./flow";

describe("conHpGain / conHpBonus / hpDeltaText", () => {
  it("每點體質 3 HP", () => {
    expect(conHpGain({ con: 2, str: 1 }, 3)).toBe(6);
    expect(conHpGain({ str: 4 }, 3)).toBe(0);
  });

  it("體質相對基準的加成可以是負的", () => {
    expect(conHpBonus(14, 10, 3)).toBe(12);
    expect(conHpBonus(8, 10, 3)).toBe(-6);
    expect(conHpBonus(10, 10, 3)).toBe(0);
  });

  it("文字：正負號與零", () => {
    expect(hpDeltaText(6)).toBe("＋6 HP");
    expect(hpDeltaText(-6)).toBe("−6 HP");
    expect(hpDeltaText(0)).toBe("");
  });
});

describe("配點時的 HP 預覽", () => {
  const base = baseAttributes(10);
  const render = (alloc: Record<string, number>) =>
    renderToStaticMarkup(
      createElement(AttributeAllocator, { base, points: 4, alloc, onChange: () => undefined, hpPerCon: 3 }),
    );

  it("體質配點後即時顯示最大 HP 增量", () => {
    expect(render({ con: 2 })).toContain("最大 HP ＋6 HP");
  });

  it("沒配體質時不顯示", () => {
    expect(render({ str: 2 })).not.toContain("con-hp-preview");
  });

  it("沒給 hpPerCon 時不顯示（舊呼叫方式）", () => {
    const html = renderToStaticMarkup(
      createElement(AttributeAllocator, { base, points: 4, alloc: { con: 2 }, onChange: () => undefined }),
    );
    expect(html).not.toContain("con-hp-preview");
  });
});

describe("主角面板", () => {
  it("體質旁顯示目前的 HP 加成", () => {
    const hero = {
      name_zh: "測試",
      level: 3,
      xp: 0,
      xp_next: 100,
      hp: 50,
      max_hp: 60,
      mana: 1,
      max_mana: 1,
      source: 0,
      source_max: 3,
      hp_per_con_point: 3,
      hp_con_base: 10,
      attributes: { ...baseAttributes(10), con: 14 },
      skills: [],
    } as unknown as RunHero;
    expect(renderToStaticMarkup(createElement(RunHeroPanel, { hero }))).toContain("＋12 HP");
  });
});
