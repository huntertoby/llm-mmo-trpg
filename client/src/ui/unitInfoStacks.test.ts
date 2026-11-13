// KW-3 待決 3（美術 PM 2026-11-13，docs/art/RG-4驗收.md「KW-3 待決 3」）：單位資訊卡的層數——
// 連擊、怒氣、專注、氣用和 HUD 同尺寸的計量 StackPips（不做縮小版），其他層數照舊 StackBadge；0 層照現行不顯示。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { smallView, unit } from "../battle/testFixtures";
import { unitNames } from "../battle/units";
import { UnitInfo } from "./UnitInfo";

const render = (stacks: Record<string, number>, heroId = "unit_0001", skills: string[] = []): string => {
  const u = unit("unit_0002", "enemy", 1, 1, { stacks, skills });
  const view = { ...smallView(), units: [u] };
  return renderToStaticMarkup(createElement(UnitInfo, { unit: u, names: unitNames(view), heroId, skills: {}, view }));
};

describe("單位資訊卡的層數", () => {
  it("四種計量層數畫成 StackPips（和 HUD 同一張畫布、同尺寸），其他層數照舊 StackBadge", () => {
    const html = render({ combo_point: 3, fury: 4, focus: 1, ki: 2, static_charge: 2 });
    expect(html).toMatch(/class="stack-pips" data-stack="combo_point" data-count="3"/);
    expect(html).toMatch(/class="stack-pips full" data-stack="fury" data-count="4"/);
    expect(html).toMatch(/data-stack="focus" data-count="1"/);
    expect(html).toMatch(/data-stack="ki" data-count="2"/);
    expect(html).not.toMatch(/stack-badge[^>]*data-stack="(combo_point|fury|focus|ki)"/);
    expect(html).toContain('data-stack="static_charge"');
    expect(html).not.toMatch(/stack-pips[^"]*" data-stack="static_charge"/);
    // 和 HUD 同尺寸：怒氣 4 格的畫布和 qIconKW3.test 的 HUD 斷言同一個寬高
    expect(html).toMatch(/<canvas width="136" height="60" style="width:68px;height:30px"/);
  });

  it("0 層照現行不顯示（看的是別人，不列空計量）", () => {
    const html = render({ combo_point: 0, fury: 0 }, "unit_0001", ["s_make"]);
    expect(html).not.toContain("stack-pips");
    expect(html).not.toContain('data-stack="combo_point"');
  });
});
