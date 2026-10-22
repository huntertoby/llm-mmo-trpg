// 頂端列（Phase 3-8）：輪數、地圖與天氣、行動順序（`TurnBar`）；右側「反應設定」「隊友指令」「圖例」
// 三個按鈕，點了在按鈕下方彈出面板（再點或按 Esc 關閉，同時只開一個）；一輪模式的「存檔」與返回鈕也在這裡。
import type { ReactNode } from "react";
import type { TopPopup } from "../battle/skillTray";
import { usePopupMenu } from "./usePopupMenu";

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

/** 一個頂端按鈕＋它的面板；Esc、點外面關閉與「同時只開一張」由 `usePopupMenu` 負責。 */
function TopTool({ tool: t, isOpen, onToggle }: { tool: Tool; isOpen: boolean; onToggle(): void }) {
  const menu = usePopupMenu({ open: isOpen, setOpen: (v) => v !== isOpen && onToggle() });
  return (
    <div className="top-tool" ref={menu.rootRef}>
      <button type="button" className={isOpen ? "selected" : ""} aria-expanded={isOpen} aria-haspopup="dialog" onClick={onToggle}>
        {t.label}
        {t.badge !== undefined && t.badge !== "" && <span className="top-tool-badge">{t.badge}</span>}
      </button>
      {isOpen && (
        <div className="top-popup popup-menu" role="dialog" aria-label={t.label}>
          {t.content}
        </div>
      )}
    </div>
  );
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
          <TopTool key={t.id} tool={t} isOpen={open === t.id} onToggle={() => onToggle(t.id)} />
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
