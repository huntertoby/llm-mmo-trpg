// 設定面板的分區標題（UI-E2；docs/archive/art/偷懶自查.md G12）：小圖示＋標題，分成聲音、減少動態、提示三區。
// 戰鬥「版面」面板與大世界齒輪面板共用（同一個元件）。圖示是純裝飾（`aria-hidden`），名稱寫在標題文字。
// QI-5：圖示換 Q 版 canvas 16px（畫法 `render/qIcon/hud.ts`；提示＝靈感點同一顆燈泡）。舊的 20×20 SVG 已刪。
import { SETTINGS_ICON_ID } from "../render/hudIcon";
import { HudGlyph } from "./HudGlyph";

export type SettingsSectionIcon = keyof typeof SETTINGS_ICON_ID;

export function SettingsHead({ icon, children }: { icon: SettingsSectionIcon; children: string }) {
  return (
    <div className="section-title settings-head" data-settings-head={icon}>
      <HudGlyph id={SETTINGS_ICON_ID[icon]} px={16} className="settings-head-icon" data={{ "data-icon": icon }} />
      <span>{children}</span>
    </div>
  );
}
