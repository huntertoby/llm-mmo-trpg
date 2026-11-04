// 測試用：照主城地圖檔（content/world/fields/capital/capital.yaml）組一張 FieldView（6V-4／6V-4b）。
// 地形、物件、建築、表面、門、傳送石、設施、情境物件，加上 6V-4b 的 `look.decor`（同伺服器 `world_field_view._decor`）。
import { parse } from "yaml";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import type { FieldView } from "../api/types";

type XY = [number, number];

export interface CapitalDoc {
  size: XY;
  terrain: string;
  legend: Record<string, string>;
  objects: Array<{ at: XY; kind: string; look?: string }>;
  buildings: Array<{ kind: string; at: XY; size: XY }>;
  surfaces: Array<{ at: XY; surface: string }>;
  doors: Array<{ id: string; at: XY }>;
  teleport_stones: Array<{ id: string; at: XY }>;
  facilities: Array<{ at: XY; id: string }>;
  situation_objects: Array<{ at: XY; id: string; name_zh?: string }>;
  look?: { decor?: Array<{ kind: FieldView["decor"][number]["kind"]; at: XY; size?: XY; center?: XY }> };
}

export const capitalDoc = parse(capitalYaml) as CapitalDoc;

/** 內容的種類表（`trpg.content.fields.DECOR_LAYERS` / `DECOR_FIXED_SIZE`）；伺服器照這個給 `layer`、寬高。 */
const LAYERS = { flower_bed: "ground", stall_cloth: "ground", clothesline: "standing", crate_stack: "standing", radial_paving: "ground" } as const;
const FIXED: Readonly<Record<string, XY>> = { flower_bed: [1, 1], stall_cloth: [1, 1], clothesline: [3, 1], crate_stack: [1, 1] };

/** 地圖檔的 `look.decor` → API 的 `FieldView.decor`（依內容順序）。 */
export function decorViews(doc: CapitalDoc = capitalDoc): FieldView["decor"] {
  return (doc.look?.decor ?? []).map((d) => {
    const [w, h] = d.size ?? FIXED[d.kind]!;
    return { kind: d.kind, layer: LAYERS[d.kind], x: d.at[0], y: d.at[1], width: w, height: h, center_x: d.center?.[0] ?? null, center_y: d.center?.[1] ?? null };
  });
}

/** 照主城地圖檔組一張 FieldView。`withDecor: false` ＝ 不帶裝飾（模擬舊伺服器）。 */
export function capitalField(withDecor = true): FieldView {
  const doc = capitalDoc;
  const rows = doc.terrain.trim().split("\n");
  const surf = new Map(doc.surfaces.map((s) => [`${s.at[0]},${s.at[1]}`, s.surface]));
  const tiles = rows.flatMap((row, y) => [...row].map((ch, x) => ({ x, y, height: 0, terrain: doc.legend[ch]!, surface: surf.get(`${x},${y}`) ?? "none", walkable: true })));
  return {
    map_id: "capital",
    region: "capital",
    interior: false,
    width: doc.size[0],
    height: doc.size[1],
    tiles,
    objects: doc.objects.map((o, i) => ({ id: `o${i}`, kind: o.kind, x: o.at[0], y: o.at[1], look: o.look ?? null })),
    buildings: doc.buildings.map((b) => ({ kind: b.kind, x: b.at[0], y: b.at[1], width: b.size[0], height: b.size[1], sign: null })),
    doors: doc.doors.map((d) => ({ id: d.id, x: d.at[0], y: d.at[1] })),
    stones: doc.teleport_stones.map((s) => ({ id: s.id, x: s.at[0], y: s.at[1], unlocked: true })),
    facilities: doc.facilities.map((f) => ({ kind: f.id, x: f.at[0], y: f.at[1], figure: null })),
    situation_objects: doc.situation_objects.map((s) => ({ id: s.id, name_zh: s.name_zh ?? "", x: s.at[0], y: s.at[1] })),
    npcs: [],
    exits: [],
    decor: withDecor ? decorViews(doc) : [],
  } as unknown as FieldView;
}
