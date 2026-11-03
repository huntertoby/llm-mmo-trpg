// 就地開打（Phase 6C-2；docs/design/21-探索地圖與城鎮.md 21.4、05 5.10）：伺服器從實地地圖切出 12×12 戰場，遭遇的
// `battlefield` 是它在實地地圖上的範圍。遭遇出現時鏡頭用 6B-6 的 `frameCamera` 框住這塊（四周各半格）；遭遇結束（打完、撤退）
// `battlefield` 不見了，鏡頭回到跟隨主角。退回模板時（`battlefield_fallback_zh`）不框，照舊跟隨。
import type { WorldEncounterView, WorldView } from "../api/types";
import type { TileRect } from "./camera";

/** 鏡頭要框住的戰場範圍：有遭遇、切出來的戰場就在目前這張實地地圖上時才框；否則 `null`（跟隨主角）。 */
export function battleFrame(view: WorldView): TileRect | null {
  const rect = view.encounter?.battlefield ?? null;
  const field = view.field ?? null;
  if (rect === null || field === null || rect.field_map !== field.map_id) return null;
  return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
}

/** 遭遇卡上的一行戰場說明；不是地圖上碰到的遭遇＝`null`。 */
export function battlefieldLine(e: WorldEncounterView): string | null {
  if (e.battlefield != null) return `就地開打（${e.battlefield.width}×${e.battlefield.height}，地形照剛剛看到的）`;
  if (e.battlefield_fallback_zh != null) return `改用這裡原本的戰場：${e.battlefield_fallback_zh}`;
  return null;
}
