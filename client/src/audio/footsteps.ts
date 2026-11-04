// 腳步聲依地表（AU-3；docs/art/音效與音樂方案.md 2.1「腳步」列）：探索與戰鬥共用。純函式，只讀畫面資料。
// 優先順序：表面（水、冰、油）→ 室內地板（木板、石板）→ 地形（草、石、土；荒原的土是沙）。
// 變體鍵＝「地圖:x,y:第幾步」，同一條路重走聲音一樣（`vary` 的音高微調照鍵）。

export const STEP_SOUNDS = ["step_grass", "step_stone", "step_dirt", "step_wood", "step_water", "step_ice", "step_sand"] as const;
export type StepSound = (typeof STEP_SOUNDS)[number];

export interface StepGround {
  terrain: string;
  surface?: string | null;
}

export interface StepPlace {
  region?: string | null;
  /** 室內地板（`render/interiorArt.ts` 的 `roomPalette().style`）；室外 `null`。 */
  floor?: "plank" | "slab" | null;
}

const SURFACE_STEP: Readonly<Partial<Record<string, StepSound>>> = { water: "step_water", oil: "step_water", ice: "step_ice" };
const TERRAIN_STEP: Readonly<Partial<Record<string, StepSound>>> = { grass: "step_grass", stone: "step_stone", dirt: "step_dirt", lava: "step_stone", ice_hole: "step_ice", wall: "step_stone" };

/** 這一格走起來是什麼聲音。 */
export function stepSoundFor(ground: StepGround | null | undefined, place: StepPlace = {}): StepSound {
  const s = ground?.surface == null ? null : SURFACE_STEP[ground.surface];
  if (s !== undefined && s !== null) return s;
  if (place.floor === "plank") return "step_wood";
  if (place.floor === "slab") return "step_stone";
  const t = ground === null || ground === undefined ? undefined : TERRAIN_STEP[ground.terrain];
  if (t === "step_dirt" && place.region === "ashen_waste") return "step_sand";
  return t ?? "step_dirt";
}

export const stepKey = (mapId: string, x: number, y: number, n: number): string => `${mapId}:${x},${y}:${n}`;
