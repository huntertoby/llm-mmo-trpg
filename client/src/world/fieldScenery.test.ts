// 6B-ART1：只畫的外觀（建築、門、室內、家具）——資料換算、確定性、門動畫時間軸。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { DOOR_OPEN_MS, doorOpenness, LEAVE_MS, STAGE_FADE_MS, FADE_LEAD_MS } from "../render/doorClips";
import { buildingArtKey, buildingKind, doorCenters, doorPanelScale, windowCenters } from "../render/townArt";
import { roomKindOf, roomPalette, wallDecor } from "../render/interiorArt";
import { interiorPieces, roofCovers } from "../render/sceneryModel";
import { fieldScenery } from "./fieldScenery";

function field(over: Partial<FieldView> = {}): FieldView {
  return {
    map_id: "mist_ferry",
    name_zh: "霧渡鎮",
    region: "cloud_ridge",
    location: "mist_ferry",
    interior: false,
    width: 24,
    height: 18,
    tiles: [],
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [],
    doors: [
      { id: "tavern_door", x: 3, y: 5, to: "mist_ferry_tavern", to_name_zh: "霧渡鎮酒館" },
      { id: "smithy_door", x: 18, y: 5, to: "mist_ferry_smithy", to_name_zh: "石記鐵鋪" },
    ],
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
    buildings: [
      { kind: "tavern", x: 1, y: 2, width: 6, height: 4 },
      { kind: "smithy", x: 16, y: 2, width: 6, height: 4 },
      { kind: "hall", x: 1, y: 10, width: 3, height: 2 },
      { kind: "pagoda", x: 10, y: 14, width: 4, height: 3 },
    ],
    ...over,
  } as FieldView;
}

function room(over: Partial<FieldView> = {}): FieldView {
  return field({
    map_id: "mist_ferry_tavern",
    interior: true,
    width: 10,
    height: 8,
    buildings: [],
    doors: [],
    exits: [{ id: "to_mist_ferry", cells: [[4, 7], [5, 7]], to: "mist_ferry", to_name_zh: "霧渡鎮" }],
    objects: [
      { id: "o2_3", kind: "crate", x: 2, y: 3, look: "bar" },
      { id: "o3_3", kind: "crate", x: 3, y: 3, look: "bar" },
      { id: "o4_3", kind: "crate", x: 4, y: 3, look: "bar" },
      { id: "o6_4", kind: "low_wall", x: 6, y: 4, look: "table" },
      { id: "o1_5", kind: "crate", x: 1, y: 5 },
    ],
    facilities: [
      { kind: "tavern", x: 3, y: 3 },
      { kind: "hire", x: 8, y: 1 },
    ],
    ...over,
  });
}

describe("建築（6B-ART1）", () => {
  it("建築照內容的範圍；門格在最下一列的才畫成建築正面的門；不認得的外觀退回 house", () => {
    const s = fieldScenery(field());
    expect(s.buildings.map((b) => [b.spec.kind, b.x, b.y, b.spec.w, b.spec.h, b.spec.doors])).toEqual([
      ["tavern", 1, 2, 6, 4, [2]],
      ["smithy", 16, 2, 6, 4, [2]],
      ["hall", 1, 10, 3, 2, []],
      ["house", 10, 14, 4, 3, []],
    ]);
    expect(s.doors).toEqual([
      { x: 3, y: 5, style: "wood" },
      { x: 18, y: 5, style: "wood" },
    ]);
    expect(buildingKind("scrap_house")).toBe("scrap_house");
    expect(buildingKind("pagoda")).toBe("house");
  });

  it("隱藏門揭露前伺服器不給，就不畫門（建築範圍內的牆照舊）", () => {
    const s = fieldScenery(field({ doors: [] }));
    expect(s.doors).toEqual([]);
    expect(s.buildings[0]!.spec.doors).toEqual([]);
  });

  it("廢鐵屋與鍛爐屋是布簾門", () => {
    const s = fieldScenery(field({ region: "ashen_waste", buildings: [{ kind: "forge_house", x: 17, y: 2, width: 6, height: 4 }], doors: [{ id: "d", x: 19, y: 5, to: "x", to_name_zh: "x" }] }));
    expect(s.doors).toEqual([{ x: 19, y: 5, style: "rag" }]);
  });

  it("屋頂往上多蓋 1 格：站在屋後那一列的人被蓋住（另畫剪影），屋前、門口的人不會", () => {
    const s = fieldScenery(field());
    expect(roofCovers(s, { x: 11, y: 13 })).toBe(true); // 渡婆的屋子北邊
    expect(roofCovers(s, { x: 3, y: 1 })).toBe(true);
    expect(roofCovers(s, { x: 3, y: 5 })).toBe(false); // 門口
    expect(roofCovers(s, { x: 3, y: 6 })).toBe(false); // 屋前
    expect(roofCovers(s, { x: 9, y: 13 })).toBe(false);
  });

  it("窗戶避開門與右邊的招牌、彼此不相鄰；沒有門的建築在正中央畫裝飾門", () => {
    expect(windowCenters({ kind: "tavern", w: 6, h: 4, doors: [2] })).toEqual([0.5, 4.5]);
    expect(windowCenters({ kind: "house", w: 4, h: 3, doors: [] })).toEqual([0.5, 3.5]);
    expect(doorCenters({ kind: "hall", w: 3, h: 2, doors: [] })).toEqual([1.5]);
  });

  it("畫法確定性：同一份資料每次的外觀與快取鍵都一樣", () => {
    const a = fieldScenery(field());
    const b = fieldScenery(field());
    expect(a).toEqual(b);
    expect(a.buildings.map((x) => buildingArtKey(x.spec))).toEqual(b.buildings.map((x) => buildingArtKey(x.spec)));
    expect(buildingArtKey(a.buildings[0]!.spec)).toBe("bld|tavern|6x4|2");
  });
});

describe("室內（6B-ART1）", () => {
  it("種類照設施、配色照區域：酒館木板、導師殿石板、荒原鐵灰牆焦木地板", () => {
    expect(roomKindOf(["tavern", "hire"])).toBe("tavern");
    expect(roomKindOf(["smithy", "enchanter"])).toBe("smithy");
    expect(roomKindOf(["mentor"])).toBe("mentor");
    expect(roomPalette("tavern", "town").style).toBe("plank");
    expect(roomPalette("mentor", "town").style).toBe("slab");
    expect(roomPalette("tavern", "ashen")).toEqual({ wall: "#5a5e60", floor: "#5a4434", style: "plank" });
  });

  it("後牆擺設：酒館＝酒架＋壁爐、鐵匠＝兩座鍛爐＋武器架、導師殿＝晶石像＋兩座書架；避開緊貼後牆的物件", () => {
    expect(wallDecor("tavern", 10, []).map((d) => [d.kind, d.x])).toEqual([
      ["wine_rack", 1],
      ["fireplace", 7],
    ]);
    expect(wallDecor("smithy", 10, []).map((d) => d.kind)).toEqual(["forge", "forge", "weapon_rack"]);
    const mentor = wallDecor("mentor", 10, [1, 2, 3, 6]);
    expect(mentor.map((d) => [d.kind, d.x])).toEqual([
      ["statue", 4],
      ["bookshelf", 7],
    ]); // 主城導師殿：書架物件（1～3）與講壇（6）緊貼後牆，第二座書架放不下就不畫
  });

  it("家具照 look；吧檯左右相連；附魔台是 enchanter 那格（沒有物件時用正北一格）的物件", () => {
    const s = fieldScenery(room());
    expect(s.furniture).toEqual({
      "2,3": { look: "bar", joinW: false, joinE: true },
      "3,3": { look: "bar", joinW: true, joinE: true },
      "4,3": { look: "bar", joinW: true, joinE: false },
      "6,4": { look: "table", joinW: false, joinE: false },
    });
    const smithy = fieldScenery(room({ objects: [{ id: "o7_2", kind: "stone_pillar", x: 7, y: 2 }], facilities: [{ kind: "enchanter", x: 7, y: 3 }] }));
    expect(smithy.furniture["7,2"]?.look).toBe("enchant");
  });

  it("外框：最上一列是後牆（另外整張畫）；左右與下方的牆格畫牆邊，下方出口畫入口光圈，其他是地板", () => {
    const s = fieldScenery(room());
    const walls = new Set<string>();
    for (let y = 0; y < 8; y++) for (let x = 0; x < 10; x++) if (y === 0 || x === 0 || x === 9 || (y === 7 && x !== 4 && x !== 5)) walls.add(`${x},${y}`);
    const pieces = interiorPieces(s.interior!, 10, 8, walls);
    expect(pieces.some((p) => p.y === 0)).toBe(false);
    expect(pieces.filter((p) => p.kind === "exit").map((p) => [p.x, p.y])).toEqual([
      [4, 7],
      [5, 7],
    ]);
    expect(pieces.find((p) => p.x === 0 && p.y === 3)).toEqual({ kind: "wall", x: 0, y: 3, side: { n: false, e: true, w: false } });
    expect(pieces.find((p) => p.x === 2 && p.y === 7)).toEqual({ kind: "wall", x: 2, y: 7, side: { n: true, e: false, w: false } });
    expect(pieces.filter((p) => p.kind === "floor")).toHaveLength(8 * 6);
  });

  it("導師殿中央鋪紅地毯（4 格寬、從第 3 列到出口前）", () => {
    const s = fieldScenery(room({ facilities: [{ kind: "mentor", x: 6, y: 2 }] }));
    expect(s.interior!.rug).toEqual({ x: 3, y: 2, w: 4, h: 5 });
  });
});

describe("門打開 0.2 秒（6B-ART1）", () => {
  it("進門：門板和離開片段同時開始轉開，0.2 秒開好，不拉長換地圖的時間", () => {
    expect(DOOR_OPEN_MS).toBe(200);
    expect(DOOR_OPEN_MS).toBeLessThanOrEqual(Math.max(LEAVE_MS, FADE_LEAD_MS + STAGE_FADE_MS));
    expect(doorOpenness("open", 0)).toBe(0);
    expect(doorOpenness("open", 1)).toBe(1);
    expect(doorOpenness("open", 0.5)).toBeGreaterThan(0.5); // 先快後慢
    expect(doorPanelScale(0)).toBe(1);
    expect(doorPanelScale(1)).toBeCloseTo(0.15);
  });

  it("出門：從開著關回去，先慢後快；越界的時間夾在 0～1", () => {
    expect(doorOpenness("close", 0)).toBe(1);
    expect(doorOpenness("close", 1)).toBe(0);
    expect(doorOpenness("close", 0.5)).toBeGreaterThan(0.5);
    expect(doorOpenness("close", 2)).toBe(0);
    expect(doorOpenness("open", -1)).toBe(0);
  });
});
