// TXT-2（`docs/phases/現代網頁指南試用.md` 第 C 項小修 1）：容器查詢一律指名。
// 沒有命名的 `@container` 會對到最近的容器祖先；以後中間多包一層 `container-type`，窄版判斷會悄悄改量那一層。
import { describe, expect, it } from "vitest";
import { readStyleFiles, stripCssComments } from "../test/sourceScan";

const styleFiles = readStyleFiles().map(([path, text]) => [path, stripCssComments(text)] as const);

describe("@container 一律指名", () => {
  it("沒有不帶名字的 @container", () => {
    const bad = styleFiles.filter(([, text]) => /@container\s*\(/.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("查詢用到的名字都有容器宣告", () => {
    const declared = new Set<string>();
    for (const [, text] of styleFiles) {
      for (const m of text.matchAll(/container(?:-name)?\s*:\s*([^;/]+?)\s*(?:\/|;)/g)) {
        for (const name of (m[1] ?? "").split(/\s+/)) if (name !== "" && name !== "none") declared.add(name);
      }
    }
    const used = styleFiles.flatMap(([, text]) => [...text.matchAll(/@container\s+([\w-]+)\s*\(/g)].map((m) => m[1] ?? ""));
    expect(used.length).toBeGreaterThan(0);
    expect(used.filter((n) => !declared.has(n))).toEqual([]);
    for (const name of ["fc", "mail", "world-panel"]) expect(declared.has(name), name).toBe(true);
  });
});
