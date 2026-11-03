// 6C-R1：掃原始碼工具本身的測試（去註解不誤吃字串／正則／JSX 文字；讀檔不靠 import.meta.glob）。
import { describe, expect, it } from "vitest";
import { listFiles, readSources, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "./sourceScan";

describe("stripTsComments", () => {
  it("去掉行註解與區塊註解，保留換行與位置", () => {
    const src = "const a = 1; // 說明 title=\n/* 多行\n title= */ const b = 2;\n";
    const out = stripTsComments(src, "x.ts");
    expect(out.length).toBe(src.length);
    expect(out.split("\n").length).toBe(src.split("\n").length);
    expect(out).not.toMatch(/title=|說明/);
    expect(out).toContain("const a = 1;");
    expect(out).toContain("const b = 2;");
  });

  it("字串、樣板字串、正則裡的 `/*`、`//` 不是註解，不會吃到下一個 `*/`", () => {
    const src = [
      'const s = "a /* b"; const keep1 = 1;',
      "const t = `x // y ${s /* 真的註解 */} /* z`; const keep2 = 2;",
      "const r = /\\/\\*/g; const keep3 = 3;",
      "// 這行 /* 不是區塊開頭",
      "const keep4 = 4; /* 結尾 */",
    ].join("\n");
    const out = stripTsComments(src, "x.ts");
    for (const k of ["keep1", "keep2", "keep3", "keep4", '"a /* b"', "x // y", "/* z`", "/\\/\\*/g"]) expect(out).toContain(k);
    expect(out).not.toMatch(/真的註解|這行|結尾/);
  });

  it("JSX 文字裡的 `//` 不是註解；`{/* */}` 是註解", () => {
    const src = 'const el = <div title="x">見 https://example.com 說明 {/* 註解 */}<b>//粗</b></div>;';
    const out = stripTsComments(src, "x.tsx");
    expect(out).toContain("https://example.com 說明");
    expect(out).toContain("//粗");
    expect(out).not.toContain("註解");
  });
});

describe("stripCssComments", () => {
  it("去掉 CSS 註解，字串裡的 `/*` 不算", () => {
    const css = '.a { content: "/*"; color: red; }\n/* .b { position: fixed; } */\n.c { z-index: 1; }';
    const out = stripCssComments(css);
    expect(out).toContain('content: "/*"; color: red;');
    expect(out).not.toContain(".b");
    expect(out).toContain(".c { z-index: 1; }");
  });
});

describe("讀檔", () => {
  it("遞迴讀到 src 底下各資料夾的原始碼與 CSS（含 world/*.css）", () => {
    const paths = readSources().map(([p]) => p);
    expect(paths).toContain("ui/floatCard.ts");
    expect(paths).toContain("dev/storyGallery.tsx");
    expect(paths.some((p) => p.endsWith(".test.ts"))).toBe(false);
    const css = readStyleFiles().map(([p]) => p);
    expect(css).toContain("styles/base.css");
    expect(css).toContain("world/story.css");
    expect(listFiles(SRC_DIR, (p) => p === "test/sourceScan.ts")).toEqual(["test/sourceScan.ts"]);
  });
});
