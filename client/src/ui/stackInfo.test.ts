// 層數說明框、技能卡傷害算法與開局資源預覽（Phase 3-41c）：文字由後端產生，前端只排版與過濾。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";
import type { Glossary, SkillCard } from "../api/types";
import { setGlossary } from "../battle/glossary";
import { stackHintText, stackSkillNames } from "../battle/stackInfo";
import { resourceText } from "../run/startResources";
import { overlayCards } from "./useHeroCards";
import { StackTip } from "./StackTip";

const GLOSSARY = {
  terrain: [],
  surfaces: [],
  objects: [],
  statuses: [],
  reactions: [],
  elements: [],
  attributes: [],
  effects: [],
  conditions: [],
  triggers: [],
  actions: [],
  objectives: [],
  weapon_looks: [],
  stacks: [
    {
      id: "static_charge",
      name_zh: "靜電",
      description_zh: "累積在施放者自己身上的蓄能。",
      tags: ["self"],
      rules_zh: ["上限依來源（最多 5 層）"],
    },
  ],
} as unknown as Glossary;

function card(id: string, name: string, stacks: SkillCard["stacks"], formula: string[] = []): SkillCard {
  return { id, name_zh: name, stacks, formula_lines: formula } as unknown as SkillCard;
}

beforeEach(() => setGlossary(GLOSSARY));

describe("層數說明框", () => {
  const cards = {
    a: card("a", "蓄電", [{ id: "static_charge", name_zh: "靜電", role: "makes" }]),
    b: card("b", "放電", [{ id: "static_charge", name_zh: "靜電", role: "uses" }]),
    c: card("c", "無關", []),
  };

  it("列出你擁有的、會累積與消耗它的技能", () => {
    expect(stackSkillNames("static_charge", cards, ["a", "b", "c"])).toEqual({ makes: ["蓄電"], uses: ["放電"] });
    const text = stackHintText("static_charge", cards, ["a", "b", "c"]) ?? "";
    expect(text).toContain("靜電");
    expect(text).toContain("・上限依來源（最多 5 層）");
    expect(text).toContain("你的技能・累積：蓄電");
    expect(text).toContain("你的技能・消耗／利用：放電");
  });

  it("只持有無關技能時說沒有", () => {
    expect(stackHintText("static_charge", cards, ["c"])).toContain("你目前沒有會累積或消耗它的技能");
  });

  it("沒有持有者（工坊）只寫一般說明", () => {
    const text = stackHintText("static_charge", cards, null) ?? "";
    expect(text).not.toContain("你的技能");
    expect(text).toContain("累積在施放者自己身上的蓄能。");
  });

  it("對照表沒有的層數沒有說明", () => {
    expect(stackHintText("nope")).toBeNull();
  });
});


describe("戰鬥中主角的技能卡", () => {
  it("實際值版本蓋在基本卡片上", () => {
    const base = { a: card("a", "基本", []), b: card("b", "另一張", []) };
    const live = { a: card("a", "實際", [], ["傷害算法：…（目前 +4）"]) };
    const merged = overlayCards(base, live);
    expect(merged.a?.formula_lines).toEqual(["傷害算法：…（目前 +4）"]);
    expect(merged.b?.name_zh).toBe("另一張");
    expect(overlayCards(base, null)).toBe(base);
  });
});

describe("層數名稱元件", () => {
  it("用共用的說明卡包住名稱", () => {
    const html = renderToStaticMarkup(createElement(StackTip, { id: "static_charge" }));
    expect(html).toContain("hint-tip");
    expect(html).toContain("靜電");
  });
});

describe("開局資源預覽", () => {
  it("寫出 HP、法力與耐力", () => {
    expect(resourceText({ hp: 38, mana: 12, stamina: 34 })).toBe("HP 38・法力 12・耐力 34");
    expect(resourceText(null)).toContain("耐力");
  });
});
