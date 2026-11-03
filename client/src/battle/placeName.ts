// 戰鬥畫面右上的地名（Phase 6A-4e）：大世界的戰鬥寫大世界的地點名（實地地圖名，沒有實地就寫地點名），
// 一輪（roguelite）與其他戰鬥照舊寫戰場地圖名。大世界的戰鬥借用 roguelite 的地圖再換皮（`reskin`），
// 地圖名不換，所以荒原的枯木林曾寫成雲嶺的「竹林」（美術 PM 5A-ART6 檢查）；只改顯示，地圖檔與戰鬥設定不動。
import type { BattleView, WorldView } from "../api/types";

/** 大世界畫面帶進戰鬥的地點名：實地地圖名優先，再來是地點名；沒有世界畫面為 `null`。 */
export function worldPlaceName(world: Pick<WorldView, "field" | "here"> | null | undefined): string | null {
  if (world == null) return null;
  const name = world.field?.name_zh ?? world.here.name_zh;
  return name.trim() === "" ? null : name;
}

/** 右上要顯示的地名：有大世界的地點名用它，否則用戰場地圖名。 */
export function battlePlaceName(view: Pick<BattleView, "map_name_zh">, place: string | null | undefined): string {
  if (place != null && place.trim() !== "") return place;
  return view.map_name_zh;
}
