// TXT-2：選變體畫面的換行（FL-1g 複驗新可修 1：一輪窄欄條件字；美術 PM：大標 text-wrap: balance）。
import { describe, expect, it } from "vitest";
import { readStyleFiles, stripCssComments } from "../test/sourceScan";

const css = stripCssComments(readStyleFiles().find(([p]) => p === "styles/flash-choice.css")?.[1] ?? "");

function rule(selector: string): string {
  const at = css.indexOf(`${selector} {`);
  expect(at, selector).toBeGreaterThan(-1);
  return css.slice(at, css.indexOf("}", at));
}

describe("選變體畫面的換行（TXT-2）", () => {
  it("大標加 text-wrap: balance，仍是 keep-all＋兩行截斷", () => {
    const head = rule(".fc-headline");
    expect(head).toContain("text-wrap: balance");
    expect(head).toContain("word-break: keep-all");
    expect(head).toContain("line-clamp: 2");
  });
  it("「前」「後」只在空白與標點換行；括號條件可以在字間換行；帶條件的前段整段不斷", () => {
    expect(css).toMatch(/\.fc-was,\s*\.fc-now > span \{\s*word-break: keep-all;\s*overflow-wrap: break-word;\s*\}/);
    expect(rule(".fc-now .fc-when")).toContain("word-break: normal");
    expect(rule(".fc-main")).toContain("white-space: nowrap");
  });
});
