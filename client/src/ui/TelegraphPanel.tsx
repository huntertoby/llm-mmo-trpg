// 環境預告側欄：下一次環境回合（本輪結束時）會發生的變化；滑過格子時顯示那一格的說明。
import type { BattleView, Pos, TelegraphOut } from "../api/types";
import { markStyle, telegraphEntries, telegraphIsEmpty, type TelegraphMark } from "../battle/telegraph";

interface Props {
  telegraph: TelegraphOut;
  marks: readonly TelegraphMark[];
  /** 滑過的格子上的預告說明。 */
  hoverTexts: readonly string[];
  /** 用來找出預告項目涉及的格子（單位位置）。 */
  view: BattleView;
  /** 滑過（或聚焦）一個項目時回報它涉及的格子，移開時傳 `null`；呼叫端在地圖上標出來。 */
  onHoverTiles(tiles: readonly Pos[] | null): void;
}

export function TelegraphPanel({ telegraph, marks, hoverTexts, view, onHoverTiles }: Props) {
  const entries = telegraphEntries(telegraph, view);
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
          {entries.map((e, i) => (
            <li
              key={`${i}:${e.text}`}
              tabIndex={e.tiles.length > 0 ? 0 : undefined}
              className={e.tiles.length > 0 ? "telegraph-item" : undefined}
              onMouseEnter={() => e.tiles.length > 0 && onHoverTiles(e.tiles)}
              onMouseLeave={() => onHoverTiles(null)}
              onFocus={() => e.tiles.length > 0 && onHoverTiles(e.tiles)}
              onBlur={() => onHoverTiles(null)}
            >
              {e.text}
            </li>
          ))}
        </ul>
      )}
      {marks.length > 0 && (
        <div className="small muted">
          格子上的標記：
          {[...new Set(marks.map((m) => m.kind))].map((k) => `${markStyle(k).glyph}`).join(" ")}
          （滑過格子看說明；滑過上面的項目會在地圖上標出格子）
        </div>
      )}
    </div>
  );
}
