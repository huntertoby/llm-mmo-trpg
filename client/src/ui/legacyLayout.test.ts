// 6A-4g：舊版戰鬥版面（右側窄欄 SidePanel、拖曳分隔線 ResizeHandle、欄寬／列高／主角卡寬設定與它們的 CSS）已刪，
// 這裡掃原始碼與樣式，確認沒有殘留引用（註解裡提到不算）。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀 CSS 檔
import { readFileSync, readdirSync } from "node:fs";

const stylesDir = new URL("../styles/", import.meta.url);
const styles: string = (readdirSync as (url: URL) => string[])(stylesDir)
  .filter((f) => f.endsWith(".css"))
  .sort()
  .map((f) => (readFileSync as (url: URL, enc: string) => string)(new URL(f, stylesDir), "utf8"))
  .join("\n")
  .replace(/\/\*[\s\S]*?\*\//g, "");

const sources = import.meta.glob<string>(["/src/**/*.tsx", "/src/**/*.ts", "!/src/**/*.d.ts", "!/src/**/*.test.ts"], {
  query: "?raw",
  import: "default",
  eager: true,
});
const strip = (text: string): string => text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
const files = Object.entries(sources).map(([path, text]) => [path.replace(/^\/src\//, ""), strip(text)] as const);

describe("舊版戰鬥版面已刪（6A-4g）", () => {
  it("沒有檔案引用 SidePanel、ResizeHandle 或舊的欄寬設定", () => {
    const words = /\b(SidePanel|ResizeHandle|layoutLimits|dragValue|sideWidth|heroWidth|layoutStyle)\b/;
    const bad = files.filter(([, text]) => words.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
    expect(Object.keys(sources).some((p) => /\/(SidePanel|ResizeHandle)\.tsx$/.test(p))).toBe(false);
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
