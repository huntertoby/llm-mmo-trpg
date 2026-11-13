// 大世界圖（Phase 6D-5；21.1、9.6.5「碎界」）與主城情境物件的純函式。
// 規則一律由後端算好（`AtlasView`：三種狀態、解鎖條件、能不能傳送），這裡只決定浮島的位置、外觀與說明文字。
// 浮島的位置與大小只有一份：`render/worldMapArt.ts` 的 `ISLAND_GEO`（6D-R2 把原本這裡的 SPOTS 併過去）。
import type { AtlasRegionView, AtlasView, WorldMapView } from "../api/types";
import type { FieldSituationObject } from "./fieldModel";
import type { HudPanel } from "./hud";

export interface AtlasIsland {
  region: string;
  name: string;
  status: AtlasRegionView["status"];
  /** `regions` 裡的順序（主城＝-1）：表裡沒有的區照這個沿外圈排。 */
  index: number;
  current: boolean;
  /** 島上寫的小字：城鎮名（已開放）、解鎖條件（未解鎖）、「之後的賽季」。 */
  caption: string;
  /** 滑過的說明。 */
  hint: string;
  /** 點了能不能進該區的區域圖（已開放且有區域圖資料）。 */
  canOpen: boolean;
  /** 點城鎮能不能直接傳送（送 `teleport`）。 */
  canTeleport: boolean;
  /** 第一次免費傳送（RT-5：伺服器的 `free`，還沒到過新手區的小鎮）。 */
  free: boolean;
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
  if (r.can_teleport && r.town_name_zh != null) parts.push(`點城鎮傳送到${r.town_name_zh}${r.free === true ? "（第一次免費）" : ""}`);
  return parts.join("・");
}

/** 有區域圖資料的區（所在區＝`view.map`、別區＝`atlas.maps`）。 */
export function atlasMapOf(atlas: AtlasView, current: WorldMapView, region: string): WorldMapView | null {
  if (current.region === region) return current;
  return (atlas.maps ?? []).find((m) => m.region === region) ?? null;
}

function island(r: AtlasRegionView, index: number, canOpen: boolean): AtlasIsland {
  return {
    region: r.region,
    name: r.name_zh,
    status: r.status,
    index,
    current: r.current ?? false,
    caption: caption(r),
    hint: hint(r, canOpen),
    canOpen,
    canTeleport: r.can_teleport ?? false,
    free: r.free ?? false,
    town: r.town ?? null,
  };
}

/** 五區的浮島（照 `regions` 的順序）。 */
export function atlasIslands(atlas: AtlasView, current: WorldMapView): AtlasIsland[] {
  return atlas.regions.map((r, i) => {
    const canOpen = r.status === "open" && atlasMapOf(atlas, current, r.region) !== null;
    return island(r, i, canOpen);
  });
}

/** 中央的主城浮島（點了不進區域圖；在城鎮或傳送石上時可以傳過去）。 */
export function capitalIsland(atlas: AtlasView): AtlasIsland {
  return island(atlas.capital, -1, false);
}

/** 標題列的說明。 */
export function atlasNote(atlas: AtlasView): string {
  if (atlas.can_teleport) return "可以點已開放區的城鎮直接傳送";
  return `只能看：${atlas.teleport_problem_zh ?? "站在傳送石上或在城鎮裡才能傳送"}`;
}

/** 開地圖時先開哪一層：在主城這類樞紐裡（伺服器給的 `hub`，沒有區域圖）直接開大世界圖。 */
export function firstMapLayer(map: WorldMapView): "region" | "atlas" {
  return map.hub === true ? "atlas" : "region";
}

/** 再按一次 M：區域圖 → 大世界圖 → 關閉。 */
export function nextMapLayer(layer: "region" | "atlas" | null, map: WorldMapView): "region" | "atlas" | null {
  if (layer === null) return firstMapLayer(map);
  if (layer === "region") return "atlas";
  return null;
}

// ---------------------------------------------------------------------------
// 主城的情境物件（6D-4 待決：功能型 NPC 與攤位接到既有面板；6D-R2 改讀內容的 `panel`／`stele_region`）
// ---------------------------------------------------------------------------

/** 情境物件點了直接開的面板：橋頭石碑（`stele_region`）開該區的傳送選單、功能型物件（`panel`）開既有
 * 面板；兩個都沒有（一般物件）與許願池（`wish`，WP-3 前）＝`null`，照舊開說明卡。 */
export function objectHud(
  obj: Pick<FieldSituationObject, "panel" | "stele_region"> | null,
): { panel: HudPanel; who: string | null } | null {
  if (obj === null) return null;
  if (obj.stele_region != null) return { panel: "stele", who: obj.stele_region };
  // PR-2b：`workshop`（工坊師傅選單）也是面板（`WorldScreen` 另記師傅的物件 ID，給「重選」入口用）
  // WP-2：`wish`（許願池面板）在 WP-3 接上前先略過，照舊開說明卡
  if (obj.panel != null && obj.panel !== "wish") return { panel: obj.panel, who: null };
  return null;
}
