// PK-4b（玩法 PM 4.1.27 題 4）：許願池的三選一不標「偏離路線」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { OfferTag, RunHero, RunOffer, SkillCard } from "../api/types";
import cards from "../ui/fixtures/skillCards.json";
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
