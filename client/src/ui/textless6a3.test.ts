// Phase 6A-3（去文字化④）：HP／法力／護盾說明句、釘選小卡精簡版、戰鬥紀錄浮動提示與釘選、操作說明句只出現前 3 次。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { smallView, unit } from "../battle/testFixtures";
import type { UnitNames } from "../battle/units";
import { Hud } from "./Hud";
import { UnitInfo } from "./UnitInfo";
import { barData, pinnedCompact, PIN_COMPACT_WIDTH, RESOURCE_TEXT, unitChips } from "./statusCard";

const names: UnitNames = { name: (id) => id, marker: (id) => id.slice(-1) } as UnitNames;

const hero = unit("unit_0001", "ally", 0, 2, {
  name_zh: "主角",
  hp: 41,
  max_hp: 50,
  shield: 5,
  mana: 18,
  max_mana: 30,
  stamina: 6,
  max_stamina: 8,
});
const foe = unit("unit_0002", "enemy", 1, 1, {
  name_zh: "斷崖幫刀手",
  hp: 30,
  max_hp: 42,
  stamina: 6,
  max_stamina: 8,
  mana: 4,
  max_mana: 10,
  shield: 3,
  weapon_name_zh: "鬼頭刀",
  tags: ["elite"],
  traits_zh: ["精英詞綴「狂暴」：HP 低於一半時傷害 +2。"],
});

describe("HP、法力、護盾的說明句（玩法 PM 給的文字，一字不改）", () => {
  it("三句原文", () => {
    expect(RESOURCE_TEXT.hp).toBe("生命值，歸零就會倒下；靠治療、藥水或營火回復。");
    expect(RESOURCE_TEXT.mana).toBe("施放法術要花法力，戰鬥中不會自然回復；在營火或城鎮回滿。");
    expect(RESOURCE_TEXT.shield).toBe("受到傷害時先扣護盾、再扣生命值；時間到就消失，重複獲得只保留較大的一層。");
  });
  it("主角卡：HP 條（有護盾時加護盾句）、法力條", () => {
    expect(barData("hp", hero).hint.split("\n")).toEqual(["HP 41 / 50", RESOURCE_TEXT.hp, "護盾 5", RESOURCE_TEXT.shield]);
    expect(barData("hp", { ...hero, shield: 0 }).hint.split("\n")).toEqual(["HP 41 / 50", RESOURCE_TEXT.hp]);
    expect(barData("mana", hero).hint.split("\n")).toEqual(["法力 18 / 30", RESOURCE_TEXT.mana]);
    const html = renderToStaticMarkup(createElement(Hud, { view: { ...smallView(), units: [hero] }, hero, skills: {} }));
    expect(html).toContain('aria-label="HP 41 / 50"');
  });
  it("單位小卡共用同一份文字：HP 條、護盾與法力圖示", () => {
    expect(barData("hp", foe).hint).toContain(RESOURCE_TEXT.hp);
    const chips = unitChips(foe);
    expect(chips.find((c) => c.key === "shield")?.hint).toBe(`護盾 3\n${RESOURCE_TEXT.shield}`);
    expect(chips.find((c) => c.key === "mana")?.hint).toBe(`法力 4 / 10\n${RESOURCE_TEXT.mana}`);
  });
});

describe("釘選小卡：視窗不到 1000 寬收成精簡版", () => {
  it("門檻 1000；滑過（展開）時不收", () => {
    expect(PIN_COMPACT_WIDTH).toBe(1000);
    expect(pinnedCompact(800, false)).toBe(true);
    expect(pinnedCompact(999, false)).toBe(true);
    expect(pinnedCompact(1000, false)).toBe(false);
    expect(pinnedCompact(1600, false)).toBe(false);
    expect(pinnedCompact(800, true)).toBe(false);
  });
  const props = { unit: foe, names, heroId: "unit_0001", skills: {}, view: { ...smallView(), units: [hero, foe] }, pinned: true, onTogglePin: () => {} };
  it("精簡版只留名稱、HP 條、耐力條（與圖釘）", () => {
    const html = renderToStaticMarkup(createElement(UnitInfo, { ...props, compact: true }));
    expect(html).toContain("斷崖幫刀手");
    expect([...html.matchAll(/class="stat-bar (\w+)"/g)].map((m) => m[1])).toEqual(["hp", "stamina"]);
    expect(html).toContain("unit-pin");
    expect(html).not.toContain("hud-icons");
    expect(html).not.toContain("unit-details");
    expect(html).not.toContain("affix-badge");
    expect(html).not.toContain("鬼頭刀");
  });
  it("完整版照舊有圖示、詞綴徽章與「詳細」", () => {
    const html = renderToStaticMarkup(createElement(UnitInfo, { ...props, compact: false }));
    expect(html).toContain("hud-icons");
    expect(html).toContain("unit-details");
    expect(html).toContain("affix-badge");
  });
});
