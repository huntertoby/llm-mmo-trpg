// 技能特效的玩家設定（Phase 3-12；localStorage）：畫面震動可以在「版面」面板關閉。

const SHAKE_KEY = "trpg.vfxShake";

/** 畫面震動是否開啟（預設開；只有明確存過 "off" 才關）。 */
export function loadShake(): boolean {
  try {
    return window.localStorage.getItem(SHAKE_KEY) !== "off";
  } catch {
    return true;
  }
}

export function saveShake(on: boolean): void {
  try {
    window.localStorage.setItem(SHAKE_KEY, on ? "on" : "off");
  } catch {
    // 無法存取 localStorage（私密視窗等）時只在本次有效。
  }
}
