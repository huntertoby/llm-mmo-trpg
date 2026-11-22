// KD-1 第 8 項（E5 美術小修）：沒有套用到這招的裝備變形，寫在說明卡內文最後的灰字。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { SkillCard } from "../api/types";
import { skillButtons } from "../battle/targeting";
import { unit } from "../battle/testFixtures";
import cards from "./fixtures/skillCards.json";
import { SkillCardView } from "./SkillCardView";

const card = cards.skill_gale_kick as unknown as SkillCard;

describe("說明卡最後的灰字", () => {
  it("有 notes 時排在內文最後，沒有時不畫", () => {
    const html = renderToStaticMarkup(createElement(SkillCardView, { card, compact: true, notes: ["彈射不會套用到這招"] }));
    expect(html).toContain('class="small skill-card-left-out"');
    expect(html).toContain("彈射不會套用到這招");
    expect(html.indexOf("skill-card-left-out")).toBeLessThan(html.indexOf("skill-card-detail"));
    expect(renderToStaticMarkup(createElement(SkillCardView, { card, compact: true }))).not.toContain("skill-card-left-out");
  });

  it("技能列按鈕帶著伺服器給的灰字", () => {
    const hero = unit("unit_0001", "ally", 1, 1, {
      skills: ["skill_gale_kick"],
      skill_notes_zh: { skill_gale_kick: ["彈射不會套用到這招"] },
    });
    const [b] = skillButtons(hero, [], {});
    expect(b?.reshapeNotes).toEqual(["彈射不會套用到這招"]);
    const [plain] = skillButtons(unit("unit_0001", "ally", 1, 1, { skills: ["skill_gale_kick"] }), [], {});
    expect(plain?.reshapeNotes).toEqual([]);
  });
});
