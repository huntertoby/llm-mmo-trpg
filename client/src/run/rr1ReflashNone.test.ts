// RR-1：出不了題的重閃格比照 FL-1c 標灰、不能按，灰字照伺服器的 problem_zh。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero, RunResponse } from "../api/types";
import { ReflashSection } from "./CampfireSkillCare";
import { NO_REFLASH_OPTIONS_TEXT, reflashSlots } from "./flash";
import campfire from "./fixtures/run_campfire.json";

const CAMPFIRE = campfire as unknown as RunResponse;
const noop = async () => null;

function withSlot1None(hero: RunHero): { hero: RunHero; skill: string } {
  const flashed = (hero.flash ?? []).find((f) => f.records.length === 3);
  if (flashed === undefined) throw new Error("夾具缺少已閃過的技能");
  const slots = flashed.reflash_slots.map((s) => (s.slot === 1 ? { ...s, available: false, problem_zh: NO_REFLASH_OPTIONS_TEXT } : { ...s, available: true, problem_zh: null }));
  const flash = (hero.flash ?? []).map((f) => (f.skill_id === flashed.skill_id ? { ...f, reflash_slots: slots } : f));
  return { hero: { ...hero, flash, insight: 99 }, skill: flashed.skill_id };
}

describe("RR-1 出不了題的重閃格", () => {
  it("reflashSlots：available false 的格子標 none，帶伺服器灰字；沒有欄位的舊資料照常可按", () => {
    const { hero } = withSlot1None(CAMPFIRE.hero);
    const flashed = (hero.flash ?? []).find((f) => f.records.length === 3);
    const slots = reflashSlots(flashed);
    expect(slots.map((s) => [s.slot, s.none, s.problem])).toEqual([
      [1, true, NO_REFLASH_OPTIONS_TEXT],
      [2, false, null],
      [3, false, null],
    ]);
    const legacy = (CAMPFIRE.hero.flash ?? []).find((f) => f.records.length === 3);
    expect(reflashSlots(legacy).every((s) => !s.none && s.problem === null)).toBe(true);
  });

  it("按鈕停用並顯示灰字；其他格照常可按", () => {
    const { hero, skill } = withSlot1None(CAMPFIRE.hero);
    const html = renderToStaticMarkup(createElement(ReflashSection, { runId: "r", hero, busy: false, onChoose: noop }));
    const button = (slot: number) => {
      const found = html.match(new RegExp(`<button[^>]*data-testid="reflash-${skill}-${slot}"[^>]*>`));
      if (found === null) throw new Error(`找不到第 ${slot} 格的按鈕`);
      return found[0];
    };
    expect(button(1)).toContain('disabled=""');
    expect(button(1)).toContain('data-reflash-none="1"');
    expect(button(2)).not.toContain("disabled");
    expect(html).toContain(`data-testid="reflash-none-${skill}-1"`);
    expect(html).toContain(NO_REFLASH_OPTIONS_TEXT);
    expect(html).not.toContain(`data-testid="reflash-none-${skill}-2"`);
  });
});
