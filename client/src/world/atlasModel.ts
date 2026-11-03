// 大世界圖（Phase 6D-5；21.1、9.6.5「碎界」）與主城情境物件的純函式。
// 規則一律由後端算好（`AtlasView`：三種狀態、解鎖條件、能不能傳送），這裡只決定浮島的位置、外觀與說明文字。
// 浮島的方位照主城五座浮橋（6D-4 待決 4，美術定案時一起改）：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮；主城在中央。
import type { AtlasRegionView, AtlasView, WorldMapView } from "../api/types";
import type { HudPanel } from "./hud";

/** 浮島中心（0～100 的相對座標）與大小（寬度，同一座標系）。 */
export interface IslandSpot {
  x: number;
  y: number;
  size: number;
}

export const CAPITAL_SPOT: IslandSpot = { x: 50, y: 47, size: 16 };

const SPOTS: Readonly<Record<string, IslandSpot>> = {
  crystal_crown: { x: 50, y: 17, size: 18 },
  cloud_ridge: { x: 16, y: 48, size: 20 },
  arcane_hub: { x: 84, y: 40, size: 18 },
  ashen_waste: { x: 42, y: 76, size: 20 },
  frost_tide: { x: 78, y: 74, size: 18 },
};

/** 沒列在上面的區（內容新增的）：沿外圈依序排。 */
function fallbackSpot(index: number): IslandSpot {
  const angle = (index / 5) * Math.PI * 2;
  return { x: Math.round(50 + 35 * Math.cos(angle)), y: Math.round(50 + 35 * Math.sin(angle)), size: 20 };
}

export interface AtlasIsland {
  region: string;
  name: string;
  status: AtlasRegionView["status"];
  spot: IslandSpot;
  current: boolean;
  /** 島上寫的小字：城鎮名（已開放）、解鎖條件（未解鎖）、「之後的賽季」。 */
  caption: string;
  /** 滑過的說明。 */
  hint: string;
  /** 點了能不能進該區的區域圖（已開放且有區域圖資料）。 */
  canOpen: boolean;
  /** 點城鎮能不能直接傳送（送 `teleport`）。 */
  canTeleport: boolean;
  town: string | null;
}

function caption(r: AtlasRegionView): string {
  if (r.status === "open") return r.town_name_zh ?? "";
  return r.condition_zh ?? "";
}

function hint(r: AtlasRegionView, canOpen: boolean): string {
  if (r.status === "later") return `${r.name_zh}：之後的賽季`;
  if (r.status === "locked") return `${r.name_zh}：還沒解鎖（${r.condition_zh ?? "條件未知"}）`;
  const parts = [`${r.name_zh}：已開放`];
  if (r.current) parts.push("你在這裡");
  if (canOpen) parts.push("點了看區域圖");
  if (r.can_teleport && r.town_name_zh != null) parts.push(`點城鎮傳送到${r.town_name_zh}`);
  return parts.join("・");
}

/** 有區域圖資料的區（所在區＝`view.map`、別區＝`atlas.maps`）。 */
export function atlasMapOf(atlas: AtlasView, current: WorldMapView, region: string): WorldMapView | null {
  if (current.region === region) return current;
  return (atlas.maps ?? []).find((m) => m.region === region) ?? null;
}

function island(r: AtlasRegionView, spot: IslandSpot, canOpen: boolean): AtlasIsland {
  return {
    region: r.region,
    name: r.name_zh,
    status: r.status,
    spot,
    current: r.current ?? false,
    caption: caption(r),
    hint: hint(r, canOpen),
    canOpen,
    canTeleport: r.can_teleport ?? false,
    town: r.town ?? null,
  };
}

/** 五區的浮島（照 `regions` 的順序）。 */
export function atlasIslands(atlas: AtlasView, current: WorldMapView): AtlasIsland[] {
  return atlas.regions.map((r, i) => {
    const canOpen = r.status === "open" && atlasMapOf(atlas, current, r.region) !== null;
    return island(r, SPOTS[r.region] ?? fallbackSpot(i), canOpen);
  });
}

/** 中央的主城浮島（點了不進區域圖；在城鎮或傳送石上時可以傳過去）。 */
export function capitalIsland(atlas: AtlasView): AtlasIsland {
  return island(atlas.capital, CAPITAL_SPOT, false);
}

/** 標題列的說明。 */
export function atlasNote(atlas: AtlasView): string {
  if (atlas.can_teleport) return "可以點已開放區的城鎮直接傳送";
  return `只能看：${atlas.teleport_problem_zh ?? "站在傳送石上或在城鎮裡才能傳送"}`;
}

/** 開地圖時先開哪一層：在主城裡（沒有區域圖）直接開大世界圖。 */
export function firstMapLayer(map: WorldMapView): "region" | "atlas" {
  return map.region === "capital" ? "atlas" : "region";
}

/** 再按一次 M：區域圖 → 大世界圖 → 關閉。 */
export function nextMapLayer(layer: "region" | "atlas" | null, map: WorldMapView): "region" | "atlas" | null {
  if (layer === null) return firstMapLayer(map);
  if (layer === "region") return "atlas";
  return null;
}

// ---------------------------------------------------------------------------
// 主城的情境物件（6D-4 待決：功能型 NPC 與攤位接到既有面板）
// ---------------------------------------------------------------------------

/** 橋頭石碑 `stele_<區域>` 的區域（不是石碑＝`null`）。 */
export function steleRegion(objectId: string): string | null {
  return objectId.startsWith("stele_") ? objectId.slice("stele_".length) : null;
}

/** 主城情境物件 → 既有面板（沒有現成面板的許願池、工坊照舊開說明卡）。 */
const CAPITAL_PANELS: Readonly<Record<string, HudPanel>> = {
  seal_altar: "board", // 封印台：全服封印鑰匙進度（公告板的賽季 Boss 區）
  seal_keeper: "board", // 守印人：封印進度、賽季 Boss 挑戰
  rift_projection: "board", // 裂界投影：賽季 Boss 挑戰入口
  boss_stele: "board", // 排行榜與擊殺石碑：通關評分榜
  shadow_league_desk: "league", // 影子循環賽報名台
  loadout_pavilion: "pavilion", // 整備亭：休息、換技能、配點、換裝
  scribe: "skills", // 書記：魔導書與技能圖鑑（目前＝自己的技能）
  grimoire_shelf: "skills",
};

export function capitalPanel(objectId: string): HudPanel | null {
  return CAPITAL_PANELS[objectId] ?? null;
}
