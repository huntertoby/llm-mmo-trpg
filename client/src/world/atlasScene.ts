// 大世界圖插畫（6F-ART1）要畫的場景：由 `atlasModel` 的浮島（狀態、條件、能不能傳送）加上插畫的浮島位置組成。
// 全部用現有欄位（`atlas.regions`、`capital`、`can_teleport`、`maps` 的 `level_zh`），不新增伺服器欄位。
import type { AtlasView, WorldMapView } from "../api/types";
import { islandGeo, type AtlasArtIsland, type AtlasScene } from "../render/worldMapArt";
import { atlasIslands, atlasMapOf, capitalIsland, type AtlasIsland } from "./atlasModel";

const LATER_ZH = "之後的賽季";

function artIsland(atlas: AtlasView, map: WorldMapView, i: AtlasIsland): AtlasArtIsland {
  const open = i.status === "open";
  return {
    region: i.region,
    name: i.name,
    status: i.status,
    current: i.current,
    canTeleport: i.canTeleport,
    town: open ? i.caption : "",
    level: open ? (atlasMapOf(atlas, map, i.region)?.level_zh ?? "") : "",
    condition: open ? "" : i.caption !== "" ? i.caption : LATER_ZH,
    geo: islandGeo(i.region, i.spot),
  };
}

export interface AtlasArtModel {
  scene: AtlasScene;
  /** 與 `scene.islands` 同順序的浮島資料（點擊區、說明卡用）。 */
  islands: AtlasIsland[];
  capital: AtlasIsland;
}

export function atlasScene(atlas: AtlasView, map: WorldMapView): AtlasArtModel {
  const islands = atlasIslands(atlas, map);
  const capital = capitalIsland(atlas);
  const scene: AtlasScene = {
    islands: islands.map((i) => artIsland(atlas, map, i)),
    capital: { ...artIsland(atlas, map, capital), geo: islandGeo("capital", capital.spot) },
  };
  return { scene, islands, capital };
}
