// 6F-ART1b：地景檔裡寫死的地點座標（樹、山避開地點用，含隱藏地點）要和 `content/world/maps/*.yaml` 的 pos 一致。
// 改了 yaml 忘了同步地景檔就失敗（docs/archive/art/6F-ART1檢查.md 第 2 節第 1 點）。
// 讀檔用 6C-R1 的 sourceScan（node 的 fs，在執行時讀目錄），不用 import.meta.glob，避免 vitest 快取把檔案清單凍結。
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { listFiles, readFile, SRC_DIR } from "../test/sourceScan";
import { POS as ASHEN_POS } from "./regionArtAshen";
import { POS as CLOUD_POS } from "./regionArtCloud";
import type { Pt } from "./regionMapArt";
import { REGION_ART } from "./regionMapPainter";

/** 有地景檔的區 → 地景檔裡寫死的 pos。新增地景檔時要登記在這裡（下面有測試檢查）。 */
const LANDSCAPE_POS: Readonly<Record<string, readonly Pt[]>> = {
  cloud_ridge: CLOUD_POS,
  ashen_waste: ASHEN_POS,
};

const MAPS_DIR = new URL("../../content/world/maps/", SRC_DIR);

interface YamlMap {
  region: string;
  locations?: { id: string; pos: { x: number; y: number } }[];
}

function yamlMaps(): YamlMap[] {
  return listFiles(MAPS_DIR, (p) => p.endsWith(".yaml") && !p.includes("/")).map((p) => parse(readFile(MAPS_DIR, p)) as YamlMap);
}

const key = ([x, y]: readonly [number, number]): string => `${x},${y}`;
const sorted = (pts: readonly (readonly [number, number])[]): string[] => pts.map(key).sort();

describe("地景檔的地點座標和內容檔一致", () => {
  const maps = yamlMaps();

  it("讀得到地圖內容檔", () => {
    expect(maps.map((m) => m.region)).toEqual(expect.arrayContaining(["cloud_ridge", "ashen_waste"]));
  });

  it("每個有地景檔的區都登記了寫死的座標", () => {
    expect(Object.keys(REGION_ART).sort()).toEqual(Object.keys(LANDSCAPE_POS).sort());
  });

  for (const [region, pos] of Object.entries(LANDSCAPE_POS)) {
    it(`${region}：地景檔的 pos 和 yaml 的全部地點（含隱藏）一模一樣`, () => {
      const m = maps.find((x) => x.region === region);
      if (m === undefined) throw new Error(`content/world/maps 裡沒有 ${region}`);
      const want = (m.locations ?? []).map((l) => [l.pos.x, l.pos.y] as const);
      expect(want.length).toBeGreaterThan(0);
      expect(sorted(pos)).toEqual(sorted(want));
    });
  }
});
