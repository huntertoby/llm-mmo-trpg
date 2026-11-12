// 戰鬥版 HUD 右上工具鈕的圖示（Phase 6A-4e；QI-5 換 Q 版）：反應設定、隊友指令、圖例、版面、存檔、離開、環境預告。名稱與說明在呼叫端的 `Hint`。
// QI-5（docs/art/Q版小圖示-HUD移植需求.md）：Q 版 canvas（畫法 `render/qIcon/hud.ts`，經 `render/hudIcon.ts` 快取），畫布寬高＝顯示 × 2、CSS 不縮放。
// 反應設定改成第④批卡片「反應」的綠色回轉箭頭（原本的盾＋閃電和第⑤批「帶電護盾」撞圖）；版面＝設定的齒輪；離開＝風格樣張；環境預告＝第④批延遲沙漏。舊的 24×24 SVG 已刪。
import { TOOL_ICON_ID } from "../render/hudIcon";
import { HudGlyph } from "./HudGlyph";

export type BattleToolIconName = keyof typeof TOOL_ICON_ID;

export function BattleToolIcon({ name, size = 20 }: { name: BattleToolIconName; size?: number }) {
  return <HudGlyph id={TOOL_ICON_ID[name]} px={size} className="bhud-icon" data={{ "data-icon": name }} />;
}
