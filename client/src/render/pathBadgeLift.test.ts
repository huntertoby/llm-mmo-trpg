// E3b（美術 E3 驗收小修 2）：台階的高度標記「▲N」畫在路徑線上面，線本身不改。
import { describe, expect, it } from "vitest";
import type { PathDraw } from "../battle/pathPreview";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { pathLineCells } from "./pathArt";

const seg = (a: [number, number], b: [number, number]): PathDraw["segments"][number] => ({
  from: { x: a[0], y: a[1] },
  to: { x: b[0], y: b[1] },
  kind: "normal",
  possible: false,
  dashed: false,
});

describe("路徑線上的「▲N」", () => {
  it("路徑線經過的格子（每段兩端、不重複）", () => {
    expect(pathLineCells({ segments: [seg([0, 0], [1, 0]), seg([1, 0], [2, 0]), seg([2, 0], [2, 1])] })).toEqual([
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 2, y: 0 },
      { x: 2, y: 1 },
    ]);
    expect(pathLineCells({ segments: [] })).toEqual([]);
  });

  it("高亮層把這些格子的高度標記接到路徑線後面的 RenderLayer，清除前放回，重畫地形後再接", () => {
    const src = readFile(SRC_DIR, "render/battle/highlightLayer.ts");
    const line = src.indexOf("drawPathLine(g, path, geo);");
    const lift = src.indexOf("this.marks.addChild(this.pathBadgeTop);");
    const tags = src.indexOf("const nodes = path.tags.map((tag) => pathTagNode(tag));");
    expect(line).toBeGreaterThan(0);
    expect(lift).toBeGreaterThan(line);
    expect(tags).toBeGreaterThan(lift);
    expect(src.indexOf("this.dropPathBadges();")).toBeLessThan(src.indexOf("clearLayer(this.marks);"));
    expect(readFile(SRC_DIR, "render/BattleRenderer.ts")).toContain("this.liftPathBadges();");
    expect(readFile(SRC_DIR, "render/battle/terrainLayer.ts")).toContain("this.heightBadgeAt.set(posKey(t), node);");
  });
});
