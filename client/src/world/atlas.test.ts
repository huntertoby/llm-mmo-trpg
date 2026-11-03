// Phase 6D-5：大世界圖（五區浮島＋中央主城、三種狀態、點了進區域圖、在城鎮或傳送石上點城鎮傳送）、
// M 的切換順序、主城的橋頭石碑選單與整備亭。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AtlasRegionView, AtlasView, WorldMapView, WorldView } from "../api/types";
import { AtlasMap } from "./AtlasMap";
import { atlasIslands, atlasMapOf, atlasNote, capitalIsland, capitalPanel, firstMapLayer, nextMapLayer, steleRegion } from "./atlasModel";
import { PavilionPanel, SteleMenu } from "./CapitalPanels";

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, ...over };
}

function map(regionId: string, name = regionId): WorldMapView {
  return { region: regionId, name_zh: name, level_zh: "", locations: [], edges: [], stones: [], can_teleport: false };
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
    expect(capitalIsland(a)).toMatchObject({ region: "capital", current: true, spot: { x: 50, y: 50 } });
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

describe("M 的切換", () => {
  it("區域圖 → 大世界圖 → 關閉；在主城直接開大世界圖", () => {
    const ridge = map("cloud_ridge");
    expect(nextMapLayer(null, ridge)).toBe("region");
    expect(nextMapLayer("region", ridge)).toBe("atlas");
    expect(nextMapLayer("atlas", ridge)).toBeNull();
    expect(firstMapLayer(map("capital"))).toBe("atlas");
    expect(nextMapLayer(null, map("capital"))).toBe("atlas");
  });
});

describe("主城的情境物件", () => {
  it("橋頭石碑對到區域；功能型 NPC 對到既有面板", () => {
    expect(steleRegion("stele_ashen_waste")).toBe("ashen_waste");
    expect(steleRegion("bridge_ashen_waste")).toBeNull();
    expect(capitalPanel("seal_keeper")).toBe("board");
    expect(capitalPanel("rift_projection")).toBe("board");
    expect(capitalPanel("shadow_league_desk")).toBe("league");
    expect(capitalPanel("loadout_pavilion")).toBe("pavilion");
    expect(capitalPanel("scribe")).toBe("skills");
    expect(capitalPanel("wishing_pool")).toBeNull(); // 許願還沒開放：照舊開說明卡
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
