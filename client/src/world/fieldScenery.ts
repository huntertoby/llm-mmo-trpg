// 實地地圖畫面 → 只畫的外觀（Phase 6B-ART1）：建築（`buildings`）、建築正面的門、室內的外框與後牆擺設、家具（物件的 `look`）。
// 純函式、確定性；不改任何規則（走路、視線、戰鬥照伺服器的地形與物件）。
import type { FieldView } from "../api/types";
import { buildingKind, doorStyleOf, type BuildingKind } from "../render/townArt";
import { isFurnitureLook, roomKindOf, roomPalette, wallDecor, type FurnitureLook, type FurnitureSpec } from "../render/interiorArt";
import { EMPTY_SCENERY, type BuildingScene, type DoorScene, type FieldScenery, type InteriorScene } from "../render/sceneryModel";

const key = (x: number, y: number): string => `${x},${y}`;

/** 長條家具：左右鄰格是同一種時接成一條。 */
const LONG: ReadonlySet<FurnitureLook> = new Set<FurnitureLook>(["bar", "counter"]);

/** 建築與正面的門：門格在建築範圍內的才畫成木門／布簾門（其他門照舊用標示）。 */
function buildingsOf(field: FieldView): { buildings: BuildingScene[]; doors: DoorScene[] } {
  const buildings: BuildingScene[] = [];
  const doors: DoorScene[] = [];
  for (const b of field.buildings ?? []) {
    const kind: BuildingKind = buildingKind(b.kind);
    const bottom = b.y + b.height - 1;
    const inside = field.doors.filter((d) => d.x >= b.x && d.x < b.x + b.width && d.y >= b.y && d.y <= bottom);
    const front = inside.filter((d) => d.y === bottom).sort((p, q) => p.x - q.x);
    buildings.push({ spec: { kind, w: b.width, h: b.height, doors: front.map((d) => d.x - b.x) }, x: b.x, y: b.y });
    for (const d of front) doors.push({ x: d.x, y: d.y, style: doorStyleOf(kind) });
  }
  return { buildings, doors };
}

/**
 * 家具：物件的 `look`；附魔台＝`enchanter` 設施那格的物件，那格沒有物件時用正北一格的物件（站位在台子前面）。
 * 長條家具記下左右是否相連。
 */
function furnitureOf(field: FieldView): Record<string, FurnitureSpec> {
  const looks = new Map<string, FurnitureLook>();
  for (const o of field.objects) if (isFurnitureLook(o.look)) looks.set(key(o.x, o.y), o.look);
  const objects = new Set(field.objects.map((o) => key(o.x, o.y)));
  for (const f of field.facilities) {
    if (f.kind !== "enchanter") continue;
    const at = objects.has(key(f.x, f.y)) ? key(f.x, f.y) : objects.has(key(f.x, f.y - 1)) ? key(f.x, f.y - 1) : null;
    if (at !== null) looks.set(at, "enchant");
  }
  const out: Record<string, FurnitureSpec> = {};
  for (const [k, look] of [...looks].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
    const [x, y] = k.split(",").map(Number) as [number, number];
    const long = LONG.has(look);
    out[k] = { look, joinW: long && looks.get(key(x - 1, y)) === look, joinE: long && looks.get(key(x + 1, y)) === look };
  }
  return out;
}

/** 室內：種類照設施、配色照區域（荒原＝鐵灰牆焦木地板）；後牆擺設避開緊貼後牆那一列的物件。 */
function interiorOf(field: FieldView): InteriorScene {
  const kind = roomKindOf(field.facilities.map((f) => f.kind));
  const palette = roomPalette(kind, field.region === "ashen_waste" ? "ashen" : "town");
  const blocked = field.objects.filter((o) => o.y === 1).map((o) => o.x);
  const rugW = Math.min(4, Math.max(0, field.width - 4));
  const rug = kind === "mentor" && rugW > 0 && field.height >= 5 ? { x: Math.floor((field.width - rugW) / 2), y: 2, w: rugW, h: field.height - 3 } : null;
  const exits = field.exits.flatMap((e) => e.cells.map(([x, y]) => ({ x, y }))).sort((a, b) => a.y - b.y || a.x - b.x);
  return { palette, decor: wallDecor(kind, field.width, blocked), rug, exits };
}

/** 這張實地地圖的只畫外觀；什麼都沒有時回傳共用的空外觀。 */
export function fieldScenery(field: FieldView): FieldScenery {
  const { buildings, doors } = buildingsOf(field);
  const furniture = furnitureOf(field);
  const interior = field.interior ? interiorOf(field) : null;
  if (buildings.length === 0 && interior === null && Object.keys(furniture).length === 0) return EMPTY_SCENERY;
  return { buildings, doors, interior, furniture };
}
