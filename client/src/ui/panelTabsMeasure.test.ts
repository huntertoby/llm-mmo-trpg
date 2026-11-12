// pnl2-merge（PNL-1b 美術驗收可修 2）：量高度的那層量完要移出排版，不能撐大捲動區的 scrollHeight。
// vitest 沒有 DOM：這裡鎖 CSS（量測外層 0 高、不佔位）、原始碼（只在量的時候掛）與靜態輸出；
// 實機量到的 scrollHeight 變化見 docs/phases/PhasePNL-2報告.md「與 PNL-1b 整合」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { readFile, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { PanelTabs, type PanelTabDef } from "./PanelTabs";

const css = readStyleFiles()
  .map(([, t]) => stripCssComments(t))
  .join("\n");

const rule = (sel: string): string => {
  const esc = sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|\\})\\s*${esc}\\s*\\{([^}]*)\\}`, "m").exec(css);
  return m?.[1] ?? "";
};

describe("PanelTabs 量高度的那層不留在排版裡（PNL-1b 可修 2）", () => {
  it("量測外層 0 高、overflow hidden、看不見：量的時候也不撐大捲動區", () => {
    const r = rule(".pnl-measure-wrap");
    expect(r).toMatch(/height:\s*0/);
    expect(r).toMatch(/overflow:\s*hidden/);
    expect(r).toMatch(/visibility:\s*hidden/);
  });

  it("量測盒只在量的時候掛（量完卸下），而且一定包在 0 高的外層裡", () => {
    const code = stripTsComments(readFile(SRC_DIR, "ui/PanelTabs.tsx"));
    expect(code).toMatch(/\{measuring && \(\s*<div className="pnl-measure-wrap"[^>]*>\s*<div ref=\{measureBox\} className="pnl-measure">/);
    expect(code.match(/className="pnl-measure"/g)?.length).toBe(1);
    expect(code).toContain("setMeasuring(false)");
  });

  it("靜態輸出（沒在量）只有目前分頁，沒有量測層", () => {
    const tabs: PanelTabDef[] = [
      { id: "a", label: "甲頁", short: "甲", icon: null, render: () => createElement("p", null, "甲") },
      { id: "b", label: "乙頁", short: "乙", icon: null, render: () => createElement("p", null, "乙") },
    ];
    const out = renderToStaticMarkup(createElement(PanelTabs, { tabs }));
    expect(out).not.toContain("pnl-measure");
    expect(out).toContain('data-pane="a"');
  });
});
