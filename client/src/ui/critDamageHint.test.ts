// CR-1c（05 5.4.2 第 8 點）：有「條件看目標」的暴擊傷害修正技時，「▸ 詳細」暴擊傷害列最後加一行
// 「另有看目標的加成，攻擊預覽時才算」；沒有時不出現。單位卡與主角面板都有。
// 看不到修正技名稱的陣營，後端不給這一行（`crit_damage_hint_zh` 為 null），前端也就不畫。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero } from "../api/types";
import { unit } from "../battle/testFixtures";
import type { UnitNames } from "../battle/units";
import { baseAttributes } from "../run/flow";
import { RunHeroPanel } from "../run/RunHeroPanel";
import { UnitInfo } from "./UnitInfo";

const HINT = "另有看目標的加成，攻擊預覽時才算";
const DETAIL = "武器「戰斧」200%・修正技「斬首」+25%（全身上限 300%）";
const names = { name: (id: string) => id, label: (id: string) => id, marker: () => "A" } as unknown as UnitNames;

function card(hint: string | null): string {
  const u = unit("unit_0001", "ally", 1, 1, {
    crit_damage_permille: 2250,
    crit_damage_detail_zh: DETAIL,
    crit_damage_hint_zh: hint,
  });
  return renderToStaticMarkup(createElement(UnitInfo, { unit: u, names, heroId: "unit_0001", skills: {} }));
}

function heroPanel(hint: string | null): string {
  const hero = {
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
    crit_damage_permille: 2250,
    crit_damage_detail_zh: DETAIL,
    crit_damage_hint_zh: hint,
  } as unknown as RunHero;
  return renderToStaticMarkup(createElement(RunHeroPanel, { hero }));
}

/** 提示行在來源之後（同一格的最後一行）。 */
function expectHintAfterDetail(html: string): void {
  expect(html).toContain(`data-testid="crit-damage-hint">${HINT}<`);
  const text = plain(html); // 來源切成 WrapUnits 段（CR-1c 小修 1），比字要先去掉標籤
  const at = text.indexOf(DETAIL);
  expect(at).toBeGreaterThanOrEqual(0);
  expect(text.indexOf(HINT)).toBe(at + DETAIL.length);
}

const plain = (html: string) => html.replace(/<[^>]+>/g, "");

describe("看目標的暴擊傷害加成提示", () => {
  it("單位卡：有這類修正技時，來源後面加一行提示", () => {
    expectHintAfterDetail(card(HINT));
  });

  it("單位卡：沒有時不出現（後端送 null）", () => {
    expect(card(null)).not.toContain("crit-damage-hint");
    expect(plain(card(null))).toContain(DETAIL);
  });

  it("主角面板：有這類修正技時，來源後面加一行提示", () => {
    expectHintAfterDetail(heroPanel(HINT));
  });

  it("主角面板：沒有時不出現", () => {
    expect(heroPanel(null)).not.toContain("crit-damage-hint");
    expect(plain(heroPanel(null))).toContain(DETAIL);
  });
});
