// Phase 6V-1：主城功能型 NPC（守印人、守池人、工坊師傅、書記）站在原本的情境物件格子上，有紙娃娃與頭像；
// 只畫：點了照舊是情境物件（開原本的面板或說明卡），不是 NPC、不畫血條；工坊師傅待機打鐵。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { type FieldFigure, type FieldView, type NpcPortrait, type WorldView } from "../api/types";
import { resolveDoll } from "../render/appearance";
import { npcIdleFrame } from "../render/npcFidgets";
import { drawPortrait, PORTRAIT_EXTRAS, PORTRAIT_REGION } from "../render/portrait";
import { fieldAmbient } from "./fieldAmbient";
import { barlessIds, fieldDrawModel, figureObjects, hoverText, interactTarget, targetAt, type FieldSituationObject, facilityFigures, figureSpots } from "./fieldModel";
import { FieldObjectCard } from "./FieldThings";
import { figureFieldLook, figureUnitId, facilityFigureId, FIGURE_EMPTY_HAND, npcFieldLook } from "./npcLook";
import { BoardPanel, boardKeeper } from "./BoardPanel";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import hallYaml from "../../../content/world/fields/capital/interiors/capital_mentor_hall.yaml?raw";
import tavernYaml from "../../../content/world/fields/capital/interiors/capital_tavern.yaml?raw";
import smithyYaml from "../../../content/world/fields/capital/interiors/capital_smithy.yaml?raw";

interface SpotRow {
  at: [number, number];
  id: string;
  name_zh: string;
  panel?: string;
  note_zh?: string;
  figure?: FieldFigure;
}

const spots = (text: string): SpotRow[] => (parse(text) as { situation_objects: SpotRow[] }).situation_objects;
const ALL = [...spots(capitalYaml), ...spots(hallYaml)];
const FIGURES = ALL.filter((s) => s.figure !== undefined);

/** 原本（6D-4／6D-R2）的格子與面板。 */
const ORIGINAL: Record<string, { at: [number, number]; panel: string | undefined }> = {
  seal_keeper: { at: [14, 12], panel: "board" }, // RT-5b：移到中央廣場傳送石旁（玩法 PM 決定）
  pool_keeper: { at: [6, 4], panel: "wish" }, // WP-2：點了開許願池面板
  workshop_master: { at: [24, 18], panel: "workshop" }, // PR-2a：點了開工坊師傅選單
  scribe: { at: [2, 2], panel: "skills" },
};

/** 記錄呼叫的假 Canvas 2D（同 portrait.test.ts）。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${fmt(o)},${c})`) };
        if (prop === "measureText") return { width: String(args[0]).length * 6 };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const drawCalls = (p: NpcPortrait, region: string): string[] => {
  const { ctx, calls } = mockCtx();
  drawPortrait(ctx, 0, 0, 96, p, region);
  return calls;
};

function asObject(s: SpotRow): FieldSituationObject {
  return {
    id: s.id,
    name_zh: s.name_zh,
    x: s.at[0],
    y: s.at[1],
    use: "note",
    usable: false,
    note_zh: s.note_zh ?? "",
    problem_zh: null,
    panel: (s.panel ?? null) as FieldSituationObject["panel"],
    stele_region: null,
    figure: s.figure ?? null,
  };
}

/** 32×24 的主城（只放情境物件；主角在入口）。 */
function capital(me = { x: 16, y: 11 }): FieldView {
  const tiles = Array.from({ length: 32 * 24 }, (_, i) => ({ x: i % 32, y: Math.floor(i / 32), height: 0, terrain: "stone", surface: "none", walkable: true }));
  return {
    map_id: "capital",
    name_zh: "樞島",
    region: "capital",
    location: "capital",
    interior: false,
    width: 32,
    height: 24,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    npcs: [],
    facilities: [],
    me: { ...me, facing: "s" },
    max_climb: 1,
    walk_max_steps: 30,
    hero: { template_id: "hero_mage", weapon_id: "fire_staff", weapon_class: "focus", doll_look: null, race_look: null, equipment: [] },
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [],
    situation_objects: spots(capitalYaml).map(asObject),
    sneaking: false,
    sneak_cost: 1,
    footprints: [],
    buildings: [],
    chasm_style: "default",
    decor: [],
  } as unknown as FieldView;
}

describe("內容：四位都有外觀與頭像，格子不變", () => {
  it("剛好四位，位置與面板照舊", () => {
    expect(FIGURES.map((s) => s.id).sort()).toEqual(Object.keys(ORIGINAL).sort());
    for (const s of FIGURES) {
      expect(s.at, s.id).toEqual(ORIGINAL[s.id]!.at);
      expect(s.panel, s.id).toBe(ORIGINAL[s.id]!.panel);
      expect(s.figure!.portrait.look, s.id).toBeDefined();
      expect(s.figure!.portrait.gear?.["body"], s.id).toBeDefined();
    }
  });

  it("頭像的配件都畫得出來，框色是主城（QK-2b：RT-1 的晶紫 #a898ff，不再是傭兵金），畫法確定", () => {
    const known: readonly string[] = PORTRAIT_EXTRAS;
    const ring = PORTRAIT_REGION["capital"]![0];
    expect(ring).toBe("#a898ff");
    for (const s of FIGURES) {
      const p = s.figure!.portrait as NpcPortrait;
      for (const e of p.extras ?? []) expect(known, `${s.id} ${e}`).toContain(e);
      const calls = drawCalls(p, "capital");
      expect(calls, s.id).toContain(`strokeStyle=${ring}`);
      expect(calls, s.id).not.toContain(`strokeStyle=${PORTRAIT_REGION["merc"]![0]}`);
      expect(calls).toEqual(drawCalls(p, "capital"));
    }
  });

  it("四位的頭像彼此不同", () => {
    const keys = FIGURES.map((s) => drawCalls(s.figure!.portrait as NpcPortrait, "capital").join("|"));
    expect(new Set(keys).size).toBe(4);
  });
});

describe("地圖紙娃娃", () => {
  it("站在原本的格子、不畫血條、朝向照內容", () => {
    const field = capital();
    const model = fieldDrawModel(field);
    const barless = barlessIds(field);
    for (const o of figureObjects(field)) {
      const u = model.units.find((x) => x.id === figureUnitId(o.id));
      expect(u, o.id).toBeDefined();
      expect([u!.x, u!.y]).toEqual([o.x, o.y]);
      expect(u!.noBar).toBe(true);
      expect(barless.has(u!.id)).toBe(true);
      expect(u!.dollLook).not.toBeNull();
    }
    const facing = Object.fromEntries(model.units.map((u) => [u.id, u.facing]));
    expect(facing[figureUnitId("seal_keeper")]).toBe("east"); // RT-5b：面向剛醒來的主角
    expect(facing[figureUnitId("workshop_master")]).toBe("east");
    // 沒有 figure 的物件不畫人
    expect(model.units.some((u) => u.id === figureUnitId("wishing_pool"))).toBe(false);
  });

  it("守印人兜帽長袍拿晶杖、工坊師傅拿錘子（照樣張）", () => {
    const field = capital();
    const doll = (id: string) => {
      const o = figureObjects(field).find((x) => x.id === id)!;
      const look = figureFieldLook(o.id, o.figure);
      return resolveDoll({ template: look.template_id, dollLook: look.doll_look, team: "ally", summon: false, weaponId: look.weapon_id, weaponClass: look.weapon_class, equipment: look.equipment, raceLook: null });
    };
    const keeper = doll("seal_keeper");
    expect(keeper.gear.main_hand).toMatchObject({ kind: "staff", material: "crystal" });
    expect(keeper.gear.head?.kind).toBe("hood");
    expect(keeper.gear.body?.kind).toBe("robe");
    expect(doll("workshop_master").gear.main_hand?.kind).toBe("hammer");
    const pool = doll("pool_keeper");
    expect(pool.gear.off_hand?.kind).toBe("orb");
    expect(pool.gear.main_hand).toBeUndefined(); // 沒拿東西＝主手空著（不是退回的劍）
  });

  it("書記一手捧魔導書、主手空著", () => {
    const hall = ALL.find((s) => s.id === "scribe")!;
    const look = figureFieldLook(hall.id, hall.figure!);
    const spec = resolveDoll({ template: look.template_id, dollLook: look.doll_look, team: "ally", summon: false, weaponId: look.weapon_id, weaponClass: look.weapon_class, equipment: look.equipment, raceLook: null });
    expect(spec.gear.off_hand?.kind).toBe("tome");
    expect(spec.gear.main_hand).toBeUndefined();
  });

  it("工坊師傅待機打鐵（6N-10 的鐵匠小動作），其他人是一般小動作", () => {
    const scene = fieldAmbient(capital());
    expect(scene.roles[figureUnitId("workshop_master")]).toBe("smith");
    expect(scene.roles[figureUnitId("seal_keeper")]).toBe("town");
    expect(scene.roles[figureUnitId("pool_keeper")]).toBe("town");
    const ids = new Set<string>();
    for (let ms = 0; ms < 120_000; ms += 100) {
      const f = npcIdleFrame(scene.key, figureUnitId("workshop_master"), "smith", ms, "east");
      if (f.key.startsWith("n:")) ids.add(f.key.split(":")[1]!);
    }
    expect(ids.has("hammer")).toBe(true);
  });
});

describe("互動照舊", () => {
  it("點那一格還是情境物件，不是 NPC；說明照舊", () => {
    const field = capital({ x: 13, y: 12 });
    expect(targetAt(field, { x: 14, y: 12 })).toMatchObject({ kind: "object", id: "seal_keeper" });
    expect(targetAt(field, { x: 24, y: 18 })).toMatchObject({ kind: "object", id: "workshop_master" });
    expect(interactTarget(field)).toMatchObject({ kind: "object", id: "seal_keeper" });
    expect(hoverText(field, { x: 6, y: 4 })).toBe("守池人");
    expect(field.npcs).toEqual([]);
  });

  it("說明卡：有人的物件名稱前加頭像，沒有人的照舊", () => {
    const field = capital({ x: 6, y: 5 });
    const view = { field, encounter: null, battle_id: null, event: null } as unknown as WorldView;
    const card = (object: string) => renderToStaticMarkup(createElement(FieldObjectCard, { view, object, busy: false, onAct: () => {}, onClose: () => {} }));
    const pool = card("pool_keeper");
    expect(pool).toContain('data-testid="world-object-who"');
    expect(pool).toContain('data-portrait="doll"');
    expect(pool).toContain("守池人");
    expect(pool).toContain("說出你想要的力量"); // WP-2 的暫定台詞（待玩法 PM 給字）
    const well = card("wishing_pool");
    expect(well).not.toContain("world-object-who");
    expect(well).not.toContain("data-portrait");
  });
});

// --- 原 figures6v3.test.ts ---
describe("原 figures6v3.test.ts", () => {
// Phase 6V-3：主城設施格上的人（殿主、酒館老闆、鐵匠、附魔師、傭兵管事）只填資料、用現有部件；
// 公告板上緣「頭像＋一句話」（守印人）；照頭像換算的 NPC 武器欄空著 ＝ 空手（不退回預設的劍）。

interface FacilityRow {
  at: [number, number];
  id: string;
  figure?: FieldFigure;
}
interface SpotRow {
  at: [number, number];
  id: string;
  name_zh: string;
  panel?: string;
  figure?: FieldFigure;
}
const doc = (t: string) => parse(t) as { facilities?: FacilityRow[]; situation_objects?: SpotRow[] };

const FACILITIES: Array<[string, FacilityRow]> = [
  ["capital", capitalYaml],
  ["capital_mentor_hall", hallYaml],
  ["capital_tavern", tavernYaml],
  ["capital_smithy", smithyYaml],
].flatMap(([m, t]) => (doc(t!).facilities ?? []).map((f) => [m!, f] as [string, FacilityRow]));

function field(mapId: string, facilities: FacilityRow[], situation: SpotRow[] = []): FieldView {
  const tiles = Array.from({ length: 32 * 24 }, (_, i) => ({ x: i % 32, y: Math.floor(i / 32), height: 0, terrain: "stone", surface: "none", walkable: true }));
  return {
    map_id: mapId,
    name_zh: mapId,
    region: "capital",
    location: "capital",
    interior: mapId !== "capital",
    width: 32,
    height: 24,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    npcs: [],
    facilities: facilities.map((f) => ({ kind: f.id, x: f.at[0], y: f.at[1], figure: f.figure ?? null })),
    me: { x: 0, y: 0, facing: "s" },
    max_climb: 1,
    walk_max_steps: 30,
    hero: { template_id: "hero_mage", weapon_id: "fire_staff", weapon_class: "focus", doll_look: null, race_look: null, equipment: [] },
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [],
    situation_objects: situation.map((s) => ({ id: s.id, name_zh: s.name_zh, x: s.at[0], y: s.at[1], use: "note", usable: false, note_zh: "", problem_zh: null, panel: s.panel ?? null, stele_region: null, figure: s.figure ?? null })),
    sneaking: false,
    sneak_cost: 1,
    footprints: [],
    buildings: [],
    chasm_style: "default",
    decor: [],
  } as unknown as FieldView;
}

describe("設施格上的人（6V-3）", () => {
  it("內容裡剛好 5 個設施有 figure：殿主、酒館老闆、鐵匠、附魔師、傭兵管事；用現有部件", () => {
    const withFig = FACILITIES.filter(([, f]) => f.figure !== undefined).map(([m, f]) => `${m}:${f.id}`);
    expect(withFig.sort()).toEqual(["capital:hire", "capital_mentor_hall:mentor", "capital_smithy:enchanter", "capital_smithy:smithy", "capital_tavern:tavern"]);
    const known = new Set(["robe", "leather", "mail", "shirt", "plate", "coat", "crown", "hood", "gloves", "apron"]); // QK-8：圍裙（waist apron）
    for (const [, f] of FACILITIES) for (const g of Object.values(f.figure?.portrait.gear ?? {})) expect(known.has(g!.kind), g!.kind).toBe(true);
  });

  it("地圖上多一個不畫血條的紙娃娃，站在設施原格；點那一格照舊是設施", () => {
    for (const [mapId, f] of FACILITIES.filter(([, x]) => x.figure !== undefined)) {
      const view = field(mapId, [f]);
      const spots = facilityFigures(view);
      expect(spots).toHaveLength(1);
      const id = facilityFigureId(f.id);
      const unit = fieldDrawModel(view).units.find((u) => u.id === id);
      expect(unit, id).toBeDefined();
      expect([unit!.x, unit!.y]).toEqual(f.at);
      expect(barlessIds(view).has(id)).toBe(true);
      expect(targetAt(view, { x: f.at[0], y: f.at[1] })).toMatchObject({ kind: "facility", facility: f.id });
    }
  });

  it("鐵匠拿錘子、待機打鐵；殿主拿晶杖；沒拿東西的主手空著", () => {
    const smith = FACILITIES.find(([, f]) => f.id === "smithy")![1];
    const view = field("capital_smithy", [smith]);
    expect(fieldAmbient(view).roles[facilityFigureId("smithy")]).toBe("smith");
    const look = (id: string, f: FacilityRow) => fieldDrawModel(field("m", [f])).units.find((u) => u.id === facilityFigureId(id));
    expect(look("smithy", smith)).toBeDefined();
    const spots = figureSpots(view);
    expect(spots[0]!.figure.held?.kind).toBe("hammer");
    const mentor = FACILITIES.find(([, f]) => f.id === "mentor")![1];
    expect(mentor.figure!.held).toEqual({ kind: "staff", material: "crystal" });
    expect(mentor.figure!.portrait.gear!["head"]!.kind).toBe("crown");
  });
});

describe("公告板上緣的頭像＋一句話（6V-3）", () => {
  const situation = doc(capitalYaml).situation_objects!;
  const view = (f: FieldView) => ({ field: f }) as unknown as WorldView;

  it("主城：守印人（panel: board、有 figure）＋ figure.line_zh；其他城鎮沒有就不顯示", () => {
    const cap = field("capital", [], situation);
    const keeper = boardKeeper(view(cap));
    expect(keeper?.id).toBe("seal_keeper");
    expect(keeper?.figure?.line_zh ?? "").not.toBe("");
    const html = renderToStaticMarkup(createElement(BoardPanel, { characterId: "c", view: view(cap), onClose: () => undefined }));
    expect(html).toContain('data-testid="world-board-keeper"');
    expect(html).toContain("守印人");
    expect(html).toContain(keeper!.figure!.line_zh!);
    expect(boardKeeper(view(field("mist_ferry", [], [])))).toBeNull();
    const plain = renderToStaticMarkup(createElement(BoardPanel, { characterId: "c", view: view(field("mist_ferry", [], [])), onClose: () => undefined }));
    expect(plain).not.toContain("world-board-keeper");
  });
});

describe("既有 NPC 武器欄空著 ＝ 空手（6V-3）", () => {
  const portrait: NpcPortrait = { look: { skin: "#f1c9a5", hair: "bun", beard: false }, gear: { body: { kind: "robe", color: "#6a4a7a" } }, extras: [] } as unknown as NpcPortrait;

  it("照頭像換算的 NPC：主手設成空手（不退回預設的劍）；伺服器給的外觀照舊", () => {
    const look = npcFieldLook({ id: "granny_du", portrait });
    expect((look!.doll_look as { main_kind?: string }).main_kind).toBe(FIGURE_EMPTY_HAND);
    const server = { template_id: "x", doll_look: null, weapon_id: "iron_sword", weapon_class: "melee", race_look: null, equipment: [] } as unknown as NonNullable<FieldView["hero"]>;
    expect(npcFieldLook({ id: "a", look: server, portrait })).toBe(server);
    expect(npcFieldLook({ id: "a" })).toBeNull();
  });
});
});
