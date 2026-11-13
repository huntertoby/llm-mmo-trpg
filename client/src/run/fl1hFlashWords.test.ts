// FL-1h：閃現與重閃的字與小修。
// (e3h) 轉型不套整招篩選（06 6.34.5，玩法 PM 選 (b)）：有轉型選項的面板，上固定區那句帶「轉型除外」；轉型卡的下固定區句末接一句。
// (e3i) 「▼ 比原本弱」的 ▼ 用和前 → 後同一個 CSS 三角（美術 RR-2 可修 1）。
// (e3j) 重閃選項整招和現在一樣、前 → 後一列都沒有：卡裡放「和現在一樣，選了這招不會變」（玩法 PM 4.1.2 第 4 條）。
// (e3f) 條件括號裡「雙手槍」不斷行（美術 11-13）；FL-1i：下固定區的一句話也開 nobr，「強度」不斷成「強／度」。
// 夾具：`dev/fixtures/flashChoice.json`（`scripts/export_flash_choice_fixture.py`，`reflash`／`reflash_major` 是伺服器真的出題）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PendingFlash, RunHero, SkillCard } from "../api/types";
import { FlashPendingPanel } from "../screens/RunFlashPending";
import { readFile, SRC_DIR } from "../test/sourceScan";
import data from "../dev/fixtures/flashChoice.json";
import {
  FLASH_MUST_PICK_TRANSFORM_ZH,
  FLASH_MUST_PICK_ZH,
  FLASH_NO_BREAK_WORDS,
  FLASH_SAME_AS_NOW_ZH,
  FLASH_TRANSFORM_FOOT_ZH,
  hasTransform,
  noBreakRuns,
  sameAsNow,
  sayText,
} from "./flashChoice";
import { TermText } from "./FlashChoiceParts";
import { mustPickText } from "./reflashWeaker";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;
const noop = async () => null;

function set(key: string): PendingFlash {
  const p = FIXTURE.sets[key];
  if (p === undefined) throw new Error(`夾具缺少 ${key}`);
  return p;
}

function heroFor(key: string): RunHero {
  const base = FIXTURE.bases[key];
  return base === undefined ? FIXTURE.hero : { ...FIXTURE.hero, skills: [base, ...FIXTURE.hero.skills.slice(1)] };
}

function panel(key: string, pending: PendingFlash = set(key)): string {
  return renderToStaticMarkup(createElement(FlashPendingPanel, { pending, hero: heroFor(key), busy: false, onChoose: noop }));
}

describe("FL-1h (e3h) 轉型不套整招篩選的字", () => {
  it("有轉型選項的面板：上固定區那句帶「轉型除外」；沒有轉型的照舊", () => {
    expect(FLASH_MUST_PICK_TRANSFORM_ZH).toBe("一定要選一個。選哪個這招整體都會強一點（轉型除外），標 ▼ 的是拿來換的");
    for (const key of ["transform", "stance", "llm", "reflash_major"]) {
      expect(hasTransform(set(key).options)).toBe(true);
      expect(mustPickText(set(key))).toBe(FLASH_MUST_PICK_TRANSFORM_ZH);
      expect(panel(key)).toContain(FLASH_MUST_PICK_TRANSFORM_ZH);
    }
    for (const key of ["base", "rows"]) {
      expect(mustPickText(set(key))).toBe(FLASH_MUST_PICK_ZH);
      expect(panel(key)).not.toContain("轉型除外");
    }
  });

  it("較弱的重閃照舊用伺服器的句子（即使有轉型選項）", () => {
    const weak = set("reflash");
    expect(weak.weaker_foot_zh).toBeTruthy();
    expect(mustPickText(weak)).toBe("一定要選一個。這次的選項可能比現在弱；標 ▼ 的是變小的地方");
    const withTransform = { ...weak, options: weak.options.map((o, i) => (i === 0 ? { ...o, transform: true } : o)) };
    expect(mustPickText(withTransform)).not.toContain("轉型除外");
  });

  it("轉型卡的一句話句末接「轉型後照新種類重算強度，不跟原本比。」；一般卡照伺服器的字", () => {
    expect(FLASH_TRANSFORM_FOOT_ZH).toBe("轉型後照新種類重算強度，不跟原本比。");
    for (const key of ["transform", "stance", "llm", "reflash_major"]) {
      for (const o of set(key).options) {
        const say = o.say_zh || o.summary_zh;
        if (o.transform) expect(sayText(o)).toBe(/[。！？]$/u.test(say) ? `${say}${FLASH_TRANSFORM_FOOT_ZH}` : `${say}。${FLASH_TRANSFORM_FOOT_ZH}`);
        else expect(sayText(o)).toBe(say);
      }
    }
    const o = set("transform").options.find((x) => x.transform);
    if (o === undefined) throw new Error("夾具缺少轉型卡");
    expect(sayText({ ...o, say_zh: "", summary_zh: "轉成反應" })).toBe(`轉成反應。${FLASH_TRANSFORM_FOOT_ZH}`);
  });

  it("有轉型選項的面板下固定區多留一行（transform-room），沒有的不加", () => {
    expect(panel("transform")).toMatch(/class="fc-foot reserve transform-room"/);
    expect(panel("llm")).toMatch(/class="fc-foot transform-room"/);
    expect(panel("base")).toMatch(/class="fc-foot"/);
  });
});

describe("FL-1h (e3i) 「比原本弱」的 ▼", () => {
  it("小標用 .fc-down，且不再縮小（和前 → 後列同一個三角）；重閃入口按鈕裡的照舊縮小", () => {
    const html = panel("reflash");
    expect(html.match(/data-testid="flash-option-weaker"/g)?.length).toBe(3);
    expect(html).toMatch(/class="fc-weaker"[^>]*><i class="fc-down" aria-label="變弱"><\/i>比原本弱/);
    const css = readFile(SRC_DIR, "styles/reflash-weaker.css");
    const weakerDown = css.match(/\.fc-weaker \.fc-down\s*\{([^}]*)\}/u);
    expect(weakerDown).not.toBeNull();
    expect(weakerDown?.[1]).not.toMatch(/border/u);
    expect(css).not.toMatch(/\.fc-weaker \.fc-down\s*,/u);
    expect(css).toMatch(/\.reflash-weaker-note \.fc-down\s*\{[^}]*border-top-width: 8px/u);
  });
});

describe("FL-1h (e3j) 和現在一樣", () => {
  it("重現案例（#160 例外格）：整招等於現在的那張卡放「和現在一樣」，其他三張照舊列前 → 後", () => {
    const p = set("reflash");
    const now = FIXTURE.bases.reflash;
    const same = p.options.filter((o) => sameAsNow(p, o, now));
    expect(same.length).toBe(1);
    expect(same[0]?.weaker_tag_zh ?? null).toBeNull();
    const html = panel("reflash");
    expect(html.match(/data-testid="flash-same"/g)?.length).toBe(1);
    expect(html).toContain(`<p class="fc-same" data-testid="flash-same">${FLASH_SAME_AS_NOW_ZH}</p>`);
    expect(html.match(/data-testid="flash-diffs"/g)?.length).toBe(3);
  });

  it("大變化格的重閃：卡的內容和現在一樣的那張也放；有變化的不放", () => {
    const p = set("reflash_major");
    expect(p.options.filter((o) => sameAsNow(p, o, FIXTURE.bases.reflash_major)).length).toBe(1);
  });

  it("新的閃現不放；找不到現在的卡、卡的內容不同、名稱不同都不放", () => {
    const p = set("reflash");
    const o = p.options.find((x) => sameAsNow(p, x, FIXTURE.bases.reflash));
    const now = FIXTURE.bases.reflash;
    if (o === undefined || now === undefined) throw new Error("夾具缺少一樣的卡");
    expect(sameAsNow({ ...p, slot: null }, o, now)).toBe(false);
    expect(sameAsNow(p, o, undefined)).toBe(false);
    expect(sameAsNow(p, { ...o, card: { ...o.card, tier: o.card.tier + 1 } }, now)).toBe(false);
    expect(sameAsNow(p, { ...o, card: { ...o.card, name_zh: "別的名字" } }, now)).toBe(false);
    expect(sameAsNow(p, { ...o, note_zh: "源晶的一句話" }, now)).toBe(false);
    // id 不同、鍵的順序不同都算一樣
    const reordered = Object.fromEntries(Object.entries(o.card).reverse()) as SkillCard;
    expect(sameAsNow(p, { ...o, card: { ...reordered, id: "other" } }, now)).toBe(true);
    for (const key of ["base", "rows", "transform", "stance", "llm"]) expect(panel(key)).not.toContain("flash-same");
  });
});

describe("FL-1h (e3f) 條件括號的不可拆詞", () => {
  it("「雙手槍」切成不斷行的一段", () => {
    expect(noBreakRuns("（手持雙手槍時才有）")).toEqual([
      { text: "（手持", keep: false },
      { text: "雙手槍", keep: true },
      { text: "時才有）", keep: false },
    ]);
    expect(noBreakRuns("（目標站在「水」表面上時才有）")).toEqual([{ text: "（目標站在「水」表面上時才有）", keep: false }]);
    expect(noBreakRuns("雙手槍雙手槍")).toEqual([
      { text: "雙手槍", keep: true },
      { text: "雙手槍", keep: true },
    ]);
    expect(noBreakRuns("")).toEqual([]);
  });

  it("選項卡的條件括號裡「雙手槍」包成 .fc-nobr（夾具 rows 組的額外傷害）", () => {
    const html = panel("rows");
    expect(html).toMatch(/<span class="fc-when">（手持<span class="fc-nobr">雙手槍<\/span>時才有）<\/span>/u);
    expect(readFile(SRC_DIR, "styles/flash-choice.css")).toMatch(/\.fc-nobr\s*\{\s*white-space: nowrap;\s*\}/u);
  });
});

describe("FL-1i 轉型卡下固定區「強度」不可拆（美術 RR-2 驗收 F-1）", () => {
  it("「強度」是不可拆詞；轉型句切出「強度」一段", () => {
    expect(FLASH_NO_BREAK_WORDS).toContain("強度");
    expect(noBreakRuns(FLASH_TRANSFORM_FOOT_ZH)).toEqual([
      { text: "轉型後照新種類重算", keep: false },
      { text: "強度", keep: true },
      { text: "，不跟原本比。", keep: false },
    ]);
  });

  it("下固定區的一句話開 nobr（轉型句的「強度」包成 .fc-nobr）", () => {
    expect(readFile(SRC_DIR, "screens/RunFlashPending.tsx")).toContain("<TermText text={sayText(picked)} terms={terms} nobr />");
    const p = set("transform");
    const o = p.options.find((x) => x.transform);
    if (o === undefined) throw new Error("夾具 transform 組缺轉型選項");
    const html = renderToStaticMarkup(createElement(TermText, { text: sayText(o), terms: p.terms ?? {}, nobr: true }));
    expect(html).toContain('重算<span class="fc-nobr">強度</span>，不跟原本比。');
  });
});
