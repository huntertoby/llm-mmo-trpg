// HUD 的 Q 版小圖示（Phase QI-5，第⑦批；畫法在 `qIcon/hud.ts`）：畫布快取、圖示名稱對照、圖釘。
// 遊戲端的 React 元件（`HudBarIcon`、`HudIcon`、`BattleToolIcon`、`SettingsHead`、`RegionCrest`、`StatGlyph`、狀態卡的源力圓點、浮動卡的 `PinIcon`）
// 都經這裡拿畫布：畫布邊長＝顯示 × `ICON_RES`，CSS 不縮放（`docs/dev/上手-前端戰鬥畫面與動畫.md` 第四節第 19 點）。
import { ICON_RES } from "./qIcon/core";
import * as QH from "./qIcon/hud";
import { cardGlyphCanvas } from "./skillIcon";

export type HudIconOpt = QH.HudPaintOpt;

/** 快取鍵：圖示 id、顯示邊長、內部解析度、有沒有框、區域色。 */
export const hudIconKey = (id: string, px: number, res: number = ICON_RES, opt: HudIconOpt = {}): string => [id, px, res, opt.frame ?? "", opt.accent ?? ""].join("|");

const CACHE_LIMIT = 256;
const cache = new Map<string, HTMLCanvasElement>();
/** 一個 HUD 圖示的畫布（`qIcon/hud.ts` 的 `canvas`），同鍵共用一張。 */
export function hudIconCanvas(id: string, px: number, res: number = ICON_RES, opt: HudIconOpt = {}): HTMLCanvasElement {
  const key = hudIconKey(id, px, res, opt);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const cv = QH.canvas(id, px, res, opt);
  if (cache.size >= CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(key, cv);
  return cv;
}
export function clearHudIconCache(): void {
  cache.clear();
}

/** 功能列 8 顆（`HudBarIcon` 的 k）→ 圖示 id。 */
export const BAR_ICON_ID = { I: "bar_I", K: "bar_K", G: "bar_G", J: "bar_J", Y: "bar_Y", N: "bar_N", R: "bar_R", M: "bar_M" } as const;

/** 通用小圖（`HudIcon` 的 name；QI-5 起只留用到的 18 個）→ 圖示 id 與框。任務卷軸、留言和功能列同一份畫法、沒有淺色圓底（需求 3 第 2 點）。 */
export const HUD_ICON_ID = {
  rank: "rank",
  gear: "gear",
  town: "town",
  warn: "warn",
  scroll: "bar_J",
  notes: "bar_N",
  sun: "sun",
  moon: "moon",
  clear: "clear",
  rain: "rain",
  fog: "fog",
  snow: "snow",
  wind: "wind",
  night: "night",
  coin: "coin",
  token: "token",
  ration: "ration",
  bulb: "bulb",
} as const;
export type HudIconName = keyof typeof HUD_ICON_ID;
/** 通用小圖的畫布選項：和功能列同一份畫法的（任務、留言）不畫圓底。 */
export const hudIconOpt = (name: HudIconName): HudIconOpt => (QH.ICON[HUD_ICON_ID[name]]?.grp === "bar" ? { frame: "none" } : {});

/** 戰鬥工具鈕 7 個 → 圖示 id。 */
export const TOOL_ICON_ID = { reactions: "t_reactions", orders: "t_orders", legend: "t_legend", layout: "t_layout", save: "t_save", exit: "t_exit", telegraph: "t_telegraph" } as const;
/** 設定標題 3 個 → 圖示 id。 */
export const SETTINGS_ICON_ID = { sound: "s_sound", motion: "s_motion", hint: "s_hint" } as const;
/** 資源小圖裡還是舊 SVG 的 4 個（`STAT_PATHS`）→ 圖示 id；AP、法力、源力、反應照舊走 `ChipGlyph`（同一張第 4 批卡片小圖）。 */
export const STAT_ICON_ID = { move: "r_move", shield: "r_shield", weapon: "r_weapon", ammo: "r_ammo" } as const;
/** 源力圓點：亮＝晶石、暗＝同形紫框深底（9px）。 */
export const SOURCE_PIP_PX = 9;
export const sourcePipId = (on: boolean): string => (on ? "pip_on" : "pip_off");

/** 浮動卡的圖釘（`HoverFloat` 的 `PinIcon`，13px）：開發 PM 選 A＝第 4 批紅頭（已釘）／灰鋼 55%（未釘），和 `PinGlyph` 同一張畫布。 */
export const FLOAT_PIN_PX = 13;
export const floatPinCanvas = (pinned: boolean, px: number = FLOAT_PIN_PX, res: number = ICON_RES): HTMLCanvasElement => cardGlyphCanvas("pin", px, res, { pinned });

/** 釘住的說明卡右上角（`.float-card.pinned::after`）：金圓底與深藍外圈照現行 CSS，圓底裡 12px 換紅頭圖釘（樣張 `pinBadge("a")` 的裡面那一張）。 */
export const PIN_BADGE_GLYPH_PX = 12;
export const PIN_BADGE_VAR = "--float-pin-glyph";
/** 把圓底裡的圖釘做成 PNG data URL 掛到 `<html>` 的 CSS 變數（`::after` 的 `background` 讀它）。沒有畫布時不做事。 */
export function installPinBadge(doc: Document): void {
  try {
    const cv = floatPinCanvas(true, PIN_BADGE_GLYPH_PX);
    doc.documentElement.style.setProperty(PIN_BADGE_VAR, `url("${cv.toDataURL("image/png")}")`);
  } catch {
    // 沒有畫布（測試環境）：維持 CSS 的預設（只有金圓底）
  }
}
