// RR-2（#160，06 6.34.3「強度下限」例外）：被強度下限卡住的重閃格不標灰，掛提醒；按下去先確認；出題後固定區換句、每張卡加「比原本弱」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero, RunResponse } from "../api/types";
import { RunFlashPending } from "../screens/RunFlashPending";
import { ReflashSection, ReflashWeakerConfirm } from "./CampfireSkillCare";
import { FLASH_MUST_PICK_ZH } from "./flashChoice";
import { mustPickText, REFLASH_WEAKER_BACK_ZH, REFLASH_WEAKER_GO_ZH, weakerSlot } from "./reflashWeaker";
import campfire from "./fixtures/run_campfire.json";
import pendingFlash from "./fixtures/run_pending_flash.json";

const CAMPFIRE = campfire as unknown as RunResponse;
const PENDING = pendingFlash as unknown as RunResponse;
const noop = async () => null;
const WARN = "這一格重閃可能比原本弱";
const CONFIRM = "這一格原本的變化特別強，這次重閃出的選項都會比原本弱。扣點後一定要選一個。還要重閃嗎？";
const FOOT = "這次的選項都比原本弱，標 ▼ 的是變弱的地方。";
const TAG = "比原本弱";

function withSlot1Weaker(hero: RunHero): { hero: RunHero; skill: string } {
  const flashed = (hero.flash ?? []).find((f) => f.records.length === 3);
  if (flashed === undefined) throw new Error("夾具缺少已閃過的技能");
  const slots = flashed.reflash_slots.map((s) =>
    s.slot === 1 ? { ...s, available: true, problem_zh: null, weaker: true, weaker_zh: WARN, weaker_confirm_zh: CONFIRM } : { ...s, available: true, problem_zh: null },
  );
  const flash = (hero.flash ?? []).map((f) => (f.skill_id === flashed.skill_id ? { ...f, reflash_slots: slots } : f));
  return { hero: { ...hero, flash, insight: 99 }, skill: flashed.skill_id };
}

describe("RR-2 被強度下限卡住的重閃格", () => {
  it("weakerSlot：只有伺服器標 weaker 的格子有提醒與確認句；舊資料沒有欄位照常", () => {
    const { hero } = withSlot1Weaker(CAMPFIRE.hero);
    const flashed = (hero.flash ?? []).find((f) => f.records.length === 3);
    expect(weakerSlot(flashed, 1)).toEqual({ warn: WARN, confirm: CONFIRM });
    expect(weakerSlot(flashed, 2)).toBeNull();
    const legacy = (CAMPFIRE.hero.flash ?? []).find((f) => f.records.length === 3);
    expect(weakerSlot(legacy, 1)).toBeNull();
  });

  it("入口不標灰、掛變弱樣式的提醒字；其他格沒有", () => {
    const { hero, skill } = withSlot1Weaker(CAMPFIRE.hero);
    const html = renderToStaticMarkup(createElement(ReflashSection, { runId: "r", hero, busy: false, onChoose: noop }));
    const button = (slot: number) => {
      const found = html.match(new RegExp(`<button[^>]*data-testid="reflash-${skill}-${slot}"[^>]*>`));
      if (found === null) throw new Error(`找不到第 ${slot} 格的按鈕`);
      return found[0];
    };
    expect(button(1)).not.toContain("disabled");
    expect(button(1)).toContain('data-reflash-weaker="1"');
    expect(button(2)).not.toContain("data-reflash-weaker");
    expect(html).toContain(`data-testid="reflash-weaker-${skill}-1"`);
    expect(html).toContain(WARN);
    expect(html).toMatch(/class="reflash-weaker-note"[^>]*><i class="fc-down" aria-label="變弱"><\/i>/);
    expect(html).not.toContain(`data-testid="reflash-weaker-${skill}-2"`);
    // 還沒按之前沒有確認框
    expect(html).not.toContain("reflash-weaker-confirm");
  });

  it("確認框：伺服器的確認句＋「重閃」「先不要」", () => {
    const html = renderToStaticMarkup(createElement(ReflashWeakerConfirm, { text: CONFIRM, busy: false, onGo: () => {}, onBack: () => {} }));
    expect(html).toContain('role="alertdialog"');
    expect(html).toContain(CONFIRM);
    expect(html).toContain(`data-testid="reflash-weaker-go">${REFLASH_WEAKER_GO_ZH}</button>`);
    expect(html).toContain(`data-testid="reflash-weaker-back">${REFLASH_WEAKER_BACK_ZH}</button>`);
    expect([REFLASH_WEAKER_GO_ZH, REFLASH_WEAKER_BACK_ZH]).toEqual(["重閃", "先不要"]);
  });

  it("出題後：固定區那句換成伺服器的句子，每張卡類別標籤旁加「比原本弱」", () => {
    const pending = PENDING.pending_flash;
    if (pending === null || pending === undefined) throw new Error("夾具缺少待選閃現");
    expect(mustPickText(pending)).toBe(FLASH_MUST_PICK_ZH);
    const weak = { ...pending, weaker_foot_zh: FOOT, options: pending.options.map((o) => ({ ...o, weaker_tag_zh: TAG })) };
    expect(mustPickText(weak)).toBe("一定要選一個。這次的選項都比原本弱，標 ▼ 的是變弱的地方");
    const html = renderToStaticMarkup(createElement(RunFlashPending, { run: { ...PENDING, pending_flash: weak }, busy: false, onChoose: noop }));
    expect(html).toContain("一定要選一個。這次的選項都比原本弱，標 ▼ 的是變弱的地方");
    expect(html).not.toContain("選哪個這招整體都會強一點");
    expect(html.match(/data-testid="flash-option-weaker"/g)?.length).toBe(weak.options.length);
    expect(html).toMatch(/class="fc-weaker"[^>]*><i class="fc-down" aria-label="變弱"><\/i>比原本弱/);
    // 一般出題：沒有小標，原句照舊
    const plain = renderToStaticMarkup(createElement(RunFlashPending, { run: PENDING, busy: false, onChoose: noop }));
    expect(plain).not.toContain("flash-option-weaker");
    expect(plain).toContain(FLASH_MUST_PICK_ZH);
  });
});
