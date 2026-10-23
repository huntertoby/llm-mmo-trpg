// Phase 3-47：Hint 不產生任何外層元素（舊版外包 `<span class="hint-tip">` 會打斷 `父 > 子` 的 CSS）
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Hint, hintChild, isExpanded } from "./Hint";

const button = (props: Record<string, unknown> = {}) => createElement("button", { type: "button", className: "x", ...props }, "按鈕");

describe("Hint 不多包一層", () => {
  it("輸出與沒有 Hint 的子元素完全相同", () => {
    const bare = renderToStaticMarkup(button());
    expect(renderToStaticMarkup(createElement(Hint, { text: "說明", children: button() }))).toBe(bare);
  });
  it("在父元素底下，子元素仍是直接子節點", () => {
    const html = renderToStaticMarkup(createElement("div", { className: "p" }, createElement(Hint, { text: "說明", children: button() })));
    expect(html).toBe('<div class="p"><button type="button" class="x">按鈕</button></div>');
    expect(html).not.toContain("hint-tip");
  });
  it("text 為空時原樣回傳子元素", () => {
    const bare = renderToStaticMarkup(button());
    for (const text of [undefined, null, ""]) {
      expect(renderToStaticMarkup(createElement(Hint, { text, children: button() }))).toBe(bare);
    }
  });
  it("子元素不是單一 DOM 元素時給清楚的錯誤", () => {
    expect(() => hintChild([button(), button()])).toThrow("<Hint>");
    expect(() => hintChild("純文字")).toThrow("<Hint>");
    expect(() => hintChild(createElement(Hint, { text: "x", children: button() }))).toThrow("<Hint>");
    expect(hintChild(button()).type).toBe("button");
  });
});

describe("按鈕自己的選單開著", () => {
  it('aria-expanded 為 true／"true" 才算', () => {
    expect(isExpanded({ "aria-expanded": true })).toBe(true);
    expect(isExpanded({ "aria-expanded": "true" })).toBe(true);
    expect(isExpanded({ "aria-expanded": false })).toBe(false);
    expect(isExpanded({})).toBe(false);
  });
});
