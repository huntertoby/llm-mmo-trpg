// CR-1c（05 5.4.2 第 8 點）：一輪中的主角面板也顯示暴擊傷害，「▸ 詳細」列來源；用字和戰鬥中的單位卡相同。
// 倍率與來源由後端算（`HeroOut.crit_damage_permille`、`crit_damage_detail_zh`），前端只排版。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero } from "../api/types";
import { baseAttributes } from "./flow";
import { RunHeroPanel } from "./RunHeroPanel";

function hero(extra: Partial<RunHero>): RunHero {
  return {
    name_zh: "測試",
    level: 1,
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
    attributes: baseAttributes(10),
    skills: [],
    ...extra,
  } as unknown as RunHero;
}

const render = (h: RunHero) => renderToStaticMarkup(createElement(RunHeroPanel, { hero: h }));

describe("主角面板的暴擊傷害", () => {
  const cases: [string, number, string][] = [
    ["沒截到", 2600, "武器「戰斧」200%・詞條 +10%・種族 +25%・修正技「暴擊專精」+25%（全身上限 300%）"],
    ["頂到上限", 3000, "武器「戰斧」250%・修正技「暴擊專精」+100%・頂到上限 300%"],
    ["最低", 1500, "武器「戰斧」150%・種族 -30%・最低 150%"],
  ];
  for (const [label, permille, detail] of cases) {
    it(`${label}：數值區寫最後倍率，「▸ 詳細」的暴擊傷害列寫來源`, () => {
      const html = render(hero({ crit_damage_permille: permille, crit_damage_detail_zh: detail }));
      expect(html).toContain(`data-testid="run-crit-damage">暴擊傷害 ${permille / 10}%<`);
      expect(html).toMatch(/<details class="unit-details" data-testid="run-crit-details"><summary>詳細<\/summary>/);
      expect(html).toContain("<th>暴擊傷害</th>");
      expect(html).toContain(detail);
    });
  }

  it("200% 也顯示", () => {
    const html = render(hero({ crit_damage_permille: 2000, crit_damage_detail_zh: "武器「火焰法杖」200%（全身上限 300%）" }));
    expect(html).toContain("暴擊傷害 200%");
  });

  it("舊回應沒有欄位時整格不畫", () => {
    const html = render(hero({}));
    expect(html).not.toContain("run-crit-damage");
    expect(html).not.toContain("run-crit-details");
  });
});
