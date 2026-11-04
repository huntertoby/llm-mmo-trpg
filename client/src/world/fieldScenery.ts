// 實地地圖畫面 → 只畫的外觀（Phase 6B-ART1）：建築（`buildings`）、建築正面的門、室內的外框與後牆擺設、家具（物件的 `look`）。
// 6D-ART2：主城的建築、側牆的門、中央傳送陣與區旗、源晶燈、橋頭石碑、浮橋；屋後站著東西時屋頂不往上蓋；招牌照門通往的室內。
// 純函式、確定性；不改任何規則（走路、視線、戰鬥照伺服器的地形與物件）。
import type { FieldView } from "../api/types";
import { buildingKind, doorStyleOf, signFromView, type BuildingKind, type BuildingSpec } from "../render/townArt";
import { isFurnitureLook, roomKindOf, roomPalette, wallDecor, wallHangings, type FurnitureLook, type FurnitureSpec } from "../render/interiorArt";
import type { BridgeSide } from "../render/capitalArt";
import { EMPTY_SCENERY, type BuildingScene, type DoorScene, type FieldScenery, type InteriorScene, type PlazaScene } from "../render/sceneryModel";

const key = (x: number, y: number): string => `${x},${y}`;

/** 長條家具：左右鄰格是同一種時接成一條。 */
const LONG: ReadonlySet<FurnitureLook> = new Set<FurnitureLook>(["bar", "counter"]);

/** 不往上蓋屋頂的種類：噴水池是平的。 */
const FLAT: ReadonlySet<BuildingKind> = new Set<BuildingKind>(["fountain"]);

/**
 * 屋頂往上多蓋那一列（建築範圍正北一列）站著東西的格子：NPC、設施、情境物件、傳送石（開發 PM 補充 1）。
 * 這些格子上有東西時，那一棟的屋頂收在自己的範圍內，不往上蓋。路過的玩家不算（照舊畫虛線剪影）。
 */
function standingCells(field: FieldView): Set<string> {
  return new Set([
    ...field.npcs.map((n) => key(n.x, n.y)),
    ...field.facilities.map((f) => key(f.x, f.y)),
    ...(field.situation_objects ?? []).map((o) => key(o.x, o.y)),
    ...field.stones.map((s) => key(s.x, s.y)),
  ]);
}

/** 畫成建築門板的門格（最下一列與側牆的門）：這些門不再畫淡黃色門框（開發 PM 補充 3）；其他門照舊有框。 */
export function buildingDoorCells(field: FieldView): Set<string> {
  return new Set(buildingsOf(field).doors.map((d) => key(d.x, d.y)));
}

/**
 * 建築與正面的門：最下一列的門畫在原地；側牆的門（左右兩欄、不在最下一列）畫在同一欄的最下一列，入口光圈在門外側。
 * 其他門照舊用標示。
 */
function buildingsOf(field: FieldView): { buildings: BuildingScene[]; doors: DoorScene[] } {
  const buildings: BuildingScene[] = [];
  const doors: DoorScene[] = [];
  const standing = standingCells(field);
  for (const b of field.buildings ?? []) {
    const kind: BuildingKind = buildingKind(b.kind);
    const bottom = b.y + b.height - 1;
    const inside = field.doors.filter((d) => d.x >= b.x && d.x < b.x + b.width && d.y >= b.y && d.y <= bottom).sort((p, q) => p.x - q.x || p.y - q.y);
    const drawn: DoorScene[] = [];
    for (const d of inside) {
      if (d.y === bottom) drawn.push({ x: d.x, y: d.y, style: doorStyleOf(kind) });
      else if (d.x === b.x) drawn.push({ x: d.x, y: d.y, style: doorStyleOf(kind), side: "w", drawY: bottom });
      else if (d.x === b.x + b.width - 1) drawn.push({ x: d.x, y: d.y, style: doorStyleOf(kind), side: "e", drawY: bottom });
    }
    const cols = [...new Set(drawn.map((d) => d.x - b.x))].sort((p, q) => p - q);
    const behind = Array.from({ length: b.width }, (_, i) => key(b.x + i, b.y - 1));
    const spec: BuildingSpec = { kind, w: b.width, h: b.height, doors: cols };
    if (FLAT.has(kind) || behind.some((c) => standing.has(c))) spec.roof = 0;
    const sign = signFromView(kind, b.sign);
    if (sign !== undefined) spec.sign = sign;
    buildings.push({ spec, x: b.x, y: b.y });
    doors.push(...drawn);
  }
  return { buildings, doors };
}

/** 物件格在地圖哪一邊的邊上（浮橋往哪裡）；不在邊上＝往北。 */
function edgeSide(field: FieldView, x: number, y: number): BridgeSide {
  if (y === 0) return "n";
  if (y === field.height - 1) return "s";
  if (x === 0) return "w";
  if (x === field.width - 1) return "e";
  return "n";
}

/** 一件家具的畫法輸入（長條家具與浮橋記下鄰格是否相連；石碑記下紋章的區域）。 */
function furnitureSpec(field: FieldView, looks: ReadonlyMap<string, FurnitureLook>, x: number, y: number, look: FurnitureLook): FurnitureSpec {
  if (look === "sky_bridge") {
    const side = edgeSide(field, x, y);
    const ns = side === "n" || side === "s";
    const [a, b] = ns ? [key(x - 1, y), key(x + 1, y)] : [key(x, y - 1), key(x, y + 1)];
    return { look, joinW: looks.get(a) === look, joinE: looks.get(b) === look, side };
  }
  if (look === "stele") {
    const region = (field.situation_objects ?? []).find((o) => o.x === x && o.y === y)?.stele_region ?? "";
    return { look, joinW: false, joinE: false, region };
  }
  const long = LONG.has(look);
  return { look, joinW: long && looks.get(key(x - 1, y)) === look, joinE: long && looks.get(key(x + 1, y)) === look };
}

/**
 * 家具：物件的 `look`；附魔台＝`enchanter` 設施那格的物件，那格沒有物件時用正北一格的物件（站位在台子前面）。
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
    out[k] = furnitureSpec(field, looks, x, y, look);
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
  const decor = wallDecor(kind, field.width, blocked);
  return { palette, decor, hangings: wallHangings(kind, field.width, blocked, decor), rug, exits };
}

/** 主城（`region: capital`、室外）的中央傳送陣：第一顆傳送石（依座標排序）；`open` 照大世界圖已開放的區。 */
function plazaOf(field: FieldView, openRegions: readonly string[]): PlazaScene | null {
  if (field.region !== "capital" || field.interior) return null;
  const stone = [...field.stones].sort((a, b) => a.y - b.y || a.x - b.x)[0];
  if (stone === undefined) return null;
  return { x: stone.x, y: stone.y, open: [...new Set(openRegions)].sort() };
}

/**
 * 這張實地地圖的只畫外觀；什麼都沒有時回傳共用的空外觀。
 * `openRegions` ＝ 大世界圖已開放的區（`atlas.regions` 的 `status: open`；不新增伺服器欄位），只用在主城的傳送陣。
 */
export function fieldScenery(field: FieldView, openRegions: readonly string[] = []): FieldScenery {
  const { buildings, doors } = buildingsOf(field);
  const furniture = furnitureOf(field);
  const interior = field.interior ? interiorOf(field) : null;
  const plaza = plazaOf(field, openRegions);
  if (buildings.length === 0 && interior === null && Object.keys(furniture).length === 0 && plaza === null) return EMPTY_SCENERY;
  return plaza === null ? { buildings, doors, interior, furniture } : { buildings, doors, interior, furniture, plaza };
}

/** 大世界圖已開放的區（依區域 ID 排序）；沒有大世界圖＝空（傳送陣全灰）。 */
export function openRegionsOf(atlas: { regions: readonly { region: string; status: string }[] } | null | undefined): string[] {
  return (atlas?.regions ?? [])
    .filter((r) => r.status === "open")
    .map((r) => r.region)
    .sort();
}

