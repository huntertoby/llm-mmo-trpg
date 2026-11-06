import { describe, expect, it } from "vitest";
import { BASE_LEGEND } from "./legend";
import { HIGHLIGHT } from "./glossary";

describe("legend (3-28)", () => {
  it("explains the exit and hold-point tiles with the same colours the renderer uses", () => {
    const exit = BASE_LEGEND.find((e) => e.label.includes("出口"));
    const point = BASE_LEGEND.find((e) => e.label.includes("守點"));
    expect(exit?.color).toBe(HIGHLIGHT.exit);
    expect(point?.color).toBe(HIGHLIGHT.point);
  });

  it("has no duplicate labels", () => {
    expect(new Set(BASE_LEGEND.map((e) => e.label)).size).toBe(BASE_LEGEND.length);
  });
});
