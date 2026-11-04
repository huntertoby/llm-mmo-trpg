// 6D-ART2：主城建築與街景的畫法——確定性（同樣輸入畫出一模一樣的指令序列）、不寫字、種類與狀態之間畫法不同。
import { describe, expect, it } from "vitest";
import { drawBanner, drawCrystalLamp, drawPortalPillar, drawPortalRing, drawSkyBridge, drawStele, paintBuilding, REGION_COLOR, REGION_ORDER, regionColor, LOCKED_COLOR } from "./capitalArt";
import { bridgeRails, drawFurniture, furnitureKey } from "./interiorArt";
import { buildingArtKey, signOf, type BuildingSpec } from "./townArt";
import { REGION_TERRAIN_DRAW } from "./terrainArt";

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

function same(draw: (c: CanvasRenderingContext2D) => void): string[] {
  const a = calls(draw);
  expect(a.length).toBeGreaterThan(10);
  expect(a).toEqual(calls(draw));
  expect(noText(a)).toBe(true);
  return a;
}

describe("6D-ART2：主城建築", () => {
  const specs: BuildingSpec[] = [
    { kind: "mentor_hall", w: 5, h: 4, doors: [2], sign: "scroll" },
    { kind: "stone_hall", w: 4, h: 4, doors: [3], sign: "jar" },
    { kind: "stone_hall", w: 4, h: 3, doors: [0], sign: "anvil" },
    { kind: "tent", w: 2, h: 2, doors: [] },
    { kind: "fountain", w: 2, h: 2, doors: [], roof: 0 },
  ];

  it.each(specs)("$kind $w×$h：確定性、不寫字", (s) => {
    same((c) => paintBuilding(c, s));
  });

  it("每一棟的畫法彼此不同；導師殿有晶尖塔（多一次發光）；招牌不同畫法不同", () => {
    const all = specs.map((s) => calls((c) => paintBuilding(c, s)).join("|"));
    expect(new Set(all).size).toBe(specs.length);
    const hall = { kind: "stone_hall", w: 5, h: 4, doors: [2], sign: "scroll" } as const;
    const glows = (s: BuildingSpec) => calls((c) => paintBuilding(c, s)).filter((x) => x.startsWith("createRadialGradient")).length;
    expect(glows(specs[0]!)).toBeGreaterThan(glows(hall));
    expect(calls((c) => paintBuilding(c, { ...hall, sign: "jar" }))).not.toEqual(calls((c) => paintBuilding(c, hall)));
    expect(calls((c) => paintBuilding(c, { ...hall, sign: null }))).not.toEqual(calls((c) => paintBuilding(c, hall)));
  });

  it("屋頂不往上蓋（roof 0）時畫法與快取鍵都不同；招牌進快取鍵", () => {
    const up: BuildingSpec = { kind: "house", w: 4, h: 3, doors: [] };
    const flat: BuildingSpec = { ...up, roof: 0 };
    expect(calls((c) => paintBuilding(c, flat))).not.toEqual(calls((c) => paintBuilding(c, up)));
    expect(buildingArtKey(up)).toBe("bld|house|4x3|");
    expect(buildingArtKey(flat)).toBe("bld|house|4x3||r0");
    expect(buildingArtKey({ kind: "scrap_house", w: 6, h: 4, doors: [2], sign: "jar" })).toBe("bld|scrap_house|6x4|2|sjar");
    expect(buildingArtKey({ kind: "scrap_house", w: 6, h: 4, doors: [2], sign: null })).toBe("bld|scrap_house|6x4|2|s-");
  });

  it("廢鐵屋、鍛爐屋的招牌照門通往的室內（開發 PM 補充 2）：有 sign 才掛", () => {
    const base: BuildingSpec = { kind: "scrap_house", w: 6, h: 4, doors: [2] };
    expect(signOf(base)).toBeNull();
    expect(signOf({ kind: "forge_house", w: 6, h: 4, doors: [2] })).toBeNull();
    expect(signOf({ ...base, sign: "jar" })).toBe("jar");
    expect(calls((c) => paintBuilding(c, { ...base, sign: "jar" }))).not.toEqual(calls((c) => paintBuilding(c, base)));
    expect(signOf({ kind: "tavern", w: 6, h: 4, doors: [2] })).toBe("jar"); // 霧渡鎮的白牆屋舍照種類
  });
});

describe("6D-ART2：傳送陣、區旗與街景", () => {
  it("傳送陣：確定性；光圈的顏色照開放狀態（開放＝該區顏色、沒開放＝灰色）", () => {
    const none = same((c) => drawPortalRing(c, []));
    const two = same((c) => drawPortalRing(c, ["ashen_waste", "cloud_ridge"]));
    expect(two).not.toEqual(none);
    const strokes = (a: string[]) => a.filter((x) => x.startsWith("strokeStyle="));
    expect(strokes(none).filter((x) => x === `strokeStyle=${LOCKED_COLOR}`)).toHaveLength(5);
    expect(strokes(two)).toContain(`strokeStyle=${REGION_COLOR.cloud_ridge}`);
    expect(strokes(two)).toContain(`strokeStyle=${REGION_COLOR.ashen_waste}`);
    expect(strokes(two).filter((x) => x === `strokeStyle=${LOCKED_COLOR}`)).toHaveLength(3);
    same((c) => drawPortalPillar(c));
  });

  it("五面區旗：五區各一面、顏色不同（晶冠紫、雲嶺綠、樞市青、灰燼橘、霜潮藍）", () => {
    expect(REGION_ORDER).toEqual(["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"]);
    const all = REGION_ORDER.map((r) => same((c) => drawBanner(c, r)).join("|"));
    expect(new Set(all).size).toBe(5);
    expect(new Set(Object.values(REGION_COLOR)).size).toBe(5);
    expect(regionColor("nowhere")).toBe(LOCKED_COLOR);
  });

  it("源晶燈、橋頭石碑（各區紋章不同）、浮橋（四個方向、繩欄）：確定性、不寫字", () => {
    same((c) => drawCrystalLamp(c));
    const steles = REGION_ORDER.map((r) => same((c) => drawStele(c, r)).join("|"));
    expect(new Set(steles).size).toBe(5);
    const sides = (["n", "e", "s", "w"] as const).map((s) => same((c) => drawSkyBridge(c, s, true, true)).join("|"));
    expect(new Set(sides).size).toBe(4);
    expect(calls((c) => drawSkyBridge(c, "n", true, false)).length).toBeLessThan(calls((c) => drawSkyBridge(c, "n", true, true)).length);
  });

  it("家具外觀接上主城街景：石碑的區域、浮橋的方向進快取鍵；浮橋的繩欄照方向換算", () => {
    expect(calls((c) => drawFurniture(c, { look: "stele", joinW: false, joinE: false, region: "frost_tide" }))).toEqual(calls((c) => drawStele(c, "frost_tide")));
    expect(furnitureKey({ look: "stele", joinW: false, joinE: false, region: "frost_tide" })).toBe("fur|stele|00|frost_tide");
    expect(furnitureKey({ look: "sky_bridge", joinW: true, joinE: false, side: "w" })).toBe("fur|sky_bridge|10|w");
    expect(furnitureKey({ look: "barrel", joinW: false, joinE: false })).toBe("fur|barrel|00"); // 6B-ART1 的鍵不變
    // 北橋：左＝西；東橋：左＝北；南橋：左＝東；西橋：左＝南
    expect(bridgeRails({ look: "sky_bridge", joinW: false, joinE: true, side: "n" })).toEqual({ left: true, right: false });
    expect(bridgeRails({ look: "sky_bridge", joinW: false, joinE: true, side: "e" })).toEqual({ left: true, right: false });
    expect(bridgeRails({ look: "sky_bridge", joinW: false, joinE: true, side: "s" })).toEqual({ left: false, right: true });
    expect(bridgeRails({ look: "sky_bridge", joinW: false, joinE: true, side: "w" })).toEqual({ left: false, right: true });
  });

  it("主城的地面：只有石板換成晶冠的白石板（其他地形照預設）", () => {
    expect(Object.keys(REGION_TERRAIN_DRAW["capital"] ?? {})).toEqual(["stone"]);
  });
});
