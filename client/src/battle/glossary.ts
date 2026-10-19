// 顯示用對照表（色塊、圖示）。之後換美術只改這個檔。
// 中文名與旗標（可燃、致命、不可通行……）不手寫：啟動時讀 /api/glossary（由 content 產生）。
// 內容新增種類時找不到的鍵會退回預設值（顯示 ID），不會壞掉。

import type { Glossary, GlossaryEntry, Surface } from "../api/types";

// ---- 名詞對照（由 /api/glossary 提供；啟動時載入）-------------------------------------------

export type GlossaryCategory =
  | "terrain"
  | "surfaces"
  | "objects"
  | "statuses"
  | "stacks"
  | "reactions"
  | "elements"
  | "attributes";

const index = new Map<GlossaryCategory, Map<string, GlossaryEntry>>();

/** 載入（或在測試中設定）名詞對照表。 */
export function setGlossary(g: Glossary): void {
  index.clear();
  const categories: GlossaryCategory[] = [
    "terrain",
    "surfaces",
    "objects",
    "statuses",
    "stacks",
    "reactions",
    "elements",
    "attributes",
  ];
  for (const c of categories) index.set(c, new Map(g[c].map((e) => [e.id, e])));
}

export function glossaryEntry(category: GlossaryCategory, id: string): GlossaryEntry | undefined {
  return index.get(category)?.get(id);
}

/** 中文名；對照表沒有時顯示 ID。 */
export function glossaryName(category: GlossaryCategory, id: string): string {
  return glossaryEntry(category, id)?.name_zh ?? id;
}

export function glossaryHasTag(category: GlossaryCategory, id: string, tag: string): boolean {
  return glossaryEntry(category, id)?.tags.includes(tag) ?? false;
}

export const statusName = (id: string): string => glossaryName("statuses", id);
export const stackName = (id: string): string => glossaryName("stacks", id);
export const reactionName = (id: string): string => glossaryName("reactions", id);
export const surfaceName = (id: string): string => glossaryName("surfaces", id);
export const objectName = (id: string): string => glossaryName("objects", id);
export const elementName = (id: string): string => glossaryName("elements", id);

// ---- 顯示用對照（色塊、圖示；中文名與旗標來自上面的對照表）--------------------------------------

export interface TerrainStyle {
  name: string;
  color: number;
  /** 不可通行（牆、深淵、岩漿、冰窟）。 */
  blocked: boolean;
  /** 致命地形：被推進去會死。 */
  deadly: boolean;
  /** 牆壁：阻擋視線。 */
  wall: boolean;
}

export const TERRAIN: Readonly<Record<string, { color: number }>> = {
  stone: { color: 0x9a968c },
  grass: { color: 0x6f9a52 },
  dirt: { color: 0x9b7a55 },
  chasm: { color: 0x111118 },
  lava: { color: 0xd8471c },
  ice_hole: { color: 0x17345c },
  wall: { color: 0x4a4440 },
};

const UNKNOWN_TERRAIN_COLOR = 0xff00ff;

export function terrainStyle(terrain: string): TerrainStyle {
  return {
    name: glossaryName("terrain", terrain),
    color: TERRAIN[terrain]?.color ?? UNKNOWN_TERRAIN_COLOR,
    blocked: glossaryHasTag("terrain", terrain, "blocked"),
    deadly: glossaryHasTag("terrain", terrain, "deadly"),
    wall: glossaryHasTag("terrain", terrain, "blocks_sight") && glossaryHasTag("terrain", terrain, "blocked"),
  };
}

export interface SurfaceStyle {
  color: number;
  /** 疊在地形色上的比例（0–1）。 */
  alpha: number;
}

export const SURFACES: Readonly<Record<Surface, SurfaceStyle | null>> = {
  none: null,
  oil: { color: 0x2b2416, alpha: 0.6 },
  water: { color: 0x3a7bd5, alpha: 0.55 },
  fire: { color: 0xff7a1a, alpha: 0.7 },
  ice: { color: 0xc8ecff, alpha: 0.7 },
  poison: { color: 0x7bc043, alpha: 0.6 },
  holy: { color: 0xfff1a8, alpha: 0.6 },
  darkness: { color: 0x3b1f4f, alpha: 0.65 },
};

export interface ObjectStyle {
  name: string;
  /** 格子上的單字圖示。 */
  glyph: string;
  color: number;
  flammable: boolean;
  /** 地板型物件（橋、薄冰、草叢）：畫成整格底色，單位可以站上去。 */
  floor: boolean;
}

interface ObjectLook {
  glyph: string;
  color: number;
  floor: boolean;
}

export const OBJECTS: Readonly<Record<string, ObjectLook>> = {
  wooden_bridge: { glyph: "橋", color: 0x8a5a2b, floor: true },
  oil_barrel: { glyph: "油", color: 0x5a3a1a, floor: false },
  thin_ice: { glyph: "冰", color: 0xaad8f0, floor: true },
  stone_pillar: { glyph: "柱", color: 0x6b6b6b, floor: false },
  grass: { glyph: "草", color: 0x3f7a2a, floor: true },
  crate: { glyph: "箱", color: 0xb07a3a, floor: false },
  earth_wall: { glyph: "土", color: 0x7a5a3a, floor: false },
  low_wall: { glyph: "矮", color: 0x8a8070, floor: false },
  fallen_log: { glyph: "木", color: 0x6a4a2a, floor: false },
};

export function objectStyle(kind: string): ObjectStyle {
  const look = OBJECTS[kind] ?? { glyph: "?", color: 0x888888, floor: false };
  return {
    ...look,
    name: glossaryName("objects", kind),
    flammable: glossaryHasTag("objects", kind, "flammable"),
  };
}

export const END_REASONS: Readonly<Record<string, string>> = {
  eliminate: "全滅",
  escaped: "撤離成功",
  escape_failed: "撤離超時",
  defended: "守住守點",
  point_lost: "守點失守",
  round_limit: "輪數上限",
};

export const DIRECTIONS: Readonly<Record<string, string>> = {
  north: "北",
  east: "東",
  south: "南",
  west: "西",
};

export const TEAM_COLORS: Readonly<Record<"ally" | "enemy", number>> = {
  ally: 0x2f7de1,
  enemy: 0xd23c3c,
};

export const HIGHLIGHT = {
  move: 0x7fe3ff,
  attack: 0xff4040,
  preview: 0xff9a2e,
  direction: 0xffe14d,
  active: 0xffe14d,
  hero: 0xffffff,
  trap: 0xffd23f,
  burning: 0xff5a00,
  flammable: 0xe0a040,
  deadly: 0xff3030,
  trigger: 0xff4fd8,
} as const;
