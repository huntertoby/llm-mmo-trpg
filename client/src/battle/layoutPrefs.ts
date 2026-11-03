// 戰鬥畫面的版面設定（Phase 3-10；純函式＋ localStorage 包裝）：地圖縮放。
// 6A-4g：版面 A 沒有窄欄與分隔線，舊的欄寬、列高、主角卡寬設定刪掉；以前存下的這幾個欄位讀取時忽略。

export interface LayoutPrefs {
  /** 地圖縮放；`null` ＝ 自動填滿可用空間。 */
  zoom: number | null;
}

export const DEFAULT_LAYOUT: LayoutPrefs = { zoom: null };

/** 手動縮放的範圍與每次按 ＋／－ 的倍率。 */
export const ZOOM_MIN = 0.4;
export const ZOOM_MAX = 3;
export const ZOOM_STEP = 1.25;

/** 縮放夾在範圍內，取到小數第二位（百分比為整數）。 */
export function clampZoom(zoom: number): number {
  return Math.round(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom)) * 100) / 100;
}

/** 把設定夾進範圍。 */
export function clampLayout(prefs: LayoutPrefs): LayoutPrefs {
  return { zoom: prefs.zoom === null ? null : clampZoom(prefs.zoom) };
}

/** 在目前的實際縮放上乘以倍率（＋ 用 `ZOOM_STEP`，－ 用其倒數）。 */
export function zoomBy(current: number, factor: number): number {
  return clampZoom(current * factor);
}

/** 縮放的顯示文字，例如「125%」。 */
export function zoomPercent(scale: number): string {
  return `${Math.round(scale * 100)}%`;
}

const LAYOUT_KEY = "trpg.battleLayout";

/** 讀取記下的版面設定；讀不到或格式不對時用預設（舊版存的欄寬、列高忽略）。 */
export function loadLayout(): LayoutPrefs {
  try {
    const raw = window.localStorage.getItem(LAYOUT_KEY);
    if (raw === null) return DEFAULT_LAYOUT;
    const v = JSON.parse(raw) as Record<string, unknown> | null;
    if (v === null || typeof v !== "object") return DEFAULT_LAYOUT;
    return { zoom: typeof v.zoom === "number" && Number.isFinite(v.zoom) ? clampZoom(v.zoom) : null };
  } catch {
    return DEFAULT_LAYOUT;
  }
}

export function saveLayout(prefs: LayoutPrefs): void {
  try {
    window.localStorage.setItem(LAYOUT_KEY, JSON.stringify(prefs));
  } catch {
    // 無法存取 localStorage（私密視窗等）時只在本次有效。
  }
}
