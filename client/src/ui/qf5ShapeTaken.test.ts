// QF-5（佇列 (o)，08 8.29 E5 第 7 點）：同一招有兩個以上裝備給的變形時，一招只套一種；沒生效的那個在技能卡註明
// 「已有其他變形」。生效的是哪一個以後端算的為準（`UnitView.skill_notes_zh`，KD-1 第 8 項已傳出），前端只照著畫。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { SkillCard } from "../api/types";
import { skillButtons } from "../battle/targeting";
import { unit } from "../battle/testFixtures";
import cards from "./fixtures/skillCards.json";
import { SkillCardView } from "./SkillCardView";

const card = cards.skill_gale_kick as unknown as SkillCard;
const TAKEN = "已有其他變形，彈射護腕的二段彈射不會套用";

function cardFor(notes: Record<string, string[]> | undefined): string {
  const hero = unit("unit_0001", "ally", 1, 1, { skills: ["skill_gale_kick"], skill_notes_zh: notes ?? null });
  const [b] = skillButtons(hero, [], {});
  return renderToStaticMarkup(createElement(SkillCardView, { card, compact: true, notes: b?.reshapeNotes ?? [] }));
}

describe("一招只套一種變形：技能卡的「已有其他變形」", () => {
  it("兩個變形：後端給的灰字畫在技能卡內文最後", () => {
    const html = cardFor({ skill_gale_kick: [TAKEN] });
    expect(html).toContain('class="small skill-card-left-out"');
    expect(html).toContain(TAKEN);
  });

  it("只有一個變形：後端不給灰字，技能卡沒有「已有其他變形」", () => {
    expect(cardFor(undefined)).not.toContain("已有其他變形");
    expect(cardFor(undefined)).not.toContain("skill-card-left-out");
  });

  it("前端不自己判斷：別招的灰字不會畫到這招", () => {
    expect(cardFor({ skill_palm_strike: [TAKEN] })).not.toContain("已有其他變形");
  });
});
