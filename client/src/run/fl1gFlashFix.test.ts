// FL-1g：選變體畫面的美術驗收修正（docs/art/FL-1b驗收.md 第 2、3、7 節）。
// 版面高度與捲動要實拍（docs/art/shots/FL-1g/）；這裡只鎖住字、結構與 CSS 規則。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync } from "node:fs";
import type { PendingFlash, RunHero, SkillCard } from "../api/types";
import data from "../dev/fixtures/flashChoice.json";
import { FlashPendingPanel, scrollBlock } from "../screens/RunFlashPending";
import { FLASH_LLM_NAME_HINT } from "./flashChoice";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases?: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;
const readText = readFileSync as (url: URL, enc: string) => string;
const CSS = readText(new URL("../styles/flash-choice.css", import.meta.url), "utf-8");
const noop = async () => null;
const html = (pending: PendingFlash) => renderToStaticMarkup(createElement(FlashPendingPanel, { pending, hero: FIXTURE.hero, busy: false, onChoose: noop }));

/** CSS 檔裡某個選擇器的規則本文（第一個符合的）。 */
function rule(selector: string): string {
  const at = CSS.indexOf(`${selector} {`);
  expect(at, selector).toBeGreaterThanOrEqual(0);
  return CSS.slice(at, CSS.indexOf("}", at));
}

describe("FL-1g 字", () => {
  it("源晶推演說明卡（玩法 PM 2026-11-13 定案）", () => {
    expect(FLASH_LLM_NAME_HINT).toBe("源晶推演：這個名字是源晶照你這一路的戰鬥推演出來的，只是名字；效果和數值都照規則定，不會因為名字改變。");
  });
});

describe("FL-1g 結構", () => {
  it("新名稱和「源晶推演」包在同一個不斷行的組（LF-3 可修 1）", () => {
    const out = html(FIXTURE.sets.llm!);
    const groups = out.split('data-testid="flash-name-group"').slice(1);
    expect(groups.length).toBeGreaterThan(0);
    const tagged = groups.filter((g) => g.slice(0, g.indexOf("</span></span></span>") + 30).includes('data-testid="flash-name-source"'));
    expect(tagged.length).toBeGreaterThan(0);
    expect(rule(".fc-name-group")).toContain("white-space: nowrap");
  });

  it("「源晶推演」字級 11.5px（LF-3 可修 2）", () => {
    expect(rule(".fc-src")).toContain("font-size: 11.5px");
  });

  it("選變體捲動區的上緣漸隱 32px、選中的卡讓出漸隱（FL-1b 可修 1、LF-3 必修 1）", () => {
    const fade = rule(".ui-popup-hud > .ui-popup-body:has(.fc-in-popup)::before");
    expect(fade).toContain("height: 32px");
    expect(fade).toContain("margin-bottom: -32px");
    expect(rule(".fc-in-popup .fc-opt")).toContain("scroll-margin-top: 36px");
  });

  it("一輪的下固定區上方有漸隱，一句話 text-wrap: pretty（FL-1b 可修 5）", () => {
    expect(rule(".fc-run > .fc-foot::before")).toContain("bottom: 100%");
    expect(rule(".fc-say")).toContain("text-wrap: pretty");
  });
});

describe("FL-1g 選中的卡捲到哪（LF-3 必修 1）", () => {
  afterEach(() => vi.unstubAllGlobals());

  function card(height: number, room: number | null): HTMLElement {
    vi.stubGlobal("window", {
      innerHeight: 600,
      getComputedStyle: () => ({ scrollMarginTop: "36px", scrollMarginBottom: "20px" }),
    });
    return {
      closest: () => (room === null ? null : { clientHeight: room }),
      getBoundingClientRect: () => ({ height }),
    } as unknown as HTMLElement;
  }

  it("放得下用 nearest，放不下對齊上緣", () => {
    expect(scrollBlock(card(150, 262))).toBe("nearest");
    expect(scrollBlock(card(220, 262))).toBe("start");
  });

  it("一輪（沒有捲動區）看視窗高", () => {
    expect(scrollBlock(card(500, null))).toBe("nearest");
    expect(scrollBlock(card(560, null))).toBe("start");
  });
});
