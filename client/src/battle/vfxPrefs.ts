// 技能特效的玩家設定（Phase 3-12；localStorage）：畫面震動可以在「版面」面板關閉。
import { prefersReducedMotion } from "../world/frameLoop";

const SHAKE_KEY = "trpg.vfxShake";

/**
 * 畫面震動是否開啟：存過 "on"／"off" 照存的；沒存過時預設 `!prefersReducedMotion()`（6R-F：系統開了減少動態就預設關）。
 * 減少動態時繪製器本身也不震（`reducedMotion.ts`），這裡只管開關的預設值。
 */
export function loadShake(): boolean {
  try {
    const saved = window.localStorage.getItem(SHAKE_KEY);
    if (saved === "off") return false;
    if (saved === "on") return true;
  } catch {
    // 無法存取 localStorage 時照系統設定
  }
  return !prefersReducedMotion();
}

export function saveShake(on: boolean): void {
  try {
    window.localStorage.setItem(SHAKE_KEY, on ? "on" : "off");
  } catch {
    // 無法存取 localStorage（私密視窗等）時只在本次有效。
  }
}
