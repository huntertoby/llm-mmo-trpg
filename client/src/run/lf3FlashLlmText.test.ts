// LF-3：選變體畫面顯示本機模型的名稱與一句話描述、名稱來源（夾具 `llm` 組由 `scripts/export_flash_choice_fixture.py` 真的出題產生）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FlashOption, PendingFlash, RunHero, SkillCard } from "../api/types";
import data from "../dev/fixtures/flashChoice.json";
import { FlashPendingPanel } from "../screens/RunFlashPending";
import { FLASH_LLM_NAME_HINT, FLASH_LLM_NAME_ZH, FLASH_NAME_ZH, llmNamed, noteOf, renamedTo } from "./flashChoice";
import { LLM_SOURCE_LABEL } from "./llmFlow";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases?: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;
const LLM = FIXTURE.sets.llm!;
const BASE = FIXTURE.sets.base!;
const CURRENT = FIXTURE.hero.skills[0]!.name_zh;
const noop = async () => null;
const html = (pending: PendingFlash) => renderToStaticMarkup(createElement(FlashPendingPanel, { pending, hero: FIXTURE.hero, busy: false, onChoose: noop }));
const count = (text: string, needle: string) => text.split(needle).length - 1;

function option(over: Partial<FlashOption>): FlashOption {
  return { ...BASE.options[0]!, ...over } as FlashOption;
}

describe("LF-3 純函式", () => {
  it("改名：名稱和畫面上的原名不同才算；來源照伺服器", () => {
    const o = option({ card: { ...BASE.options[0]!.card, name_zh: "竹影焚心" }, name_source: "llm" });
    expect(renamedTo(o, "點燃斬")).toBe("竹影焚心");
    expect(renamedTo(o, "竹影焚心")).toBeNull();
    expect(llmNamed(o)).toBe(true);
    expect(llmNamed(option({ name_source: "template" }))).toBe(false);
  });

  it("描述：沒有、空字串都不佔位", () => {
    expect(noteOf(option({ note_zh: null }))).toBeNull();
    expect(noteOf(option({ note_zh: "" }))).toBeNull();
    expect(noteOf(option({ note_zh: "火更旺。" }))).toBe("火更旺。");
  });

  it("名稱來源標記沿用候選卡的 LLM 標記字", () => {
    expect(FLASH_LLM_NAME_ZH).toBe(LLM_SOURCE_LABEL);
    expect(FLASH_LLM_NAME_HINT).not.toMatch(/LLM/u);
  });
});

describe("LF-3 夾具（伺服器真的出題）", () => {
  it("llm 組：大變化與轉型帶本機模型的名稱，第 3 個只有描述、名稱是組合式", () => {
    const sources = LLM.options.map((o) => o.name_source);
    expect(sources).toEqual(["llm", "llm", "template", "llm"]);
    expect(LLM.options.every((o) => noteOf(o) !== null)).toBe(true);
    const third = LLM.options[2]!;
    expect(third.card.name_zh).toContain("・");
  });

  it("沒有 LLM 文字的組：來源一律 template、沒有描述（FL-1b 的畫面不變）", () => {
    for (const key of ["base", "rows", "transform", "stance"]) {
      for (const o of FIXTURE.sets[key]!.options) {
        expect(o.name_source).toBe("template");
        expect(noteOf(o)).toBeNull();
      }
    }
  });
});

describe("LF-3 選項卡", () => {
  it("改名列排第一、描述接在名稱下面、名稱來源只標本機模型取的", () => {
    const out = html(LLM);
    // 四張都改名（組合式的也列），標記只有三顆
    expect(count(out, 'data-testid="flash-new-name"')).toBe(4);
    expect(count(out, 'data-testid="flash-name-source"')).toBe(3);
    expect(count(out, 'data-testid="flash-note"')).toBe(4);
    for (const o of LLM.options) {
      expect(out).toContain(o.card.name_zh);
      expect(out).toContain(noteOf(o)!);
    }
    // 一張卡裡的順序：大標 → 名稱列 → 描述 → 其他「前 → 後」
    const first = out.slice(out.indexOf('data-testid="flash-option-0"'), out.indexOf('data-testid="flash-option-1"'));
    const at = (s: string) => first.indexOf(s);
    expect(at('data-testid="flash-headline"')).toBeLessThan(at(FLASH_NAME_ZH));
    expect(at(FLASH_NAME_ZH)).toBeLessThan(at('data-testid="flash-new-name"'));
    expect(at('data-testid="flash-new-name"')).toBeLessThan(at('data-testid="flash-note"'));
    expect(first).toContain(`>${CURRENT}<`);
  });

  it("沒有 LLM 文字、名稱也不變（小變化）時，選項卡和 FL-1b 一樣：沒有名稱列、沒有描述", () => {
    const out = html(BASE);
    expect(out).not.toContain('data-testid="flash-new-name"');
    expect(out).not.toContain('data-testid="flash-note"');
    expect(out).not.toContain('data-testid="flash-name-source"');
  });

  it("小變化帶描述：只多一行描述，不出名稱列", () => {
    const noted: PendingFlash = { ...BASE, options: BASE.options.map((o) => ({ ...o, note_zh: "火光更盛，燒得更遠。" })) };
    const out = html(noted);
    expect(count(out, 'data-testid="flash-note"')).toBe(BASE.options.length);
    expect(out).not.toContain('data-testid="flash-new-name"');
  });

  it("描述是純文字：不解析術語標記、照字面跳脫", () => {
    const noted: PendingFlash = { ...BASE, options: [{ ...BASE.options[0]!, note_zh: "[[range|射程]]<b>" }] };
    const out = html(noted);
    expect(out).toContain("[[range|射程]]&lt;b&gt;");
  });
});
