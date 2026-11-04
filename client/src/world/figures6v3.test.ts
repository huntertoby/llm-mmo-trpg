// Phase 6V-3：主城設施格上的人（殿主、酒館老闆、鐵匠、附魔師、傭兵管事）只填資料、用現有部件；
// 公告板上緣「頭像＋一句話」（守印人）；照頭像換算的 NPC 武器欄空著 ＝ 空手（不退回預設的劍）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import hallYaml from "../../../content/world/fields/capital/interiors/capital_mentor_hall.yaml?raw";
import tavernYaml from "../../../content/world/fields/capital/interiors/capital_tavern.yaml?raw";
import smithyYaml from "../../../content/world/fields/capital/interiors/capital_smithy.yaml?raw";
import type { FieldFigure, FieldView, NpcPortrait, WorldView } from "../api/types";
import { BoardPanel, boardKeeper } from "./BoardPanel";
import { fieldAmbient } from "./fieldAmbient";
import { barlessIds, facilityFigures, fieldDrawModel, figureSpots, targetAt } from "./fieldModel";
import { facilityFigureId, FIGURE_EMPTY_HAND, npcFieldLook } from "./npcLook";

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
    const known = new Set(["robe", "leather", "mail", "shirt", "plate", "coat", "crown", "hood", "gloves"]);
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
