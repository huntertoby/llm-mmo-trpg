// Phase 6C-5：地圖上的東西——事件「！」、營火、情境物件、朋友的腳印、留言石碑的標記與互動，潛行鈕，
// 區域圖的足跡，情境物件的說明卡。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FieldView, WorldLocationView, WorldMapView, WorldView } from "../api/types";
import { FieldObjectCard, objectButtonText } from "./FieldThings";
import { CAMPFIRE_ZH, EVENT_MARK_ZH, fieldHighlights, hoverText, interactTarget, mapThings, objectText, targetAt } from "./fieldModel";
import { buttonState, HUD_BUTTONS, hudButtonCard, sneakState } from "./hud";
import { regionNodes } from "./regionModel";

type Obj = NonNullable<FieldView["situation_objects"]>[number];

const ALTAR: Obj = { id: "horned_fire_altar", name_zh: "火焰祭壇", x: 4, y: 1, use: "event", usable: true, note_zh: "", problem_zh: null };
const WALL: Obj = { id: "rift_mist_wall", name_zh: "霧牆", x: 0, y: 4, use: "note", usable: false, note_zh: "霧後是石階。", problem_zh: null };
const GATE: Obj = { id: "summit_gate", name_zh: "觀門", x: 5, y: 4, use: "encounter", usable: false, note_zh: "", problem_zh: "還有沒處理的遭遇" };

function field(over: Partial<FieldView> = {}): FieldView {
  const tiles = Array.from({ length: 30 }, (_, i) => ({ x: i % 6, y: Math.floor(i / 6), height: 0, terrain: "stone", surface: "none", walkable: true }));
  return {
    map_id: "ferry_steps",
    name_zh: "渡口石階",
    region: "cloud_ridge",
    location: "ferry_steps",
    interior: false,
    width: 6,
    height: 5,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [],
    doors: [{ id: "d", x: 1, y: 2, to: "x", to_name_zh: "酒館" }],
    stones: [],
    npcs: [],
    facilities: [],
    me: { x: 2, y: 2, facing: "s" },
    max_climb: 1,
    walk_max_steps: 30,
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [{ id: "campfire_ferry_steps", x: 3, y: 3 }],
    event_mark: { x: 2, y: 0 },
    situation_objects: [ALTAR, WALL, GATE],
    sneaking: false,
    sneak_cost: 1,
    sneak_problem_zh: null,
    footprints: [
      { owner: "bob", name_zh: "小白", x: 5, y: 0, facing: "e" },
      { owner: "bob", name_zh: "小白", x: 1, y: 2, facing: "e" }, // 和門同一格：不畫
    ],
    note_stone: { x: 0, y: 0, count: 2 },
    buildings: [],
    ...over,
  };
}

describe("地圖上的東西的標記", () => {
  it("「！」、營火、石碑、腳印（6C-8）照形狀畫、不進格子框；情境物件不再有淡色框與「◎」（6C-8b）；和門同一格的不畫", () => {
    const h0 = fieldHighlights(field(), null);
    expect(h0.telegraph.some((m) => m.kind === "object" || m.glyph === "◎")).toBe(false);
    const things = mapThings(field());
    const thing = (x: number, y: number) => things.find((t) => t.pos.x === x && t.pos.y === y);
    expect(thing(2, 0)).toMatchObject({ kind: "event" });
    expect(thing(3, 3)).toMatchObject({ kind: "campfire", lit: true });
    expect(thing(0, 0)).toMatchObject({ kind: "note_stone" });
    expect(thing(5, 0)).toMatchObject({ kind: "footprint", facing: "e" });
    expect(thing(1, 2)).toBeUndefined();
    const h = fieldHighlights(field(), null);
    expect(h.telegraph.some((m) => ["event", "campfire", "note_stone", "footprint"].includes(m.kind))).toBe(false);
    expect(h.things).toEqual(things);
    // 說明卡照舊
    expect(hoverText(field(), { x: 2, y: 0 })).toBe(EVENT_MARK_ZH);
    expect(hoverText(field(), { x: 3, y: 3 })).toBe(CAMPFIRE_ZH);
    expect(hoverText(field(), { x: 5, y: 0 })).toBe("小白走過這裡");
  });

  it("同一格只畫一個（「！」優先）", () => {
    const things = mapThings(field({ campfires: [{ id: "c", x: 2, y: 0 }] }));
    expect(things.filter((m) => m.pos.x === 2 && m.pos.y === 0).map((m) => m.kind)).toEqual(["event"]);
  });

  it("情境物件提示（6C-8b）：主角在 1 格內（站上或四方向相鄰）才有，離開就沒有；說明卡照舊", () => {
    const hints = (me: { x: number; y: number }) =>
      mapThings(field({ me: { ...me, facing: "s" } }))
        .filter((t) => t.kind === "object_hint")
        .map((t) => t.pos);
    expect(hints({ x: 2, y: 2 })).toEqual([]); // 祭壇 (4,1)、霧牆 (0,4)、觀門 (5,4) 都不在旁邊
    expect(hints({ x: 4, y: 2 })).toEqual([{ x: 4, y: 1 }]); // 祭壇正下方
    expect(hints({ x: 3, y: 1 })).toEqual([{ x: 4, y: 1 }]); // 祭壇左邊
    expect(hints({ x: 4, y: 1 })).toEqual([{ x: 4, y: 1 }]); // 站在上面
    expect(hints({ x: 3, y: 2 })).toEqual([]); // 斜角不算（同按 E 的判定）
    expect(hints({ x: 5, y: 3 })).toEqual([{ x: 5, y: 4 }]); // 不能用的物件也提示（按 E 會開說明卡）
    expect(hints({ x: 0, y: 3 })).toEqual([{ x: 0, y: 4 }]); // 只能看的也提示
    const h = fieldHighlights(field({ me: { x: 4, y: 2, facing: "n" } }), null);
    expect(h.things?.filter((t) => t.kind === "object_hint")).toEqual([{ kind: "object_hint", pos: { x: 4, y: 1 } }]);
    expect(h.telegraph.some((m) => m.kind === "object")).toBe(false);
    expect(hoverText(field({ me: { x: 4, y: 2, facing: "n" } }), { x: 4, y: 1 })).toBe("火焰祭壇（走過去調查）");
    expect(hoverText(field(), { x: 4, y: 1 })).toBe("火焰祭壇（走過去調查）");
  });

  it("情境物件即使不畫提示也照舊佔住那一格（營火不會畫到物件上）", () => {
    const things = mapThings(field({ campfires: [{ id: "c", x: 4, y: 1 }] }));
    expect(things.some((t) => t.pos.x === 4 && t.pos.y === 1)).toBe(false);
  });

  it("沒有東西的地圖沒有標記", () => {
    expect(mapThings(field({ campfires: [], event_mark: null, situation_objects: [], footprints: [], note_stone: null }))).toEqual([]);
  });
});

describe("滑過說明與互動目標", () => {
  it("物件的說明：能用、不能用、只能看", () => {
    expect(objectText(ALTAR)).toBe("火焰祭壇（走過去調查）");
    expect(objectText(GATE)).toBe("觀門（還有沒處理的遭遇）");
    expect(objectText(WALL)).toBe("霧牆");
    expect(objectText({ ...GATE, usable: true, problem_zh: null })).toBe("觀門（走過去挑戰）");
  });

  it("hoverText：「！」、營火、物件、石碑、腳印", () => {
    const f = field();
    expect(hoverText(f, { x: 2, y: 0 })).toBe(EVENT_MARK_ZH);
    expect(hoverText(f, { x: 3, y: 3 })).toBe(CAMPFIRE_ZH);
    expect(hoverText(f, { x: 4, y: 1 })).toBe("火焰祭壇（走過去調查）");
    expect(hoverText(f, { x: 0, y: 0 })).toContain("2 則留言");
    expect(hoverText(f, { x: 5, y: 0 })).toBe("小白走過這裡");
  });

  it("點物件與石碑是互動目標（走到旁邊再開）；E 找相鄰的", () => {
    const f = field();
    expect(targetAt(f, { x: 4, y: 1 })).toEqual({ kind: "object", id: "horned_fire_altar", name: "火焰祭壇", x: 4, y: 1 });
    expect(targetAt(f, { x: 0, y: 0 })).toEqual({ kind: "note_stone", x: 0, y: 0 });
    expect(targetAt(f, { x: 3, y: 3 })).toBeNull(); // 營火不是目標（站上去按紮營）
    const beside = field({ me: { x: 4, y: 2, facing: "n" } });
    expect(interactTarget(beside)).toMatchObject({ kind: "object", id: "horned_fire_altar" });
  });

  it("潛行中，視野的說明加註減半", () => {
    const enemy = { id: "e0", x: 5, y: 4, facing: "n" as const, patrol: false, group: "g", name_zh: "盜賊", elite: false, units: [], sight: [[5, 3]] as [number, number][] };
    expect(hoverText(field({ enemies: [enemy] }), { x: 5, y: 3 })).toBe("敵人的視野");
    expect(hoverText(field({ enemies: [enemy], sneaking: true }), { x: 5, y: 3 })).toBe("敵人的視野（潛行中，減半）");
  });
});

describe("潛行鈕（R）", () => {
  const sneakBtn = HUD_BUTTONS.find((b) => b.id === "sneak")!;
  const view = (f: FieldView | null) => ({ field: f }) as unknown as WorldView;

  it("可以開：normal，說明花多少補給", () => {
    expect(sneakState(view(field()))).toEqual({ active: false, problem: null, status: "花 1 補給" });
    expect(buttonState(view(field()), sneakBtn, null)).toBe("normal");
  });

  it("潛行中：亮著（open）", () => {
    const v = view(field({ sneaking: true }));
    expect(sneakState(v).active).toBe(true);
    expect(buttonState(v, sneakBtn, null)).toBe("open");
    expect(hudButtonCard(v, "sneak").status).toBe("潛行中（到下一張地圖為止）");
  });

  it("不能開：灰掉，說明原因", () => {
    const v = view(field({ sneak_problem_zh: "城鎮與室內不用潛行" }));
    expect(buttonState(v, sneakBtn, null)).toBe("disabled");
    expect(hudButtonCard(v, "sneak").status).toBe("城鎮與室內不用潛行");
    expect(sneakState(view(null)).problem).not.toBeNull();
  });
});

describe("情境物件的說明卡", () => {
  const view = (f: FieldView, over: Partial<WorldView> = {}) => ({ field: f, encounter: null, battle_id: null, event: null, ...over }) as unknown as WorldView;
  const render = (v: WorldView, object: string) => renderToStaticMarkup(createElement(FieldObjectCard, { view: v, object, busy: false, onAct: () => undefined, onClose: () => undefined }));

  it("能用、在旁邊：按鈕可以按", () => {
    const out = render(view(field({ me: { x: 4, y: 2, facing: "n" } })), "horned_fire_altar");
    expect(out).toContain('data-use="event"');
    expect(out).toContain("調查");
    expect(out).not.toMatch(/data-testid="world-object-use"[^>]*disabled/);
    expect(out).not.toContain("走到旁邊");
  });

  it("不在旁邊：按鈕灰掉並提示", () => {
    const out = render(view(field()), "horned_fire_altar");
    expect(out).toMatch(/disabled=""[^>]*data-testid="world-object-use"|data-testid="world-object-use"[^>]*disabled/);
    expect(out).toContain("走到旁邊才能調查");
  });

  it("只能看的沒有按鈕；不能用的顯示原因", () => {
    expect(render(view(field()), "rift_mist_wall")).not.toContain("world-object-use");
    expect(render(view(field()), "rift_mist_wall")).toContain("霧後是石階。");
    expect(render(view(field()), "summit_gate")).toContain("還有沒處理的遭遇");
    expect(objectButtonText("encounter")).toBe("挑戰");
    expect(objectButtonText("note")).toBeNull();
  });
});

describe("區域圖的足跡", () => {
  const loc = (id: string, over: Partial<WorldLocationView>): WorldLocationView => ({
    id,
    name_zh: id,
    kind: "camp",
    kind_zh: "營地",
    level_zh: "Lv 1",
    description_zh: "",
    x: 10,
    y: 10,
    current: false,
    adjacent: false,
    blocked_zh: null,
    cleared: false,
    hidden: false,
    fog: "visited",
    quest_marks: [],
    footprints: [],
    ...over,
  });
  const map = (locations: WorldLocationView[]) =>
    ({ region: "cloud_ridge", name_zh: "雲嶺", level_zh: "", locations, edges: [], stones: [], can_teleport: false, teleport_problem_zh: null }) as unknown as WorldMapView;

  it("去過、剪影的地點列出朋友；霧裡不顯示", () => {
    const nodes = regionNodes(map([loc("a", { footprints: ["小白"] }), loc("b", { fog: "fog", footprints: ["小白"] })]));
    expect(nodes[0]!.footprints).toEqual(["小白"]);
    expect(nodes[0]!.hint).toContain("足跡：小白走過這裡");
    expect(nodes[1]!.footprints).toEqual([]);
  });
});
