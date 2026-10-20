// 戰鬥畫面的版面設定（Phase 3-10；純函式＋ localStorage 包裝）：右側窄欄寬、底部列高、主角狀態卡寬、地圖縮放。
// 拖曳分隔線與設定面板的滑桿共用同一組數值與上下限（地圖不會小於可用區域的一半）。
import type { Size } from "./stageLayout";

export interface LayoutPrefs {
  /** 右側窄欄寬度（CSS 像素）。 */
  sideWidth: number;
  /** 底部列高度。 */
  bottomHeight: number;
  /** 底部左側主角狀態卡寬度。 */
  heroWidth: number;
  /** 地圖縮放；`null` ＝ 自動填滿可用空間。 */
  zoom: number | null;
}

export const DEFAULT_LAYOUT: LayoutPrefs = { sideWidth: 300, bottomHeight: 166, heroWidth: 300, zoom: null };

export type Range = readonly [min: number, max: number];

export const SIDE_MIN = 200;
export const BOTTOM_MIN = 120;
export const HERO_RANGE: Range = [200, 520];
/** 頂端列、間距等佔用的高度與寬度（估計值；只用來算上限）。 */
const TOP_RESERVED = 56;
const SIDE_RESERVED = 22;

/** 手動縮放的範圍與每次按 ＋／－ 的倍率。 */
export const ZOOM_MIN = 0.4;
export const ZOOM_MAX = 3;
export const ZOOM_STEP = 1.25;

export interface LayoutLimits {
  side: Range;
  bottom: Range;
  hero: Range;
}

/** 依視窗大小算出各項的上下限：窄欄與底部列都不能讓地圖小於視窗（可用區域）的一半。 */
export function layoutLimits(viewport: Size): LayoutLimits {
  const sideMax = Math.max(SIDE_MIN, Math.floor(viewport.width / 2) - SIDE_RESERVED);
  const bottomMax = Math.max(BOTTOM_MIN, Math.floor(viewport.height / 2) - TOP_RESERVED);
  return { side: [SIDE_MIN, sideMax], bottom: [BOTTOM_MIN, bottomMax], hero: HERO_RANGE };
}

export function clampTo(value: number, [min, max]: Range): number {
  return Math.round(Math.max(min, Math.min(max, value)));
}

/** 縮放夾在範圍內，取到小數第二位（百分比為整數）。 */
export function clampZoom(zoom: number): number {
  return Math.round(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom)) * 100) / 100;
}

/** 把整組設定夾進目前視窗的上下限（視窗縮小時自動收回）。 */
export function clampLayout(prefs: LayoutPrefs, viewport: Size): LayoutPrefs {
  const limits = layoutLimits(viewport);
  return {
    sideWidth: clampTo(prefs.sideWidth, limits.side),
    bottomHeight: clampTo(prefs.bottomHeight, limits.bottom),
    heroWidth: clampTo(prefs.heroWidth, limits.hero),
    zoom: prefs.zoom === null ? null : clampZoom(prefs.zoom),
  };
}

/**
 * 拖曳分隔線：新值 ＝ 起始值 ＋ 方向 × 滑鼠位移，夾進範圍。
 * `direction`：往右（或往下）拖會讓值變大為 1，變小為 -1（右側窄欄的左緣往左拖才變寬，所以是 -1）。
 */
export function dragValue(start: number, delta: number, direction: 1 | -1, range: Range): number {
  return clampTo(start + direction * delta, range);
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

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

/** 讀取記下的版面設定；讀不到或格式不對時用預設（逐欄位檢查）。 */
export function loadLayout(): LayoutPrefs {
  try {
    const raw = window.localStorage.getItem(LAYOUT_KEY);
    if (raw === null) return DEFAULT_LAYOUT;
    const v = JSON.parse(raw) as Record<string, unknown> | null;
    if (v === null || typeof v !== "object") return DEFAULT_LAYOUT;
    return {
      sideWidth: numberOr(v.sideWidth, DEFAULT_LAYOUT.sideWidth),
      bottomHeight: numberOr(v.bottomHeight, DEFAULT_LAYOUT.bottomHeight),
      heroWidth: numberOr(v.heroWidth, DEFAULT_LAYOUT.heroWidth),
      zoom: typeof v.zoom === "number" && Number.isFinite(v.zoom) ? clampZoom(v.zoom) : null,
    };
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
