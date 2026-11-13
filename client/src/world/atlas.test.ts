// Phase 6D-5：大世界圖（五區浮島＋中央主城、三種狀態、點了進區域圖、在城鎮或傳送石上點城鎮傳送）、
// M 的切換順序、主城的橋頭石碑選單與整備亭。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AtlasRegionView, AtlasView, WorldMapView, WorldView } from "../api/types";
import { AtlasMap } from "./AtlasMap";
import { hereText, ISLAND_GEO, islandGeo } from "../render/worldMapArt";
import { atlasIslands, atlasMapOf, atlasNote, capitalIsland, firstMapLayer, nextMapLayer, objectHud } from "./atlasModel";
import { atlasScene, hereName } from "./atlasScene";
import { PavilionPanel, SteleMenu } from "./CapitalPanels";

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, free: false, ...over };
}

function map(regionId: string, name = regionId): WorldMapView {
  return { region: regionId, name_zh: name, level_zh: "", locations: [], edges: [], stones: [], can_teleport: false, hub: regionId === "capital" };
}

function atlas(over: Partial<AtlasView> = {}): AtlasView {
  return {
    regions: [
      region({ region: "cloud_ridge", name_zh: "雲嶺", town: "mist_ferry", town_name_zh: "霧渡鎮", can_teleport: true }),
      region({ region: "crystal_crown", name_zh: "晶冠城邦", status: "later", condition_zh: "之後的賽季" }),
      region({ region: "arcane_hub", name_zh: "魔導樞市", status: "later", condition_zh: "之後的賽季" }),
      region({ region: "ashen_waste", name_zh: "灰燼荒原", status: "locked", condition_zh: "世界事件：霧潮入侵", town: "ember_market", town_name_zh: "餘燼集" }),
      region({ region: "frost_tide", name_zh: "霜潮海境", status: "later", condition_zh: "之後的賽季" }),
    ],
    capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島", current: true }),
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
    maps: [map("cloud_ridge", "雲嶺")],
    ...over,
  };
}

describe("大世界圖的浮島", () => {
  it("五區照順序；已開放、未解鎖、之後的賽季各寫自己的字", () => {
    const islands = atlasIslands(atlas(), map("capital", "主城"));
    expect(islands.map((i) => i.region)).toEqual(["cloud_ridge", "crystal_crown", "arcane_hub", "ashen_waste", "frost_tide"]);
    const by = Object.fromEntries(islands.map((i) => [i.region, i]));
    expect(by.cloud_ridge).toMatchObject({ status: "open", caption: "霧渡鎮", canOpen: true, canTeleport: true });
    expect(by.ashen_waste).toMatchObject({ status: "locked", caption: "世界事件：霧潮入侵", canOpen: false, canTeleport: false });
    expect(by.frost_tide).toMatchObject({ status: "later", caption: "之後的賽季", canOpen: false });
    expect(by.ashen_waste?.hint).toContain("還沒解鎖");
  });

  it("主城在正中央；所在區的區域圖用 view.map，別區用 atlas.maps", () => {
    const a = atlas();
    expect(capitalIsland(a)).toMatchObject({ region: "capital", current: true });
    // 6D-R2：浮島位置只有 ISLAND_GEO 一份（主城在畫布正中附近）
    expect(atlasScene(a, map("capital")).scene.capital.geo).toBe(ISLAND_GEO.capital);
    const here = map("cloud_ridge", "雲嶺（所在）");
    expect(atlasMapOf(a, here, "cloud_ridge")).toBe(here);
    expect(atlasMapOf(a, map("capital"), "cloud_ridge")?.name_zh).toBe("雲嶺");
    expect(atlasMapOf(a, map("capital"), "ashen_waste")).toBeNull();
  });

  it("說明列：能傳送／只能看", () => {
    expect(atlasNote(atlas())).toContain("點已開放區的城鎮");
    expect(atlasNote(atlas({ can_teleport: false, teleport_problem_zh: "站在傳送石上或在城鎮裡打開地圖" }))).toContain("只能看");
  });

  it("畫面：已開放的區有傳送鈕，未解鎖寫條件，之後的賽季是灰色；自己的位置有圈", () => {
    const html = renderToStaticMarkup(
      createElement(AtlasMap, { atlas: atlas(), map: map("capital"), busy: false, onOpenRegion: () => undefined, onTeleport: () => undefined, onClose: () => undefined }),
    );
    expect(html).toContain('data-testid="atlas-teleport-cloud_ridge"');
    expect(html).toContain("傳送到霧渡鎮");
    expect(html).toContain('data-testid="atlas-condition-ashen_waste"');
    expect(html).toContain("世界事件：霧潮入侵");
    expect(html).toContain('data-status="later"');
    expect(html).toContain('data-testid="atlas-me"');
    expect(html).not.toContain("atlas-teleport-ashen_waste");
    expect(html).not.toContain("atlas-teleport-capital"); // 已經在主城
  });

  it("只能看的時候沒有傳送鈕", () => {
    const a = atlas({ can_teleport: false, regions: atlas().regions.map((r) => ({ ...r, can_teleport: false })) });
    const html = renderToStaticMarkup(
      createElement(AtlasMap, { atlas: a, map: map("cloud_ridge"), busy: false, onOpenRegion: () => undefined, onTeleport: () => undefined, onClose: () => undefined }),
    );
    expect(html).not.toContain("atlas-teleport-");
    expect(html).toContain("霧渡鎮");
  });
});

describe("你在〇〇（6F-3 巡檢 bug 5）", () => {
  const loc = (id: string, name_zh: string, current: boolean) =>
    ({ id, name_zh, kind: "camp", kind_zh: "營地", level_zh: null, description_zh: "", x: 0, y: 0, current, adjacent: false, blocked_zh: null, cleared: false, hidden: false }) as WorldMapView["locations"][number];
  const ashen = (): WorldMapView => ({ ...map("ashen_waste", "灰燼荒原"), locations: [loc("ember_market", "餘燼集", false), loc("ash_ferry", "灰渡口", true)] });
  const a = atlas({
    regions: atlas().regions.map((r) => (r.region === "ashen_waste" ? { ...r, status: "open" as const, current: true } : { ...r, current: false })),
    capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島" }),
  });

  it("荒原站在灰渡口：寫灰渡口，不是固定寫餘燼集", () => {
    const art = atlasScene(a, ashen()).scene.islands.find((i) => i.region === "ashen_waste");
    expect(art).toBeDefined();
    expect(hereText(art!)).toBe("你在灰渡口");
  });

  it("不是所在區、或區域圖沒有 current：照舊寫城鎮名", () => {
    expect(hereName(ashen(), { region: "cloud_ridge", current: true })).toBeUndefined();
    expect(hereName(ashen(), { region: "ashen_waste", current: false })).toBeUndefined();
    const art = atlasScene(a, map("ashen_waste")).scene.islands.find((i) => i.region === "ashen_waste");
    expect(hereText(art!)).toBe("你在餘燼集");
  });
});

describe("M 的切換", () => {
  it("區域圖 → 大世界圖 → 關閉；在主城直接開大世界圖", () => {
    const ridge = map("cloud_ridge");
    expect(nextMapLayer(null, ridge)).toBe("region");
    expect(nextMapLayer("region", ridge)).toBe("atlas");
    expect(nextMapLayer("atlas", ridge)).toBeNull();
    expect(firstMapLayer(map("capital"))).toBe("atlas");
    expect(nextMapLayer(null, map("capital"))).toBe("atlas");
    // 6D-R2：看伺服器給的 hub，不看區域 ID
    expect(firstMapLayer({ ...map("capital"), hub: false })).toBe("region");
    expect(firstMapLayer({ ...map("elsewhere"), hub: true })).toBe("atlas");
  });
});

describe("主城的情境物件", () => {
  it("橋頭石碑對到區域；功能型 NPC 對到既有面板（6D-R2：讀伺服器給的 stele_region／panel）", () => {
    expect(objectHud({ stele_region: "ashen_waste", panel: null })).toEqual({ panel: "stele", who: "ashen_waste" });
    expect(objectHud({ stele_region: null, panel: "board" })).toEqual({ panel: "board", who: null });
    expect(objectHud({ panel: "league" })).toEqual({ panel: "league", who: null });
    expect(objectHud({ panel: "pavilion" })).toEqual({ panel: "pavilion", who: null });
    expect(objectHud({ panel: "skills" })).toEqual({ panel: "skills", who: null });
    expect(objectHud({})).toBeNull(); // 浮橋等一般物件：照舊開說明卡
    expect(objectHud({ panel: "wish" })).toBeNull(); // WP-2：許願池面板在 WP-3 接上前照舊開說明卡
    expect(objectHud(null)).toBeNull();
    // 物件 ID 叫 stele_ 也不算，要有 stele_region
    expect(objectHud({ stele_region: null, panel: null })).toBeNull();
  });

  it("表裡沒有的區沿外圈排", () => {
    const geo = islandGeo("new_region", 0);
    expect(geo.kind).toBe("new_region");
    expect(geo.x).toBeGreaterThan(ISLAND_GEO.capital?.x ?? 0);
  });

  function view(over: Partial<WorldView> = {}): WorldView {
    return {
      atlas: atlas(),
      character: { hp: 10, max_hp: 40, mana: 3, max_mana: 17 },
      here: { can_rest: true, can_loadout: true },
      inventory: {},
      ...over,
    } as unknown as WorldView;
  }

  it("石碑三種狀態：已開放有傳送鈕、未解鎖寫條件、之後的賽季", () => {
    const render = (r: string) =>
      renderToStaticMarkup(createElement(SteleMenu, { view: view(), region: r, busy: false, onAct: () => undefined, onClose: () => undefined }));
    const open = render("cloud_ridge");
    expect(open).toContain('data-status="open"');
    expect(open).toContain("傳送到霧渡鎮");
    const locked = render("ashen_waste");
    expect(locked).toContain('data-status="locked"');
    expect(locked).toContain("未解鎖：世界事件：霧潮入侵");
    expect(locked).not.toContain("world-stele-teleport");
    const later = render("frost_tide");
    expect(later).toContain('data-status="later"');
    expect(later).toContain("之後的賽季");
    expect(later).not.toContain("world-stele-teleport");
  });

  it("整備亭：休息、換技能、配點、換裝", () => {
    const html = renderToStaticMarkup(createElement(PavilionPanel, { view: view(), busy: false, onAct: () => undefined, onPanel: () => undefined }));
    for (const id of ["rest", "skills", "growth", "bag"]) expect(html).toContain(`data-testid="world-pavilion-${id}"`);
    expect(html).toContain("HP 10 / 40");
  });
});
