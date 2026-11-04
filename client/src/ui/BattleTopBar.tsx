// 戰鬥版 HUD 右上的工具鈕（Phase 3-8 頂端列；6A-4e 改成版面 A 的圖示鈕）：「反應設定」「隊友指令」「圖例」「版面」
// 點了在按鈕下方彈出面板（再點或按 Esc 關閉，同時只開一個）；環境預告的開關、一輪模式的「存檔」與返回鈕也在這裡。
// 鈕上只有圖示，名稱與說明滑過看（`Hint`）；回合、天氣、勝利條件在 `BattleStatusBox`，行動順序在 `TurnBar`。
import type { ReactNode } from "react";
import type { TopPopup } from "../battle/skillTray";
import { BattleToolIcon, type BattleToolIconName } from "./BattleToolIcons";
import { Hint } from "./Hint";
import { usePopupMenu } from "./usePopupMenu";

interface Tool {
  id: TopPopup;
  label: string;
  /** 按鈕上的小提示（例如有指令時標「●」）。 */
  badge?: string;
  content: ReactNode;
}

interface Props {
  tools: readonly Tool[];
  open: TopPopup | null;
  onToggle(id: TopPopup): void;
  /** 返回鈕（工坊試玩、一輪、大世界）；`null` 不顯示。 */
  exit: { label: string; onExit(): void } | null;
  /** 一輪模式的存檔；`null` 不顯示（存檔結果的訊息由呼叫端顯示在提示列）。 */
  save: { busy: boolean; onSave(): void } | null;
  /** 環境預告面板的開關。 */
  telegraph: { open: boolean; onToggle(): void };
}

const TOOL_ICON: Record<TopPopup, BattleToolIconName> = {
  reactions: "reactions",
  orders: "orders",
  legend: "legend",
  layout: "layout",
};

/** 一個工具鈕＋它的面板；Esc、點外面關閉與「同時只開一張」由 `usePopupMenu` 負責。 */
function TopTool({ tool: t, isOpen, onToggle }: { tool: Tool; isOpen: boolean; onToggle(): void }) {
  const menu = usePopupMenu({ open: isOpen, setOpen: (v) => v !== isOpen && onToggle() });
  const marked = t.badge !== undefined && t.badge !== "";
  return (
    <div className="top-tool" ref={menu.rootRef}>
      <Hint text={isOpen ? null : `${t.label}${marked ? "（已設定）" : ""}`}>
        <button
          type="button"
          className={`bhud-tool${isOpen ? " selected" : ""}`}
          aria-label={t.label}
          aria-expanded={isOpen}
          aria-haspopup="dialog"
          data-tool={t.id}
          onClick={onToggle}
        >
          <BattleToolIcon name={TOOL_ICON[t.id]} />
          {marked && <span className="top-tool-badge">{t.badge}</span>}
        </button>
      </Hint>
      {isOpen && (
        <div className="top-popup popup-menu" role="dialog" aria-label={t.label}>
          {t.content}
        </div>
      )}
    </div>
  );
}

export function BattleTopBar({ tools, open, onToggle, exit, save, telegraph }: Props) {
  return (
    <div className="battle-top-tools" aria-label="戰鬥工具">
      <Hint text={telegraph.open ? "收起環境預告" : "環境預告"}>
        <button
          type="button"
          className={`bhud-tool${telegraph.open ? " selected" : ""}`}
          aria-label="環境預告"
          aria-pressed={telegraph.open}
          data-tool="telegraph"
          onClick={telegraph.onToggle}
        >
          <BattleToolIcon name="telegraph" />
        </button>
      </Hint>
      {tools.map((t) => (
        <TopTool key={t.id} tool={t} isOpen={open === t.id} onToggle={() => onToggle(t.id)} />
      ))}
      {save !== null && (
        <Hint text="存檔">
          <button type="button" className="bhud-tool" aria-label="存檔" data-tool="save" disabled={save.busy} onClick={save.onSave}>
            <BattleToolIcon name="save" />
          </button>
        </Hint>
      )}
      {exit !== null && (
        <Hint text={exit.label}>
          <button type="button" className="bhud-tool battle-leave" data-sfx="ui_cancel" aria-label={exit.label} data-tool="exit" onClick={exit.onExit}>
            <BattleToolIcon name="exit" />
          </button>
        </Hint>
      )}
    </div>
  );
}
