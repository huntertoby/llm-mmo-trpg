// 6D-ART2：主城的只畫外觀（建築、側牆的門、傳送陣、街景）與開發 PM 補充三項（屋頂不往上蓋、招牌照室內、建築的門不畫門框）。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { roofCovers } from "../render/sceneryModel";
import { fieldScenery, openRegionsOf } from "./fieldScenery";
import { fieldHighlights, hoverText } from "./fieldModel";

function base(over: Partial<FieldView> = {}): FieldView {
  return {
    map_id: "x",
    name_zh: "x",
    region: "cloud_ridge",
    location: "x",
    interior: false,
    width: 24,
    height: 18,
    tiles: [],
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    npcs: [],
    facilities: [],
    me: { x: 11, y: 9, facing: "s" },
    max_climb: 1,
    hero: null,
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [],
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    footprints: [],
    buildings: [],
    chasm_style: "default",
    decor: [],
    ...over,
  } as FieldView;
}

/** 主城（capital.yaml 的節錄）：建築、三扇門、傳送石、街景物件、橋頭石碑。 */
function capital(over: Partial<FieldView> = {}): FieldView {
  return base({
    map_id: "capital",
    name_zh: "樞島",
    region: "capital",
    location: "capital",
    width: 32,
    height: 24,
    buildings: [
      { kind: "mentor_hall", x: 13, y: 1, width: 5, height: 4, sign: "scroll" },
      { kind: "stone_hall", x: 2, y: 9, width: 4, height: 4, sign: "jar" },
      { kind: "stone_hall", x: 25, y: 10, width: 4, height: 3, sign: "anvil" },
      { kind: "tent", x: 12, y: 19, width: 2, height: 2, sign: null },
      { kind: "fountain", x: 4, y: 3, width: 2, height: 2, sign: null },
    ],
    doors: [
      { id: "mentor_hall_door", x: 15, y: 4, to: "capital_mentor_hall", to_name_zh: "技能導師殿" },
      { id: "tavern_door", x: 5, y: 11, to: "capital_tavern", to_name_zh: "樞島酒館" },
      { id: "smithy_door", x: 25, y: 11, to: "capital_smithy", to_name_zh: "樞島鐵匠鋪" },
    ],
    stones: [{ id: "stone_capital", x: 15, y: 11, unlocked: true }],
    objects: [
      { id: "o9_0", kind: "wooden_bridge", x: 9, y: 0, look: "sky_bridge" },
      { id: "o10_0", kind: "wooden_bridge", x: 10, y: 0, look: "sky_bridge" },
      { id: "o0_15", kind: "wooden_bridge", x: 0, y: 15, look: "sky_bridge" },
      { id: "o0_16", kind: "wooden_bridge", x: 0, y: 16, look: "sky_bridge" },
      { id: "o11_1", kind: "stone_pillar", x: 11, y: 1, look: "stele" },
      { id: "o11_9", kind: "stone_pillar", x: 11, y: 9, look: "crystal_lamp" },
      { id: "o17_10", kind: "stone_pillar", x: 17, y: 10 },
    ],
    situation_objects: [{ id: "stele_crystal_crown", name_zh: "石碑", x: 11, y: 1, use: "note", usable: true, note_zh: "", stele_region: "crystal_crown" }],
    ...over,
  } as Partial<FieldView>);
}

describe("6D-ART2：主城的建築與門", () => {
  it("建築照內容；最下一列的門畫在原地，側牆的門畫在同一欄的最下一列、入口光圈在外側", () => {
    const s = fieldScenery(capital());
    expect(s.buildings.map((b) => [b.spec.kind, b.x, b.y, b.spec.w, b.spec.h, b.spec.doors, b.spec.sign])).toEqual([
      ["mentor_hall", 13, 1, 5, 4, [2], "scroll"],
      ["stone_hall", 2, 9, 4, 4, [3], "jar"],
      ["stone_hall", 25, 10, 4, 3, [0], "anvil"],
      ["tent", 12, 19, 2, 2, [], undefined],
      ["fountain", 4, 3, 2, 2, [], undefined],
    ]);
    expect(s.doors).toEqual([
      { x: 15, y: 4, style: "wood" },
      { x: 5, y: 11, style: "wood", side: "e", drawY: 12 },
      { x: 25, y: 11, style: "wood", side: "w", drawY: 12 },
    ]);
    expect(s.buildings.find((b) => b.spec.kind === "fountain")!.spec.roof).toBe(0); // 噴水池是平的
    expect(s.buildings.find((b) => b.spec.kind === "mentor_hall")!.spec.roof).toBeUndefined();
  });

  it("中央傳送陣在傳送石那格；光圈照大世界圖已開放的區（排序、去重）；其他地圖沒有", () => {
    expect(fieldScenery(capital(), ["ashen_waste", "cloud_ridge", "ashen_waste"]).plaza).toEqual({ x: 15, y: 11, open: ["ashen_waste", "cloud_ridge"] });
    expect(fieldScenery(capital()).plaza).toEqual({ x: 15, y: 11, open: [] });
    expect(fieldScenery(capital({ interior: true })).plaza ?? null).toBeNull();
    expect(fieldScenery(base({ stones: [{ id: "s", x: 3, y: 3, unlocked: true }] }), ["cloud_ridge"]).plaza ?? null).toBeNull();
    const atlas = {
      regions: [
        { region: "frost_tide", status: "locked" },
        { region: "cloud_ridge", status: "open" },
        { region: "ashen_waste", status: "open" },
        { region: "crystal_crown", status: "later" },
      ],
    };
    expect(openRegionsOf(atlas)).toEqual(["ashen_waste", "cloud_ridge"]);
    expect(openRegionsOf(null)).toEqual([]);
  });

  it("街景物件：浮橋的方向與相連、石碑的紋章區域、源晶燈；沒有 look 的石柱照原本畫", () => {
    const f = fieldScenery(capital()).furniture;
    expect(f["9,0"]).toEqual({ look: "sky_bridge", joinW: false, joinE: true, side: "n" });
    expect(f["10,0"]).toEqual({ look: "sky_bridge", joinW: true, joinE: false, side: "n" });
    expect(f["0,15"]).toEqual({ look: "sky_bridge", joinW: false, joinE: true, side: "w" }); // 東西向：joinW＝北鄰、joinE＝南鄰
    expect(f["0,16"]).toEqual({ look: "sky_bridge", joinW: true, joinE: false, side: "w" });
    expect(f["11,1"]).toEqual({ look: "stele", joinW: false, joinE: false, region: "crystal_crown" });
    expect(f["11,9"]).toEqual({ look: "crystal_lamp", joinW: false, joinE: false });
    expect(f["17,10"]).toBeUndefined();
  });

  it("確定性：同一份資料每次的外觀都一樣", () => {
    expect(fieldScenery(capital(), ["cloud_ridge"])).toEqual(fieldScenery(capital(), ["cloud_ridge"]));
  });
});

describe("開發 PM 補充（6B-ART1 驗收）", () => {
  const mist = (over: Partial<FieldView> = {}) =>
    base({
      map_id: "mist_ferry",
      buildings: [
        { kind: "tavern", x: 1, y: 2, width: 6, height: 4 },
        { kind: "house", x: 10, y: 14, width: 4, height: 3 },
      ],
      doors: [
        { id: "tavern_door", x: 3, y: 5, to: "mist_ferry_tavern", to_name_zh: "霧渡鎮酒館" },
        { id: "gate", x: 20, y: 9, to: "hidden_place", to_name_zh: "密林" },
      ],
      ...over,
    } as Partial<FieldView>);

  it("1. 屋後那一列站著 NPC、設施、情境物件或傳送石：屋頂不往上蓋，那裡的人不被蓋住；路過的玩家照舊有剪影", () => {
    const plain = fieldScenery(mist());
    expect(roofCovers(plain, { x: 11, y: 13 })).toBe(true);
    const granny = fieldScenery(mist({ npcs: [{ id: "ferry_granny", name_zh: "渡婆", x: 11, y: 13 }] } as Partial<FieldView>));
    const house = granny.buildings.find((b) => b.spec.kind === "house")!;
    expect(house.spec.roof).toBe(0);
    expect(roofCovers(granny, { x: 11, y: 13 })).toBe(false);
    expect(roofCovers(granny, { x: 3, y: 1 })).toBe(true); // 別棟照舊
    expect(granny.buildings.find((b) => b.spec.kind === "tavern")!.spec.roof).toBeUndefined();
    for (const over of [
      { facilities: [{ kind: "shop", x: 13, y: 13 }] },
      { situation_objects: [{ id: "o", name_zh: "o", x: 10, y: 13, use: "note", usable: true, note_zh: "" }] },
      { stones: [{ id: "s", x: 12, y: 13, unlocked: false }] },
    ] as Partial<FieldView>[]) {
      expect(fieldScenery(mist(over)).buildings[1]!.spec.roof).toBe(0);
    }
    expect(fieldScenery(mist({ npcs: [{ id: "n", name_zh: "n", x: 14, y: 13 }] } as Partial<FieldView>)).buildings[1]!.spec.roof).toBeUndefined(); // 範圍外
    expect(fieldScenery(mist({ me: { x: 11, y: 13, facing: "s" } })).buildings[1]!.spec.roof).toBeUndefined(); // 玩家不算
  });

  it("2. 廢鐵屋、鍛爐屋的招牌照伺服器的 sign（門通往的室內設施）；沒有門的不掛", () => {
    const ember = base({
      region: "ashen_waste",
      buildings: [
        { kind: "scrap_house", x: 1, y: 2, width: 6, height: 4, sign: "jar" },
        { kind: "forge_house", x: 17, y: 2, width: 6, height: 4, sign: "anvil" },
        { kind: "scrap_house", x: 6, y: 13, width: 3, height: 3, sign: null },
      ],
    } as Partial<FieldView>);
    expect(fieldScenery(ember).buildings.map((b) => b.spec.sign)).toEqual(["jar", "anvil", null]);
    expect(fieldScenery(mist()).buildings[0]!.spec.sign).toBeUndefined(); // 白牆屋舍照種類的表
  });

  it("3. 建築的門不畫淡黃色門框，不屬於建築的門保留；滑過的說明照舊", () => {
    const f = mist();
    const doors = fieldHighlights(f, null).telegraph.filter((t) => t.kind === "door");
    expect(doors.map((t) => [t.pos.x, t.pos.y])).toEqual([[20, 9]]);
    expect(hoverText(f, { x: 3, y: 5 })).toBe("霧渡鎮酒館");
    const cap = fieldHighlights(capital(), null).telegraph.filter((t) => t.kind === "door");
    expect(cap).toEqual([]); // 主城三扇門都畫成建築的門板（含側牆的門）
  });
});
