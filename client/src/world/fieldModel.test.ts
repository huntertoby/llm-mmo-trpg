// Phase 6B-3：實地地圖的組圖、BFS 路徑、方向鍵、分段、換地圖的地名與互動目標。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import {
  chunkPath,
  FIELD_HERO,
  fieldDrawModel,
  fieldHighlights,
  findPath,
  hoverText,
  interactTarget,
  keyDirection,
  mapPaneKind,
  pathNextTo,
  placeBanner,
  SIGHT_COLOR,
  stepTarget,
  targetAt,
  walkAction,
  walkedCells,
  walkPlan,
} from "./fieldModel";

/**
 * 6×5 的小鎮：`#` 牆、`^` 高 2 的台子、`E` 東邊出口、`D` 門、`S` 傳送石、`N` NPC、`F` 商店（在牆上）。
 *   y0  . . . . . .
 *   y1  . # # . ^ .
 *   y2  . D . S . E
 *   y3  . . N . . E
 *   y4  . F . . . .
 */
const ROWS = ["......", ".##.^.", ".D.S.E", "..N..E", ".#...."];

function town(over: Partial<FieldView> = {}): FieldView {
  const tiles = ROWS.flatMap((row, y) =>
    [...row].map((c, x) => ({
      x,
      y,
      height: c === "^" ? 2 : 0,
      terrain: c === "#" ? "wall" : "stone",
      surface: x === 0 && y === 0 ? "water" : "none",
      walkable: c !== "#" && c !== "N",
    })),
  );
  return {
    map_id: "mist_ferry",
    name_zh: "霧渡鎮",
    region: "cloud_ridge",
    location: "mist_ferry",
    interior: false,
    width: 6,
    height: 5,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [{ id: "o0_4", kind: "crate", x: 0, y: 4 }],
    exits: [{ id: "to_ferry_steps", cells: [[5, 2], [5, 3]], to: "ferry_steps", to_name_zh: "渡口石階" }],
    doors: [{ id: "tavern_door", x: 1, y: 2, to: "mist_ferry_tavern", to_name_zh: "霧渡鎮酒館" }],
    stones: [{ id: "stone_mist_ferry", x: 3, y: 2, unlocked: false }],
    npcs: [{ id: "granny_du", name_zh: "渡婆婆", x: 2, y: 3, rank: "neutral", rank_zh: "中立" }],
    facilities: [{ kind: "shop", x: 1, y: 4 }],
    me: { x: 0, y: 2, facing: "s" },
    max_climb: 1,
    walk_max_steps: 30,
    hero: { template_id: "hero_mage", weapon_id: "fire_staff", weapon_class: "focus", doll_look: null, race_look: null, equipment: [] },
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
  };
}

describe("field 組成 DrawModel", () => {
  it("地形、高低差、表面、物件照戰鬥畫法；區域換皮跟著所在區", () => {
    const model = fieldDrawModel(town());
    expect(model.region).toBe("cloud_ridge");
    expect([model.width, model.height]).toEqual([6, 5]);
    expect(model.tiles).toHaveLength(30);
    expect(model.tiles[1 * 6 + 1]).toMatchObject({ terrain: "wall", wall: true });
    expect(model.tiles[1 * 6 + 4]).toMatchObject({ height: 2 });
    expect(model.tiles[0]).toMatchObject({ surface: "water" });
    expect(model.objects).toEqual([expect.objectContaining({ id: "o0_4", kind: "crate", x: 0, y: 4, hpRatio: null })]);
  });

  it("主角站在 field 的位置與朝向，帶武器外觀；NPC 也是紙娃娃單位", () => {
    const model = fieldDrawModel(town({ me: { x: 3, y: 0, facing: "w" } }), "阿霧");
    const hero = model.units.find((u) => u.id === FIELD_HERO);
    expect(hero).toMatchObject({ x: 3, y: 0, facing: "west", hero: true, name: "阿霧", weaponId: "fire_staff", weaponClass: "focus", template: "hero_mage" });
    expect(model.units.find((u) => u.id === "npc_granny_du")).toMatchObject({ x: 2, y: 3, name: "渡婆婆", hero: false });
  });

  it("出口是路牌＋地面光圈（UI-E4，不再畫「出」綠框）；門與傳送石是淡色外框加小圖示", () => {
    const field = town();
    const model = fieldDrawModel(field);
    expect(model.markers).toEqual([]);
    expect(model.exitSigns).toEqual([
      { id: "to_ferry_steps", dir: "e", cells: [{ x: 5, y: 2 }, { x: 5, y: 3 }], sign: { x: 5, y: 2 }, name: "渡口石階", bare: false },
    ]);
    expect(fieldHighlights(field, { x: 5, y: 3 }).exitHover?.id).toBe("to_ferry_steps"); // 滑過才出現綠框
    const h = fieldHighlights(field, { x: 0, y: 0 });
    expect(h.exitHover).toBeNull();
    expect(h.telegraph.map((m) => [m.pos, m.glyph])).toEqual([
      [{ x: 1, y: 2 }, "門"],
      [{ x: 3, y: 2 }, "◆"],
    ]);
    expect(h.hover).toEqual({ x: 0, y: 0 });
    expect(h.moves).toEqual([]);
  });

  it("滑過的說明：出口往哪、門通到哪、NPC 名字", () => {
    const field = town();
    expect(hoverText(field, { x: 5, y: 3 })).toBe("往渡口石階");
    expect(hoverText(field, { x: 1, y: 2 })).toBe("霧渡鎮酒館");
    expect(hoverText(field, { x: 3, y: 2 })).toBe("傳送石");
    expect(hoverText(field, { x: 2, y: 3 })).toBe("渡婆婆（好感：中立）"); // 6B-4：加上好感與「！」
    expect(hoverText(field, { x: 1, y: 4 })).toBe("商店");
    expect(hoverText(field, { x: 0, y: 0 })).toBeNull();
    expect(hoverText(field, null)).toBeNull();
  });
});

describe("BFS 路徑", () => {
  it("四方向、繞過牆與 NPC，終點可以是出口", () => {
    const field = town({ me: { x: 0, y: 0, facing: "s" } });
    const path = findPath(field, field.me, { x: 5, y: 3 });
    expect(path).not.toBeNull();
    let here: { x: number; y: number } = field.me;
    for (const p of path!) {
      expect(Math.abs(p.x - here.x) + Math.abs(p.y - here.y)).toBe(1);
      expect(field.tiles[p.y * 6 + p.x]!.walkable).toBe(true);
      here = p;
    }
    expect(path![path!.length - 1]).toEqual({ x: 5, y: 3 });
  });

  it("路上避開出口、門、傳送石（伺服器會在那裡停下）", () => {
    const field = town({ me: { x: 2, y: 4, facing: "n" } });
    expect(findPath(field, field.me, { x: 4, y: 2 })).toEqual([
      { x: 3, y: 4 },
      { x: 3, y: 3 },
      { x: 4, y: 3 },
      { x: 4, y: 2 },
    ]); // 一樣長的 (3,2) 是傳送石，不走
    // 四周都是門、傳送石、牆、NPC 時才穿過去
    const boxed = town({ me: { x: 2, y: 2, facing: "s" } });
    expect(findPath(boxed, boxed.me, { x: 4, y: 2 })).toEqual([
      { x: 3, y: 2 },
      { x: 4, y: 2 },
    ]);
  });

  it("往上超過 max_climb 的格子走不上去；往下不限", () => {
    const field = town({ me: { x: 3, y: 1, facing: "e" } });
    expect(stepTarget(field, "right")).toBeNull(); // 高 0 → 2
    expect(findPath(field, field.me, { x: 4, y: 1 })).toBeNull();
    const high = town({ me: { x: 4, y: 1, facing: "w" } });
    expect(stepTarget(high, "left")).toEqual({ x: 3, y: 1 });
  });

  it("到不了、原地、終點不可站時為 null；同樣輸入同樣結果", () => {
    const field = town();
    expect(findPath(field, field.me, field.me)).toBeNull();
    expect(findPath(field, field.me, { x: 1, y: 1 })).toBeNull(); // 牆
    expect(findPath(field, field.me, { x: 2, y: 3 })).toBeNull(); // NPC
    expect(findPath(field, field.me, { x: 9, y: 9 })).toBeNull();
    expect(findPath(field, field.me, { x: 4, y: 4 })).toEqual(findPath(field, field.me, { x: 4, y: 4 }));
  });

  it("超過 30 格切成好幾段", () => {
    const path = Array.from({ length: 65 }, (_, i) => ({ x: i, y: 0 }));
    expect(chunkPath(path).map((c) => c.length)).toEqual([30, 30, 5]);
    expect(chunkPath([])).toEqual([]);
  });

  it("照伺服器給的上限切段（6P-2：規則 walk_max_steps）", () => {
    const path = Array.from({ length: 65 }, (_, i) => ({ x: i, y: 0 }));
    expect(chunkPath(path, 45).map((c) => c.length)).toEqual([45, 20]);
    expect(chunkPath(path, 10).map((c) => c.length)).toEqual([10, 10, 10, 10, 10, 10, 5]);
    expect(chunkPath(path, 0).map((c) => c.length)).toEqual([30, 30, 5]); // 不合法的值退回預設
  });
});

describe("方向鍵送出的動作", () => {
  it("方向鍵與 WASD 對到方向，其他鍵不理", () => {
    expect(["ArrowUp", "w", "W", "ArrowDown", "s", "ArrowLeft", "a", "ArrowRight", "D"].map(keyDirection)).toEqual([
      "up",
      "up",
      "up",
      "down",
      "down",
      "left",
      "left",
      "right",
      "right",
    ]);
    expect(keyDirection("e")).toBeNull();
    expect(keyDirection("Enter")).toBeNull();
  });

  it("一次一格送 walk；走不過去不送", () => {
    const field = town({ me: { x: 0, y: 2, facing: "s" } });
    const down = stepTarget(field, keyDirection("s")!);
    expect(walkAction([down!])).toEqual({ kind: "walk", path: [[0, 3]] });
    expect(stepTarget(town({ me: { x: 0, y: 0, facing: "n" } }), "up")).toBeNull(); // 地圖外
    expect(stepTarget(town({ me: { x: 0, y: 1, facing: "e" } }), "right")).toBeNull(); // 牆
  });
});

describe("伺服器結果與動畫", () => {
  const sent = [
    { x: 3, y: 3 },
    { x: 4, y: 3 },
    { x: 5, y: 3 },
  ];
  it("同一張地圖：動畫走到伺服器回報的位置", () => {
    const before = town({ me: { x: 2, y: 4, facing: "n" } });
    expect(walkedCells(before, sent, town({ me: { x: 4, y: 3, facing: "e" } }))).toEqual(sent.slice(0, 2));
    expect(walkedCells(before, sent, town({ me: { x: 2, y: 4, facing: "e" } }))).toEqual([]);
  });

  it("換了地圖：走到第一個出口格為止", () => {
    const before = town({ me: { x: 3, y: 4, facing: "n" } });
    const after = town({ map_id: "ferry_steps", me: { x: 1, y: 8, facing: "e" } });
    expect(walkedCells(before, sent, after)).toEqual(sent);
    expect(walkedCells(before, sent, null)).toEqual(sent);
  });

  it("逐格平移，每格約 0.12 秒", () => {
    const plan = walkPlan({ x: 2, y: 3 }, sent.slice(0, 2));
    expect(plan).toEqual([
      { unitId: FIELD_HERO, from: { x: 2, y: 3 }, to: { x: 3, y: 3 }, mode: "walk", durationMs: 120, style: "slide" },
      { unitId: FIELD_HERO, from: { x: 3, y: 3 }, to: { x: 4, y: 3 }, mode: "walk", durationMs: 120, style: "slide" },
    ]);
  });
});

describe("換地圖的地名與退回節點圖", () => {
  it("沒有 field 時退回節點圖", () => {
    expect(mapPaneKind({ field: null })).toBe("nodes");
    expect(mapPaneKind({})).toBe("nodes");
    expect(mapPaneKind({ field: town() })).toBe("field");
  });

  it("第一次載入不跳；換到另一張實地地圖才跳一行地名", () => {
    expect(placeBanner(undefined, town())).toBeNull();
    expect(placeBanner("mist_ferry", town())).toBeNull();
    expect(placeBanner("ferry_steps", town())).toBe("霧渡鎮");
    expect(placeBanner(null, town())).toBe("霧渡鎮");
    expect(placeBanner("mist_ferry", null)).toBeNull();
  });
});

describe("設施與 NPC 的互動", () => {
  it("點到的格子是 NPC 或設施", () => {
    const field = town();
    expect(targetAt(field, { x: 2, y: 3 })).toEqual({ kind: "npc", npc: "granny_du", name: "渡婆婆", x: 2, y: 3 });
    expect(targetAt(field, { x: 1, y: 4 })).toEqual({ kind: "facility", facility: "shop", x: 1, y: 4 });
    expect(targetAt(field, { x: 0, y: 0 })).toBeNull();
  });

  it("按 E：面向的那格優先，再找相鄰的；旁邊沒有東西為 null", () => {
    expect(interactTarget(town({ me: { x: 2, y: 4, facing: "n" } }))).toMatchObject({ kind: "npc", npc: "granny_du" });
    expect(interactTarget(town({ me: { x: 2, y: 4, facing: "w" } }))).toMatchObject({ kind: "facility", facility: "shop" });
    expect(interactTarget(town({ me: { x: 5, y: 0, facing: "s" } }))).toBeNull();
  });

  it("不在旁邊時先走到最近的相鄰可站格", () => {
    const field = town({ me: { x: 0, y: 0, facing: "s" } });
    const path = pathNextTo(field, { x: 1, y: 4 })!;
    const end = path[path.length - 1]!;
    expect(Math.abs(end.x - 1) + Math.abs(end.y - 4)).toBe(1);
    expect(pathNextTo(town({ me: { x: 2, y: 4, facing: "n" } }), { x: 1, y: 4 })).toEqual([]);
  });
});

describe("看得見的敵人（6C-1）", () => {
  const enemy = {
    id: "e0",
    x: 4,
    y: 4,
    facing: "w" as const,
    patrol: true,
    group: "bandit_raiders",
    name_zh: "盜賊",
    elite: true,
    units: [
      { unit: "bandit_blade", name_zh: "刀盜", affix: "swift", elite: true, third: false },
      { unit: "bandit_archer", name_zh: "弓盜", affix: null, elite: false, third: false },
      { unit: "mist_wolf", name_zh: "霧狼", affix: null, elite: false, third: true },
    ],
    sight: [
      [3, 4],
      [2, 4],
      [3, 2],
    ] as [number, number][],
  };

  it("敵群畫成敵方單位：陣容第一名的範本、朝向照伺服器", () => {
    const view = fieldDrawModel(town({ enemies: [enemy] }));
    const unit = view.units.find((u) => u.id === "enemy_e0");
    expect(unit).toBeDefined();
    expect(unit?.team).toBe("enemy");
  });

  it("視野併成一塊淡紅範圍（門與傳送石那一格不重疊）、不再是每格的標記；精英多一個「精」", () => {
    const h = fieldHighlights(town({ enemies: [enemy] }), null);
    expect(h.regions?.map((r) => [r.color, r.cells.map((p) => `${p.x},${p.y}`)])).toEqual([[SIGHT_COLOR, ["2,4", "3,4"]]]); // (3, 2) 是傳送石
    expect(h.telegraph.some((m) => m.kind === "sight")).toBe(false);
    expect(h.telegraph.find((m) => m.kind === "elite")?.glyph).toBe("精");
  });

  it("滑過敵群說明陣容，滑過視野格提示", () => {
    const field = town({ enemies: [enemy] });
    expect(hoverText(field, { x: 4, y: 4 })).toBe("盜賊・精英・2 名・另有第三方 1 名・巡邏");
    expect(hoverText(field, { x: 2, y: 4 })).toBe("敵人的視野");
  });

  it("帶頭單位的外觀照戰鬥畫法（6C-R3）：異形帶 creature、人形帶紙娃娃與種族外觀", () => {
    const wolf = {
      template_id: "mist_wolf",
      weapon_id: "wolf_fang",
      weapon_class: "melee",
      doll_look: { creature: { body: "quadruped", size: "medium" } },
      race_look: null,
      equipment: [],
    } as unknown as NonNullable<FieldView["enemies"][number]["look"]>;
    const view = fieldDrawModel(town({ enemies: [{ ...enemy, look: wolf }] }));
    const unit = view.units.find((u) => u.id === "enemy_e0");
    expect(unit?.dollLook?.creature).toEqual({ body: "quadruped", size: "medium" });
    expect(unit?.team).toBe("enemy");
    const human = { ...wolf, template_id: "bandit_blade", doll_look: { head: "hood" }, race_look: { ears: "long" } } as unknown as typeof wolf;
    const drawn = fieldDrawModel(town({ enemies: [{ ...enemy, look: human }] })).units.find((u) => u.id === "enemy_e0");
    expect(drawn?.dollLook?.creature ?? null).toBeNull();
    expect(drawn?.raceLook).toEqual({ ears: "long" });
  });

  it("沒有外觀（舊伺服器）時照舊用陣容第一名的範本", () => {
    const unit = fieldDrawModel(town({ enemies: [{ ...enemy, look: null }] })).units.find((u) => u.id === "enemy_e0");
    expect(unit?.dollLook ?? null).toBeNull();
  });

  it("沒有敵人時不多畫東西", () => {
    const h = fieldHighlights(town(), null);
    expect(h.telegraph.some((m) => m.kind === "sight" || m.kind === "elite")).toBe(false);
    expect(h.regions).toEqual([]);
    expect(fieldDrawModel(town()).units.some((u) => u.id.startsWith("enemy_"))).toBe(false);
  });
});
