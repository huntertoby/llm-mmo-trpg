// 由繪製模型推導每個格子、物件的繪圖規格（純函式；Pixi 與 Canvas 都不碰）。
// 高度（3-19 整格抬高）：崖面、描邊、位移改由 Pixi 依 `battle/elevation.ts` 畫，貼圖只含頂面亮度。
import type { DrawModel, ObjectDraw, TileDraw } from "../battle/drawModel";
import { tileAt } from "../battle/drawModel";
import { terrainStyle } from "../battle/glossary";
import { hpStageOf } from "./fieldFx";
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
    turnsLeft: o.expiresIn,
    hpStage: hpStageOf(o.hpRatio),
  };
}

const NEIGHBORS = [
  [0, -1],
  [0, 1],
  [-1, 0],
  [1, 0],
] as const;

/** 同高、相連（四方向）、可站立、高度 > 0 的一片格子；回傳這一片的格子與是否有鄰格不同高。 */
function heightRegion(model: DrawModel, start: TileDraw, seen: Set<string>): { tiles: TileDraw[]; edge: boolean } {
  const tiles: TileDraw[] = [];
  let edge = false;
  const stack = [start];
  seen.add(`${start.x},${start.y}`);
  for (let t = stack.pop(); t !== undefined; t = stack.pop()) {
    tiles.push(t);
    for (const [dx, dy] of NEIGHBORS) {
      const n = neighbor(model, t, dx, dy);
      if (n === undefined) continue;
      if (n.height !== t.height) edge = true;
      const key = `${n.x},${n.y}`;
      if (n.height === t.height && !n.blocked && !seen.has(key)) {
        seen.add(key);
        stack.push(n);
      }
    }
  }
  return { tiles, edge };
}

const badgeCache = new WeakMap<DrawModel, ReadonlyMap<string, string>>();

/**
 * 高度徽章（3-21b，美術 PM 檢查）：同高、相連的一片只標一個，放在這片最上排最左邊的格子；單獨一格照標；
 * 整張圖都同高（沒有任何鄰格不同高）的一片不標。鍵為 `x,y`，值為高度文字。
 */
export function heightBadges(model: DrawModel): ReadonlyMap<string, string> {
  const cached = badgeCache.get(model);
  if (cached !== undefined) return cached;
  const badges = new Map<string, string>();
  const seen = new Set<string>();
  for (const t of model.tiles) {
    if (t.blocked || t.height <= 0 || seen.has(`${t.x},${t.y}`)) continue;
    const { tiles, edge } = heightRegion(model, t, seen);
    if (!edge) continue;
    const anchor = tiles.reduce((a, b) => (b.y < a.y || (b.y === a.y && b.x < a.x) ? b : a));
    badges.set(`${anchor.x},${anchor.y}`, String(t.height));
  }
  badgeCache.set(model, badges);
  return badges;
}

/** 左上角高度徽章的文字：這一格是它那一片的徽章位置時才有（見 :func:`heightBadges`）。 */
export function heightBadgeText(model: DrawModel, t: TileDraw): string | null {
  return heightBadges(model).get(`${t.x},${t.y}`) ?? null;
}
