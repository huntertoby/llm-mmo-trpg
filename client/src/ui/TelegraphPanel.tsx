// 環境預告側欄：下一次環境回合（本輪結束時）會發生的變化；滑過格子時顯示那一格的說明。
import type { TelegraphOut } from "../api/types";
import { markStyle, telegraphIsEmpty, telegraphLines, type TelegraphMark } from "../battle/telegraph";

interface Props {
  telegraph: TelegraphOut;
  marks: readonly TelegraphMark[];
  /** 滑過的格子上的預告說明。 */
  hoverTexts: readonly string[];
}

export function TelegraphPanel({ telegraph, marks, hoverTexts }: Props) {
  const lines = telegraphLines(telegraph);
  return (
    <div className="panel telegraph-panel" aria-label="環境預告">
      <div className="section-title">環境預告（第 {telegraph.round} 輪結束時）</div>
      {hoverTexts.length > 0 && (
        <ul className="telegraph-hover">
          {hoverTexts.map((t, i) => (
            <li key={`${i}:${t}`}>{t}</li>
          ))}
        </ul>
      )}
      {telegraphIsEmpty(telegraph) ? (
        <div className="small muted">下一次環境回合沒有明顯變化。</div>
      ) : (
        <ul className="telegraph-list">
          {lines.map((t, i) => (
            <li key={`${i}:${t}`}>{t}</li>
          ))}
        </ul>
      )}
      {marks.length > 0 && (
        <div className="small muted">
          格子上的標記：
          {[...new Set(marks.map((m) => m.kind))].map((k) => `${markStyle(k).glyph}`).join(" ")}
          （滑過格子看說明）
        </div>
      )}
    </div>
  );
}
