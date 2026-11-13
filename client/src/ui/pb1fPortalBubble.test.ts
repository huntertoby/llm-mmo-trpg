// PB-1f（e3q）：portal 到 body 的說明卡，點一下（或焦點在卡上按鍵）會照 React 元件樹冒泡到外層的可點元素。
// PB-1e 修了 PartMenu；這裡鎖住同一類的其他三處都只認「DOM 真的在元素裡面」的事件（vitest 是 node 環境，沒有 DOM，用原始碼掃描）。
import { describe, expect, it } from "vitest";
import { readFile, SRC_DIR } from "../test/sourceScan";

describe("portal 說明卡的點擊不冒泡成外層動作", () => {
  it("閃現選項卡：點卡裡的術語說明卡不會選了那張；焦點在說明卡上按 Enter／方向鍵也不會", () => {
    const src = readFile(SRC_DIR, "screens/RunFlashPending.tsx");
    expect(src).toMatch(/const ownEvent = \(e: \{ target: EventTarget; currentTarget: EventTarget \}\): boolean => e\.target instanceof Node && e\.currentTarget instanceof Node && e\.currentTarget\.contains\(e\.target\);/u);
    expect(src).toMatch(/onClick=\{\(e\) => \{\s*if \(ownEvent\(e\)\) onPick\(\);\s*\}\}/u);
    expect(src).toMatch(/onKeyDown=\{\(e\) => \{\s*if \(ownEvent\(e\)\) onKey\(e\);\s*\}\}/u);
    expect(src).not.toMatch(/onClick=\{onPick\}/u);
  });
  it("浮動卡的觸發元素：卡片裡再開的說明卡冒泡上來的點擊不切換外層卡片（技能卡、技能列小格）", () => {
    const src = readFile(SRC_DIR, "ui/useFloatCard.tsx");
    expect(src).toMatch(/if \(inCard\(e\.target\)\) return;[^\n]*\n[^\n]*\n\s*if \(!\(e\.target instanceof Node\) \|\| triggerRef\.current\?\.contains\(e\.target\) !== true\) return;/u);
  });
  it("釘選單位停靠區：觸控點說明卡不會展開／收起停靠區", () => {
    expect(readFile(SRC_DIR, "ui/PinnedUnitDock.tsx")).toMatch(/e\.pointerType === "touch" && e\.target instanceof Node && e\.currentTarget\.contains\(e\.target\)/u);
  });
  it("PartMenu（PB-1e）照舊", () => {
    expect(readFile(SRC_DIR, "ui/PartMenu.tsx")).toMatch(/e\.currentTarget\.contains\(e\.target\)/u);
  });
});
