// 地形資訊卡的玩家設定（Phase 3-18b；localStorage）：格子上有單位時，地形卡可以收起成一行
// （在「版面」面板勾選）；記住使用者的選擇。

const KEY = "trpg.tileCardCollapsed";

/** 格子上有單位時是否把地形卡收起（預設不收；只有明確存過 "on" 才收）。 */
export function loadTileCollapse(): boolean {
  try {
    return window.localStorage.getItem(KEY) === "on";
  } catch {
    return false;
  }
}

export function saveTileCollapse(on: boolean): void {
  try {
    window.localStorage.setItem(KEY, on ? "on" : "off");
  } catch {
    // 無法存取 localStorage（私密視窗等）時只在本次有效。
  }
}
