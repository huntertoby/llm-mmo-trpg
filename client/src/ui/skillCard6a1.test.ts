// Phase 6A-1（去文字化②）：技能卡常駐 3 行、「詳細」收合、長按判定。
// 卡片用真實的 API 回應（`fixtures/skillCards.json`，重產：uv run python scripts/export_client_fixtures.py）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SkillCard } from "../api/types";
import { LONG_PRESS_MS, LONG_PRESS_SLOP_PX, LongPress } from "./floatCard";
import { hintChild, hintPinMode } from "./Hint";
import { SkillCardView } from "./SkillCardView";
import { chipLine, effectLine } from "./skillCardLines";
import cards from "./fixtures/skillCards.json";

const card = (id: keyof typeof cards) => cards[id] as unknown as SkillCard;

describe("第 2 行：AP 圓點、資源、冷卻、射程、時機", () => {
  it("法術技：AP 用圓點，法力、冷卻、射程帶數字；說明用原本的句子", () => {
    const c = card("skill_ash_harvest");
    const chips = chipLine(c);
    expect(chips.map((x) => x.icon)).toEqual(["ap", "mana", "cooldown", "range"]);
    expect(chips[0]).toMatchObject({ pips: 2, label: "", hint: "AP 2" });
    expect(chips[2]).toMatchObject({ label: "2", hint: "冷卻 2 回合" });
    expect(chips[3]).toMatchObject({ label: "5", hint: c.shape });
  });
  it("武器射程寫「武器」；反應技有時機圖示，說明是反應時機那一句", () => {
    expect(chipLine(card("skill_gale_kick")).find((x) => x.icon === "range")?.label).toBe("武器");
    const counter = card("skill_counterspell");
    const timing = chipLine(counter).find((x) => x.key === "timing");
    expect(timing).toMatchObject({ icon: "reaction", label: "反應", hint: counter.timing });
  });
  it("傳說的源力與啟動", () => {
    const icons = chipLine(card("skill_afterimage_vow")).map((x) => x.icon);
    expect(icons).toContain("source");
    expect(icons).toContain("activation");
  });
  it("舊的快照沒有 stats：第 2 行是空的（卡片照樣顯示句子）", () => {
    const { stats: _stats, ...old } = card("skill_ash_harvest") as SkillCard & { stats?: unknown };
    void _stats;
    expect(chipLine(old as SkillCard)).toEqual([]);
    expect(effectLine(old as SkillCard).fallback).toBe(old.effects[0]);
  });
});

describe("第 3 行：效果數字＋元素／縮放", () => {
  it("傷害數字＋元素，滑過看效果句與算式；有縮放屬性", () => {
    const c = card("skill_ash_harvest");
    const line = effectLine(c);
    expect(line.items).toHaveLength(1);
    expect(line.items[0]).toMatchObject({ icon: "damage", label: "3d6", element: "fire" });
    expect(line.items[0]!.hint).toContain(c.effects[0]!);
    expect(line.items[0]!.hint).toContain("傷害算法");
    expect(line.scaling.map((a) => a.label)).toEqual(["智力"]);
  });
  it("武器傷害寫倍率，推開寫格數", () => {
    const line = effectLine(card("skill_gale_kick"));
    expect(line.items.map((e) => [e.icon, e.label])).toEqual([
      ["damage", "×0.4"],
      ["move", "2"],
    ]);
    expect(line.items[1]!.tag).toBe("格");
  });
  it("表面與狀態寫回合與名稱", () => {
    const line = effectLine(card("skill_downpour"));
    expect(line.items.map((e) => e.icon)).toEqual(["surface", "status"]);
    expect(line.items[1]!.tag).toBe("回合・緩速");
    expect(line.scaling).toEqual([]); // 沒有傷害、治療、護盾就不列縮放
  });
  it("沒有數字可寫的效果（規則改變）：放第一句", () => {
    const c = card("skill_afterimage_vow");
    const line = effectLine(c);
    expect(line.items).toEqual([]);
    expect(line.fallback).toBe(c.effects[0]);
  });
});

describe("SkillCardView：常駐 3 行、其餘收進「詳細」", () => {
  const html = (props: Record<string, unknown>) => renderToStaticMarkup(createElement(SkillCardView, props as never));
  const resident = (markup: string) => markup.split("<details")[0]!;

  it("詳細外面剛好 3 行：名稱、圖示列、效果列", () => {
    const markup = html({ card: card("skill_ash_harvest") });
    expect(resident(markup).match(/data-testid="skill-card-line"/g)).toHaveLength(3);
  });
  it("標題列不寫稀有度與類型；稀有度、代價句、效果句、算式都在「詳細」裡", () => {
    const c = card("skill_ash_harvest");
    const markup = html({ card: c });
    const top = resident(markup);
    expect(top).not.toContain(c.rarity);
    expect(top).not.toContain(c.effects[0]!);
    const detail = markup.slice(top.length);
    expect(detail).toContain('data-testid="skill-card-rarity"');
    expect(detail).toContain(c.cost.join("，"));
    expect(detail).toContain(c.effects[0]!);
    expect(detail).toContain('data-testid="skill-formula"');
  });
  it("「詳細」預設收合；工坊（detailOpen）預設展開", () => {
    expect(html({ card: card("skill_ash_harvest") })).toMatch(/<details class="skill-card-detail">/);
    expect(html({ card: card("skill_ash_harvest"), detailOpen: true })).toMatch(/<details class="skill-card-detail" open="">/);
  });
  it("技能列傳入圖釘時畫圖釘與「Shift 固定」；其他地方不畫", () => {
    const pinned = html({ card: card("skill_ash_harvest"), compact: true, pin: { pinned: false, toggle: () => undefined } });
    expect(pinned).toContain("skill-card-pin");
    expect(pinned).toContain("Shift 固定");
    expect(html({ card: card("skill_ash_harvest") })).not.toContain("skill-card-pin");
  });
});

describe("長按判定（有動作的按鈕：點一下執行、長按約 0.4 秒開說明、放開不執行）", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("點一下（沒到 0.4 秒就放開）：不開說明，click 照常執行", () => {
    const fire = vi.fn();
    const lp = new LongPress(fire);
    lp.down(0, 0);
    vi.advanceTimersByTime(LONG_PRESS_MS - 1);
    lp.up();
    vi.advanceTimersByTime(1000);
    expect(fire).not.toHaveBeenCalled();
    expect(lp.consumeClick()).toBe(false);
  });
  it("長按 0.4 秒：開說明；接著的 click 被吞掉（只吞一次）", () => {
    const fire = vi.fn();
    const lp = new LongPress(fire);
    lp.down(0, 0);
    vi.advanceTimersByTime(LONG_PRESS_MS);
    expect(fire).toHaveBeenCalledTimes(1);
    lp.up();
    expect(lp.consumeClick()).toBe(true);
    expect(lp.consumeClick()).toBe(false);
  });
  it("按著移動超過容許距離（捲動）就取消", () => {
    const fire = vi.fn();
    const lp = new LongPress(fire);
    lp.down(0, 0);
    lp.move(LONG_PRESS_SLOP_PX, 0); // 沒超過
    lp.move(LONG_PRESS_SLOP_PX + 1, 0);
    vi.advanceTimersByTime(LONG_PRESS_MS * 2);
    expect(fire).not.toHaveBeenCalled();
    expect(lp.consumeClick()).toBe(false);
  });
  it("pointercancel 取消，已觸發的也不吞下一次 click", () => {
    const lp = new LongPress(() => undefined);
    lp.down();
    vi.advanceTimersByTime(LONG_PRESS_MS);
    lp.cancel();
    expect(lp.consumeClick()).toBe(false);
  });
  it("Hint 包按鈕用長按，包沒有動作的元素維持點一下開說明", () => {
    expect(hintPinMode(hintChild(createElement("button", { type: "button" }, "x")))).toBe("hold");
    expect(hintPinMode(hintChild(createElement("span", null, "x")))).toBe("touch");
    expect(hintPinMode(null)).toBe("touch");
  });
});
