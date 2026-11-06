// Phase 6Q-1：酒館燈籠的光暈對準 townArt 畫的燈籠（6N-10 報告第 7 點；6D-ART2 改過屋頂列數之後）。
import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "../battle/geometry";
import { lanternLights } from "./ambientLayer";
import { paintBuilding } from "./capitalArt";
import { BUILDING_ART_T, BUILDING_KINDS, LANTERN_H, lanternCenters, type BuildingSpec } from "./townArt";

const T = TILE_SIZE;

/** 記下畫布上每個燈籠框（設了 shadowColor 之後的第一個 roundRect）的中心。 */
function drawnLanterns(s: BuildingSpec): { x: number; y: number }[] {
  const out: { x: number; y: number }[] = [];
  let armed = false;
  const ctx = new Proxy({} as Record<string, unknown>, {
    get(t, p: string) {
      if (p in t) return t[p];
      if (p === "createLinearGradient" || p === "createRadialGradient") return () => ({ addColorStop: () => undefined });
      return (...a: number[]) => {
        if (p === "roundRect" && armed) {
          out.push({ x: a[0]! + a[2]! / 2, y: a[1]! + a[3]! / 2 });
          armed = false;
        }
      };
    },
    set(t, p: string, v) {
      t[p] = v;
      if (p === "shadowColor" && v === "#ffcf6a") armed = true;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  paintBuilding(ctx, s);
  return out;
}

const TAVERNS: BuildingSpec[] = [
  { kind: "tavern", w: 5, h: 2, doors: [2] },
  { kind: "tavern", w: 5, h: 2, doors: [2], roof: 0 }, // 6D-ART2：屋後站人時屋頂讓位
  { kind: "tavern", w: 7, h: 3, doors: [1, 5] },
  { kind: "tavern", w: 6, h: 2, doors: [], sign: null },
];

describe("6Q-1：燈籠光暈對準燈籠", () => {
  it("畫燈籠和算光暈用同一組中心（屋頂讓位、換寬高、沒有招牌都一樣）", () => {
    for (const s of TAVERNS) {
      const drawn = drawnLanterns(s);
      expect(drawn.length, JSON.stringify(s)).toBeGreaterThan(0);
      expect(drawn).toEqual(lanternCenters(s));
    }
  });

  it("場景座標：照 sceneryLayer 放建築（左上＝(x, y − 屋頂列數) 格），跟著抬高；屋頂讓位不會讓光暈上下跑掉", () => {
    for (const s of TAVERNS) {
      const b = { x: 4, y: 6, spec: s };
      const lights = lanternLights(b, 0);
      const k = T / BUILDING_ART_T;
      const roof = s.roof ?? 1;
      expect(lights.map(({ x, y }) => ({ x, y }))).toEqual(lanternCenters(s).map((l) => ({ x: b.x * T + l.x * k, y: (b.y - roof) * T + l.y * k })));
      // 立面在建築最下一列往上 1.3 格，燈籠框中心再往下 2 + 6.5 px（和屋頂幾列無關）
      for (const l of lights) expect(l.y).toBeCloseTo((b.y + s.h - 1.3) * T + ((2 + LANTERN_H / 2) * T) / BUILDING_ART_T, 6);
      // 抬高：整組往上移
      expect(lanternLights(b, -10).map((l) => l.y)).toEqual(lights.map((l) => l.y - 10));
      // 閃動種子和 6N-10 一樣（燈籠所在的欄,建築的 y）
      for (const l of lights) expect(l.cell).toMatch(/^\d+(\.5)?,6$/);
    }
    const a = lanternLights({ x: 4, y: 6, spec: TAVERNS[0]! }, 0);
    const b = lanternLights({ x: 4, y: 6, spec: TAVERNS[1]! }, 0);
    expect(b).toEqual(a);
  });

  it("沒有燈籠的建築沒有光暈", () => {
    for (const kind of BUILDING_KINDS.filter((k) => k !== "tavern")) {
      const s: BuildingSpec = { kind, w: 5, h: 2, doors: [2] };
      expect(lanternCenters(s)).toEqual([]);
      expect(drawnLanterns(s)).toEqual([]);
      expect(lanternLights({ x: 0, y: 0, spec: s }, 0)).toEqual([]);
    }
  });
});
