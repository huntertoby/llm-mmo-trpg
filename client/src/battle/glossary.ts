// 顯示用對照表（色塊、名稱、圖示）。之後換美術只改這個檔。
// 名稱與標籤抄自 content/terrain.yaml、surfaces.yaml、objects.yaml、statuses.yaml、reactions.yaml；
// 內容新增種類時找不到的鍵會退回預設值（顯示 ID），不會壞掉。

import type { Surface } from "../api/types";

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

export const TERRAIN: Readonly<Record<string, TerrainStyle>> = {
  stone: { name: "石地", color: 0x9a968c, blocked: false, deadly: false, wall: false },
  grass: { name: "草地", color: 0x6f9a52, blocked: false, deadly: false, wall: false },
  dirt: { name: "泥土", color: 0x9b7a55, blocked: false, deadly: false, wall: false },
  chasm: { name: "深淵", color: 0x111118, blocked: true, deadly: true, wall: false },
  lava: { name: "岩漿", color: 0xd8471c, blocked: true, deadly: true, wall: false },
  ice_hole: { name: "冰窟", color: 0x17345c, blocked: true, deadly: true, wall: false },
  wall: { name: "牆壁", color: 0x4a4440, blocked: true, deadly: false, wall: true },
};

export const UNKNOWN_TERRAIN: TerrainStyle = {
  name: "未知地形",
  color: 0xff00ff,
  blocked: false,
  deadly: false,
  wall: false,
};

export interface SurfaceStyle {
  name: string;
  color: number;
  /** 疊在地形色上的比例（0–1）。 */
  alpha: number;
}

export const SURFACES: Readonly<Record<Surface, SurfaceStyle | null>> = {
  none: null,
  oil: { name: "油", color: 0x2b2416, alpha: 0.6 },
  water: { name: "水", color: 0x3a7bd5, alpha: 0.55 },
  fire: { name: "火焰", color: 0xff7a1a, alpha: 0.7 },
  ice: { name: "冰", color: 0xc8ecff, alpha: 0.7 },
  poison: { name: "毒", color: 0x7bc043, alpha: 0.6 },
  holy: { name: "聖光", color: 0xfff1a8, alpha: 0.6 },
  darkness: { name: "黑暗", color: 0x3b1f4f, alpha: 0.65 },
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

export const OBJECTS: Readonly<Record<string, ObjectStyle>> = {
  wooden_bridge: { name: "木橋", glyph: "橋", color: 0x8a5a2b, flammable: true, floor: true },
  oil_barrel: { name: "油桶", glyph: "油", color: 0x5a3a1a, flammable: true, floor: false },
  thin_ice: { name: "薄冰", glyph: "冰", color: 0xaad8f0, flammable: false, floor: true },
  stone_pillar: { name: "石柱", glyph: "柱", color: 0x6b6b6b, flammable: false, floor: false },
  grass: { name: "草叢", glyph: "草", color: 0x3f7a2a, flammable: true, floor: true },
  crate: { name: "木箱", glyph: "箱", color: 0xb07a3a, flammable: true, floor: false },
  earth_wall: { name: "土牆", glyph: "土", color: 0x7a5a3a, flammable: false, floor: false },
  low_wall: { name: "矮牆", glyph: "矮", color: 0x8a8070, flammable: false, floor: false },
  fallen_log: { name: "倒木", glyph: "木", color: 0x6a4a2a, flammable: true, floor: false },
};

export function objectStyle(kind: string): ObjectStyle {
  return OBJECTS[kind] ?? { name: kind, glyph: "?", color: 0x888888, flammable: false, floor: false };
}

export function terrainStyle(terrain: string): TerrainStyle {
  return TERRAIN[terrain] ?? { ...UNKNOWN_TERRAIN, name: terrain };
}

export const STATUS_NAMES: Readonly<Record<string, string>> = {
  defending: "防禦",
  prone: "倒地",
  burning: "燃燒",
  concealed: "隱蔽",
  slow: "緩速",
  root: "定身",
  stun: "暈眩",
  frozen: "冰凍",
  weaken: "虛弱",
  vulnerable: "易傷",
  bleed: "流血",
  poison: "中毒",
  guarded: "護衛",
  empowered: "激昂",
  hasted: "加速",
  regenerating: "再生",
  shielded: "護盾",
  taunted: "嘲諷",
  feared: "恐懼",
  silenced: "沉默",
  blinded: "致盲",
  marked: "被標記",
  stance_fury: "狂怒姿態",
  stance_bulwark: "堅壁姿態",
};

export const REACTION_NAMES: Readonly<Record<string, string>> = {
  block: "格擋",
  opportunity_attack: "藉機攻擊",
};

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
  active: 0xffe14d,
  hero: 0xffffff,
  trap: 0xffd23f,
  burning: 0xff5a00,
  flammable: 0xe0a040,
  deadly: 0xff3030,
} as const;

export function statusName(id: string): string {
  return STATUS_NAMES[id] ?? id;
}

export function reactionName(id: string): string {
  return REACTION_NAMES[id] ?? id;
}
