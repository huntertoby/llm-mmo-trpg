// PB-1f（e3p）：美術 FL-1j 待決 2 裁定（`docs/art/FL-1b驗收.md` 末節）——
// (1)「」括起來的名字 ≤ 6 字時連同括號不斷行（通用規則）；(2) 不可拆詞再加「回合」「點燃」（「本／回合」可以）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PendingFlash, RunHero, SkillCard } from "../api/types";
import data from "../dev/fixtures/flashChoice.json";
import { FLASH_NO_BREAK_WORDS, noBreakRuns, numberUnitRuns, QUOTED_NAME_MAX, sayText } from "./flashChoice";
import { NoBreakText } from "./FlashChoiceParts";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;
const kept = (text: string) => noBreakRuns(text).filter((r) => r.keep).map((r) => r.text);

describe("「」括起來的名字不斷行", () => {
  it("≤ 6 字連同括號整段；超過 6 字照常可斷；空的不包", () => {
    expect(QUOTED_NAME_MAX).toBe(6);
    expect(kept("目標帶有狀態「雷電」時")).toEqual(["「雷電」"]);
    expect(kept("目標帶有狀態「被標記」時")).toEqual(["「被標記」"]);
    expect(kept("技能「六個字的名字」")).toEqual(["「六個字的名字」"]);
    expect(kept("技能「七個字的長名字」")).toEqual([]);
    expect(kept("「」")).toEqual([]);
  });
  it("一句話裡兩個名字各自一段；括號沒配對不包", () => {
    expect(kept("站在「水」或「油」上")).toEqual(["「水」", "「油」"]);
    expect(kept("站在「水上")).toEqual([]);
  });
  it("名字裡的數字＋單位、不可拆詞和名字併成一段（重疊的取聯集）", () => {
    expect(kept("「第 3 式」")).toEqual(["「第 3 式」"]);
    expect(kept("目標有「點燃」時")).toEqual(["「點燃」"]);
  });
  it("段落接回去等於原文", () => {
    const s = "目標站在「水」表面上、帶有「被標記」時，燃燒少 1 回合";
    expect(noBreakRuns(s).map((r) => r.text).join("")).toBe(s);
  });
  it("NoBreakText 輸出 .fc-nobr", () => {
    expect(renderToStaticMarkup(createElement(NoBreakText, { text: "帶有「被標記」時" }))).toBe('帶有<span class="fc-nobr">「被標記」</span>時');
  });
});

describe("不可拆詞加「回合」「點燃」", () => {
  it("清單", () => {
    expect(FLASH_NO_BREAK_WORDS).toContain("回合");
    expect(FLASH_NO_BREAK_WORDS).toContain("點燃");
  });
  it("「本回合」只保「回合」（「本／回合」可以斷）", () => {
    expect(kept("本回合結束時")).toEqual(["回合"]);
    expect(kept("命中後點燃目標")).toEqual(["點燃"]);
  });
  it("數字＋單位照舊一段（不被「回合」切成「少 1」＋「回合」兩段）", () => {
    expect(noBreakRuns("燃燒少 1 回合，")).toEqual([
      { text: "燃燒", keep: false },
      { text: "少 1 回合", keep: true },
      { text: "，", keep: false },
    ]);
    expect(numberUnitRuns("燃燒少 1 回合，")).toEqual(noBreakRuns("燃燒少 1 回合，"));
  });
  it("數字的單位不切進不可拆詞的中間（「第 3 格」＋「轉型」、「強度」不從「度」黏起）", () => {
    expect(kept("可以重閃第 3 格轉型")).toEqual(["第 3 格", "轉型"]);
    expect(kept("灼燒強度 +1")).toEqual(["強度"]);
    expect(kept("持續 2 回合點燃")).toEqual(["續 2 回合", "點燃"]);
  });
  it("夾具每一句話：「」≤ 6 字的名字都在不斷行段裡；「回合」「點燃」不被拆開", () => {
    for (const [key, p] of Object.entries(FIXTURE.sets)) {
      for (const o of p.options) {
        const say = sayText(o);
        const runs = noBreakRuns(say);
        expect(runs.map((r) => r.text).join(""), key).toBe(say);
        for (const r of runs.filter((x) => !x.keep)) {
          expect(/「[^「」]{1,6}」/u.test(r.text), `${key}: ${r.text}`).toBe(false);
          expect(/回合|點燃/u.test(r.text), `${key}: ${r.text}`).toBe(false);
        }
      }
    }
  });
});
