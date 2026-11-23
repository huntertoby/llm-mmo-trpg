// CR-1c（美術 CR-1b 驗收小修 1）：「名稱＋數字」是一個單位，換行時整個一起移到下一行。
// 用「・」「、」全形空白切段，每段 inline-block（不是 nowrap）；套用在預覽面板與暴擊來源文字。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero } from "../api/types";
import { unit } from "../battle/testFixtures";
import type { UnitNames } from "../battle/units";
import { baseAttributes } from "../run/flow";
import { RunHeroPanel } from "../run/RunHeroPanel";
import { PreviewBox } from "./ActionPanel";
import { UnitInfo } from "./UnitInfo";
import { WrapUnits, wrapUnitParts } from "./WrapUnits";

const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const css = readFileSync("src/styles/battle-hud.css", "utf-8");
const names = { name: (id: string) => id, label: (id: string) => id, marker: () => "A" } as unknown as UnitNames;
const DETAIL = "武器「匕首」250%・詞條 +10%・種族 +25%（全身上限 300%）";

/** 每個 wrap-unit 段的字。 */
function units(html: string): string[] {
  return [...html.matchAll(/<span class="wrap-unit">([^<]*)<\/span>/g)].map((m) => m[1] ?? "");
}

describe("名稱＋數字不拆開", () => {
  it("用「・」「、」全形空白切段，分隔符留在前一段尾巴，接起來是原字", () => {
    expect(wrapUnitParts("命中 95%　暴擊率 15%　傷害 52–146")).toEqual(["命中 95%　", "暴擊率 15%　", "傷害 52–146"]);
    expect(wrapUnitParts("擲出 19–20 暴擊・暴擊傷害 260%")).toEqual(["擲出 19–20 暴擊・", "暴擊傷害 260%"]);
    expect(wrapUnitParts("命中 +1、暴擊範圍 +1")).toEqual(["命中 +1、", "暴擊範圍 +1"]);
    expect(wrapUnitParts(DETAIL).join("")).toBe(DETAIL);
    expect(wrapUnitParts("暴擊傷害 260%")).toEqual(["暴擊傷害 260%"]);
  });

  it("每個單位是一個 inline-block 的段：「暴擊傷害 260%」「詞條 +10%」「傷害 52–146」都不被拆開", () => {
    const head = renderToStaticMarkup(createElement(WrapUnits, { text: "命中 95%　暴擊率 15%　傷害 52–146" }));
    expect(units(head)).toContain("傷害 52–146");
    const crit = renderToStaticMarkup(createElement(WrapUnits, { text: "擲出 19–20 暴擊・暴擊傷害 260%" }));
    expect(units(crit)).toContain("暴擊傷害 260%");
    const detail = renderToStaticMarkup(createElement(WrapUnits, { text: DETAIL }));
    expect(units(detail)).toContain("詞條 +10%・");
  });

  it("QF-5：全形「（」前面切段（括號整段一起移），「，」後面切段（「，」留前段尾巴）", () => {
    // 美術 CR-1c 驗收小修 1 列的三處 800 寬斷在詞中間
    expect(wrapUnitParts("傷害 55–288（期望 69.3）")).toEqual(["傷害 55–288", "（期望 69.3）"]);
    expect(wrapUnitParts("武器「匕首」250%・詞條 +10%（全身上限 300%）")).toEqual(["武器「匕首」250%・", "詞條 +10%", "（全身上限 300%）"]);
    expect(wrapUnitParts("另有看目標的加成，攻擊預覽時才算")).toEqual(["另有看目標的加成，", "攻擊預覽時才算"]);
    // 開頭就是「（」不會多出空段；接起來仍是原字
    expect(wrapUnitParts("（期望 69.3）")).toEqual(["（期望 69.3）"]);
    expect(wrapUnitParts(DETAIL).join("")).toBe(DETAIL);
  });

  it("QF-5 接線：預覽「（期望 69.3）」、單位卡「（全身上限 300%）」與提示行「攻擊預覽時才算」各是完整的一段", () => {
    const content = { lines: ["傷害 55–288（期望 69.3）"], chain: null, hasChain: false, noTurn: new Map() };
    const preview = units(renderToStaticMarkup(createElement(PreviewBox, { content, practice: false })));
    expect(preview).toEqual(["傷害 55–288", "（期望 69.3）"]);
    const u = unit("unit_0001", "ally", 1, 1, {
      crit_damage_permille: 2850,
      crit_damage_detail_zh: DETAIL,
      crit_damage_hint_zh: "另有看目標的加成，攻擊預覽時才算",
    });
    const card = units(renderToStaticMarkup(createElement(UnitInfo, { unit: u, names, heroId: "unit_0001", skills: {} })));
    expect(card).toEqual(expect.arrayContaining(["種族 +25%", "（全身上限 300%）", "另有看目標的加成，", "攻擊預覽時才算"]));
  });

  it("CSS 用 inline-block，不用 nowrap（一段比一行長時段內還能斷）", () => {
    const rule = /\.wrap-unit\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toContain("display: inline-block");
    expect(rule).not.toContain("nowrap");
  });

  it("接線：預覽面板的每一行（實戰；測試模式的非總覽行）", () => {
    const lines = ["命中 95%　暴擊率 15%　傷害 52–146", "擲出 19–20 暴擊・暴擊傷害 260%"];
    const content = { lines, chain: null, hasChain: false, noTurn: new Map() };
    const html = renderToStaticMarkup(createElement(PreviewBox, { content, practice: false }));
    expect(units(html)).toEqual(expect.arrayContaining(["傷害 52–146", "暴擊傷害 260%"]));
    const practice = renderToStaticMarkup(createElement(PreviewBox, { content, practice: true }));
    expect(units(practice)).toContain("暴擊傷害 260%");
  });

  it("接線：單位卡與主角面板的暴擊來源", () => {
    const u = unit("unit_0001", "ally", 1, 1, { crit_damage_permille: 2850, crit_damage_detail_zh: DETAIL });
    const card = renderToStaticMarkup(createElement(UnitInfo, { unit: u, names, heroId: "unit_0001", skills: {} }));
    expect(units(card)).toContain("詞條 +10%・");
    const hero = {
      name_zh: "測試",
      level: 1,
      xp: 0,
      xp_next: 100,
      hp: 1,
      max_hp: 1,
      mana: 1,
      max_mana: 1,
      source: 0,
      source_max: 3,
      hp_per_con_point: 3,
      hp_con_base: 10,
      attributes: baseAttributes(10),
      skills: [],
      crit_damage_permille: 2850,
      crit_damage_detail_zh: DETAIL,
    } as unknown as RunHero;
    expect(units(renderToStaticMarkup(createElement(RunHeroPanel, { hero })))).toContain("詞條 +10%・");
  });
});
