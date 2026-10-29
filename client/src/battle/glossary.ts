// 顯示用對照表（色塊、圖示）。之後換美術只改這個檔。
// 中文名與旗標（可燃、致命、不可通行……）不手寫：啟動時讀 /api/glossary（由 content 產生）。
// 內容新增種類時找不到的鍵會退回預設值（顯示 ID），不會壞掉。

import type { Glossary, GlossaryEntry, StatusLook, Surface, WeaponLookEntry } from "../api/types";
import { SURFACE_GROUND_COLOR } from "../render/palette";

// ---- 名詞對照（由 /api/glossary 提供；啟動時載入）-------------------------------------------

export type GlossaryCategory =
  | "terrain"
  | "surfaces"
  | "objects"
  | "statuses"
  | "stacks"
  | "reactions"
  | "elements"
  | "attributes"
  | "effects"
  | "conditions"
  | "triggers"
  | "actions"
  | "objectives";

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
    "effects",
    "conditions",
    "triggers",
    "actions",
    "objectives",
  ];
  for (const c of categories) index.set(c, new Map((g[c] ?? []).map((e) => [e.id, e])));
  weaponLooks.clear();
  for (const w of g.weapon_looks ?? []) weaponLooks.set(w.id, w);
}

/** 武器預設外觀（`/api/glossary` 的 `weapon_looks`；`weapons.yaml` 的 `look`）。 */
const weaponLooks = new Map<string, WeaponLookEntry>();

export function weaponLookEntry(id: string): WeaponLookEntry | undefined {
  return weaponLooks.get(id);
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

/** 代價狀態（技能代價自己付的狀態，3-50c）的註記。 */
export const COST_STATUS_NOTE = "（代價狀態，無法淨化）";
/** 狀態圖示與身上特效用的欄位（`/api/glossary` 的 `status_look`）；沒有資料時為 `undefined`。 */
export const statusLook = (id: string): StatusLook | undefined => glossaryEntry("statuses", id)?.status_look ?? undefined;
export const stackName = (id: string): string => glossaryName("stacks", id);
export const reactionName = (id: string): string => glossaryName("reactions", id);
export const surfaceName = (id: string): string => glossaryName("surfaces", id);
/** 擋視線的表面（煙霧、黑暗…；內容資料的 `blocks_sight`）：單位之上多畫一層霧。 */
export const surfaceBlocksSight = (id: string): boolean => glossaryHasTag("surfaces", id, "blocks_sight");
export const objectName =(id: string): string => glossaryName("objects", id);
export const elementName = (id: string): string => glossaryName("elements", id);
export const effectName = (id: string): string => glossaryName("effects", id);
export const conditionName = (id: string): string => glossaryName("conditions", id);
export const triggerName = (id: string): string => glossaryName("triggers", id);

/** 效果原語、條件、觸發的玩家說明（內容檔的 `player_description`／`description_zh`）；沒有時為空字串。 */
export const glossaryDescription = (category: GlossaryCategory, id: string): string => glossaryEntry(category, id)?.description_zh ?? "";

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

/** 表面的顏色取自 `render/palette.ts`（單一來源），這裡只決定疊色比例。 */
const ground = (id: string, alpha: number): SurfaceStyle => ({ color: parseInt((SURFACE_GROUND_COLOR[id] ?? "#888888").slice(1), 16), alpha });

export const SURFACES: Readonly<Record<Surface, SurfaceStyle | null>> = {
  none: null,
  oil: ground("oil", 0.6),
  water: ground("water", 0.55),
  fire: ground("fire", 0.7),
  ice: ground("ice", 0.7),
  poison: ground("poison", 0.6),
  holy: ground("holy", 0.6),
  darkness: ground("darkness", 0.65),
  smoke: ground("smoke", 0.6),
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
  thin_ice: { glyph: "薄", color: 0xaad8f0, floor: true },
  stone_pillar: { glyph: "柱", color: 0x6b6b6b, floor: false },
  grass: { glyph: "草", color: 0x3f7a2a, floor: true },
  crate: { glyph: "箱", color: 0xb07a3a, floor: false },
  earth_wall: { glyph: "土", color: 0x7a5a3a, floor: false },
  low_wall: { glyph: "矮", color: 0x8a8070, floor: false },
  fallen_log: { glyph: "木", color: 0x6a4a2a, floor: false },
  dead_tree: { glyph: "樹", color: 0x5a4a32, floor: false },
  rubble: { glyph: "礫", color: 0x7a7468, floor: false },
  ice_wall: { glyph: "冰", color: 0x8fd3f0, floor: false },
  thorn_wall: { glyph: "棘", color: 0x4f7a2a, floor: false },
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
  /** 被揭露的敵方陷阱（Phase 3C-6a）。 */
  trap_revealed: 0xff5a5a,
  /** 源泉格（Phase 3C-6a）。 */
  well: 0xb98cff,
  /** 撤離的出口格（Phase 3-22）。 */
  exit: 0x5ee08a,
  /** 守點格（Phase 3-22）。 */
  point: 0xffc83d,
  burning: 0xff5a00,
  flammable: 0xe0a040,
  deadly: 0xff3030,
  trigger: 0xff4fd8,
  // 場景物件預覽（Phase 3C-5b）：穿透路線與穿過的物件、後方單位、推倒壓住的格子、倒塌物、投擲的物件與落點
  route: 0xffe14d,
  pierced: 0x4fd8ff,
  behind: 0xffa94d,
  crush: 0xc0392b,
  rubble: 0xb08a60,
  picked: 0x4fd8ff,
  landing: 0x7dff7d,
  // 自身位移預覽（Phase 3D-2）：衝鋒的路線與終點、跳躍的落點、交換的兩格
  dash: 0xff8c42,
  leap: 0x7dd3ff,
  swap: 0xd88cff,
  // 攀跳的落點（Phase 3-21b）
  vault: 0xb36bff,
  // 位移他人預覽（Phase 3D-2b）：被傳送的單位、落點、致命地形的落點
  banish: 0xb98cff,
  banish_lethal: 0xff3030,
  // 召喚（Phase 3D-4b）：召喚物的外框、預覽的召喚位置與圖騰光環
  summon: 0x5eead4,
  /** 持續區域（Phase 3D-5）：有害（傷害、減益）與有益的底色。 */
  zone_harmful: 0xff6a3d,
  zone_helpful: 0xffd54a,
  /** 不影響我方的持續區域（3-37b）：虛線外框＋淡底色。 */
  zone_neutral: 0xb0b8c4,
  /** 定時炸彈（Phase 3D-8b）：預覽的爆炸範圍與倒數；倒地的友方（可復活）與復活的位置。 */
  bomb: 0xff7a1a,
  downed: 0xff3b30,
  revive: 0x7dff7d,
  /** 複合技能（Phase 3F-3b）：動作段的範圍（紫色）。 */
  followup: 0xc77dff,
} as const;
