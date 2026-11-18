// PK-4b（玩法 PM 4.1.27 題 4、5）：許願池的三選一不標「偏離路線」；挑選模式（`pick: llm`）的卡也標「源晶推演」，說明句分兩種。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { OfferTag, RunHero, RunOffer, SkillCard } from "../api/types";
import cards from "../ui/fixtures/skillCards.json";
import { LLM_PICK_HINT, LLM_SOURCE_HINT, isLlmTag, llmTagHint } from "./llmFlow";
import { OfferPicker } from "./OfferPicker";

const CARD = (cards as unknown as Record<string, SkillCard>)["skill_ash_harvest"]!;

const tag = (source: OfferTag["source"], pick: OfferTag["pick"] = null): OfferTag => ({
  kind: "new",
  label_zh: "新方向",
  keywords: [],
  fallback: false,
  source,
  pick,
});

function offer(t: OfferTag): RunOffer {
  return { reason: "level_up", tier: 1, top_attribute: "int", candidates: [CARD], off_route: [0], tags: [t] } as unknown as RunOffer;
}

function render(t: OfferTag, extra: Record<string, unknown> = {}): string {
  const props = { offer: offer(t), hero: { skills: [] } as unknown as RunHero, runSeed: 0, groupKey: "g", pick: null, replace: null, onPick: () => {}, onReplace: () => {} };
  return renderToStaticMarkup(createElement(OfferPicker, { ...props, ...extra }));
}

describe("PK-4b 許願池不標偏離路線", () => {
  it("許願池（hideOffRoute）不畫偏離標籤與偏離框", () => {
    const html = render(tag("composer", "llm"), { wish: true, hideOffRoute: true });
    expect(html).not.toContain("off-route");
    expect(html).not.toContain("偏離路線");
  });

  it("其他三選一照舊標偏離路線", () => {
    const html = render(tag("composer", "llm"));
    expect(html).toContain("off-route-tag");
    expect(html).toContain("偏離路線");
  });
});

describe("PK-4b 源晶推演小標", () => {
  it("說明句：挑選模式照 4.1.27 題 5 的字，自由設計照舊", () => {
    expect(LLM_PICK_HINT).toBe("這張技能的名字和描述由本機模型取；效果和數值都照規則出題。");
    expect(LLM_SOURCE_HINT).toBe("這張技能由本機模型提議，數值由規則補齊。");
  });

  it("哪些卡有小標、用哪一句說明", () => {
    expect(llmTagHint(tag("llm"))).toBe(LLM_SOURCE_HINT);
    expect(llmTagHint(tag("composer", "llm"))).toBe(LLM_PICK_HINT);
    expect(llmTagHint(tag("pool", "llm"))).toBe(LLM_PICK_HINT);
    expect(llmTagHint(tag("composer", "top"))).toBeNull();
    expect(llmTagHint(tag("pool"))).toBeNull();
    expect(llmTagHint(undefined)).toBeNull();
    expect(isLlmTag(tag("composer", "llm"))).toBe(true);
    expect(isLlmTag(tag("composer", "top"))).toBe(false);
  });

  it("挑選模式的卡畫小標（升級與許願都有），分數第一名（top）不畫", () => {
    expect(render(tag("composer", "llm"))).toContain('data-testid="offer-llm"');
    expect(render(tag("composer", "llm"), { wish: true, hideOffRoute: true })).toContain('data-testid="offer-llm"');
    expect(render(tag("composer", "top"))).not.toContain('data-testid="offer-llm"');
    expect(render(tag("llm"))).toContain('data-testid="offer-llm"');
  });
});
