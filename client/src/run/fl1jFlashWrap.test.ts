// FL-1j：閃現、重閃、成長面板的斷行（美術 FL-1i 複驗可修 1、2；`docs/art/FL-1b驗收.md` 末節）。
// (1) 「傷害」「轉型」是不可拆詞；(2) 數字和單位不拆開（通用規則 `numberUnitRuns`，不逐字列舉）；
// (3) 成長面板／營火重閃格的藍字「可以重閃第 3 格轉型」不斷成「轉／型」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PendingFlash, RunHero, SkillCard } from "../api/types";
import data from "../dev/fixtures/flashChoice.json";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { TRANSFORM_HINT } from "./flash";
import { FLASH_NO_BREAK_WORDS, noBreakRuns, numberUnitRuns, sayText, unitAfterNumber } from "./flashChoice";
import { NoBreakText, TermText } from "./FlashChoiceParts";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;

const kept = (text: string) => noBreakRuns(text).filter((r) => r.keep).map((r) => r.text);

describe("FL-1j (1) 「傷害」「轉型」不可拆", () => {
  it("清單有四個詞", () => {
    expect([...FLASH_NO_BREAK_WORDS]).toEqual(["雙手槍", "強度", "傷害", "轉型"]);
  });
  it("「1d4 火焰傷害」切出「傷害」；轉型句切出「轉型」", () => {
    expect(kept("多了額外傷害：1d4 火焰傷害（目標帶有狀態「被標記」時才有）。")).toEqual(["傷害", "1d4 火焰", "傷害"]);
    expect(kept("這招變成陷阱：先布在地上。轉型後照新種類重算強度")).toEqual(["轉型", "強度"]);
  });
});

describe("FL-1j (2) 數字和單位不拆開（通用規則）", () => {
  it("單位：中文取前兩個字；英文字母整串", () => {
    expect(unitAfterNumber("格的敵人")).toBe("格的");
    expect(unitAfterNumber("回合，多了")).toBe("回合");
    expect(unitAfterNumber("格外。")).toBe("格外");
    expect(unitAfterNumber("AP（原本 2）")).toBe("AP");
    expect(unitAfterNumber("，")).toBe("");
    expect(unitAfterNumber("")).toBe("");
  });

  it("「燃燒少 1 回合」整段不拆；前面緊貼的一個字一起黏", () => {
    expect(numberUnitRuns("燃燒少 1 回合，")).toEqual([
      { text: "燃燒", keep: false },
      { text: "少 1 回合", keep: true },
      { text: "，", keep: false },
    ]);
  });

  it("小數、骰子、AP、括號裡的原本值都黏；沒有單位也沒有前字的不包", () => {
    expect(kept("只要 1 AP（原本 2），用過之後要等 5 回合")).toEqual(["要 1 AP", "本 2", "等 5 回合"]);
    expect(kept("從 1.15 倍")).toEqual(["從 1.15 倍"]);
    expect(kept("（2d6）")).toEqual([]);
    expect(numberUnitRuns("沒有數字")).toEqual([{ text: "沒有數字", keep: false }]);
    expect(numberUnitRuns("")).toEqual([]);
  });

  it("夾具每一句話：每個數字都在不斷行段裡，或前後都不是中文字（不會出現「少 1 ／回合」）", () => {
    for (const [key, p] of Object.entries(FIXTURE.sets)) {
      for (const o of p.options) {
        const say = sayText(o).replace(/\[\[[^|\]]*\|([^\]]*)\]\]/gu, "$1");
        const runs = noBreakRuns(say);
        expect(runs.map((r) => r.text).join(""), key).toBe(say);
        for (const r of runs.filter((x) => !x.keep)) {
          // 不斷行段以外的數字：後面不能直接接中文字或英文單位
          expect(/\d ?[\p{Script=Han}A-Za-z]/u.test(r.text.replace(/\d+d\d+/gu, "")), `${key}: ${r.text}`).toBe(false);
        }
      }
    }
  });

  it("1600 斷錯的兩張重閃大變化卡：「燃燒少 1 回合」「1d4 火焰」「傷害」都包成 .fc-nobr", () => {
    const p = FIXTURE.sets.reflash_major;
    if (p === undefined) throw new Error("夾具缺 reflash_major");
    const plain = p.options.filter((o) => !o.transform && o.say_zh !== "");
    expect(plain.length).toBe(2);
    for (const o of plain) {
      const html = renderToStaticMarkup(createElement(TermText, { text: sayText(o), terms: p.terms ?? {}, nobr: true }));
      expect(html).toContain('<span class="fc-nobr">少 1 回合</span>');
      expect(html).toContain('<span class="fc-nobr">1d4 火焰</span><span class="fc-nobr">傷害</span>');
    }
  });
});

describe("FL-1j (3) 成長面板／營火的藍字「可以重閃第 3 格轉型」", () => {
  it("切成「可以重閃」＋「第 3 格」＋「轉型」，後兩段不斷行", () => {
    expect(noBreakRuns(TRANSFORM_HINT)).toEqual([
      { text: "可以重閃", keep: false },
      { text: "第 3 格", keep: true },
      { text: "轉型", keep: true },
    ]);
    expect(renderToStaticMarkup(createElement(NoBreakText, { text: TRANSFORM_HINT }))).toBe(
      '可以重閃<span class="fc-nobr">第 3 格</span><span class="fc-nobr">轉型</span>',
    );
  });
  it("營火重閃鈕與技能卡的閃現資訊都經過 NoBreakText", () => {
    expect(readFile(SRC_DIR, "run/CampfireSkillCare.tsx")).toContain("<NoBreakText text={TRANSFORM_HINT} />");
    expect(readFile(SRC_DIR, "ui/SkillFlashInfo.tsx")).toContain("<NoBreakText text={TRANSFORM_HINT} />");
    // .fc-nobr 在 flash-choice.css，index.css 全域載入，成長面板也吃得到
    expect(readFile(SRC_DIR, "styles/index.css")).toContain("flash-choice.css");
  });
});
