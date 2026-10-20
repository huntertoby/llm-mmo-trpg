// 頂端列（Phase 3-8）：輪數、地圖與天氣、行動順序（`TurnBar`）；右側「反應設定」「隊友指令」「圖例」
// 三個按鈕，點了在按鈕下方彈出面板（再點或按 Esc 關閉，同時只開一個）；一輪模式的「存檔」與返回鈕也在這裡。
import type { ReactNode } from "react";
import type { TopPopup } from "../battle/skillTray";

interface Tool {
  id: TopPopup;
  label: string;
  /** 按鈕上的小提示（例如有指令時標「●」）。 */
  badge?: string;
  content: ReactNode;
}

interface Props {
  turnBar: ReactNode;
  tools: readonly Tool[];
  open: TopPopup | null;
  onToggle(id: TopPopup): void;
  /** 返回鈕（工坊試玩、一輪）；`null` 不顯示。 */
  exit: { label: string; onExit(): void } | null;
  /** 一輪模式的存檔；`null` 不顯示。 */
  save: { busy: boolean; note: string | null; onSave(): void } | null;
}

export function BattleTopBar({ turnBar, tools, open, onToggle, exit, save }: Props) {
  return (
    <header className="battle-top">
      {turnBar}
      <div className="battle-top-tools">
        {save !== null && (
          <>
            {save.note !== null && <span className="muted small save-note">{save.note}</span>}
            <button type="button" disabled={save.busy} onClick={save.onSave}>
              存檔
            </button>
          </>
        )}
        {tools.map((t) => (
          <span key={t.id} className="top-tool">
            <button
              type="button"
              className={open === t.id ? "selected" : ""}
              aria-expanded={open === t.id}
              aria-haspopup="dialog"
              onClick={() => onToggle(t.id)}
            >
              {t.label}
              {t.badge !== undefined && t.badge !== "" && <span className="top-tool-badge">{t.badge}</span>}
            </button>
            {open === t.id && (
              <div className="top-popup" role="dialog" aria-label={t.label}>
                {t.content}
              </div>
            )}
          </span>
        ))}
        {exit !== null && (
          <button type="button" className="battle-leave" onClick={exit.onExit}>
            ← {exit.label}
          </button>
        )}
      </div>
    </header>
  );
}
