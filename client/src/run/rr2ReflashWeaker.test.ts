// RR-2（#160，06 6.34.3「強度下限」例外）：被強度下限卡住的重閃格不標灰，掛提醒；出題後固定區換句。
// RR-2b：兩層確認合成一層（選類別面板最上面再寫一次提醒，不另跳確認框）；「比原本弱」小標撤掉。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FlashPreview, RunHero, RunResponse } from "../api/types";
import { RunFlashPending } from "../screens/RunFlashPending";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";
import { ReflashSection } from "./CampfireSkillCare";
import { FlashChooserView } from "./FlashChooser";
import { FLASH_MUST_PICK_ZH } from "./flashChoice";
import { mustPickText, weakerLeadText, weakerSlot } from "./reflashWeaker";
import campfire from "./fixtures/run_campfire.json";
import pendingFlash from "./fixtures/run_pending_flash.json";

const CAMPFIRE = campfire as unknown as RunResponse;
const PENDING = pendingFlash as unknown as RunResponse;
const noop = async () => null;
// 字照伺服器（`flash_offer.REFLASH_WEAKER_ZH`／`REFLASH_WEAKER_PICK_ZH`／`WEAKER_FOOT_ZH`）
const WARN = "這一格原本的變化特別強，重閃後這部分會變弱";
const PICK = "整招不會比現在弱；扣點後一定要選一個。";
const FOOT = "被換掉的部分會變弱，整招不會比現在弱；標 ▼ 的是變小的地方。";

function withSlot1Weaker(hero: RunHero): { hero: RunHero; skill: string } {
  const flashed = (hero.flash ?? []).find((f) => f.records.length === 3);
  if (flashed === undefined) throw new Error("夾具缺少已閃過的技能");
  const slots = flashed.reflash_slots.map((s) =>
    s.slot === 1 ? { ...s, available: true, problem_zh: null, weaker: true, weaker_zh: WARN, weaker_pick_zh: PICK } : { ...s, available: true, problem_zh: null },
  );
  const flash = (hero.flash ?? []).map((f) => (f.skill_id === flashed.skill_id ? { ...f, reflash_slots: slots } : f));
  return { hero: { ...hero, flash, insight: 99 }, skill: flashed.skill_id };
}

const PREVIEW: FlashPreview = {
  skill_id: "s",
  slot: 1,
  nth: 1,
  major: false,
  problem_zh: null,
  open_cost: 1,
  focused_cost: 2,
  categories: [{ id: "combo", name_zh: "連段", count: 2 }],
};

function chooser(weaker: ReturnType<typeof weakerSlot>): string {
  return renderToStaticMarkup(
    createElement(FlashChooserView, {
      hero: { ...CAMPFIRE.hero, insight: 8 },
      skillId: "s",
      skillName: "測試技",
      slot: 1,
      slotLabel: "第 1 次",
      weaker,
      busy: false,
      onChoose: noop,
      onCancel: () => undefined,
      preview: PREVIEW,
      loadError: null,
    }),
  );
}

describe("RR-2／RR-2b 被強度下限卡住的重閃格", () => {
  it("weakerSlot：只有伺服器標 weaker 的格子有提醒與選類別那句；舊資料沒有欄位照常", () => {
    const { hero } = withSlot1Weaker(CAMPFIRE.hero);
    const flashed = (hero.flash ?? []).find((f) => f.records.length === 3);
    expect(weakerSlot(flashed, 1)).toEqual({ warn: WARN, pick: PICK });
    expect(weakerSlot(flashed, 2)).toBeNull();
    const legacy = (CAMPFIRE.hero.flash ?? []).find((f) => f.records.length === 3);
    expect(weakerSlot(legacy, 1)).toBeNull();
    expect(weakerLeadText({ warn: WARN, pick: PICK })).toBe(`${WARN}。${PICK}`);
  });

  it("入口不標灰、掛變弱樣式的提醒字；其他格沒有；沒有確認框", () => {
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
    // RR-2b：兩層合成一層，原始碼裡不再有確認框
    const src = stripTsComments(readFile(SRC_DIR, "run/CampfireSkillCare.tsx"));
    expect(src).not.toContain("ReflashWeakerConfirm");
    expect(src).not.toContain("reflash-weaker-confirm");
  });

  it("選類別面板：較弱的格子最上面多一行提醒（在扣點說明之前）；一般格子沒有", () => {
    const html = chooser({ warn: WARN, pick: PICK });
    expect(html).toMatch(/data-testid="flash-weaker-lead"><i class="fc-down" aria-label="變弱"><\/i><span>這一格原本的變化特別強，重閃後這部分會變弱。整招不會比現在弱；扣點後一定要選一個。<\/span>/);
    expect(html.indexOf("flash-weaker-lead")).toBeLessThan(html.indexOf("flash-warning"));
    // 扣點仍在這一層的確定鍵；「先不要」關掉面板就不重閃
    expect(html).toContain('data-testid="flash-confirm"');
    expect(html).toContain("先不要");
    expect(chooser(null)).not.toContain("flash-weaker-lead");
  });

  it("出題後：固定區那句換成伺服器的句子；選項卡沒有「比原本弱」小標", () => {
    const pending = PENDING.pending_flash;
    if (pending === null || pending === undefined) throw new Error("夾具缺少待選閃現");
    expect(mustPickText(pending)).toBe(FLASH_MUST_PICK_ZH);
    const weak = { ...pending, weaker_foot_zh: FOOT };
    const sentence = "一定要選一個。被換掉的部分會變弱，整招不會比現在弱；標 ▼ 的是變小的地方";
    expect(mustPickText(weak)).toBe(sentence);
    const html = renderToStaticMarkup(createElement(RunFlashPending, { run: { ...PENDING, pending_flash: weak }, busy: false, onChoose: noop }));
    expect(html).toContain(sentence);
    expect(html).not.toContain("選哪個這招整體都會強一點");
    expect(html).not.toContain("fc-weaker");
    expect(html).not.toContain("比原本弱");
    const plain = renderToStaticMarkup(createElement(RunFlashPending, { run: PENDING, busy: false, onChoose: noop }));
    expect(plain).toContain(FLASH_MUST_PICK_ZH);
  });
});
