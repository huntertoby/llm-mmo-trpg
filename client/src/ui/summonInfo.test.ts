// 召喚物資訊小卡與關鍵字分級（Phase 3-41a）：實際渲染出的文字。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { KeywordRef, SummonInfoCard } from "../api/types";
import { KeywordLine } from "./KeywordLine";
import { SummonInfo } from "./SummonInfo";

const ICE: SummonInfoCard = {
  id: "summon_ice_spirit",
  name_zh: "冰靈",
  count: 1,
  hp: 14,
  hp_note: "施放者 1 級時",
  move: "5 格",
  defense: "護甲 +0",
  attack: "冰霜法杖：1d6 冰霜傷害（射程 5）",
  innate: ["普攻命中時施加「緩速」2 回合", "普攻命中站在水上的目標時施加「冰凍」1 回合"],
  behavior: ["預設模式「跟隨」"],
  infusion: "灌注：施放時從你持有的關鍵字選一個帶上",
};

describe("召喚物資訊小卡", () => {
  it("寫出 HP、攻擊與自帶能力（後端產生的文字照排）", () => {
    const html = renderToStaticMarkup(createElement(SummonInfo, { info: ICE, open: true }));
    expect(html).toContain("召喚物資訊：冰靈（HP 14）");
    expect(html).toContain("<details");
    expect(html).toContain("open");
    expect(html).toContain("普攻命中站在水上的目標時施加「冰凍」1 回合");
    expect(html).toContain("施放時從你持有的關鍵字選一個帶上");
    expect(html).not.toContain("灌注：施放時");
  });

  it("浮動卡預設收起", () => {
    const html = renderToStaticMarkup(createElement(SummonInfo, { info: ICE }));
    expect(html).not.toMatch(/<details[^>]*open/);
  });
});

describe("關鍵字分級", () => {
  const ref = (id: string, general: boolean): KeywordRef => ({
    id,
    name_zh: id === "prone" ? "倒地" : "點燃",
    description_zh: "說明",
    variant: false,
    general,
    reason_zh: general ? "近戰攻擊倒地的目標有優勢" : null,
  });

  it("通用歸類的關鍵字標灰", () => {
    const html = renderToStaticMarkup(
      createElement(KeywordLine, { keywords: { makes: [ref("ignite", false)], uses: [ref("prone", true)] } }),
    );
    expect(html).toContain('class="part-tip keyword-chip general"');
    expect(html).toContain('class="part-tip keyword-chip"');
  });
});
