// CR-1b（05 5.4.2 第 8 點，佇列 (v)）：角色面板的暴擊傷害。倍率與來源由後端算，前端只排版。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { unit } from "../battle/testFixtures";
import { critDamageDetail, critDamageText } from "../battle/critDamage";
import { detailRows, UnitInfo } from "./UnitInfo";
import type { UnitNames } from "../battle/units";

const names = { name: (id: string) => id, label: (id: string) => id, marker: () => "A" } as unknown as UnitNames;

describe("角色面板的暴擊傷害", () => {
  it("200% 也顯示；小數照寫", () => {
    expect(critDamageText({ crit_damage_permille: 2000 })).toBe("暴擊傷害 200%");
    expect(critDamageText({ crit_damage_permille: 2125 })).toBe("暴擊傷害 212.5%");
  });

  it("看不到資訊（後端送 null）時不畫", () => {
    expect(critDamageText({ crit_damage_permille: null })).toBeNull();
    expect(critDamageText({})).toBeNull();
    expect(critDamageDetail({ crit_damage_detail_zh: null })).toBeNull();
  });

  const cases: [string, number, string][] = [
    ["沒截到", 2600, "武器「戰斧」200%・詞條 +10%・種族 +25%・修正技「暴擊專精」+25%（全身上限 300%）"],
    ["頂到上限", 3000, "武器「戰斧」250%・修正技「暴擊專精」+100%・頂到上限 300%"],
    ["最低", 1500, "武器「戰斧」150%・種族 -30%・最低 150%"],
  ];
  for (const [label, permille, detail] of cases) {
    it(`${label}：數值區寫最後倍率，「▸ 詳細」列來源`, () => {
      const u = unit("unit_0001", "ally", 1, 1, { crit_damage_permille: permille, crit_damage_detail_zh: detail });
      const html = renderToStaticMarkup(createElement(UnitInfo, { unit: u, names, heroId: "unit_0001", skills: {} }));
      expect(html).toContain(`data-testid="unit-crit-damage">暴擊傷害 ${permille / 10}%<`);
      const row = detailRows(u, names).find(([k]) => k === "暴擊傷害");
      expect(renderToStaticMarkup(createElement("td", null, row?.[1]))).toBe(`<td>${detail}</td>`);
      expect(html).toContain(detail);
    });
  }

  it("沒有欄位時（舊回應）整格不畫，詳細也不列", () => {
    const u = unit("unit_0002", "enemy", 1, 1);
    const html = renderToStaticMarkup(createElement(UnitInfo, { unit: u, names, heroId: "unit_0001", skills: {} }));
    expect(html).not.toContain("unit-crit-damage");
    expect(detailRows(u, names).some(([k]) => k === "暴擊傷害")).toBe(false);
  });
});
