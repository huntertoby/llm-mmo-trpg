// 由繪製模型推導每個格子、物件的繪圖規格（純函式；Pixi 與 Canvas 都不碰）。
// 高度（3-19 整格抬高）：崖面、描邊、位移改由 Pixi 依 `battle/elevation.ts` 畫，貼圖只含頂面亮度。
import type { DrawModel, ObjectDraw, TileDraw } from "../battle/drawModel";
import { tileAt } from "../battle/drawModel";
import { terrainStyle } from "../battle/glossary";
import type { ObjectArtSpec } from "./objectArt";
import { hasTerrainArt, type Sides, type TileArtSpec } from "./terrainArt";

function neighbor(model: DrawModel, t: { x: number; y: number }, dx: number, dy: number): TileDraw | undefined {
  const x = t.x + dx;
  const y = t.y + dy;
  if (x < 0 || y < 0 || x >= model.width || y >= model.height) return undefined;
  return tileAt(model, { x, y });
}

export function tileArtSpec(model: DrawModel, t: TileDraw): TileArtSpec {
  const n = neighbor(model, t, 0, -1);
  const s = neighbor(model, t, 0, 1);
  const w = neighbor(model, t, -1, 0);
  const e = neighbor(model, t, 1, 0);
  const differs = (nb: TileDraw | undefined): boolean => nb !== undefined && nb.terrain !== t.terrain;
  const same = (nb: TileDraw | undefined): boolean => nb !== undefined && nb.surface === t.surface && t.surface !== "none";
  const surfSame: Sides = { n: same(n), s: same(s), w: same(w), e: same(e) };
  return {
    terrain: t.terrain,
    x: t.x,
    y: t.y,
    height: t.height,
    surface: t.surface,
    surfSame,
    lip: { n: differs(n), s: differs(s), w: differs(w), e: differs(e) },
    wallFace: t.wall && !(s !== undefined && s.wall),
    blocked: t.blocked,
    tint: hasTerrainArt(t.terrain) ? null : terrainStyle(t.terrain).color,
  };
}

/** 物件所在位置 → 種類，供鄰格相依的畫法（矮牆相連、橋的方向）。 */
export function objectKinds(model: DrawModel): Map<string, string> {
  const m = new Map<string, string>();
  for (const o of model.objects) m.set(`${o.x},${o.y}`, o.kind);
  return m;
}

export function objectArtSpec(o: ObjectDraw, kinds: ReadonlyMap<string, string>): ObjectArtSpec {
  const at = (dx: number, dy: number): boolean => kinds.get(`${o.x + dx},${o.y + dy}`) === o.kind;
  return {
    kind: o.kind,
    x: o.x,
    y: o.y,
    joinL: at(-1, 0),
    joinR: at(1, 0),
    vertical: (at(0, -1) || at(0, 1)) && !at(-1, 0) && !at(1, 0),
    flammable: o.flammable,
  };
}

/** 左上角高度徽章的文字：高度 > 0 且至少一個鄰格高度不同才有（高台內部格不標）。 */
export function heightBadgeText(model: DrawModel, t: TileDraw): string | null {
  if (t.blocked || t.height <= 0) return null;
  const edge = (
    [
      [0, -1],
      [0, 1],
      [-1, 0],
      [1, 0],
    ] as const
  ).some(([dx, dy]) => {
    const n = neighbor(model, t, dx, dy);
    return n !== undefined && n.height !== t.height;
  });
  return edge ? String(t.height) : null;
}
