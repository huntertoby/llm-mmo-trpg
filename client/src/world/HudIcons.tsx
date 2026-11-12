// HUD 的通用小圖示（Phase 6B-5；QI-5 換 Q 版）：畫法 `render/qIcon/hud.ts`（第⑦批），經 `render/hudIcon.ts` 快取，畫布寬高＝顯示 × 2、CSS 不縮放。
// QI-5（docs/art/Q版小圖示-HUD移植需求.md 第 4 節第 2 點，開發 PM 定）：沒有地方用到的 7 個名字（bag、book、growth、shadow、map、boots、pin）刪掉，不畫新圖；
// 任務卷軸 `scroll`、留言 `notes` 和功能列 J、N 同一份畫法（不畫淺色圓底）。時間「月亮」`moon` 與天氣「夜晚」`night` 分成兩個圖。舊的 24×24 SVG 已刪。
import { HUD_ICON_ID, hudIconOpt, type HudIconName } from "../render/hudIcon";
import { HudGlyph } from "../ui/HudGlyph";

export type { HudIconName };

export function HudIcon({ name, size = 22 }: { name: HudIconName; size?: number }) {
  return <HudGlyph id={HUD_ICON_ID[name]} px={size} className="hud-icon" opt={hudIconOpt(name)} data={{ "data-icon": name }} />;
}

/** 圓頭像（程式繪製的小人臉；主角金框、隊友藍框）。 */
export function HudPortrait({ size, ring, tone = 0 }: { size: number; ring: string; tone?: number }) {
  const skin = ["#f0c8a0", "#d8a878", "#c89060"][tone % 3];
  const hair = ["#2a2018", "#5a3a20", "#1a1a2a"][tone % 3];
  return (
    <svg className="hud-portrait" viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
      {/* UI-E1 追加 5：框色寫在 style（換區時 CSS `.hud-portrait-ring` 淡入 0.3 秒），畫法不變 */}
      <circle className="hud-portrait-ring" cx="32" cy="32" r="30" fill="#3a5a6a" stroke={ring} strokeWidth="3" style={{ stroke: ring }} />
      <path d="M14 58c2-12 9-16 18-16s16 4 18 16z" fill="#4a6a8a" />
      <circle cx="32" cy="30" r="12" fill={skin} />
      <path d="M19 28c0-10 6-15 13-15s13 5 13 15c-3-5-8-7-13-7s-10 2-13 7z" fill={hair} />
      <circle cx="27.5" cy="31" r="1.6" fill="#2a2018" />
      <circle cx="36.5" cy="31" r="1.6" fill="#2a2018" />
    </svg>
  );
}
