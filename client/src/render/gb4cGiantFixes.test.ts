// GB-4c：巨型頭目與冷卻井的美術修正小段（美術 GB-4b 驗收、CW-1 驗收的美術 PM 裁定）。
import { describe, expect, it } from "vitest";
import type { Pos } from "../api/types";
import { hoverCellFrame } from "../battle/drawModel";
import { bodyRowName, partMenuRows } from "../battle/partMenu";
import { unit } from "../battle/testFixtures";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { popAt } from "./qBossGiant";

const P = (x: number, y: number): Pos => ({ x, y });
const tiles3 = (cx: number, cy: number): Pos[] => {
  const out: Pos[] = [];
  for (let y = cy - 1; y <= cy + 1; y++) for (let x = cx - 1; x <= cx + 1; x++) out.push(P(x, y));
  return out;
};

describe("必修 1：噴口「破」字放 (0, −140)，殼縫、核心不動", () => {
  it("位置（移植需求 5.4）", () => {
    expect(popAt("vent")).toEqual([0, -140]);
    expect(popAt("seam", -1)).toEqual([-57, -106]);
    expect(popAt("core")).toEqual([0, -114]);
  });
});

describe("待決 1：3×3 目標紅框在標示層內排最底", () => {
  it("部位格標示放 giantMarkTop，排在 attackTop（紅框）之後", () => {
    const hl = readFile(SRC_DIR, "render/battle/highlightLayer.ts");
    expect(hl).toContain("this.giantMarkTop.addChild(n)");
    expect(hl).toContain("clearLayer(this.giantMarkTop)");
    expect(hl).toContain("this.attackTop.addChild(giantTargetFrame(");
    const line = readFile(SRC_DIR, "render/BattleRenderer.ts")
      .split("\n")
      .find((l) => l.includes("this.world.addChild(this.rows.root"))!;
    expect(line.indexOf("this.giantMarkTop")).toBeGreaterThan(line.indexOf("this.attackTop"));
    expect(line.indexOf("this.giantMarkTop")).toBeLessThan(line.indexOf("this.hudTop"));
  });
});

describe("待決 8：選單本體列的字跟著頭目走", () => {
  it("巨型頭目＝「前殼（本體）」，1 格頭目＝「本體」", () => {
    const giant = unit("boss", "enemy", 5, 3, { footprint: 3, tiles: tiles3(5, 3), parts: [] });
    const mist = unit("mist", "enemy", 3, 3, { parts: [] });
    expect(bodyRowName(giant)).toBe("前殼（本體）");
    expect(bodyRowName(mist)).toBe("本體");
    expect(partMenuRows(giant, [])[0]!.name).toBe("前殼（本體）");
    expect(partMenuRows(mist, [])[0]!.name).toBe("本體");
  });
});

describe("可修 1：滑過巨型頭目不畫單格白框", () => {
  const giant = { x: 5, y: 3, footprint: 3, tiles: tiles3(5, 3), downed: false };
  const one = { x: 1, y: 1, downed: false };
  it("巨型頭目的 9 格都不畫；旁邊的格與 1 格單位照舊", () => {
    for (const t of tiles3(5, 3)) expect(hoverCellFrame([giant, one], t)).toBeNull();
    expect(hoverCellFrame([giant, one], P(1, 1))).toEqual(P(1, 1));
    expect(hoverCellFrame([giant, one], P(7, 3))).toEqual(P(7, 3));
    expect(hoverCellFrame([giant], null)).toBeNull();
  });
  it("倒下的巨型頭目照舊畫", () => {
    expect(hoverCellFrame([{ ...giant, downed: true }], P(5, 3))).toEqual(P(5, 3));
  });
});

describe("可修 2：核心破第 1 格白閃只用晶體", () => {
  it("白閃遮罩帶 crystal（不含殼窩）；滑過亮起照舊", () => {
    const src = readFile(SRC_DIR, "render/qBossGiant.ts");
    expect(src).toContain("const mask = giantPartMask(st, part, res, true);");
    expect(src).toContain('zone(g, "core", true);\n  cavity(g, S);\n  zone(g, "core");\n  core(g, S);');
    expect(src).toMatch(/giantGlowCanvas[\s\S]*?giantPartMask\(st, part, res\);/);
  });
});
