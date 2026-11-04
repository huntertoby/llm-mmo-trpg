// 6B-ART1：建築、門、室內、家具的畫法——確定性（同樣輸入畫出一模一樣的指令序列）、不寫字（招牌只畫圖示）、種類之間畫法不同。
import { describe, expect, it } from "vitest";
import { BUILDING_KINDS, doorFrame, doorPanel, drawBuilding, entrance, type BuildingSpec } from "./townArt";
import { drawBackWall, drawExitCell, drawFloor, drawFurniture, drawWallCell, FURNITURE_LOOKS, roomPalette, wallDecor } from "./interiorArt";

function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const ctx = new Proxy({} as Record<string, unknown>, {
    get(t, p: string) {
      if (p in t) return t[p];
      if (p === "createLinearGradient" || p === "createRadialGradient") return (...a: unknown[]) => (calls.push(`${p}(${a.join(",")})`), { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) });
      return (...a: unknown[]) => void calls.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(2) : String(x))).join(",")})`);
    },
    set(t, p: string, v) {
      t[p] = v;
      calls.push(`${p}=${String(v)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

function calls(draw: (c: CanvasRenderingContext2D) => void): string[] {
  const r = recorder();
  draw(r.ctx);
  return r.calls;
}

const noText = (c: string[]) => !c.some((x) => x.startsWith("fillText") || x.startsWith("strokeText"));

describe("6B-ART1：建築與門的畫法", () => {
  const specs: BuildingSpec[] = BUILDING_KINDS.map((kind) => ({ kind, w: 6, h: 4, doors: [2] }));

  it.each(specs)("$kind：確定性、不寫字", (s) => {
    const a = calls((c) => drawBuilding(c, s));
    expect(a.length).toBeGreaterThan(30);
    expect(a).toEqual(calls((c) => drawBuilding(c, s)));
    expect(noText(a)).toBe(true);
  });

  it("六種外觀彼此不同；同一種的門位置不同畫法也不同（窗、招牌跟著門）", () => {
    const all = specs.map((s) => calls((c) => drawBuilding(c, s)).join("|"));
    expect(new Set(all).size).toBe(specs.length);
    expect(calls((c) => drawBuilding(c, { kind: "tavern", w: 6, h: 4, doors: [4] }))).not.toEqual(calls((c) => drawBuilding(c, specs[0]!)));
  });

  it("門框、門板、入口光圈：確定性、木門和布簾門不同", () => {
    for (const style of ["wood", "rag"] as const) {
      expect(calls((c) => doorFrame(c, 26, 52, style))).toEqual(calls((c) => doorFrame(c, 26, 52, style)));
      expect(calls((c) => doorPanel(c, 14, 52, style))).toEqual(calls((c) => doorPanel(c, 14, 52, style)));
    }
    expect(calls((c) => doorPanel(c, 14, 52, "wood"))).not.toEqual(calls((c) => doorPanel(c, 14, 52, "rag")));
    expect(calls((c) => entrance(c, 26, 23)).length).toBeGreaterThan(5);
  });
});

describe("6B-ART1：室內的畫法", () => {
  const town = roomPalette("tavern", "town");
  const ashen = roomPalette("tavern", "ashen");

  it("地板、牆邊、出口、後牆：確定性；荒原配色不同", () => {
    expect(calls((c) => drawFloor(c, 3, 4, town, null))).toEqual(calls((c) => drawFloor(c, 3, 4, town, null)));
    expect(calls((c) => drawFloor(c, 3, 4, town, null))).not.toEqual(calls((c) => drawFloor(c, 3, 4, ashen, null)));
    expect(calls((c) => drawFloor(c, 3, 4, roomPalette("mentor", "town"), { n: true, e: false, s: false, w: true })).some((x) => x.includes("#8a2f3a"))).toBe(true); // 紅地毯
    expect(calls((c) => drawWallCell(c, { n: true, e: false, w: false }, town))).toEqual(calls((c) => drawWallCell(c, { n: true, e: false, w: false }, town)));
    expect(calls((c) => drawExitCell(c, 4, 7, town)).some((x) => x.startsWith("setLineDash"))).toBe(true); // 入口光圈的虛線
    for (const kind of ["tavern", "smithy", "mentor"] as const) {
      const decor = wallDecor(kind, 10, []);
      const a = calls((c) => drawBackWall(c, 10, roomPalette(kind, "town"), decor));
      expect(a).toEqual(calls((c) => drawBackWall(c, 10, roomPalette(kind, "town"), decor)));
      expect(noText(a)).toBe(true);
    }
  });

  it.each(FURNITURE_LOOKS.map((look) => [look]))("家具 %s：確定性、不寫字", (look) => {
    const spec = { look, joinW: false, joinE: false };
    const a = calls((c) => drawFurniture(c, spec));
    expect(a.length).toBeGreaterThan(5);
    expect(a).toEqual(calls((c) => drawFurniture(c, spec)));
    expect(noText(a)).toBe(true);
  });

  it("十種家具畫法彼此不同；吧檯接成一條時兩端不畫封邊", () => {
    const all = FURNITURE_LOOKS.map((look) => calls((c) => drawFurniture(c, { look, joinW: false, joinE: false })).join("|"));
    expect(new Set(all).size).toBe(FURNITURE_LOOKS.length);
    const lone = calls((c) => drawFurniture(c, { look: "bar", joinW: false, joinE: false }));
    const mid = calls((c) => drawFurniture(c, { look: "bar", joinW: true, joinE: true }));
    expect(mid.length).toBeLessThan(lone.length);
  });
});
