// WL-1c（美術 PM `docs/art/WL-1b驗收.md` 的 WL-1c 節）：組裝列所有格子的名稱放不下就換行、最多兩行、兩行平均分配（「蓄力與／終結」），
// 兩行還放不下才在第二行尾巴「…」；格寬維持 44px。實際排版見 `docs/art/shots/wl-1c/wl1c-3-*`。
import { describe, expect, it } from "vitest";

// 沒有 @types/node：同 arX10StatusTip.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("WL-1c：組裝列格子名稱最多兩行", () => {
  it(".f-label：44px、換行、balance、兩行截斷，不再單行 nowrap", () => {
    const css = readFileSync("src/styles/workshop.css", "utf8");
    const block = /\.f-label \{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(block).toContain("max-width: 44px;");
    expect(block).toContain("white-space: normal;");
    expect(block).toContain("text-wrap: balance;");
    expect(block).toContain("-webkit-line-clamp: 2;");
    expect(block).not.toContain("nowrap");
    expect(css).toMatch(/\.f-tile \{[^}]*width: 44px;/);
  });
});
