// 6A-4g：舊版戰鬥版面（右側窄欄 SidePanel、拖曳分隔線 ResizeHandle、欄寬／列高／主角卡寬設定與它們的 CSS）已刪，
// 這裡掃原始碼與樣式，確認沒有殘留引用（註解裡提到不算）。
// 6C-R1：原始碼與 CSS（`src/**/*.css`）在執行時用 fs 讀（`test/sourceScan.ts`），不用 `import.meta.glob`（清單會被 vitest 快取）。
import { describe, expect, it } from "vitest";
import { readSources, readStyleFiles, stripCssComments, stripTsComments } from "../test/sourceScan";

const styles: string = readStyleFiles()
  .map(([, text]) => stripCssComments(text))
  .join("\n");

const sources = readSources();
const files = sources.map(([path, text]) => [path, stripTsComments(text, path)] as const);

describe("舊版戰鬥版面已刪（6A-4g）", () => {
  it("沒有檔案引用 SidePanel、ResizeHandle 或舊的欄寬設定", () => {
    expect(files.length).toBeGreaterThan(100);
    const words = /\b(SidePanel|ResizeHandle|layoutLimits|dragValue|sideWidth|heroWidth|layoutStyle)\b/;
    const bad = files.filter(([, text]) => words.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
    expect(sources.some(([p]) => /(^|\/)(SidePanel|ResizeHandle)\.tsx$/.test(p))).toBe(false);
  });

  it("樣式裡沒有舊的窄欄、分隔線、主角狀態卡欄與欄寬變數", () => {
    const bad = [/\.resize-handle\b/, /\.battle-side\b/, /\.side-toggle/, /\.side-telegraph\b/, /\.side-collapsed\b/, /\.battle-hero\b/, /--side-w\b/, /--hero-w\b/, /--bottom-h\b/].filter((re) => re.test(styles));
    expect(bad.map(String)).toEqual([]);
  });

  it("原始碼裡沒有舊版面的 class 名稱", () => {
    const names = /["'`. ](resize-handle|battle-side|side-toggle|side-telegraph|battle-hero)["'` ]/;
    const bad = files.filter(([, text]) => names.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
  });
});
