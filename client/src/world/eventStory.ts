// 地點事件的旁白後補（WM-1 第 4 項）：走路觸發事件、LLM 開著時，伺服器先回畫面（`event.story_pending`），
// 前端畫占位、另外送 `POST …/event_story` 補上旁白。純函式：要不要送、回來之後怎麼併進目前的畫面。
// 只換 `event` 這一塊：補旁白的請求和走路的請求可能交錯，整份畫面以走路的回應為準（位置、地圖都不被舊的蓋掉）；
// 旁白寫進日誌時順帶記下的人名、地名、線頭，下一個動作的整份畫面就會帶到。
import type { WorldEventView, WorldView } from "../api/types";

/** 占位的文字。 */
export const STORY_PENDING_ZH = "說書人正在構思這段故事……";

/** 這份畫面的事件還在等旁白時的鍵（同一個事件只送一次）；不用等為 `null`。 */
export function pendingStoryKey(characterId: string | null, view: WorldView | null): string | null {
  const event = view?.event ?? null;
  if (characterId === null || event === null || event.story != null || event.story_pending !== true) return null;
  return `${characterId}|${event.skeleton}|${event.location_name_zh}`;
}

function sameEvent(a: WorldEventView, b: WorldEventView): boolean {
  return a.skeleton === b.skeleton && a.location_name_zh === b.location_name_zh;
}

/** 補上的旁白併進目前的畫面：還是同一個事件、而且還沒有旁白才換 `event`；其他照目前的畫面。 */
export function withStory(current: WorldView, filled: WorldView): WorldView {
  const now = current.event ?? null;
  const got = filled.event ?? null;
  if (now === null || got === null || got.story == null || now.story != null || !sameEvent(now, got)) return current;
  return { ...current, event: got };
}
