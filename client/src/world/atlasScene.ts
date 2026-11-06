// 大世界圖插畫（6F-ART1）要畫的場景：由 `atlasModel` 的浮島（狀態、條件、能不能傳送）加上插畫的浮島位置組成。
// 全部用現有欄位（`atlas.regions`、`capital`、`can_teleport`、`maps` 的 `level_zh`），不新增伺服器欄位。
// 6F-3：「你在〇〇」寫所在區區域圖上 `current` 的地點（原本固定寫該區的城鎮，荒原站在灰渡口也寫餘燼集）。
import type { AtlasView, WorldMapView } from "../api/types";
import { islandGeo, type AtlasArtIsland, type AtlasScene } from "../render/worldMapArt";
import { atlasIslands, atlasMapOf, capitalIsland, type AtlasIsland } from "./atlasModel";

const LATER_ZH = "之後的賽季";

/** 自己所在的地點名（所在區的區域圖上 `current` 的那一點；不是所在區或找不到＝`undefined`）。 */
export function hereName(map: WorldMapView, i: Pick<AtlasIsland, "region" | "current">): string | undefined {
  if (!i.current || map.region !== i.region) return undefined;
  return map.locations.find((l) => l.current === true)?.name_zh;
}

function artIsland(atlas: AtlasView, map: WorldMapView, i: AtlasIsland): AtlasArtIsland {
  const open = i.status === "open";
  return {
    region: i.region,
    name: i.name,
    status: i.status,
    current: i.current,
    canTeleport: i.canTeleport,
    ...(i.free ? { free: true } : {}),
    town: open ? i.caption : "",
    here: hereName(map, i),
    level: open ? (atlasMapOf(atlas, map, i.region)?.level_zh ?? "") : "",
    condition: open ? "" : i.caption !== "" ? i.caption : LATER_ZH,
    geo: islandGeo(i.region, i.index),
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
    capital: artIsland(atlas, map, capital),
  };
  return { scene, islands, capital };
}
