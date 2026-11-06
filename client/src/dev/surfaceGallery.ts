// 開發用：地表併塊示範場景（Phase 6A-4a；docs/archive/art/戰鬥D版樣張.md 第 2 節）。
// 在 fx-gallery.html 的第二個場景畫出來：冰、油、火、水、毒、聖光、黑暗、煙霧各一塊（單格、一排、L 形、
// 有內凹角的 2×2 缺角、異種相鄰），外加我方陷阱與已揭露的敵方陷阱。待機畫面：沒有格線、沒有高亮。
import type { BattleView, TileView, TrapView, UnitView } from "../api/types";
import { tile, unit } from "../battle/testFixtures";

export const SURFACE_GALLERY_W = 12;
export const SURFACE_GALLERY_H = 8;

/** 地圖（每格一個字元）：. 無、i 冰、o 油、f 火、w 水、p 毒、h 聖光、d 黑暗、s 煙霧。 */
const MAP = [
  "iii..oo..f..",
  "i.i..o..ff..",
  "iii.....fff.",
  "....ww......",
  ".pp.wwwhh...",
  ".pp..w.hh.ss",
  "..p.dd...sss",
  "....d.ioos..",
];

const CODE: Readonly<Record<string, string>> = { i: "ice", o: "oil", f: "fire", w: "water", p: "poison", h: "holy", d: "darkness", s: "smoke" };

export const SURFACE_GALLERY_HERO = "unit_0001";

export function surfaceGalleryView(): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < SURFACE_GALLERY_H; y++) {
    for (let x = 0; x < SURFACE_GALLERY_W; x++) {
      const surface = CODE[MAP[y]![x]!] ?? "none";
      tiles.push(tile(x, y, { terrain: x >= 10 && y <= 1 ? "grass" : "stone", surface: surface as TileView["surface"] }));
    }
  }
  const units: UnitView[] = [
    unit(SURFACE_GALLERY_HERO, "ally", 1, 1, { template_id: "hero_fighter", name_zh: "主角" }),
    unit("unit_0002", "enemy", 9, 1, { name_zh: "敵人" }),
    unit("unit_0003", "enemy", 5, 4, { name_zh: "敵人" }),
  ];
  const traps: TrapView[] = [
    { owner_id: SURFACE_GALLERY_HERO, team: "ally", pos: { x: 3, y: 1 }, skill_id: "t_fire", remaining: 2 },
    { owner_id: "unit_0002", team: "enemy", pos: { x: 10, y: 3 }, skill_id: "t_poison", remaining: 2 },
  ];
  return {
    team: "ally",
    map_id: "surface_gallery",
    map_name_zh: "地表併塊",
    width: SURFACE_GALLERY_W,
    height: SURFACE_GALLERY_H,
    tiles,
    objects: [],
    units,
    traps,
    turn_order: [SURFACE_GALLERY_HERO],
    active_unit: SURFACE_GALLERY_HERO,
    round: 1,
    max_rounds: 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
  } as unknown as BattleView;
}
