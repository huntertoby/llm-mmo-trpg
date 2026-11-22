// E3b（美術 E4 驗收末節）：所有用「・」分點的說明框都懸掛縮排，共用 `part-tip-bullet`。
import { describe, expect, it } from "vitest";
import { createElement, Fragment, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { actionCardText, actionHint } from "../battle/actionInfo";
import { stackHintText } from "../battle/stackInfo";
import { glossaryEntry } from "../battle/glossary";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { BULLET_CLASS, bulletLines } from "./bulletText";
import { hintBody } from "./Hint";

const html = (n: ReactNode): string => renderToStaticMarkup(createElement(Fragment, null, n));

describe("「・」分點的懸掛縮排", () => {
  it("切成行，「・」開頭的標成分點；沒有分點時照舊", () => {
    expect(bulletLines("移動\n・每格 1 點\n・可以分段")).toEqual([
      { text: "移動", bullet: false },
      { text: "・每格 1 點", bullet: true },
      { text: "・可以分段", bullet: true },
    ]);
    expect(bulletLines("一句話說明")).toBeNull();
    expect(bulletLines("A・B 中間的點不算")).toBeNull();
  });

  it("Hint 的說明：分點的行套 part-tip-bullet", () => {
    const text = actionHint("move");
    expect(text).not.toBeNull();
    const out = html(hintBody(text as string));
    const bullets = (text as string).split("\n").filter((l) => l.startsWith("・")).length;
    expect(bullets).toBeGreaterThan(0);
    expect(out.match(new RegExp(`class="${BULLET_CLASS}"`, "g"))?.length).toBe(bullets);
    expect(html(hintBody("沒有分點"))).toBe("沒有分點");
  });

  it("套到的說明框：動作（按鈕、狀態列）、層數、倒地；CSS 只有一條規則", () => {
    // 動作說明（actionInfo.ts）：Hint（TurnControls、狀態列 statusCard）
    expect(actionCardText("move")).toMatch(/\n・/);
    // 層數說明（stackInfo.ts）：PartTip 的 tip
    expect((glossaryEntry("stacks", "focus")?.rules_zh ?? []).length).toBeGreaterThan(0);
    expect(stackHintText("focus")).toMatch(/\n・/);
    const hint = readFile(SRC_DIR, "ui/Hint.tsx");
    expect(hint).toContain("hintBody(text");
    const partTip = readFile(SRC_DIR, "ui/PartTip.tsx");
    expect(partTip).toContain("tipBody(tip)");
    expect(partTip).toContain('p.bullet === true ? " part-tip-bullet"'); // E4b 倒地照舊
    const css = readFile(SRC_DIR, "styles/float-card.css");
    expect(css.match(/part-tip-bullet/g)?.length).toBe(1);
    expect(css).toMatch(/\.part-tip-bullet \{\s*padding-left: 1em;\s*text-indent: -1em;\s*\}/);
  });
});
