// 由繪製模型推導每個格子、物件的繪圖規格（純函式；Pixi 與 Canvas 都不碰）。
// 與 3-14 的高度表現整合：高度差、懸崖、陰影的判斷都在這裡，繪圖端只照規格畫。
import type { DrawModel, ObjectDraw, TileDraw } from "../battle/drawModel";
import { tileAt } from "../battle/drawModel";
import { terrainStyle } from "../battle/glossary";
import type { ObjectArtSpec } from "./objectArt";
import { hasTerrainArt, type Sides, type TileArtSpec } from "./terrainArt";

/** 南側崖面高度：每一層高度差 5 虛擬像素，上限 15。 */
export const DROP_PX_PER_LEVEL = 5;
export const DROP_MAX_PX = 15;

function neighbor(model: DrawModel, t: { x: number; y: number }, dx: number, dy: number): TileDraw | undefined {
  const x = t.x + dx;
  const y = t.y + dy;
  if (x < 0 || y < 0 || x >= model.width || y >= model.height) return undefined;
  return tileAt(model, { x, y });
}

const isHole = (t: TileDraw | undefined): boolean => t !== undefined && t.blocked && !t.wall;

/**
 * 鄰格相對本格的「落差」：鄰格可站立 → 高度差；鄰格是深淵、岩漿、冰窟 → 本格高度（視為低到底）；
 * 牆、地圖外 → 0（不畫）。正值表示鄰格比本格低。
 */
function dropTo(self: TileDraw, n: TileDraw | undefined): number {
  if (n === undefined || self.blocked) return 0;
  if (isHole(n)) return Math.max(0, self.height);
  if (n.blocked) return 0;
  return Math.max(0, self.height - n.height);
}

/** 較高的鄰格投在本格的陰影強度（高度差）；本格不可站立或鄰格不可站立時為 0。 */
function riseFrom(self: TileDraw, n: TileDraw | undefined): number {
  if (n === undefined || self.blocked || n.blocked) return 0;
  return Math.max(0, n.height - self.height);
}

export function tileArtSpec(model: DrawModel, t: TileDraw): TileArtSpec {
  const n = neighbor(model, t, 0, -1);
  const s = neighbor(model, t, 0, 1);
  const w = neighbor(model, t, -1, 0);
  const e = neighbor(model, t, 1, 0);
  const differs = (nb: TileDraw | undefined): boolean => nb !== undefined && nb.terrain !== t.terrain;
  const same = (nb: TileDraw | undefined): boolean => nb !== undefined && nb.surface === t.surface && t.surface !== "none";
  const surfSame: Sides = { n: same(n), s: same(s), w: same(w), e: same(e) };
  const dropLevels = dropTo(t, s);
  return {
    terrain: t.terrain,
    x: t.x,
    y: t.y,
    height: t.height,
    surface: t.surface,
    surfSame,
    lip: { n: differs(n), s: differs(s), w: differs(w), e: differs(e) },
    wallFace: t.wall && !(s !== undefined && s.wall),
    drop: Math.min(DROP_MAX_PX, dropLevels * DROP_PX_PER_LEVEL),
    shadowN: riseFrom(t, n),
    shadowW: riseFrom(t, w),
    lowerW: dropTo(t, w) > 0,
    lowerE: dropTo(t, e) > 0,
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
