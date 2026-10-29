// Phase 3W-6：閃現的純函式，以及閃現／營火／完整技能畫面的實際渲染（用真實的 API 回應存成的夾具）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FlashOption, FlashPreview, RunHero, RunResponse } from "../api/types";
import { RunCompleteOffer } from "../screens/RunCompleteOffer";
import { RunFlashPending } from "../screens/RunFlashPending";
import { SkillCardView } from "../ui/SkillCardView";
import { CampfireSkillCare } from "./CampfireSkillCare";
import { FlashChooserView } from "./FlashChooser";
import { FlashSection } from "./FlashSection";
import {
  carryable,
  categoryLabel,
  categorySelectable,
  costProblem,
  dissolveConfirm,
  flashChoice,
  flashCountText,
  flashWarning,
  focusedMode,
  inheritChoice,
  inheritTargets,
  maxCarry,
  openMode,
  optionTag,
  pickChoice,
  pickReady,
  recordLine,
  reflashSlots,
  showCanFlash,
  sortedOptions,
  toggleCarry,
} from "./flash";
import { runView } from "./flow";
import afterFlash from "./fixtures/run_after_flash.json";
import campfire from "./fixtures/run_campfire.json";
import completeOffer from "./fixtures/run_complete_offer.json";
import pendingFlash from "./fixtures/run_pending_flash.json";

const CAMPFIRE = campfire as unknown as RunResponse;
const PENDING = pendingFlash as unknown as RunResponse;
const AFTER = afterFlash as unknown as RunResponse;
const COMPLETE = completeOffer as unknown as RunResponse;
const noop = async () => null;

describe("價格與說明", () => {
  const rules = CAMPFIRE.hero.flash_rules;
  it("不指定 1 點出 4 個、指定類別 2 點出 3 個（數值來自後端規則）", () => {
    expect(openMode(rules)).toMatchObject({ cost: 1, options: 4, category: null });
    expect(focusedMode(rules, "combo")).toMatchObject({ cost: 2, options: 3, category: "combo" });
  });
  it("出題前說清楚會扣點、一定要選一個", () => {
    const text = flashWarning(openMode(rules));
    expect(text).toContain("扣 1 點");
    expect(text).toContain("一定要選 1 個");
    expect(flashWarning(focusedMode(rules, "x"))).toContain("扣 2 點");
  });
  it("點數不足時說明原因", () => {
    expect(costProblem(1, focusedMode(rules, "x"))).toContain("靈感點不足");
    expect(costProblem(2, focusedMode(rules, "x"))).toBeNull();
  });
  it("類別按鈕：數量寫在括號裡，0 個不能選", () => {
    expect(categoryLabel({ id: "combo", name_zh: "連段", count: 2 })).toBe("連段（2）");
    expect(categorySelectable({ id: "combo", name_zh: "連段", count: 0 })).toBe(false);
    expect(categorySelectable({ id: "combo", name_zh: "連段", count: 1 })).toBe(true);
  });
  it("閃現請求：閃現 slot 為空，重閃帶格子", () => {
    expect(flashChoice("s", null, null)).toEqual({ kind: "flash", skill: "s", slot: null, category: null });
    expect(flashChoice("s", 2, "area")).toEqual({ kind: "flash", skill: "s", slot: 2, category: "area" });
  });
});

describe("技能卡文字", () => {
  const flashes = CAMPFIRE.hero.flash;
  const fresh = flashes.find((f) => f.records.length === 0 && !f.complete && f.can_flash);
  const flashed = flashes.find((f) => f.records.length === 3);
  const complete = flashes.find((f) => f.complete);
  it("已閃 N／5 次；完整技能另寫", () => {
    expect(flashCountText(fresh, CAMPFIRE.hero.flash_rules)).toBe("已閃 0／5 次");
    expect(flashCountText(flashed, CAMPFIRE.hero.flash_rules)).toBe("已閃 3／5 次");
    expect(flashCountText(complete, CAMPFIRE.hero.flash_rules)).toContain("完整技能");
    expect(flashCountText(undefined, null)).toBe("");
  });
  it("可以閃現了：只在真的能閃時；完整技能不顯示", () => {
    expect(showCanFlash(fresh)).toBe(true);
    expect(showCanFlash(flashed)).toBe(false);
    expect(showCanFlash(complete)).toBe(false);
  });
  it("變化歷程一行一次，大變化另標", () => {
    const lines = (flashed?.records ?? []).map(recordLine);
    expect(lines).toHaveLength(3);
    expect(lines[0]).toMatch(/^第 1 次・/);
    expect(lines[2]).toMatch(/^第 3 次・大變化：/);
  });
  it("渲染：已閃次數、可以閃現了、變化歷程、稀有度提示", () => {
    const card = CAMPFIRE.hero.skills.find((s) => s.id === fresh?.skill_id) ?? CAMPFIRE.hero.skills[0];
    expect(card).toBeDefined();
    if (card === undefined) return;
    const html = renderToStaticMarkup(createElement(SkillCardView, { card, flash: fresh, flashRules: CAMPFIRE.hero.flash_rules }));
    expect(html).toContain("已閃 0／5 次");
    expect(html).toContain("可以閃現了");
    expect(html).toContain('data-testid="skill-card-rarity"');
    const flashedCard = CAMPFIRE.hero.skills.find((s) => s.id === flashed?.skill_id);
    if (flashedCard === undefined) throw new Error("夾具缺少已閃過的技能");
    const html2 = renderToStaticMarkup(createElement(SkillCardView, { card: flashedCard, flash: flashed, flashRules: CAMPFIRE.hero.flash_rules }));
    expect(html2).toContain("skill-flash-history");
    expect(html2).toContain("第 3 次・大變化");
    expect(html2).toContain("可以重閃第 3 格轉型");
  });
});

describe("重閃", () => {
  it("一般技能每個已閃的格子可以重閃；完整技能只有調整欄", () => {
    const flashed = CAMPFIRE.hero.flash.find((f) => f.records.length === 3);
    const slots = reflashSlots(flashed, CAMPFIRE.hero.flash_rules);
    expect(slots.map((s) => s.slot)).toEqual([1, 2, 3]);
    const complete = CAMPFIRE.hero.flash.find((f) => f.complete);
    expect(reflashSlots(complete, CAMPFIRE.hero.flash_rules)).toEqual([{ slot: 0, label: "調整欄", transformHint: false }]);
    expect(reflashSlots(undefined, null)).toEqual([]);
  });
  it("升階後第 3 格還不是轉型：只有第 3 格帶轉型提示", () => {
    const flashed = CAMPFIRE.hero.flash.find((f) => f.records.length === 3);
    expect(flashed?.reflash_transform_hint).toBe(true);
    const slots = reflashSlots(flashed, CAMPFIRE.hero.flash_rules);
    expect(slots.filter((s) => s.transformHint).map((s) => s.slot)).toEqual([3]);
  });
  it("沒有旗標就沒有提示", () => {
    const flashed = CAMPFIRE.hero.flash.find((f) => f.records.length === 3);
    if (flashed === undefined) throw new Error("夾具缺少已閃過的技能");
    const slots = reflashSlots({ ...flashed, reflash_transform_hint: false }, CAMPFIRE.hero.flash_rules);
    expect(slots.some((s) => s.transformHint)).toBe(false);
  });
});

describe("溶掉與傳承", () => {
  it("溶掉確認：花費、退回一半、技能會消失", () => {
    const flashed = CAMPFIRE.hero.flash.find((f) => f.records.length === 3);
    const lines = dissolveConfirm("測試技", flashed);
    expect(lines[0]).toContain("消失");
    expect(lines[1]).toContain(`${flashed?.spent} 點`);
    expect(lines[1]).toContain(`＝ ${flashed?.dissolve_refund} 點`);
    expect(flashed?.dissolve_refund).toBe(Math.floor((flashed?.spent ?? 0) / 2));
  });
  it("傳承：只有小變化可以帶；完整技能與有紀錄的技能不能接受", () => {
    const flashed = CAMPFIRE.hero.flash.find((f) => f.records.length === 3);
    expect(carryable(flashed).map((r) => r.nth)).toEqual([1, 2]);
    expect(carryable(CAMPFIRE.hero.flash.find((f) => f.complete))).toEqual([]);
    const targets = inheritTargets(CAMPFIRE.hero).map((t) => t.card.id);
    expect(targets).not.toContain(flashed?.skill_id);
    expect(targets).not.toContain(CAMPFIRE.hero.flash.find((f) => f.complete)?.skill_id);
    expect(targets.length).toBeGreaterThan(0);
  });
  it("最多帶走 2 個；選滿後不能再加，再按一次取消", () => {
    expect(maxCarry(CAMPFIRE.hero.flash_rules)).toBe(2);
    expect(toggleCarry([], 1, 2)).toEqual([1]);
    expect(toggleCarry([1, 2], 3, 2)).toEqual([1, 2]);
    expect(toggleCarry([1, 2], 1, 2)).toEqual([2]);
  });
  it("傳承請求：依序排好", () => {
    expect(inheritChoice("new", "old", [2, 1])).toEqual({ kind: "inherit", skill: "new", source: "old", records: [1, 2] });
  });
});

describe("閃現選項", () => {
  const options = PENDING.pending_flash?.options ?? [];
  it("夾具有選項", () => {
    expect(options.length).toBeGreaterThan(0);
  });
  it("轉型保底排最後", () => {
    const base = options[0] as FlashOption;
    const mixed = [
      { ...base, index: 0, transform: true, source: "transform" as const },
      { ...base, index: 1, transform: false },
      { ...base, index: 2, transform: false },
    ];
    expect(sortedOptions(mixed).map((o) => o.index)).toEqual([1, 2, 0]);
    expect(optionTag(mixed[0] as FlashOption)).toBe("轉型");
  });
  it("轉型要卸下欄位時，沒選卸下的技能不能確定", () => {
    const base = options[0] as FlashOption;
    const needs = { ...base, unequip_candidates: ["a", "b"] };
    expect(pickReady(needs, null)).toBe(false);
    expect(pickReady(needs, "a")).toBe(true);
    expect(pickReady(base, null)).toBe(true);
    expect(pickReady(undefined, null)).toBe(false);
    expect(pickChoice(needs, "a")).toEqual({ kind: "flash_pick", pick: needs.index, unequip: "a" });
    expect(pickChoice(base, "a")).toEqual({ kind: "flash_pick", pick: base.index, unequip: null });
  });
});

describe("畫面渲染", () => {
  const preview: FlashPreview = {
    skill_id: "s",
    slot: null,
    nth: 1,
    major: false,
    problem_zh: null,
    open_cost: 1,
    focused_cost: 2,
    categories: [
      { id: "area", name_zh: "範圍", count: 1 },
      { id: "combo", name_zh: "連段", count: 2 },
      { id: "cost", name_zh: "費用", count: 0 },
    ],
  };
  const hero: RunHero = CAMPFIRE.hero;
  const chooser = (over: { category?: string | null; insight?: number; preview?: FlashPreview | null } = {}) =>
    renderToStaticMarkup(
      createElement(FlashChooserView, {
        hero: { ...hero, insight: over.insight ?? 8 },
        skillId: "s",
        skillName: "測試技",
        slot: null,
        busy: false,
        onChoose: noop,
        onCancel: () => undefined,
        preview: over.preview === undefined ? preview : over.preview,
        loadError: null,
        initialCategory: over.category ?? null,
      }),
    );
  it("選類別畫面：數量寫在按鈕上，0 個的按鈕停用", () => {
    const html = chooser();
    expect(html).toContain("連段（2）");
    expect(html).toContain("範圍（1）");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*data-testid="flash-cat-cost"[^>]*>費用（0）/);
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*data-testid="flash-cat-combo"/);
    expect(html).toContain("會立刻扣 1 點靈感");
    expect(html).toContain("一定要選 1 個");
  });
  it("指定類別後確定鍵寫 2 點；點數不足時停用並說明", () => {
    expect(chooser({ category: "combo" })).toContain("確定，扣 2 點並出題");
    const poor = chooser({ category: "combo", insight: 1 });
    expect(poor).toContain("靈感點不足");
    expect(poor).toMatch(/<button[^>]*data-testid="flash-confirm"[^>]*disabled=""|<button[^>]*disabled=""[^>]*data-testid="flash-confirm"/);
  });
  it("閃現區：列出技能與已閃次數，不能閃的按鈕停用", () => {
    const html = renderToStaticMarkup(createElement(FlashSection, { runId: "r", hero, busy: false, onChoose: noop }));
    expect(html).toContain("靈感閃現");
    expect(html).toContain("已閃 3／5 次");
    expect(html).toContain("完整技能・不能再閃現");
    expect(html).toContain("一定要選一個");
  });
  it("營火：重閃、溶掉、傳承都在，溶掉與傳承是二選一的同一區", () => {
    const html = renderToStaticMarkup(createElement(CampfireSkillCare, { runId: "r", hero, busy: false, onChoose: noop }));
    expect(html).toContain("重閃（只在營火）");
    expect(html).toContain("溶掉或傳承（二選一，只在營火）");
    expect(html).toContain("調整欄");
    expect(html).toContain("可以重閃第 3 格轉型");
  });
  it("閃現選項畫面：點數已扣、每個選項有標籤與說明、最後有確定鍵", () => {
    const html = renderToStaticMarkup(createElement(RunFlashPending, { run: PENDING, busy: false, onChoose: noop }));
    expect(html).toContain("點數已經扣了，一定要選一個");
    expect(html).toContain("已扣 2 點");
    expect(html).toContain('data-testid="flash-option-tag"');
    expect(html).toContain('data-testid="flash-pick-confirm"');
  });
  it("閃現完成後 pending 清掉、歷程多一筆", () => {
    expect(AFTER.pending_flash ?? null).toBeNull();
    const f = AFTER.hero.flash.find((x) => x.records.length === 1);
    expect(f).toBeDefined();
  });
  it("完整技能三選一：說明、標籤與三張卡", () => {
    const view = runView(COMPLETE);
    if (view.screen !== "complete_offer") throw new Error("夾具不是完整技能三選一");
    const html = renderToStaticMarkup(createElement(RunCompleteOffer, { run: COMPLETE, view, busy: false, onChoose: noop }));
    expect(html).toContain("完整技能三選一");
    expect(html).toContain("預算 +120‰");
    expect(html).toContain("不能再閃現");
    expect(html.match(/data-testid="offer-badge"/g)?.length).toBe(view.offer.candidates.length);
  });
});
